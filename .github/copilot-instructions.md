## Purpose
This file tells AI coding agents how this small FastAPI service is structured and what patterns to follow when making changes.

## Quick Start (what a human would run)
- Install dependencies: `pip install -r requirements.txt`
- Run locally: `uvicorn main:app --reload --host 127.0.0.1 --port 8000`

## Key files
- App entry / routes: [main.py](main.py)
- Persistent data (flat JSON): [users.json](users.json)
- Dependencies: [requirements.txt](requirements.txt)

## High-level architecture
- Single FastAPI process exposing REST endpoints for user management and auth.
- JWT-based auth with short-lived access tokens and refresh tokens. Tokens embed `sub` (username) and `role` claims.
- User records are stored in a single JSON file next to `main.py`. The app uses an in-process `threading.Lock` to avoid concurrent writes (single-process only).

## Project-specific patterns & conventions
- Pydantic models define request and response shapes. See `User`, `PublicUser`, `LoginRequest` in `main.py`.
- Passwords are hashed with passlib/bcrypt (`CryptContext`). The code enforces a 72-byte bcrypt limit before hashing.
- Role-based access is implemented via `role_required(...)` and the convenience `admin_required` / `require_admin` dependencies.
- Token extraction uses `OAuth2PasswordBearer(tokenUrl="login")` and endpoints `/login` and `/refresh` to obtain tokens.
- `load_users()` silently recovers from JSON decode errors by returning an empty list — be careful when changing persistence behavior.

## Safety & deployment notes (important for edits)
- `USERS_FILE` is a flat file; the lock is process-local. Do NOT assume file writes are safe under multi-process deployment (Gunicorn/uvicorn workers). If you need concurrency, migrate to a proper datastore.
- SECRET_KEY is read from `JWT_SECRET_KEY` env var; hard-coded fallback exists for dev only. New changes must keep this env override.
- Avoid leaking internal exceptions in HTTP responses (the code intentionally maps errors to 4xx/5xx messages).

## Typical change examples
- Add a new protected endpoint: use `Depends(get_current_user)` for authenticated or `Depends(require_admin)` for admin-only.
- Return public user views: match the pattern used in `list_users` / `get_user` (hide `password` field and return `id`, `name`, `role`).
- When changing password handling: respect `BCRYPT_MAX_BYTES` and use `pwd_context.hash()` / `pwd_context.verify()` consistently.

## Useful examples
- Login request (JSON body):
```
{ "name": "AliceAdmin", "password": "hunter2" }
```
- Use access token on requests:
```
Authorization: Bearer <access_token>
```

## Debugging tips
- Logs from the server typically appear in the terminal started by `uvicorn`. There is an `uvicorn.err` file in repo root — check it if a background run was used.
- To reproduce persistent-state problems, inspect [users.json](users.json) directly but prefer API endpoints to mutate state so business rules are enforced.

## What not to change without review
- The simple file-based persistence model and `_lock` concurrency mechanism — migrating this requires coordination and tests.
- Token claim names (`sub`, `role`) — these are used throughout role checks and token refresh flows.

## Where to look for related code
- Authentication and auth helpers: `main.py` (search for `create_access_token`, `verify_token`, `oauth2_scheme`).
- File persistence helpers: `load_users()`, `save_users()` in `main.py`.

## Questions for the repo owner
- Should we add unit/integration tests for auth flows?
- Is multi-process deployment expected (to decide whether to migrate persistence)?

Please review and tell me if you want this tightened (fewer instructions) or expanded with code snippets and CI commands.
