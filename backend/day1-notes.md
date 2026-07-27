# Day 1 Notes — Django Project Setup + PostgreSQL

**Project:** Study Space Finder (Django REST Framework + React)
**Goal of this session:** Set up the Django backend project and connect it to a PostgreSQL database.

---

## 1. Big Picture — What Was Actually Built Today

- Created a `backend/` folder with a working **Django project** (not yet an "app" — that's next).
- Installed and connected **PostgreSQL** as the database instead of Django's default SQLite.
- Ran Django's built-in migrations successfully — confirming the whole stack (Django ↔ Postgres) talks to each other correctly.
- No models, no API endpoints yet — this was pure foundation/setup work.

**Interview one-liner:**
> "I set up a Django project connected to PostgreSQL, using environment variables for secrets and Django REST Framework ready for building the API."

---

## 2. Key Concepts to Understand (not just remember)

### Django Project vs. Django App
- A **project** (`config/` folder here) = the overall settings, root URL routing, WSGI/ASGI config. There's only one project.
- An **app** (e.g. `spaces/`, coming in Step 2) = a self-contained module with its own models, views, logic. A project can have many apps.
- **Why it matters:** interviewers may ask "what's the difference between a Django project and app" — this is a classic Django fundamentals question.

### Virtual Environment (`venv`)
- A `venv` is an **isolated Python environment** — packages installed here don't affect your system-wide Python or other projects.
- Created with: `python -m venv venv`
- Activated with: `.\venv\Scripts\Activate.ps1` (Windows PowerShell)
- **Why it matters:** avoids version conflicts between projects (Project A needs Django 4, Project B needs Django 5 — venv keeps them separate).

### `.env` and `python-dotenv`
- Secrets (DB password, secret key) are stored in a `.env` file — **never committed to git** (it's in `.gitignore`).
- `.env.example` is a template *with* committed, showing what variables are needed, but without real values.
- `python-dotenv`'s `load_dotenv()` reads `.env` and loads those values into environment variables, which `settings.py` then reads via `os.environ.get(...)`.
- **Why it matters:** hardcoding passwords in code is a security anti-pattern. This `.env` pattern is industry standard.

### PostgreSQL vs. SQLite
- **SQLite** = a simple file-based database, zero setup, fine for small/local projects. Django's default.
- **PostgreSQL** = a full database *server*, used in real production apps — handles more data, more concurrent users, more complex queries.
- We switched to Postgres for realistic, resume-relevant experience.

### `psycopg2-binary`
- This is the **adapter/driver** that lets Django (Python) actually talk to PostgreSQL. Without it, Django has no way to send SQL commands to Postgres.

### Django REST Framework (DRF) & CORS — installed now, used later
- **DRF** = the toolkit for building APIs in Django (serializers, viewsets — coming in later steps).
- **django-cors-headers** = lets a *different* origin (our React app, running on a different port) call this Django API without the browser blocking it for security reasons (CORS = Cross-Origin Resource Sharing).

---

## 3. The PostgreSQL Permission Issues (the confusing part!) — Explained Simply

This was the trickiest part of today, so here's the plain-English breakdown:

**Analogy:** PostgreSQL is like a building with rooms (databases). Inside each room there's a common area called the `public` schema, where tables actually get stored.

**What happened, step by step:**

1. **Password mismatch** — the app's `.env` file had one password, but the actual PostgreSQL user (`studyspace_user`) had a different one set in pgAdmin. Fixed by making them match (`ALTER USER ... WITH PASSWORD ...`).

2. **Permission denied for schema public** — Since PostgreSQL 15+, only the **owner** of the `public` schema (usually the `postgres` superuser) is allowed to create tables in it by default. Our app's regular user (`studyspace_user`) wasn't allowed to create tables — which is exactly what Django's `migrate` command needed to do.
   - **Fix attempt 1:** granted `CREATE` and `ALL` privileges on the schema — didn't fully work.
   - **Fix attempt 2 (worked):** made `studyspace_user` the **owner** of the `public` schema itself:
     ```sql
     ALTER SCHEMA public OWNER TO studyspace_user;
     GRANT ALL ON SCHEMA public TO studyspace_user;
     GRANT CREATE ON SCHEMA public TO studyspace_user;
     ```

**Why this is worth remembering (interview-relevant):**
> "PostgreSQL 15+ changed default permissions so regular users can't create tables in the public schema — I had to grant schema ownership to my app's database user to let Django's migrations run. It's a common real-world gotcha when setting up a fresh Postgres install."

This is a genuinely realistic "I hit a production-style issue and debugged it" story — good to have ready for interviews.

---

## 4. Commands Used Today (reference)

```bash
# Create + activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install django djangorestframework psycopg2-binary python-dotenv django-cors-headers
pip freeze > requirements.txt

# Start Django project (the "." keeps manage.py in backend/, no extra nested folder)
django-admin startproject config .

# Apply Django's built-in migrations (creates auth_user, django_migrations, etc.)
python manage.py migrate

# Run the local dev server
python manage.py runserver
```

```sql
-- Create database + app-specific user (safer than using the postgres superuser directly)
CREATE DATABASE study_space_finder;
CREATE USER studyspace_user WITH PASSWORD 'your_password_here';
GRANT ALL PRIVILEGES ON DATABASE study_space_finder TO studyspace_user;

-- Fix password mismatch
ALTER USER studyspace_user WITH PASSWORD 'studyspace_dev_password';

-- Fix schema permission (the actual fix that worked)
ALTER SCHEMA public OWNER TO studyspace_user;
GRANT ALL ON SCHEMA public TO studyspace_user;
GRANT CREATE ON SCHEMA public TO studyspace_user;
```

---

## 5. Project Structure So Far

```
study-space-finder/
├── .gitignore
└── backend/
    ├── .env                  # real secrets (gitignored, never commit)
    ├── .env.example          # template, safe to commit
    ├── requirements.txt      # locked dependency versions
    ├── manage.py             # Django's CLI entry point
    ├── venv/                 # isolated Python packages (gitignored)
    └── config/               # the Django "project" (not an "app")
        ├── settings.py       # DB config, installed apps, middleware
        ├── urls.py           # root URL router
        ├── wsgi.py
        └── asgi.py
```

---

## 6. Things I Should Be Able to Explain Out Loud (self-check)

- [ ] Difference between a Django **project** and an **app**
- [ ] What a virtual environment does and why it's used
- [ ] Why secrets go in `.env` instead of directly in code
- [ ] Why we chose PostgreSQL over SQLite for this project
- [ ] What `psycopg2-binary` does
- [ ] What the PostgreSQL schema permission issue was, and how it was fixed
- [ ] What `python manage.py migrate` actually does under the hood
- [ ] What `USE_TZ = True` means (Django stores times in UTC, converts to local `TIME_ZONE` on display)

---

## 7. What's Next — Step 2

**Step 2: `Space` model** — the first real Django app, containing the model for a study space (name, description, location, capacity, amenities, image). This is where actual coding/logic begins.