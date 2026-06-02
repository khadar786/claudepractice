import pytest

from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
)


# ================================================================== #
# Unit tests: get_user_by_id                                         #
# ================================================================== #

class TestGetUserById:
    def test_returns_correct_name_and_email(self, in_memory_conn):
        conn, uid = in_memory_conn
        result = get_user_by_id(uid)
        assert result["name"] == "Demo User"
        assert result["email"] == "demo@spendly.com"

    def test_returns_initials(self, in_memory_conn):
        conn, uid = in_memory_conn
        result = get_user_by_id(uid)
        assert result["initials"] == "DU"

    def test_returns_member_since_format(self, in_memory_conn):
        conn, uid = in_memory_conn
        result = get_user_by_id(uid)
        # conftest seeds created_at = "2026-01-15 10:00:00"
        assert result["member_since"] == "January 2026"

    def test_nonexistent_id_returns_none(self, in_memory_conn):
        conn, uid = in_memory_conn
        assert get_user_by_id(9999) is None


# ================================================================== #
# Unit tests: get_summary_stats                                      #
# ================================================================== #

class TestGetSummaryStats:
    def test_total_spent_with_expenses(self, in_memory_conn):
        conn, uid = in_memory_conn
        stats = get_summary_stats(uid)
        assert stats["total_spent"] == "₹301.18"

    def test_transaction_count_with_expenses(self, in_memory_conn):
        conn, uid = in_memory_conn
        stats = get_summary_stats(uid)
        assert stats["transaction_count"] == 8

    def test_top_category_with_expenses(self, in_memory_conn):
        conn, uid = in_memory_conn
        stats = get_summary_stats(uid)
        # Shopping (89.99) is the highest single-category total
        assert stats["top_category"] == "Shopping"

    def test_no_expenses_returns_zeros(self, in_memory_conn):
        conn, uid = in_memory_conn
        stats = get_summary_stats(9999)
        assert stats == {"total_spent": "₹0.00", "transaction_count": 0, "top_category": "—"}


# ================================================================== #
# Unit tests: get_recent_transactions                                #
# ================================================================== #

class TestGetRecentTransactions:
    def test_returns_list_of_dicts(self, in_memory_conn):
        conn, uid = in_memory_conn
        txns = get_recent_transactions(uid)
        assert isinstance(txns, list)
        assert len(txns) == 8

    def test_each_item_has_required_keys(self, in_memory_conn):
        conn, uid = in_memory_conn
        txns = get_recent_transactions(uid)
        for t in txns:
            assert "date" in t
            assert "description" in t
            assert "category" in t
            assert "amount" in t

    def test_ordered_newest_first(self, in_memory_conn):
        conn, uid = in_memory_conn
        txns = get_recent_transactions(uid)
        # Last seeded date is 2026-05-07 (Other / Misc cash expense)
        assert "7 May 2026" in txns[0]["date"]

    def test_amount_has_rupee_symbol(self, in_memory_conn):
        conn, uid = in_memory_conn
        txns = get_recent_transactions(uid)
        for t in txns:
            assert t["amount"].startswith("₹")

    def test_no_expenses_returns_empty_list(self, in_memory_conn):
        conn, uid = in_memory_conn
        assert get_recent_transactions(9999) == []

    def test_limit_is_respected(self, in_memory_conn):
        conn, uid = in_memory_conn
        txns = get_recent_transactions(uid, limit=3)
        assert len(txns) == 3


# ================================================================== #
# Unit tests: get_category_breakdown                                 #
# ================================================================== #

class TestGetCategoryBreakdown:
    def test_returns_all_seven_categories(self, in_memory_conn):
        conn, uid = in_memory_conn
        cats = get_category_breakdown(uid)
        assert len(cats) == 7

    def test_ordered_by_amount_descending(self, in_memory_conn):
        conn, uid = in_memory_conn
        cats = get_category_breakdown(uid)
        # Shopping (89.99) should be first
        assert cats[0]["name"] == "Shopping"

    def test_percent_values_sum_to_100(self, in_memory_conn):
        conn, uid = in_memory_conn
        cats = get_category_breakdown(uid)
        assert sum(c["percent"] for c in cats) == 100

    def test_percent_values_are_integers(self, in_memory_conn):
        conn, uid = in_memory_conn
        cats = get_category_breakdown(uid)
        for c in cats:
            assert isinstance(c["percent"], int)

    def test_amount_has_rupee_symbol(self, in_memory_conn):
        conn, uid = in_memory_conn
        cats = get_category_breakdown(uid)
        for c in cats:
            assert c["amount"].startswith("₹")

    def test_no_expenses_returns_empty_list(self, in_memory_conn):
        conn, uid = in_memory_conn
        assert get_category_breakdown(9999) == []


# ================================================================== #
# Route tests: GET /profile                                          #
# ================================================================== #

class TestProfileRoute:
    def test_unauthenticated_redirects_to_login(self, client):
        test_client, _ = client
        response = test_client.get("/profile")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_authenticated_returns_200(self, authenticated_client):
        test_client, _ = authenticated_client
        response = test_client.get("/profile")
        assert response.status_code == 200

    def test_shows_seed_user_name(self, authenticated_client):
        test_client, _ = authenticated_client
        response = test_client.get("/profile")
        assert b"Demo User" in response.data

    def test_shows_seed_user_email(self, authenticated_client):
        test_client, _ = authenticated_client
        response = test_client.get("/profile")
        assert b"demo@spendly.com" in response.data

    def test_contains_rupee_symbol(self, authenticated_client):
        test_client, _ = authenticated_client
        response = test_client.get("/profile")
        assert "₹".encode("utf-8") in response.data

    def test_total_spent_matches_seed_sum(self, authenticated_client):
        test_client, _ = authenticated_client
        response = test_client.get("/profile")
        assert "₹301.18".encode("utf-8") in response.data

    def test_top_category_is_shopping(self, authenticated_client):
        test_client, _ = authenticated_client
        response = test_client.get("/profile")
        assert b"Shopping" in response.data

    def test_category_breakdown_has_7_categories(self, authenticated_client):
        test_client, _ = authenticated_client
        response = test_client.get("/profile")
        html = response.data.decode("utf-8")
        assert html.count('class="category-row"') == 7
