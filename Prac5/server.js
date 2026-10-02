require("dotenv").config();
const express = require("express");
const session = require("express-session");
const { body, validationResult } = require("express-validator");
const helmet = require("helmet");
const multer = require("multer");
const bcrypt = require("bcryptjs");
const crypto = require("crypto");
const path = require("path");
const fs = require("fs");
const db = require("./db");
const { layout } = require("./views");
const {
  catalogPage,
  productPage,
  registerPage,
  loginPage,
  profilePage,
  cartPage,
  checkoutPage,
  wishlistPage,
  adminPage,
  errorPage,
} = require("./pages");
const app = express();
let catalogCache = null;
app.use(helmet({ contentSecurityPolicy: false }));
app.use(express.urlencoded({ extended: false }));
app.use(express.json());
app.use("/public", express.static(path.join(__dirname, "public"), { maxAge: "1d" }));
//1. Сессии и HttpOnly cookie
app.use(
  session({
    secret: process.env.SESSION_SECRET || "local-development-secret-change-me",
    resave: false,
    saveUninitialized: false,
    cookie: {
      httpOnly: true,
      sameSite: "lax",
      secure: process.env.COOKIE_SECURE === "true",
      maxAge: 7 * 86400000,
    },
  }),
);
//2. Определение текущего пользователя и корзины
app.use((req, res, next) => {
  req.user = req.session.userId
    ? db
        .prepare("SELECT id,username,full_name,email,role FROM users WHERE id=?")
        .get(req.session.userId)
    : null;
  req.session.cart ??= {};
  next();
});
function go(res, url = "/") {
  res.redirect(url);
}
function message(req, text) {
  req.session.notice = text;
}
function page(req, res, title, content, status = 200) {
  const notice = req.session.notice;
  delete req.session.notice;
  res.status(status).send(layout(title, content, req.user, notice, cartCount(req)));
}
function error(req, res, text, status = 400) {
  page(
    req,
    res,
    "Ошибка",
    errorPage(text),
    status,
  );
}
function auth(req, res, next) {
  if (!req.user) return go(res, "/login");
  next();
}
//3. Защита административных маршрутов
function admin(req, res, next) {
  if (!req.user) return go(res, `/login?next=${encodeURIComponent(req.originalUrl)}`);
  if (req.user.role !== "admin")
    return error(req, res, "Доступ разрешён только администратору.", 403);
  next();
}
function cartCount(req) {
  return Object.values(req.session.cart).reduce((a, b) => a + b, 0);
}
function cartItems(req) {
  return Object.entries(req.session.cart)
    .map(([id, quantity]) => {
      const p = db.prepare("SELECT * FROM products WHERE id=?").get(id);
      return p ? { ...p, quantity, total: p.price * quantity } : null;
    })
    .filter(Boolean);
}
function coupon(code) {
  if (!code) return null;
  const c = db.prepare("SELECT * FROM coupons WHERE code=? AND active=1").get(code);
  if (!c) return null;
  const now = new Date().toISOString();
  return (!c.valid_from || c.valid_from <= now) && (!c.valid_until || c.valid_until >= now)
    ? c
    : null;
}
function totals(req) {
  const subtotal = cartItems(req).reduce((a, i) => a + i.total, 0),
    c = coupon(req.session.coupon);
  const discount = c
    ? Math.min(
        subtotal,
        c.discount_type === "percent"
          ? Math.round((subtotal * c.value) / 100)
          : Math.round(c.value * 100),
      )
    : 0;
  return { subtotal, discount, total: subtotal - discount, coupon: c };
}
function verifyPassword(input, stored) {
  if (stored.startsWith("pbkdf2_sha256$")) {
    const [, iterations, salt, hash] = stored.split("$");
    const actual = crypto.pbkdf2Sync(input, salt, Number(iterations), 32, "sha256");
    const expected = Buffer.from(hash, "base64");
    return actual.length === expected.length && crypto.timingSafeEqual(actual, expected);
  }
  return bcrypt.compareSync(input, stored);
}
//4. Серверная валидация регистрации
const usernamePattern = /^[A-Za-z0-9]{6,}$/;

