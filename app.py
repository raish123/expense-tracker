import os
import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database.db import create_user, get_user_by_email, init_db, seed_db


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
templates = Jinja2Templates(directory="templates")


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)
async def register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


def validate_registration(name: str, email: str, password: str) -> str | None:
    """Return a human-readable error for the first failing rule, else None.

    Inputs are expected already normalized (name stripped, email stripped +
    lowercased). The email check is intentionally lightweight (a single ``@``
    with non-empty local and domain parts) — no regex library, no new package.
    """
    if not name:
        return "Please enter your name."
    if len(name) > 100:
        return "Name is too long."
    local, _, domain = email.partition("@")
    if not email or email.count("@") != 1 or not local or not domain or len(email) > 254:
        return "Please enter a valid email address."
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if len(password) > 128:
        return "Password is too long."
    return None


@app.post("/register")
async def register_submit(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
):
    # Normalize before validating/storing so uniqueness is case-insensitive.
    name, email = name.strip(), email.strip().lower()
    error = validate_registration(name, email, password)
    if not error and get_user_by_email(email):
        error = "That email is already registered."
    if error:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": error},
            status_code=400,
        )
    try:
        create_user(name, email, password)
    except sqlite3.IntegrityError:
        # UNIQUE(email) is the source of truth — closes the check-then-insert race.
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "That email is already registered."},
            status_code=400,
        )
    # 303 See Other → Post/Redirect/Get so a refresh on /login does not re-submit.
    return RedirectResponse(
        f"{request.url_for('login')}?registered=1", status_code=303
    )


@app.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


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
    return {"message": "Logout — coming in Step 3"}


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
