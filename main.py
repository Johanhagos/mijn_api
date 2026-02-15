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

# INTERNATIONAL TAX RATES DATABASE (2026)
# Format: 'COUNTRY_CODE': tax_rate_percentage

# EU countries - VAT rates
EU_COUNTRIES = {
    'AT': 20.0,  'BE': 21.0,  'BG': 20.0,  'HR': 25.0,  'CY': 19.0,
    'CZ': 21.0,  'DK': 25.0,  'EE': 22.0,  'FI': 25.5,  'FR': 20.0,
    'DE': 19.0,  'GR': 24.0,  'HU': 27.0,  'IE': 23.0,  'IT': 22.0,
    'LV': 21.0,  'LT': 21.0,  'LU': 17.0,  'MT': 18.0,  'NL': 21.0,
    'PL': 23.0,  'PT': 23.0,  'RO': 19.0,  'SK': 20.0,  'SI': 22.0,
    'ES': 21.0,  'SE': 25.0,
}

# Non-EU Europe
NON_EU_EUROPE = {
    'GB': 20.0,   # United Kingdom (post-Brexit)
    'CH': 7.7,    # Switzerland
    'NO': 25.0,   # Norway
    'IS': 24.0,   # Iceland
    'UA': 20.0,   # Ukraine
    'RU': 18.0,   # Russia
    'TR': 18.0,   # Turkey
}

# Americas
AMERICAS = {
    'US': 0.0,    # No federal sales tax (state-level handling)
    'CA': 5.0,    # Canada GST (plus PST per province)
    'MX': 16.0,   # Mexico
    'BR': 15.0,   # Brazil (ICMS average)
    'AR': 21.0,   # Argentina
    'CL': 19.0,   # Chile
    'CO': 19.0,   # Colombia
}

# Asia-Pacific
ASIA_PACIFIC = {
    'AU': 10.0,   # Australia GST
    'NZ': 15.0,   # New Zealand GST
    'JP': 10.0,   # Japan Consumption Tax
    'KR': 10.0,   # South Korea
    'CN': 13.0,   # China (VAT average)
    'IN': 18.0,   # India (CGST average)
    'SG': 8.0,    # Singapore GST
    'TH': 7.0,    # Thailand VAT
    'ID': 11.0,   # Indonesia
    'MY': 6.0,    # Malaysia SST
}

# Middle East & Africa
MIDDLE_EAST_AFRICA = {
    'AE': 5.0,    # UAE VAT
    'SA': 15.0,   # Saudi Arabia VAT
    'EG': 14.0,   # Egypt VAT
    'ZA': 15.0,   # South Africa VAT
    'NG': 7.5,    # Nigeria VAT
}

# Combine all into global tax database
GLOBAL_TAX_RATES = {
    **EU_COUNTRIES,
    **NON_EU_EUROPE,
    **AMERICAS,
    **ASIA_PACIFIC,
    **MIDDLE_EAST_AFRICA,
}

# Regions for tax rule determination
TAX_REGIONS = {
    'EU': set(EU_COUNTRIES.keys()),
    'ECEA': set(NON_EU_EUROPE.keys()),  # Europe, Caucasus, Central Asia
    'AMERICAS': set(AMERICAS.keys()),
    'ASIA_PACIFIC': set(ASIA_PACIFIC.keys()),
    'MIDDLE_EAST_AFRICA': set(MIDDLE_EAST_AFRICA.keys()),
}

def get_region_for_country(country_code: str) -> str:
    """Get region for a country code"""
    country = country_code.upper() if country_code else 'NL'
    for region, countries in TAX_REGIONS.items():
        if country in countries:
            return region
    return 'OTHER'

def get_tax_rate(country: str) -> float:
    """Get standard tax rate for a country"""
    return GLOBAL_TAX_RATES.get(country.upper(), 0.0)

def determine_tax_rate(seller_country: str, buyer_country: str, buyer_tax_id: str = None) -> tuple:
    """
    Determine tax rate and reason based on seller/buyer countries (INTERNATIONAL).
    
    Applies correct tax rules for:
    - EU: VAT rules (same country, intra-EU, export, B2B reverse charge)
    - Other regions: Tax rules based on seller's country (destination tax, origin tax, etc.)
    
    Returns:
        (tax_rate, is_reverse_charge, explanation)
    """
    seller = seller_country.upper() if seller_country else 'NL'
    buyer = buyer_country.upper() if buyer_country else seller
    
    seller_region = get_region_for_country(seller)
    buyer_region = get_region_for_country(buyer)
    
    # === EU RULES ===
    if seller_region == 'EU' and buyer_region == 'EU':
        # Intra-EU transaction
        if seller == buyer:
            # Same country - charge local VAT
            rate = EU_COUNTRIES.get(seller, 21.0)
            return rate, False, f"Domestic (EU) - {seller} VAT {rate}%"
        else:
            # Different EU countries
            if buyer_tax_id:
                # B2B with VAT number - reverse charge (0%)
                return 0.0, True, f"EU B2B Reverse Charge - {seller} to {buyer}"
            else:
                # B2C - charge seller's VAT
                rate = EU_COUNTRIES.get(seller, 21.0)
                return rate, False, f"EU B2C - {seller} VAT {rate}%"
    
    elif seller_region == 'EU':
        # EU seller selling to non-EU
        return 0.0, False, f"Export from {seller} - 0% VAT"
    
    elif buyer_region == 'EU':
        # Non-EU seller selling to EU
        rate = EU_COUNTRIES.get(buyer, 21.0)
        return rate, False, f"Import to {buyer} - {buyer} VAT {rate}%"
    
    # === US RULES (simplified - destination tax per state) ===
    elif seller == 'US' and buyer == 'US':
        # Same country - would need state code
        return 0.0, False, "US - Sales tax applies per state (state code required)"
    elif seller == 'US':
        # US seller to non-US
        return 0.0, False, "US Export - 0% tax"
    elif buyer == 'US':
        # Non-US to US
        return 0.0, False, "Import to US - federal 0% (state tax may apply)"
    
    # === CANADA RULES ===
    elif seller == 'CA' and buyer == 'CA':
        # Same country - GST + PST (simplified to GST only)
        return 5.0, False, "Canada Domestic - GST applies"
    elif seller == 'CA':
        # Canadian seller to non-Canada
        return 0.0, False, "Canadian Export - 0% tax"
    elif buyer == 'CA':
        # Non-Canada to Canada
        return 5.0, False, "Import to Canada - GST 5%"
    
    # === DEFAULT: Same country or seller's rate ===
    else:
        if seller == buyer:
            rate = get_tax_rate(seller)
            return rate, False, f"Domestic - {seller} rate {rate}%"
        else:
            # Different countries outside EU/CA/US
            # Apply seller's local rate (origin tax principle)
            seller_rate = get_tax_rate(seller)
            return seller_rate, False, f"International - {seller} rate applies {seller_rate}%"
    
    # Same country - always charge local VAT
    if seller == buyer:
        rate = EU_COUNTRIES.get(seller, 21.0)
        return rate, False, f"Domestic sale - {seller} VAT"
    
    # Check if both in EU
    seller_in_eu = seller in EU_COUNTRIES
    buyer_in_eu = buyer in EU_COUNTRIES
    
    if seller_in_eu and buyer_in_eu:
        # EU cross-border
        if buyer_vat_number:
            # B2B with valid VAT number - reverse charge
            return 0.0, True, "EU B2B - Reverse charge (customer pays VAT)"
        else:
            # B2C - charge seller's VAT
            rate = EU_COUNTRIES.get(seller, 21.0)
            return rate, False, f"EU B2C - {seller} VAT applies"
    else:
        # Export outside EU - 0% VAT
        return 0.0, False, "Export outside EU - 0% VAT"

app = FastAPI(title="Secure User API")

