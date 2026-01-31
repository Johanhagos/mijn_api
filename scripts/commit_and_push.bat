@echo off
REM Commit and push current workspace changes to branch feat/merchant-dashboard-auth
REM Usage: run this from PowerShell or cmd after installing Git

SETLOCAL ENABLEDELAYEDEXPANSION
REM Change to repo root (assumes this script is in scripts\)
PUSHD "%~dp0.."

echo Creating branch feat/merchant-dashboard-auth (or switching to it)...
git checkout -B feat/merchant-dashboard-auth

echo Adding changes...
git add .

echo Committing...
git commit -m "feat: merchant dashboard auth + migration" || (
  echo No changes to commit or commit failed.
)

echo Pushing to origin...
git push -u origin feat/merchant-dashboard-auth

POPD
ENDLOCAL
