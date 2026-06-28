# Spec: Login and Logout Feature (002)

**Feature ID:** 002
**Status:** Draft (2026-06-28)
**Owner:** raish123
**Target file(s):** `app.py` (POST `/login` handler + `/logout` handler + session helpers + `get_current_user`), `templates/base.html` (nav reflects auth state), `templates/login.html` (reuse existing form/error block), CLAUDE.md (route table + env var docs), `tests/test_auth.py` (new)
**Created:** 2026-06-28

---

## 1. Summary

Add real authentication to Spendly: a working `POST /login` handler that verifies
a user's credentials against the `users` table, and a `GET /logout` handler that
ends the session. This maps to **Step 2 (login)** and **Step 3 (logout)** in the
CLAUDE.md route table.

Today `GET /login` renders `login.html` but the form `POST`s to `/login` with no
handler (404), and `GET /logout` is a JSON stub (`"Logout — coming in Step 3"`).
The `users` table, `hash_password()`, and `verify_password()` already exist from
Spec 001 — this feature **consumes** them; it does not add storage or hashing.

The missing piece is **session state**. Spendly has no session mechanism yet, and
`requirements.txt` does **not** include `itsdangerous`, so Starlette's
`SessionMiddleware` is unavailable without a new package (forbidden by CLAUDE.md).
This spec therefore introduces a small **stdlib-HMAC-signed cookie**, reusing the
exact `hmac` + `hashlib` pattern already established in `database/db.py`.

---

## 2. Goals

- Authenticate a user from the existing `login.html` form against `users`.
- Establish a tamper-resistant session identifying the logged-in user.
- Clear that session on logout and return the user to a public page.
- Reflect auth state in the shared navbar (`base.html`): show the user / a
  "Sign out" link when logged in; "Sign in" / "Get started" when not.
- Stay within all CLAUDE.md constraints — **no new pip packages**.

## 3. Non-Goals

- **Registration / `POST /register`** — the register POST handler is a separate
  pending item; this spec only assumes users exist (via `seed_db()` or a later
  register step).
- **Profile page (`/profile`, Step 4)** and **expense pages (Steps 7–9)** — out
  of scope; their stubs stay untouched.
- **Route protection / `@login_required`-style guards** — there are no protected
  pages yet (dashboard/profile come later). The session is *established and read*
  here; enforcing it on protected routes is deferred to the step that adds them.
- **Password reset, "remember me", CSRF tokens, rate limiting** — noted under
  Security/Open Questions, not built here.
- **Switching to `SessionMiddleware`** — recorded as a flagged alternative (§11),
  not adopted, because it requires the `itsdangerous` package.

---

## 4. User Stories

| ID | As a… | I want… | So that… |
|----|-------|---------|----------|
| US-1 | returning user | to submit my email + password and be signed in | I can access my account |
| US-2 | user with wrong credentials | a clear, generic error on the same page | I know it failed without leaking which field was wrong |
| US-3 | signed-in user | a "Sign out" link that ends my session | I can log out on a shared device |
| US-4 | any visitor | the navbar to reflect whether I'm signed in | the UI matches my actual state |
| US-5 | future route code | a `get_current_user(request)` helper | protected pages (later steps) can read the logged-in user |

---

## 5. Constraints (from CLAUDE.md)

- **FastAPI + Jinja2 + SQLite only.** No Flask, no JS frameworks, no build step.
- **No new pip packages.** `requirements.txt` has no `itsdangerous`, so
  `starlette.middleware.sessions.SessionMiddleware` is **off the table** unless
  the owner explicitly approves adding the dependency (see §11).
- **All SQL in `database/db.py`.** The login lookup must go through a new helper
  in `db.py` (e.g. `get_user_by_email()`) — no inline SQL in `app.py`.
- **Parameterized queries only** (`?` placeholders).
- Page routes are `async def`, take `request: Request`, and render via
  `templates.TemplateResponse(..., {"request": request, ...})` with
  `response_class=HTMLResponse` on the decorator.
- Form bodies use `Form(...)` params (`python-multipart` is already installed).
- Templates use `url_for()` for every internal link (`path=` for static).
- Errors via `HTTPException` where appropriate — **but** a bad login is a normal
  user outcome, so it re-renders `login.html` with an `error` (not a 4xx page).
- App runs on **port 5001**.

---

## 6. Session Design (stdlib-signed cookie)

No third-party session library is available, so the session is a **signed
cookie** carrying only the user id, signed with HMAC-SHA256 using a server secret.
This mirrors the stdlib approach already in `db.py` (`hmac.compare_digest`,
`hashlib`).