# CORS configuration: lock down to known frontend origins in production, allow localhost in non-prod
FRONTEND_ORIGINS = [
    "https://dashboard.apiblockchain.io",
    "https://apiblockchain.io",
    "https://api.apiblockchain.io",
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

# Always copy users.json from repo to DATA_DIR on startup (ensures latest version)
if not READ_ONLY_FS:
    repo_users = Path(__file__).parent / "users.json"
    if repo_users.exists():
        import shutil
        try:
            shutil.copy(str(repo_users), str(DATA_DIR / "users.json"))
            print(f"[INFO] Initialized users.json from repo to {DATA_DIR}")
        except Exception as e:
            print(f"[WARN] Could not copy users.json: {e}")

# Initialize invoices.json from repo if not present in DATA_DIR
if not READ_ONLY_FS and not (DATA_DIR / "invoices.json").exists():
    repo_invoices = Path(__file__).parent / "invoices.json"
    if repo_invoices.exists():
        import shutil
        try:
            shutil.copy(str(repo_invoices), str(DATA_DIR / "invoices.json"))
            print(f"[INFO] Initialized invoices.json from repo to {DATA_DIR}")
        except Exception as e:
            print(f"[WARN] Could not copy invoices.json: {e}")

# If invoices.json exists but is empty, seed from repo copy
if not READ_ONLY_FS and (DATA_DIR / "invoices.json").exists():
    try:
        existing_text = (DATA_DIR / "invoices.json").read_text(encoding="utf-8").strip()
        existing_invoices = json.loads(existing_text or "[]")
        if not existing_invoices:
            repo_invoices = Path(__file__).parent / "invoices.json"
            if repo_invoices.exists():
                import shutil
                shutil.copy(str(repo_invoices), str(DATA_DIR / "invoices.json"))
                print(f"[INFO] Seeded invoices.json from repo to {DATA_DIR}")
    except Exception as e:
        print(f"[WARN] Could not seed invoices.json: {e}")

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

# PayPal configuration
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", "BAA0ISTOuKNpz_VjPaEjdcIaf7pfGfvjxmr4rUjrtSIRoP04FNSCJ31lTf2FSn3mj--r8lBKyQN9FxKmV8")
PAYPAL_SECRET = os.getenv("PAYPAL_SECRET", "EDpVfkShOT0lnfla4G221mvPeVtMsDGTpw-GrN4q6iv0yiLMwX4UehjE8g5URfJH04Zluu1_vsJTqsYt")
PAYPAL_MODE = os.getenv("PAYPAL_MODE", "live")  # "sandbox" or "live"

# Coinbase Commerce configuration
COINBASE_COMMERCE_API_KEY = os.getenv("COINBASE_COMMERCE_API_KEY", "837cb701-982d-435a-8abd-724b723a3883")
COINBASE_WEBHOOK_SECRET = os.getenv("COINBASE_WEBHOOK_SECRET", "")

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


@app.post("/register")
async def register_merchant(payload: dict = Body(...)):
    """Public endpoint for merchant self-registration."""
    name = payload.get("name", "").strip()
    email = payload.get("email", "").strip()
    password = payload.get("password", "").strip()
    business_name = payload.get("business_name", "").strip()
    country = payload.get("country", "NL").strip().upper()  # Country code for VAT calculation

    if not name or not email or not password:
        raise HTTPException(status_code=400, detail="Username, email, and password are required")

    # Validate email format
    if "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email address")

    # Enforce password length
    pw_bytes = password.encode("utf-8")
    if len(pw_bytes) > BCRYPT_MAX_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Password is too long: maximum {BCRYPT_MAX_BYTES} bytes"
        )

    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    # Hash password
    try:
        hashed = _hash_password(password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Error processing password")

    # Check for existing user
    users = load_users()
    if any(u["name"] == name for u in users):
        raise HTTPException(status_code=400, detail="Username already exists")
    if any(u.get("email") == email for u in users):
        raise HTTPException(status_code=400, detail="Email already registered")

    # Generate new ID
    new_id = max([u["id"] for u in users], default=0) + 1

    # Create new user with merchant role
    new_user = {
        "id": new_id,
        "name": name,
        "email": email,
        "password": hashed,
        "role": "merchant",
        "business_name": business_name or name,
        "country": country,  # For automatic VAT calculation
    }

    users.append(new_user)
    save_users(users)

    # Auto-login: generate access token
    access_token = create_access_token(
        data={"sub": name, "role": "merchant"}
    )

    return {
        "message": "Registration successful",
        "access_token": access_token,
        "token_type": "bearer",
        "merchant_id": new_id,
        "email": email,
        "country": country
    }


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
    # ========== HEADER SECTION ==========
    logo_url: Optional[str] = None
    invoice_number: Optional[str] = "INV-TEST-001"
    invoice_date: Optional[str] = None  # e.g., "2026-02-12"
    supply_date: Optional[str] = None  # If different from invoice date
    currency: Optional[str] = "EUR"  # ISO code: EUR, USD, GBP, etc.
    
    # ========== SELLER INFORMATION (Legal Entity) ==========
    seller: Optional[str] = "Example Seller"  # Legal business name
    seller_address: Optional[str] = None  # Full address with country
    seller_country: Optional[str] = None  # Country code or name
    seller_registration_number: Optional[str] = None  # Company reg. number
    seller_vat: Optional[str] = None  # VAT ID / Tax ID
    seller_eori: Optional[str] = None  # EORI for international export
    seller_email: Optional[str] = None
    seller_phone: Optional[str] = None
    
    # ========== BUYER INFORMATION ==========
    buyer: Optional[str] = "Example Buyer"  # Legal name
    buyer_address: Optional[str] = None  # Full address with country
    buyer_country: Optional[str] = None  # Country code or name
    buyer_vat: Optional[str] = None  # VAT ID / Tax ID (for B2B reverse charge)
    buyer_registration_number: Optional[str] = None  # Company reg. number
    buyer_email: Optional[str] = None
    buyer_phone: Optional[str] = None
    buyer_type: Optional[str] = None  # "B2B" or "B2C" (affects tax treatment)
    
    # ========== DESCRIPTION TABLE (Tax-Safe Format) ==========
    description: Optional[str] = "Service"  # Line item description
    quantity: Optional[float] = 1.0
    unit_price: Optional[float] = 100.0
    net_amount: Optional[float] = None  # Subtotal before tax
    vat_rate: Optional[float] = 0.0  # Tax rate percentage (e.g., 19.0 for 19%)
    vat_amount: Optional[float] = None  # Tax amount
    total_amount: Optional[float] = None  # Total amount gross
    
    # Legacy fields (for backward compatibility)
    subtotal: Optional[float] = None  # Deprecated: use net_amount
    amount: Optional[float] = None  # Deprecated: use total_amount
    order_number: Optional[str] = None
    due_date: Optional[str] = None
    
    # ========== TAX INFORMATION SECTION (Flexible) ==========
    # Choose appropriate tax treatment statement
    tax_treatment: Optional[str] = None  # E.g. "VAT calculated in accordance with local regulations"
    is_reverse_charge: Optional[bool] = False  # EU reverse charge
    is_export: Optional[bool] = False  # Export of services - VAT exempt
    is_outside_scope: Optional[bool] = False  # Outside scope of VAT
    tax_exempt_reason: Optional[str] = None  # E.g. "Charity donation", "Government agency"
    
    # ========== PAYMENT INFORMATION ==========
    payment_terms: Optional[str] = None  # E.g. "14 days net", "Net 30"
    payment_system: Optional[str] = "web2"  # web2 or web3
    payment_provider: Optional[str] = None  # E.g. Stripe, PayPal
    blockchain_tx_id: Optional[str] = None  # Blockchain reference
    bank_name: Optional[str] = None
    iban: Optional[str] = None
    swift_bic: Optional[str] = None
    alternative_payment_methods: Optional[str] = None  # Free text
    late_payment_clause: Optional[str] = None  # E.g. interest rate info
    
    # ========== ADDITIONAL INFO ==========
    notes: Optional[str] = None  # General notes
    footer_statement: Optional[str] = None  # Legal footer text
    registered_office: Optional[str] = None  # For footer


class InvoiceCreate(BaseModel):
    seller_name: str
    seller_vat: Optional[str] = None
    seller_address: Optional[str] = None
    seller_country: Optional[str] = None
    buyer_name: str
    buyer_vat: Optional[str] = None
    buyer_address: Optional[str] = None
    buyer_country: Optional[str] = None
    buyer_type: Optional[str] = None  # "B2B" or "B2C"
    invoice_number: Optional[str] = None  # Auto-generated if not provided
    order_number: Optional[str] = None
    date_issued: Optional[str] = Field(default_factory=lambda: datetime.now(timezone.utc).date().isoformat())
    due_date: Optional[str] = None
    items: Optional[List[dict]] = []
    subtotal: Optional[float] = None
    vat_rate: Optional[float] = None  # Percentage (e.g., 21 for 21% VAT)
    vat_amount: Optional[float] = None  # Auto-calculated if not provided
    total: Optional[float] = None  # Auto-calculated if not provided
    payment_system: Optional[str] = "web2"  # "web2" or "web3"
    blockchain_tx_id: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = "issued"  # "issued", "paid", "void", "draft"
    merchant_logo_url: Optional[str] = None


class InvoiceOut(BaseModel):
    id: str
    invoice_number: Optional[str] = None
    order_number: Optional[str] = None
    seller_name: Optional[str] = None
    seller_address: Optional[str] = None
    seller_country: Optional[str] = None
    seller_vat: Optional[str] = None
    buyer_name: Optional[str] = None
    buyer_address: Optional[str] = None
    buyer_country: Optional[str] = None
    buyer_vat: Optional[str] = None
    buyer_type: Optional[str] = None
    subtotal: float = 0.0
    vat_rate: Optional[float] = None
    vat_amount: float = 0.0
    total: float = 0.0
    payment_system: Optional[str] = None
    blockchain_tx_id: Optional[str] = None
    pdf_url: Optional[str] = None
    status: Optional[str] = "issued"
    created_at: Optional[str] = None
    due_date: Optional[str] = None
    notes: Optional[str] = None
    merchant_logo_url: Optional[str] = None


class InvoiceUpdate(BaseModel):
    status: Optional[str] = None  # draft, sent, paid, overdue, void, cancelled
    due_date: Optional[str] = None
    items: Optional[List[dict]] = None
    vat_rate: Optional[float] = None
    notes: Optional[str] = None
    buyer_name: Optional[str] = None
    buyer_email: Optional[str] = None
    buyer_address: Optional[str] = None
    buyer_country: Optional[str] = None
    buyer_vat: Optional[str] = None
    buyer_type: Optional[str] = None


class CreditNoteCreate(BaseModel):
    invoice_id: str  # Reference to original invoice
    amount: float
    vat_amount: Optional[float] = None
    reason: str  # "full_refund", "partial_refund", etc.
    description: Optional[str] = None


class CreditNoteOut(BaseModel):
    id: str
    credit_note_number: str
    invoice_reference: str
    amount: float
    vat_amount: float = 0.0
    reason: str
    description: Optional[str] = None
    created_at: Optional[str] = None


def render_invoice_pdf(data: InvoicePDFRequest) -> bytes:
    """Render universal international invoice PDF compliant with EU, UK, US, and global tax jurisdictions."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=10)
    
    # Normalize fields for backward compatibility
    net_amount = data.net_amount or data.subtotal or (data.quantity * data.unit_price if data.quantity and data.unit_price else 0)
    total_amount = data.total_amount or data.amount or (net_amount + (data.vat_amount or 0))
    invoice_date = data.invoice_date or datetime.now(timezone.utc).date().isoformat()
    currency = data.currency or "EUR"
    
    # ========== HEADER SECTION WITH TWO COLUMNS ==========
    # Left side: Invoice title and numbers
    # Right side: Seller company info
    pdf.set_font("Arial", "B", size=20)
    pdf.set_text_color(34, 139, 34)  # Nature green (Forest Green)
    pdf.cell(100, 12, "INVOICE", ln=False)
    
    # Seller info on right
    pdf.set_font("Arial", "B", size=10)
    pdf.set_text_color(34, 139, 34)  # Nature green
    pdf.cell(0, 6, "SELLER", ln=True, align="R")
    pdf.set_font("Arial", size=9)
    pdf.set_text_color(0, 0, 0)
    
    # Move to next line and create two-column layout
    pdf.set_x(10)
    pdf.set_font("Arial", size=9)
    pdf.cell(95, 4, f"Invoice #: {data.invoice_number or 'N/A'}", ln=False)
    pdf.set_x(110)
    pdf.cell(0, 4, data.seller or "Unknown Seller", ln=True)
    
    pdf.set_x(10)
    pdf.cell(95, 4, f"Invoice Date: {invoice_date}", ln=False)
    pdf.set_x(110)
    if data.seller_vat:
        pdf.cell(0, 4, f"VAT: {data.seller_vat}", ln=True)
    else:
        pdf.ln(4)
    
    pdf.set_x(10)
    if data.supply_date and data.supply_date != invoice_date:
        pdf.cell(95, 4, f"Supply Date: {data.supply_date}", ln=False)
    else:
        pdf.cell(95, 4, "", ln=False)
    pdf.set_x(110)
    if data.seller_registration_number:
        pdf.cell(0, 4, f"Reg: {data.seller_registration_number}", ln=True)
    else:
        pdf.ln(4)
    
    # Seller address
    pdf.set_x(110)
    if data.seller_address:
        for line in data.seller_address.split('\n')[:2]:
            if line.strip():
                pdf.set_x(110)
                pdf.cell(0, 4, line.strip(), ln=True)
    pdf.set_x(110)
    if data.seller_country:
        pdf.cell(0, 4, f"Country: {data.seller_country}", ln=True)
    if data.seller_email:
        pdf.set_x(110)
        pdf.cell(0, 4, f"Email: {data.seller_email}", ln=True)
    
    pdf.ln(5)
    
    # ========== BILLING ADDRESS (LEFT) & ADDITIONAL INFO (RIGHT) ==========
    pdf.set_font("Arial", "B", size=11)
    pdf.set_text_color(34, 139, 34)  # Nature green
    pdf.cell(95, 6, "BILL TO", ln=False)
    pdf.cell(0, 6, "ORDER INFORMATION", ln=True, align="R")
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", size=9)
    
    # Bill to on left
    pdf.set_x(10)
    pdf.cell(95, 5, data.buyer or "Unknown Buyer", ln=False)
    
    # Order info on right
    pdf.set_x(110)
    if data.order_number:
        pdf.cell(0, 5, f"Order #: {data.order_number}", ln=True)
    else:
        pdf.ln(5)
    
    # Buyer details
    if data.buyer_vat:
        pdf.set_x(10)
        pdf.cell(95, 4, f"VAT: {data.buyer_vat}", ln=False)
        pdf.set_x(110)
        if data.due_date:
            pdf.cell(0, 4, f"Due Date: {data.due_date}", ln=True)
        else:
            pdf.ln(4)
    
    if data.buyer_email:
        pdf.set_x(10)
        pdf.cell(95, 4, f"Email: {data.buyer_email}", ln=False)
        pdf.set_x(110)
        pdf.cell(0, 4, f"Currency: {currency}", ln=True)
    elif currency:
        pdf.set_x(110)
        pdf.cell(0, 4, f"Currency: {currency}", ln=True)
    
    if data.buyer_address:
        for line in data.buyer_address.split('\n')[:2]:
            if line.strip():
                pdf.set_x(10)
                pdf.cell(95, 4, line.strip(), ln=True)
    
    pdf.ln(4)
    
    # ========== DESCRIPTION TABLE (Tax-Safe Format) ==========
    pdf.set_font("Arial", "B", size=9)
    pdf.set_fill_color(34, 139, 34)  # Nature green header
    pdf.set_text_color(255, 255, 255)  # White text
    pdf.cell(75, 7, "Description", border=1, fill=True, align="L")
    pdf.cell(15, 7, "Qty", border=1, fill=True, align="C")
    pdf.cell(25, 7, "Unit Price", border=1, fill=True, align="R")
    pdf.cell(25, 7, "Net Amount", border=1, fill=True, align="R", ln=True)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", size=9)
    desc = (data.description or "Service")[:75]
    pdf.cell(75, 6, desc, border=1, align="L")
    pdf.cell(15, 6, f"{data.quantity:.0f}", border=1, align="C")
    pdf.cell(25, 6, f"{currency} {data.unit_price:.2f}", border=1, align="R")
    pdf.cell(25, 6, f"{currency} {net_amount:.2f}", border=1, align="R", ln=True)
    pdf.ln(4)
    
    # ========== TAX CALCULATION SUMMARY ==========
    x_right = 125
    pdf.set_font("Arial", size=9)
    
    # Subtotal (Net)
    pdf.set_x(x_right)
    pdf.cell(35, 5, "Subtotal (Net):", align="L")
    pdf.cell(0, 5, f"{currency} {net_amount:.2f}", align="R", ln=True)
    
    # VAT/Tax line (only if applicable)
    if data.vat_amount and data.vat_amount > 0:
        pdf.set_x(x_right)
        vat_rate = data.vat_rate or 0
        pdf.cell(35, 5, f"Tax ({vat_rate}%):", align="L")
        pdf.cell(0, 5, f"{currency} {data.vat_amount:.2f}", align="R", ln=True)
    elif data.is_reverse_charge or data.is_export or data.is_outside_scope or data.tax_exempt_reason:
        pdf.set_x(x_right)
        pdf.set_font("Arial", "I", size=8)
        pdf.cell(0, 5, "Tax: 0.00 (see tax treatment)", align="R", ln=True)
        pdf.set_font("Arial", size=9)
    
    # Total (Gross)
    pdf.set_x(x_right)
    pdf.set_font("Arial", "B", size=11)
    pdf.set_text_color(34, 139, 34)  # Nature green
    pdf.cell(35, 7, "TOTAL:", align="L")
    pdf.cell(0, 7, f"{currency} {total_amount:.2f}", align="R", ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)
    
    # ========== TAX INFORMATION SECTION (Flexible) ==========
    if data.is_reverse_charge or data.is_export or data.is_outside_scope or data.tax_exempt_reason or data.tax_treatment:
        pdf.set_font("Arial", "B", size=10)
        pdf.set_text_color(34, 139, 34)  # Nature green
        pdf.cell(0, 6, "TAX TREATMENT", ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", size=8)
        
        if data.is_reverse_charge and data.buyer_vat:
            pdf.cell(0, 4, "VAT reverse charged to customer (B2B EU transaction).", ln=True)
        if data.is_export:
            pdf.cell(0, 4, "Export of services — VAT exempt per international trade rules.", ln=True)
        if data.is_outside_scope:
            pdf.cell(0, 4, "Transaction outside scope of VAT.", ln=True)
        if data.tax_exempt_reason:
            pdf.cell(0, 4, f"Tax exempt: {data.tax_exempt_reason}", ln=True)
        if not (data.is_reverse_charge or data.is_export or data.is_outside_scope or data.tax_exempt_reason) and data.tax_treatment:
            pdf.multi_cell(0, 4, data.tax_treatment)
        elif not (data.is_reverse_charge or data.is_export or data.is_outside_scope or data.tax_exempt_reason):
            pdf.cell(0, 4, "Tax calculated in accordance with local regulations.", ln=True)
        pdf.ln(2)
    
    # ========== PAYMENT INFORMATION ==========
    pdf.set_font("Arial", "B", size=10)
    pdf.set_text_color(34, 139, 34)  # Nature green
    pdf.cell(0, 6, "PAYMENT INFORMATION", ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", size=9)
    
    if data.payment_terms:
        pdf.cell(0, 4, f"Terms: {data.payment_terms}", ln=True)
    if data.due_date:
        pdf.cell(0, 4, f"Due Date: {data.due_date}", ln=True)
    
    pdf.cell(0, 4, f"Method: {data.payment_provider or data.payment_system.upper()}", ln=True)
    
    if data.iban:
        pdf.cell(0, 4, f"IBAN: {data.iban}", ln=True)
    if data.swift_bic:
        pdf.cell(0, 4, f"SWIFT/BIC: {data.swift_bic}", ln=True)
    if data.bank_name:
        pdf.cell(0, 4, f"Bank: {data.bank_name}", ln=True)
    
    if data.blockchain_tx_id:
        pdf.cell(0, 4, f"Blockchain TX: {data.blockchain_tx_id}", ln=True)
    
    if data.alternative_payment_methods:
        pdf.set_font("Arial", size=8)
        pdf.multi_cell(0, 3, f"Other methods: {data.alternative_payment_methods}")
        pdf.set_font("Arial", size=9)
    
    if data.late_payment_clause:
        pdf.set_font("Arial", "I", size=8)
        pdf.multi_cell(0, 3, f"Late payment: {data.late_payment_clause}")
        pdf.set_font("Arial", size=9)
    
    pdf.ln(2)
    
    # ========== NOTES SECTION ==========
    if data.notes:
        pdf.set_font("Arial", "B", size=10)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 6, "NOTES", ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", size=8)
        pdf.multi_cell(0, 4, data.notes)
        pdf.ln(2)
    
    # ========== 7️⃣ FOOTER (Universal Legal Safety) ==========
    pdf.set_font("Arial", "I", size=7)
    pdf.set_text_color(100, 100, 100)
    
    footer_text = data.footer_statement or "This invoice is issued in accordance with applicable international tax regulations."
    if data.registered_office:
        footer_text += f" | Registered Office: {data.registered_office}"
    if data.seller_registration_number:
        footer_text += f" | Company Reg: {data.seller_registration_number}"
    
    pdf.multi_cell(0, 3, footer_text)
    
    # Generate PDF
    pdf_str = pdf.output(dest='S')
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


# ========== INVOICE NUMBERING HELPERS ==========
def get_next_invoice_number(merchant_id: int = None) -> str:
    """Get next sequential invoice number (e.g., INV-2026-0001)."""
    invoices = load_invoices()
    year = datetime.now(timezone.utc).year
    
    # Find max invoice number for this year
    max_num = 0
    for inv in invoices:
        inv_num = inv.get("invoice_number", "")
        if inv_num.startswith(f"INV-{year}-"):
            try:
                num = int(inv_num.split("-")[-1])
                if num > max_num:
                    max_num = num
            except (ValueError, IndexError):
                pass
    
    return f"INV-{year}-{max_num + 1:04d}"


def calculate_vat(subtotal: float, vat_rate: float = 0) -> tuple:
    """Calculate VAT amount and total.
    
    Args:
        subtotal: Net amount before VAT
        vat_rate: VAT percentage (0-100)
    
    Returns:
        (vat_amount, total_with_vat)
    """
    if vat_rate <= 0:
        return 0.0, subtotal
    
    vat_amount = round(subtotal * (vat_rate / 100), 2)
    total = round(subtotal + vat_amount, 2)
    return vat_amount, total


def create_credit_note_number(merchant_id: int = None) -> str:
    """Generate credit note number (e.g., CN-2026-0001)."""
    invoices = load_invoices()
    year = datetime.now(timezone.utc).year
    
    max_num = 0
    for inv in invoices:
        cn_num = inv.get("credit_note_number", "")
        if cn_num.startswith(f"CN-{year}-"):
            try:
                num = int(cn_num.split("-")[-1])
                if num > max_num:
                    max_num = num
            except (ValueError, IndexError):
                pass
    
    return f"CN-{year}-{max_num + 1:04d}"


@app.post("/invoices", response_model=InvoiceOut, status_code=201)
async def create_invoice(payload: InvoiceCreate, current_user: dict = Depends(get_current_user)):
    """Create and persist an invoice with automatic numbering and VAT calculation."""
    import uuid
    
    invoices = load_invoices()
    
    # Generate unique ID
    unique_id = str(uuid.uuid4())
    
    # Auto-generate invoice number if not provided
    invoice_number = payload.invoice_number or get_next_invoice_number()
    
    def _to_number(value, default=0.0):
        try:
            if value is None:
                return default
            return float(str(value).strip())
        except (ValueError, TypeError):
            return default

    # Normalize items and calculate subtotal
    items = payload.items or []
    normalized_items = []
    for item in items:
        qty = _to_number(item.get("quantity", 1), 1.0)
        unit_price = _to_number(item.get("unit_price", 0), 0.0)
        amount = _to_number(item.get("amount", qty * unit_price), qty * unit_price)
        normalized_items.append({
            **item,
            "quantity": qty,
            "unit_price": unit_price,
            "amount": round(amount, 2),
        })

    subtotal = payload.subtotal
    if subtotal is None:
        subtotal = sum(i.get("amount", 0) for i in normalized_items)
    subtotal = _to_number(subtotal, 0.0)
    
    # Determine VAT rate
    vat_rate = 0.0
    if payload.buyer_type == "B2B" and payload.buyer_vat:
        # B2B with VAT number: reverse charge (0% VAT)
        vat_rate = 0.0
    elif payload.vat_rate is not None:
        vat_rate = payload.vat_rate
    else:
        # Default: 21% VAT (adjustable by merchant later)
        vat_rate = 21.0
    
    vat_amount, total = calculate_vat(subtotal, vat_rate)
    
    # If user provided vat_amount, use it (for special cases)
    if payload.vat_amount is not None:
        vat_amount = payload.vat_amount
        total = subtotal + vat_amount
    
    # If user provided total, recalculate vat_amount
    if payload.total is not None:
        total = payload.total
        vat_amount = total - subtotal

    inv = {
        "id": unique_id,
        "invoice_number": invoice_number,
        "order_number": payload.order_number,
        "seller_name": payload.seller_name,
        "seller_vat": payload.seller_vat,
        "seller_address": payload.seller_address,
        "seller_country": payload.seller_country,
        "buyer_name": payload.buyer_name,
        "buyer_vat": payload.buyer_vat,
        "buyer_address": payload.buyer_address,
        "buyer_country": payload.buyer_country,
        "buyer_type": payload.buyer_type,
        "date_issued": payload.date_issued or datetime.now(timezone.utc).date().isoformat(),
        "due_date": payload.due_date,
        "items": normalized_items,
        "subtotal": round(subtotal, 2),
        "vat_rate": vat_rate,
        "vat_amount": round(vat_amount, 2),
        "total": round(total, 2),
        "payment_system": payload.payment_system or "web2",
        "blockchain_tx_id": payload.blockchain_tx_id,
        "description": payload.description,
        "notes": payload.notes,
        "status": payload.status or "issued",
        "merchant_logo_url": payload.merchant_logo_url,
        "created_by": current_user.get("name"),
        "created_at": datetime.now(timezone.utc).isoformat(),
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
            logo_url=inv.get("merchant_logo_url"),
            invoice_number=inv["invoice_number"],
            invoice_date=inv.get("date_issued"),
            seller=inv["seller_name"],
            seller_vat=inv.get("seller_vat"),
            seller_address=inv.get("seller_address"),
            seller_country=inv.get("seller_country"),
            buyer=inv["buyer_name"],
            buyer_vat=inv.get("buyer_vat"),
            buyer_address=inv.get("buyer_address"),
            buyer_country=inv.get("buyer_country"),
            buyer_type=inv.get("buyer_type"),
            description=inv.get("description") or (normalized_items[0].get("description") if normalized_items else ""),
            quantity=normalized_items[0].get("quantity", 1) if normalized_items else 1,
            unit_price=normalized_items[0].get("unit_price", 0) if normalized_items else 0,
            net_amount=inv["subtotal"],
            vat_amount=inv["vat_amount"],
            vat_rate=vat_rate,
            total_amount=inv["total"],
            payment_system=inv.get("payment_system", "web2"),
            blockchain_tx_id=inv.get("blockchain_tx_id"),
        )

        pdf_bytes = render_invoice_pdf(pdf_req)
        ensure_invoice_pdf_dir()
        if not READ_ONLY_FS and INVOICE_PDF_DIR.exists():
            pdf_path = INVOICE_PDF_DIR / f"invoice-{unique_id}.pdf"
            pdf_path.write_bytes(pdf_bytes)
            pdf_url = str(pdf_path)
    except Exception as e:
        logger = logging.getLogger("uvicorn.error")
        logger.exception("Error generating invoice PDF")
        pdf_url = None

    inv["pdf_url"] = pdf_url
    
    # Update saved invoice with PDF URL
    invoices[-1] = inv
    try:
        save_invoices(invoices)
    except RuntimeError:
        pass

    return InvoiceOut(
        id=inv["id"],
        invoice_number=inv["invoice_number"],
        order_number=inv.get("order_number"),
        seller_name=inv["seller_name"],
        seller_address=inv.get("seller_address"),
        seller_vat=inv.get("seller_vat"),
        buyer_name=inv["buyer_name"],
        buyer_address=inv.get("buyer_address"),
        buyer_vat=inv.get("buyer_vat"),
        buyer_type=inv.get("buyer_type"),
        subtotal=inv["subtotal"],
        vat_rate=inv.get("vat_rate"),
        vat_amount=inv["vat_amount"],
        total=inv["total"],
        payment_system=inv.get("payment_system"),
        blockchain_tx_id=inv.get("blockchain_tx_id"),
        pdf_url=inv.get("pdf_url"),
        status=inv.get("status"),
        created_at=inv.get("created_at"),
        due_date=inv.get("due_date"),
        notes=inv.get("notes"),
        merchant_logo_url=inv.get("merchant_logo_url"),
    )


@app.get("/invoices", response_model=List[InvoiceOut])
async def list_invoices(current_user: dict = Depends(get_current_user)):
    invoices = load_invoices()
    return [InvoiceOut(**{
        "id": inv.get("id"),
        "invoice_number": inv.get("invoice_number"),
        "order_number": inv.get("order_number"),
        "seller_name": inv.get("seller_name"),
        "seller_address": inv.get("seller_address"),
        "seller_vat": inv.get("seller_vat"),
        "buyer_name": inv.get("buyer_name"),
        "buyer_address": inv.get("buyer_address"),
        "buyer_vat": inv.get("buyer_vat"),
        "buyer_type": inv.get("buyer_type"),
        "subtotal": inv.get("subtotal", 0),
        "vat_rate": inv.get("vat_rate"),
        "vat_amount": inv.get("vat_amount", 0),
        "total": inv.get("total", 0),
        "payment_system": inv.get("payment_system"),
        "blockchain_tx_id": inv.get("blockchain_tx_id"),
        "pdf_url": inv.get("pdf_url"),
        "status": inv.get("status", "issued"),
        "created_at": inv.get("created_at"),
        "due_date": inv.get("due_date"),
        "notes": inv.get("notes"),
        "merchant_logo_url": inv.get("merchant_logo_url"),
    }) for inv in invoices]


@app.post("/invoices/{invoice_id}/void")
async def void_invoice(invoice_id: str, current_user: dict = Depends(get_current_user)):
    """Mark an invoice as VOID without reusing its number. Only works for non-sent invoices."""
    invoices = load_invoices()
    inv = next((i for i in invoices if i.get("id") == invoice_id), None)
    
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Only allow voiding drafted/non-sent invoices
    if inv.get("status") in ["paid", "refunded"]:
        raise HTTPException(status_code=400, detail="Cannot void a paid or refunded invoice")
    
    inv["status"] = "void"
    inv["voided_at"] = datetime.now(timezone.utc).isoformat()
    inv["voided_by"] = current_user.get("name")
    
    try:
        save_invoices(invoices)
    except RuntimeError:
        pass
    
    return {"status": "voided", "invoice_id": invoice_id, "invoice_number": inv.get("invoice_number")}


@app.post("/credit-notes", response_model=CreditNoteOut, status_code=201)
async def create_credit_note(payload: CreditNoteCreate, current_user: dict = Depends(get_current_user)):
    """Create a credit note referencing an original invoice. This handles refunds without modifying the original."""
    invoices = load_invoices()
    
    # Find original invoice
    original_inv = next((i for i in invoices if i.get("id") == payload.invoice_id), None)
    if not original_inv:
        raise HTTPException(status_code=404, detail="Referenced invoice not found")
    
    credit_note_num = create_credit_note_number()
    
    credit_note = {
        "id": str(uuid.uuid4()),
        "type": "credit_note",
        "credit_note_number": credit_note_num,
        "invoice_reference": original_inv.get("invoice_number"),
        "invoice_id": payload.invoice_id,
        "amount": payload.amount,
        "vat_amount": payload.vat_amount or 0,
        "reason": payload.reason,  # "full_refund", "partial_refund", etc.
        "description": payload.description,
        "created_by": current_user.get("name"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    
    # Mark original invoice as having a credit note
    if "credit_notes" not in original_inv:
        original_inv["credit_notes"] = []
    original_inv["credit_notes"].append(credit_note_num)
    
    invoices.append(credit_note)
    try:
        save_invoices(invoices)
    except RuntimeError:
        pass
    
    return CreditNoteOut(
        id=credit_note["id"],
        credit_note_number=credit_note["credit_note_number"],
        invoice_reference=credit_note["invoice_reference"],
        amount=credit_note["amount"],
        vat_amount=credit_note["vat_amount"],
        reason=credit_note["reason"],
        description=credit_note["description"],
        created_at=credit_note["created_at"],
    )


@app.get("/invoices/{invoice_id}/credit-notes", response_model=List[CreditNoteOut])
async def get_invoice_credit_notes(invoice_id: str, current_user: dict = Depends(get_current_user)):
    """Get all credit notes for an invoice."""
    invoices = load_invoices()
    
    # Find original invoice
    original_inv = next((i for i in invoices if i.get("id") == invoice_id), None)
    if not original_inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    credit_notes = []
    for cn in invoices:
        if cn.get("type") == "credit_note" and cn.get("invoice_id") == invoice_id:
            credit_notes.append(CreditNoteOut(
                id=cn["id"],
                credit_note_number=cn["credit_note_number"],
                invoice_reference=cn["invoice_reference"],
                amount=cn["amount"],
                vat_amount=cn.get("vat_amount", 0),
                reason=cn["reason"],
                description=cn.get("description"),
                created_at=cn.get("created_at"),
            ))
    
    return credit_notes


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
            total = 0.0
            for i in lst:
                val = i.get("total", 0)
                if val is None:
                    val = 0
                try:
                    total += float(str(val).strip())
                except (ValueError, TypeError):
                    total += 0.0
            return round(total, 2)
        except Exception:
            return 0.0

    web2_total = _sum_total(web2_invoices)
    web3_total = _sum_total(web3_invoices)
    total_amount = _sum_total(my_invoices)

    # Generate daily revenue for last 30 days
    from datetime import datetime, timedelta
    today = datetime.now().date()
    daily_revenue = {}
    
    for i in range(30):
        date = today - timedelta(days=i)
        daily_revenue[date.strftime("%Y-%m-%d")] = 0.0
    
    # Aggregate invoices by date
    for inv in my_invoices:
        try:
            created_at = inv.get("created_at", "")
            if created_at:
                # Parse date (format: 2026-02-12 or 2026-02-12T...)
                date_str = created_at.split("T")[0] if "T" in created_at else created_at[:10]
                if date_str in daily_revenue:
                    val = inv.get("total", 0)
                    if val is None:
                        val = 0
                    try:
                        daily_revenue[date_str] += float(str(val).strip())
                    except (ValueError, TypeError):
                        daily_revenue[date_str] += 0.0
        except Exception:
            pass
    
    # Format as array for chart, sorted by date
    revenue_data = [
        {"date": date, "amount": round(amount, 2)}
        for date, amount in sorted(daily_revenue.items())
    ]

    return {
        "total_invoices": total_invoices,
        "web2_count": len(web2_invoices),
        "web3_count": len(web3_invoices),
        "web2_total": web2_total,
        "web3_total": web3_total,
        "total_amount": total_amount,
        "revenue": revenue_data,
    }


@app.get("/merchant/me")
async def merchant_me(current_user: dict = Depends(get_current_user)):
    """Return merchant identity info (id, name, email if present)."""
    users = load_users()
    user = next((u for u in users if u["id"] == current_user.get("id")), None)
    if not user:
        return {"id": current_user.get("id"), "name": current_user.get("name"), "email": current_user.get("email")}
    
    # Return full profile data
    return {
        "id": user.get("id"),
        "name": user.get("name"),
        "username": user.get("username", user.get("name")),
        "email": user.get("email"),
        "business_name": user.get("business_name"),
        "phone_number": user.get("phone_number"),
        "address": user.get("address"),
        "city": user.get("city"),
        "postal_code": user.get("postal_code"),
        "country": user.get("country"),
        "vat_number": user.get("vat_number"),
        "business_type": user.get("business_type"),
        "website": user.get("website"),
        "description": user.get("description"),
    }


@app.put("/merchant/profile")
async def update_merchant_profile(payload: dict = Body(...), current_user: dict = Depends(get_current_user)):
    """Update merchant profile information."""
    users = load_users()
    user = next((u for u in users if u["id"] == current_user.get("id")), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update allowed fields
    allowed_fields = [
        "username", "business_name", "email", "phone_number",
        "address", "city", "postal_code", "country",
        "vat_number", "business_type", "website", "description"
    ]
    
    for field in allowed_fields:
        if field in payload:
            # Map camelCase to snake_case
            snake_field = field
            camel_field = field
            
            # Convert camelCase keys from frontend
            field_mapping = {
                "businessName": "business_name",
                "contactEmail": "email",
                "phoneNumber": "phone_number",
                "postalCode": "postal_code",
                "vatNumber": "vat_number",
                "businessType": "business_type",
            }
            
            if camel_field in field_mapping:
                snake_field = field_mapping[camel_field]
            
            # Check for both camelCase and snake_case
            value = payload.get(camel_field) or payload.get(snake_field)
            if value is not None:
                user[snake_field] = value
    
    save_users(users)
    return {"message": "Profile updated successfully", "user": user}


@app.post("/merchant/logo")
async def upload_merchant_logo(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """Upload merchant logo for use in invoices. Returns logo URL."""
    if not file.filename or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")
    
    # Validate file size (max 2MB)
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 2MB)")
    
    # Generate filename
    merchant_id = current_user.get("id", "unknown")
    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"merchant-{merchant_id}-logo.{ext}"
    
    # Save to LOGOS directory
    logo_dir = DATA_DIR / "logos"
    try:
        logo_dir.mkdir(parents=True, exist_ok=True)
        logo_path = logo_dir / filename
        logo_path.write_bytes(content)
        logo_url = str(logo_path)
        
        return {
            "status": "success",
            "logo_url": logo_url,
            "filename": filename,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save logo: {str(e)}")


@app.get("/merchant/logo")
async def get_merchant_logo(current_user: dict = Depends(get_current_user)):
    """Get merchant's uploaded logo URL if it exists."""
    merchant_id = current_user.get("id", "unknown")
    logo_dir = DATA_DIR / "logos"
    
    # Check for common logo files
    for ext in ["png", "jpg", "jpeg", "gif", "webp"]:
        logo_path = logo_dir / f"merchant-{merchant_id}-logo.{ext}"
        if logo_path.exists():
            return {
                "status": "success",
                "logo_url": str(logo_path),
                "filename": logo_path.name,
            }
    
    return {
        "status": "not_found",
        "logo_url": None,
        "message": "No logo uploaded yet"
    }


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
async def get_invoice(invoice_id: str, current_user: dict = Depends(get_current_user)):
    invoices = load_invoices()
    inv = next((i for i in invoices if str(i.get("id")) == str(invoice_id)), None)
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


@app.patch("/invoices/{invoice_id}", response_model=InvoiceOut)
async def update_invoice(invoice_id: str, payload: InvoiceUpdate, current_user: dict = Depends(get_current_user)):
    """Update an invoice. Recalculates VAT if items are modified. Validates state transitions."""
    invoices = load_invoices()
    inv = next((i for i in invoices if str(i.get("id")) == str(invoice_id)), None)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # State transition validation
    current_status = inv.get("status", "draft")
    new_status = payload.status or current_status
    
    if new_status != current_status:
        valid_transitions = {
            "draft": ["sent", "cancelled"],
            "sent": ["paid", "overdue", "cancelled"],
            "paid": ["overdue"],
            "overdue": ["paid"],
            "void": [],
            "cancelled": [],
        }
        if new_status not in valid_transitions.get(current_status, []):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot transition from '{current_status}' to '{new_status}'"
            )
    
    # Update allowed fields
    if payload.status is not None:
        inv["status"] = payload.status
    if payload.due_date is not None:
        inv["due_date"] = payload.due_date
    if payload.notes is not None:
        inv["notes"] = payload.notes
    if payload.buyer_name is not None:
        inv["buyer_name"] = payload.buyer_name
    if payload.buyer_email is not None:
        inv["buyer_email"] = payload.buyer_email
    if payload.buyer_address is not None:
        inv["buyer_address"] = payload.buyer_address
    if payload.buyer_country is not None:
        inv["buyer_country"] = payload.buyer_country
    if payload.buyer_vat is not None:
        inv["buyer_vat"] = payload.buyer_vat
    if payload.buyer_type is not None:
        inv["buyer_type"] = payload.buyer_type
    
    # Recalculate VAT if items changed
    if payload.items is not None:
        def _to_number(value, default=0.0):
            try:
                if value is None:
                    return default
                return float(str(value).strip())
            except (ValueError, TypeError):
                return default
        
        normalized_items = []
        for item in payload.items:
            qty = _to_number(item.get("quantity", 1), 1.0)
            unit_price = _to_number(item.get("unit_price", 0), 0.0)
            amount = _to_number(item.get("amount", qty * unit_price), qty * unit_price)
            normalized_items.append({
                **item,
                "quantity": qty,
                "unit_price": unit_price,
                "amount": round(amount, 2),
            })
        
        inv["items"] = normalized_items
        
        # Recalculate subtotal
        subtotal = sum(i.get("amount", 0) for i in normalized_items)
        inv["subtotal"] = round(subtotal, 2)
        
        # Recalculate VAT
        vat_rate = payload.vat_rate if payload.vat_rate is not None else inv.get("vat_rate", 21.0)
        vat_amount, total = calculate_vat(subtotal, vat_rate)
        inv["vat_rate"] = vat_rate
        inv["vat_amount"] = vat_amount
        inv["total"] = total
    
    # Mark as updated
    inv["updated_at"] = datetime.now(timezone.utc).isoformat()
    inv["updated_by"] = current_user.get("name")
    
    # Persist
    try:
        save_invoices(invoices)
    except RuntimeError:
        pass
    
    # Log audit event
    log_event(f"INVOICE_UPDATED id={invoice_id} status={new_status}", current_user.get("name"), "-")
    
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


