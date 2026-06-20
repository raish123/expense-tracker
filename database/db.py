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
import sqlite3
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
