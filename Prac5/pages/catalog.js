const { esc, card } = require("../views");

module.exports = ({ products, categories, user, query, category, sort }) => `
  <div class="bg-white border rounded p-3 mb-3 shadow-sm">
    <div class="d-flex flex-wrap gap-2 mb-3">
      <a class="btn btn-sm ${!category ? "btn-dark" : "btn-light"}" href="/">Все</a>
      ${categories.map((item) => `<a class="btn btn-sm ${category === item.slug ? "btn-dark" : "btn-light"}" href="/?category=${encodeURIComponent(item.slug)}">${esc(item.name)}</a>`).join("")}
    </div>
    <form class="filters" method="get">
      <input class="form-control" name="q" placeholder="Поиск" value="${esc(query.q || "")}">
      <select class="form-select" name="category">
        <option value="">Все категории</option>
        ${categories.map((item) => `<option value="${esc(item.slug)}" ${category === item.slug ? "selected" : ""}>${esc(item.name)}</option>`).join("")}
      </select>
      <input class="form-control" name="min_price" type="number" step="0.01" min="0" placeholder="Цена от" value="${esc(query.min_price || "")}">
      <input class="form-control" name="max_price" type="number" step="0.01" min="0" placeholder="Цена до" value="${esc(query.max_price || "")}">
      <select class="form-select" name="sort">
        <option value="">Без сортировки</option>
        <option value="price_asc" ${sort === "price_asc" ? "selected" : ""}>Цена ↑</option>
        <option value="price_desc" ${sort === "price_desc" ? "selected" : ""}>Цена ↓</option>
      </select>
      <button class="btn btn-dark">Применить</button>
    </form>
  </div>
  <div class="row g-3">${products.map((product) => card(product, user)).join("") || "<p>Товаров нет.</p>"}</div>
`;
