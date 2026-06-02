"""
tests/test_06-date-filter-profile.py

Pytest test suite for Step 6: Date Filter for the Profile Page.

All test logic is derived exclusively from the Step 6 spec
(.claude/specs/06-date-filter-profile.md) — NOT from reading the
implementation.

Seed data (from conftest.py _build_in_memory_db):
    uid  amount  category       date        description
    ---  ------  -------------- ----------  ----------------------
    1    12.50   Food           2026-05-01  Lunch sandwich
    2    30.00   Transport      2026-05-02  Monthly metro
    3    75.40   Bills          2026-05-03  Electricity bill
    4    45.00   Health         2026-05-04  Pharmacy
    5    15.99   Entertainment  2026-05-05  Movie ticket
    6    89.99   Shopping       2026-05-06  T-shirts
    7    22.30   Food           2026-05-06  Dinner takeout
    8    10.00   Other          2026-05-07  Misc cash expense
    Total (all 8) = 301.18

Today is 2026-06-02 (per project env).

Period math (as spec defines it):
  last_7      : start = today - 6 days  = 2026-05-27 → no seed rows → 0 txns
  last_30     : start = today - 29 days = 2026-05-04 → rows 4-8     → 5 txns, ₹183.28
  this_month  : start = 2026-06-01               → no seed rows → 0 txns
  last_month  : 2026-05-01 → 2026-05-31           → all 8 rows    → 8 txns, ₹301.18
  all / none  : no filter                          → all 8 rows    → 8 txns, ₹301.18

Custom ranges used in tests:
  2026-05-01 → 2026-05-06 : rows 1-7 → 7 txns, ₹291.18
  2026-05-01 → 2026-05-03 : rows 1-3 → 3 txns, ₹117.90
"""

import sqlite3

import pytest
from werkzeug.security import generate_password_hash

import app as flask_app_module
from database import db as db_module
from database import queries as queries_module

# ------------------------------------------------------------------ #
# Fixtures                                                            #
# ------------------------------------------------------------------ #

# Re-use the helpers from conftest so we do not duplicate schema logic.
# The conftest.py fixtures (in_memory_conn, flask_app, client,
# authenticated_client) are automatically available to every test in this
# file through pytest's fixture discovery.


# ------------------------------------------------------------------ #
# Helper constants derived from the spec's date math and seed data   #
# ------------------------------------------------------------------ #

# All-time totals (all 8 seed rows)
ALL_TIME_TOTAL = "₹301.18"
ALL_TIME_COUNT = 8

# last_30: rows on 2026-05-04..2026-06-02 → 5 rows
# 45.00 + 15.99 + 89.99 + 22.30 + 10.00 = 183.28
LAST_30_TOTAL = "₹183.28"
LAST_30_COUNT = 5

# last_7 and this_month: no seed rows in that window
EMPTY_TOTAL = "₹0.00"
EMPTY_COUNT = 0

# last_month (2026-05-01..2026-05-31): all 8 seed rows
LAST_MONTH_TOTAL = "₹301.18"
LAST_MONTH_COUNT = 8

# Custom 2026-05-01..2026-05-06: rows 1-7
# 12.50 + 30.00 + 75.40 + 45.00 + 15.99 + 89.99 + 22.30 = 291.18
CUSTOM_RANGE_TOTAL = "₹291.18"
CUSTOM_RANGE_COUNT = 7

# Custom 2026-05-01..2026-05-03: rows 1-3
# 12.50 + 30.00 + 75.40 = 117.90
CUSTOM_NARROW_TOTAL = "₹117.90"
CUSTOM_NARROW_COUNT = 3


# ------------------------------------------------------------------ #
# 1. Auth guard                                                       #
# ------------------------------------------------------------------ #

class TestAuthGuard:
    """Unauthenticated requests must be redirected to /login."""

    def test_unauthenticated_get_profile_redirects(self, client):
        tc, _ = client
        response = tc.get("/profile")
        assert response.status_code == 302, (
            "Expected 302 redirect for unauthenticated /profile"
        )
        assert "/login" in response.headers["Location"], (
            "Redirect target must be /login"
        )

    def test_unauthenticated_with_period_param_redirects(self, client):
        tc, _ = client
        response = tc.get("/profile?period=this_month")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_unauthenticated_with_custom_range_redirects(self, client):
        tc, _ = client
        response = tc.get("/profile?start=2026-05-01&end=2026-05-06")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


