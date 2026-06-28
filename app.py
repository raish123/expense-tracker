import hashlib
import hmac
import logging
import os
import secrets
import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database.db import (
    get_user_by_email,
    get_user_by_id,
    init_db,
    seed_db,
    verify_password,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema creation is idempotent and always safe to run on startup.
    init_db()
    # Sample data is dev-only — never auto-seed in production.
    if os.getenv("SPENDLY_ENV") == "dev":
        seed_db()
    yield


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")


# ------------------------------------------------------------------ #
# Session (stdlib HMAC-signed cookie — no third-party session libs)   #
# ------------------------------------------------------------------ #

SESSION_COOKIE = "spendly_session"

# HMAC secret for signing the session cookie. Must be set in production so
# sessions survive restarts; in dev we fall back to an ephemeral random secret.
SECRET_KEY = os.getenv("SPENDLY_SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_hex(32)
    logging.warning(
        "SPENDLY_SECRET_KEY not set — using an ephemeral dev secret; sessions "
        "will not survive a restart. Set it in production."
    )

# Single source of truth for where a logged-in user belongs after auth.
POST_LOGIN_REDIRECT = "/"  # TODO: point to dashboard once that step lands.


def _sign_session(user_id: int) -> str:
    """Return the signed cookie value ``<user_id>.<hex_signature>``."""
    sig = hmac.new(
        SECRET_KEY.encode(), str(user_id).encode(), hashlib.sha256
    ).hexdigest()
    return f"{user_id}.{sig}"


def _read_session(cookie: str | None) -> int | None:
    """Verify a signed cookie and return its user_id, or None if invalid."""
    if not cookie:
        return None
    try:
        user_id_str, sig = cookie.rsplit(".", 1)
        expected = hmac.new(
            SECRET_KEY.encode(), user_id_str.encode(), hashlib.sha256
        ).hexdigest()
        # Constant-time comparison; a tampered id/sig fails here.
        if not hmac.compare_digest(sig, expected):
            return None
        return int(user_id_str)
    except (ValueError, AttributeError):
        return None


def get_current_user(request: Request) -> sqlite3.Row | None:
    """Return the logged-in user row from the session cookie, or None.

    The single integration point later steps use to gate protected pages.
    """
    user_id = _read_session(request.cookies.get(SESSION_COOKIE))
    if user_id is None:
        return None
    return get_user_by_id(user_id)


def _inject_current_user(request: Request) -> dict:
    """Make ``current_user`` available to every template (e.g. base.html nav)."""
    return {"current_user": get_current_user(request)}


templates = Jinja2Templates(
    directory="templates", context_processors=[_inject_current_user]
)


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)
async def register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    # Already-authenticated users never see the form — send them to where a
    # logged-in user belongs.
    if get_current_user(request):
        return RedirectResponse(POST_LOGIN_REDIRECT, status_code=303)
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login", response_class=HTMLResponse)
async def login_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    # A logged-in user re-submitting the form is not re-authenticated.
    if get_current_user(request):
        return RedirectResponse(POST_LOGIN_REDIRECT, status_code=303)

    user = get_user_by_email(email.strip().lower())
    # Same generic message whether the email is unknown or the password is
    # wrong — never reveal which field failed.
    if user is None or not verify_password(password, user["password_hash"]):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid email or password."},
        )

    response = RedirectResponse(POST_LOGIN_REDIRECT, status_code=303)
    response.set_cookie(
        SESSION_COOKIE,
        _sign_session(user["id"]),
        httponly=True,
        samesite="lax",
        secure=os.getenv("SPENDLY_ENV") != "dev",
        path="/",
    )
    return response


@app.get("/terms", response_class=HTMLResponse)
async def terms(request: Request):
    return templates.TemplateResponse("terms.html", {"request": request})


@app.get("/privacy", response_class=HTMLResponse)
async def privacy(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request})


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.get("/logout")
async def logout():
    # Idempotent: clears the session cookie and returns to the landing page.
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@app.get("/profile")
async def profile():
    return {"message": "Profile page — coming in Step 4"}


@app.get("/expenses/add")
async def add_expense():
    return {"message": "Add expense — coming in Step 7"}


@app.get("/expenses/{id}/edit")
async def edit_expense(id: int):
    return {"message": f"Edit expense {id} — coming in Step 8"}


@app.get("/expenses/{id}/delete")
async def delete_expense(id: int):
    return {"message": f"Delete expense {id} — coming in Step 9"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=5001, reload=True)
