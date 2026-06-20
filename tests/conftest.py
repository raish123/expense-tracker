"""Shared pytest fixtures.

Every test runs against a throwaway SQLite file (never the dev DB) by
monkeypatching ``database.db.DB_PATH`` to a path inside pytest's ``tmp_path``.
"""

import pytest

from database import db


@pytest.fixture
def empty_db(tmp_path, monkeypatch):
    """A freshly created, empty schema in a throwaway DB file."""
    test_db_path = tmp_path / "test_expense_tracker.db"
    monkeypatch.setattr(db, "DB_PATH", test_db_path)
    db.init_db()
    return test_db_path


@pytest.fixture
def seeded_db(empty_db):
    """The throwaway DB with sample data loaded."""
    db.seed_db()
    return empty_db
