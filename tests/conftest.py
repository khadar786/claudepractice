import sqlite3

import pytest
from werkzeug.security import generate_password_hash

import app as flask_app_module
from database import db as db_module
from database import queries as queries_module


def _build_in_memory_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(
        """
        CREATE TABLE users (
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
        CREATE TABLE expenses (
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
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (
            "Demo User",
            "demo@spendly.com",
            generate_password_hash("demo123"),
            "2026-01-15 10:00:00",
        ),
    )
    uid = cursor.lastrowid
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        [
            (uid, 12.50, "Food",          "2026-05-01", "Lunch sandwich"),
            (uid, 30.00, "Transport",     "2026-05-02", "Monthly metro"),
            (uid, 75.40, "Bills",         "2026-05-03", "Electricity bill"),
            (uid, 45.00, "Health",        "2026-05-04", "Pharmacy"),
            (uid, 15.99, "Entertainment", "2026-05-05", "Movie ticket"),
            (uid, 89.99, "Shopping",      "2026-05-06", "T-shirts"),
            (uid, 22.30, "Food",          "2026-05-06", "Dinner takeout"),
            (uid, 10.00, "Other",         "2026-05-07", "Misc cash expense"),
        ],
    )
    conn.commit()
    return conn, uid


@pytest.fixture
def in_memory_conn():
    conn, uid = _build_in_memory_db()
    yield conn, uid
    conn.close()


@pytest.fixture
def app(monkeypatch):
    conn, seed_uid = _build_in_memory_db()

    class _NoClose:
        def __init__(self, c):
            self._c = c

        def execute(self, *a, **kw):
            return self._c.execute(*a, **kw)

        def executemany(self, *a, **kw):
            return self._c.executemany(*a, **kw)

        def commit(self):
            return self._c.commit()

        def close(self):
            pass  # prevent tests from closing the shared in-memory connection

        def __getattr__(self, n):
            return getattr(self._c, n)

    monkeypatch.setattr(db_module, "get_db", lambda: _NoClose(conn))
    monkeypatch.setattr(queries_module, "get_db", lambda: _NoClose(conn))

    flask_app_module.app.config.update(TESTING=True, SECRET_KEY="test-secret")

    yield flask_app_module.app, seed_uid
    conn.close()


@pytest.fixture
def client(app):
    a, uid = app
    return a.test_client(), uid


@pytest.fixture
def authenticated_client(client):
    tc, uid = client
    with tc.session_transaction() as sess:
        sess["user_id"] = uid
    return tc, uid
