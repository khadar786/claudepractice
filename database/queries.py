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
    raise NotImplementedError  # Subagent 2


def get_recent_transactions(user_id, limit=10):
    raise NotImplementedError  # Subagent 1


def get_category_breakdown(user_id):
    raise NotImplementedError  # Subagent 3
