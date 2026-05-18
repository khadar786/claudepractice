Plan: Step 03 — Login and Logout

Context

Spendly currently has working registration (Step 02) that creates users with werkzeug-hashed passwords,
plus stubbed GET /login and GET /logout routes in app.py. Step 03 turns these into real authentication:
POST /login verifies credentials against the users table and stores the user's id in flask.session; GET
/logout clears the session. The navbar in base.html is also made session-aware so logged-in users see
Profile/Sign out instead of Sign in/Get started. This unblocks Step 04 (Profile) and all expense routes
that need to know which user is acting.

Source of truth for behaviour: .claude/specs/03-login-and-logout.md.

Files to modify

- app.py — upgrade login() (GET + POST) and logout()
- database/db.py — add get_user_by_email(email) helper
- templates/login.html — change form action to url_for('login')
- templates/base.html — session-aware navbar links

Implementation steps

1.  database/db.py — add get_user_by_email

Mirror the style of the existing create_user helper (db.py:86–96):

- Open a connection via get_db()
- Run a parameterised SELECT id, name, email, password_hash FROM users WHERE email = ?, with
  email.lower() as the bound parameter (matches the casing create_user writes — db.py:92)
- fetchone() and return the sqlite3.Row (or None)
- Close the connection in a finally block

No new imports needed.

2.  app.py — upgrade login()

Currently a GET-only stub (app.py:68–70). Restructure to mirror the existing register() route
(app.py:33–65):

- @app.route("/login", methods=["GET", "POST"])
- On GET: render_template("login.html") (unchanged)
- On POST:
  a. Read email (stripped + lower-cased) and password (raw) from request.form
  b. If either is empty → flash("Invalid email or password.", "error") and re-render — do not query the
  DB with empty values
  c. Call get_user_by_email(email)
  d. If row is None or check_password_hash(row["password_hash"], password) is False → flash the same
  generic "Invalid email or password." error and re-render (prevents user-enumeration — spec rule)
  e. On success: session["user_id"] = row["id"], flash("Signed in.", "success"),
  redirect(url_for("profile"))
- Fall-through abort(405) (matches the register route pattern)

Imports to add to the existing from flask import (...) block: session. Add from werkzeug.security import
check_password_hash.

3.  app.py — upgrade logout()

Currently returns a placeholder string (app.py:87–89). Replace with:

- session.pop("user_id", None) (safe when no user is logged in — spec definition-of-done item)
- flash("Signed out.", "success")
- return redirect(url_for("landing"))

No method restriction change; GET is fine for this teaching project.

4.  templates/login.html — fix form action

Line 20 currently has action="/login" hardcoded. Change to action="{{ url_for('login') }}". Everything
else (inputs, flash block, links) already matches the spec.

5.  templates/base.html — session-aware navbar

The current nav block (base.html:21–25) always shows Sign in + Get started. Replace with a Jinja {% if
 session.user_id %} / {% else %} split:

- Logged in: link to url_for('profile') ("Profile") and url_for('logout') ("Sign out", styled with
  nav-cta)
- Logged out: existing url_for('login') ("Sign in") and url_for('register') ("Get started", nav-cta)

session is available in templates by default — no new template globals.

Reused code / patterns

- get_db() and parameterised query style — database/db.py:13–17, database/db.py:90–93
- Flash + re-render pattern for failed form validation — app.py:44–60 (the register() route)
- flash / redirect / url_for already imported in app.py:3–11
- werkzeug.security.generate_password_hash already in use in db.py:4 — we add the matching
  check_password_hash in app.py

Verification

Run python app.py (port 5001) and verify each item against the spec's Definition of Done:

1.  GET /login renders without error
2.  Sign in as demo@spendly.com / demo123 (seeded by seed_db()) → redirects to /profile (still a stub
    returning "Profile page — coming in Step 4", which is the expected next-step placeholder). Inspect the
    browser cookie or add a temporary print to confirm session["user_id"] is set
3.  Submit wrong password → re-renders with "Invalid email or password."; cookie still anonymous
4.  Submit unknown email → same generic error message
5.  Submit empty email or empty password → validation error, no DB hit
6.  Sign in as Demo@Spendly.com (mixed-case) → succeeds (case-insensitive)
7.  Hit /logout while logged in → redirected to /, navbar reverts to Sign in / Get started
8.  Hit /logout while logged out → still redirects to / without raising
9.  Grep the repo for the literal string password to confirm no plaintext is logged or stored

Out of scope (deliberately)

- No @login_required decorator yet — Step 04 (Profile) will introduce it
- No "remember me", password reset, or rate limiting — not in the spec
- No CSS changes — login template visuals are already in place
