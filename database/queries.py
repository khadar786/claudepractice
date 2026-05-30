from datetime import datetime

from database.db import get_db


def get_user_by_id(user_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    words = row["name"].split()
    initials = "".join(w[0].upper() for w in words if w)[:2]

    try:
        dt = datetime.strptime(row["created_at"][:19], "%Y-%m-%d %H:%M:%S")
        member_since = dt.strftime("%B %Y")
    except (ValueError, TypeError):
        member_since = "Unknown"

    return {
        "name": row["name"],
        "email": row["email"],
        "initials": initials,
        "member_since": member_since,
    }


def get_summary_stats(user_id):
    conn = get_db()
    try:
        totals_row = conn.execute(
            "SELECT SUM(amount) as total, COUNT(*) as cnt FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        top_row = conn.execute(
            """
            SELECT category, SUM(amount) as cat_total
            FROM expenses
            WHERE user_id = ?
            GROUP BY category
            ORDER BY cat_total DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
    finally:
        conn.close()

    total = totals_row["total"] if totals_row and totals_row["total"] is not None else 0.0
    count = totals_row["cnt"] if totals_row and totals_row["cnt"] is not None else 0
    top_category = top_row["category"] if top_row else "—"

    return {
        "total_spent": f"₹{total:,.2f}",
        "transaction_count": count,
        "top_category": top_category,
    }


def get_recent_transactions(user_id, limit=10):
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT date, description, category, amount
            FROM expenses
            WHERE user_id = ?
            ORDER BY date DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    finally:
        conn.close()

    result = []
    for row in rows:
        try:
            dt = datetime.strptime(row["date"], "%Y-%m-%d")
            fmt_date = f"{dt.day} {dt.strftime('%b %Y')}"
        except (ValueError, TypeError):
            fmt_date = row["date"]
        result.append({
            "date": fmt_date,
            "description": row["description"] or "",
            "category": row["category"],
            "amount": f"₹{row['amount']:,.2f}",
        })
    return result


def get_category_breakdown(user_id):
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT category, SUM(amount) as cat_total
            FROM expenses
            WHERE user_id = ?
            GROUP BY category
            ORDER BY cat_total DESC
            """,
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return []

    grand_total = sum(row["cat_total"] for row in rows)
    if grand_total == 0:
        return []

    raw = [(row["cat_total"] / grand_total) * 100 for row in rows]
    floored = [int(p) for p in raw]
    deficit = 100 - sum(floored)
    remainders = sorted(enumerate(raw), key=lambda x: x[1] - int(x[1]), reverse=True)
    for i in range(deficit):
        floored[remainders[i][0]] += 1

    return [
        {
            "name": rows[i]["category"],
            "amount": f"₹{rows[i]['cat_total']:,.2f}",
            "percent": floored[i],
        }
        for i in range(len(rows))
    ]
