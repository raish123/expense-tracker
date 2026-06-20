"""Tests for the SQLite persistence layer (spec 001 §11)."""

import sqlite3

import pytest

from database import db
from database.db import (
    get_db,
    hash_password,
    init_db,
    seed_db,
    verify_password,
)


def _table_names(conn):
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {row["name"] for row in rows}


def test_init_db_creates_tables(empty_db):
    conn = get_db()
    try:
        names = _table_names(conn)
    finally:
        conn.close()
    assert {"users", "expenses"} <= names


def test_init_db_idempotent(empty_db):
    # Already initialised by the fixture — a second call must not raise.
    init_db()
    init_db()


def test_foreign_keys_enabled(empty_db):
    conn = get_db()
    try:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        conn.close()


def test_row_factory(seeded_db):
    conn = get_db()
    try:
        row = conn.execute("SELECT email FROM users LIMIT 1").fetchone()
    finally:
        conn.close()
    assert row["email"]  # accessible by column name, not just row[0]


def test_seed_populates(seeded_db):
    conn = get_db()
    try:
        user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        expense_count = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
    finally:
        conn.close()
    assert user_count > 0
    assert expense_count > 0


def test_seed_idempotent(seeded_db):
    conn = get_db()
    try:
        before = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    finally:
        conn.close()

    seed_db()  # second seed should be a no-op

    conn = get_db()
    try:
        after = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    finally:
        conn.close()
    assert before == after


def test_orphan_expense_rejected(empty_db):
    conn = get_db()
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO expenses (user_id, amount, category, date) "
                "VALUES (?, ?, ?, ?)",
                (9999, 100.0, "Food", "2026-06-20"),
            )
            conn.commit()
    finally:
        conn.close()


def test_cascade_delete(seeded_db):
    conn = get_db()
    try:
        user_id = conn.execute("SELECT id FROM users LIMIT 1").fetchone()["id"]
        had_expenses = conn.execute(
            "SELECT COUNT(*) FROM expenses WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
        assert had_expenses > 0

        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()

        remaining = conn.execute(
            "SELECT COUNT(*) FROM expenses WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
    finally:
        conn.close()
    assert remaining == 0


def test_amount_check(seeded_db):
    conn = get_db()
    try:
        user_id = conn.execute("SELECT id FROM users LIMIT 1").fetchone()["id"]
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO expenses (user_id, amount, category, date) "
                "VALUES (?, ?, ?, ?)",
                (user_id, 0, "Food", "2026-06-20"),
            )
            conn.commit()
    finally:
        conn.close()


def test_password_roundtrip():
    pw = "s3cret-pa$$word"
    stored = hash_password(pw)
    assert verify_password(pw, stored) is True
    assert verify_password("wrong", stored) is False
