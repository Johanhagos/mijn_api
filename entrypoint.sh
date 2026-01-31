#!/bin/sh
set -e

echo "Starting API..."
echo "=== Entrypoint debug start: $(date -u) ==="

# helper to mask long env values when printing
mask_val() {
  v="$1"
  if [ -z "$v" ]; then
    printf "<not set>"
    return
  fi
  len=${#v}
  if [ "$len" -le 12 ]; then
    printf "%s" "$v"
    return
  fi
  prefix=$(printf "%s" "$v" | cut -c1-6)
  suffix=$(printf "%s" "$v" | rev | cut -c1-4 | rev)
  printf "%s****%s" "$prefix" "$suffix"
}

echo "Environment (masked):"
echo "  PORT=${PORT:-8000}"
echo "  DATABASE_URL=$(mask_val "$DATABASE_URL")"
echo "  RAILWAY_ENVIRONMENT=${RAILWAY_ENVIRONMENT:-<not set>}"
echo "  REQUIRE_API_KEY=${REQUIRE_API_KEY:-0}"
echo "  DATA_DIR=$(mask_val "$DATA_DIR")"

# Check if alembic command is available
if command -v alembic >/dev/null 2>&1; then
  if [ -n "$DATABASE_URL" ]; then
    echo "Running Alembic migrations (verbose)..."
    alembic upgrade head 2>&1 | sed 's/^/alembic: /'
    echo "Alembic exit status: $?"
  else
    echo "No DATABASE_URL set, skipping migrations"
  fi
else
  echo "alembic not installed; skipping migrations"
fi

# Quick DB connectivity check via Python (use `python` from PATH for portability)
echo "Checking DB connectivity..."
python - <<'PY'
import os,sys
from sqlalchemy import create_engine, text
url=os.environ.get('DATABASE_URL')
if not url:
    print('DB_TEST: DATABASE_URL not set, skipping')
    sys.exit(0)
try:
    connect_args = {}
    if url.startswith('sqlite'):
        connect_args = {"check_same_thread": False}
    engine = create_engine(url, connect_args=connect_args)
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    print('DB_TEST: OK')
except Exception as e:
    import traceback
    traceback.print_exc()
    print('DB_TEST: FAILED')
    # Do not exit non-zero; let the process continue so logs are visible
PY

# Default PORT for Railway
PORT=${PORT:-8000}

# Prefer gunicorn if available, otherwise fall back to uvicorn for easier local debugging
if command -v gunicorn >/dev/null 2>&1; then
  echo "Starting Gunicorn (single worker, debug logging)"
  exec gunicorn main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers ${GUNICORN_WORKERS:-1} \
    --bind 0.0.0.0:$PORT \
    --timeout 120 \
    --capture-output \
    --log-level debug \
    --access-logfile - \
    --error-logfile -
else
  echo "gunicorn not found; starting uvicorn directly"
  exec python -m uvicorn main:app --host 0.0.0.0 --port $PORT --log-level debug
fi
