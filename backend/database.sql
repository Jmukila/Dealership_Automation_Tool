DROP TABLE IF EXISTS generated_creatives;
DROP TABLE IF EXISTS generation_jobs;
DROP TABLE IF EXISTS assets;
DROP TABLE IF EXISTS dealerships;
DROP TABLE IF EXISTS accounts;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);

CREATE TABLE accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE dealerships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    panel_path TEXT NOT NULL,
    logo_light_path TEXT,
    logo_dark_path TEXT,
    FOREIGN KEY (account_id) REFERENCES accounts (id)
);

CREATE TABLE assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    name TEXT NOT NULL,
    file_path TEXT NOT NULL
);

CREATE TABLE generation_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL UNIQUE,
    account_id INTEGER NOT NULL,
    background_path TEXT NOT NULL,
    zip_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts (id)
);

CREATE TABLE generated_creatives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    dealership_id INTEGER NOT NULL,
    format TEXT NOT NULL,
    output_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES generation_jobs (job_id),
    FOREIGN KEY (dealership_id) REFERENCES dealerships (id)
);

INSERT INTO users (username, password_hash)
VALUES ('admin', 'admin123');