# --- Country-Specific VAT & Compliance Database ---
COUNTRY_VAT_RULES = {
    "NL": {
        "name": "Netherlands",
        "standard_rate": 21.0,
        "reduced_rates": [9.0],  # Food, books, medicines
        "oss_threshold": 10000,  # EUR
        "currency": "EUR",
        "tax_authority": "Belastingdienst",
        "vat_return_frequency": "Quarterly",
        "invoice_requirements": [
            "Sequential invoice number",
            "VAT identification number",
            "Date of supply",
            "Customer VAT number (B2B)",
            "Reverse charge notation (EU B2B)"
        ],
        "reverse_charge_phrase": "Verlegd naar u - BTW-heffing bij afnemer",
        "digital_reporting": "Yes - SAF-T required",
        "record_retention_years": 7,
    },
    "DE": {
        "name": "Germany",
        "standard_rate": 19.0,
        "reduced_rates": [7.0],
        "oss_threshold": 10000,
        "currency": "EUR",
        "tax_authority": "Bundeszentralamt für Steuern",
        "vat_return_frequency": "Monthly/Quarterly",
        "invoice_requirements": [
            "Rechnungsnummer (invoice number)",
            "Steuernummer (tax number)",
            "Reverse charge: 'Steuerschuldnerschaft des Leistungsempfängers'",
            "GoBD compliant archiving"
        ],
        "reverse_charge_phrase": "Steuerschuldnerschaft des Leistungsempfängers gemäß §13b UStG",
        "digital_reporting": "Yes - GoBD compliance required",
        "record_retention_years": 10,
    },
    "FR": {
        "name": "France",
        "standard_rate": 20.0,
        "reduced_rates": [10.0, 5.5, 2.1],
        "oss_threshold": 10000,
        "currency": "EUR",
        "tax_authority": "Direction Générale des Finances Publiques (DGFiP)",
        "vat_return_frequency": "Monthly",
        "invoice_requirements": [
            "Numéro de TVA intracommunautaire",
            "Autoliquidation mention (reverse charge)",
            "Electronic invoicing mandatory from 2026"
        ],
        "reverse_charge_phrase": "Autoliquidation - Article 283-2 du CGI",
        "digital_reporting": "Yes - E-invoicing mandatory 2026",
        "record_retention_years": 6,
    },
    "BE": {
        "name": "Belgium",
        "standard_rate": 21.0,
        "reduced_rates": [12.0, 6.0],
        "oss_threshold": 10000,
        "currency": "EUR",
        "tax_authority": "FOD Financiën / SPF Finances",
        "vat_return_frequency": "Monthly/Quarterly",
        "invoice_requirements": [
            "BTW-nummer / Numéro de TVA",
            "Sequential numbering per fiscal year",
            "Reverse charge: 'Autoliquidation / Verlegde BTW'"
        ],
        "reverse_charge_phrase": "Autoliquidation / Verlegde BTW - Art. 51 §2 1° WBTW/CTVA",
        "digital_reporting": "Yes - Mandatory listing required",
        "record_retention_years": 7,
    },
    "GB": {
        "name": "United Kingdom",
        "standard_rate": 20.0,
        "reduced_rates": [5.0, 0.0],
        "oss_threshold": 0,  # Post-Brexit: no EU OSS
        "currency": "GBP",
        "tax_authority": "HM Revenue & Customs (HMRC)",
        "vat_return_frequency": "Quarterly",
        "invoice_requirements": [
            "VAT registration number",
            "Unique sequential invoice number",
            "Making Tax Digital (MTD) compliance",
            "No reverse charge for EU (post-Brexit)"
        ],
        "reverse_charge_phrase": "Reverse charge: Customer to account for VAT",
        "digital_reporting": "Yes - Making Tax Digital mandatory",
        "record_retention_years": 6,
        "special_notes": "Post-Brexit: EU B2B treated as exports (0% VAT with proof)"
    },
    "US": {
        "name": "United States",
        "standard_rate": 0.0,  # No federal VAT
        "reduced_rates": [],
        "oss_threshold": 0,
        "currency": "USD",
        "tax_authority": "State-specific (no federal VAT)",
        "vat_return_frequency": "State-dependent",
        "invoice_requirements": [
            "Sales tax varies by state",
            "Economic nexus rules apply",
            "Marketplace facilitator laws"
        ],
        "reverse_charge_phrase": "N/A - Use tax applies",
        "digital_reporting": "State-dependent",
        "record_retention_years": 7,
        "special_notes": "No VAT - Sales tax system. Each state has different rates (0-10%). Economic nexus: $100k+ or 200+ transactions."
    },
    "ES": {
        "name": "Spain",
        "standard_rate": 21.0,
        "reduced_rates": [10.0, 4.0],
        "oss_threshold": 10000,
        "currency": "EUR",
        "tax_authority": "Agencia Tributaria",
        "vat_return_frequency": "Quarterly/Monthly",
        "invoice_requirements": [
            "NIF (tax ID) or VAT number",
            "Reverse charge: 'Inversión del sujeto pasivo'",
            "SII (Immediate Supply of Information) for large companies"
        ],
        "reverse_charge_phrase": "Inversión del sujeto pasivo - Art. 84.Uno.2º LIVA",
        "digital_reporting": "Yes - SII for turnover >6M EUR",
        "record_retention_years": 4,
    },
    "IT": {
        "name": "Italy",
        "standard_rate": 22.0,
        "reduced_rates": [10.0, 5.0, 4.0],
        "oss_threshold": 10000,
        "currency": "EUR",
        "tax_authority": "Agenzia delle Entrate",
        "vat_return_frequency": "Monthly/Quarterly",
        "invoice_requirements": [
            "Partita IVA (VAT number)",
            "SDI (electronic invoicing) mandatory",
            "Reverse charge: 'Inversione contabile - Reverse charge'"
        ],
        "reverse_charge_phrase": "Inversione contabile art. 17 c. 6 DPR 633/72",
        "digital_reporting": "Yes - FatturaPA (SDI) mandatory",
        "record_retention_years": 10,
    },
    "SE": {
        "name": "Sweden",
        "standard_rate": 25.0,
        "reduced_rates": [12.0, 6.0],
        "oss_threshold": 10000,
        "currency": "SEK",
        "tax_authority": "Skatteverket",
        "vat_return_frequency": "Monthly",
        "invoice_requirements": [
            "Organisationsnummer and VAT number",
            "Reverse charge: 'Omvänd skattskyldighet'",
            "Electronic invoicing recommended"
        ],
        "reverse_charge_phrase": "Omvänd skattskyldighet enligt 1 kap. 2 § ML",
        "digital_reporting": "Yes - SIE format for accounting",
        "record_retention_years": 7,
    },
    "PL": {
        "name": "Poland",
        "standard_rate": 23.0,
        "reduced_rates": [8.0, 5.0],
        "oss_threshold": 10000,
        "currency": "PLN",
        "tax_authority": "Krajowa Administracja Skarbowa",
        "vat_return_frequency": "Monthly",
        "invoice_requirements": [
            "NIP number (tax ID)",
            "KSeF (structured electronic invoices) from 2024",
            "Split payment mechanism for high-risk goods"
        ],
        "reverse_charge_phrase": "Odwrotne obciążenie - Art. 17 ust. 1 pkt 4 Ustawy o VAT",
        "digital_reporting": "Yes - KSeF mandatory from 2024",
        "record_retention_years": 5,
    },
}

