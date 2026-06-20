# Spec: User Registration (002)

**Feature ID:** 002
**Status:** Implemented (2026-06-20)
**Owner:** raish123
**Target file(s):** `app.py` (new `POST /register` handler), `database/db.py` (new `create_user()` + `get_user_by_email()` helpers), `templates/register.html` (reuse — minor success/error wiring), `tests/test_register.py` (new)
**Created:** 2026-06-20

---

## 1. Summary

Wire up the **`POST /register`** handler so the existing registration form
actually creates accounts. Today the registration flow is half-built:

- `GET /register` is **implemented** ([app.py:37-39](../../app.py#L37-L39)) and renders
  [register.html](../../templates/register.html), which already POSTs `name`, `email`,
  `password` to `/register`.
- The `users` table already exists with the exact columns this feature needs
  (`name`, `email UNIQUE`, `password_hash`) from Spec 001.
- `hash_password()` already exists in [database/db.py](../../database/db.py) and is the
  designated way to store credentials.

What is **missing** is the server side: there is no `POST /register` route, so
submitting the form currently 405s. This spec adds that handler plus the two
thin DB helpers it needs, validates the input, hashes the password, inserts the
user, and redirects to `GET /login` on success.

This is the natural follow-on to Spec 001 (database) and the precursor to login
(`GET /login` exists; its POST handler and sessions are a **separate, later
step** — see §3 Non-Goals).

---

## 2. Goals

- Add a working `POST /register` route that creates a real `users` row.
- Validate name / email / password before insert, re-rendering the form with a
  human-readable error on failure (no stack traces, no JSON).
- Hash passwords with the existing `hash_password()` — never store plaintext.
- Keep **all** SQL in `database/db.py` via two new helpers — no inline SQL in the route.
- Reuse the existing [register.html](../../templates/register.html) and its `{% if error %}`
  block — no new template, no new CSS.

## 3. Non-Goals

- **No login / session creation.** Registration does **not** log the user in or
  set a cookie. After success it redirects to `GET /login`. Sessions, `POST /login`,
  and `GET /logout` (Step 3) are out of scope.
- No email verification / confirmation emails (no mail dependency exists).
- No "confirm password" field, password-strength meter, or CAPTCHA.
- No profile page (`GET /profile`, Step 4) or any expense routes.
- **No new pip packages** and no new template/CSS files.

---

## 4. User Stories

| ID | As a… | I want… | So that… |
|----|-------|---------|----------|
| US-1 | new visitor | to submit the signup form and have my account created | I can later sign in and track expenses |
| US-2 | new visitor | a clear inline error when my email is already taken | I know to sign in instead of re-registering |
| US-3 | new visitor | a clear inline error when my input is invalid | I can correct it without losing context |
| US-4 | the system | the password stored only as a PBKDF2 hash | a DB leak never exposes raw passwords |
| US-5 | future login step | a `get_user_by_email()` lookup helper | Step 2 (login) can reuse it to authenticate |

---

## 5. Constraints (from CLAUDE.md)

- **FastAPI only.** Route lives in [app.py](../../app.py) (single file, no routers yet).
- Form bodies use `Form(...)` params — requires `python-multipart` (already present).
- **All SQL in `database/db.py`** — the route calls helpers, never embeds SQL.
- Queries **parameterized** (`?` placeholders) — never f-strings/concatenation.
- Errors raise `HTTPException(...)` *or*, for form re-render, return the template
  with an `error` — never bare strings or Flask's `abort()`.
- Templates use `url_for()` for internal links; the route resolves by function
  name (`url_for('login')`, `url_for('register')`).
- Password hashing uses the existing stdlib `hash_password()` — **no `bcrypt`/`passlib`.**
- App runs on **port 5001**.

---

## 6. Route Specification

### `POST /register`

| Aspect | Value |
|--------|-------|
| Decorator | `@app.post("/register")` |
| Function | `async def register_submit(request: Request, name: str = Form(...), email: str = Form(...), password: str = Form(...))` |
| Success response | `RedirectResponse(f"{request.url_for('login')}?registered=1", status_code=303)` — the `?registered=1` query param drives the login-page confirmation banner (§9) |
| Failure response | `TemplateResponse("register.html", {"request": request, "error": <msg>}, status_code=400)` |
| Imports needed | add `Form` to the `fastapi` import; add `RedirectResponse` to `fastapi.responses` |

**Why 303 (See Other):** turns the POST into a GET redirect so a browser refresh
on the login page does not re-submit the registration (Post/Redirect/Get).

**Sketch (illustrative — not the deliverable):**

```python
@app.post("/register")
async def register_submit(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
):
    name, email = name.strip(), email.strip().lower()
    error = validate_registration(name, email, password)  # §7
    if error:
        return templates.TemplateResponse(
            "register.html", {"request": request, "error": error}, status_code=400
        )
    try:
        create_user(name, email, password)          # db.py helper, §8
    except sqlite3.IntegrityError:                   # UNIQUE(email) race
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "That email is already registered."},
            status_code=400,
        )
    return RedirectResponse(f"{request.url_for('login')}?registered=1", status_code=303)
```

> `GET /register` ([app.py:37-39](../../app.py#L37-L39)) stays as-is.

---

## 7. Validation Rules

Validated in `app.py` **before** touching the DB. First failing rule wins;
return its message via the template `error`.

| Field | Rule | Error message |
|-------|------|---------------|
| `name` | non-empty after `.strip()` | "Please enter your name." |
| `name` | length ≤ 100 | "Name is too long." |
| `email` | non-empty, contains `@` with text either side, length ≤ 254 | "Please enter a valid email address." |
| `email` | not already in `users` (UNIQUE) | "That email is already registered." |
| `password` | length ≥ 8 | "Password must be at least 8 characters." |
| `password` | length ≤ 128 | "Password is too long." |

Notes:
- **Normalize before validating/storing:** `name.strip()`, `email.strip().lower()`
  (case-insensitive uniqueness — emails are stored lowercased).
- Email check is intentionally lightweight (no regex library / no new package) —
  presence of a single `@` with non-empty local and domain parts is sufficient
  for this learning project; HTML5 `type="email"` is the first line of defense.
- The DB `UNIQUE(email)` constraint is the **source of truth** for duplicates;
  the pre-check is a UX nicety, and the `IntegrityError` catch in §6 closes the
  check-then-insert race.

---

## 8. Database Helpers (new, in `database/db.py`)

No schema change — the `users` table from Spec 001 is reused as-is. Add two
thin, parameterized helpers:

### `create_user(name: str, email: str, password: str) -> int`
- Hashes via existing `hash_password(password)`.
- `INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)`.
- Commits, returns the new `lastrowid`.
- Lets `sqlite3.IntegrityError` propagate on duplicate email (caller handles it).
- Opens/closes its own connection via `get_db()` (same pattern as `seed_db()`).

### `get_user_by_email(email: str) -> sqlite3.Row | None`
- `SELECT id, name, email, password_hash, created_at FROM users WHERE email = ?`.
- Returns the `sqlite3.Row` or `None`.
- Used by §7's duplicate pre-check now, and by the **login** step later (US-5).

> `created_at` is populated automatically by the column `DEFAULT (datetime('now'))` —
> the helper does not set it.

---

## 9. UX / Template Notes

[register.html](../../templates/register.html) already supports everything needed —
**no template changes required for the error path**:

- The `{% if error %}<div class="auth-error">{{ error }}</div>{% endif %}` block
  (lines 16-18) renders the validation message.
- The form already POSTs `name` / `email` / `password` to `/register` (line 20).
- `.auth-error`, `.form-group`, `.btn-submit`, `.auth-section` styles already
  exist in [static/css/style.css](../../static/css/style.css) — no new CSS.

**Login confirmation banner (IMPLEMENTED, owner-approved):** after the redirect,
`login.html` shows an "Account created — please sign in." banner via the
`?registered=1` query param (no session/flash dependency). Concretely:
- `login.html` renders, above the existing `auth-error` block:
  `{% if request.query_params.get('registered') %}<div class="auth-success">Account created — please sign in.</div>{% endif %}`.
  (`request` is already in the `GET /login` context, so no route change.)
- A new `.auth-success` rule was added to
  [static/css/style.css](../../static/css/style.css) (green variant of
  `.auth-error`, reusing `--accent` / `--accent-light`). **No new CSS *file*** —
  this is the single in-scope CSS addition that supersedes the original "no new
  CSS" line for the success path.

**Field values on error (NOT implemented — owner decision):** the entered
`name`/`email` are **not** echoed back on a validation re-render; the form clears.
Echoing would mean passing `name`/`email` into the context and adding
`value="{{ name|default('') }}"` to those inputs, but it was explicitly left out
of v1. The password is never echoed.

---

## 10. Security Considerations

- **Never store plaintext** — only `hash_password()` output (PBKDF2-SHA256,
  per-user salt) goes into `password_hash`.
- **No password in logs / no echo** — never log the raw password; never reflect
  it back into the rendered template.
- **Account enumeration:** "That email is already registered." is a deliberate,
  accepted trade-off for this learning project's UX (consistent with the
  separate Sign-in link). Note it; do not over-engineer.
- **Parameterized inserts** prevent SQL injection on `name`/`email`.
- **Email normalized to lowercase** so `A@x.com` and `a@x.com` can't both register.
- No session/cookie is set here, so no session-fixation surface is introduced by
  registration (that risk belongs to the login step).
- CSRF is **not** handled (no token, no session yet) — acceptable for now and
  consistent with the rest of the app; revisit when sessions land.

---

## 11. Acceptance Criteria

- [x] `POST /register` exists; submitting valid `name`/`email`/`password` creates exactly one `users` row.
- [x] The stored `password_hash` is **not** the plaintext password and `verify_password(password, row["password_hash"])` returns `True`.
- [x] On success the response is a **303 redirect to `GET /login?registered=1`** (`Location` resolves via `url_for('login')`, with the `?registered=1` query param driving the confirmation banner).
- [x] Duplicate email (case-insensitive) does **not** create a second row and re-renders the form with "That email is already registered." (HTTP 400).
- [x] Empty name, malformed email (`"not-an-email"`), and a 7-char password each re-render the form with the matching §7 message (HTTP 400) and insert **no** row.
- [x] Email is stored lowercased and stripped.
- [x] No raw SQL exists in `app.py`; all DB access goes through `create_user()` / `get_user_by_email()`.
- [x] No new pip packages; `requirements.txt` unchanged.
- [x] `GET /register` still renders the form unchanged.

---

## 12. Testing Scenarios (`tests/test_register.py`)

Per CLAUDE.md testing section — use the `empty_db` fixture (monkeypatches
`database.db.DB_PATH` to a `tmp_path` file via `conftest.py`); **never** the dev
DB.

**Client choice (implementation note):** routes are driven with
`httpx.AsyncClient` over an `httpx.ASGITransport(app=app)` (async tests, auto-run
under `asyncio_mode = auto`), **not** Starlette's `TestClient`. Reason: the
installed environment is out of sync with `requirements.txt` (starlette 0.36.3 /
fastapi 0.110.0 installed vs. fastapi 0.115.x pinned), and that older
`TestClient` is incompatible with the installed httpx 0.28.1 (it passes the
removed `app=` kwarg → `TypeError`). `httpx.AsyncClient` is version-robust and is
explicitly endorsed by CLAUDE.md for async tests. Create the client with
`follow_redirects=False` so the 303 is observable. Pure-helper tests
(`create_user`, `get_user_by_email`) stay synchronous. Running `pip install -r
requirements.txt` to realign versions would also let `TestClient` work, but is
not required for the suite to pass.

| # | Test | Asserts |
|---|------|---------|
| 1 | `test_register_success_creates_user` | 303 → `/login?registered=1`; one row in `users`; email lowercased |
| 2 | `test_register_hashes_password` | stored hash ≠ plaintext; `verify_password()` True |
| 3 | `test_register_duplicate_email` | second POST → 400, "already registered", still one row |
| 4 | `test_register_duplicate_email_case_insensitive` | `A@x.com` then `a@x.com` → 400, one row |
| 5 | `test_register_empty_name` | 400, "Please enter your name.", no row |
| 6 | `test_register_invalid_email` | 400, invalid-email message, no row |
| 7 | `test_register_short_password` | 7-char password → 400, length message, no row |
| 8 | `test_register_get_still_renders` | `GET /register` → 200, contains the form |
| 9 | `test_create_user_helper` | `create_user()` returns an int id; row readable by `get_user_by_email()` |
| 10 | `test_get_user_by_email_missing` | returns `None` for unknown email |

---

## 13. Edge Cases

| Case | Expected behavior |
|------|-------------------|
| Whitespace-only name (`"   "`) | rejected (empty after strip) |
| Email with surrounding spaces / mixed case | stripped + lowercased before store |
| Duplicate email submitted twice quickly (race) | `IntegrityError` caught → 400 message, no dup row |
| Missing form field entirely | FastAPI `Form(...)` → 422 (framework default; acceptable) |
| Very long name/password (>limit) | rejected by §7 length rules |
| Valid submit | one row, 303 → `/login?registered=1` (banner shown) |

---

## 14. Dependencies

- **Spec 001 (Database Setup)** — requires `users` table, `get_db()`,
  `hash_password()`, `verify_password()`, and the `conftest.py` fixtures. All
  implemented.
- Blocks the upcoming **login** step (`POST /login` + sessions), which will
  reuse `get_user_by_email()` and `verify_password()`.

---

## 15. Open Questions (RESOLVED)

- [x] Echo `name`/`email` back into the form on validation error (§9)?
      **Decision: NO** — left out of v1 (owner decision). Form clears on error.
- [x] Show a "registered — please sign in" confirmation on `login.html` via
      `?registered=1` (§9)? **Decision: YES, implemented** (owner-approved) via the
      query-param approach — see §9.
- [x] Accept account-enumeration via the duplicate message (§10), or use a
      generic error? **Decision: keep the specific** "That email is already
      registered." message for UX.

---

## 16. Definition of Done

- [x] `POST /register` handler added to [app.py](../../app.py) (with `Form` + `RedirectResponse` + `sqlite3` imports, and a module-level `validate_registration()` helper); `GET /register` unchanged.
- [x] `create_user()` and `get_user_by_email()` added to [database/db.py](../../database/db.py); no SQL in `app.py`.
- [x] All §11 acceptance criteria met; `tests/test_register.py` (§12, 10 tests) passes via `pytest` (full suite: 20 passed).
- [x] `requirements.txt` unchanged; **no new** template/CSS *files*. `login.html` modified and a `.auth-success` rule added to `style.css` for the owner-approved confirmation banner (§9).
- [x] CLAUDE.md "Implemented vs stub routes" table updated: `GET /register` note "(POST handler pending)" removed and a `POST /register` row added as Implemented.
- [x] App starts on port 5001; manual signup creates a user and lands on `/login?registered=1` with the confirmation banner.
