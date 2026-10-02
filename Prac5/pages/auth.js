const { esc, form } = require("../views");

function register() {
  const fields = `
    <label>Логин<input name="username" required minlength="6" data-validate="username"></label>
    <label>ФИО<input name="full_name" required data-validate="full_name"></label>
    <label>Телефон<input name="phone" required placeholder="8(999)123-45-67" data-validate="phone"></label>
    <label>Почта<input name="email" type="email" required data-validate="email"></label>
    <label>Пароль<input name="password" type="password" minlength="8" required data-validate="password"></label>
  `;
  return `<section class="auth panel"><h1>Регистрация</h1>${form("/register", fields, "Создать аккаунт")}<p>Уже есть аккаунт? <a href="/login">Войти</a></p></section>`;
}

function login(next = "") {
  const fields = `<input type="hidden" name="next" value="${esc(next)}"><label>Логин<input name="username" required></label><label>Пароль<input name="password" type="password" required></label>`;
  return `<section class="auth panel"><h1>Вход</h1>${form("/login", fields, "Войти")}<p><a href="/register">Еще не зарегистрированы? Регистрация</a></p></section>`;
}

module.exports = { register, login };
