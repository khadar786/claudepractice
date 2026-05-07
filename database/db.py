import os
import sqlite3

from werkzeug.security import generate_password_hash


DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "expense_tracker.db",
)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    try:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    name          TEXT NOT NULL,
                    email         TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at    TEXT DEFAULT (datetime('now'))
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS expenses (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL,
                    amount      REAL NOT NULL,
                    category    TEXT NOT NULL,
                    date        TEXT NOT NULL,
                    description TEXT,
                    created_at  TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
                """
            )
    finally:
        conn.close()


def seed_db():
    conn = get_db()
    try:
        existing = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if existing > 0:
            return

        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
        )
        user_id = cursor.lastrowid

        expenses = [
            (user_id, 12.50, "Food",          "2026-05-01", "Lunch sandwich"),
            (user_id, 30.00, "Transport",     "2026-05-02", "Monthly metro"),
            (user_id, 75.40, "Bills",         "2026-05-03", "Electricity bill"),
            (user_id, 45.00, "Health",        "2026-05-04", "Pharmacy"),
            (user_id, 15.99, "Entertainment", "2026-05-05", "Movie ticket"),
            (user_id, 89.99, "Shopping",      "2026-05-06", "T-shirts"),
            (user_id, 22.30, "Food",          "2026-05-06", "Dinner takeout"),
            (user_id, 10.00, "Other",         "2026-05-07", "Misc cash expense"),
        ]
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            expenses,
        )
        conn.commit()
    finally:
        conn.close()
