# Spec: Database Setup (Step 1)

**Feature ID:** 001
**Status:** Implemented (2026-06-20)
**Owner:** raish123
**Target file(s):** `database/db.py` (primary), `requirements.txt` (unchanged), `app.py` (bootstrap only), `pytest.ini` + `tests/` (new)
**Created:** 2026-06-20

---

## 1. Summary

Implement the SQLite persistence layer for Spendly. This is the foundational
step every later feature (auth, profile, add/edit/delete expense) depends on.
The deliverable is a fully working `database/db.py` exposing three helpers —
`get_db()`, `init_db()`, and `seed_db()` — plus a documented bootstrap command.

Currently `database/db.py` is a stub (a docstring describing the expected
shape). No tables exist. This spec turns that stub into a working module.

---

## 2. Goals

- Provide a single, reusable SQLite connection helper with correct settings.
- Define the schema for `users` and `expenses` via idempotent DDL.
- Provide deterministic sample data for local development.
- Keep **all** SQL inside `database/db.py` — no inline SQL in routes (per CLAUDE.md).

## 3. Non-Goals

- No route handlers (auth, add expense, etc.) — those are later steps.
- No password-verification or session logic — only the storage of a hash.
- No migrations framework (Alembic etc.) — `CREATE TABLE IF NOT EXISTS` only.
- No ORM / SQLAlchemy — stdlib `sqlite3` only (tech constraint).
- No new pip packages.

---

## 4. User Stories

| ID | As a… | I want… | So that… |
|----|-------|---------|----------|
| US-1 | developer | to run one command to create the DB | I can start the app on a clean checkout |
| US-2 | developer | sample users/expenses seeded | I can see the UI populated without manual entry |
| US-3 | future route code | a connection with rows accessible by column name | I can write `row["amount"]` instead of `row[0]` |
| US-4 | future route code | foreign keys enforced | deleting a user cascades / orphan expenses are rejected |

---

## 5. Constraints (from CLAUDE.md)

- **SQLite only**, via stdlib `sqlite3`. No PostgreSQL, no ORM.
- DB file is `expense_tracker.db` (gitignored) at the project root.
- `get_db()` **must** run `PRAGMA foreign_keys = ON` on *every* connection —
  SQLite has FK enforcement off by default.
- Queries must be parameterized (`?` placeholders) — never f-strings in SQL.
- **No new packages.** requirements.txt has no `passlib`/`bcrypt`, so password
  hashing uses the stdlib `hashlib` (PBKDF2 via `hashlib.pbkdf2_hmac`).

---

## 6. Data Model

### 6.1 `users`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| `name` | TEXT | NOT NULL | from register form `name` |
| `email` | TEXT | NOT NULL UNIQUE | login identifier |
| `password_hash` | TEXT | NOT NULL | PBKDF2 hash, never plaintext |
| `created_at` | TEXT | NOT NULL DEFAULT (datetime('now')) | ISO timestamp |

### 6.2 `expenses`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| `user_id` | INTEGER | NOT NULL, FK → users(id) ON DELETE CASCADE | owner |
| `amount` | REAL | NOT NULL, CHECK(amount > 0) | stored in ₹ |
| `category` | TEXT | NOT NULL | e.g. Food, Travel, Bills |
| `description` | TEXT | | optional note |
| `date` | TEXT | NOT NULL | expense date, `YYYY-MM-DD` |
| `created_at` | TEXT | NOT NULL DEFAULT (datetime('now')) | row insert time |

**Relationship:** one user has many expenses. `ON DELETE CASCADE` removes a
user's expenses when the user is deleted (relies on FK pragma being ON).

### 6.3 ER sketch

```
users (1) ────< (many) expenses
  id  ◄─────────── user_id
```

---

## 7. Public API (functions in `database/db.py`)

### `get_db() -> sqlite3.Connection`
- Connects to `expense_tracker.db` (path resolved relative to project root, not CWD).
- Sets `conn.row_factory = sqlite3.Row` (US-3).
- Executes `PRAGMA foreign_keys = ON` (US-4).
- Returns the open connection (caller is responsible for closing/committing).

### `init_db() -> None`
- Opens a connection via `get_db()`.
- Runs `CREATE TABLE IF NOT EXISTS` for `users` then `expenses` (order matters: FK target first).
- Commits and closes. Safe to run repeatedly (idempotent).

