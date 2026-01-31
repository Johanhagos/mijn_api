#!/usr/bin/env pwsh
Write-Host "Starting API (PowerShell entrypoint)..."
Write-Host "=== Entrypoint debug start: $(Get-Date -Format o) ==="

function Mask-Val($v) {
  if ([string]::IsNullOrEmpty($v)) { return '<not set>' }
  $len = $v.Length
  if ($len -le 12) { return $v }
  $prefix = $v.Substring(0,6)
  $suffix = $v.Substring($len-4,4)
  return "$prefix****$suffix"
}

Write-Host "Environment (masked):"
Write-Host "  PORT=$($env:PORT -or 8000)"
Write-Host "  DATABASE_URL=$(Mask-Val $env:DATABASE_URL)"
Write-Host "  RAILWAY_ENVIRONMENT=$($env:RAILWAY_ENVIRONMENT -or '<not set>')"
Write-Host "  REQUIRE_API_KEY=$($env:REQUIRE_API_KEY -or '0')"

# Run alembic if available
if (Get-Command alembic -ErrorAction SilentlyContinue) {
  if ($env:DATABASE_URL) {
    Write-Host "Running Alembic migrations (verbose)..."
    try {
      & alembic upgrade head 2>&1 | ForEach-Object { "alembic: $_" }
      Write-Host "Alembic finished"
    } catch {
      Write-Warning "Alembic failed: $_"
    }
  } else {
    Write-Host "No DATABASE_URL set, skipping migrations"
  }
} else {
  Write-Host "alembic not installed; skipping migrations"
}

# Quick DB connectivity check via Python
Write-Host "Checking DB connectivity..."
$py = @'
import os,sys
from sqlalchemy import create_engine, text
url = os.environ.get('DATABASE_URL')
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
    sys.exit(2)
'@

& python -c $py
if ($LASTEXITCODE -ne 0) {
  Write-Warning "DB test failed (exit $LASTEXITCODE); continuing so logs are visible."
}

# Start uvicorn for local testing (use Gunicorn in production container)
$port = $env:PORT
if (-not $port) { $port = 8000 }
Write-Host "Starting uvicorn on 0.0.0.0:$port (for local testing)"
& python -m uvicorn main:app --host 0.0.0.0 --port $port --reload
