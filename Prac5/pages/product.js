const { esc, money, form, card } = require("../views");

module.exports = ({ product, reviews, user, canReview }) => `
  ${card(product, user, true)}
  <section class="panel">
    <h2>Отзывы</h2>
    ${reviews.map((review) => `<p><strong>${esc(review.username)} · ${review.rating}/5</strong><br>${esc(review.comment)}</p>`).join("") || "<p>Пока нет отзывов.</p>"}
    ${canReview ? form(`/product/${esc(product.slug)}/review`, '<select name="rating" required><option value="">Оценка</option>' + [1, 2, 3, 4, 5].map((number) => `<option>${number}</option>`).join("") + '</select><textarea name="comment" required maxlength="2000" placeholder="Ваш отзыв"></textarea>', "Опубликовать отзыв") : '<p class="muted">Отзыв доступен после завершённого заказа с этим товаром.</p>'}
  </section>
`;
