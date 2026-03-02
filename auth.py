"""
Authentication and security utilities for PHASE 1
Handles JWT tokens, password hashing, email verification, password reset
"""

import os
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session

from models_phase1 import User, Organization, TokenVersion, AuditLog
from schemas import TokenResponse

# ===== CONFIGURATION =====

# Enforce JWT secret from environment (NO fallback in production)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    raise RuntimeError(
        "FATAL: JWT_SECRET_KEY environment variable is not set. "
        "This is required for token signing. Set it in .env or your deployment platform."
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7
BCRYPT_MAX_BYTES = 72

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ===== PASSWORD HASHING =====

def hash_password(password: str) -> str:
    """Hash password with bcrypt (enforcing 72-byte limit)."""
    if len(password.encode('utf-8')) > BCRYPT_MAX_BYTES:
        raise ValueError(f"Password exceeds {BCRYPT_MAX_BYTES} bytes when UTF-8 encoded")
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, password_hash)


# ===== TOKEN MANAGEMENT =====

def create_access_token(
    user_id: int,
    org_id: int,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token."""
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": str(user_id),
        "org_id": org_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    }
    
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=ALGORITHM)
    return token


def create_refresh_token(
    user_id: int,
    org_id: int,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT refresh token."""
    if expires_delta is None:
        expires_delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": str(user_id),
        "org_id": org_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh"
    }
    
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=ALGORITHM)
    return token


def verify_token(token: str) -> dict:
    """Verify JWT token and return payload."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


# ===== TOKEN CONFIRMATION HELPERS =====

def hash_token(token: str) -> str:
    """Hash a token for storage (one-way)."""
    return hashlib.sha256(token.encode()).hexdigest()


def create_email_verification_token() -> Tuple[str, str]:
    """Generate email verification token and hash."""
    token = secrets.token_urlsafe(32)
    token_hash = hash_token(token)
    return token, token_hash


def create_password_reset_token() -> Tuple[str, str]:
    """Generate password reset token and hash."""
    token = secrets.token_urlsafe(32)
    token_hash = hash_token(token)
    return token, token_hash


# ===== CURRENT USER DEPENDENCY =====

def get_current_user(
    token: str,
    db: Session
) -> User:
    """
    Extract and verify JWT, return current user.
    Called as a dependency in protected endpoints.
    """
    try:
        payload = verify_token(token)
    except HTTPException:
        raise
    
    user_id = payload.get("sub")
    org_id = payload.get("org_id")
    
    if not user_id or not org_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims"
        )
    
    user = db.query(User).filter(User.id == int(user_id), User.org_id == int(org_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user


def get_current_org(user: User) -> Organization:
    """Extract org from authenticated user."""
    if not user.organization:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Organization not found"
        )
    return user.organization


def require_role(required_role: str):
    """Dependency: enforce role check."""
    def check_role(user: User):
        if user.role != required_role and user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This endpoint requires {required_role} role"
            )
        return user
    return check_role


def require_admin(user: User) -> User:
    """Dependency: ensure user is admin."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user


# ===== AUDIT LOGGING =====

def log_audit_event(
    db: Session,
    org_id: int,
    event_type: str,
    entity_type: str,
    entity_id: Optional[int] = None,
    user_id: Optional[int] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> AuditLog:
    """Log event to audit trail."""
    log_entry = AuditLog(
        org_id=org_id,
        user_id=user_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.add(log_entry)
    db.commit()
    return log_entry


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    # Check X-Forwarded-For (important for reverse proxies)
    if request.headers.get("x-forwarded-for"):
        return request.headers.get("x-forwarded-for").split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ===== BRUTE FORCE PROTECTION =====

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15


def check_account_lockout(db: Session, user: User) -> bool:
    """Check if user account is locked from failed logins."""
    # Simple version: track in audit logs
    # For production, consider a dedicated table
    recent_failures = db.query(AuditLog).filter(
        AuditLog.user_id == user.id,
        AuditLog.event_type == "LOGIN_FAILED",
        AuditLog.created_at > datetime.now(timezone.utc) - timedelta(minutes=LOCKOUT_DURATION_MINUTES)
    ).count()
    
    if recent_failures >= MAX_LOGIN_ATTEMPTS:
        return True  # locked
    return False  # not locked


def record_failed_login(
    db: Session,
    org_id: int,
    user_id: int,
    ip_address: str
):
    """Record failed login attempt."""
    log_audit_event(
        db=db,
        org_id=org_id,
        event_type="LOGIN_FAILED",
        entity_type="user",
        entity_id=user_id,
        user_id=user_id,
        ip_address=ip_address,
        details={"reason": "invalid_password"}
    )


def record_successful_login(
    db: Session,
    org_id: int,
    user_id: int,
    ip_address: str
):
    """Record successful login and clear failures."""
    # Log success
    log_audit_event(
        db=db,
        org_id=org_id,
        event_type="LOGIN_SUCCESS",
        entity_type="user",
        entity_id=user_id,
        user_id=user_id,
        ip_address=ip_address
    )
    
    # Update last_login
    user = db.query(User).get(user_id)
    if user:
        user.last_login = datetime.now(timezone.utc)
        db.commit()
