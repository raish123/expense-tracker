"""SQLite persistence layer for Spendly.

All SQL for the application lives in this module (see CLAUDE.md). It exposes:
  get_db()         — a configured sqlite3 connection (row factory + FK pragma)
  init_db()        — idempotent schema creation
  seed_db()        — sample dev data (only when tables are empty)
  hash_password()  — PBKDF2 password hashing (stdlib only)
  verify_password()— constant-time hash verification
"""

import hashlib
import hmac
import os
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

# Resolve the DB file relative to the project root (this file's parent's parent),
# never the current working directory — so the path is stable regardless of where
# the app/tests are launched from.
DB_PATH = Path(__file__).resolve().parent.parent / "expense_tracker.db"

# PBKDF2 configuration (no third-party hashing libs — stdlib hashlib only).
_PBKDF2_ALGORITHM = "sha256"
_PBKDF2_ITERATIONS = 100_000
_PBKDF2_SALT_BYTES = 16


def get_db() -> sqlite3.Connection:
    """Return an open SQLite connection with row factory and FK enforcement.

    The caller is responsible for committing and closing the connection.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # SQLite has foreign-key enforcement OFF by default; it must be enabled on
    # every connection or ON DELETE CASCADE / orphan rejection silently no-op.
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create the schema if it does not already exist. Safe to run repeatedly."""
    conn = get_db()
    try:
        # users first — expenses references it via a foreign key.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT NOT NULL,
                email         TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at    TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                amount      REAL NOT NULL CHECK(amount > 0),
                category    TEXT NOT NULL,
                description TEXT,
                date        TEXT NOT NULL,
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def seed_db() -> None:
    """Insert sample dev data, but only if the users table is empty.

    The empty-table guard makes a second call a no-op (no duplicate rows).
    """
    conn = get_db()
    try:
        existing = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if existing:
            return

        users = [
            ("Nitish Kumar", "nitish@example.com", hash_password("password123")),
            ("Asha Verma", "asha@example.com", hash_password("password456")),
        ]
        conn.executemany(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            users,
        )

        # (user_id, amount, category, description, date)
        expenses = [
            (1, 450.0, "Food", "Lunch with team", "2026-06-01"),
            (1, 1200.0, "Travel", "Cab to airport", "2026-06-03"),
            (1, 2300.0, "Bills", "Electricity bill", "2026-06-05"),
            (1, 899.0, "Shopping", "Running shoes", "2026-06-08"),
            (1, 350.0, "Health", "Pharmacy", "2026-06-10"),
            (2, 150.0, "Food", "Coffee", "2026-06-02"),
            (2, 600.0, "Travel", "Train tickets", "2026-06-04"),
            (2, 1800.0, "Bills", "Internet bill", "2026-06-06"),
            (2, 250.0, "Other", "Stationery", "2026-06-09"),
        ]
        conn.executemany(
            """
            INSERT INTO expenses (user_id, amount, category, description, date)
            VALUES (?, ?, ?, ?, ?)
            """,
            expenses,
        )
        conn.commit()
    finally:
        conn.close()


# Pools used only by seed_dummy_data() to fabricate believable dev rows.
_DUMMY_FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ishaan",
    "Rohan", "Kabir", "Ananya", "Diya", "Saanvi", "Aadhya", "Anika", "Navya",
    "Myra", "Sara", "Aarohi", "Ira",
]
_DUMMY_LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Iyer", "Nair", "Reddy", "Patel", "Singh",
    "Mehta", "Joshi", "Kulkarni", "Bose", "Chopra", "Malhotra", "Desai",
]
_DUMMY_CATEGORY_DESCRIPTIONS = {
    "Food": ["Groceries at BigBazaar", "Lunch with team", "Dinner at restaurant", "Coffee", "Evening snacks"],
    "Travel": ["Auto fare", "Cab to airport", "Train tickets", "Petrol refill", "Metro card recharge"],
    "Bills": ["Electricity bill", "Internet bill", "Mobile recharge", "Water bill", "Gas cylinder"],
    "Shopping": ["Running shoes", "Cotton T-shirt", "Headphones", "Books", "Kitchenware"],
    "Health": ["Pharmacy", "Doctor consultation", "Gym membership", "Health checkup", "Vitamins"],
    "Entertainment": ["Movie tickets", "Netflix subscription", "Concert pass", "Bowling night", "Game purchase"],
    "Other": ["Stationery", "Birthday gift", "Charity donation", "Misc supplies", "Minor repairs"],
}


