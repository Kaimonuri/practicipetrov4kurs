const { esc, money, form } = require("../views");

module.exports = ({ items, totals, couponCode }) => `
  <section class="panel">
    <h1>Корзина</h1>
    ${items.map((item) => `<div class="cart-row"><a href="/product/${esc(item.slug)}">${esc(item.name)}</a><span>${money(item.price)}</span>${form(`/cart/update/${item.id}`, `<input type="number" name="quantity" min="0" max="${item.stock}" value="${item.quantity}">`, "Обновить")}${form(`/cart/remove/${item.id}`, "", "Удалить")}</div>`).join("") || "<p>Корзина пуста.</p>"}
    <div class="totals"><p>Подытог: ${money(totals.subtotal)}</p><p>Скидка: ${money(totals.discount)}</p><h2>Итого: ${money(totals.total)}</h2></div>
    ${items.length ? `${form("/coupon", `<input name="code" placeholder="Промокод" value="${esc(couponCode || "")}">`, "Применить")}<a class="button" href="/checkout">Оформить заказ</a>` : ""}
  </section>
`;