def get_country_vat_info(country_code: str) -> dict:
    """Get VAT rules for a specific country. Returns generic EU rules if country not found."""
    country = country_code.upper() if country_code else "XX"
    
    if country in COUNTRY_VAT_RULES:
        return COUNTRY_VAT_RULES[country]
    
    # Default EU country rules
    return {
        "name": country,
        "standard_rate": 20.0,
        "reduced_rates": [10.0],
        "oss_threshold": 10000,
        "currency": "EUR",
        "tax_authority": "Local tax authority",
        "vat_return_frequency": "Quarterly",
        "invoice_requirements": ["VAT number", "Sequential numbering", "Reverse charge notation for EU B2B"],
        "reverse_charge_phrase": "Reverse charge applies - VAT payable by customer",
        "digital_reporting": "Check local requirements",
        "record_retention_years": 7,
    }


# --- AI Assistant Endpoint ---
@app.post("/ai/chat")
async def ai_chat(payload: dict = Body(...), current_user: dict = Depends(get_current_user)):
    """AI assistant endpoint for merchant dashboard help - specialized in VAT & compliance."""
    message = payload.get("message", "").strip()
    context = payload.get("context", {})
    history = payload.get("history", [])
    
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    # Build context string for AI
    stats = context.get("stats", {})
    merchant = context.get("merchant", {})
    
    # Get country-specific VAT rules
    merchant_country = merchant.get('country', 'XX')
    country_info = get_country_vat_info(merchant_country)
    
    context_info = f"""
You are a specialized AI assistant for VAT compliance, tax regulations, and blockchain payment technology on the APIBlockchain platform.

=== CORE PLATFORM KNOWLEDGE ===

ABOUT APIBLOCKCHAIN:
- Full name: "Blockchain Payment Gateway & Smart Contract Invoicing for Your Webshop"
- Purpose: Enterprise-grade payment infrastructure combining Web2 (traditional cards/payment methods) and Web3 (cryptocurrency) payments with automated VAT compliance
- Key differentiators: Smart contract invoicing, multi-currency support, automatic tax calculation, blockchain transparency
- Target users: E-commerce merchants, SaaS companies, digital service providers
- Integration: REST API, WordPress plugin, WooCommerce, custom integrations

PLATFORM FEATURES:
1. Dual Payment Processing: Accept both traditional (credit/debit cards, bank transfers) and crypto (ETH, BTC, USDT, etc.)
2. Smart Contract Invoices: Blockchain-verified invoices with immutable records
3. Automatic VAT Calculation: Real-time tax calculation based on customer location and merchant country
4. Multi-Currency Support: Process payments in 150+ fiat currencies and 50+ cryptocurrencies
5. Compliance Automation: Automatic VAT reporting, invoice generation, audit trails
6. Developer-Friendly API: RESTful API with OAuth2, webhooks, sandbox environment
7. Dashboard Analytics: Real-time revenue tracking, payment method breakdown, geographic insights

API INTEGRATION BASICS:
- Base URL: https://api.apiblockchain.io
- Authentication: Bearer token (OAuth2)
- Key endpoints: /checkout/create, /invoice/create, /merchant/usage, /api-keys
- Webhook events: payment.completed, invoice.created, session.expired
- Test mode: Use test API keys for sandbox environment
- Plugin setup: Add script tag to website, configure API key, customize checkout flow

=== MERCHANT PROFILE ===

Name: {merchant.get('name', 'Unknown')}
Business location: {country_info['name']} ({merchant_country})
Address: {merchant.get('address', 'Not set')}, {merchant.get('city', '')}, {merchant.get('postal_code', '')}
VAT Number: {merchant.get('vat_number', 'Not registered')}
Total revenue: {country_info['currency']} {stats.get('total_amount', 0)}
Web2 transactions: {stats.get('web2_count', 0)}
Web3 transactions: {stats.get('web3_count', 0)}

=== COUNTRY-SPECIFIC VAT RULES FOR {country_info['name'].upper()} ===

- Standard VAT rate: {country_info['standard_rate']}%
- Reduced rates: {', '.join(map(str, country_info['reduced_rates']))}%
- Tax authority: {country_info['tax_authority']}
- VAT return frequency: {country_info['vat_return_frequency']}
- OSS threshold: {country_info['currency']} {country_info['oss_threshold']}
- Digital reporting: {country_info['digital_reporting']}
- Record retention: {country_info['record_retention_years']} years
- Reverse charge phrase: "{country_info['reverse_charge_phrase']}"

VAT RULES BY TRANSACTION TYPE:
- Domestic sales (same country): {country_info['standard_rate']}% VAT applies
- EU B2B (different countries): 0% VAT (reverse charge: "{country_info['reverse_charge_phrase']}")
- EU B2C (cross-border): Your VAT or destination VAT if sales exceed {country_info['currency']} {country_info['oss_threshold']}/year
- Non-EU exports: 0% VAT (export documentation required)
- Crypto payments: Same VAT rules apply (EU guidance: treat as payment method, not currency)

=== YOUR EXPERTISE ===

1. Platform Usage - How to use dashboard, create invoices, integrate API, troubleshoot issues
2. Country-Specific VAT Compliance - {country_info['name']} tax laws and regulations
3. Cross-Border Tax Rules - EU VAT, OSS scheme, international commerce, export/import
4. Invoice Requirements - Local legal compliance, mandatory fields per {country_info['name']} law
5. Digital Currency Taxation - Cryptocurrency VAT treatment, tax reporting, exchange rate handling
6. API Integration - Technical implementation, webhooks, authentication, error handling
7. Audit Preparation - {country_info['name']}-specific record keeping and documentation
8. Payment Optimization - Conversion rates, payment method selection, customer experience

=== RESPONSE GUIDELINES ===

- Provide accurate, practical advice specific to {country_info['name']} regulations
- For technical questions, include code examples or API references when relevant
- For tax questions, cite specific regulations and use correct legal terminology
- Be conversational but professional - merchants need guidance, not lectures
- If you don't know something specific, recommend contacting support rather than guessing
- Always prioritize legal compliance and security best practices
- Use merchant's data (from context) to personalize responses when applicable
"""
    
    # Simple AI responses (can be replaced with OpenAI API)
    try:
        # Check for OpenAI API key
        openai_key = os.getenv("OPENAI_API_KEY")
        
        if openai_key:
            # Use OpenAI if available
            import openai
            openai.api_key = openai_key
            
            messages = [
                {"role": "system", "content": context_info},
                *[{"role": msg["role"], "content": msg["content"]} for msg in history[-5:]],
                {"role": "user", "content": message}
            ]
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )
            
            reply = response.choices[0].message.content
        else:
            # Fallback to rule-based responses
            reply = generate_rule_based_response(message, stats, merchant)
            
    except Exception as e:
        # Fallback on error
        reply = generate_rule_based_response(message, stats, merchant)
    
    return {"reply": reply}


