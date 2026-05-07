# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project context

Spendly is a personal expense-tracker built as a teaching project. It is being implemented in numbered "Steps" (see prompts in `file.txt`); much of the application is intentionally stubbed out and gets filled in step by step. Routes that return placeholder strings like `"Add expense — coming in Step 7"` are not bugs — they are the next units of work.

## Commands

Activate the venv before running anything; the project assumes Python 3 with Flask 3.1.

```bash
# install deps
pip install -r requirements.txt

# run the dev server (debug on, port 5001 — NOT the Flask default 5000)
python app.py

# run tests (pytest + pytest-flask are pinned in requirements.txt; no tests exist yet)
pytest
pytest path/to/test_file.py::test_name   # single test
```

The SQLite database file is `expense_tracker.db` at the repo root (gitignored). It is created/seeded by helpers in `database/db.py` once those are implemented.

## Architecture

Single-file Flask app — `app.py` defines every route. There is no blueprint split, no application factory, and no ORM. The `database/db.py` module is the planned single source of truth for SQLite access and is expected to expose:

- `get_db()` — connection with `row_factory` set and foreign keys enabled
- `init_db()` — `CREATE TABLE IF NOT EXISTS …` for all tables
- `seed_db()` — sample data for development

When implementing or wiring these, keep them in `database/db.py` rather than introducing a new module.

Templates use Jinja inheritance from `templates/base.html`, which provides the navbar, footer (with Terms/Privacy links), and loads `static/css/style.css` plus `static/js/main.js` globally. Page-specific CSS lives alongside (e.g. `static/css/landing.css`) and is included via the `{% block head %}` block. New pages should `{% extends "base.html" %}` and use `url_for()` for links rather than hardcoded paths — existing footer links to `/terms` and `/privacy` are the exception, not the pattern to copy.

The brand name in user-facing copy is **Spendly**; the directory name `expense-tracker` is just the repo.

## Conventions

- **No JS frameworks.** Frontend is vanilla JS only (see the YouTube modal request in `file.txt`). Do not add jQuery, React, Alpine, etc.
- **Commit message style** — lowercase area prefix, colon, imperative summary: `landing: add youtube modal on see how it works click`. Match this for new commits.
- `file.txt` is a scratchpad of pending lesson prompts; treat it as instructions/history, not as runtime content.
