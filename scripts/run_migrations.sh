#!/usr/bin/env bash
set -euo pipefail

# Safe migration runner for CI / ops
# Checks for required env vars then runs alembic upgrade heads

if [ -z "${DATABASE_URL:-}" ]; then
  echo "ERROR: DATABASE_URL is not set. Aborting."
  exit 2
fi

if [ -z "${JWT_SECRET_KEY:-}" ]; then
  echo "ERROR: JWT_SECRET_KEY is not set. Aborting."
  exit 3
fi

echo "Using DATABASE_URL=${DATABASE_URL%%@*}@..."

# Ensure alembic is available
if ! command -v alembic >/dev/null 2>&1; then
  echo "alembic not found on PATH. Activate your venv or install requirements." >&2
  exit 4
fi

echo "Running alembic upgrade heads..."
alembic upgrade heads

echo "Migrations applied."
