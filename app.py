import sqlite3
from datetime import date, timedelta

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash

from database.db import create_user, get_user_by_email, init_db, seed_db
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
)

def _resolve_date_range(period, start, end):
    """Return (start_str, end_str, active_period) from URL query params."""
    today = date.today()
    today_str = today.isoformat()

    # Custom range takes precedence if both params are valid and start <= end
    if start and end:
        try:
            s = date.fromisoformat(start)
            e = date.fromisoformat(end)
            if s <= e:
                return start, end, "custom"
        except ValueError:
            pass

    # Named period
    if period == "last_7":
        return (today - timedelta(days=6)).isoformat(), today_str, "last_7"
    if period == "last_30":
        return (today - timedelta(days=29)).isoformat(), today_str, "last_30"
    if period == "this_month":
        return today.replace(day=1).isoformat(), today_str, "this_month"
    if period == "last_month":
        first_this = today.replace(day=1)
        last_prev = first_this - timedelta(days=1)
        first_prev = last_prev.replace(day=1)
        return first_prev.isoformat(), last_prev.isoformat(), "last_month"

    return None, None, "all"


app = Flask(__name__)
# Dev placeholder — replace with env-var lookup before any non-local deployment.
app.secret_key = "dev-secret-change-me"

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("register.html")

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not (name and email and password and confirm_password):
            flash("All fields are required.", "error")
            return render_template("register.html")

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("register.html")

        try:
            create_user(name, email, password)
        except sqlite3.IntegrityError:
            flash("Email already registered.", "error")
            return render_template("register.html")

        flash("Account created. Please sign in.", "success")
        return redirect(url_for("login"))

    abort(405)


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("login.html")

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not (email and password):
            flash("Invalid email or password.", "error")
            return render_template("login.html")

        user = get_user_by_email(email)
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "error")
            return render_template("login.html")

        session["user_id"] = user["id"]
        flash("Signed in.", "success")
        return redirect(url_for("profile"))

    abort(405)


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("Signed out.", "success")
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # ---- SECTION: USER (main agent) -------------------------------- #
    user = get_user_by_id(user_id)
    if user is None:
        session.pop("user_id", None)
        flash("Session expired. Please sign in again.", "error")
        return redirect(url_for("login"))
    # ---- END SECTION: USER ----------------------------------------- #

    period = request.args.get("period", "")
    start  = request.args.get("start", "")
    end    = request.args.get("end", "")
    start_date, end_date, active_period = _resolve_date_range(period, start, end)

    # ---- SECTION: STATS (Subagent 2 — do not edit above/below) ----- #
    stats = get_summary_stats(user_id, start_date, end_date)
    # ---- END SECTION: STATS ---------------------------------------- #

    # ---- SECTION: TRANSACTIONS (Subagent 1 — do not edit above/below) #
    transactions = get_recent_transactions(user_id, start_date=start_date, end_date=end_date)
    # ---- END SECTION: TRANSACTIONS ---------------------------------- #

    # ---- SECTION: CATEGORIES (Subagent 3 — do not edit above/below) - #
    categories = get_category_breakdown(user_id, start_date, end_date)
    # ---- END SECTION: CATEGORIES ------------------------------------ #

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
        active_period=active_period,
        filter_start=start_date or "",
        filter_end=end_date or "",
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
