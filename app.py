import sqlite3

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

    # ---- SECTION: STATS (Subagent 2 — do not edit above/below) ----- #
    stats = {"total_spent": "₹12,480", "transaction_count": 24, "top_category": "Food"}
    # ---- END SECTION: STATS ---------------------------------------- #

    # ---- SECTION: TRANSACTIONS (Subagent 1 — do not edit above/below) #
    transactions = [
        {"date": "25 May 2026", "description": "Swiggy dinner",    "category": "Food",          "amount": "₹650"},
        {"date": "22 May 2026", "description": "Electricity bill", "category": "Bills",         "amount": "₹1,240"},
        {"date": "20 May 2026", "description": "Metro pass",       "category": "Transport",     "amount": "₹300"},
        {"date": "18 May 2026", "description": "Pharmacy",         "category": "Health",        "amount": "₹480"},
        {"date": "15 May 2026", "description": "Movie tickets",    "category": "Entertainment", "amount": "₹600"},
    ]
    # ---- END SECTION: TRANSACTIONS ---------------------------------- #

    # ---- SECTION: CATEGORIES (Subagent 3 — do not edit above/below) - #
    categories = [
        {"name": "Food",          "amount": "₹4,200", "percent": 34},
        {"name": "Bills",         "amount": "₹2,800", "percent": 22},
        {"name": "Transport",     "amount": "₹1,900", "percent": 15},
        {"name": "Health",        "amount": "₹1,580", "percent": 13},
        {"name": "Entertainment", "amount": "₹1,200", "percent": 10},
    ]
    # ---- END SECTION: CATEGORIES ------------------------------------ #

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
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
