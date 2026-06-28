# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Spendly is a lightweight personal expense tracker built with **FastAPI**, **Jinja2** server-rendered templates, and **SQLite**. Currency is displayed in Indian Rupees (₹).

This is a step-by-step learning project: the database layer and most routes are currently stubs (placeholder responses / "coming in Step N" markers) awaiting implementation. Before building a feature, check whether the target file already has a placeholder describing the expected shape, and follow it.

---

## Architecture
```
spendly/
├── app.py              # FastAPI app + all routes — single file, no routers yet
├── database/
│   ├── __init__.py     # package marker
│   └── db.py           # SQLite helpers: get_db(), init_db(), seed_db(), seed_dummy_data()
├── scripts/            # dev-only one-off scripts (thin callers of db.py helpers)
│   └── seed_dummy.py   # CLI wrapper for seed_dummy_data() — see /seed-dummy-data
├── session/            # historical session/migration notes (reference only)
├── templates/
│   ├── base.html       # Shared layout — all templates must extend this
│   └── *.html          # One template per page
├── static/
│   ├── css/
│   │   ├── style.css       # Global styles / design system
│   │   └── landing.css     # Landing-page-only styles
│   └── js/
│       └── main.js         # Vanilla JS only
├── tests/              # pytest suite (placeholder — not created yet)
└── requirements.txt
```

**Where things belong:**
- New routes → `app.py` (single file for now; introduce `APIRouter` modules only when it grows large)
- DB logic → `database/db.py` only, never inline raw SQL in route functions
- New pages → new `.html` file extending `base.html`
- Page-specific styles → new `.css` file, not inline `<style>` tags

---

## Code style

- Python: PEP 8, snake_case for all variables and functions; type-annotate route params and return types
- Page routes that render templates are `async def` and take `request: Request`, returning `TemplateResponse("x.html", {"request": request, ...})` with `response_class=HTMLResponse` on the decorator
- Path params use FastAPI syntax with type annotations: `@app.get("/expenses/{id}/edit")` + `async def edit(id: int)` — never Flask's `<int:id>`
- Form bodies use `Form(...)` params (requires `python-multipart`, already in requirements)
- Templates: Jinja2 with `url_for()` for every internal link — never hardcode URLs. Static assets use Starlette's `path=` kwarg: `url_for('static', path='css/style.css')` — **not** Flask's `filename=`
- Route `url_for()` resolves by the Python function name (e.g. `url_for('landing')`)
- DB queries: always parameterized (`?` placeholders) — never f-strings/string concatenation in SQL
- Error handling: raise `HTTPException(status_code=..., detail=...)` — not bare string returns or Flask's `abort()`

---

## Tech constraints

- **FastAPI only** — no Flask, no Django, no other web frameworks
- **SQLite only** via the stdlib `sqlite3` module — no PostgreSQL, no SQLAlchemy ORM, no external DB
- **Server-rendered Jinja2 + vanilla JS only** — no React, no jQuery, no npm/build step
- **No new pip packages** — work within `requirements.txt` as-is unless explicitly told otherwise
- Python 3.10+ assumed — f-strings and `match` statements are fine

---

## Subagent policy
- Use a builtin Explore subagent for codebase exploration before implementing any new feature
- Use a subagent to verify test results after any implementation
- When asked to plan, delegate codebase research to a subagent before presenting the plan
- Use the builtin Plan subagent in plan mode

---

## Commands
```bash
# Setup
python -m venv venv
venv\Scripts\activate              # Windows; macOS/Linux: source venv/bin/activate
pip install -r requirements.txt

# Run dev server (port 5001, auto-reload)
uvicorn app:app --reload --port 5001
# Equivalent: python app.py  (app.py has a uvicorn.run() __main__ block)

# Interactive API docs (free with FastAPI)
#   http://localhost:5001/docs    (Swagger UI)
#   http://localhost:5001/redoc

# Tests (suite not yet created — see Testing section)
pytest                             # run all
pytest tests/test_foo.py           # one file
pytest -k "test_name"              # one test by name
pytest -s                          # show stdout
```

---

## Development

