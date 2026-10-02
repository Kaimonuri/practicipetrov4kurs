const { card } = require("../views");

module.exports = ({ items, user }) => `<section><h1>Избранное</h1><div class="row g-3">${items.map((product) => card(product, user)).join("") || "<p>Здесь пока пусто.</p>"}</div></section>`;
