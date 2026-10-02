const { esc, money } = require("../views");

module.exports = ({ user, orders, statusLabel }) => `
  <section class="panel">
    <h1>${esc(user.full_name || user.username)}</h1>
    <p>${esc(user.email)}</p>
    <h2>История заказов</h2>
    ${orders.map((order) => `<article class="order"><div class="section-head"><strong>Заказ №${order.id}</strong><span class="badge">${statusLabel(order.status)}</span></div><p>${esc(order.created_at)} · ${esc(order.delivery_method)} · ${esc(order.delivery_date)}</p><ul>${order.items.map((item) => `<li>${esc(item.name)} × ${item.quantity} — ${money(item.price * item.quantity)}</li>`).join("")}</ul></article>`).join("") || "<p>Заказов пока нет.</p>"}
  </section>
`;