### `seed_db() -> None`
- Inserts sample data **only if the tables are empty** (guard against duplicate seeds).
- At least 1–2 users and ~6–10 expenses across multiple categories/dates.
- Uses a stdlib helper (e.g. `hash_password()`) so seeded users can later log in.
- Parameterized inserts only. Commits and closes.

### Helper: `hash_password(password: str) -> str` (and matching `verify_password`)
- PBKDF2 (`hashlib.pbkdf2_hmac("sha256", ...)`) with a per-user random salt.
- Stored format e.g. `pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>`.
- `verify_password` is included now so Step 2 (login) can reuse it; storage shape is decided here.

---

## 8. Bootstrap

Document this exact command in CLAUDE.md (replaces the STUB marker) and run on first checkout:

```bash
python -c "from database.db import init_db, seed_db; init_db(); seed_db()"
```

Then `uvicorn app:app --reload --port 5001`.

**Implemented addition:** `app.py` also auto-bootstraps via a FastAPI `lifespan` handler —
`init_db()` runs on every startup (idempotent), and `seed_db()` runs **only when
`SPENDLY_ENV=dev`**, so production never auto-seeds. The manual command above remains the
documented alternative. (This stays within the spec's `app.py (bootstrap only)` scope.)

---

## 9. Acceptance Criteria

- [x] `from database.db import get_db, init_db, seed_db` imports without error.
- [x] `init_db()` creates `expense_tracker.db` with `users` and `expenses` tables.
- [x] Running `init_db()` twice does not raise and does not duplicate tables.
- [x] `get_db()` returns a connection where `PRAGMA foreign_keys` reports `1`.
- [x] Rows are accessible by column name (`row["email"]`).
- [x] `seed_db()` populates sample data; running it twice does not duplicate rows.
- [x] Inserting an expense with a non-existent `user_id` raises an `IntegrityError`.
- [x] Deleting a seeded user cascades to delete that user's expenses.
- [x] `amount <= 0` is rejected by the CHECK constraint.
- [x] No raw SQL exists outside `database/db.py`.

---

## 10. Edge Cases

| Case | Expected behavior |
|------|-------------------|
| DB file missing | `init_db()` creates it |
| `init_db()` called twice | No-op for existing tables (IF NOT EXISTS) |
| `seed_db()` called twice | Skips inserts (empty-table guard) |
| Duplicate email insert | `IntegrityError` (UNIQUE) |
| Orphan expense (`user_id` not in users) | `IntegrityError` (FK + pragma ON) |
| Connection opened without pragma | FK **not** enforced — bug; pragma must live in `get_db()` |
| Working dir is not project root | Path must resolve via `__file__`, not relative CWD |

---

## 11. Test Plan (`tests/test_db.py`)

Per CLAUDE.md testing section — use a **throwaway** DB (temp file or `:memory:`),
never the dev DB. Suggested fixtures via `conftest.py`.

1. `test_init_db_creates_tables` — query `sqlite_master`, assert both tables present.
2. `test_init_db_idempotent` — call twice, no error.
3. `test_foreign_keys_enabled` — `PRAGMA foreign_keys` returns `1`.
4. `test_row_factory` — fetched row supports `row["col"]` access.
5. `test_seed_populates` — counts > 0 after seed.
6. `test_seed_idempotent` — count unchanged after second seed.
7. `test_orphan_expense_rejected` — insert bad `user_id` raises `IntegrityError`.
8. `test_cascade_delete` — delete user removes their expenses.
9. `test_amount_check` — `amount = 0` raises `IntegrityError`.
10. `test_password_roundtrip` — `verify_password(pw, hash_password(pw))` is True.

---

## 12. Open Questions

- [x] Seed categories confirmed: Food, Travel, Bills, Shopping, Health, Other.
- [x] PBKDF2 iteration count: **100,000** (decided by owner; below the suggested ≥200k for faster test runs in this learning project — revisit before any production use).
- [ ] Should `get_db()` be a context manager / dependency for FastAPI `Depends`? **Still deferred to route steps** — implemented as a plain function returning an open connection for now.

---

## 13. Definition of Done

- [x] `database/db.py` implements all functions above; tests in §11 pass (`pytest` → 10 passed).
- [x] CLAUDE.md bootstrap STUB replaced with the §8 command (and testing STUB replaced).
- [x] `requirements.txt` unchanged (no new packages).
- [x] App starts on port 5001 against a seeded DB.
