from fastapi import FastAPI, HTTPException, Body, Response, Request, UploadFile, File
import hashlib
from pydantic import BaseModel, Field
from typing import List
import json
from pathlib import Path
import os
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from time import time
from jose import jwt, JWTError
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
import threading

app = FastAPI(title="Secure User API")

# Determine storage directory. Use /tmp when running in AWS Lambda (writable),
# otherwise keep the file next to the module for local dev.
if os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
    DATA_DIR = Path(os.getenv("DATA_DIR", "/tmp"))
else:
    DATA_DIR = Path(__file__).parent

USERS_FILE = DATA_DIR / "users.json"
AUDIT_LOG_FILE = DATA_DIR / "audit.log"

# Simple in-process lock to avoid concurrent writes from multiple requests (single-process only)
_lock = threading.Lock()

# passlib CryptContext configured for bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# bcrypt has a maximum password length of 72 bytes. Enforce server-side to avoid
# subtle truncation or backend errors.
BCRYPT_MAX_BYTES = 72


# JWT / OAuth2 config
# Prefer a secret from the environment for production. Fallback only for dev/testing.
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "supersecretkey123")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Brute-force protection
MAX_ATTEMPTS = 5
LOCK_TIME_SECONDS = 15 * 60  # 15 minutes
failed_logins = {}

# Cookie settings for refresh token storage (change for production)
COOKIE_NAME = "refresh_token"
COOKIE_SECURE = False  # Set True in production (HTTPS only)
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


def clear_attempts(username: str):
    failed_logins.pop(username, None)


def log_event(event: str, username: str = "-", ip: str = "-"):
    timestamp = datetime.now(timezone.utc).isoformat()
    line = f"{timestamp} | {ip} | {username} | {event}\n"
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
    name: str
    password: str


class RoleUpdate(BaseModel):
    role: str  # expected values: "admin" or "user"


def _ensure_users_file() -> None:
    if not USERS_FILE.exists():
        USERS_FILE.write_text("[]", encoding="utf-8")


def load_users() -> List[dict]:
    _ensure_users_file()
    try:
        return json.loads(USERS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # If the file is corrupted, return empty list (could also raise)
        return []


def save_users(users: List[dict]) -> None:
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


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Resolve the current user from the OAuth2 token."""
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    username = payload.get("sub")
    users = load_users()
    user = next((u for u in users if u["name"] == username), None)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


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
    users = load_users()
    # Hide password hashes from responses
    return [{"id": u["id"], "name": u["name"], "role": u.get("role", "user")} for u in users]


@app.get("/users/{user_id}", response_model=PublicUser)
async def get_user(user_id: int, current_user: dict = Depends(get_current_user)):
    """Return a single public user by id. 404 if not found."""
    users = load_users()
    user = next((u for u in users if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user["id"], "name": user["name"], "role": user.get("role", "user")}


@app.post("/users", response_model=PublicUser, status_code=201)
async def add_user(user: User, admin: dict = Depends(require_admin)):
    users = load_users()

    if any(u["id"] == user.id for u in users):
        raise HTTPException(status_code=400, detail="User id already exists")
    if any(u["name"] == user.name for u in users):
        raise HTTPException(status_code=400, detail="User name already exists")

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
        # Known validation error from bcrypt (e.g. password too long)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        # Unexpected error during hashing; don't leak internals
        raise HTTPException(status_code=500, detail="Error processing password")

    new_user = {
        "id": user.id,
        "name": user.name,
        "password": hashed,
        "role": user.role,
    }

    users.append(new_user)
    save_users(users)

    return {"id": new_user["id"], "name": new_user["name"], "role": new_user.get("role", "user")}


@app.post("/login")
async def login_for_access_token(
    request: Request,
    response: Response,
    login: LoginRequest = Body(...)
):
    if is_locked(login.name):
        raise HTTPException(
            status_code=403,
            detail="Account temporarily locked due to too many failed login attempts. Try again later."
        )

    ip = get_client_ip(request)

    users = load_users()
    user = next((u for u in users if u["name"] == login.name), None)

    if not user or not pwd_context.verify(login.password, user["password"]):
        log_event("LOGIN_FAIL", login.name, ip)
        register_failed_attempt(login.name)
        raise HTTPException(status_code=401, detail="Invalid username or password")

    clear_attempts(login.name)

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

    return {"access_token": access_token, "token_type": "bearer"}


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

    bio = io.BytesIO()
    pdf.output(bio)
    return bio.getvalue()


@app.post("/invoice/pdf")
async def invoice_pdf(req: InvoicePDFRequest):
    """Generate an invoice PDF. Set `payment_system` to 'web2' or 'web3'.

    For `web3`, include `blockchain_tx_id` to display the on-chain reference.
    """
    pdf_bytes = render_invoice_pdf(req)
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
    users = load_users()
    user = next((u for u in users if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user["id"], "name": user["name"], "role": user.get("role", "user")}


@app.delete("/admin/users/{user_id}", response_model=PublicUser)
async def admin_delete_user(user_id: int, admin: dict = Depends(require_admin)):
    """Admin-only: delete a user by id and return the deleted user's public info."""
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
    users = load_users()

    if payload.role not in ["admin", "user"]:
        raise HTTPException(status_code=400, detail="Role must be admin or user")

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
