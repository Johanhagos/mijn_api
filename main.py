from fastapi import FastAPI, HTTPException, Body, Response, Request, UploadFile, File, Header
from fastapi.middleware.cors import CORSMiddleware
import hashlib
from pydantic import BaseModel, Field
from typing import List
import json
from pathlib import Path
import os
import sys
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
import uuid
from fastapi.responses import JSONResponse, HTMLResponse
from time import time
from jose import jwt, JWTError
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
import threading

app = FastAPI(title="Secure User API")

# CORS configuration: lock down to known frontend origins in production, allow localhost in non-prod
FRONTEND_ORIGINS = [
    "https://dashboard.apiblockchain.io",
    "https://apiblockchain.io",
]

# Allow localhost origins when not running in production (convenience for dev)
if os.getenv("RAILWAY_ENVIRONMENT") != "production":
    FRONTEND_ORIGINS += [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware to block debug routes when debug access is disabled.
@app.middleware("http")
async def block_debug_routes(request, call_next):
    path = request.url.path or ""
    if path.startswith("/debug") and (IS_PROD or not ALLOW_DEBUG):
        # Return 404 for any debug route when disabled for safety in production.
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    return await call_next(request)

# --- Environment / production hardening ---
# Detect a Railway production environment. Set `RAILWAY_ENVIRONMENT=production` there.
IS_PROD = os.getenv("RAILWAY_ENVIRONMENT") == "production"
# Require explicit opt-in to debug endpoints (extra safety).
# ALLOW_DEBUG is only true when the env var is set and we're NOT in production.
# This ensures Railway/production cannot enable debug routes accidentally.
ALLOW_DEBUG = (os.getenv("ALLOW_DEBUG", "0") == "1") and (not IS_PROD)

# In production we must have an explicit JWT secret. Fail fast if missing.
if IS_PROD:
    if not os.getenv("JWT_SECRET_KEY"):
        print("FATAL: JWT_SECRET_KEY is not set", file=sys.stderr)
        sys.exit(1)

# Determine storage directory. Prefer `DATA_DIR` env var (set to /tmp on Railway),
# otherwise fall back to /tmp by default. For local dev you can set DATA_DIR back
# to a project-local path if desired.
DATA_DIR = Path(os.getenv("DATA_DIR", "/tmp"))

if not DATA_DIR.exists():
    # Try creating DATA_DIR when not running in production (local dev).
    if not IS_PROD:
        DATA_DIR.mkdir(parents=True, exist_ok=True)

USERS_FILE = DATA_DIR / "users.json"
AUDIT_LOG_FILE = DATA_DIR / "audit.log"
INVOICES_FILE = DATA_DIR / "invoices.json"
INVOICE_PDF_DIR = DATA_DIR / "invoice_pdfs"
API_KEYS_FILE = DATA_DIR / "api_keys.json"
SESSIONS_FILE = DATA_DIR / "sessions.json"

# Detect read-only filesystem state so writes can be disabled safely.
READ_ONLY_FS = not os.access(DATA_DIR, os.W_OK)

# Initialize api_keys.json from repo if not present in DATA_DIR (important for Railway deployments)
if not READ_ONLY_FS and not (DATA_DIR / "api_keys.json").exists():
    repo_api_keys = Path(__file__).parent / "api_keys.json"
    if repo_api_keys.exists():
        import shutil
        try:
            shutil.copy(str(repo_api_keys), str(DATA_DIR / "api_keys.json"))
            print(f"[INFO] Initialized api_keys.json from repo to {DATA_DIR}")
        except Exception as e:
            print(f"[WARN] Could not copy api_keys.json: {e}")

# Initialize users.json from repo if not present in DATA_DIR
if not READ_ONLY_FS and not (DATA_DIR / "users.json").exists():
    repo_users = Path(__file__).parent / "users.json"
    if repo_users.exists():
        import shutil
        try:
            shutil.copy(str(repo_users), str(DATA_DIR / "users.json"))
            print(f"[INFO] Initialized users.json from repo to {DATA_DIR}")
        except Exception as e:
            print(f"[WARN] Could not copy users.json: {e}")
            print(f"[INFO] Initialized api_keys.json from repo to {DATA_DIR}")
        except Exception as e:
            print(f"[WARNING] Failed to copy api_keys.json: {e}")

# Simple in-process lock to avoid concurrent writes from multiple requests (single-process only)
_lock = threading.Lock()

# passlib CryptContext configured for bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# bcrypt has a maximum password length of 72 bytes. Enforce server-side to avoid
# subtle truncation or backend errors.
BCRYPT_MAX_BYTES = 72


# JWT / OAuth2 config
# In production `JWT_SECRET_KEY` must be set (checked above). Do not use a hard-coded fallback.
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Brute-force protection
MAX_ATTEMPTS = 5
LOCK_TIME_SECONDS = 15 * 60  # 15 minutes
failed_logins = {}

# Cookie settings for refresh token storage. Force secure cookies in production.
COOKIE_NAME = "refresh_token"
COOKIE_SECURE = IS_PROD
COOKIE_SAMESITE = "lax"


def is_locked(username: str):
    entry = failed_logins.get(username)
    if not entry:
        return False

    attempts, lock_until = entry
    if lock_until and time() < lock_until:
        return True

    # Lock expired → reset
    if lock_until and time() >= lock_until:
        failed_logins.pop(username, None)
    return False


def register_failed_attempt(username: str, ip: str = "-"):
    attempts, lock_until = failed_logins.get(username, (0, None))
    attempts += 1

    if attempts >= MAX_ATTEMPTS:
        lock_until = time() + LOCK_TIME_SECONDS
        # Audit account lock event
        log_event("ACCOUNT_LOCK", username, ip)

    failed_logins[username] = (attempts, lock_until)


# --- PHASE 2: Payment State Machine Helpers ---
def validate_payment_state_transition(current_status: str, new_status: str) -> bool:
    """Validate state machine: created -> pending -> paid -> failed"""
    valid_transitions = {
        "created": ["pending", "paid", "failed"],
        "pending": ["paid", "failed"],
        "paid": [],
        "failed": [],
    }
    return new_status in valid_transitions.get(current_status, [])


def generate_customer_access_link(session_id: str, merchant_id: int, expires_days: int = 7) -> dict:
    """Generate JWT-based customer access link valid for N days."""
    expires = datetime.utcnow() + timedelta(days=expires_days)
    payload = {
        "sub": f"customer_{session_id}",
        "merchant_id": merchant_id,
        "session_id": session_id,
        "exp": expires,
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return {
        "token": token,
        "expires_at": expires.isoformat(),
        "access_url": f"{os.getenv('HOSTED_CHECKOUT_BASE', 'https://api.apiblockchain.io')}/access/{session_id}?token={token}"
    }


def auto_unlock_api_keys(merchant_id: int, session: dict) -> dict:
    """On payment, create API keys for merchant if they don't exist."""
    keys = load_api_keys()
    existing = next((k for k in keys if k.get("merchant_id") == merchant_id), None)
    if existing:
        return existing
    
    import secrets
    raw_suffix = secrets.token_urlsafe(24)
    raw_key = f"sk_test_{raw_suffix}"
    
    new_key = {
        "id": max((k.get("id", 0) for k in keys), default=0) + 1,
        "merchant_id": merchant_id,
        "key": raw_key,
        "label": f"Auto-generated from session {session.get('id')[:8]}",
        "mode": "test",
        "created_at": datetime.utcnow().isoformat(),
    }
    
    keys.append(new_key)
    save_api_keys(keys)
    log_event(f"API_KEY_CREATED merchant_id={merchant_id}", "-", "-")
    return new_key


def clear_attempts(username: str):
    failed_logins.pop(username, None)


def log_event(event: str, username: str = "-", ip: str = "-"):
    timestamp = datetime.now(timezone.utc).isoformat()
    line = f"{timestamp} | {ip} | {username} | {event}\n"
    if READ_ONLY_FS:
        # Fall back to stderr so platform logs still capture the event.
        print(line, file=sys.stderr, end="")
        return

    with _lock:
        with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)


def get_client_ip(request: Request):
    return request.client.host if request.client else "unknown"


class User(BaseModel):
    id: int
    name: str
    # Add early validation for password length (characters). We still enforce
    # bcrypt's 72-byte limit server-side because max_length here counts
    # characters, not bytes.
    password: str = Field(..., min_length=6, max_length=72)
    # Role for role-based access control. Defaults to 'user'. Example: 'admin'
    role: str = "user"


class PublicUser(BaseModel):
    id: int
    name: str
    role: str


class LoginRequest(BaseModel):
    name: str | None = None  # username (can login by username or email)
    email: str | None = None  # email (alternative to username)
    password: str

    def get_identifier(self) -> str:
        """Return either the name or email, whichever is provided."""
        if self.name:
            return self.name
        if self.email:
            return self.email
        raise ValueError("Either 'name' (username) or 'email' must be provided")


class RoleUpdate(BaseModel):
    role: str  # expected values: "admin" or "user"


class StripeWebhookPayload(BaseModel):
    type: str
    data: dict


class OneComWebhookPayload(BaseModel):
    event: str
    reference: str
    amount: float
    currency: str = "USD"
    merchant_id: int
    payload: dict = {}


def _ensure_users_file() -> None:
    if READ_ONLY_FS:
        # Running on read-only filesystem — don't attempt to create files.
        return

    if not USERS_FILE.exists():
        USERS_FILE.write_text("[]", encoding="utf-8")


def _ensure_invoices_file() -> None:
    if READ_ONLY_FS:
        return

    if not INVOICES_FILE.exists():
        INVOICES_FILE.write_text("[]", encoding="utf-8")


def _ensure_api_keys_file() -> None:
    if READ_ONLY_FS:
        return
    if not API_KEYS_FILE.exists():
        API_KEYS_FILE.write_text("[]", encoding="utf-8")


def _ensure_sessions_file() -> None:
    if READ_ONLY_FS:
        return
    if not SESSIONS_FILE.exists():
        SESSIONS_FILE.write_text("[]", encoding="utf-8")


def load_invoices() -> List[dict]:
    _ensure_invoices_file()
    try:
        return json.loads(INVOICES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_invoices(invoices: List[dict]) -> None:
    if READ_ONLY_FS:
        raise RuntimeError("Filesystem is read-only; cannot persist invoices.json")

    with _lock:
        INVOICES_FILE.write_text(json.dumps(invoices, indent=4), encoding="utf-8")


def load_api_keys() -> List[dict]:
    _ensure_api_keys_file()
    try:
        return json.loads(API_KEYS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def load_sessions() -> List[dict]:
    _ensure_sessions_file()
    try:
        return json.loads(SESSIONS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_api_keys(keys: List[dict]) -> None:
    if READ_ONLY_FS:
        raise RuntimeError("Filesystem is read-only; cannot persist api_keys.json")
    with _lock:
        API_KEYS_FILE.write_text(json.dumps(keys, indent=4), encoding="utf-8")


def save_sessions(sessions: List[dict]) -> None:
    if READ_ONLY_FS:
        raise RuntimeError("Filesystem is read-only; cannot persist sessions.json")

    with _lock:
        SESSIONS_FILE.write_text(json.dumps(sessions, indent=4), encoding="utf-8")


def ensure_invoice_pdf_dir() -> None:
    if READ_ONLY_FS:
        return
    if not INVOICE_PDF_DIR.exists():
        INVOICE_PDF_DIR.mkdir(parents=True, exist_ok=True)


def load_users() -> List[dict]:
    _ensure_users_file()
    try:
        return json.loads(USERS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # If the file is corrupted, return empty list (could also raise)
        return []


def _get_db_session():
    try:
        from app.db.session import SessionLocal
        return SessionLocal()
    except Exception:
        return None


def db_get_user(username: str):
    """Return a user dict from the database, or None if DB unavailable or user not found."""
    try:
        from app.models.user import User as ORMUser
        db = _get_db_session()
        if not db:
            return None
        user = db.query(ORMUser).filter(ORMUser.username == username).first()
        if not user:
            return None
        return {"id": user.id, "name": user.username, "password": user.password_hash, "role": user.role}
    except Exception:
        return None


def db_list_users():
    try:
        from app.models.user import User as ORMUser
        db = _get_db_session()
        if not db:
            return None
        rows = db.query(ORMUser).all()
        return [{"id": r.id, "name": r.username, "role": r.role} for r in rows]
    except Exception:
        return None


def db_create_user(user_dict: dict):
    try:
        from app.models.user import User as ORMUser
        db = _get_db_session()
        if not db:
            return None
        u = ORMUser(username=user_dict["name"], password_hash=user_dict["password"], role=user_dict.get("role", "user"))
        db.add(u)
        db.commit()
        db.refresh(u)
        return {"id": u.id, "name": u.username, "role": u.role}
    except Exception:
        return None


def db_delete_user_by_id(user_id: int):
    try:
        from app.models.user import User as ORMUser
        db = _get_db_session()
        if not db:
            return None
        u = db.query(ORMUser).filter(ORMUser.id == user_id).first()
        if not u:
            return None
        out = {"id": u.id, "name": u.username, "role": u.role}
        db.delete(u)
        db.commit()
        return out
    except Exception:
        return None


def db_update_role(user_id: int, role: str):
    try:
        from app.models.user import User as ORMUser
        db = _get_db_session()
        if not db:
            return None
        u = db.query(ORMUser).filter(ORMUser.id == user_id).first()
        if not u:
            return None
        u.role = role
        db.commit()
        return {"id": u.id, "name": u.username, "role": u.role}
    except Exception:
        return None


def save_users(users: List[dict]) -> None:
    if READ_ONLY_FS:
        raise RuntimeError("Filesystem is read-only; cannot persist users.json")

    with _lock:
        USERS_FILE.write_text(json.dumps(users, indent=4), encoding="utf-8")


def _hash_password(password: str) -> str:
    # Use passlib's CryptContext with bcrypt for secure password hashing.
    # passlib handles salts and versioning for bcrypt.
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Return the full payload (claims) so callers can inspect role, sub, etc.
        return payload
    except JWTError:
        return None


def decode_jwt(token: str) -> dict:
    """Decode and verify a JWT, raising HTTPException on failure.

    Use this in production code where you want a verified payload (claims).
    Ensure `JWT_SECRET_KEY` is set in the environment for production deployments.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def get_token_payload(token: str = Depends(oauth2_scheme)) -> dict:
    """FastAPI dependency that returns verified JWT claims for the current request."""
    return decode_jwt(token)


async def get_current_user(request: Request):
    """Resolve the current user from either a Bearer JWT or an API key.

    Order of precedence:
    1. Bearer JWT in `Authorization: Bearer <token>`
    2. API key in `X-API-KEY: <key>` or `Authorization: ApiKey <key>`
    3. Non-production fallback to the first user in `users.json` for local dev convenience
    """
    # Try JWT first (Authorization: Bearer ...)
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth and isinstance(auth, str) and auth.lower().startswith("bearer "):
        token = auth.split(None, 1)[1]
        payload = verify_token(token)
        if payload:
            username = payload.get("sub")
            user = db_get_user(username) or next((u for u in load_users() if u.get("name") == username), None)
            if user:
                return user

    # Next: accept API keys via X-API-KEY header or Authorization: ApiKey <key>
    api_key = request.headers.get("x-api-key") or request.headers.get("X-API-KEY")
    if not api_key and auth and isinstance(auth, str):
        # Accept Authorization: ApiKey <key> or Authorization: Api-Key <key>
        low = auth.lower()
        if low.startswith("apikey ") or low.startswith("api-key ") or low.startswith("api_key "):
            api_key = auth.split(None, 1)[1]

    if api_key:
        try:
            key_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
            # First check file-based api_keys store
            keys = load_api_keys()
            # Primary lookup: SHA256 key hash (preferred)
            row = next((k for k in keys if k.get("key_hash") == key_hash), None)
            # Backward-compatibility: accept raw `key` field if present in the store
            if not row:
                row = next((k for k in keys if k.get("key") == api_key), None)
            if row:
                uid = row.get("user_id")
                # Prefer DB-backed user if available
                try:
                    from app.models.user import User as ORMUser
                    db = _get_db_session()
                    if db:
                        u = db.query(ORMUser).filter(ORMUser.id == uid).first()
                        if u:
                            return {"id": u.id, "name": u.username, "role": u.role}
                except Exception:
                    pass
                # Fallback to file-based users
                users = load_users()
                u = next((x for x in users if x.get("id") == uid), None)
                if u:
                    return u

            # Try DB-backed API keys when available (older deployments)
            try:
                from app.models.api_key import APIKey as ORMAPIKey
                db = _get_db_session()
                if db:
                    row = db.query(ORMAPIKey).filter(ORMAPIKey.key_hash == key_hash).first()
                    if row:
                        try:
                            from app.models.user import User as ORMUser
                            u = db.query(ORMUser).filter(ORMUser.id == row.user_id).first()
                            if u:
                                return {"id": u.id, "name": u.username, "role": u.role}
                        except Exception:
                            pass
            except Exception:
                pass
        except Exception:
            pass

    # Development fallback: allow local dev convenience when not in production
    if not IS_PROD:
        users = load_users()
        if users:
            return users[0]
        return {"id": 0, "name": "dev", "role": "user"}

    # No auth found
    raise HTTPException(status_code=401, detail="Invalid or expired token or API key")


def role_required(*allowed_roles: str):
    """Return a dependency that enforces the current user's role is one of `allowed_roles`.

    Usage: `Depends(role_required("admin", "manager"))` or create aliases like
    `admin_required = role_required("admin")`.
    """
    async def _dependency(current_user: dict = Depends(get_current_user)):
        if current_user.get("role", "user") not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient role privileges")
        return current_user

    return _dependency


# Convenience alias for admin-only endpoints
admin_required = role_required("admin")

# Backwards-compatible name requested in examples
require_admin = admin_required


@app.get("/", response_model=dict)
async def root():
    return {"message": "API is running 🚀"}


@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    return {"status": "ok"}


@app.get("/users", response_model=List[PublicUser])
async def list_users(current_user: dict = Depends(get_current_user)):
    users = db_list_users()
    if users is None:
        users = load_users()
    # Hide password hashes from responses
    return [{"id": u["id"], "name": u["name"], "role": u.get("role", "user")} for u in users]


@app.get("/users/{user_id}", response_model=PublicUser)
async def get_user(user_id: int, current_user: dict = Depends(get_current_user)):
    """Return a single public user by id. 404 if not found."""
    users = db_list_users()
    if users is None:
        users = load_users()
    user = next((u for u in users if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user["id"], "name": user["name"], "role": user.get("role", "user")}


@app.post("/users", response_model=PublicUser, status_code=201)
async def add_user(user: User, admin: dict = Depends(require_admin)):
    # Enforce bcrypt byte-length limit on password (UTF-8 bytes)
    pw_bytes = user.password.encode("utf-8")
    if len(pw_bytes) > BCRYPT_MAX_BYTES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Password is too long: bcrypt limits passwords to {BCRYPT_MAX_BYTES} bytes when encoded as UTF-8. "
                "Please choose a shorter password."
            ),
        )

    try:
        hashed = _hash_password(user.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Error processing password")

    # Try to create user in DB first
    created = db_create_user({"name": user.name, "password": hashed, "role": user.role})
    if created:
        return {"id": created["id"], "name": created["name"], "role": created.get("role", "user")}

    # Fallback to file-based store
    users = load_users()
    if any(u["id"] == user.id for u in users):
        raise HTTPException(status_code=400, detail="User id already exists")
    if any(u["name"] == user.name for u in users):
        raise HTTPException(status_code=400, detail="User name already exists")

    new_user = {"id": user.id, "name": user.name, "password": hashed, "role": user.role}
    users.append(new_user)
    save_users(users)
    return {"id": new_user["id"], "name": new_user["name"], "role": new_user.get("role", "user")}


@app.post("/login")
async def login_for_access_token(
    request: Request,
    response: Response,
    login: LoginRequest = Body(...)
):
    # Get the identifier (username or email, whichever is provided)
    try:
        identifier = login.get_identifier()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if is_locked(identifier):
        raise HTTPException(
            status_code=403,
            detail="Account temporarily locked due to too many failed login attempts. Try again later."
        )

    ip = get_client_ip(request)

    users = load_users()
    # Search by username or email
    user = None
    if login.name:
        user = next((u for u in users if u["name"] == login.name), None)
    elif login.email:
        user = next((u for u in users if u.get("email") == login.email), None)

    stored_pw = user.get("password") if user else None
    valid = False
    if stored_pw and isinstance(stored_pw, str) and stored_pw.startswith("sha256$"):
        try:
            import hashlib as _hl
            valid = _hl.sha256(login.password.encode("utf-8")).hexdigest() == stored_pw.split("sha256$", 1)[1]
        except Exception:
            valid = False
    else:
        try:
            valid = bool(stored_pw and pwd_context.verify(login.password, stored_pw))
        except Exception:
            valid = False

    if not user or not valid:
        log_event("LOGIN_FAIL", identifier, ip)
        register_failed_attempt(identifier)
        raise HTTPException(status_code=401, detail="Invalid username/email or password")

    clear_attempts(identifier)

    access_token = create_access_token(
        data={"sub": user["name"], "role": user.get("role", "user")}
    )
    refresh_token = create_refresh_token(
        data={"sub": user["name"], "role": user.get("role", "user")}
    )

    # 🔐 Store refresh token in HttpOnly cookie
    response.set_cookie(
        key=COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/refresh",
    )

    # Audit successful login
    log_event("LOGIN_SUCCESS", user["name"], ip)

    # Return canonical auth response including merchant identity
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "merchant_id": user.get("id"),
        "email": user.get("email") if isinstance(user, dict) else None,
    }


@app.post("/forgot_password")
async def forgot_password(request: Request, payload: dict = Body(...)):
    """Development-only password reset endpoint.

    For local development this endpoint will reset the user's password
    to a new randomly-generated temporary password and return it in the
    JSON response so the developer can sign in. This endpoint is
    explicitly disabled in production deployments.
    """
    if IS_PROD:
        raise HTTPException(status_code=403, detail="Not allowed in production")

    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Missing 'name' field")

    # Optional: allow caller to specify an explicit password to set (dev only)
    set_to = payload.get("set_to")

    users = load_users()
    user = next((u for u in users if u.get("name") == name), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    import hashlib as _hl

    if set_to:
        # Developer explicitly provided a password — store as sha256$ for quick dev logins
        user["password"] = "sha256$" + _hl.sha256(str(set_to).encode("utf-8")).hexdigest()
        save_users(users)
        ip = get_client_ip(request)
        log_event("PASSWORD_SET", name, ip)
        return {"detail": "password set (dev)", "password": "(hidden)"}

    # Generate a temporary password and store it as a sha256$ entry
    # (login endpoint supports sha256$ entries for dev convenience).
    import secrets
    temp_pw = secrets.token_urlsafe(8) + "A1!"
    user["password"] = "sha256$" + _hl.sha256(temp_pw.encode("utf-8")).hexdigest()
    save_users(users)

    ip = get_client_ip(request)
    log_event("PASSWORD_RESET", name, ip)

    return {"detail": "password reset", "password": temp_pw}


@app.post("/refresh")
async def refresh_access_token(request: Request):
    ip = get_client_ip(request)
    refresh_token = request.cookies.get(COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token cookie")

    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    users = load_users()
    user = next((u for u in users if u["name"] == username), None)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    new_access_token = create_access_token(
        data={"sub": username, "role": role or user.get("role", "user")}
    )

    return {"access_token": new_access_token, "token_type": "bearer"}


@app.get("/protected")
async def protected_route(token: str = Depends(oauth2_scheme)):
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    username = payload.get("sub")
    role = payload.get("role", "user")
    return {"message": f"Hello {username} (role={role}), you have access!"}


@app.delete("/users/{user_id}", response_model=PublicUser)
async def delete_user(user_id: int, admin: dict = Depends(require_admin)):
    """Admin-only: delete a user by id and return the deleted user's public info."""
    # Try DB delete first
    db_removed = db_delete_user_by_id(user_id)
    if db_removed:
        log_event(f"DELETE_USER id={user_id}", admin["name"], "-")
        return db_removed

    users = load_users()
    idx = next((i for i, u in enumerate(users) if u["id"] == user_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="User not found")

    removed = users.pop(idx)
    save_users(users)

    # Audit admin deletion
    log_event(f"DELETE_USER id={user_id}", admin["name"], "-")

    return {"id": removed["id"], "name": removed["name"], "role": removed.get("role", "user")}


# --- Invoice PDF endpoint (simple generator) ---
from typing import Optional
import io
import logging
from fpdf import FPDF


class InvoicePDFRequest(BaseModel):
    seller: Optional[str] = "Example Seller"
    buyer: Optional[str] = "Example Buyer"
    invoice_number: Optional[str] = "INV-TEST-001"
    date: Optional[str] = datetime.now(timezone.utc).date().isoformat()
    description: Optional[str] = "Service"
    amount: Optional[float] = 100.0
    payment_system: Optional[str] = "web2"  # 'web2' or 'web3'
    blockchain_tx_id: Optional[str] = None


class InvoiceCreate(BaseModel):
    seller_name: str
    seller_vat: Optional[str] = None
    buyer_name: str
    buyer_vat: Optional[str] = None
    invoice_number: Optional[str] = None
    order_number: Optional[str] = None
    date_issued: Optional[str] = Field(default_factory=lambda: datetime.now(timezone.utc).date().isoformat())
    items: Optional[List[dict]] = []
    payment_system: Optional[str] = "web2"
    blockchain_tx_id: Optional[str] = None


class InvoiceOut(BaseModel):
    id: int
    invoice_number: str
    order_number: Optional[str] = None
    seller_name: str
    buyer_name: str
    subtotal: float
    vat_amount: float
    total: float
    payment_system: Optional[str]
    blockchain_tx_id: Optional[str]
    pdf_url: Optional[str] = None


def render_invoice_pdf(data: InvoicePDFRequest) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=14)

    pdf.cell(0, 10, f"Invoice {data.invoice_number}", ln=True, align="C")
    pdf.ln(6)

    pdf.set_font("Arial", size=12)
    pdf.cell(0, 8, f"Seller: {data.seller}", ln=True)
    pdf.cell(0, 8, f"Buyer: {data.buyer}", ln=True)
    pdf.cell(0, 8, f"Date: {data.date}", ln=True)
    pdf.ln(6)

    pdf.cell(0, 8, f"Description: {data.description}", ln=True)
    pdf.cell(0, 8, f"Amount: EUR {data.amount:.2f}", ln=True)
    pdf.ln(6)

    pdf.cell(0, 8, f"Payment system: {data.payment_system}", ln=True)
    if data.payment_system == "web3" and data.blockchain_tx_id:
        pdf.cell(0, 8, f"Blockchain TX ID: {data.blockchain_tx_id}", ln=True)

    pdf.ln(10)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 6, "This PDF was generated by the API for testing Web2 vs Web3 invoice rendering.")

    # fpdf2: use `output(dest='S')` to get the PDF as a string, then encode to bytes
    pdf_str = pdf.output(dest='S')
    # fpdf2 uses latin-1 encoding for PDF bytes
    # pdf.output may return `str`, `bytes` or `bytearray` depending on fpdf2 version.
    if isinstance(pdf_str, (bytes, bytearray)):
        return bytes(pdf_str)
    return pdf_str.encode('latin-1')


def _compute_invoice_totals(items: List[dict]) -> tuple:
    # items: each item should have qty, unit_price, vat_rate
    subtotal = 0.0
    vat_total = 0.0
    for it in items:
        qty = float(it.get("qty") or it.get("quantity") or 1)
        price = float(it.get("unit_price") or it.get("price") or 0)
        rate = float(it.get("vat_rate") or it.get("vat") or 0)
        line = qty * price
        subtotal += line
        vat_total += line * (rate / 100.0)

    total = subtotal + vat_total
    return round(subtotal, 2), round(vat_total, 2), round(total, 2)


@app.post("/invoice/pdf")
async def invoice_pdf(req: InvoicePDFRequest):
    """Generate an invoice PDF. Set `payment_system` to 'web2' or 'web3'.

    For `web3`, include `blockchain_tx_id` to display the on-chain reference.
    """
    try:
        pdf_bytes = render_invoice_pdf(req)
        return Response(content=pdf_bytes, media_type="application/pdf")
    except Exception as e:
        # Log full exception with traceback so it's visible in container logs
        logger = logging.getLogger("uvicorn.error")
        logger.exception("Error generating invoice PDF")
        # Return sanitized error to client
        raise HTTPException(status_code=500, detail="Internal server error while generating PDF")


@app.post("/invoices", response_model=InvoiceOut, status_code=201)
async def create_invoice(payload: InvoiceCreate, current_user: dict = Depends(get_current_user)):
    """Create and persist an invoice. Returns invoice metadata and PDF URL when available."""
    # compute totals
    items = payload.items or []
    subtotal, vat_total, total = _compute_invoice_totals(items)

    invoices = load_invoices()
    next_id = (max((inv.get("id", 0) for inv in invoices), default=0) + 1)

    invoice_number = payload.invoice_number or f"INV-{next_id:06d}"

    inv = {
        "id": next_id,
        "invoice_number": invoice_number,
        "order_number": payload.order_number,
        "seller_name": payload.seller_name,
        "seller_vat": payload.seller_vat,
        "buyer_name": payload.buyer_name,
        "buyer_vat": payload.buyer_vat,
        "date_issued": payload.date_issued,
        "items": items,
        "subtotal": subtotal,
        "vat_amount": vat_total,
        "total": total,
        "payment_system": payload.payment_system,
        "blockchain_tx_id": payload.blockchain_tx_id,
        "created_by": current_user.get("name"),
    }

    invoices.append(inv)
    try:
        save_invoices(invoices)
    except RuntimeError:
        # Filesystem read-only: continue without persistence (in-memory only)
        pass

    # Generate and store PDF if possible
    pdf_url = None
    try:
        pdf_req = InvoicePDFRequest(
            seller=inv["seller_name"],
            buyer=inv["buyer_name"],
            invoice_number=inv["invoice_number"],
            date=inv.get("date_issued"),
            description=payload.items[0].get("description") if payload.items else "",
            amount=inv["total"],
            payment_system=inv.get("payment_system", "web2"),
            blockchain_tx_id=inv.get("blockchain_tx_id"),
        )

        pdf_bytes = render_invoice_pdf(pdf_req)
        ensure_invoice_pdf_dir()
        if not READ_ONLY_FS and INVOICE_PDF_DIR.exists():
            pdf_path = INVOICE_PDF_DIR / f"invoice-{next_id}.pdf"
            pdf_path.write_bytes(pdf_bytes)
            pdf_url = str(pdf_path)
    except Exception:
        pdf_url = None

    inv["pdf_url"] = pdf_url

    return InvoiceOut(
        id=inv["id"],
        invoice_number=inv["invoice_number"],
        order_number=inv.get("order_number"),
        seller_name=inv["seller_name"],
        buyer_name=inv["buyer_name"],
        subtotal=inv["subtotal"],
        vat_amount=inv["vat_amount"],
        total=inv["total"],
        payment_system=inv.get("payment_system"),
        blockchain_tx_id=inv.get("blockchain_tx_id"),
        pdf_url=inv.get("pdf_url"),
    )


@app.get("/invoices", response_model=List[InvoiceOut])
async def list_invoices(current_user: dict = Depends(get_current_user)):
    invoices = load_invoices()
    return [InvoiceOut(**{
        "id": inv.get("id"),
        "invoice_number": inv.get("invoice_number"),
        "order_number": inv.get("order_number"),
        "seller_name": inv.get("seller_name"),
        "buyer_name": inv.get("buyer_name"),
        "subtotal": inv.get("subtotal", 0),
        "vat_amount": inv.get("vat_amount", 0),
        "total": inv.get("total", 0),
        "payment_system": inv.get("payment_system"),
        "blockchain_tx_id": inv.get("blockchain_tx_id"),
        "pdf_url": inv.get("pdf_url"),
    }) for inv in invoices]


@app.get("/merchant/usage")
async def merchant_usage(request: Request):
    """Return simple usage statistics for the current merchant/user.

    If an Authorization bearer token is provided it will be used to resolve the
    current user. In non-production environments, if no valid token is present
    a fallback user from `users.json` will be used to make local development
    and the AuthGuard easier to test.
    """
    # Try to resolve user from Authorization header first
    current_user = None
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        token = auth.split(None, 1)[1]
        payload = verify_token(token)
        if payload:
            username = payload.get("sub")
            # Prefer DB-backed user when available
            current_user = db_get_user(username) or next((u for u in load_users() if u.get("name") == username), None)

    # Fallback to a local user in non-production for convenience
    if current_user is None:
        if IS_PROD:
            raise HTTPException(status_code=401, detail="Unauthorized")
        users = load_users()
        current_user = users[0] if users else {"id": 0, "name": "dev", "role": "user"}
    """Return simple usage statistics for the current merchant/user.

    Aggregates invoices created by the current user (or matching `merchant_id` when present).
    """
    invoices = load_invoices()

    merchant_name = current_user.get("name")
    merchant_id = current_user.get("id")

    # Match either by `created_by` (legacy) or explicit `merchant_id` field
    my_invoices = [
        inv for inv in invoices
        if (inv.get("created_by") == merchant_name) or (merchant_id is not None and inv.get("merchant_id") == merchant_id)
    ]

    total_invoices = len(my_invoices)
    web2_invoices = [i for i in my_invoices if (i.get("payment_system") or "web2") == "web2"]
    web3_invoices = [i for i in my_invoices if i.get("payment_system") == "web3"]

    def _sum_total(lst):
        try:
            return round(sum(float(i.get("total", 0) or 0) for i in lst), 2)
        except Exception:
            return 0.0

    web2_total = _sum_total(web2_invoices)
    web3_total = _sum_total(web3_invoices)
    total_amount = _sum_total(my_invoices)

    return {
        "total_invoices": total_invoices,
        "web2_count": len(web2_invoices),
        "web3_count": len(web3_invoices),
        "web2_total": web2_total,
        "web3_total": web3_total,
        "total_amount": total_amount,
    }


@app.get("/merchant/me")
async def merchant_me(current_user: dict = Depends(get_current_user)):
    """Return merchant identity info (id, name, email if present)."""
    return {"id": current_user.get("id"), "name": current_user.get("name"), "email": current_user.get("email")}


class APIKeyCreate(BaseModel):
    label: str = None
    mode: str = "live"  # 'live' or 'test'


@app.get("/api-keys")
async def list_api_keys(current_user: dict = Depends(get_current_user)):
    """List API keys for the current user (does NOT return raw key material)."""
    keys = load_api_keys()
    my = [k for k in keys if k.get("merchant_id") == current_user.get("id") or k.get("user_id") == current_user.get("id")]

    def mask_key(raw: str | None) -> str | None:
        if not raw:
            return None
        # preserve prefix and last 4 chars
        for p in ("sk_live_", "sk_test_"):
            if raw.startswith(p):
                return f"{p}****{raw[-4:]}"
        # generic mask
        return f"****{raw[-4:]}"

    # Return safe fields including masked key
    return [{
        "id": k.get("id"),
        "label": k.get("label"),
        "mode": k.get("mode"),
        "created_at": k.get("created_at"),
        "key_masked": mask_key(k.get("key"))
    } for k in my]


@app.post("/api-keys")
async def create_api_key(payload: APIKeyCreate, current_user: dict = Depends(get_current_user)):
    """Create a new API key for the current user and return the raw key once.

    Keys are prefixed with `sk_test_` or `sk_live_`. We persist the raw key (masked in listings),
    along with `merchant_id`, `mode` and `created_at` as requested.
    """
    if READ_ONLY_FS:
        raise HTTPException(status_code=500, detail="Storage is read-only; cannot create API keys")
    import secrets
    mode = (payload.mode or "live").lower()
    if mode not in ("live", "test"):
        raise HTTPException(status_code=400, detail="mode must be 'live' or 'test'")

    prefix = "sk_live_" if mode == "live" else "sk_test_"
    raw_suffix = secrets.token_urlsafe(24)
    raw = f"{prefix}{raw_suffix}"

    keys = load_api_keys()
    next_id = (max((k.get("id", 0) for k in keys), default=0) + 1)
    now = datetime.now(timezone.utc).isoformat()

    # Persist the raw key and merchant association
    new = {
        "id": next_id,
        "user_id": current_user.get("id"),
        "merchant_id": current_user.get("id"),
        "key": raw,
        "label": payload.label,
        "mode": mode,
        "created_at": now,
    }
    keys.append(new)
    save_api_keys(keys)

    # Return raw key once to user
    return {"id": next_id, "key": raw, "label": payload.label, "mode": mode, "created_at": now}


@app.delete("/api-keys/{key_id}")
async def revoke_api_key(key_id: int, current_user: dict = Depends(get_current_user)):
    """Revoke (delete) an API key owned by the current user."""
    if READ_ONLY_FS:
        raise HTTPException(status_code=500, detail="Storage is read-only; cannot delete API keys")
    keys = load_api_keys()
    idx = next((i for i, k in enumerate(keys) if k.get("id") == key_id and k.get("user_id") == current_user.get("id")), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="API key not found")
    removed = keys.pop(idx)
    save_api_keys(keys)
    return {"ok": True, "id": removed.get("id")}


@app.get("/debug/invoices_file")
async def debug_invoices_file():
    """Debug endpoint: return the configured invoices file path and current content."""
    raise HTTPException(status_code=404, detail="Not found")


@app.post("/debug/add_invoice")
async def debug_add_invoice(payload: dict = Body(...)):
    """Debug helper: append an invoice dict to the invoices store used by the app."""
    raise HTTPException(status_code=404, detail="Not found")


@app.get('/debug/users')
async def debug_users():
    raise HTTPException(status_code=404, detail="Not found")


@app.post('/debug/add_user')
async def debug_add_user(payload: dict = Body(...)):
    """Debug helper: add a plaintext-password user to the app's users.json (dev only)."""
    # Only allow this in non-production when explicitly enabled via ALLOW_DEBUG
    if IS_PROD or not ALLOW_DEBUG:
        raise HTTPException(status_code=404, detail="Not found")

    try:
        name = payload.get('name')
        password = payload.get('password')
        role = payload.get('role', 'user')
        if not name or not password:
            raise HTTPException(status_code=400, detail="name and password required")

        users = load_users()
        if any(u.get('name') == name for u in users):
            return {"ok": False, "reason": "exists"}

        # Try to hash with bcrypt; fall back to a debug sha256 prefix if hashing fails
        try:
            pw_bytes = password.encode('utf-8')
            if len(pw_bytes) > BCRYPT_MAX_BYTES:
                raise HTTPException(status_code=400, detail="Password too long for bcrypt")
            hashed = _hash_password(password)
        except HTTPException:
            raise
        except Exception:
            import hashlib as _hl
            hashed = "sha256$" + _hl.sha256(password.encode("utf-8")).hexdigest()

        next_id = (max((u.get('id', 0) for u in users), default=0) + 1)
        users.append({"id": next_id, "name": name, "password": hashed, "role": role})
        try:
            save_users(users)
        except Exception:
            # Best-effort: if saving fails on this host, still return success for testing
            pass

        log_event("DEBUG_ADD_USER", name, "-")
        return {"ok": True, "id": next_id, "name": name}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/debug/add_api_key')
async def debug_add_api_key(payload: dict = Body(...)):
    """Debug helper: create an API key for a given user id and return the raw key (dev only)."""
    raise HTTPException(status_code=404, detail="Not found")


@app.get("/invoices/{invoice_id}", response_model=InvoiceOut)
async def get_invoice(invoice_id: int, current_user: dict = Depends(get_current_user)):
    invoices = load_invoices()
    inv = next((i for i in invoices if i.get("id") == invoice_id), None)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return InvoiceOut(**{
        "id": inv.get("id"),
        "invoice_number": inv.get("invoice_number"),
        "order_number": inv.get("order_number"),
        "seller_name": inv.get("seller_name"),
        "buyer_name": inv.get("buyer_name"),
        "subtotal": inv.get("subtotal", 0),
        "vat_amount": inv.get("vat_amount", 0),
        "total": inv.get("total", 0),
        "payment_system": inv.get("payment_system"),
        "blockchain_tx_id": inv.get("blockchain_tx_id"),
        "pdf_url": inv.get("pdf_url"),
    })


@app.get("/invoices/{invoice_id}/pdf")
async def download_invoice_pdf(invoice_id: int, current_user: dict = Depends(get_current_user)):
    invoices = load_invoices()
    inv = next((i for i in invoices if i.get("id") == invoice_id), None)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # If a stored pdf exists, return it
    if inv.get("pdf_url"):
        try:
            path = Path(inv.get("pdf_url"))
            if path.exists():
                return Response(content=path.read_bytes(), media_type="application/pdf")
        except Exception:
            pass

    # Otherwise generate on-the-fly
    pdf_req = InvoicePDFRequest(
        seller=inv.get("seller_name"),
        buyer=inv.get("buyer_name"),
        invoice_number=inv.get("invoice_number"),
        date=inv.get("date_issued"),
        description=inv.get("items", [{}])[0].get("description") if inv.get("items") else "",
        amount=inv.get("total", 0),
        payment_system=inv.get("payment_system"),
        blockchain_tx_id=inv.get("blockchain_tx_id"),
    )
    pdf_bytes = render_invoice_pdf(pdf_req)
    return Response(content=pdf_bytes, media_type="application/pdf")


@app.post("/calculate-vat")
async def vat(data: dict = Body(...)):
    """Calculate VAT for a simple invoice-like payload.

    Expects JSON body with `items` list where each item has `qty` (or `quantity`),
    `unit_price` (or `price`) and `vat_rate`. Returns JSON with `subtotal`,
    `vat_total`, and `total` as strings.
    """
    try:
        # Import lazily to avoid importing SQLAlchemy at module import time
        from vat_engine import calculate_vat
        return calculate_vat(data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/pdf-hash")
async def pdf_hash(file: UploadFile = File(...)):
    """Accept a PDF upload and return its SHA256 hash."""
    if file.content_type and not file.content_type.startswith("application/pdf"):
        raise HTTPException(status_code=400, detail="Expected application/pdf file")
    try:
        data = await file.read()
        h = hashlib.sha256(data).hexdigest()
        return {"filename": file.filename, "sha256": h}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/users", response_model=List[PublicUser])
async def admin_list_users(admin: dict = Depends(require_admin)):
    """Admin-only: return all users (public view)."""
    users = db_list_users()
    if users is None:
        users = load_users()
    return [{"id": u["id"], "name": u["name"], "role": u.get("role", "user")} for u in users]


@app.get("/admin/logs")
async def get_audit_logs(admin: dict = Depends(require_admin)):
    """Admin-only: return the most recent audit log lines (up to 100)."""
    if not AUDIT_LOG_FILE.exists():
        return {"count": 0, "logs": []}

    lines = AUDIT_LOG_FILE.read_text(encoding="utf-8").splitlines()
    return {
        "count": len(lines),
        "logs": lines[-100:]
    }


@app.get("/admin/users/{user_id}", response_model=PublicUser)
async def admin_get_user(user_id: int, admin: dict = Depends(require_admin)):
    """Admin-only: return a single user by id."""
    users = db_list_users()
    if users is None:
        users = load_users()
    user = next((u for u in users if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user["id"], "name": user["name"], "role": user.get("role", "user")}


@app.delete("/admin/users/{user_id}", response_model=PublicUser)
async def admin_delete_user(user_id: int, admin: dict = Depends(require_admin)):
    """Admin-only: delete a user by id and return the deleted user's public info."""
    db_removed = db_delete_user_by_id(user_id)
    if db_removed:
        return db_removed

    users = load_users()
    idx = next((i for i, u in enumerate(users) if u["id"] == user_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="User not found")

    removed = users.pop(idx)
    save_users(users)

    return {"id": removed["id"], "name": removed["name"], "role": removed.get("role", "user")}


@app.patch("/admin/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    payload: RoleUpdate,
    current_user: dict = Depends(require_admin),
):
    if payload.role not in ["admin", "user"]:
        raise HTTPException(status_code=400, detail="Role must be admin or user")

    # Try DB update first
    updated = db_update_role(user_id, payload.role)
    if updated:
        log_event(f"ROLE_CHANGE id={user_id} → {payload.role}", current_user["name"], "-")
        return {"message": f"User {updated['name']} role updated to {payload.role}"}

    users = load_users()
    for u in users:
        if u["id"] == user_id:
            u["role"] = payload.role
            save_users(users)

            # Audit role change
            log_event(f"ROLE_CHANGE id={user_id} → {payload.role}", current_user["name"], "-")

            return {"message": f"User {u['name']} role updated to {payload.role}"}

    raise HTTPException(status_code=404, detail="User not found")


# AWS Lambda adapter (Mangum). If Mangum isn't installed this will silently
# leave `handler` as None so local uvicorn still works.
try:
    from mangum import Mangum
    handler = Mangum(app)
except Exception:
    handler = None


# --- Simple checkout endpoint for plugin integration (persistence-only) ---
@app.post("/checkout")
def checkout(
    payload: dict,
    x_api_key: str = Header(None)
):
    # Require API key header
    if not x_api_key:
        return JSONResponse(status_code=401, content={"error": "Missing API key"})

    # Persistence must be available
    if READ_ONLY_FS:
        return JSONResponse(status_code=503, content={"error": "Persistence disabled on this server"})

    # Find key from persistent storage
    try:
        api_keys = load_api_keys()
    except Exception:
        return JSONResponse(status_code=500, content={"error": "Failed to load API keys"})

    key = next((k for k in api_keys if k.get("key") == x_api_key), None)
    # Local dev fallback: allow any key in non-production for quick testing
    if not key and not IS_PROD:
        # Create a temporary key object mapping to merchant_id 1
        key = {"merchant_id": 1, "key": x_api_key, "mode": "test"}
    if not key:
        return JSONResponse(status_code=403, content={"error": "Invalid API key"})

    # Build invoice and persist to invoices.json
    try:
        invoices = load_invoices()
    except Exception:
        return JSONResponse(status_code=500, content={"error": "Failed to load invoices storage"})

    try:
        amount = float(payload.get("amount", 0) or 0)
    except Exception:
        amount = 0.0
    mode = payload.get("mode", "test")

    invoice = {
        "id": str(uuid.uuid4()),
        "merchant_id": key.get("merchant_id"),
        "amount": amount,
        "mode": mode,
        "status": "paid" if mode == "test" else "pending",
        "created_at": datetime.utcnow().isoformat(),
    }

    invoices.append(invoice)

    try:
        save_invoices(invoices)
    except Exception:
        return JSONResponse(status_code=500, content={"error": "Failed to persist invoice"})

    return {"success": True, "invoice": invoice}


# Hosted session creation endpoint used by the plugin to create server-side sessions
@app.post("/create_session")
def create_session(
    payload: dict,
    x_api_key: str = Header(None)
):
    # Require API key header
    if not x_api_key:
        return JSONResponse(status_code=401, content={"error": "Missing API key"})

    if READ_ONLY_FS:
        return JSONResponse(status_code=503, content={"error": "Persistence disabled on this server"})

    try:
        api_keys = load_api_keys()
    except Exception:
        return JSONResponse(status_code=500, content={"error": "Failed to load API keys"})

    key = next((k for k in api_keys if k.get("key") == x_api_key), None)
    if not key and not IS_PROD:
        key = {"merchant_id": 1, "key": x_api_key, "mode": "test"}
    if not key:
        return JSONResponse(status_code=403, content={"error": "Invalid API key"})

    # Prefer DB-backed sessions when available
    db_sessions_available = False
    try:
        from app.db.sessions import create_session as db_create_session
        db_sessions_available = True
    except Exception:
        db_sessions_available = False

    try:
        amount = float(payload.get("amount", 0) or 0)
    except Exception:
        amount = 0.0

    success_url = payload.get("success_url") or payload.get("successUrl") or payload.get("success")
    cancel_url = payload.get("cancel_url") or payload.get("cancelUrl") or payload.get("cancel")
    mode = payload.get("mode", key.get("mode", "test"))

    session_id = str(uuid.uuid4())

    # Build hosted checkout URL. Allow override via HOSTED_CHECKOUT_BASE env var.
    HOSTED_BASE = os.getenv("HOSTED_CHECKOUT_BASE", "https://api.apiblockchain.io")
    session_url = f"{HOSTED_BASE.rstrip('/')}/checkout?session={session_id}"

    session = {
        "id": session_id,
        "merchant_id": key.get("merchant_id"),
        "amount": amount,
        "mode": mode,
        "status": "created",
        "payment_status": "not_started",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "url": session_url,
        "created_at": datetime.utcnow().isoformat(),
        "metadata": {
            "customer_email": payload.get("customer_email"),
            "customer_name": payload.get("customer_name"),
            "webhook_sources": [],
        }
    }

    if db_sessions_available:
        try:
            created = db_create_session(session)
            return {"success": True, "id": created.get("id"), "url": created.get("url"), "session": created}
        except Exception:
            # Fall back to file-based persistence
            pass

    try:
        sessions = load_sessions()
    except Exception:
        return JSONResponse(status_code=500, content={"error": "Failed to load sessions storage"})

    sessions.append(session)

    try:
        save_sessions(sessions)
    except Exception:
        return JSONResponse(status_code=500, content={"error": "Failed to persist session"})

    return {"success": True, "id": session_id, "url": session_url, "session": session}


@app.get("/session/{session_id}")
def get_session(session_id: str):
    # Try DB-backed lookup first
    try:
        from app.db.sessions import get_session as db_get_session
        s = db_get_session(session_id)
        if s:
            return {"success": True, "session": s}
    except Exception:
        pass

    try:
        sessions = load_sessions()
    except Exception:
        return JSONResponse(status_code=500, content={"error": "Failed to load sessions storage"})

    s = next((x for x in sessions if x.get("id") == session_id), None)
    if not s:
        return JSONResponse(status_code=404, content={"error": "Session not found"})
    return {"success": True, "session": s}


@app.get("/checkout")
def hosted_checkout(session: str = None):
        """Hosted checkout page. Renders a simple UI to pay a session.

        Query param: ?session=<session_id>
        """
        if not session:
                return HTMLResponse("<h1>Missing session</h1>", status_code=400)

        # Try DB-backed lookup first
        s = None
        try:
            from app.db.sessions import get_session as db_get_session
            s = db_get_session(session)
        except Exception:
            s = None

        if not s:
            try:
                sessions = load_sessions()
            except Exception:
                return HTMLResponse("<h1>Failed to load sessions</h1>", status_code=500)

            s = next((x for x in sessions if x.get("id") == session), None)
        if not s:
                return HTMLResponse("<h1>Session not found</h1>", status_code=404)

        # Resolve merchant name if available
        merchant_name = None
        try:
                users = load_users()
                u = next((x for x in users if x.get("id") == s.get("merchant_id")), None)
                if u:
                        merchant_name = u.get("name")
        except Exception:
                merchant_name = None

        if not merchant_name:
                merchant_name = f"Merchant {s.get('merchant_id')}"

        amount = float(s.get("amount") or 0)
        success_url = s.get("success_url") or ""
        cancel_url = s.get("cancel_url") or ""

        # Build HTML by concatenation to avoid f-string brace escaping issues
        sess_id_js = json.dumps(s.get('id'))
        success_js = json.dumps(success_url)
        cancel_js = json.dumps(cancel_url)
        merchant_escaped = (merchant_name or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        html = (
            "<!doctype html>"
            "<html>"
            "<head>"
            "<meta charset=\"utf-8\"/>"
            "<title>APIBlockchain Checkout</title>"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>"
            "<style>"
            " :root{--primary:#0b63ff;--bg:#f6f8fb;--text:#071226}"
            " body{font-family:Arial,Helvetica,sans-serif;background:var(--bg);color:var(--text);padding:20px;margin:0;}"
            " .box{max-width:520px;margin:32px auto;background:#fff;padding:20px;border-radius:10px;box-shadow:0 8px 24px rgba(7,18,38,0.06);}"
            " .logo{display:block;margin:0 auto 12px;max-width:160px;}"
            " h2{color:var(--primary);text-align:center;margin:6px 0 12px;}"
            " .amount{font-size:1.25rem;margin:8px 0;}"
            " .actions{margin-top:14px;text-align:center;}"
            " button{background:var(--primary);color:#fff;border:none;border-radius:8px;padding:10px 16px;margin:6px;cursor:pointer;font-weight:600;}"
            " button.secondary{background:#fff;color:var(--primary);border:1px solid #e6e9ef;}"
            " #status{margin-top:12px;text-align:center;color:#093;}"
            " footer{margin-top:18px;font-size:12px;color:#7b8390;text-align:center;}"
            "</style>"
            "</head>"
            "<body>"
            "<div class=\"box\">"
            "<img class=\"logo\" src=\"https://apiblockchain.io/logo.svg\" alt=\"APIBlockchain\"/>"
            "<h2>Checkout</h2>"
            "<p><strong>Merchant:</strong> " + merchant_escaped + "</p>"
            "<p class=\"amount\"><strong>Amount:</strong> $" + f"{amount:.2f}" + "</p>"
            "<div class=\"actions\">"
            "<button id=\"pay-web2\">Pay with Card</button>"
            "<button id=\"pay-web3\" class=\"secondary\">Pay with Crypto</button>"
            "</div>"
            "<div id=\"status\"></div>"
            "<footer><a href=\"https://apiblockchain.io\" target=\"_blank\">Powered by APIBlockchain</a></footer>"
            "<script>"
            "const sessionId = " + sess_id_js + ";"
            "const successUrl = " + success_js + ";"
            "const cancelUrl = " + cancel_js + ";"
            "async function complete(payment_system){"
            "document.getElementById('status').innerText = 'Processing...';"
            "try{"
            "const res = await fetch('/session/' + sessionId + '/complete', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ payment_system }) });"
            "const data = await res.json();"
            "if(!res.ok){ document.getElementById('status').innerText = 'Error: ' + (data.error || res.statusText); return; }"
            "document.getElementById('status').innerText = 'Payment successful';"
            "try{ window.opener && window.opener.postMessage({ type: 'apiblockchain.checkout_complete', sessionId: sessionId }, '*'); }catch(e){}"
            "setTimeout(()=>{ if(successUrl) window.location.href = successUrl; else document.getElementById('status').innerText += ' — You may close this window.'; }, 800);"
            "}catch(e){ document.getElementById('status').innerText = 'Network error'; }"
            "}"
            "document.getElementById('pay-web2').addEventListener('click', ()=> complete('web2'));"
            "document.getElementById('pay-web3').addEventListener('click', ()=> complete('web3'));"
            "</script>"
            "</div>"
            "</body>"
            "</html>"
        )

        return HTMLResponse(html)


@app.post("/session/{session_id}/complete")
def complete_session(session_id: str, payload: dict = Body(...)):
        """Mark session paid, create invoice, persist to `invoices.json` and update session."""
        payment_system = payload.get('payment_system', 'web2')
        blockchain_tx_id = payload.get('blockchain_tx_id')

        if READ_ONLY_FS:
                return JSONResponse(status_code=503, content={"error": "Persistence disabled on this server"})

        # Try DB-backed lookup first
        s = None
        db_available = False
        try:
            from app.db.sessions import get_session as db_get_session, update_session as db_update_session
            db_available = True
            s = db_get_session(session_id)
        except Exception:
            s = None

        if not s:
            try:
                sessions = load_sessions()
            except Exception:
                return JSONResponse(status_code=500, content={"error": "Failed to load sessions storage"})

            s = next((x for x in sessions if x.get('id') == session_id), None)
            if not s:
                return JSONResponse(status_code=404, content={"error": "Session not found"})
        else:
            # s found in DB
            pass

        # ensure we don't double-pay
        if s.get('status') == 'paid':
                return {"success": True, "message": "Already paid"}

        # create invoice
        try:
                invoices = load_invoices()
        except Exception:
                return JSONResponse(status_code=500, content={"error": "Failed to load invoices storage"})

        invoice = {
                'id': str(uuid.uuid4()),
                'merchant_id': s.get('merchant_id'),
                'amount': float(s.get('amount') or 0),
                'mode': s.get('mode', 'test'),
                'status': 'paid',
                'payment_system': payment_system,
                'blockchain_tx_id': blockchain_tx_id,
                'created_at': datetime.utcnow().isoformat(),
        }

        invoices.append(invoice)

        # update session (DB or file)
        if db_available and s and isinstance(s, dict) and s.get('id'):
            try:
                db_update_session(session_id, {
                    'status': 'paid',
                    'paid_at': datetime.utcnow(),
                    'payment_system': payment_system,
                    'blockchain_tx_id': blockchain_tx_id,
                })
            except Exception:
                return JSONResponse(status_code=500, content={"error": "Failed to persist DB session"})
        else:
            s['status'] = 'paid'
            s['paid_at'] = datetime.utcnow().isoformat()
            s['payment_system'] = payment_system
            if blockchain_tx_id:
                s['blockchain_tx_id'] = blockchain_tx_id

            try:
                save_invoices(invoices)
                save_sessions(sessions)
            except Exception:
                return JSONResponse(status_code=500, content={"error": "Failed to persist invoice/session"})

        # simple audit/event
        log_event('SESSION_COMPLETED id=' + session_id, '-', '-')

        return {"success": True, "invoice": invoice, "session": s}


@app.post('/webhooks/stripe')
def webhook_stripe(payload: dict = Body(...), request: Request = None):
    """Stripe webhook: payment_intent.succeeded -> mark session PAID."""
    if READ_ONLY_FS:
        return JSONResponse(status_code=503, content={"error": "Persistence disabled"})
    
    event_type = payload.get('type', '')
    if event_type not in ['payment_intent.succeeded', 'charge.completed']:
        log_event(f'WEBHOOK_STRIPE_IGNORED event_type={event_type}', '-', '-')
        return {"received": True}
    
    intent_data = payload.get('data', {}).get('object', {})
    session_id = intent_data.get('metadata', {}).get('session_id') or intent_data.get('description', '')
    
    if not session_id:
        log_event('WEBHOOK_STRIPE_NO_SESSION_ID', '-', '-')
        return JSONResponse(status_code=400, content={"error": "No session_id in webhook"})
    
    try:
        sessions = load_sessions()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    
    session = next((s for s in sessions if s.get('id') == session_id), None)
    if not session:
        log_event(f'WEBHOOK_STRIPE_SESSION_NOT_FOUND session_id={session_id[:8]}', '-', '-')
        return JSONResponse(status_code=404, content={"error": "Session not found"})
    
    if session.get('status') in ['paid', 'failed']:
        return {"success": True, "message": f"Session already in terminal state: {session.get('status')}"}
    
    if not validate_payment_state_transition(session.get('status', 'created'), 'paid'):
        return JSONResponse(status_code=409, content={"error": "Invalid state transition"})
    
    session['status'] = 'paid'
    session['payment_status'] = 'completed'
    session['paid_at'] = datetime.utcnow().isoformat()
    session['payment_provider'] = 'stripe'
    session['stripe_intent_id'] = intent_data.get('id')
    session['metadata']['webhook_sources'].append('stripe')
    
    try:
        invoices = load_invoices()
    except Exception:
        invoices = []
    
    invoice = {
        'id': str(uuid.uuid4()),
        'session_id': session_id,
        'merchant_id': session.get('merchant_id'),
        'amount': session.get('amount'),
        'mode': session.get('mode', 'test'),
        'status': 'paid',
        'payment_provider': 'stripe',
        'stripe_intent_id': intent_data.get('id'),
        'created_at': datetime.utcnow().isoformat(),
    }
    invoices.append(invoice)
    
    api_key = auto_unlock_api_keys(session.get('merchant_id'), session)
    access_link = generate_customer_access_link(session_id, session.get('merchant_id'))
    
    try:
        save_sessions(sessions)
        save_invoices(invoices)
    except Exception as e:
        log_event(f'WEBHOOK_STRIPE_PERSIST_FAILED {str(e)[:50]}', '-', '-')
        return JSONResponse(status_code=500, content={"error": "Failed to persist"})
    
    log_event(f'WEBHOOK_STRIPE_SUCCESS session_id={session_id[:8]} amount={session.get("amount")}', '-', '-')
    
    return {
        "success": True,
        "session_id": session_id,
        "invoice": invoice,
        "api_key_generated": api_key.get('id'),
        "customer_access": access_link,
    }


@app.post('/webhooks/onecom')
def webhook_onecom(payload: dict = Body(...), request: Request = None):
    """One.com webhook: payment.completed -> mark session PAID."""
    if READ_ONLY_FS:
        return JSONResponse(status_code=503, content={"error": "Persistence disabled"})
    
    event = payload.get('event', '')
    if event != 'payment.completed':
        log_event(f'WEBHOOK_ONECOM_IGNORED event={event}', '-', '-')
        return {"received": True}
    
    session_id = payload.get('reference')
    if not session_id:
        log_event('WEBHOOK_ONECOM_NO_REFERENCE', '-', '-')
        return JSONResponse(status_code=400, content={"error": "No reference (session_id) in webhook"})
    
    try:
        sessions = load_sessions()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    
    session = next((s for s in sessions if s.get('id') == session_id), None)
    if not session:
        log_event(f'WEBHOOK_ONECOM_SESSION_NOT_FOUND session_id={session_id[:8]}', '-', '-')
        return JSONResponse(status_code=404, content={"error": "Session not found"})
    
    if session.get('status') in ['paid', 'failed']:
        return {"success": True, "message": f"Session already in terminal state: {session.get('status')}"}
    
    if not validate_payment_state_transition(session.get('status', 'created'), 'paid'):
        return JSONResponse(status_code=409, content={"error": "Invalid state transition"})
    
    session['status'] = 'paid'
    session['payment_status'] = 'completed'
    session['paid_at'] = datetime.utcnow().isoformat()
    session['payment_provider'] = 'onecom'
    session['onecom_txn_id'] = payload.get('payload', {}).get('txn_id')
    session['metadata']['webhook_sources'].append('onecom')
    
    try:
        invoices = load_invoices()
    except Exception:
        invoices = []
    
    invoice = {
        'id': str(uuid.uuid4()),
        'session_id': session_id,
        'merchant_id': session.get('merchant_id'),
        'amount': payload.get('amount', session.get('amount')),
        'currency': payload.get('currency', 'USD'),
        'mode': session.get('mode', 'test'),
        'status': 'paid',
        'payment_provider': 'onecom',
        'onecom_txn_id': payload.get('payload', {}).get('txn_id'),
        'created_at': datetime.utcnow().isoformat(),
    }
    invoices.append(invoice)
    
    api_key = auto_unlock_api_keys(session.get('merchant_id'), session)
    access_link = generate_customer_access_link(session_id, session.get('merchant_id'))
    
    try:
        save_sessions(sessions)
        save_invoices(invoices)
    except Exception as e:
        log_event(f'WEBHOOK_ONECOM_PERSIST_FAILED {str(e)[:50]}', '-', '-')
        return JSONResponse(status_code=500, content={"error": "Failed to persist"})
    
    log_event(f'WEBHOOK_ONECOM_SUCCESS session_id={session_id[:8]} amount={payload.get("amount")}', '-', '-')
    
    return {
        "success": True,
        "session_id": session_id,
        "invoice": invoice,
        "api_key_generated": api_key.get('id'),
        "customer_access": access_link,
    }


@app.post('/webhooks/web3')
def webhook_web3(payload: dict = Body(...), request: Request = None):
    """Web3 webhook: blockchain payment verification."""
    if READ_ONLY_FS:
        return JSONResponse(status_code=503, content={"error": "Persistence disabled"})
    
    event = payload.get('event', '')
    if event not in ['payment.confirmed', 'transfer.confirmed']:
        log_event(f'WEBHOOK_WEB3_IGNORED event={event}', '-', '-')
        return {"received": True}
    
    session_id = payload.get('session_id')
    if not session_id:
        return JSONResponse(status_code=400, content={"error": "No session_id"})
    
    try:
        sessions = load_sessions()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    
    session = next((s for s in sessions if s.get('id') == session_id), None)
    if not session:
        return JSONResponse(status_code=404, content={"error": "Session not found"})
    
    if session.get('status') in ['paid', 'failed']:
        return {"success": True, "message": f"Already in {session.get('status')}"}
    
    if not validate_payment_state_transition(session.get('status', 'created'), 'paid'):
        return JSONResponse(status_code=409, content={"error": "Invalid state transition"})
    
    session['status'] = 'paid'
    session['payment_status'] = 'completed'
    session['paid_at'] = datetime.utcnow().isoformat()
    session['payment_provider'] = 'web3'
    session['blockchain_tx_id'] = payload.get('blockchain_tx_id')
    session['blockchain_network'] = payload.get('network')
    session['metadata']['webhook_sources'].append('web3')
    
    try:
        invoices = load_invoices()
    except Exception:
        invoices = []
    
    invoice = {
        'id': str(uuid.uuid4()),
        'session_id': session_id,
        'merchant_id': session.get('merchant_id'),
        'amount': payload.get('amount', session.get('amount')),
        'mode': session.get('mode', 'test'),
        'status': 'paid',
        'payment_provider': 'web3',
        'blockchain_tx_id': payload.get('blockchain_tx_id'),
        'blockchain_network': payload.get('network'),
        'created_at': datetime.utcnow().isoformat(),
    }
    invoices.append(invoice)
    
    api_key = auto_unlock_api_keys(session.get('merchant_id'), session)
    access_link = generate_customer_access_link(session_id, session.get('merchant_id'))
    
    try:
        save_sessions(sessions)
        save_invoices(invoices)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    
    log_event(f'WEBHOOK_WEB3_SUCCESS session_id={session_id[:8]} tx_id={payload.get("blockchain_tx_id")[:16]}', '-', '-')
    
    return {
        "success": True,
        "session_id": session_id,
        "invoice": invoice,
        "api_key_generated": api_key.get('id'),
        "customer_access": access_link,
        "blockchain_tx": payload.get('blockchain_tx_id'),
    }


@app.get('/session/{session_id}/status')
def get_session_status(session_id: str):
    """Public endpoint to check session payment status."""
    try:
        sessions = load_sessions()
    except Exception:
        return JSONResponse(status_code=500, content={"error": "Failed to load sessions"})
    
    session = next((s for s in sessions if s.get('id') == session_id), None)
    if not session:
        return JSONResponse(status_code=404, content={"error": "Session not found"})
    
    return {
        "session_id": session_id,
        "status": session.get('status'),
        "payment_status": session.get('payment_status'),
        "payment_provider": session.get('payment_provider'),
        "paid_at": session.get('paid_at'),
        "amount": session.get('amount'),
        "created_at": session.get('created_at'),
    }
