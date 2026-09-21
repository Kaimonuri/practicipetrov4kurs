const { DatabaseSync } = require('node:sqlite');
const path = require('path');
const bcrypt = require('bcryptjs');
const db = new DatabaseSync(path.join(__dirname, 'dev.db'));
db.transaction = (fn) => (...args) => { db.exec('BEGIN IMMEDIATE'); try { const result = fn(...args); db.exec('COMMIT'); return result; } catch (error) { db.exec('ROLLBACK'); throw error; } };
db.exec('PRAGMA journal_mode = WAL');
db.exec('PRAGMA foreign_keys = ON');
db.exec(`
CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE COLLATE NOCASE NOT NULL, password TEXT NOT NULL, full_name TEXT NOT NULL DEFAULT '', phone TEXT NOT NULL DEFAULT '', email TEXT NOT NULL DEFAULT '', role TEXT NOT NULL DEFAULT 'customer');
CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY, name TEXT NOT NULL, slug TEXT UNIQUE NOT NULL);
CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, category_id INTEGER REFERENCES categories(id), name TEXT NOT NULL, slug TEXT UNIQUE NOT NULL, description TEXT NOT NULL DEFAULT '', price INTEGER NOT NULL CHECK(price>=0), stock INTEGER NOT NULL CHECK(stock>=0), image TEXT NOT NULL DEFAULT '', available INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS coupons (id INTEGER PRIMARY KEY, code TEXT UNIQUE COLLATE NOCASE NOT NULL, discount_type TEXT NOT NULL, value REAL NOT NULL, active INTEGER NOT NULL DEFAULT 1, valid_from TEXT, valid_until TEXT);
CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id), first_name TEXT NOT NULL, last_name TEXT NOT NULL, email TEXT NOT NULL, address TEXT NOT NULL, postal_code TEXT NOT NULL, city TEXT NOT NULL, delivery_method TEXT NOT NULL, delivery_date TEXT NOT NULL, payment_method TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'New', coupon_code TEXT NOT NULL DEFAULT '', discount_amount INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS order_items (id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(id), product_id INTEGER NOT NULL REFERENCES products(id), price INTEGER NOT NULL, quantity INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY, product_id INTEGER NOT NULL REFERENCES products(id), user_id INTEGER NOT NULL REFERENCES users(id), rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5), comment TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(product_id,user_id));
CREATE TABLE IF NOT EXISTS wishlist (user_id INTEGER NOT NULL REFERENCES users(id), product_id INTEGER NOT NULL REFERENCES products(id), PRIMARY KEY(user_id,product_id));
`);
if (!db.prepare('SELECT id FROM users WHERE username = ?').get('lab16')) {
  db.prepare('INSERT INTO users (username,password,full_name,role) VALUES (?,?,?,?)').run('lab16', bcrypt.hashSync('prac3', 12), 'Администратор', 'admin');
}
module.exports = db;

