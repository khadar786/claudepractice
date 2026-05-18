Implementation Plan — Step 2: Registration

Below is a step-by-step plan derived from .claude/specs/02-registration.md. No code is written; this is what to do,
in what order, and why.

---

1. Add the create_user() helper in database/db.py

Location: new function placed after seed_db() so existing functions stay at the top.

Responsibilities:

- Accept name, email, password as arguments.
- Hash the password with werkzeug.security.generate_password_hash (already imported).
- Open a connection via get_db(), insert into users(name, email, password_hash) using a parameterised INSERT, commit
  (use a with conn: block), and return cursor.lastrowid.
- Let sqlite3.IntegrityError from the UNIQUE-email constraint propagate to the caller — the route is responsible for
  translating it into a user-facing error.
- Wrap the connection lifecycle in try/finally to close cleanly, matching the pattern already used in init_db() /
  seed_db().

Why this shape: the spec explicitly says the helper raises IntegrityError on duplicate email, so error mapping stays
in the route layer (separation of concerns). Keeping all SQL inside database/db.py honors the rule in CLAUDE.md
that db.py is the single source of truth for SQLite access.

---

2. Update templates/register.html

Current state (from earlier read):

- Already extends base.html.
- Already has <form method="POST" action="/register">.
- Already has name, email, password inputs with name= attributes.
- Already has an {% if error %} error block.
- Already has a Sign in link via url_for('login').

Changes:

1. Replace action="/register" with action="{{ url_for('register') }}" to satisfy the "no hardcoded URLs" rule.
2. Lowercase method="post" per the spec wording (functionally identical, but matches the spec).
3. Add a new Confirm password field below the existing password input — same form-group markup, type="password",
   name="confirm_password", id="confirm_password", required.
4. Replace the {% if error %} block with a flashed-messages block that iterates
   get_flashed_messages(with_categories=true) and renders each one. Use auth-error for the error category and a new
   auth-success style (or simply reuse auth-error with a different category class) for the success category — re-check
   static/css/style.css before adding any new CSS to confirm whether auth-success already exists; if not, add a CSS
   rule using existing CSS variables (no new hex codes).
5. Do not repopulate the form fields from prior input — the spec uses flash messaging and re-rendering only; it does
   not require sticky form values. Keep the existing visual design otherwise.

---

3. Update app.py

3a. Imports

Add to the existing from flask import … line: request, redirect, url_for, flash, abort. Add from database.db import
create_user (and keep the existing init_db, seed_db import).

Also import sqlite3 so the route can catch sqlite3.IntegrityError explicitly. (Or import it lazily inside the
handler — top-of-file is cleaner.)

3b. Set app.secret_key

Immediately after app = Flask(**name**), set app.secret_key = "dev-secret-change-me" (or similar hardcoded dev
string per spec). Add a single short comment noting this is a dev placeholder — it is the kind of non-obvious "why"
that earns a comment.

3c. Replace the existing /register route

The current route only handles GET. Rewrite it to accept both methods: @app.route("/register", methods=["GET",
"POST"]).

Handler logic, top to bottom:

1. If request.method == "GET" → return render_template("register.html").
2. If request.method == "POST":
   - Read name, email, password, confirm_password from request.form, applying .strip() to all four (treating

whitespace-only input as empty per the spec's "non-empty" rule). - Validation 1 — non-empty fields: if any of the four is empty, flash("All fields are required.", "error") and
return render_template("register.html"). - Validation 2 — password match: if password != confirm_password, flash("Passwords do not match.", "error") and
re-render. - Insert attempt: call create_user(name, email, password) inside a try block. - On sqlite3.IntegrityError: flash("Email already registered.", "error") and re-render. - Success path: flash("Account created — please sign in.", "success") and return redirect(url_for("login")). 3. If somehow another method reaches the route (shouldn't happen given the methods= whitelist, but the spec asks for
it), call abort(405). Practically this is unreachable — Flask returns 405 itself — but include it to honor the spec
wording.

Important: never echo the plaintext password back to the template, never include it in flash messages, never log it.

---

4. Optional but recommended verification touch-ups

These are not new files or features; they are checks to perform manually while wrapping up:

- Inspect static/css/style.css for an existing .auth-success (or equivalent positive-state) class. If absent, add
  one using existing CSS variables — no new hex codes — so the success flash on the login page renders nicely. (Note:
  success message is flashed before the redirect, so it will appear on /login, not /register. The login template will
  need to render flashed messages too — confirm this before declaring DoD complete.)
- Confirm templates/login.html already renders flashed messages. If it does not, that becomes a small follow-up edit
  in this same step so the success flash from registration actually shows up on the login screen. Read login.html
  during implementation to decide.

---

5. Manual verification against the Definition of Done

After the changes, run python app.py and confirm each DoD checkbox by interacting with the browser:

1. GET /register renders.
2. Valid submission creates a row (check via sqlite3 expense_tracker.db "SELECT id, name, email,
   substr(password_hash,1,12) FROM users ORDER BY id DESC LIMIT 1") and lands on /login with the success flash.
3. Mismatched passwords → form re-renders with the error flash, no DB write (re-check row count before vs after).
4. Duplicate email (e.g. demo@spendly.com from seed_db) → form re-renders with "Email already registered."
5. Any empty field → form re-renders with the validation flash.
6. The stored value in password_hash begins with pbkdf2: or scrypt: (i.e. hashed).
7. Re-submitting the same valid form twice creates only one row (the second is rejected as duplicate).

---

Order of operations (suggested)

1. database/db.py — add create_user().
2. app.py — imports, secret_key, new POST handler.
3. templates/register.html — confirm_password input + flash block + url_for action.
4. Skim templates/login.html; add a flash-rendering block there if missing.
5. Manual walkthrough of the DoD checklist.

---

Risks / things to watch

- Case sensitivity on email: the modified spec did not retain the case-insensitive lookup requirement from the
  earlier draft. The UNIQUE constraint in SQLite is case-sensitive by default, so Foo@Bar.com and foo@bar.com would
  both succeed unless we normalise. Flag this to the user before implementing — the spec is silent, but it's a
  real-world footgun. Default plan: do nothing and follow the spec literally; mention the gap.
- app.secret_key as a hardcoded dev string — fine for this teaching project per the spec, but note it should be
  replaced with os.environ lookup before any production deployment.
- Flash on /login — the success message is flashed before a redirect, so it surfaces on the login page. If
  login.html doesn't render flashes, the success message silently disappears.