const registration = [
  body("username")
    .matches(usernamePattern)
    .withMessage("Логин: латиница и цифры, минимум 6 символов."),
  body("password").isLength({ min: 8 }).withMessage("Пароль: минимум 8 символов."),
  body("full_name")
    .matches(/^[А-Яа-яЁё]+(?: [А-Яа-яЁё]+)+$/u)
    .withMessage("ФИО: кириллица и пробелы."),
  body("phone")
    .matches(/^8\(\d{3}\)\d{3}-\d{2}-\d{2}$/)
    .withMessage("Телефон: 8(XXX)XXX-XX-XX."),
  body("email").isEmail().withMessage("Некорректная почта."),
];

function validationErrors(req) {
  return validationResult(req)
    .array()
    .map(({ msg }) => msg);
}

//5. Каталог: поиск, категории, цены и сортировка
app.get("/", (req, res) => {
  const q = String(req.query.q || "").trim(),
    cat = String(req.query.category || ""),
    sort = String(req.query.sort || "");
  const params = [],
    parts = ["p.available=1"];
  if (q) {
    parts.push("(p.name LIKE ? OR p.description LIKE ?)");
    params.push(`%${q}%`, `%${q}%`);
  }
  if (cat) {
    parts.push("c.slug=?");
    params.push(cat);
  }
  if (req.query.min_price) {
    parts.push("p.price>=?");
    params.push(Math.round(Number(req.query.min_price) * 100) || 0);
  }
  if (req.query.max_price) {
    parts.push("p.price<=?");
    params.push(Math.round(Number(req.query.max_price) * 100) || 0);
  }
  const order =
    sort === "price_asc" ? "p.price ASC" : sort === "price_desc" ? "p.price DESC" : "p.id DESC";
  const products = db
    .prepare(
      `SELECT p.*,c.name category FROM products p JOIN categories c ON c.id=p.category_id WHERE ${parts.join(" AND ")} ORDER BY ${order}`,
    )
    .all(...params);
  const categories = db.prepare("SELECT * FROM categories ORDER BY name").all();
  page(
    req,
    res,
    "Магазин мебели",
    catalogPage({ products, categories, user: req.user, query: req.query, category: cat, sort }),
  );
});
//6. Публичный REST API и кеш каталога
app.get("/api/products", (req, res) => {
  res.set("Cache-Control", "public, max-age=60");
  if (!catalogCache || catalogCache.expires < Date.now())
    catalogCache = {
      expires: Date.now() + 60000,
      items: db
        .prepare(
          "SELECT id,category_id,name,slug,description,price,stock,image FROM products WHERE available=1 ORDER BY id DESC",
        )
        .all(),
    };
  res.json(catalogCache.items);
});
app.get("/api/products/:id", (req, res) => {
  const p = db.prepare("SELECT * FROM products WHERE id=? AND available=1").get(req.params.id);
  p ? res.json(p) : res.status(404).json({ error: "Товар не найден" });
});
app.get("/product/:slug", (req, res) => {
  const p = db.prepare("SELECT * FROM products WHERE slug=? AND available=1").get(req.params.slug);
  if (!p) return error(req, res, "Товар не найден", 404);
  const reviews = db
    .prepare(
      "SELECT r.*,u.username FROM reviews r JOIN users u ON u.id=r.user_id WHERE product_id=? ORDER BY r.created_at DESC",
    )
    .all(p.id);
  const canReview =
    req.user &&
    db
      .prepare(
        "SELECT 1 FROM order_items i JOIN orders o ON o.id=i.order_id WHERE o.user_id=? AND o.status='Completed' AND i.product_id=? LIMIT 1",
      )
      .get(req.user.id, p.id);
  page(
    req,
    res,
    p.name,
    productPage({ product: p, reviews, user: req.user, canReview }),
  );
});
//7. Отзыв только после завершённого заказа
app.post("/product/:slug/review", auth, (req, res) => {
  const p = db.prepare("SELECT * FROM products WHERE slug=?").get(req.params.slug);
  if (!p) return error(req, res, "Товар не найден", 404);
  const allowed = db
    .prepare(
      "SELECT 1 FROM order_items i JOIN orders o ON o.id=i.order_id WHERE o.user_id=? AND o.status='Completed' AND i.product_id=? LIMIT 1",
    )
    .get(req.user.id, p.id);
  if (!allowed) return error(req, res, "Отзыв можно оставить после завершения заказа.", 403);
  const rating = Number(req.body.rating),
    comment = String(req.body.comment || "").trim();
  if (!Number.isInteger(rating) || rating < 1 || rating > 5 || !comment)
    return error(req, res, "Укажите оценку и комментарий.");
  db.prepare(
    "INSERT INTO reviews(product_id,user_id,rating,comment) VALUES(?,?,?,?) ON CONFLICT(product_id,user_id) DO UPDATE SET rating=excluded.rating,comment=excluded.comment",
  ).run(p.id, req.user.id, rating, comment);
  go(res, `/product/${p.slug}`);
});
app.get("/register", (req, res) =>
  page(
    req,
    res,
    "Регистрация",
    registerPage(),
  ),
);
app.get("/api/validate-username", (req, res) => {
  const username = String(req.query.username || "");
  res.json({
    valid:
      usernamePattern.test(username) &&
        !db.prepare("SELECT 1 FROM users WHERE username=?").get(username),
  });
});
//8. Создание пользователя и хеширование пароля
app.post("/register", registration, (req, res) => {
  const errors = validationErrors(req);
  if (db.prepare("SELECT 1 FROM users WHERE username=?").get(req.body.username))
    errors.push("Логин занят.");
  if (errors.length) return error(req, res, errors.join(" "));
  db.prepare("INSERT INTO users(username,password,full_name,phone,email) VALUES(?,?,?,?,?)").run(
    req.body.username,
    bcrypt.hashSync(req.body.password, 12),
    req.body.full_name,
    req.body.phone,
    req.body.email,
  );
  message(req, "Регистрация завершена. Войдите в аккаунт.");
  go(res, "/login");
});
app.get("/login", (req, res) => {
  const next = String(req.query.next || "");
  const safeNext = next.startsWith("/") && !next.startsWith("//") ? next : "";
  page(
    req,
    res,
    "Вход",
    loginPage(safeNext),
  );
});
//9. Вход и создание пользовательской сессии
app.post("/login", (req, res) => {
  const user = db.prepare("SELECT * FROM users WHERE username=?").get(req.body.username);
  if (!user || !verifyPassword(String(req.body.password || ""), user.password))
    return error(req, res, "Неверный логин или пароль.", 401);
  req.session.regenerate((err) => {
    if (err) return error(req, res, "Ошибка сессии", 500);
    req.session.userId = user.id;
    req.session.cart = {};
    const next = String(req.body.next || "");
    const safeNext = next.startsWith("/") && !next.startsWith("//") ? next : "";
    go(res, safeNext || (user.role === "admin" ? "/admin" : "/profile"));
  });
});
app.post("/logout", (req, res) => req.session.destroy(() => go(res, "/")));
app.get("/profile", auth, (req, res) => {
  const orders = db
    .prepare("SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC")
    .all(req.user.id)
    .map((order) => ({
      ...order,
      items: db
        .prepare(
          "SELECT i.*,p.name FROM order_items i JOIN products p ON p.id=i.product_id WHERE i.order_id=?",
        )
        .all(order.id),
    }));
  page(
    req,
    res,
    "Личный кабинет",
    profilePage({ user: req.user, orders, statusLabel }),
  );
});
function statusLabel(s) {
  return { New: "Новый", Processing: "В обработке", Completed: "Завершено" }[s] || s;
}
//10. Добавление товара в сессионную корзину
app.post("/cart/add/:id", (req, res) => {
  const p = db.prepare("SELECT * FROM products WHERE id=? AND available=1").get(req.params.id),
    qty = Number(req.body.quantity || 1);
  if (!p) return error(req, res, "Товар не найден", 404);
  if (
    !Number.isInteger(qty) ||
    qty < 1 ||
    qty > 99 ||
    qty + (req.session.cart[p.id] || 0) > p.stock
  )
    return error(req, res, "Недостаточно товара на складе.");
  req.session.cart[p.id] = (req.session.cart[p.id] || 0) + qty;
  message(req, "Товар добавлен в корзину.");
  go(res, "/cart");
});
app.post("/cart/update/:id", (req, res) => {
  const p = db.prepare("SELECT * FROM products WHERE id=?").get(req.params.id),
    qty = Number(req.body.quantity);
  if (!p || !Number.isInteger(qty) || qty < 0 || qty > p.stock)
    return error(req, res, "Неверное количество.");
  if (qty) req.session.cart[p.id] = qty;
  else delete req.session.cart[p.id];
  go(res, "/cart");
});
app.post("/cart/remove/:id", (req, res) => {
  delete req.session.cart[req.params.id];
  go(res, "/cart");
});
app.get("/cart", (req, res) => {
  const items = cartItems(req),
    t = totals(req);
  page(req, res, "Корзина", cartPage({ items, totals: t, couponCode: req.session.coupon }));
});
//11. Проверка и применение промокода
app.post("/coupon", (req, res) => {
  const c = coupon(String(req.body.code || "").trim());
  req.session.coupon = c ? c.code : null;
  message(req, c ? "Промокод применён." : "Промокод не найден или не действует.");
  go(res, "/cart");
});
app.get("/checkout", (req, res) => {
  if (!cartItems(req).length) return go(res, "/cart");
  page(
    req,
    res,
    "Оформление заказа",
    checkoutPage({
      user: req.user || {},
      total: totals(req).total,
      minimumDate: new Date().toISOString().slice(0, 10),
    }),
  );
});
//12. Оформление заказа в транзакции и списание остатков
app.post(
  "/checkout",
  [
    body("email").isEmail(),
    body("delivery_method").isIn(["courier", "pickup"]),
    body("payment_method").isIn(["on_receipt", "sbp"]),
    body("delivery_date").isISO8601(),
  ],
  (req, res) => {
    if (validationErrors(req).length) return error(req, res, "Проверьте данные заказа.");
    for (const k of ["first_name", "last_name", "address", "postal_code", "city"])
      if (!String(req.body[k] || "").trim()) return error(req, res, "Заполните все поля.");
    if (req.body.delivery_date < new Date().toISOString().slice(0, 10))
      return error(req, res, "Дата доставки не может быть в прошлом.");
    const items = cartItems(req);
    if (!items.length) return go(res, "/cart");
    try {
      const id = db.transaction(() => {
        for (const i of items) {
          const p = db.prepare("SELECT stock,available FROM products WHERE id=?").get(i.id);
          if (!p || !p.available || p.stock < i.quantity)
            throw Error(`Недостаточно товара: ${i.name}`);
        }
        const t = totals(req);
        const result = db
          .prepare(
            "INSERT INTO orders(user_id,first_name,last_name,email,address,postal_code,city,delivery_method,delivery_date,payment_method,status,coupon_code,discount_amount) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
          )
          .run(
            req.user?.id || null,
            req.body.first_name,
            req.body.last_name,
            req.body.email,
            req.body.address,
            req.body.postal_code,
            req.body.city,
            req.body.delivery_method,
            req.body.delivery_date,
            req.body.payment_method,
            "New",
            t.coupon?.code || "",
            t.discount,
          );
        for (const i of items) {
          db.prepare(
            "INSERT INTO order_items(order_id,product_id,price,quantity) VALUES(?,?,?,?)",
          ).run(result.lastInsertRowid, i.id, i.price, i.quantity);
          db.prepare(
            "UPDATE products SET stock=stock-?,available=CASE WHEN stock-? > 0 THEN 1 ELSE 0 END WHERE id=?",
          ).run(i.quantity, i.quantity, i.id);
        }
        return result.lastInsertRowid;
      })();
      req.session.cart = {};
      req.session.coupon = null;
      catalogCache = null;
      message(req, `Заказ №${id} оформлен.`);
      go(res, req.user ? "/profile" : "/");
    } catch (e) {
      error(req, res, e.message);
    }
  },
);
app.get("/wishlist", auth, (req, res) => {
  const items = db
    .prepare("SELECT p.* FROM wishlist w JOIN products p ON p.id=w.product_id WHERE w.user_id=?")
    .all(req.user.id);
  page(req, res, "Избранное", wishlistPage({ items, user: req.user }));
});
//13. Добавление и удаление товара из избранного
app.post("/wishlist/:id", auth, (req, res) => {
  const p = db.prepare("SELECT * FROM products WHERE id=? AND available=1").get(req.params.id);
  if (!p) return error(req, res, "Товар не найден", 404);
  const existing = db
    .prepare("SELECT 1 FROM wishlist WHERE user_id=? AND product_id=?")
    .get(req.user.id, p.id);
  if (existing)
    db.prepare("DELETE FROM wishlist WHERE user_id=? AND product_id=?").run(req.user.id, p.id);
  else db.prepare("INSERT INTO wishlist(user_id,product_id) VALUES(?,?)").run(req.user.id, p.id);
  go(
    res,
    req.get("Referer")?.startsWith(`${req.protocol}://${req.get("host")}`)
      ? req.get("Referer")
      : "/wishlist",
  );
});
//14. Multer: загрузка и проверка изображений
const upload = multer({
  storage: multer.diskStorage({
    destination: path.join(__dirname, "public", "uploads"),
    filename: (req, file, cb) =>
      cb(null, crypto.randomUUID() + path.extname(file.originalname).toLowerCase()),
  }),
  limits: { fileSize: 5 * 1024 * 1024 },
  fileFilter: (req, file, cb) =>
    cb(null, ["image/jpeg", "image/png", "image/webp"].includes(file.mimetype)),
});
//15. Административная панель
app.get("/admin", admin, (req, res) => {
  const status = ["New", "Processing", "Completed"].includes(req.query.status)
    ? req.query.status
    : null;
  const orders = (status
    ? db.prepare("SELECT * FROM orders WHERE status=? ORDER BY id DESC").all(status)
    : db.prepare("SELECT * FROM orders ORDER BY id DESC").all()
  ).map((order) => ({
    ...order,
    items: db
      .prepare(
        "SELECT i.*,p.name FROM order_items i JOIN products p ON p.id=i.product_id WHERE i.order_id=?",
      )
      .all(order.id),
  }));
  const products = db.prepare("SELECT * FROM products ORDER BY id DESC").all(),
    categories = db.prepare("SELECT * FROM categories").all();
  page(
    req,
    res,
    "Админ-панель",
    adminPage({ orders, products, categories, statusLabel }),
  );
});
//16. Массовая смена статусов заказов
app.post("/admin/orders/bulk", admin, (req, res) => {
  const ids = []
      .concat(req.body.ids || [])
      .map(Number)
      .filter(Number.isInteger),
    status = req.body.status;
  if (!["New", "Processing", "Completed"].includes(status) || !ids.length)
    return error(req, res, "Выберите заказы и статус.");
  const stmt = db.prepare("UPDATE orders SET status=? WHERE id=?");
  db.transaction(() => ids.forEach((id) => stmt.run(status, id)))();
  go(res, "/admin");
});
app.post("/admin/products", admin, upload.single("image"), (req, res) => {
  const { name, slug, description, category_id } = req.body,
    price = Math.round(Number(req.body.price) * 100),
    stock = Number(req.body.stock);
  if (
    !name ||
    !/^[a-z0-9-]+$/.test(slug) ||
    !Number.isInteger(price) ||
    price < 0 ||
    !Number.isInteger(stock) ||
    stock < 0 ||
    !db.prepare("SELECT 1 FROM categories WHERE id=?").get(category_id)
  )
    return error(req, res, "Проверьте данные товара.");
  try {
    db.prepare(
      "INSERT INTO products(category_id,name,slug,description,price,stock,image,available) VALUES(?,?,?,?,?,?,?,?)",
    ).run(
      category_id,
      name,
      slug,
      description || "",
      price,
      stock,
      req.file?.filename || "",
      stock > 0 ? 1 : 0,
    );
    catalogCache = null;
    go(res, "/admin");
  } catch (e) {
    error(req, res, "Товар с таким slug уже существует.");
  }
});
app.post("/admin/products/:id/image", admin, upload.single("image"), (req, res) => {
  if (!req.file) return error(req, res, "Выберите изображение JPEG, PNG или WebP.");
  db.prepare("UPDATE products SET image=? WHERE id=?").run(req.file.filename, req.params.id);
  catalogCache = null;
  go(res, "/admin");
});
app.post("/admin/coupons", admin, (req, res) => {
  const { code, discount_type, valid_until } = req.body,
    value = Number(req.body.value);
  if (
    !code ||
    !["percent", "fixed"].includes(discount_type) ||
    !Number.isFinite(value) ||
    value <= 0 ||
    (discount_type === "percent" && value > 100)
  )
    return error(req, res, "Проверьте промокод.");
  try {
    db.prepare("INSERT INTO coupons(code,discount_type,value,valid_until) VALUES(?,?,?,?)").run(
      code.trim(),
      discount_type,
      value,
      valid_until || null,
    );
    go(res, "/admin");
  } catch (e) {
    error(req, res, "Такой промокод уже существует.");
  }
});
app.get("/health", (req, res) => res.json({ status: "ok" }));
app.use((err, req, res, next) =>
  error(
    req,
    res,
    err.code === "LIMIT_FILE_SIZE" ? "Файл слишком большой." : "Ошибка загрузки файла.",
    400,
  ),
);
app.use((req, res) => error(req, res, "Страница не найдена", 404));
if (require.main === module)
  app.listen(process.env.PORT || 3000, () =>
    console.log(`Prac4: http://127.0.0.1:${process.env.PORT || 3000}`),
  );
module.exports = app;
