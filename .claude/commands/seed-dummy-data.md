---
description: Populate the SQLite database with dummy users and expenses for local development.
argument-hint: "[users=N] [expenses-per-user=M]  (optional, defaults to 5 users / 2 expenses each)"
allowed-tools: Read, Edit, Bash, Glob, Grep
---

# Seed dummy data into the Spendly database

Populate the local SQLite database (`expense_tracker.db`) with realistic dummy
data for the `users` and `expenses` tables so the app has something to render
during development.

**Arguments (optional):** `$ARGUMENTS`
- `users=N` — number of dummy users to create (default: **5**)
- `expenses-per-user=M` — number of expenses per user (default: **2**)

If no arguments are given, use the defaults.

---

## Schema reference (do not assume — confirm against `database/db.py`)

`database/db.py` is the **only** place SQL belongs (see `CLAUDE.md`). Read it
first to confirm the current schema before inserting anything.

**`users`**
| column | type | notes |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | do not set manually |
| `name` | TEXT NOT NULL | |
| `email` | TEXT NOT NULL **UNIQUE** | must be unique per user |
| `password_hash` | TEXT NOT NULL | **must** be produced by `hash_password()` — never a plaintext string |
| `created_at` | TEXT | has a default, can omit |

**`expenses`**
| column | type | notes |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | do not set manually |
| `user_id` | INTEGER NOT NULL → `users(id)` ON DELETE CASCADE | must reference a real user id |
| `amount` | REAL NOT NULL **CHECK(amount > 0)** | always > 0 |
| `category` | TEXT NOT NULL | one of: Food, Travel, Bills, Shopping, Health, Entertainment, Other |
| `description` | TEXT | short, human-readable |
| `date` | TEXT NOT NULL | `YYYY-MM-DD`, within the last ~60 days |
| `created_at` | TEXT | has a default, can omit |

---

## Steps

1. **Read `database/db.py`** to confirm the live schema and the available
   helpers (`get_db`, `init_db`, `seed_db`, `hash_password`). Do not assume
   columns — match what is actually there.

2. **Ensure the schema exists** by running `init_db()` before inserting.

3. **Generate the dummy data in Python**, respecting every constraint:
   - Unique, realistic Indian names + matching unique emails.
   - Hash every password with `hash_password("password123")` — **never** insert
     a plaintext password into `password_hash`.
   - Spread expenses across the allowed categories, vary amounts (₹50–₹5000,
     always > 0), and use dates within the last ~60 days from today.
   - Vary descriptions so the data looks real (e.g. "Groceries at BigBazaar",
     "Auto fare", "Mobile recharge").

4. **Insert via parameterized queries only** (`?` placeholders) on a connection
   from `get_db()` — never f-strings or string concatenation in SQL. Use
   `executemany()` for the bulk inserts and `commit()` once.

5. **Make it idempotent / safe to re-run**: before inserting a user, skip (or
   `INSERT OR IGNORE` on) emails that already exist so re-running this command
   does not crash on the UNIQUE constraint or pile up duplicate users.

6. **Run it.** Prefer a one-off command that reuses the existing helpers rather
   than adding throwaway code to the app, e.g.:
   ```bash
   python -c "from database.db import init_db; init_db()"
   python scripts/seed_dummy.py        # if you create a script
   ```
   If you write a reusable seeding script, put it under a `scripts/` directory
   (not inside `app.py`), keep all SQL inside helpers that live in
   `database/db.py`, and keep the script itself a thin caller.

7. **Verify**: query and print the row counts and a few sample rows so the user
   can see the result:
   ```bash
   python -c "from database.db import get_db; c=get_db(); print('users:', c.execute('SELECT COUNT(*) FROM users').fetchone()[0]); print('expenses:', c.execute('SELECT COUNT(*) FROM expenses').fetchone()[0]); [print(dict(r)) for r in c.execute('SELECT id,user_id,amount,category,description,date FROM expenses LIMIT 5')]; c.close()"
   ```

8. **Report** how many users and expenses were inserted, and how many existing
   rows were skipped.

---

## Constraints (from CLAUDE.md — must follow)

- **SQLite only** via stdlib `sqlite3`. No SQLAlchemy, no other DB.
- **All SQL lives in `database/db.py`** — never inline raw SQL in `app.py` or
  scattered scripts; call helpers instead.
- **Always parameterized queries** (`?`) — never f-strings / concatenation.
- **No new pip packages** — use the stdlib (`random`, `datetime`) for generation.
- **Never store plaintext passwords** — always go through `hash_password()`.
- This is a **dev-only** convenience — never run against a production database.
