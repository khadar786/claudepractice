import os
import random
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import get_db


CATEGORY_CONFIG = {
    "Food": {
        "weight": 30,
        "min": 50,
        "max": 800,
        "descriptions": [
            "Lunch at office canteen", "Dinner at Saravana Bhavan",
            "Swiggy biryani order", "Zomato dinner delivery",
            "Chai and samosa", "Breakfast at Udupi", "Masala dosa",
            "Pav bhaji at street stall", "Veg thali", "Paneer butter masala",
            "Cold coffee at CCD", "Chole bhature lunch", "Filter coffee",
            "Groceries from BigBasket", "Vegetables from local market",
        ],
    },
    "Transport": {
        "weight": 20,
        "min": 20,
        "max": 500,
        "descriptions": [
            "Ola cab to office", "Uber ride home", "Auto rickshaw fare",
            "Metro card recharge", "Petrol top-up", "Local bus ticket",
            "Rapido bike ride", "Train ticket", "Parking fee",
            "Toll charges", "Diesel for car",
        ],
    },
    "Bills": {
        "weight": 15,
        "min": 200,
        "max": 3000,
        "descriptions": [
            "Electricity bill", "Airtel mobile recharge",
            "Jio fiber broadband", "Water bill", "DTH recharge",
            "Gas cylinder refill", "Maintenance charges",
            "Netflix subscription", "Spotify premium", "Hotstar subscription",
        ],
    },
    "Health": {
        "weight": 5,
        "min": 100,
        "max": 2000,
        "descriptions": [
            "Apollo Pharmacy medicines", "Doctor consultation",
            "Dental checkup", "Lab tests at Dr Lal PathLabs",
            "Eye checkup", "Physiotherapy session", "Yoga class fees",
            "Gym membership", "Vitamin supplements",
        ],
    },
    "Entertainment": {
        "weight": 5,
        "min": 100,
        "max": 1500,
        "descriptions": [
            "PVR movie tickets", "BookMyShow event", "Concert tickets",
            "Bowling at Smaaash", "Weekend trip to Lonavala",
            "Amusement park entry", "Gaming zone", "Karaoke night",
        ],
    },
    "Shopping": {
        "weight": 15,
        "min": 200,
        "max": 5000,
        "descriptions": [
            "Myntra clothes order", "Amazon electronics",
            "Flipkart sale purchase", "Reliance Trends shirt",
            "Footwear from Bata", "Decathlon sportswear",
            "Lifestyle store haul", "DMart household items",
            "Lenskart sunglasses",
        ],
    },
    "Other": {
        "weight": 10,
        "min": 50,
        "max": 1000,
        "descriptions": [
            "Salon haircut", "Temple donation", "Gift for friend",
            "Stationery from local shop", "Book from Crossword",
            "Courier charges", "Photocopying", "Tip to delivery agent",
            "Diwali sweets", "Birthday gift",
        ],
    },
}


def parse_args(argv):
    if len(argv) < 4:
        return None
    try:
        return int(argv[1]), int(argv[2]), int(argv[3])
    except ValueError:
        return None


def usage():
    print(
        "Usage: /seed-expenses <user_id> <count> <months>\n"
        "Example: /seed-expenses 1 50 6"
    )


def user_exists(conn, user_id):
    row = conn.execute(
        "SELECT 1 FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    return row is not None


def pick_category():
    categories = list(CATEGORY_CONFIG.keys())
    weights = [CATEGORY_CONFIG[c]["weight"] for c in categories]
    return random.choices(categories, weights=weights, k=1)[0]


def random_date_within(months):
    today = datetime.now().date()
    days_back = months * 30
    delta = random.randint(0, days_back)
    return (today - timedelta(days=delta)).isoformat()


def generate_expense(user_id, months):
    category = pick_category()
    cfg = CATEGORY_CONFIG[category]
    amount = round(random.uniform(cfg["min"], cfg["max"]), 2)
    description = random.choice(cfg["descriptions"])
    date = random_date_within(months)
    return (user_id, amount, category, date, description)


def main():
    parsed = parse_args(sys.argv)
    if parsed is None:
        usage()
        sys.exit(1)

    user_id, count, months = parsed

    if count <= 0 or months <= 0:
        usage()
        sys.exit(1)

    conn = get_db()
    try:
        if not user_exists(conn, user_id):
            print(f"No user found with id {user_id}.")
            sys.exit(1)

        rows = [generate_expense(user_id, months) for _ in range(count)]

        try:
            with conn:
                conn.executemany(
                    "INSERT INTO expenses "
                    "(user_id, amount, category, date, description) "
                    "VALUES (?, ?, ?, ?, ?)",
                    rows,
                )
        except Exception as exc:
            print(f"Insert failed, rolled back: {exc}")
            sys.exit(1)

        dates = sorted(r[3] for r in rows)
        print(f"Inserted {len(rows)} expenses for user_id={user_id}")
        print(f"Date range: {dates[0]} to {dates[-1]}")
        print("Sample:")

        sample = conn.execute(
            "SELECT id, user_id, amount, category, date, description "
            "FROM expenses WHERE user_id = ? "
            "ORDER BY id DESC LIMIT 5",
            (user_id,),
        ).fetchall()
        for row in sample:
            print(
                f"  #{row['id']} | {row['date']} | {row['category']:13} | "
                f"Rs {row['amount']:>7.2f} | {row['description']}"
            )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
