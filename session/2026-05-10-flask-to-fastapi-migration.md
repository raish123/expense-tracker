# Session Notes — Flask to FastAPI Migration
**Date:** 2026-05-10
**Project:** Spendly — Expense Tracker (`d:\expense-tracker`)

---

## 1. Project Structure Overview

```
d:\expense-tracker\
├── app.py                  ← Flask/FastAPI entry point
├── requirements.txt        ← Python dependencies
├── .gitignore
├── database/
│   ├── __init__.py         ← empty package marker
│   └── db.py               ← placeholder: get_db(), init_db(), seed_db()
├── static/
│   ├── css/style.css       ← complete design system
│   └── js/main.js          ← placeholder (empty)
└── templates/
    ├── base.html            ← master layout (navbar + footer)
    ├── landing.html         ← hero, features, CTAs
    ├── login.html           ← login form
    └── register.html        ← registration form
```

### Tech Stack
- **Backend:** Python + FastAPI (migrated from Flask)
- **Database:** SQLite (not yet implemented)
- **Templates:** Jinja2
- **Styling:** Pure CSS with custom properties
- **Testing:** pytest + httpx + pytest-asyncio
- **Currency:** Indian Rupees (₹)
- **Brand:** Spendly

---

## 2. Flask → FastAPI Migration

### app.py Changes

| Flask | FastAPI |
|---|---|
| `@app.route("/")` | `@app.get("/", response_class=HTMLResponse)` |
| `render_template("x.html")` | `templates.TemplateResponse("x.html", {"request": request})` |
| `def landing()` | `async def landing(request: Request)` |
| `<int:id>` path param | `{id}` with `id: int` type annotation |
| `app.run(port=5001)` | `uvicorn.run("app:app", port=5001, reload=True)` |

### Final app.py

```python
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

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
```

---

## 3. HTML Templates — FastAPI Update

Only `base.html` needed changes. FastAPI/Starlette uses `path=` instead of Flask's `filename=` for static file references.

| Before (Flask) | After (FastAPI) |
|---|---|
| `url_for('static', filename='css/style.css')` | `url_for('static', path='css/style.css')` |
| `url_for('static', filename='js/main.js')` | `url_for('static', path='js/main.js')` |

Route `url_for` calls (`landing`, `login`, `register`) are unchanged — FastAPI resolves them by Python function name identically to Flask.

---

## 4. requirements.txt Changes

### Before (Flask)
```
flask==3.1.3
werkzeug==3.1.6
pytest==8.3.5
pytest-flask==1.3.0
```

### After (FastAPI)
```
fastapi==0.115.12
uvicorn[standard]==0.34.2
jinja2==3.1.6
python-multipart==0.0.20
aiofiles==24.1.0
pytest==8.3.5
httpx==0.28.1
pytest-asyncio==0.26.0
```

---

## 5. Installed Libraries (pip list snapshot)

Key packages already installed in environment:

| Package | Installed |
|---|---|
| fastapi | 0.110.0 |
| uvicorn | 0.29.0 |
| jinja2 | 3.1.6 |
| python-multipart | 0.0.9 |
| httpx | 0.28.1 |
| starlette | 0.36.3 |
| aiofiles | ❌ missing |
| pytest | ❌ missing |
| pytest-asyncio | ❌ missing |

> **Action required:** `pip install aiofiles` — needed for FastAPI to serve static files.

---

## 6. How to Run the Project

```powershell
# Navigate to project
cd d:\expense-tracker

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn app:app --reload --port 5001
```

### Available URLs
- `http://localhost:5001` — Landing page
- `http://localhost:5001/login` — Login
- `http://localhost:5001/register` — Register
- `http://localhost:5001/docs` — Swagger UI (free with FastAPI)
- `http://localhost:5001/redoc` — ReDoc API docs

---

## 7. Planned Route Map

| Route | Method | Step | Purpose |
|---|---|---|---|
| `/` | GET | done | Landing page |
| `/register` | GET/POST | 2 | User registration |
| `/login` | GET/POST | 2 | User login |
| `/logout` | GET | 3 | Session teardown |
| `/profile` | GET | 4 | User profile |
| `/expenses/add` | GET/POST | 7 | Add expense |
| `/expenses/<id>/edit` | GET/POST | 8 | Edit expense |
| `/expenses/<id>/delete` | GET | 9 | Delete expense |

---

## 8. Next Steps

- [ ] Implement `database/db.py` — `get_db()`, `init_db()`, `seed_db()` with SQLite
- [ ] Add POST handler for `/register` with form validation
- [ ] Add POST handler for `/login` with session/JWT auth
- [ ] Implement `/logout` route
- [ ] Build expense CRUD routes (Steps 7–9)
- [ ] Add JavaScript to `static/js/main.js`