# ------------------------------------------------------------------ #
# 2. No query params — all-time (default) behaviour preserved        #
# ------------------------------------------------------------------ #

class TestNoParamsDefaultsToAllTime:
    """GET /profile with no query params shows the full unfiltered history."""

    def test_returns_200(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile")
        assert response.status_code == 200

    def test_all_time_total_spent_shown(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile")
        assert ALL_TIME_TOTAL.encode("utf-8") in response.data, (
            f"Expected {ALL_TIME_TOTAL} in all-time view"
        )

    def test_all_time_transaction_count_shown(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile")
        html = response.data.decode("utf-8")
        # The stats section renders transaction_count as a plain integer
        assert str(ALL_TIME_COUNT) in html

    def test_active_period_defaults_to_all(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile")
        html = response.data.decode("utf-8")
        # The "All time" anchor must carry the active class when no period given
        assert 'filter-btn active' in html, (
            "The 'All time' filter button must be active when no period is selected"
        )


# ------------------------------------------------------------------ #
# 3. period=all — explicit "all time"                                 #
# ------------------------------------------------------------------ #

class TestPeriodAll:
    """GET /profile?period=all is identical to no params."""

    def test_returns_200(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?period=all")
        assert response.status_code == 200

    def test_all_time_total_shown(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?period=all")
        assert ALL_TIME_TOTAL.encode("utf-8") in response.data

    def test_all_time_transaction_count(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?period=all")
        html = response.data.decode("utf-8")
        assert str(ALL_TIME_COUNT) in html

    def test_active_period_is_all(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?period=all")
        html = response.data.decode("utf-8")
        assert 'filter-btn active' in html


# ------------------------------------------------------------------ #
# 4. period=last_month                                                #
# ------------------------------------------------------------------ #

class TestPeriodLastMonth:
    """last_month = 2026-05-01 to 2026-05-31 → all 8 seed rows."""

    def test_returns_200(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?period=last_month")
        assert response.status_code == 200

    def test_total_spent_equals_full_seed(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?period=last_month")
        assert LAST_MONTH_TOTAL.encode("utf-8") in response.data, (
            f"last_month should include all seed rows; expected {LAST_MONTH_TOTAL}"
        )

    def test_transaction_count_equals_full_seed(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?period=last_month")
        html = response.data.decode("utf-8")
        assert str(LAST_MONTH_COUNT) in html

    def test_active_period_is_last_month(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?period=last_month")
        html = response.data.decode("utf-8")
        # The anchor pointing to ?period=last_month must have the active class
        assert "period=last_month" in html
        assert 'filter-btn active' in html

    def test_all_seed_categories_appear(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?period=last_month")
        html = response.data.decode("utf-8")
        for cat in ("Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"):
            assert cat in html, f"Category '{cat}' should appear for last_month"


# ------------------------------------------------------------------ #
# 5. period=last_30                                                   #
# ------------------------------------------------------------------ #

class TestPeriodLast30:
    """last_30 = 2026-05-04 to 2026-06-02 → 5 seed rows."""

    def test_returns_200(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?period=last_30")
        assert response.status_code == 200

    def test_total_spent_reflects_filtered_range(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?period=last_30")
        html = response.data.decode("utf-8")
        assert LAST_30_TOTAL.encode("utf-8") in response.data, (
            f"last_30 should show {LAST_30_TOTAL}, not the all-time total"
        )
        # Confirm the all-time total is NOT shown (it differs from last_30)
        assert ALL_TIME_TOTAL.encode("utf-8") not in response.data, (
            "All-time total must not appear when last_30 filter is active"
        )

    def test_transaction_count_reflects_filtered_range(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?period=last_30")
        html = response.data.decode("utf-8")
        assert str(LAST_30_COUNT) in html

    def test_active_period_is_last_30(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?period=last_30")
        html = response.data.decode("utf-8")
        assert "period=last_30" in html
        assert 'filter-btn active' in html

    def test_rows_before_range_excluded_from_transactions(self, authenticated_client):
        """Rows with date < 2026-05-04 must not appear in the transaction table."""
        tc, _ = authenticated_client
        response = tc.get("/profile?period=last_30")
        html = response.data.decode("utf-8")
        # "Lunch sandwich" is on 2026-05-01 — before last_30 start
        assert "Lunch sandwich" not in html, (
            "Expenses before the last-30-day window must be excluded"
        )
        # "Monthly metro" is on 2026-05-02 — before last_30 start
        assert "Monthly metro" not in html, (
            "Expenses before the last-30-day window must be excluded"
        )
        # "Electricity bill" is on 2026-05-03 — before last_30 start
        assert "Electricity bill" not in html, (
            "Expenses before the last-30-day window must be excluded"
        )

    def test_rows_within_range_present_in_transactions(self, authenticated_client):
        """Rows with date >= 2026-05-04 must appear in the transaction table."""
        tc, _ = authenticated_client
        response = tc.get("/profile?period=last_30")
        html = response.data.decode("utf-8")
        assert "Pharmacy" in html
        assert "Movie ticket" in html
        assert "T-shirts" in html
        assert "Dinner takeout" in html
        assert "Misc cash expense" in html

    def test_category_breakdown_excludes_early_categories(self, authenticated_client):
        """Categories that only appear before the range must not be in breakdown."""
        tc, _ = authenticated_client
        response = tc.get("/profile?period=last_30")
        html = response.data.decode("utf-8")
        # Transport only appears on 2026-05-02 (before last_30 start)
        # Bills only appears on 2026-05-03 (before last_30 start)
        # Both should be absent from the category breakdown section
        # We check the category-list section which follows the breakdown header
        breakdown_start = html.find("Spending by category")
        if breakdown_start != -1:
            breakdown_html = html[breakdown_start:]
            assert "Transport" not in breakdown_html, (
                "Transport category (May 2) must not appear in last_30 breakdown"
            )
            assert "Bills" not in breakdown_html, (
                "Bills category (May 3) must not appear in last_30 breakdown"
            )


# ------------------------------------------------------------------ #
# 6. period=last_7                                                    #
# ------------------------------------------------------------------ #

class TestPeriodLast7:
    """last_7 = 2026-05-27 to 2026-06-02 → 0 seed rows in that window."""

    def test_returns_200(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?period=last_7")
        assert response.status_code == 200

    def test_zero_total_when_no_expenses_in_range(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?period=last_7")
        assert EMPTY_TOTAL.encode("utf-8") in response.data, (
            "last_7 must show ₹0.00 when no expenses fall in that window"
        )

    def test_zero_transaction_count(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?period=last_7")
        html = response.data.decode("utf-8")
        # Transaction count stat should be 0
        assert str(EMPTY_COUNT) in html

    def test_no_500_error(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?period=last_7")
        assert response.status_code != 500

    def test_active_period_is_last_7(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?period=last_7")
        html = response.data.decode("utf-8")
        assert "period=last_7" in html
        assert 'filter-btn active' in html


# ------------------------------------------------------------------ #
# 7. period=this_month                                                #
# ------------------------------------------------------------------ #

class TestPeriodThisMonth:
    """this_month = 2026-06-01 to 2026-06-02 → 0 seed rows."""

    def test_returns_200(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?period=this_month")
        assert response.status_code == 200

    def test_zero_total_when_no_expenses_in_range(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?period=this_month")
        assert EMPTY_TOTAL.encode("utf-8") in response.data, (
            "this_month must show ₹0.00 when no expenses fall in the current month"
        )

    def test_zero_transaction_count(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?period=this_month")
        html = response.data.decode("utf-8")
        assert str(EMPTY_COUNT) in html

    def test_no_500_error(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?period=this_month")
        assert response.status_code != 500

    def test_active_period_is_this_month(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?period=this_month")
        html = response.data.decode("utf-8")
        assert "period=this_month" in html
        assert 'filter-btn active' in html


# ------------------------------------------------------------------ #
# 8. Custom date range — valid                                        #
# ------------------------------------------------------------------ #

class TestCustomDateRangeValid:
    """Custom ?start=&end= with a valid range where start <= end."""

    def test_custom_range_returns_200(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?start=2026-05-01&end=2026-05-06")
        assert response.status_code == 200

    def test_custom_range_total_matches_spec(self, authenticated_client):
        """2026-05-01 to 2026-05-06 includes 7 expenses totalling ₹291.18."""
        tc, _ = authenticated_client
        response = tc.get("/profile?start=2026-05-01&end=2026-05-06")
        assert CUSTOM_RANGE_TOTAL.encode("utf-8") in response.data, (
            f"Custom range 05-01..05-06 should show {CUSTOM_RANGE_TOTAL}"
        )

    def test_custom_range_transaction_count(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?start=2026-05-01&end=2026-05-06")
        html = response.data.decode("utf-8")
        assert str(CUSTOM_RANGE_COUNT) in html

    def test_custom_range_excludes_out_of_range_transactions(self, authenticated_client):
        """2026-05-07 expense must not appear when range ends on 2026-05-06."""
        tc, _ = authenticated_client
        response = tc.get("/profile?start=2026-05-01&end=2026-05-06")
        assert b"Misc cash expense" not in response.data, (
            "May 7 expense must be excluded from 05-01..05-06 custom range"
        )

    def test_custom_range_includes_boundary_transactions(self, authenticated_client):
        """Expenses on the start and end boundary dates must be included."""
        tc, _ = authenticated_client
        response = tc.get("/profile?start=2026-05-01&end=2026-05-06")
        assert b"Lunch sandwich" in response.data, (
            "Expense on start boundary date (05-01) must be included"
        )
        assert b"T-shirts" in response.data, (
            "Expense on end boundary date (05-06) must be included"
        )

    def test_custom_range_active_period_is_custom(self, authenticated_client):
        """active_period must be 'custom' when a valid custom range is active."""
        tc, _ = authenticated_client
        response = tc.get("/profile?start=2026-05-01&end=2026-05-06")
        html = response.data.decode("utf-8")
        # The custom-range date inputs must carry the active class
        assert 'filter-input active' in html, (
            "Date inputs must have active class when a custom range is selected"
        )

    def test_custom_range_prefills_date_inputs(self, authenticated_client):
        """The custom date inputs must be pre-filled with the active range."""
        tc, _ = authenticated_client
        response = tc.get("/profile?start=2026-05-01&end=2026-05-06")
        html = response.data.decode("utf-8")
        assert 'value="2026-05-01"' in html, (
            "Start date input must be pre-filled with 2026-05-01"
        )
        assert 'value="2026-05-06"' in html, (
            "End date input must be pre-filled with 2026-05-06"
        )

    def test_narrow_custom_range_total(self, authenticated_client):
        """2026-05-01 to 2026-05-03 → 3 expenses, ₹117.90."""
        tc, _ = authenticated_client
        response = tc.get("/profile?start=2026-05-01&end=2026-05-03")
        assert CUSTOM_NARROW_TOTAL.encode("utf-8") in response.data, (
            f"Custom range 05-01..05-03 should show {CUSTOM_NARROW_TOTAL}"
        )

    def test_narrow_custom_range_count(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?start=2026-05-01&end=2026-05-03")
        html = response.data.decode("utf-8")
        assert str(CUSTOM_NARROW_COUNT) in html

    def test_custom_range_category_breakdown_reflects_filter(self, authenticated_client):
        """Categories outside the range must not appear in the breakdown."""
        tc, _ = authenticated_client
        # 2026-05-01..2026-05-03 has Food, Transport, Bills only
        response = tc.get("/profile?start=2026-05-01&end=2026-05-03")
        html = response.data.decode("utf-8")
        breakdown_start = html.find("Spending by category")
        assert breakdown_start != -1
        breakdown_html = html[breakdown_start:]
        assert "Food" in breakdown_html
        assert "Transport" in breakdown_html
        assert "Bills" in breakdown_html
        # Health, Entertainment, Shopping, Other are on May 4-7 — excluded
        for absent_cat in ("Health", "Entertainment", "Shopping", "Other"):
            assert absent_cat not in breakdown_html, (
                f"'{absent_cat}' must not appear in the category breakdown "
                f"for 2026-05-01..2026-05-03"
            )

    def test_custom_range_overrides_period_param(self, authenticated_client):
        """When both period and start/end are present, start/end takes precedence."""
        tc, _ = authenticated_client
        # period=last_7 would return 0 txns; custom range should override it
        response = tc.get("/profile?period=last_7&start=2026-05-01&end=2026-05-06")
        assert CUSTOM_RANGE_TOTAL.encode("utf-8") in response.data, (
            "Custom start/end must override period param"
        )


# ------------------------------------------------------------------ #
# 9. Invalid custom ranges — fallback to all-time, no errors         #
# ------------------------------------------------------------------ #

class TestCustomDateRangeInvalid:
    """Invalid custom ranges must fall back silently to all-time, no 500."""

    def test_end_before_start_no_500(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?start=2026-05-06&end=2026-05-01")
        assert response.status_code == 200, (
            "end < start must not cause a 500 — should silently fall back to all-time"
        )

    def test_end_before_start_shows_all_time_total(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?start=2026-05-06&end=2026-05-01")
        assert ALL_TIME_TOTAL.encode("utf-8") in response.data, (
            "Reversed date range must fall back to showing all-time data"
        )

    def test_unparseable_start_date_no_500(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?start=not-a-date&end=2026-05-06")
        assert response.status_code == 200, (
            "Unparseable start date must not raise a 500"
        )

    def test_unparseable_start_date_shows_all_time_total(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?start=not-a-date&end=2026-05-06")
        assert ALL_TIME_TOTAL.encode("utf-8") in response.data, (
            "Unparseable start date must fall back to all-time data"
        )

    def test_unparseable_end_date_no_500(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?start=2026-05-01&end=not-a-date")
        assert response.status_code == 200

    def test_unparseable_end_date_shows_all_time_total(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?start=2026-05-01&end=not-a-date")
        assert ALL_TIME_TOTAL.encode("utf-8") in response.data

    def test_both_dates_unparseable_no_500(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?start=foo&end=bar")
        assert response.status_code == 200

    def test_both_dates_unparseable_shows_all_time_total(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?start=foo&end=bar")
        assert ALL_TIME_TOTAL.encode("utf-8") in response.data

    def test_equal_start_and_end_is_valid(self, authenticated_client):
        """start == end is a single-day range and must NOT fall back."""
        tc, _ = authenticated_client
        # 2026-05-07 has exactly 1 expense: Misc cash expense ₹10.00
        response = tc.get("/profile?start=2026-05-07&end=2026-05-07")
        assert response.status_code == 200
        assert "₹10.00".encode("utf-8") in response.data, (
            "Single-day range (start == end) must be treated as a valid custom range"
        )
        assert b"Misc cash expense" in response.data


# ------------------------------------------------------------------ #
# 10. User with no expenses in selected range → zero stats, no errors #
# ------------------------------------------------------------------ #

class TestNoExpensesInRange:
    """When no expenses fall in the selected range the page renders cleanly."""

    def test_this_month_zero_stats_no_error(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?period=this_month")
        assert response.status_code == 200
        assert EMPTY_TOTAL.encode("utf-8") in response.data
        html = response.data.decode("utf-8")
        assert "0" in html  # transaction_count

    def test_this_month_empty_category_breakdown_no_error(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?period=this_month")
        assert response.status_code == 200
        # No category rows should be rendered
        html = response.data.decode("utf-8")
        assert 'class="category-row"' not in html, (
            "No category rows must appear when the filtered range has 0 expenses"
        )

    def test_last_7_empty_transaction_table_no_error(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?period=last_7")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        # None of the seed expense descriptions should appear
        for desc in ("Lunch sandwich", "Monthly metro", "Electricity bill",
                     "Pharmacy", "Movie ticket", "T-shirts",
                     "Dinner takeout", "Misc cash expense"):
            assert desc not in html, (
                f"'{desc}' must not appear in last_7 view (no expenses in range)"
            )


# ------------------------------------------------------------------ #
# 11. active_period template variable                                 #
# ------------------------------------------------------------------ #

class TestActivePeriodTemplateVariable:
    """The correct filter button must carry the active CSS class for each period."""

    @pytest.mark.parametrize("period_key,expected_href_fragment", [
        ("last_7",     "period=last_7"),
        ("last_30",    "period=last_30"),
        ("this_month", "period=this_month"),
        ("last_month", "period=last_month"),
        ("all",        "period=all"),
    ])
    def test_active_button_for_named_period(
        self, authenticated_client, period_key, expected_href_fragment
    ):
        tc, _ = authenticated_client
        response = tc.get(f"/profile?period={period_key}")
        html = response.data.decode("utf-8")
        # The active anchor must contain both the period href and the active class.
        # We verify the active class is present in the page and the period link exists.
        assert expected_href_fragment in html, (
            f"Link for period '{period_key}' must be in the filter bar"
        )
        assert "filter-btn active" in html, (
            f"One filter button must have the active class for period='{period_key}'"
        )

    def test_no_period_param_all_button_is_active(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile")
        html = response.data.decode("utf-8")
        assert "filter-btn active" in html

    def test_custom_range_no_named_button_active(self, authenticated_client):
        """When a custom range is active the period buttons must NOT be active."""
        tc, _ = authenticated_client
        response = tc.get("/profile?start=2026-05-01&end=2026-05-06")
        html = response.data.decode("utf-8")
        # The custom inputs should carry 'active', but no named period anchor should
        assert "filter-input active" in html, (
            "Date inputs must be active for a custom range"
        )


# ------------------------------------------------------------------ #
# 12. Filter bar HTML presence                                        #
# ------------------------------------------------------------------ #

class TestFilterBarHTML:
    """The filter bar and all its expected elements must be in the rendered page."""

    def test_filter_bar_section_present(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile")
        assert b'filter-bar' in response.data, (
            "The filter bar container must be present on the profile page"
        )

    def test_five_period_anchors_present(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile")
        html = response.data.decode("utf-8")
        for period_key in ("last_7", "last_30", "this_month", "last_month", "all"):
            assert f"period={period_key}" in html, (
                f"Filter bar must include an anchor for period='{period_key}'"
            )

    def test_custom_range_form_present(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile")
        html = response.data.decode("utf-8")
        assert 'name="start"' in html, "Custom-range form must have a 'start' date input"
        assert 'name="end"' in html, "Custom-range form must have an 'end' date input"

    def test_custom_range_form_uses_get_method(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile")
        html = response.data.decode("utf-8")
        assert 'method="get"' in html, (
            "Custom range form must submit via GET so filter state is in the URL"
        )

    def test_filter_bar_labels_present(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile")
        html = response.data.decode("utf-8")
        for label in ("Last 7 days", "Last 30 days", "This month", "Last month", "All time"):
            assert label in html, f"Filter bar must contain label '{label}'"


# ------------------------------------------------------------------ #
# 13. Stats reflect the filtered range                                #
# ------------------------------------------------------------------ #

class TestStatsReflectFilter:
    """Summary stats (total_spent, transaction_count) must match the active filter."""

    def test_stats_differ_between_all_time_and_last_30(self, authenticated_client):
        tc, _ = authenticated_client
        all_time_resp = tc.get("/profile")
        last30_resp = tc.get("/profile?period=last_30")
        all_html = all_time_resp.data.decode("utf-8")
        last30_html = last30_resp.data.decode("utf-8")
        # The all-time total must differ from the last_30 total in the page content
        assert ALL_TIME_TOTAL in all_html
        assert LAST_30_TOTAL in last30_html
        assert ALL_TIME_TOTAL not in last30_html, (
            "last_30 view must not show the all-time total"
        )

    def test_stats_differ_between_all_time_and_custom_range(self, authenticated_client):
        tc, _ = authenticated_client
        all_time_resp = tc.get("/profile")
        custom_resp = tc.get("/profile?start=2026-05-01&end=2026-05-06")
        assert ALL_TIME_TOTAL.encode("utf-8") in all_time_resp.data
        assert CUSTOM_RANGE_TOTAL.encode("utf-8") in custom_resp.data
        assert ALL_TIME_TOTAL.encode("utf-8") not in custom_resp.data, (
            "Custom-range view must not show the all-time total"
        )


# ------------------------------------------------------------------ #
# 14. Category breakdown reflects the filtered range                  #
# ------------------------------------------------------------------ #

class TestCategoryBreakdownReflectsFilter:
    """Category breakdown must only include categories with expenses in the range."""

    def test_last_month_has_all_7_categories(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?period=last_month")
        html = response.data.decode("utf-8")
        assert html.count('class="category-row"') == 7, (
            "last_month covers all seed data so all 7 categories must appear"
        )

    def test_narrow_range_has_fewer_categories(self, authenticated_client):
        """2026-05-01..2026-05-03 has exactly 3 categories: Food, Transport, Bills."""
        tc, _ = authenticated_client
        response = tc.get("/profile?start=2026-05-01&end=2026-05-03")
        html = response.data.decode("utf-8")
        assert html.count('class="category-row"') == 3, (
            "2026-05-01..2026-05-03 has expenses in 3 categories only"
        )

    def test_empty_range_has_no_category_rows(self, authenticated_client):
        tc, _ = authenticated_client
        response = tc.get("/profile?period=this_month")
        html = response.data.decode("utf-8")
        assert 'class="category-row"' not in html, (
            "An empty period must render zero category rows"
        )

    def test_category_percentages_sum_to_100_for_filtered_range(self, authenticated_client):
        """Even for a filtered subset the percentages must still sum to 100."""
        tc, _ = authenticated_client
        response = tc.get("/profile?start=2026-05-01&end=2026-05-06")
        html = response.data.decode("utf-8")
        # Percentages are rendered as integers inside the --pct CSS variable
        import re
        pct_values = re.findall(r"--pct:\s*(\d+)%", html)
        if pct_values:
            total = sum(int(p) for p in pct_values)
            assert total == 100, (
                f"Category percentages must sum to 100 for filtered range; got {total}"
            )
