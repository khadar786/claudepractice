# Step 1: Database Setup — Implementation Plan

## Context
`database/db.py` is currently a stub of comments (`database/db.py:1-6`) and `app.py` never touches a database. Every future Spendly feature (auth, profile, expense CRUD) depends on a working SQLite layer with `users` + `expenses` tables and a seeded demo account. The spec at `.claude/specs/01-database-setup.md` fixes the schema, the three functions to implement (`get_db`, `init_db`, `seed_db`), and the startup wiring in `app.py`. Seeding must be idempotent so repeated `python app.py` runs don't duplicate rows.

## Files to change
- `database/db.py` — replace the stub with the three functions
- `app.py` — import and call `init_db()` + `seed_db()` once at startup inside `app.app_context()`

No new files. No new dependencies (`sqlite3` is stdlib; `werkzeug==3.1.6` is already pinned in `requirements.txt`).

## Implementation

### `database/db.py`

Imports:
```python
import os
import sqlite3
from werkzeug.security import generate_password_hash
```

Module constant — anchor the DB at the repo root regardless of cwd, and match the name already in `.gitignore`:
```python
DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "expense_tracker.db",
)
```
(Spec section 5A allows either `spendly.db` or `expense_tracker.db`; `.gitignore:2` and `CLAUDE.md` already commit to `expense_tracker.db`.)

**`get_db()`** — returns a fresh connection with row dict access and FK enforcement:
```python
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys = ON")
return conn
```

**`init_db()`** — `CREATE TABLE IF NOT EXISTS` for both tables, exactly the columns/constraints in spec sections 4A and 4B:
- `users(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at TEXT DEFAULT (datetime('now')))`
- `expenses(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, amount REAL NOT NULL, category TEXT NOT NULL, date TEXT NOT NULL, description TEXT, created_at TEXT DEFAULT (datetime('now')), FOREIGN KEY(user_id) REFERENCES users(id))`

Use `with conn:` for the implicit commit, then close.

**`seed_db()`** — idempotent demo data:
1. Open via `get_db()`.
2. `SELECT COUNT(*) FROM users` → if result > 0, close and return early.
3. Insert demo user with `generate_password_hash("demo123")`; capture `cursor.lastrowid` as `user_id`.
4. `executemany` the 8 sample expenses below (parameterized `?` placeholders only — no f-strings, no `%`).
5. `conn.commit()`, close.

Demo user: `name="Demo User"`, `email="demo@spendly.com"`, password hashed.

Sample expenses (8 rows, all 7 categories from spec section 10 covered, dates spread across the current month — today is 2026-05-07):

| date       | category      | amount | description       |
| ---------- | ------------- | ------ | ----------------- |
| 2026-05-01 | Food          | 12.50  | Lunch sandwich    |
| 2026-05-02 | Transport     | 30.00  | Monthly metro     |
| 2026-05-03 | Bills         | 75.40  | Electricity bill  |
| 2026-05-04 | Health        | 45.00  | Pharmacy          |
| 2026-05-05 | Entertainment | 15.99  | Movie ticket      |
| 2026-05-06 | Shopping      | 89.99  | T-shirts          |
| 2026-05-06 | Food          | 22.30  | Dinner takeout    |
| 2026-05-07 | Other         | 10.00  | Misc cash expense |

### `app.py`

Add after `app = Flask(__name__)` (and before the route definitions):
```python
from database.db import init_db, seed_db

with app.app_context():
    init_db()
    seed_db()
```
`get_db` is imported here only if a route in this step needs it — it doesn't, so keep the import minimal. Existing routes (`landing`, `register`, `login`, `terms`, `privacy`, plus the placeholder routes) remain untouched.

## Rules being enforced (per spec section 11)
- No ORM — raw `sqlite3` only.
- All SQL parameterized with `?` — no `format`, `%`, or f-strings inside SQL strings.
- `PRAGMA foreign_keys = ON` set on every `get_db()` connection.
- `amount` stored as REAL.
- Passwords hashed via `werkzeug.security.generate_password_hash`.
- `seed_db()` short-circuits when users already exist.
- Dates in `YYYY-MM-DD`.

## Verification
1. **Cold start.** Delete `expense_tracker.db` if it exists, then run `python app.py`. Server should start on port 5001 with no errors and the file should appear at the repo root.
2. **Idempotent restart.** Stop and re-run `python app.py`. No errors, no duplicate seed inserts.
3. **Schema and seed counts.** From a Python shell at repo root:
   ```python
   from database.db import get_db
   c = get_db()
   c.execute("SELECT COUNT(*) FROM users").fetchone()[0]      # → 1
   c.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]   # → 8
   sorted(r[0] for r in c.execute("SELECT DISTINCT category FROM expenses"))
   # → ['Bills','Entertainment','Food','Health','Other','Shopping','Transport']
   ```
4. **Foreign key enforcement.**
   ```python
   c.execute("INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
             (999, 1.0, "Food", "2026-05-07"))
   ```
   → raises `sqlite3.IntegrityError` (FK).
5. **Unique email enforcement.**
   ```python
   c.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
             ("Dup", "demo@spendly.com", "x"))
   ```
   → raises `sqlite3.IntegrityError` (UNIQUE).
6. **Password is hashed, not plaintext.**
   ```python
   c.execute("SELECT password_hash FROM users WHERE email=?", ("demo@spendly.com",)).fetchone()[0]
   ```
   → starts with `scrypt:` or `pbkdf2:`, not the literal `demo123`.

## Definition of done (mirrors spec section 14)
- [ ] `expense_tracker.db` is created on app startup at the repo root.
- [ ] Both tables exist with the schema above and FK + UNIQUE constraints active.
- [ ] Demo user exists with a hashed password.
- [ ] 8 sample expenses exist, covering all 7 categories.
- [ ] Repeated runs do not duplicate seed data.
- [ ] `python app.py` starts cleanly on port 5001.
- [ ] Every SQL statement uses `?` placeholders.