- Dev server runs on **port 5001** (not the common 8000/5000) with `--reload` for hot-reloading on file changes.
- The SQLite database file is gitignored (`expense_tracker.db`). On first run, initialize it before serving:
  - `init_db()` creates tables (`CREATE TABLE IF NOT EXISTS`); `seed_db()` inserts sample dev data — both live in `database/db.py`.
  - Bootstrap command (manual, creates + seeds the DB):
    ```bash
    python -c "from database.db import init_db, seed_db; init_db(); seed_db()"
    ```
  - Alternatively, the app auto-bootstraps on startup: `init_db()` always runs via the FastAPI `lifespan` handler in `app.py`, and `seed_db()` runs only when `SPENDLY_ENV=dev`.
- `database/db.py` exposes `get_db()`, `init_db()`, `seed_db()`, `seed_dummy_data()`, `hash_password()`, and `verify_password()`.
  - `seed_dummy_data(num_users=5, expenses_per_user=8)` populates fabricated dev users + expenses; idempotent (skips existing users by email). Run it via the `/seed-dummy-data` command or `python scripts/seed_dummy.py [users=N] [expenses-per-user=M]`.

---

## Testing

Test deps are already in `requirements.txt`: `pytest`, `pytest-asyncio`, `httpx`. The `tests/` directory holds the suite; run with `pytest`.

- Test FastAPI routes with `httpx`/Starlette's `TestClient` (or `httpx.AsyncClient` for async tests with `pytest-asyncio`).
- Use a separate throwaway SQLite database (in-memory or temp file) per test run — never the dev DB.
- Config lives in `pytest.ini` (`asyncio_mode = auto`, `testpaths = tests`). `tests/conftest.py` provides `empty_db` / `seeded_db` fixtures that monkeypatch `database.db.DB_PATH` to a `tmp_path` file, so tests never touch the dev DB.

---

## Deployment

<!-- STUB: fill in once a target environment is chosen. Capture: -->
- Run production with a process manager / ASGI server, e.g. `uvicorn app:app --host 0.0.0.0 --port 5001` (add `gunicorn -k uvicorn.workers.UvicornWorker` for multi-worker) — disable `--reload`.
- Required environment variables:
  - `SPENDLY_ENV` — set to `dev` to auto-seed sample data on startup. **Leave unset in production** (schema is still created via `init_db()`, but no sample data is inserted). Also relaxes the session cookie `secure` flag for local `http://localhost` (set in dev → cookie sent over plain HTTP).
  - `SPENDLY_SECRET_KEY` — HMAC secret used to sign the `spendly_session` cookie. **Must be set in production**; if unset, the app generates an ephemeral secret at startup and logs a warning, so all sessions are invalidated on every restart. Rotating the key also invalidates existing sessions.
  - (DB path — document here once introduced.)
- Database migration/init step on deploy.
- Static asset serving strategy (FastAPI serves `static/` directly today; front with nginx/CDN in production).

---

## Implemented vs stub routes

| Route | Status |
|---|---|
| `GET /` | Implemented — renders `landing.html` |
| `GET /register` | Implemented — renders `register.html` (POST handler pending) |
| `GET /login` | Implemented — renders `login.html`; redirects to `/` if already authenticated |
| `POST /login` | Implemented — verifies credentials, sets signed session cookie, redirects to `/` |
| `GET /terms` | Implemented — renders `terms.html` |
| `GET /privacy` | Implemented — renders `privacy.html` |
| `GET /logout` | Implemented — clears session cookie, redirects to `/` |
| `GET /profile` | Stub — Step 4 |
| `GET /expenses/add` | Stub — Step 7 |
| `GET /expenses/{id}/edit` | Stub — Step 8 |
| `GET /expenses/{id}/delete` | Stub — Step 9 |

**Do not implement a stub route unless the active task explicitly targets that step.**

---

## Warnings and things to avoid

- **Never use raw JSON/string returns for stub routes** once a step is implemented — render a template (or return the proper response model)
- **Never hardcode URLs** in templates — always use `url_for()` (with `path=` for static assets)
- **Never put DB logic in route functions** — it belongs in `database/db.py`
- **Never install new packages** mid-feature without flagging it — keep `requirements.txt` in sync
- **Never use JS frameworks or a build step** — the frontend is intentionally vanilla
- **`database/db.py` is currently empty** — do not assume helpers exist until the step that implements them
- **FK enforcement is manual** — SQLite foreign keys are off by default; `get_db()` must run `PRAGMA foreign_keys = ON` on every connection
- The app runs on **port 5001** — don't change this