def generate_rule_based_response(message: str, stats: dict, merchant: dict) -> str:
    """Generate intelligent rule-based AI responses with context awareness and common sense."""
    msg_lower = message.lower()
    
    # Extract useful context
    web2_count = stats.get('web2_count', 0)
    web3_count = stats.get('web3_count', 0)
    total_amount = stats.get('total_amount', 0)
    
    # Plugin / integration guidance
    if any(word in msg_lower for word in ['plugin', 'integrate', 'integration', 'woocommerce', 'wordpress', 'setup']):
        return """**Plugin Integration (WordPress / WooCommerce):**

1. Install the APIBlockchain plugin in WordPress.
2. Go to Settings → API Keys in your dashboard and create a key.
3. Paste the API key into the plugin settings.
4. Choose payment methods (Web2, Web3, or both).
5. Save and run a test checkout.

If you tell me your platform (WordPress, WooCommerce, custom site), I’ll provide exact steps."""

    # Provide contextual insights based on merchant's activity
    if any(word in msg_lower for word in ['how', 'help', 'what', 'guide', 'tutorial']):
        if web2_count == 0 and web3_count == 0:
            # New merchant - guide them through getting started
            if any(word in msg_lower for word in ['start', 'begin', 'first', 'setup', 'integrate']):
                return """🚀 **Getting Started with APIBlockchain:**

1. **Get Your API Key**
   - Go to Settings → API Keys
   - Create a new key (test or live mode)
   - Copy and save securely

2. **Create Your First Checkout**
   - Use /checkout/create endpoint
   - Include product price, customer email
   - Configure payment methods (Web2, Web3, or both)

3. **Test Integration**
   - Use test API key first
   - Process a test transaction
   - Check webhook receipts

4. **Go Live**
   - Switch to live API key
   - Monitor transactions in Dashboard
   - Set up automatic reporting

📖 **Quick Links:**
- API Documentation: https://docs.apiblockchain.io
- Integration Examples: Check your plugin setup
- Support: support@apiblockchain.io

What's your integration method (API, plugin, custom)?"""
    
    # Smart recommendations based on activity
    elif web2_count > 50 and web3_count == 0:
        if any(word in msg_lower for word in ['web3', 'crypto', 'blockchain']):
            return """💡 **You're Missing Web3 Opportunities!**

Your metrics show strong Web2 sales (50+ transactions). Here's why you should enable Web3:

**Benefits:**
- ✅ Reach global crypto audience (no geographic limits)
- ✅ Instant settlements (vs 1-3 day bank transfers)
- ✅ Lower fraud risk (blockchain immutability)
- ✅ Appeal to tech-savvy customers
- ✅ Hedge against currency volatility

**Getting Started:**
1. Enable crypto payment methods in Dashboard
2. Choose currencies: ETH, BTC, USDT recommended for e-commerce
3. Test with small transactions first
4. Monitor conversion rates and optimize

**Risk**: Crypto volatility - consider auto-conversion to stablecoins (USDT, USDC) to lock in EUR value.

Ready to activate Web3 payments?"""
    
    elif web3_count > 10 and web2_count == 0:
        if any(word in msg_lower for word in ['web2', 'traditional', 'credit', 'card']):
            return """💡 **Expand Revenue with Web2 Payments!**

You're doing great with Web3 (10+ crypto transactions). Now capture mainstream customers:

**Why add Web2:**
- 🎯 70% of global commerce still uses cards/transfers
- 💰 Reach customers without crypto wallets
- 📈 Increase conversion rates
- 🌍 Support all customer types

**Methods to add:**
- Credit/Debit cards (Visa, Mastercard)
- Bank transfers (SEPA, wire)
- Digital wallets (Apple Pay, Google Pay)
- PayPal integration available

**Revenue impact:** Merchants adding both methods typically see 40% higher sales.

Want to enable Web2 payments?"""
    
    # Get merchant's country-specific info
    merchant_country = merchant.get('country', 'XX')
    country_info = get_country_vat_info(merchant_country)
    
    # VAT calculation questions
    if any(word in msg_lower for word in ['vat rate', 'tax rate', 'calculate vat', 'how much vat', 'vat percentage']):
        return f"""VAT rates for {country_info['name']} and cross-border sales:

**Your country ({country_info['name']}):**
- Standard VAT rate: {country_info['standard_rate']}% (applies to domestic sales)
- Reduced rates: {', '.join(map(str, country_info['reduced_rates']))}% (specific goods/services)
- Currency: {country_info['currency']}

**Domestic sales (B2B and B2C):** 
Charge {country_info['standard_rate']}% VAT on all sales within {country_info['name']}.

**EU Cross-border:**
- B2B (customer has valid EU VAT number): 0% VAT
  → Use reverse charge: "{country_info['reverse_charge_phrase']}"
- B2C (no VAT number): Your rate ({country_info['standard_rate']}%) applies until you exceed {country_info['currency']} {country_info['oss_threshold']}/year threshold

**Non-EU exports:** 0% VAT (proper export documentation required)

Our system automatically calculates correct VAT based on customer location and business status."""
    
    # Reverse charge mechanism
    elif any(word in msg_lower for word in ['reverse charge', 'b2b vat', 'vat exemption', 'zero vat']):
        return f"""**Reverse Charge Mechanism for {country_info['name']}:**

When you sell to an EU business (B2B) in a different country:
1. You charge 0% VAT on the invoice
2. You must validate their VAT number via VIES system
3. Invoice must include the phrase:
   📋 "{country_info['reverse_charge_phrase']}"
4. Your customer pays VAT in their own country (self-assessment)
5. Both parties report:
   - You: EC Sales List to {country_info['tax_authority']}
   - Customer: Intra-community acquisition in their country

**Important for {country_info['name']}:** Submit your EC Sales List {country_info['vat_return_frequency'].lower()}.

Our platform automatically applies reverse charge when customer provides valid EU VAT number."""
    
    # Invoice compliance
    elif any(word in msg_lower for word in ['invoice requirement', 'legal invoice', 'invoice compliance', 'mandatory field', 'invoice law']):
        requirements = '\n'.join([f"   • {req}" for req in country_info['invoice_requirements']])
        return f"""**Legally Compliant Invoice Requirements for {country_info['name']}:**

**Mandatory fields per {country_info['name']} law:**
1. ✅ Sequential invoice number (no gaps allowed)
2. ✅ Issue date and supply date
3. ✅ Your business details (name, address, VAT number)
4. ✅ Customer details (name, address, VAT number for B2B)
5. ✅ Item descriptions, quantities, unit prices
6. ✅ VAT breakdown by rate ({country_info['standard_rate']}% standard)
7. ✅ Total amounts (subtotal, VAT, grand total in {country_info['currency']})
8. ✅ Payment terms and due date

**Country-specific requirements:**
{requirements}

**Record retention:** Keep invoices for {country_info['record_retention_years']} years per {country_info['name']} law.
**Digital compliance:** {country_info['digital_reporting']}

All our auto-generated invoices meet {country_info['name']} legal requirements."""
    
    # Cryptocurrency taxation
    elif any(word in msg_lower for word in ['crypto tax', 'cryptocurrency vat', 'bitcoin tax', 'web3 tax', 'blockchain tax']):
        return """**Cryptocurrency & Web3 Payment Taxation:**

**VAT Treatment (EU guidance):**
- Cryptocurrency is treated as a medium of payment, NOT a good
- Same VAT rules apply as traditional payments
- No VAT charged on the cryptocurrency itself
- VAT applies to the goods/services being purchased

**Example:** 
- Customer pays 0.01 BTC for €500 product (21% VAT)
- You charge: €500 + €105 VAT = €605 total
- VAT doesn't change because payment was in crypto

**Tax Reporting:**
- Report based on EUR value at transaction time
- Keep records of exchange rates used
- Web3 transactions have same VAT obligations as Web2

**Capital Gains:** If you hold crypto, separate capital gains tax may apply on price fluctuations (merchant's responsibility)."""
    
    # OSS/MOSS schemes
    elif any(word in msg_lower for word in ['oss', 'moss', 'one stop shop', 'distance selling', 'vat threshold']):
        if country_info['oss_threshold'] > 0:
            return f"""**EU One-Stop Shop (OSS) Scheme for {country_info['name']}:**

**When to register:**
- Selling to EU consumers (B2C) across borders
- Annual cross-border EU B2C sales exceed {country_info['currency']} {country_info['oss_threshold']}
- Want to simplify multi-country VAT compliance

**Benefits:**
1. Register through {country_info['tax_authority']} ({country_info['name']})
2. Declare all EU B2C sales in single quarterly return
3. OSS portal distributes VAT to destination countries
4. Avoid registering for VAT in every EU country

**How it works:**
- Below {country_info['currency']} {country_info['oss_threshold']}: Charge your rate ({country_info['standard_rate']}%)
- Above threshold: Charge destination country's VAT rate
- Submit quarterly return to {country_info['tax_authority']}
- Make single payment - they distribute to other countries

**Important:** B2B sales (reverse charge) are separate - NOT included in OSS.

**Registration:** Contact {country_info['tax_authority']} or register online through your tax portal."""
        else:
            return f"""**Note for {country_info['name']}:** {'OSS (One-Stop Shop) is an EU scheme. As a non-EU country, different rules apply for cross-border sales.' if merchant_country == 'US' else 'OSS scheme details vary - consult with local tax authority.'}"""
    
    # VAT number validation
    elif any(word in msg_lower for word in ['validate vat', 'vat number', 'vies', 'check vat', 'verify vat']):
        return """**VAT Number Validation:**

**Why it matters:**
- Determines if reverse charge applies (0% VAT for valid EU B2B)
- Legal requirement before applying reverse charge
- Proves customer is legitimate business

**How to validate:**
1. Use EU VIES system (vat.europa.eu)
2. Format: 2-letter country code + digits (e.g., DE123456789, NL123456789B01)
3. API available for automated checks

**Our platform:**
- Integrates VIES validation
- Automatically applies correct VAT rules based on validation result
- Stores validation timestamps for audit trail

**Best practice:** Validate at checkout AND keep validation records for 10 years (audit requirement)."""
    
    # Record keeping & audits
    elif any(word in msg_lower for word in ['audit', 'record keeping', 'documentation', 'tax record', 'compliance check']):
        return f"""**VAT Record Keeping & Audit Compliance for {country_info['name']}:**

**Required records (keep {country_info['record_retention_years']} years per {country_info['name']} law):**
1. ✅ All invoices (issued and received)
2. ✅ VAT returns and calculations submitted to {country_info['tax_authority']}
3. ✅ Credit notes and corrections
4. ✅ Bank statements and payment proof
5. ✅ VAT number validation confirmations (VIES for EU B2B)
6. ✅ Export documentation (customs, shipping, proof of export)
7. ✅ Contracts with customers/suppliers
8. ✅ Accounting books and ledgers

**{country_info['name']}-specific digital requirements:**
{country_info['digital_reporting']}
- Sequential numbering (no gaps allowed)
- Tamper-proof storage (blockchain timestamps ideal)

**Audit preparation checklist:**
- Reconcile {country_info['vat_return_frequency'].lower()} VAT returns with invoices
- Ensure all exports have customs proof
- Verify all reverse charges have valid VAT numbers
- Check invoice sequences are complete
- Confirm {country_info['standard_rate']}% rate applied correctly

**Tax authority contact:** {country_info['tax_authority']}

Our platform automatically maintains {country_info['name']}-compliant records."""
    
    # Blockchain transactions (status, confirmations, compliance)
    elif any(word in msg_lower for word in ['blockchain transaction', 'blockchain transactions', 'web3 transaction', 'crypto transaction', 'txid', 'transaction id', 'confirmations', 'on-chain']):
        return """**Blockchain Transaction Guidance:**

**What you’ll see:**
- On-chain TX ID (hash) and network (e.g., ETH, BTC)
- Confirmation status (pending → confirmed)
- Settlement time: minutes for Web3, 1–3 days for cards

**Compliance basics:**
- Treat crypto as a payment method; VAT applies like Web2
- Record the EUR value at payment time
- Keep TX ID as audit evidence

Need help reconciling a specific transaction? Share the TX ID."""

    # Cryptocurrency specific regulations
    elif any(word in msg_lower for word in ['crypto regulation', '5th directive', 'aml', 'kyc crypto', 'crypto compliance']):
        return """**Cryptocurrency Compliance & Regulations:**

**EU 5th Anti-Money Laundering Directive (5AMLD):**
- Crypto businesses must register with financial authorities
- KYC (Know Your Customer) required for transactions >€1000
- AML (Anti-Money Laundering) screening mandatory
- Transaction monitoring for suspicious activity

**Reporting obligations:**
- Large transactions (>€10,000) reported to authorities
- Cross-border payments tracked
- Maintain customer identification records

**Tax transparency:**
- DAC8 directive: Crypto platforms must report to tax authorities
- Customer transaction history shared between EU countries
- Automatic exchange of tax information

**Your obligations as merchant:**
- Keep records of all crypto payments
- Report revenue correctly (at EUR value)
- Comply with customer verification if volumes are high
- Partner with compliant payment processors (like us!)

We handle compliance infrastructure so you can focus on your business."""
    
    # EU reverse charge & cross-border VAT/OSS
    elif any(word in msg_lower for word in ['reverse charge', 'oss', 'one stop shop', 'cross-border', 'international vat', 'eu vat']):
        return f"""**International VAT (EU) Summary for {country_info['name']}:**

**Domestic sales:** Charge {country_info['standard_rate']}% VAT.

**EU B2B:** Reverse charge applies if customer has a valid EU VAT number.
Use the phrase: "{country_info['reverse_charge_phrase']}".

**EU B2C (cross‑border):**
- Below {country_info['currency']} {country_info['oss_threshold']}: charge your local rate
- Above threshold: charge destination country VAT
- Use OSS to file a single quarterly return via {country_info['tax_authority']}

**Exports (non‑EU):** Usually 0% VAT with proof of export.

I can explain any scenario in detail if you share customer country + B2B/B2C."""

    # Revenue trend insights (requires time-series data)
    elif any(word in msg_lower for word in ['trend', 'over time', 'growth', 'month', 'monthly', 'week', 'weekly', 'daily']):
        total = float(stats.get('total_amount', 0))
        web2 = stats.get('web2_count', 0)
        web3 = stats.get('web3_count', 0)
        return f"""**Revenue Trend Overview ({country_info['name']}):**

I can’t calculate a true trend without time-series data (daily/weekly/monthly totals). Right now I only have your current snapshot:
- Total revenue: {country_info['currency']} {total:,.2f}
- Web2 (traditional): {web2} transactions
- Web3 (blockchain): {web3} transactions

If you want a trend breakdown, share a date range (e.g., last 30/90 days) or enable analytics time-series in the dashboard, and I’ll analyze direction, volatility, and mix shifts."""
    # Revenue insights with compliance context
    elif any(word in msg_lower for word in ['revenue', 'earning', 'money', 'income', 'sales']):
        total = float(stats.get('total_amount', 0))
        web2 = stats.get('web2_count', 0)
        web3 = stats.get('web3_count', 0)
        if total > 0:
            return f"""**Your Revenue & Tax Obligations ({country_info['name']}):**

Total revenue: {country_info['currency']} {total:,.2f}
- Web2 (traditional): {web2} transactions
- Web3 (blockchain): {web3} transactions

**Tax reminders for {country_info['name']}:**
- All revenue is taxable (both Web2 and Web3)
- VAT returns due: {country_info['vat_return_frequency']}
- Submit to: {country_info['tax_authority']}
- Standard rate: {country_info['standard_rate']}%
- Keep records: {country_info['record_retention_years']} years
- Crypto needs {country_info['currency']} valuation at payment time

**OSS threshold check:** {f'You have exceeded the {country_info["currency"]} {country_info["oss_threshold"]} threshold - consider OSS registration' if total > country_info['oss_threshold'] else f'Below {country_info["currency"]} {country_info["oss_threshold"]} threshold - OSS optional'} for EU B2C cross-border sales.

Need help with VAT compliance? Just ask!"""
        else:
            return f"You haven't processed any transactions yet. Once you start receiving payments, I'll help you understand {country_info['name']} VAT obligations ({country_info['standard_rate']}% standard rate), ensure compliance with {country_info['tax_authority']}, and optimize your tax reporting!"
    
    # Invoice generation questions
    elif any(word in msg_lower for word in ['invoice', 'billing', 'receipt', 'create invoice']):
        return """**Automatic Invoice Generation:**

Our system creates legally compliant invoices automatically when payments complete:

**Included automatically:**
✅ Sequential invoice numbering
✅ Your business details and VAT number
✅ Customer information
✅ Correct VAT calculation (based on location & B2B/B2C status)
✅ All mandatory legal fields
✅ Reverse charge notation (when applicable)
✅ Tamper-proof blockchain timestamp

**You can:**
- View all invoices in the Invoices section
- Download as PDF (legally valid)
- Resend to customers
- Generate credit notes if needed

**Compliance guaranteed:** All invoices meet EU Directive 2014/55 requirements for electronic invoicing."""
    
    # General VAT explanation
    elif any(word in msg_lower for word in ['what is vat', 'explain vat', 'vat basics', 'understand vat']):
        return """**VAT (Value Added Tax) Basics:**

**What it is:**
- Consumption tax collected at each stage of supply chain
- Businesses collect VAT from customers, pay to tax authorities
- Final consumer bears the cost

**How it works:**
1. You charge VAT on sales (output VAT)
2. You pay VAT on business purchases (input VAT)
3. You pay difference to tax authorities: Output - Input = VAT payment

**Rates:**
- Standard rate: 15-25% (varies by country)
- Reduced rate: 5-12% (food, books, medicines)
- Zero rate: 0% (exports, some essentials)

**Cross-border:**
- Different rules for B2B vs B2C
- EU has harmonized system with country variations
- Reverse charge simplifies B2B transactions

**Your responsibilities:**
- Charge correct VAT rate
- Issue compliant invoices
- File quarterly VAT returns
- Pay collected VAT to authorities

Our platform automates correct VAT calculation for all scenarios."""
    
    # Default response focused on compliance
    else:
        return f"""Hi {merchant.get('name', 'there')}! I'm your VAT & compliance specialist for {country_info['name']}.

**Your country details:**
📍 Location: {country_info['name']} ({merchant_country})
💰 Standard VAT rate: {country_info['standard_rate']}%
🏛️ Tax authority: {country_info['tax_authority']}
📅 VAT returns: {country_info['vat_return_frequency']}
💱 Currency: {country_info['currency']}

**I can help you with:**
- {country_info['name']}-specific VAT rules and compliance
- Cross-border tax (EU B2B/B2C, exports)
- Invoice requirements per {country_info['name']} law
- Cryptocurrency taxation in {country_info['name']}
- Reverse charge: "{country_info['reverse_charge_phrase'][:50]}..."
- OSS registration (threshold: {country_info['currency']} {country_info['oss_threshold']})
- Audit preparation ({country_info['record_retention_years']} years records)
- {country_info['tax_authority']} communication

**Ask me questions like:**
- "What VAT rate do I charge?"
- "How does reverse charge work in {country_info['name']}?"
- "What are {country_info['name']} invoice requirements?"
- "Do I need OSS registration?"
- "How is crypto taxed in {country_info['name']}?"

What would you like to know?"""


