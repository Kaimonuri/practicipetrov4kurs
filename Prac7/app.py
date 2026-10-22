"""Учебный портал записи на услуги. Запуск: python3 app.py."""

import os
import re
import secrets
import sqlite3
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

ROOT = Path(__file__).resolve().parent

# Варианты услуг, статусов и оплаты, которые используются в формах приложения.
SERVICES = [
    "Комплексная диагностика и чистка ПК",
    "Замена комплектующих и модернизация",
    "Восстановление данных и настройка ОС",
]
STATUSES = ["Новая", "В работе", "Ремонт завершен"]
PAYMENTS = ["Наличными", "Перевод по номеру телефона"]


class Database:
    """Работа с SQLite: отдельное соединение для каждого запроса."""

    def __init__(self, path):
        self.path = path

    def connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        return db

    def initialize(self):
        with self.connect() as db:
            db.executescript((ROOT / "schema.sql").read_text())
            for i, name in enumerate(SERVICES, 1):
                db.execute("INSERT OR IGNORE INTO services VALUES (?, ?)", (i, name))
            # Пароль первого администратора задаётся при запуске и не хранится в исходниках.
            if db.execute("SELECT id FROM users WHERE login=?", ("Admin",)).fetchone():
                return
            admin_password = os.environ.get("ADMIN_PASSWORD", "")
            if len(admin_password) < 8:
                raise RuntimeError(
                    "При первом запуске задайте ADMIN_PASSWORD (не менее 8 символов)."
                )
            db.execute(
                """
                INSERT OR IGNORE INTO users(login, password_hash, full_name, phone, email, ROLE) 
                VALUES(?, ?, ?, ?, ?, ?)
                """,
                (
                    "Admin",
                    generate_password_hash(admin_password),
                    "Администратор",
                    "8(000)000-00-00",
                    "admin@example.local",
                    "admin",
                ),
            )


