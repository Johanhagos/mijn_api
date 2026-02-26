Param()
Set-StrictMode -Version Latest

# Safe migration runner for Windows PowerShell
if (-not $env:DATABASE_URL) {
    Write-Error "ERROR: DATABASE_URL is not set. Aborting."
    exit 2
}
if (-not $env:JWT_SECRET_KEY) {
    Write-Error "ERROR: JWT_SECRET_KEY is not set. Aborting."
    exit 3
}

# Masked display of DATABASE_URL
$db = $env:DATABASE_URL
$masked = if ($db -match '@') { ($db -split '@')[0] + '@...' } else { $db }
Write-Host "Using DATABASE_URL=$masked"

if (-not (Get-Command alembic -ErrorAction SilentlyContinue)) {
    Write-Error "alembic not found on PATH. Activate your venv or install requirements."
    exit 4
}

Write-Host "Running alembic upgrade heads..."
alembic upgrade heads

Write-Host "Migrations applied."
