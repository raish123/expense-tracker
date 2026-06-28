"""Tests for the login/logout feature (Spec 002).

All tests run against the throwaway ``seeded_db`` fixture (see conftest.py),
never the dev DB. The seeded users are:
  nitish@example.com / password123
  asha@example.com   / password456

The app is driven via ``httpx.AsyncClient`` + ``ASGITransport`` (Starlette's
``TestClient`` is incompatible with the installed httpx). Redirects are NOT
followed (httpx default) so the 303 + Set-Cookie on login/logout are assertable.
``pytest.ini`` sets ``asyncio_mode = auto``, so ``async def`` tests just run.
"""

import httpx

from app import _sign_session, app
from database.db import get_user_by_email

GENERIC_ERROR = "Invalid email or password."


def _client(**kwargs) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
        **kwargs,
    )


def _valid_cookie_for(email: str) -> dict[str, str]:
    """Mint a valid signed session cookie for a seeded user."""
    user = get_user_by_email(email)
    return {"spendly_session": _sign_session(user["id"])}


async def test_login_success_sets_cookie(seeded_db):
    async with _client() as client:
        resp = await client.post(
            "/login",
            data={"email": "nitish@example.com", "password": "password123"},
        )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/"
    assert "spendly_session" in resp.cookies


async def test_login_wrong_password(seeded_db):
    async with _client() as client:
        resp = await client.post(
            "/login",
            data={"email": "nitish@example.com", "password": "wrongpass"},
        )
    assert resp.status_code == 200
    assert GENERIC_ERROR in resp.text
    assert "spendly_session" not in resp.cookies


async def test_login_unknown_email(seeded_db):
    async with _client() as client:
        resp = await client.post(
            "/login",
            data={"email": "nobody@example.com", "password": "password123"},
        )
    assert resp.status_code == 200
    # Same generic message as the wrong-password case — no email enumeration.
    assert GENERIC_ERROR in resp.text
    assert "spendly_session" not in resp.cookies


async def test_login_email_case_insensitive(seeded_db):
    async with _client() as client:
        resp = await client.post(
            "/login",
            data={"email": "  NITISH@EXAMPLE.COM  ", "password": "password123"},
        )
    assert resp.status_code == 303
    assert "spendly_session" in resp.cookies


async def test_get_login_redirects_when_authenticated(seeded_db):
    async with _client(cookies=_valid_cookie_for("nitish@example.com")) as client:
        resp = await client.get("/login")
    assert resp.status_code == 303
    assert resp.headers["location"] == "/"


async def test_post_login_redirects_when_authenticated(seeded_db):
    async with _client(cookies=_valid_cookie_for("nitish@example.com")) as client:
        # Even with deliberately wrong creds, an authenticated user is not re-checked.
        resp = await client.post(
            "/login",
            data={"email": "nitish@example.com", "password": "wrongpass"},
        )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/"
    assert GENERIC_ERROR not in resp.text


async def test_logout_clears_cookie(seeded_db):
    async with _client(cookies=_valid_cookie_for("nitish@example.com")) as client:
        resp = await client.get("/logout")
    assert resp.status_code == 303
    assert resp.headers["location"] == "/"
    # Starlette signals deletion via an expired Set-Cookie header.
    assert "spendly_session" in resp.headers.get("set-cookie", "")


async def test_nav_shows_user_when_logged_in(seeded_db):
    async with _client(cookies=_valid_cookie_for("nitish@example.com")) as client:
        resp = await client.get("/")
    assert resp.status_code == 200
    assert "Nitish Kumar" in resp.text
    assert "Sign out" in resp.text


async def test_nav_anonymous(seeded_db):
    async with _client() as client:
        resp = await client.get("/")
    assert resp.status_code == 200
    assert "Sign in" in resp.text


async def test_tampered_cookie_is_anonymous(seeded_db):
    # Valid user id, bogus signature.
    async with _client(cookies={"spendly_session": "1.deadbeef"}) as client:
        resp = await client.get("/")
    assert resp.status_code == 200
    assert "Sign in" in resp.text
    assert "Sign out" not in resp.text


def test_get_user_by_email_helper(seeded_db):
    found = get_user_by_email("nitish@example.com")
    assert found is not None
    assert found["email"] == "nitish@example.com"
    assert get_user_by_email("nobody@example.com") is None
