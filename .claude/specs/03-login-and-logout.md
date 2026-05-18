# Spec: Login and Logout

## Overview

Implement user authentication so existing accounts can sign in and end their session. This step upgrades the stub `GET /login` route into a working form that accepts a POST, verifies credentials against the `users` table, and stores the authenticated user's id in the Flask session. It also replaces the `GET /logout` placeholder with a route that clears the session and redirects home. Login/logout is the gateway feature for every authenticated route that follows (profile, expenses), so it must be in place before Step 4.

## Depends on

- Step 01 — Database setup (`users` table, `get_db()`)
- Step 02 — Registration (`create_user`, registration form that produces hashed-password rows to verify against)

## Routes

- `GET /login` — render login form — public (already exists as stub, upgrade it)
- `POST /login` — verify credentials, populate `session["user_id"]`, redirect to `/profile` — public
- `GET /logout` — clear the session and redirect to `/` — logged-in (already exists as stub, upgrade it)

## Database changes

No new tables or columns. The existing `users` table (id, name, email, password_hash, created_at) is sufficient.

A new DB helper must be added to `database/db.py`:

- `get_user_by_email(email)` — runs a parameterised `SELECT ... FROM users WHERE email = ?` and returns the matching `sqlite3.Row` (or `None`). Email is lower-cased before the lookup so it matches the casing used by `create_user`.

## Templates

- **Modify:** `templates/login.html`
  - Change the form `action` from the hardcoded `/login` to `url_for('login')`
  - Confirm `name` attributes are present on `email` and `password` inputs (they already are — leave alone if so)
  - Keep the existing flash-message block; it already iterates `get_flashed_messages(with_categories=true)`
- **Modify:** `templates/base.html`
  - Swap the static "Sign in / Get started" nav links for a session-aware pair: show `Sign in` + `Get started` when `session.user_id` is not set; show `Profile` + `Sign out` (linking `url_for('logout')`) when it is

## Files to change

- `app.py` — upgrade `login()` to handle `GET` + `POST`, upgrade `logout()` to clear the session and redirect
- `database/db.py` — add `get_user_by_email()` helper
- `templates/login.html` — switch form `action` to `url_for('login')`
- `templates/base.html` — make navbar links session-aware

## Files to create

None.

## New dependencies

No new dependencies. Uses `flask.session`, `werkzeug.security.check_password_hash` (werkzeug is already installed), and the existing `flash` / `redirect` / `url_for`.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only — never use f-strings in SQL
- Passwords verified with `werkzeug.security.check_password_hash` — never compare hashes manually, never store or log plaintext passwords
- All templates extend `base.html`
- Use CSS variables — never hardcode hex values
- Use `url_for()` for every internal link — never hardcode URLs
- Use Flask's built-in `session` object; do not introduce Flask-Login or other session libraries
- On `POST /login`, server-side validation must check:
  1. Both `email` and `password` form fields are non-empty
  2. A user row exists for the (lower-cased) email
  3. `check_password_hash(row["password_hash"], password)` returns `True`
- On any failure, flash a single generic message — "Invalid email or password." — and re-render the form. Do not reveal which field was wrong (prevents user-enumeration)
- On success, set `session["user_id"] = row["id"]`, flash a success message, and `redirect(url_for("profile"))`
- `logout()` must call `session.pop("user_id", None)` (or `session.clear()`), flash a sign-out confirmation, and redirect to `url_for("landing")`. It must be safe to call when no user is logged in
- Use `abort(405)` if an unsupported HTTP method reaches `login()`
- `app.secret_key` is already set in `app.py` — do not change it as part of this step

## Definition of done

- [ ] `GET /login` renders the sign-in form without errors
- [ ] Submitting valid credentials for the seeded demo user (`demo@spendly.com` / `demo123`) sets `session["user_id"]` and redirects to `/profile`
- [ ] Submitting a wrong password re-renders the form with "Invalid email or password." and no session is set
- [ ] Submitting an unknown email re-renders the form with the same generic "Invalid email or password." message
- [ ] Submitting with an empty `email` or empty `password` re-renders the form with a validation error and no DB query is attempted with empty values
- [ ] Email matching is case-insensitive (`Demo@Spendly.com` logs in as `demo@spendly.com`)
- [ ] `GET /logout` clears `session["user_id"]`, flashes a sign-out message, and redirects to `/`
- [ ] Visiting `/logout` while not logged in does not raise — it still redirects to `/`
- [ ] When logged in, the navbar shows `Profile` + `Sign out`; when logged out it shows `Sign in` + `Get started`
- [ ] No plaintext password is stored, printed, or logged anywhere in the codebase