### 6.1 Cookie shape

| Property | Value |
|----------|-------|
| Name | `spendly_session` |
| Value | `<user_id>.<hex_signature>` where `signature = HMAC_SHA256(secret, str(user_id))` |
| `httponly` | `True` (not readable by JS) |
| `samesite` | `"lax"` |
| `secure` | `True` in production (behind HTTPS); may be `False` for local `http://localhost` |
| `max_age` | session-length is acceptable for now; a fixed `max_age` (e.g. 7 days) is an Open Question |
| `path` | `/` |

### 6.2 Secret key

- Read from env var **`SPENDLY_SECRET_KEY`** at startup.
- If unset, fall back to a generated dev secret (`secrets.token_hex()`), and log a
  warning that sessions won't survive a restart — acceptable for `SPENDLY_ENV=dev`,
  **must be set in production**. Document alongside `SPENDLY_ENV` in CLAUDE.md.

### 6.3 Helpers (in `app.py`, stdlib only)

These are auth/transport concerns, not DB logic, so they live in `app.py`
(single-file convention) — *not* in `db.py`:

```
_sign_session(user_id: int) -> str          # returns "<id>.<sig>"
_read_session(cookie: str | None) -> int|None   # verify sig (hmac.compare_digest); return user_id or None
get_current_user(request: Request) -> sqlite3.Row | None
    # reads request.cookies["spendly_session"], verifies, then
    # calls database.db.get_user_by_email/get_user_by_id to load the row
```

`get_current_user` is the single integration point later steps use to gate
protected pages.

---

## 7. Data / DB Changes

**No schema change.** One new read helper in `database/db.py` (keeps SQL out of
routes, per CLAUDE.md):

### `get_user_by_email(email: str) -> sqlite3.Row | None`
- `SELECT id, name, email, password_hash FROM users WHERE email = ?`
- Returns the row or `None`. Parameterized.

### `get_user_by_id(user_id: int) -> sqlite3.Row | None`
- `SELECT id, name, email FROM users WHERE id = ?`
- Used by `get_current_user` to rehydrate the user from the session cookie.
- Returns the row or `None`.

Both open via `get_db()`, fetch, and close the connection.

---

## 8. Route Specification

### 8.1 `POST /login` (NEW — replaces the missing handler)

```python
@app.post("/login", response_class=HTMLResponse)
async def login_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    ...
```

**Flow:**
1. **Already authenticated?** If `get_current_user(request)` is not `None`, skip
   credential checks entirely and 303-redirect to the post-login target (`/`) — a
   logged-in user re-submitting the form is not re-authenticated and never sees an
   error. (See §8.4.)
2. Look up `get_user_by_email(email.strip().lower())`.
3. If no user **or** `verify_password(password, user["password_hash"])` is `False`
   → re-render `login.html` with a **generic** `error` (US-2) and HTTP `200`.
   (Same message for both cases — never reveal whether the email exists.)
4. On success → create a `RedirectResponse(url_for-style target, status_code=303)`
   and call `response.set_cookie(...)` with the signed session (§6.1).
5. Redirect target: **`/` (landing)** for now — there is no dashboard/profile page
   yet. Add a `// TODO` note that once the dashboard step lands, this redirects
   there instead.

> Note: `GET /login` does **not** stay fully as-is — see §8.4 for the
> already-authenticated guard. The existing `templates/login.html` already has
> `method="POST" action="/login"` and an
> `{% if error %}<div class="auth-error">{{ error }}</div>{% endif %}` block —
> **reuse both unchanged.**

### 8.4 Already-authenticated guard on `GET`/`POST /login`

A user who already holds a valid `spendly_session` should never see or use the
login form again — both the form page and a re-submitted POST short-circuit to the
post-login target.

- **`GET /login`** — at the top of the handler, if `get_current_user(request)` is
  not `None`, return `RedirectResponse("/", status_code=303)` instead of rendering
  `login.html`. (This adds a guard to the *existing* `GET /login` route; it is no
  longer a pure render.)
- **`POST /login`** — step 1 of the §8.1 flow performs the same check before
  touching credentials.

Rationale: prevents a confusing "log in while already logged in" flow, avoids
needless password verification, and keeps a single source of truth for "where a
logged-in user belongs" (the post-login target). The redirect is the same target
used after a successful login, so the post-login destination is defined in one
place.

### 8.2 `GET /logout` (was Step 3 stub)

```python
@app.get("/logout")
async def logout():
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("spendly_session", path="/")
    return response
```