@app.get("/invoices/{invoice_id}/pdf")
async def download_invoice_pdf(invoice_id: str, current_user: dict = Depends(get_current_user)):
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

    # Generate comprehensive international invoice PDF with all details
    items = inv.get("items", [])
    first_item = items[0] if items else {}
    
    # Determine tax treatment based on invoice data
    is_b2b = inv.get("buyer_type") == "B2B" or (inv.get("buyer_vat") and inv.get("buyer_vat").strip())
    is_reverse_charge = is_b2b and inv.get("seller_country") and inv.get("buyer_country") and inv.get("seller_country") != inv.get("buyer_country")
    is_export = inv.get("is_export", False)
    is_outside_scope = inv.get("is_outside_scope", False)
    tax_exempt_reason = inv.get("tax_exempt_reason")
    
    # Determine tax treatment statement
    tax_treatment = inv.get("tax_treatment")
    if not tax_treatment and not (is_reverse_charge or is_export or is_outside_scope or tax_exempt_reason):
        tax_treatment = "Tax calculated in accordance with local regulations."
    
    pdf_req = InvoicePDFRequest(
        # Header
        logo_url=inv.get("logo_url"),
        invoice_number=inv.get("invoice_number", invoice_id),
        invoice_date=inv.get("created_at", inv.get("date_issued", "")),
        supply_date=inv.get("supply_date"),
        currency=inv.get("currency", "EUR"),
        
        # Seller Information
        seller=inv.get("seller_name", "Unknown Seller"),
        seller_address=inv.get("seller_address"),
        seller_country=inv.get("seller_country"),
        seller_registration_number=inv.get("seller_registration_number"),
        seller_vat=inv.get("seller_vat"),
        seller_eori=inv.get("seller_eori"),
        seller_email=inv.get("seller_email"),
        seller_phone=inv.get("seller_phone"),
        
        # Buyer Information
        buyer=inv.get("buyer_name", "Unknown Buyer"),
        buyer_address=inv.get("buyer_address"),
        buyer_country=inv.get("buyer_country"),
        buyer_vat=inv.get("buyer_vat"),
        buyer_registration_number=inv.get("buyer_registration_number"),
        buyer_email=inv.get("buyer_email"),
        buyer_phone=inv.get("buyer_phone"),
        buyer_type=inv.get("buyer_type"),
        
        # Items (Tax-Safe Format)
        description=inv.get("description") or (first_item.get("description") if first_item else ""),
        quantity=first_item.get("quantity", 1),
        unit_price=first_item.get("unit_price", inv.get("total", 0)),
        net_amount=inv.get("subtotal"),
        vat_rate=inv.get("vat_rate", 0),
        vat_amount=inv.get("vat_amount", 0),
        total_amount=inv.get("total", 0),
        order_number=inv.get("order_number"),
        due_date=inv.get("due_date"),
        
        # Tax Information (Flexible)
        tax_treatment=tax_treatment,
        is_reverse_charge=is_reverse_charge,
        is_export=is_export,
        is_outside_scope=is_outside_scope,
        tax_exempt_reason=tax_exempt_reason,
        
        # Payment Information
        payment_terms=inv.get("payment_terms"),
        payment_system=inv.get("payment_system", "web2"),
        payment_provider=inv.get("payment_provider"),
        blockchain_tx_id=inv.get("blockchain_tx_id"),
        bank_name=inv.get("bank_name"),
        iban=inv.get("iban"),
        swift_bic=inv.get("swift_bic"),
        alternative_payment_methods=inv.get("alternative_payment_methods"),
        late_payment_clause=inv.get("late_payment_clause"),
        
        # Additional Info
        notes=inv.get("notes"),
        footer_statement=inv.get("footer_statement"),
        registered_office=inv.get("registered_office"),
    )
    pdf_bytes = render_invoice_pdf(pdf_req)
    return Response(content=pdf_bytes, media_type="application/pdf")


