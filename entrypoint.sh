#!/bin/sh
set -e

echo "Starting API..."

# Run migrations safely if DATABASE_URL is present
if [ -n "$DATABASE_URL" ]; then
  echo "Running Alembic migrations..."
  alembic upgrade head || echo "Alembic failed, continuing startup"
else
  echo "No DATABASE_URL set, skipping migrations"
fi

# Default PORT for Railway
PORT=${PORT:-8000}

echo "Starting Gunicorn (single worker, file-safe mode)"
exec gunicorn main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 1 \
  --bind 0.0.0.0:$PORT \
  --timeout 120 \
  --log-level info