- Replaces the JSON stub. Clears the cookie and redirects to landing.
- Idempotent — logging out when already logged out just redirects.

### 8.3 Route table after this feature

| Route | Before | After |
|-------|--------|-------|
| `GET /login` | Implemented (form) | **Updated** — redirects to `/` if already authenticated (§8.4), else renders form |
| `POST /login` | **Missing (404)** | **Implemented** (redirects to `/` if already authenticated) |
| `GET /logout` | Stub — Step 3 | **Implemented** |

CLAUDE.md's "Implemented vs stub routes" table must be updated to match.

---

## 9. Template / UX Notes

### 9.1 `templates/base.html` — nav reflects auth state

The navbar currently always shows "Sign in" / "Get started". Make it conditional
on a `current_user` value:

```jinja
<div class="nav-links">
  {% if current_user %}
    <span class="nav-user">{{ current_user.name }}</span>
    <a href="{{ url_for('logout') }}" class="nav-cta">Sign out</a>
  {% else %}
    <a href="{{ url_for('login') }}">Sign in</a>
    <a href="{{ url_for('register') }}" class="nav-cta">Get started</a>
  {% endif %}
</div>
```

- `current_user` must be available to **every** template that extends `base.html`.
  Pass it from each rendering route's context, **or** inject it globally so routes
  don't each have to thread it (e.g. a small middleware/`templates.env.globals`
  callable, or a context helper). Decide one approach and apply consistently —
  see Open Questions §16.
- `login.html` itself needs no change beyond what already exists.

### 9.2 Error rendering

Reuse the existing `.auth-error` styling in `login.html`. The error string is
generic: e.g. **"Invalid email or password."**

---

## 10. Validation & Error Handling

| Input / case | Behavior |
|--------------|----------|
| Empty email or password | `Form(...)` is required → 422 from FastAPI; HTML form also has `required`, so this is an edge case (direct POST). Acceptable to let it 422, or pre-check and re-render with error. |
| Email not in `users` | Re-render `login.html`, generic error, HTTP 200 |
| Wrong password | Re-render `login.html`, **same** generic error, HTTP 200 |
| Email case / whitespace | Normalize with `.strip().lower()` before lookup (emails stored lowercase by seed/register) |
| Valid credentials | 303 redirect to `/`, `spendly_session` cookie set |
| **Already logged in, `GET /login`** | 303 redirect to `/`; form never rendered (§8.4) |
| **Already logged in, `POST /login`** | 303 redirect to `/`; credentials ignored, no error, no re-auth (§8.4) |
| Tampered/forged cookie | `_read_session` signature check fails → treated as logged-out |
| Cookie references deleted user | `get_user_by_id` returns `None` → treated as logged-out |

---

## 11. Security Considerations

- **Generic auth errors (US-2):** never disclose whether the email exists — same
  message for "no such user" and "wrong password".
- **Signed cookie:** the session value is HMAC-signed; verification uses
  `hmac.compare_digest` (constant-time, already the pattern in `db.py`). A user
  cannot change their `user_id` without invalidating the signature.
- **Cookie flags:** `httponly` + `samesite="lax"`; `secure=True` in production.
- **Secret management:** `SPENDLY_SECRET_KEY` must be set in production; rotating
  it invalidates all sessions (acceptable).
- **No plaintext passwords** ever logged or stored — only `verify_password`.
- **Out of scope but flagged:** CSRF protection on the POST form, login rate
  limiting / lockout, and "remember me". Note them; do not build.

### Alternative considered — `SessionMiddleware` (rejected for now)

Starlette's `SessionMiddleware` would give signed cookies for free, but it
depends on **`itsdangerous`**, which is **not** in `requirements.txt`. Adopting it
means adding a package — disallowed by CLAUDE.md without explicit owner sign-off.
The stdlib-signed-cookie approach above needs **zero** new dependencies and is the
recommended path. If the owner approves adding `itsdangerous`, swap §6 for
`SessionMiddleware` + `request.session["user_id"]` and update this spec.

---

## 12. Acceptance Criteria

- [ ] `POST /login` with valid seeded credentials (e.g. `nitish@example.com` /
      `password123`) sets a `spendly_session` cookie and 303-redirects to `/`.
- [ ] `POST /login` with a wrong password re-renders `login.html` with a generic
      error and **no** session cookie (HTTP 200).
- [ ] `POST /login` with an unknown email shows the **same** generic error.
- [ ] An already-authenticated user hitting `GET /login` is 303-redirected to `/`
      (the form is never shown).
