const { esc, money, form } = require("../views");

module.exports = ({ user, total, minimumDate }) => {
  const fields = `
    <label>Имя<input name="first_name" required></label>
    <label>Фамилия<input name="last_name" required></label>
    <label>Почта<input name="email" type="email" value="${esc(user.email || "")}" required></label>
    <label>Адрес<input name="address" required></label>
    <label>Индекс<input name="postal_code" required></label>
    <label>Город<input name="city" required></label>
    <label>Доставка<select name="delivery_method"><option value="courier">Курьерская доставка</option><option value="pickup">Самовывоз</option></select></label>
    <label>Дата доставки<input type="date" name="delivery_date" min="${minimumDate}" required></label>
    <label>Оплата<select name="payment_method"><option value="on_receipt">При получении</option><option value="sbp">СБП</option></select></label>
  `;
  return `<section class="auth panel"><h1>Оформление заказа</h1><p>К оплате: <strong>${money(total)}</strong></p>${form("/checkout", fields, "Подтвердить заказ")}</section>`;
};