def seed_dummy_data(num_users: int = 5, expenses_per_user: int = 8) -> dict[str, int]:
    """Populate the DB with fabricated dev users + expenses. Idempotent & dev-only.

    Existing users (matched by email) are skipped; expenses are only generated
    for users actually inserted this run, so re-running never piles up rows.
    Returns a summary: users_inserted, users_skipped, expenses_inserted.
    """
    # Build (name, email) pairs deterministically by index so identities are
    # stable across runs — that is what makes INSERT OR IGNORE below idempotent
    # (re-running with the same count skips the same users instead of piling up).
    pairs: list[tuple[str, str]] = []
    for i in range(num_users):
        first = _DUMMY_FIRST_NAMES[i % len(_DUMMY_FIRST_NAMES)]
        last = _DUMMY_LAST_NAMES[(i // len(_DUMMY_FIRST_NAMES)) % len(_DUMMY_LAST_NAMES)]
        email = f"{first}.{last}.{i + 1}@example.com".lower()
        pairs.append((f"{first} {last}", email))

    categories = list(_DUMMY_CATEGORY_DESCRIPTIONS)
    today = date.today()

    users_inserted = 0
    users_skipped = 0
    expenses_inserted = 0

    conn = get_db()
    try:
        for name, email in pairs:
            cur = conn.execute(
                "INSERT OR IGNORE INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (name, email, hash_password("password123")),
            )
            if cur.rowcount == 0:
                users_skipped += 1
                continue
            users_inserted += 1
            user_id = cur.lastrowid

            rows = []
            for _ in range(expenses_per_user):
                category = random.choice(categories)
                description = random.choice(_DUMMY_CATEGORY_DESCRIPTIONS[category])
                amount = round(random.uniform(50, 5000), 2)
                day = (today - timedelta(days=random.randint(0, 60))).isoformat()
                rows.append((user_id, amount, category, description, day))
            conn.executemany(
                "INSERT INTO expenses (user_id, amount, category, description, date) "
                "VALUES (?, ?, ?, ?, ?)",
                rows,
            )
            expenses_inserted += len(rows)

        conn.commit()
    finally:
        conn.close()

    return {
        "users_inserted": users_inserted,
        "users_skipped": users_skipped,
        "expenses_inserted": expenses_inserted,
    }


def get_user_by_email(email: str) -> sqlite3.Row | None:
    """Return the user row matching ``email`` (incl. password_hash), or None.

    Used by the login handler to look up credentials. Parameterized.
    """
    conn = get_db()
    try:
        return conn.execute(
            "SELECT id, name, email, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> sqlite3.Row | None:
    """Return the user row matching ``user_id`` (no password_hash), or None.

    Used to rehydrate the logged-in user from the session cookie.
    """
    conn = get_db()
    try:
        return conn.execute(
            "SELECT id, name, email FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()


def hash_password(password: str) -> str:
    """Hash a password with PBKDF2 and a random per-user salt.

    Returns a self-describing string: ``pbkdf2_sha256$<iters>$<salt_hex>$<hash_hex>``.
    """
    salt = os.urandom(_PBKDF2_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        _PBKDF2_ALGORITHM, password.encode("utf-8"), salt, _PBKDF2_ITERATIONS
    )
    return f"pbkdf2_{_PBKDF2_ALGORITHM}${_PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Return True if ``password`` matches the stored PBKDF2 hash."""
    try:
        algorithm_tag, iterations_str, salt_hex, hash_hex = stored.split("$")
        algorithm = algorithm_tag.removeprefix("pbkdf2_")
        iterations = int(iterations_str)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except (ValueError, AttributeError):
        return False

    candidate = hashlib.pbkdf2_hmac(
        algorithm, password.encode("utf-8"), salt, iterations
    )
    # Constant-time comparison to avoid timing leaks.
    return hmac.compare_digest(candidate, expected)


def create_user(name: str, email: str, password: str) -> int:
    """Insert a new user with a hashed password; return the new row id.

    The password is hashed via ``hash_password()`` — plaintext is never stored.
    ``created_at`` is left to the column default. A duplicate email raises
    ``sqlite3.IntegrityError`` (UNIQUE constraint), which the caller handles.
    """
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, hash_password(password)),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_user_by_email(email: str) -> sqlite3.Row | None:
    """Return the user row for ``email``, or None if no such user exists."""
    conn = get_db()
    try:
        return conn.execute(
            "SELECT id, name, email, password_hash, created_at "
            "FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    finally:
        conn.close()
