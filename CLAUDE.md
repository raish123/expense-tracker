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
│   └── db.py           # SQLite helpers: get_db(), init_db(), seed_db()
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
  - <!-- STUB: document the exact bootstrap command once db.py is implemented, e.g. `python -c "from database.db import init_db, seed_db; init_db(); seed_db()"` -->
- `database/db.py` is currently empty — do not assume helpers exist until the step that implements them.

---

## Testing

Test deps are already in `requirements.txt`: `pytest`, `pytest-asyncio`, `httpx`. The `tests/` directory does not exist yet — create it when adding the first test.

- Test FastAPI routes with `httpx`/Starlette's `TestClient` (or `httpx.AsyncClient` for async tests with `pytest-asyncio`).
- Use a separate throwaway SQLite database (in-memory or temp file) per test run — never the dev DB.
- <!-- STUB: add `pyproject.toml`/`pytest.ini` config (asyncio_mode, testpaths) and a `conftest.py` fixture for the test DB + client once tests are introduced. -->

---

## Deployment

<!-- STUB: fill in once a target environment is chosen. Capture: -->
- Run production with a process manager / ASGI server, e.g. `uvicorn app:app --host 0.0.0.0 --port 5001` (add `gunicorn -k uvicorn.workers.UvicornWorker` for multi-worker) — disable `--reload`.
- Required environment variables (DB path, secret keys for sessions/auth once added) — document here.
- Database migration/init step on deploy.
- Static asset serving strategy (FastAPI serves `static/` directly today; front with nginx/CDN in production).

---

## Implemented vs stub routes

| Route | Status |
|---|---|
| `GET /` | Implemented — renders `landing.html` |
| `GET /register` | Implemented — renders `register.html` (POST handler pending) |
| `GET /login` | Implemented — renders `login.html` (POST handler pending) |
| `GET /terms` | Implemented — renders `terms.html` |
| `GET /privacy` | Implemented — renders `privacy.html` |
| `GET /logout` | Stub — Step 3 |
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
