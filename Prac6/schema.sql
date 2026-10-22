-- БРЕЙКПОИНТ 00: таблицы, типы полей, ограничения и связи базы данных.
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 login TEXT NOT NULL UNIQUE,
 password_hash TEXT NOT NULL,
 full_name TEXT NOT NULL,
 phone TEXT NOT NULL,
 email TEXT NOT NULL,
 role TEXT NOT NULL DEFAULT 'student' CHECK(role IN ('student','admin'))
);
CREATE TABLE IF NOT EXISTS courses (
 id INTEGER PRIMARY KEY,
 name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS applications (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER NOT NULL REFERENCES users(id),
 course_id INTEGER NOT NULL REFERENCES courses(id),
 start_date TEXT NOT NULL,
 payment TEXT NOT NULL CHECK(payment IN ('Наличными','Перевод по номеру телефона')),
 status TEXT NOT NULL DEFAULT 'Новая' CHECK(status IN ('Новая','Идет обучение','Обучение завершено')),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS reviews (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 application_id INTEGER NOT NULL UNIQUE REFERENCES applications(id),
 text TEXT NOT NULL CHECK(length(trim(text)) BETWEEN 1 AND 2000),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
