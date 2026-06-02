# Spec: Date Filter for Profile Page

## Overview

Step 6 adds a date-range filter to the profile page so users can narrow all
three data sections — summary stats, transaction history, and category
breakdown — to a specific time window. Quick-select buttons cover the most
common periods (Last 7 days, Last 30 days, This month, Last month, All time),
and a custom date-range form lets users pick any start/end pair. The filter
state lives in the URL as query parameters so it is shareable and
back-button-friendly. No JavaScript is required; the form posts a GET request
to `/profile` with the selected dates.

## Depends on

- Step 1: Database setup (`expenses` table has a `date TEXT` column in
  `YYYY-MM-DD` format)
- Step 3: Login / Logout (`session["user_id"]` guards the route)
- Step 5: Backend connection (all four query helpers in `database/queries.py`
  are live and the profile route passes real data)

## Routes

- `GET /profile?period=<period>` — filter by named period; one of:
  `last_7`, `last_30`, `this_month`, `last_month`, `all` (default when absent)
- `GET /profile?start=YYYY-MM-DD&end=YYYY-MM-DD` — filter by custom date range
- When both `period` and `start`/`end` are present, `start`/`end` takes
  precedence.

No new routes are created — only the existing `GET /profile` route gains
optional query-parameter handling.

## Database changes

No database changes. The `expenses.date` column (`TEXT`, `YYYY-MM-DD`) is
already in place and indexed via normal SQLite rowscan for the small data
sizes expected in this teaching project.

## Templates

- **Modify**: `templates/profile.html`
  - Add a filter bar above the transaction history section containing:
    - Five quick-select period buttons (Last 7 days, Last 30 days, This month,
      Last month, All time), each rendered as an anchor tag pointing to
      `url_for('profile', period=<key>)`
    - A small custom-range form with two `<input type="date">` fields
      (`name="start"` and `name="end"`) and a submit button, posting via GET
      to `url_for('profile')`
  - The active period button must receive an `active` CSS class
  - The custom date inputs must be pre-filled with the current filter values
    when a custom range is active
  - All four data sections (user card, stats, transactions, categories) must
    already accept the filtered data — no structural template changes required
    beyond the filter bar itself

## Files to change

- `app.py`
  - Parse `period`, `start`, `end` from `request.args` in the `profile()` view
  - Resolve the query params to a `(start_date, end_date)` tuple using a
    helper `_resolve_date_range(period, start, end)` defined in `app.py`
  - Pass `start_date` and `end_date` to all three stat/transaction/category
    query calls
  - Pass `active_period`, `filter_start`, `filter_end` to the template so
    the filter bar can render correctly
- `database/queries.py`
  - Update `get_summary_stats(user_id, start_date=None, end_date=None)`
  - Update `get_recent_transactions(user_id, limit=10, start_date=None, end_date=None)`
  - Update `get_category_breakdown(user_id, start_date=None, end_date=None)`
  - When both `start_date` and `end_date` are provided, add
    `AND date BETWEEN ? AND ?` to each query's WHERE clause
  - When either is `None` (i.e. "All time"), no date filter is applied —
    existing behaviour is preserved

## Files to create

No new files.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL
- Passwords hashed with werkzeug (no auth changes in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- No JavaScript — filter is submitted via native HTML GET form or anchor links
- `_resolve_date_range` must live in `app.py`; do not add it to `database/queries.py`
- Period resolution uses `datetime.date.today()` — no third-party date libraries
- Invalid custom dates (unparseable strings, start > end) must fall back
  silently to "All time" rather than raising an exception or returning a 400
- The `active_period` template variable is a string matching one of the five
  period keys, or `"custom"` when a valid custom range is active, or `"all"`
  as the default
- `filter_start` and `filter_end` passed to the template are strings in
  `YYYY-MM-DD` format (for pre-filling date inputs) or empty strings when no
  custom range is set

## Definition of done

- [ ] Visiting `/profile` with no query params shows all transactions
  (same behaviour as Step 5)
- [ ] Clicking "This month" on the filter bar reloads the page and shows only
  transactions whose `date` falls within the current calendar month
- [ ] Summary stats (total spent, transaction count, top category) reflect
  the filtered date range, not the full history
- [ ] Category breakdown reflects the filtered date range
- [ ] Clicking "All time" restores the full unfiltered view
- [ ] Submitting a custom date range (e.g. 2026-05-01 → 2026-05-06) shows
  only the matching transactions and correct stats for that window
- [ ] The currently active period button is visually distinguished (has the
  `active` CSS class)
- [ ] A user with no expenses in the selected range sees ₹0.00 total, 0
  transactions, and an empty category breakdown — no errors
- [ ] Entering an invalid custom date (e.g. end before start) falls back to
  the full unfiltered view without a 500 error
