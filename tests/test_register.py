"""Tests for the POST /register flow (Spec 002).

All tests run against a throwaway SQLite DB via the ``empty_db`` fixture
(see conftest.py), never the dev database.

Routes are driven with ``httpx.AsyncClient`` over an ``ASGITransport`` (async
tests run automatically under pytest-asyncio's ``asyncio_mode = auto``).
"""

import httpx
import pytest

from app import app
from database import db


def _count_users() -> int:
    conn = db.get_db()
    try:
        return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    finally:
        conn.close()


def _client() -> httpx.AsyncClient:
    # follow_redirects off so the 303 is observable; ASGITransport drives the app
    # in-process without a running server.
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
        follow_redirects=False,
    )


async def test_register_success_creates_user(empty_db):
    async with _client() as client:
        resp = await client.post(
            "/register",
            data={"name": "Nitish Kumar", "email": "Nitish@Example.com", "password": "password123"},
        )
    assert resp.status_code == 303
    assert resp.headers["location"].endswith("/login?registered=1")
    assert _count_users() == 1
    row = db.get_user_by_email("nitish@example.com")
    assert row is not None
    assert row["email"] == "nitish@example.com"  # stored lowercased + stripped


async def test_register_hashes_password(empty_db):
    async with _client() as client:
        await client.post(
            "/register",
            data={"name": "Asha", "email": "asha@example.com", "password": "supersecret"},
        )
    row = db.get_user_by_email("asha@example.com")
    assert row["password_hash"] != "supersecret"
    assert db.verify_password("supersecret", row["password_hash"]) is True


async def test_register_duplicate_email(empty_db):
    data = {"name": "Asha", "email": "asha@example.com", "password": "password123"}
    async with _client() as client:
        await client.post("/register", data=data)
        resp = await client.post("/register", data=data)
    assert resp.status_code == 400
    assert "already registered" in resp.text
    assert _count_users() == 1


async def test_register_duplicate_email_case_insensitive(empty_db):
    async with _client() as client:
        await client.post(
            "/register",
            data={"name": "Asha", "email": "A@x.com", "password": "password123"},
        )
        resp = await client.post(
            "/register",
            data={"name": "Asha Two", "email": "a@x.com", "password": "password123"},
        )
    assert resp.status_code == 400
    assert "already registered" in resp.text
    assert _count_users() == 1


async def test_register_empty_name(empty_db):
    async with _client() as client:
        resp = await client.post(
            "/register",
            data={"name": "   ", "email": "a@x.com", "password": "password123"},
        )
    assert resp.status_code == 400
    assert "Please enter your name." in resp.text
    assert _count_users() == 0


async def test_register_invalid_email(empty_db):
    async with _client() as client:
        resp = await client.post(
            "/register",
            data={"name": "Asha", "email": "not-an-email", "password": "password123"},
        )
    assert resp.status_code == 400
    assert "valid email address" in resp.text
    assert _count_users() == 0


async def test_register_short_password(empty_db):
    async with _client() as client:
        resp = await client.post(
            "/register",
            data={"name": "Asha", "email": "a@x.com", "password": "short12"},  # 7 chars
        )
    assert resp.status_code == 400
    assert "at least 8 characters" in resp.text
    assert _count_users() == 0


async def test_register_get_still_renders(empty_db):
    async with _client() as client:
        resp = await client.get("/register")
    assert resp.status_code == 200
    assert 'action="/register"' in resp.text


def test_create_user_helper(empty_db):
    new_id = db.create_user("Asha", "asha@example.com", "password123")
    assert isinstance(new_id, int)
    row = db.get_user_by_email("asha@example.com")
    assert row is not None
    assert row["id"] == new_id
    assert row["name"] == "Asha"


def test_get_user_by_email_missing(empty_db):
    assert db.get_user_by_email("nobody@example.com") is None