# Создаёт приложение Flask и настраивает его перед запуском.
def create_app(database_path=None):
    app = Flask(__name__)
    folder = ROOT / "instance"
    folder.mkdir(exist_ok=True)
    # Секретный ключ нужен для подписи сессии: пользователь не может незаметно её изменить.
    key_file = folder / "secret.key"
    if not key_file.exists():
        key_file.write_text(secrets.token_hex(32))
        key_file.chmod(0o600)
    # Ограничиваем размер запроса и задаём параметры cookie сессии.
    app.config.update(
        # Перечитываем HTML-шаблоны после изменения файлов во время работы сервера.
        TEMPLATES_AUTO_RELOAD=True,
        SECRET_KEY=os.environ.get("SECRET_KEY") or key_file.read_text(),
        MAX_CONTENT_LENGTH=65536,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    database = Database(database_path or folder / "master_service.sqlite3")
    database.initialize()

    def db():
        if "db" not in g:
            g.db = database.connect()
        return g.db

    @app.teardown_appcontext
    def close_db(error=None):
        if "db" in g:
            g.db.close()

    # Выполняется перед каждым запросом: определяет пользователя и проверяет отправку форм.
    @app.before_request
    def prepare():
        g.user = (
            db()
            .execute("SELECT * FROM users WHERE id=?", (session.get("user_id"),))
            .fetchone()
        )
        # CSRF-токен связывает форму с текущей сессией и защищает от поддельной отправки.
        if "csrf" not in session:
            session["csrf"] = secrets.token_hex(24)
        if request.method == "POST" and not secrets.compare_digest(
            session["csrf"], request.form.get("csrf", "")
        ):
            abort(400, "Форма устарела. Обновите страницу и повторите действие.")

    # Делает списки статусов и способов оплаты доступными во всех HTML-шаблонах.
    @app.context_processor
    def context():
        return dict(statuses=STATUSES, payments=PAYMENTS)

    # Декоратор доступа: гость направляется на вход, а админка доступна только администратору.
    def protected(admin=False):
        def decorator(fn):
            @wraps(fn)
            def wrapper(*args, **kwargs):
                if not g.user:
                    return redirect(url_for("login"))
                if admin and g.user["role"] != "admin":
                    abort(403)
                return fn(*args, **kwargs)

            return wrapper

        return decorator

    # Ссылка «На главную» выбирает нужную страницу в зависимости от входа и роли.
    @app.route("/")
    def home():
        return redirect(
            url_for(
                "admin"
                if g.user and g.user["role"] == "admin"
                else "applications" if g.user else "login"
            )
        )

    # GET показывает регистрацию; POST принимает заполненную форму и проверяет поля.
    @app.route("/register", methods=["GET", "POST"])
    def register():
        errors = {}
        data = request.form
        if request.method == "POST":
            # Регулярные выражения проверяют логин, кириллицу в ФИО, телефон и почту.
            rules = {
                "login": (
                    r"[A-Za-z0-9]{6,}",
                    "Логин: латиница и цифры, минимум 6 символов.",
                ),
                "full_name": (
                    r"[А-Яа-яЁё]+(?: +[А-Яа-яЁё]+)*",
                    "ФИО: только кириллица и пробелы.",
                ),
                "phone": (
                    r"8\([0-9]{3}\)[0-9]{3}-[0-9]{2}-[0-9]{2}",
                    "Телефон: 8(XXX)XXX-XX-XX.",
                ),
                "email": (
                    r"[^\s@]+@[^\s@]+\.[^\s@]+",
                    "Введите корректную электронную почту.",
                ),
            }
            for field, (pattern, message) in rules.items():
                if not re.fullmatch(pattern, data.get(field, "").strip()):
                    errors[field] = message
            # Длину пароля проверяем отдельно: требуется не менее восьми символов.
            if len(data.get("password", "")) < 8:
                errors["password"] = "Пароль должен содержать минимум 8 символов."
            if (
                db()
                .execute(
                    "SELECT id FROM users WHERE login=?",
                    (data.get("login", "").strip(),),
                )
                .fetchone()
            ):
                errors["login"] = "Этот логин уже занят."
            if not errors:
                try:
                    db().execute(
                        """
                        INSERT INTO users(login, password_hash, full_name, phone, email) 
                        VALUES(?, ?, ?, ?, ?)
                        """,
                        (
                            data["login"].strip(),
                            generate_password_hash(data["password"]),
                            data["full_name"].strip(),
                            data["phone"].strip(),
                            data["email"].strip(),
                        ),
                    )
                    db().commit()
                except sqlite3.IntegrityError:
                    errors["login"] = "Этот логин уже занят."
                else:
                    flash("Пользователь создан. Войдите в систему.")
                    return redirect(url_for("login"))
        # При ошибках возвращаем форму с пояснениями и введёнными данными, кроме пароля.
        return render_template(
            "register.html", errors=errors, data=data, title="Регистрация"
        )

    # Вход в личный кабинет: форма отправляет логин и пароль методом POST.
    @app.route("/login", methods=["GET", "POST"])
    def login():
        errors = {}
        if request.method == "POST":
            user = (
                db()
                .execute(
                    "SELECT * FROM users WHERE login=?",
                    (request.form.get("login", "").strip(),),
                )
                .fetchone()
            )
            # Сравниваем введённый пароль с хешем; при ошибке показываем общее сообщение.
            if not user or not check_password_hash(
                user["password_hash"], request.form.get("password", "")
            ):
                errors["form"] = "Неверный логин или пароль."
            else:
                session.clear()
                # Запоминаем вход в сессии, чтобы узнавать пользователя в следующих запросах.
                session["user_id"] = user["id"]
                return redirect(url_for("home"))
        return render_template("login.html", title="Вход", errors=errors)

    # Выход очищает сессию и возвращает посетителя на страницу авторизации.
    @app.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    # Страница личного кабинета показывает собственные заявки и оставленные отзывы.
    @app.get("/applications")
    @protected()
    def applications():
        rows = (
            db()
            .execute(
                """
                SELECT a.*, c.name, r.text AS review 
                FROM applications a 
                JOIN services c ON c.id = a.service_id 
                LEFT JOIN reviews r ON r.application_id = a.id 
                WHERE a.user_id = ? 
                ORDER BY a.id DESC
                """,
                (g.user["id"],),
            )
            .fetchall()
        )
        return render_template("applications.html", title="Мои заявки", rows=rows)

    # Форма заявки: выбор услуги, описание устройства, дата сдачи и способ оплаты.
    @app.route("/applications/new", methods=["GET", "POST"])
    @protected()
    def new_application():
        errors = {}
        data = request.form
        services = db().execute("SELECT * FROM services ORDER BY id").fetchall()
        if request.method == "POST":
            # Проверяем выбранную услугу на сервере: значения формы можно подменить.
            if data.get("service_id") not in [str(c["id"]) for c in services]:
                errors["service_id"] = "Выберите услугу из списка."
            # Проверяем формат ДД.ММ.ГГГГ и существование даты, например 31.02 не пройдёт.
            date = data.get("dropoff_date", "").strip()
            try:
                if not re.fullmatch(r"[0-9]{2}\.[0-9]{2}\.[0-9]{4}", date):
                    raise ValueError()
                date = datetime.strptime(date, "%d.%m.%Y").date().isoformat()
            except ValueError:
                errors["dropoff_date"] = "Укажите существующую дату в формате ДД.ММ.ГГГГ."
            # Описание обязательно; после удаления пробелов по краям — от 1 до 2000 символов.
            description = data.get("description", "").strip()
            if not 1 <= len(description) <= 2000:
                errors["description"] = "Опишите устройство и неисправность (от 1 до 2000 символов)."
            # Принимаются только два предусмотренных заданием способа оплаты.
            if data.get("payment") not in PAYMENTS:
                errors["payment"] = "Выберите способ оплаты."
            if not errors:
                db().execute(
                    """
                    INSERT INTO applications(user_id, service_id, dropoff_date, description, payment) 
                    VALUES(?, ?, ?, ?, ?)
                    """,
                    (g.user["id"], data["service_id"], date, description, data["payment"]),
                )
                db().commit()
                flash("Заявка отправлена администратору.")
                return redirect(url_for("applications"))
        return render_template(
            "new.html", title="Новая заявка", errors=errors, data=data, services=services
        )

    # Отзыв разрешён только владельцу заявки после завершения ремонта.
    @app.post("/applications/<int:application_id>/review")
    @protected()
    def review(application_id):
        row = (
            db()
            .execute(
                "SELECT * FROM applications WHERE id=? AND user_id=?",
                (application_id, g.user["id"]),
            )
            .fetchone()
        )
        if not row:
            abort(404)
        # До статуса «Ремонт завершен» отзыв запрещён, даже при прямой отправке запроса.
        if row["status"] != STATUSES[2]:
            abort(403)
        text = request.form.get("text", "").strip()
        if not 1 <= len(text) <= 2000:
            flash("Отзыв должен содержать от 1 до 2000 символов.")
        else:
            try:
                db().execute(
                    "INSERT INTO reviews(application_id,text) VALUES(?,?)",
                    (application_id, text),
                )
                db().commit()
                flash("Спасибо! Ваш отзыв сохранён.")
            except sqlite3.IntegrityError:
                flash("Вы уже оставили отзыв по этой заявке.")
        return redirect(url_for("applications"))

    # Администратор просматривает все заявки, применяет фильтр и переключает страницы.
    @app.get("/admin")
    @protected(admin=True)
    def admin():
        # Фильтр и номер страницы берутся из адреса, например /admin?status=Новая&page=2.
        status = request.args.get("status", "")
        if status and status not in STATUSES:
            abort(400)
        try:
            page = max(1, int(request.args.get("page", 1)))
        except ValueError:
            page = 1
        where = " WHERE a.status=?" if status else ""
        params = [status] if status else []
        total = (
            db()
            .execute("SELECT count(*) FROM applications a" + where, params)
            .fetchone()[0]
        )
        # На странице пять заявок; число страниц округляется вверх, минимум одна.
        pages = max(1, (total + 4) // 5)
        page = min(page, pages)
        rows = (
            db()
            .execute(
                """
                SELECT a.*, c.name, u.full_name, u.phone, u.email, r.text AS review 
                FROM applications a 
                JOIN services c ON c.id = a.service_id 
                JOIN users u ON u.id = a.user_id 
                LEFT JOIN reviews r ON r.application_id = a.id
                """ + where + " ORDER BY a.id DESC LIMIT 5 OFFSET ?",
                params + [(page - 1) * 5],
            )
            .fetchall()
        )
        return render_template(
            "admin.html",
            title="Панель администратора",
            rows=rows,
            selected=status,
            page=page,
            pages=pages,
            total=total,
        )

    # Обрабатывает кнопку «Сохранить статус»; доступ разрешён только администратору.
    @app.post("/admin/<int:application_id>/status")
    @protected(admin=True)
    def change_status(application_id):
        # Проверяем, что новый статус входит в список допустимых значений.
        status = request.form.get("status")
        if status not in STATUSES:
            abort(400)
        if (
            not db()
            .execute("SELECT id FROM applications WHERE id=?", (application_id,))
            .fetchone()
        ):
            abort(404)
        db().execute(
            "UPDATE applications SET status=? WHERE id=?", (status, application_id)
        )
        db().commit()
        flash("Статус заявки обновлён.")
        return redirect(url_for("admin"))

    # Шаблоны используют фильтр date_ru, чтобы показывать дату как ДД.ММ.ГГГГ.
    @app.template_filter("date_ru")
    def date_ru(value):
        return datetime.strptime(value, "%Y-%m-%d").strftime("%d.%m.%Y")

    # Единая страница для неверного запроса, запрета доступа, отсутствующей страницы и большого запроса.
    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(413)
    def error_page(error):
        return render_template("error.html", title="Ошибка", error=error), error.code

    return app


# Запускаем локальный сервер только при непосредственном выполнении app.py.
if __name__ == "__main__":
    create_app().run(
        host="127.0.0.1", port=int(os.environ.get("PORT", 8001)), debug=False
    )