- [ ] An already-authenticated user re-submitting `POST /login` is 303-redirected
      to `/` without credential checks, errors, or session change.
- [ ] After login, `base.html` nav shows the user's name + "Sign out".
- [ ] `GET /logout` clears `spendly_session` and redirects to `/`; nav reverts to
      "Sign in" / "Get started".
- [ ] A forged/tampered cookie is treated as logged-out (no 500).
- [ ] `get_current_user(request)` returns the user row when logged in, else `None`.
- [ ] No raw SQL in `app.py`; login uses `get_user_by_email` from `db.py`.
- [ ] `requirements.txt` unchanged (no `itsdangerous`, no new packages).
- [ ] CLAUDE.md route table and env-var docs updated.

---

## 13. Testing Scenarios (`tests/test_auth.py`)

Per CLAUDE.md testing section — use the throwaway-DB fixtures (`seeded_db`),
never the dev DB. Use Starlette `TestClient` (don't auto-follow redirects so the
303 + `Set-Cookie` can be asserted).

1. `test_login_success_sets_cookie` — valid creds → 303, `spendly_session` in
   `Set-Cookie`, `Location: /`.
2. `test_login_wrong_password` — 200, error text present, no session cookie.
3. `test_login_unknown_email` — 200, **same** error text as #2.
4. `test_login_email_case_insensitive` — `NITISH@EXAMPLE.COM` still logs in.
5. `test_get_login_redirects_when_authenticated` — `GET /login` with a valid
   cookie → 303 to `/`, form not rendered.
6. `test_post_login_redirects_when_authenticated` — `POST /login` with a valid
   cookie (even with *wrong* form creds) → 303 to `/`, no error, session unchanged.
7. `test_logout_clears_cookie` — `GET /logout` → 303 to `/`, cookie deleted.
8. `test_nav_shows_user_when_logged_in` — request `/` with valid cookie → name +
   "Sign out" rendered.
9. `test_nav_anonymous` — request `/` without cookie → "Sign in" rendered.
10. `test_tampered_cookie_is_anonymous` — bad signature → treated as logged-out.
11. `test_get_user_by_email_helper` — returns row / `None` (db-level).

---

## 14. Edge Cases

| Case | Expected |
|------|----------|
| Direct POST with missing field | FastAPI 422 (form `required` normally prevents) |
| Cookie present but secret rotated | Signature invalid → logged-out |
| Cookie user_id valid sig but user deleted | `get_current_user` → `None` |
| Double logout | Second `/logout` still 303s to `/` (idempotent) |
| `SPENDLY_SECRET_KEY` unset in dev | Generated ephemeral secret + warning; sessions reset on restart |
| Whitespace around email | Trimmed before lookup |

---

## 15. Dependencies

- **Spec 001 (Database Setup)** — requires `users` table, `hash_password`,
  `verify_password`, `get_db`. ✅ Implemented.
- Requires at least one user to exist: run `seed_db()` (via `SPENDLY_ENV=dev` or
  the bootstrap command) or seed dummy data before manual testing.

---

## 16. Open Questions

- [ ] **`current_user` injection:** thread it through each route's context vs.
      inject globally (middleware / `templates.env.globals`)? Global injection is
      cleaner as more pages are added — **recommend global**; confirm.
- [ ] **Cookie lifetime:** session-only vs. fixed `max_age` (e.g. 7 days)?
- [ ] **Post-login redirect target:** stays `/` until the dashboard/profile step
      exists, then point there. Confirm interim target is acceptable.
- [ ] **Adopt `itsdangerous` + `SessionMiddleware` instead?** Requires owner
      approval to add a package; default is **no** (stdlib cookie).

---

## 17. Definition of Done

- [ ] `POST /login` and `GET /logout` implemented in `app.py` per §8; stub
      replaced.
- [ ] `get_user_by_email` / `get_user_by_id` added to `database/db.py`
      (parameterized); no SQL in routes.
- [ ] Session helpers (`_sign_session`, `_read_session`, `get_current_user`) in
      `app.py`, stdlib only.
- [ ] `base.html` nav reflects auth state; `current_user` available to templates.
- [ ] `tests/test_auth.py` scenarios in §13 pass (`pytest`).
- [ ] CLAUDE.md route table updated (`POST /login`, `/logout` → Implemented) and
      `SPENDLY_SECRET_KEY` documented under Deployment env vars.
- [ ] `requirements.txt` unchanged — no new packages.
- [ ] App runs on port 5001; manual login/logout round-trip works against a
      seeded DB.
