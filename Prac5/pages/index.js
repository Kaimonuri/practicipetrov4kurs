module.exports = {
  catalogPage: require("./catalog"),
  productPage: require("./product"),
  registerPage: require("./auth").register,
  loginPage: require("./auth").login,
  profilePage: require("./profile"),
  cartPage: require("./cart"),
  checkoutPage: require("./checkout"),
  wishlistPage: require("./wishlist"),
  adminPage: require("./admin"),
  errorPage: require("./error"),
};