@app.post("/validate-vat")
async def validate_vat_number(payload: dict = Body(...), current_user: dict = Depends(get_current_user)):
    """
    Validate a VAT number using the EU VIES system.
    
    Request:
    {
        "vat_number": "DE123456789",  # Required: Country code + VAT number
        "buyer_name": "Company Name"   # Optional: For reference
    }
    
    Response:
    {
        "valid": true|false,
        "vat_number": "DE123456789",
        "country": "DE",
        "company_name": "Company registered name" (if valid),
        "address": "Company address" (if valid),
        "message": "VAT number is valid and compliant" | "VAT number is not registered" | "Invalid VAT format"
    }
    """
    try:
        vat_number = (payload.get("vat_number") or "").strip().upper().replace(" ", "")
        
        if not vat_number:
            raise HTTPException(status_code=400, detail="vat_number is required")
        
        # Validate format: should be 2-letter country code + at least 5 digits/letters
        if len(vat_number) < 7 or not vat_number[:2].isalpha():
            return {
                "valid": False,
                "vat_number": vat_number,
                "country": vat_number[:2] if len(vat_number) >= 2 else "??",
                "message": "Invalid VAT format. Expected format: CCNNNNNNNNN (e.g., DE123456789, FR12345678901)"
            }
        
        country_code = vat_number[:2]
        vat_nr = vat_number[2:]
        
        # VIES only works for EU countries, so check if it's an EU code
        eu_countries = {'AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 
                       'GR', 'HU', 'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL', 'PL', 'PT', 
                       'RO', 'SK', 'SI', 'ES', 'SE', 'GB', 'XI', 'EL', 'GE'}
        
        if country_code not in eu_countries:
            return {
                "valid": False,
                "vat_number": vat_number,
                "country": country_code,
                "message": f"VIES validation is only available for EU countries. Country '{country_code}' is not in the EU VIES system."
            }
        
        # Try to connect to VIES service
        try:
            from zeep import Client
            from zeep.exceptions import Fault
            
            wsdl_url = "https://ec.europa.eu/taxation_customs/vies/checkVatService.wsdl"
            client = Client(wsdl=wsdl_url)
            
            # Call VIES checkVat service
            response = client.service.checkVat(countryCode=country_code, vatNumber=vat_nr)
            
            # Extract response details
            is_valid = getattr(response, 'valid', False)
            company_name = getattr(response, 'name', None)
            company_address = getattr(response, 'address', None)
            
            if is_valid:
                return {
                    "valid": True,
                    "vat_number": vat_number,
                    "country": country_code,
                    "company_name": company_name or "Name not provided by VIES",
                    "address": company_address or "Address not provided by VIES",
                    "message": "✓ VAT number is valid and registered in the EU VIES system"
                }
            else:
                return {
                    "valid": False,
                    "vat_number": vat_number,
                    "country": country_code,
                    "message": "✗ VAT number is not registered in the EU VIES system or is invalid"
                }
        
        except Fault as e:
            # VIES service fault (e.g., invalid format, temporary service issue)
            error_msg = str(e)
            if "INVALID_INPUT" in error_msg or "invalid" in error_msg.lower():
                return {
                    "valid": False,
                    "vat_number": vat_number,
                    "country": country_code,
                    "message": "✗ Invalid VAT number format. The VAT number does not match the expected format for this country."
                }
            else:
                return {
                    "valid": False,
                    "vat_number": vat_number,
                    "country": country_code,
                    "message": f"VIES service error: {error_msg}"
                }
        
        except Exception as e:
            # Network error, service unavailable, etc.
            import traceback
            traceback.print_exc()
            return {
                "valid": None,
                "vat_number": vat_number,
                "country": country_code,
                "message": f"⚠ Could not reach VIES service. Please try again later. Error: {str(e)}"
            }
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"VAT validation error: {str(e)}")


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
            "buyer_country": payload.get("buyer_country") or payload.get("country"),  # For VAT calculation
            "buyer_vat_number": payload.get("buyer_vat_number") or payload.get("vat_number"),  # For B2B reverse charge
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


