Switch staging to a managed Postgres
===================================

This document describes the minimal steps to move the Mijn API staging environment
from SQLite/local to a managed Postgres instance (e.g., Supabase, AWS RDS, Railway).

1) Provision a managed Postgres instance
  - Create a database and user. Note the connection string, e.g.:
    postgres://<user>:<password>@<host>:5432/<database>

2) Set production/staging environment variables
  - Set `DATABASE_URL` to the Postgres connection string.
  - Set `JWT_SECRET_KEY` to a strong secret (use your cloud provider's secret manager or GitHub Secrets).
  - Optionally set `DATA_DIR` to a writable directory for server-local artifacts.

3) Configure connection pooling
  - For serverful deployments (multiple workers), enable a connection pool or use pgbouncer.
  - Recommended: use SQLAlchemy pool sizing appropriate for your worker count. Example (env vars):
    - `DB_POOL_SIZE` or adjust your Gunicorn/ASGI worker count accordingly.

  - Example SQLAlchemy engine configuration (use these env vars to tune in production):

```python
from sqlalchemy import create_engine
import os

DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(
    DATABASE_URL,
    pool_size=int(os.environ.get("DB_POOL_SIZE", "5")),
    max_overflow=int(os.environ.get("DB_MAX_OVERFLOW", "10")),
    pool_timeout=int(os.environ.get("DB_POOL_TIMEOUT", "30")),
    pool_pre_ping=True,
    future=True,
)
```

  - Example Gunicorn + Uvicorn command for production (4 workers as an example):

```
gunicorn -k uvicorn.workers.UvicornWorker main:app -w 4 --bind 0.0.0.0:8000
```

4) Run Alembic migrations
  - Run `alembic upgrade heads` against the managed Postgres to create required tables.
  - We provide a `deploy_migrations` workflow in `.github/workflows/deploy_migrations.yml` which can
    be used from GitHub Actions (workflow_dispatch) and reads `DATABASE_URL` from secrets.

5) Verify
  - Start the app and run smoke tests. Ensure `/health` (if you have one) and auth flows behave.
  - Check that refresh tokens persist in the `refresh_tokens` table and rotation works.

Notes and recommendations
  - Do NOT use file-based `users.json` for production state; migrate any existing users to the DB.
  - Use TLS for all traffic and set `COOKIE_SECURE=True` in production.
  - Add monitoring and alerts for DB connection exhaustion and failed migrations.

Environment variables summary (suggested additions):

```env
# Database connection and pooling
DATABASE_URL=postgresql://user:password@host:5432/mijn_api
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30

# Security
JWT_SECRET_KEY=replace_with_strong_random
COOKIE_SECURE=1  # set in production
```

Setting GitHub Secrets
----------------------

You should set `DATABASE_URL` and `JWT_SECRET_KEY` as repository secrets so CI and the `deploy_migrations` workflow can run safely.

Using the GitHub CLI:

```bash
# replace values before running
gh secret set DATABASE_URL --body "postgresql://user:password@host:5432/mijn_api"
gh secret set JWT_SECRET_KEY --body "$(openssl rand -hex 32)"
```

Or via the GitHub web UI:

1. Go to your repository → Settings → Secrets and variables → Actions.
2. Click "New repository secret" and add `DATABASE_URL` and `JWT_SECRET_KEY`.

After adding secrets, you can run the Actions → "CI: Deploy Migrations (placeholder)" workflow or trigger the `deploy_migrations` workflow directly.
