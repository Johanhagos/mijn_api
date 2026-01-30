#!/bin/sh
set -e

echo "Starting container entrypoint"

# Run Alembic migrations if alembic is available
if command -v alembic >/dev/null 2>&1; then
  echo "Running alembic upgrade head..."
  alembic upgrade head
else
  echo "alembic not installed; skipping migrations"
fi

echo "Starting Gunicorn Uvicorn worker"
exec gunicorn -k uvicorn.workers.UvicornWorker -w 4 main:app --bind 0.0.0.0:${PORT:-8000} --timeout 120
