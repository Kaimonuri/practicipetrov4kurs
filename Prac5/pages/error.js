const { esc } = require("../views");

module.exports = (message) => `<section class="panel"><h1>Ошибка</h1><p>${esc(message)}</p><a class="button" href="javascript:history.back()">Назад</a></section>`;
