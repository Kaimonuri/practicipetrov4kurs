PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    login TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'client' CHECK(role IN ('client','admin'))
);
CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    service_id INTEGER NOT NULL REFERENCES services(id),
    dropoff_date TEXT NOT NULL,
    description TEXT NOT NULL CHECK(length(trim(description)) BETWEEN 1 AND 2000),
    payment TEXT NOT NULL CHECK(payment IN ('Наличными','Перевод по номеру телефона')),
    status TEXT NOT NULL DEFAULT 'Новая' CHECK(status IN ('Новая','В работе','Ремонт завершен')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL UNIQUE REFERENCES applications(id),
    text TEXT NOT NULL CHECK(length(trim(text)) BETWEEN 1 AND 2000),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_applications_user
    ON applications(user_id, id DESC);
CREATE INDEX IF NOT EXISTS idx_applications_status
    ON applications(status, id DESC);
