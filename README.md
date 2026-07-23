# Primexium Advisors — Backend

Official FastAPI backend for the Primexium Advisors website and student management platform.

**Repository:** [gullhassanmalik6/primexium-advisors-backend](https://github.com/gullhassanmalik6/primexium-advisors-backend)

## Tech stack

| Tool | Purpose |
|------|---------|
| FastAPI | REST API |
| Python 3.12+ | Runtime |
| SQLAlchemy 2 | ORM |
| Alembic | Migrations |
| Pydantic / pydantic-settings | Validation and config |
| PostgreSQL | Database |
| python-jose + passlib | JWT auth and password hashing |
| Cloudinary | Media uploads (optional) |

## Features

- JWT authentication (access + refresh tokens)
- User registration, login, and /auth/me
- PostgreSQL via SQLAlchemy + Alembic migrations
- CORS configured for the React frontend
- Health check endpoint

## Prerequisites

- Python 3.12+
- PostgreSQL (local or Neon)
- pip / virtualenv

## Getting started

`ash
git clone https://github.com/gullhassanmalik6/primexium-advisors-backend.git
cd primexium-advisors-backend

python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
# source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Edit .env with your DATABASE_URL and SECRET_KEY

alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
`

- API: http://localhost:8000
- Docs (when DEBUG=true): http://localhost:8000/docs
- Health: http://localhost:8000/health

## Environment variables

Copy .env.example to .env (never commit .env):

| Variable | Description |
|----------|-------------|
| APP_NAME | API title |
| APP_VERSION | Version string |
| DEBUG | Enables /docs and /redoc when 	rue |
| ENVIRONMENT | e.g. development / production |
| HOST / PORT | Local server bind |
| DATABASE_URL | PostgreSQL connection string |
| SECRET_KEY | JWT signing secret (use a long random value in production) |
| ALGORITHM | JWT algorithm (default HS256) |
| ACCESS_TOKEN_EXPIRE_MINUTES | Access token lifetime |
| REFRESH_TOKEN_EXPIRE_DAYS | Refresh token lifetime |
| CORS_ORIGINS | Comma-separated allowed origins |
| CLOUDINARY_* | Optional image upload credentials |

Example local DATABASE_URL:

`env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/primexium_db
`

## API overview

Base path: `/api/v1`

| Method | Path | Description |
|--------|------|-------------|
| POST | /auth/register | Create account |
| POST | /auth/login | Get access + refresh tokens |
| POST | /auth/refresh | Rotate access + refresh tokens |
| POST | /auth/change-password | Change password (authenticated) |
| GET | /auth/me | Current user (Bearer token) |
| POST | /student/documents/upload | Upload document via Cloudinary |
| GET | /health | Health check (root, not under /api/v1) |

## Project structure

```
app/
  api/v1/          # Routers and endpoints
  auth/            # Auth dependencies
  core/            # Settings, security, Cloudinary
  database/        # SQLAlchemy session
  models/          # ORM models
  schemas/         # Pydantic schemas
  main.py          # FastAPI app entry
alembic/           # Migrations
Dockerfile
render.yaml
railway.toml
Procfile
requirements.txt
```

## Database migrations

```bash
# Apply migrations
alembic upgrade head

# Create a new migration after model changes
alembic revision --autogenerate -m "describe change"
```

## Deploy (Render)

1. Create a Web Service from this repository on Render (Docker recommended).
2. Docker uses the included `Dockerfile`, or Python start command:
   `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Optional: use `render.yaml` Blueprint.
4. Set env vars: `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`, Cloudinary keys.
5. Point `CORS_ORIGINS` at your Vercel frontend URL and production domain.
6. Optionally map `api.primexiumadvisors.com` to the service.

## Deploy (Railway)

1. Create a Railway project from this repo.
2. Railway detects `railway.toml` + `Dockerfile`.
3. Add Postgres and set `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`, Cloudinary vars.
4. Health check path: `/health`.

## Security notes

- Do not commit .env or real secrets.
- Rotate SECRET_KEY if it was ever pushed to a public repo.
- Keep DEBUG=false in production.

## Related

- Frontend: [primexium-advisors-frontend](https://github.com/gullhassanmalik6/primexium-advisors-frontend)