@app.post('/webhooks/paypal')
def webhook_paypal(payload: dict = Body(...), request: Request = None):
    """PayPal webhook: PAYMENT.CAPTURE.COMPLETED -> mark session PAID."""
    if READ_ONLY_FS:
        return JSONResponse(status_code=503, content={"error": "Persistence disabled"})
    
    event_type = payload.get('event_type', '')
    if event_type != 'PAYMENT.CAPTURE.COMPLETED':
        log_event(f'WEBHOOK_PAYPAL_IGNORED event_type={event_type}', '-', '-')
        return {"received": True}
    
    resource = payload.get('resource', {})
    session_id = resource.get('custom_id') or resource.get('invoice_id', '')
    
    if not session_id:
        log_event('WEBHOOK_PAYPAL_NO_SESSION_ID', '-', '-')
        return JSONResponse(status_code=400, content={"error": "No session_id in webhook"})
    
    try:
        sessions = load_sessions()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    
    session = next((s for s in sessions if s.get('id') == session_id), None)
    if not session:
        log_event(f'WEBHOOK_PAYPAL_SESSION_NOT_FOUND session_id={session_id[:8]}', '-', '-')
        return JSONResponse(status_code=404, content={"error": "Session not found"})
    
    if session.get('status') in ['paid', 'failed']:
        return {"success": True, "message": f"Session already in terminal state: {session.get('status')}"}
    
    if not validate_payment_state_transition(session.get('status', 'created'), 'paid'):
        return JSONResponse(status_code=409, content={"error": "Invalid state transition"})
    
    session['status'] = 'paid'
    session['payment_status'] = 'completed'
    session['paid_at'] = datetime.utcnow().isoformat()
    session['payment_provider'] = 'paypal'
    session['paypal_capture_id'] = resource.get('id')
    session['metadata']['webhook_sources'].append('paypal')
    
    try:
        invoices = load_invoices()
    except Exception:
        invoices = []
    
    amount_value = float(resource.get('amount', {}).get('value', session.get('amount', 0)))
    
    # Get merchant and buyer countries for VAT calculation
    merchant_id = session.get('merchant_id')
    users = load_users()
    merchant = next((u for u in users if u.get('id') == merchant_id), None)
    seller_country = merchant.get('country', 'NL') if merchant else 'NL'
    
    buyer_country = session.get('metadata', {}).get('buyer_country') or session.get('metadata', {}).get('country') or 'NL'
    buyer_vat = session.get('metadata', {}).get('buyer_vat_number') or session.get('metadata', {}).get('vat_number')
    
    # Calculate tax (international)
    vat_rate, is_reverse_charge, vat_explanation = determine_tax_rate(seller_country, buyer_country, buyer_vat)
    subtotal = amount_value / (1 + vat_rate / 100) if vat_rate > 0 else amount_value
    vat_amount = amount_value - subtotal
        'id': str(uuid.uuid4()),
        'session_id': session_id,
        'merchant_id': session.get('merchant_id'),
        'subtotal': round(subtotal, 2),
        'vat_rate': vat_rate,
        'vat_amount': round(vat_amount, 2),
        'total': amount_value,
        'amount': amount_value,
        'currency': resource.get('amount', {}).get('currency_code', 'EUR'),
        'seller_country': seller_country,
        'buyer_country': buyer_country,
        'buyer_vat': buyer_vat,
        'is_reverse_charge': is_reverse_charge,
        'mode': session.get('mode', 'test'),
        'status': 'paid',
        'payment_provider': 'paypal',
        'paypal_capture_id': resource.get('id'),
        'created_at': datetime.utcnow().isoformat(),
        'notes': vat_explanation,
    }
    invoices.append(invoice)
    
    api_key = auto_unlock_api_keys(session.get('merchant_id'), session)
    access_link = generate_customer_access_link(session_id, session.get('merchant_id'))
    
    try:
        save_sessions(sessions)
        save_invoices(invoices)
    except Exception as e:
        log_event(f'WEBHOOK_PAYPAL_PERSIST_FAILED {str(e)[:50]}', '-', '-')
        return JSONResponse(status_code=500, content={"error": "Failed to persist"})
    
    log_event(f'WEBHOOK_PAYPAL_SUCCESS session_id={session_id[:8]} amount={amount_value}', '-', '-')
    
    return {
        "success": True,
        "session_id": session_id,
        "invoice": invoice,
        "api_key_generated": api_key.get('id'),
        "customer_access": access_link,
    }


@app.post('/api/coinbase/create-charge')
def create_coinbase_charge(data: dict = Body(...)):
    """
    Create a Coinbase Commerce charge for crypto payment.
    Expects: { session_id, amount, currency, name, description }
    Returns: { hosted_url, charge_id }
    """
    import requests
    
    if not COINBASE_COMMERCE_API_KEY:
        return JSONResponse(status_code=503, content={"error": "Coinbase Commerce not configured"})
    
    session_id = data.get('session_id')
    amount = data.get('amount')
    currency = data.get('currency', 'EUR')
    name = data.get('name', 'API Blockchain Subscription')
    description = data.get('description', 'Monthly subscription')
    
    if not session_id or not amount:
        return JSONResponse(status_code=400, content={"error": "session_id and amount required"})
    
    # Create Coinbase Commerce charge
    charge_data = {
        "name": name,
        "description": description,
        "pricing_type": "fixed_price",
        "local_price": {
            "amount": str(amount),
            "currency": currency
        },
        "metadata": {
            "session_id": session_id
        },
        "redirect_url": "https://dashboard.apiblockchain.io/success",
        "cancel_url": "https://dashboard.apiblockchain.io/checkout.html"
    }
    
    try:
        response = requests.post(
            'https://api.commerce.coinbase.com/charges',
            json=charge_data,
            headers={
                'X-CC-Api-Key': COINBASE_COMMERCE_API_KEY,
                'X-CC-Version': '2018-03-22',
                'Content-Type': 'application/json'
            },
            timeout=10
        )
        response.raise_for_status()
        charge = response.json().get('data', {})
        
        log_event(f'COINBASE_CHARGE_CREATED session_id={session_id[:8]} charge_id={charge.get("id", "")[:8]}', '-', '-')
        
        return {
            "success": True,
            "hosted_url": charge.get('hosted_url'),
            "charge_id": charge.get('id'),
            "expires_at": charge.get('expires_at')
        }
    except requests.exceptions.RequestException as e:
        log_event(f'COINBASE_CHARGE_FAILED {str(e)[:100]}', '-', '-')
        return JSONResponse(status_code=500, content={"error": f"Failed to create charge: {str(e)}"})


@app.post('/webhooks/coinbase')
async def webhook_coinbase(request: Request):
    """
    Coinbase Commerce webhook handler.
    Handles charge:confirmed, charge:failed, charge:pending events.
    """
    if READ_ONLY_FS:
        return JSONResponse(status_code=503, content={"error": "Persistence disabled"})
    
    import hmac
    import hashlib
    
    # Get raw body for signature verification
    body = await request.body()
    
    # Verify webhook signature if secret is configured
    if COINBASE_WEBHOOK_SECRET:
        signature = request.headers.get('X-CC-Webhook-Signature', '')
        expected_sig = hmac.new(
            COINBASE_WEBHOOK_SECRET.encode('utf-8'),
            body,
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_sig):
            log_event('WEBHOOK_COINBASE_INVALID_SIGNATURE', '-', '-')
            return JSONResponse(status_code=401, content={"error": "Invalid signature"})
    
    try:
        payload = json.loads(body.decode('utf-8'))
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": f"Invalid JSON: {str(e)}"})
    
    event_type = payload.get('event', {}).get('type', '')
    event_data = payload.get('event', {}).get('data', {})
    
    # Only process confirmed charges
    if event_type != 'charge:confirmed':
        log_event(f'WEBHOOK_COINBASE_IGNORED event_type={event_type}', '-', '-')
        return {"received": True}
    
    metadata = event_data.get('metadata', {})
    session_id = metadata.get('session_id', '')
    
    if not session_id:
        log_event('WEBHOOK_COINBASE_NO_SESSION_ID', '-', '-')
        return JSONResponse(status_code=400, content={"error": "No session_id in metadata"})
    
    try:
        sessions = load_sessions()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    
    session = next((s for s in sessions if s.get('id') == session_id), None)
    if not session:
        log_event(f'WEBHOOK_COINBASE_SESSION_NOT_FOUND session_id={session_id[:8]}', '-', '-')
        return JSONResponse(status_code=404, content={"error": "Session not found"})
    
    if session.get('status') in ['paid', 'failed']:
        return {"success": True, "message": f"Session already in terminal state: {session.get('status')}"}
    
    if not validate_payment_state_transition(session.get('status', 'created'), 'paid'):
        return JSONResponse(status_code=409, content={"error": "Invalid state transition"})
    
    # Update session
    session['status'] = 'paid'
    session['payment_status'] = 'completed'
    session['paid_at'] = datetime.utcnow().isoformat()
    session['payment_provider'] = 'coinbase'
    session['coinbase_charge_id'] = event_data.get('id')
    session['metadata']['webhook_sources'].append('coinbase')
    
    # Get payment details
    pricing = event_data.get('pricing', {})
    local_price = pricing.get('local', {})
    amount_value = float(local_price.get('amount', session.get('amount', 0)))
    currency = local_price.get('currency', 'EUR')
    
    # Get crypto payment details
    payments = event_data.get('payments', [])
    crypto_payment = payments[0] if payments else {}
    
    # Get merchant and buyer countries for VAT calculation
    merchant_id = session.get('merchant_id')
    users = load_users()
    merchant = next((u for u in users if u.get('id') == merchant_id), None)
    seller_country = merchant.get('country', 'NL') if merchant else 'NL'
    
    buyer_country = session.get('metadata', {}).get('buyer_country') or session.get('metadata', {}).get('country') or 'NL'
    buyer_vat = session.get('metadata', {}).get('buyer_vat_number') or session.get('metadata', {}).get('vat_number')
    
    # Calculate tax (international)
    vat_rate, is_reverse_charge, vat_explanation = determine_tax_rate(seller_country, buyer_country, buyer_vat)
    subtotal = amount_value / (1 + vat_rate / 100) if vat_rate > 0 else amount_value
    vat_amount = amount_value - subtotal
    
    try:
        invoices = load_invoices()
    except Exception:
        invoices = []
    
    invoice = {
        'id': str(uuid.uuid4()),
        'session_id': session_id,
        'merchant_id': session.get('merchant_id'),
        'subtotal': round(subtotal, 2),
        'vat_rate': vat_rate,
        'vat_amount': round(vat_amount, 2),
        'total': amount_value,
        'amount': amount_value,
        'currency': currency,
        'seller_country': seller_country,
        'buyer_country': buyer_country,
        'buyer_vat': buyer_vat,
        'is_reverse_charge': is_reverse_charge,
        'mode': session.get('mode', 'live'),
        'status': 'paid',
        'payment_provider': 'coinbase',
        'coinbase_charge_id': event_data.get('id'),
        'crypto_amount': crypto_payment.get('value', {}).get('crypto', {}).get('amount'),
        'crypto_currency': crypto_payment.get('value', {}).get('crypto', {}).get('currency'),
        'transaction_id': crypto_payment.get('transaction_id'),
        'created_at': datetime.utcnow().isoformat(),
        'notes': vat_explanation,
    }
    invoices.append(invoice)
    
    api_key = auto_unlock_api_keys(session.get('merchant_id'), session)
    access_link = generate_customer_access_link(session_id, session.get('merchant_id'))
    
    try:
        save_sessions(sessions)
        save_invoices(invoices)
    except Exception as e:
        log_event(f'WEBHOOK_COINBASE_PERSIST_FAILED {str(e)[:50]}', '-', '-')
        return JSONResponse(status_code=500, content={"error": "Failed to persist"})
    
    log_event(f'WEBHOOK_COINBASE_SUCCESS session_id={session_id[:8]} amount={amount_value} {currency}', '-', '-')
    
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


# === Payment Processing Endpoints ===

class PaymentRequest(BaseModel):
    paymentMethodId: str = Field(..., description="Stripe payment method ID")
    amount: int = Field(..., description="Amount in cents")
    currency: str = Field(default="eur", description="Currency code")
    email: str = Field(..., description="Customer email")
    business: str = Field(default="", description="Business name")


@app.post('/api/process-payment')
def process_payment(request: PaymentRequest):
    """
    Process a payment for webshop checkout.
    Returns order ID and success status.
    """
    try:
        import stripe
        stripe_key = os.getenv("STRIPE_SECRET_KEY")
        if not stripe_key:
            return JSONResponse(
                status_code=500, 
                content={"error": "Payment processor not configured"}
            )
        
        stripe.api_key = stripe_key
        
        # Create a payment intent
        intent = stripe.PaymentIntent.create(
            amount=request.amount,
            currency=request.currency,
            payment_method=request.paymentMethodId,
            confirm=True,
            off_session=True,
        )
        
        # Log successful payment
        order_id = f"ORD-{int(time())}-{uuid.uuid4().hex[:8].upper()}"
        log_event(
            f'PAYMENT_SUCCESS order_id={order_id} email={request.email} amount={request.amount/100:.2f}{request.currency.upper()}',
            request.email,
            '-'
        )
        
        # Save order to invoices file
        try:
            invoices = load_invoices()
        except Exception:
            invoices = []
        
        order = {
            'id': order_id,
            'email': request.email,
            'business': request.business,
            'amount': request.amount,
            'currency': request.currency,
            'status': 'completed',
            'payment_method': 'stripe',
            'stripe_intent_id': intent.id,
            'created_at': datetime.utcnow().isoformat(),
            'services': [
                'Blockchain Payment Gateway Setup',
                'Smart Contract Invoicing Integration'
            ],
        }
        invoices.append(order)
        
        if not READ_ONLY_FS:
            try:
                save_invoices(invoices)
            except Exception as e:
                print(f"[WARN] Could not save invoice: {e}")
        
        return {
            "success": True,
            "orderId": order_id,
            "status": intent.status,
            "amount": request.amount,
            "currency": request.currency,
            "message": "Payment processed successfully. Our team will contact you soon."
        }
    
    except Exception as e:
        error_msg = str(e)
        log_event(f'PAYMENT_ERROR email={request.email} error={error_msg}', request.email, '-')
        return JSONResponse(
            status_code=400,
            content={"error": f"Payment failed: {error_msg}", "success": False}
        )
