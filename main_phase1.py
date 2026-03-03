"""
Secure User API - PHASE 1 Refactored
Multi-tenant SaaS platform with PostgreSQL backend

Endpoints:
- Authentication: register, login, refresh, logout
- Users: profile, update
- Organizations: create, get, update
- Invoices: CRUD, finalize, mark paid, credit notes
- Audit logs: view trail

Run: uvicorn main:app --reload
"""

from fastapi import FastAPI, Depends, HTTPException, status, Request, Header, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timezone, timedelta

import os
import logging
import uuid

from db import get_db, engine, SessionLocal
from models_phase1 import Base, Organization, User, Invoice, AuditLog, PaymentSession
from schemas import (
    # Auth
    LoginRequest, TokenResponse, RefreshTokenRequest, PasswordResetRequest,
    PasswordReset, PasswordChange, PasswordResetResponse, EmailVerificationRequest, EmailVerificationResponse,
    # Organization
    OrganizationCreate, OrganizationUpdate, OrganizationResponse,
    # User
    UserCreate, UserResponse, UserDetailResponse, UserUpdate, UserRoleUpdate,
    # Invoice
    InvoiceCreate, InvoiceUpdate, InvoiceResponse, InvoiceFinalizeRequest,
    InvoiceMarkPaidRequest, InvoiceCreditNoteRequest,
    # Payments (Phase 2)
    PaymentSessionCreate, PaymentSessionResponse, SessionStatusResponse, WebhookResponse,
    StripeWebhookPayload, OneComWebhookPayload, Web3WebhookPayload,
    # Audit
    AuditLogResponse,
    # Enums
    UserRole
)
from auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, verify_token,
    get_client_ip,
    log_audit_event, record_failed_login, record_successful_login,
    check_account_lockout, create_email_verification_token,
    create_password_reset_token, hash_token, verify_email_token, verify_password_reset_token
)
from payment import (
    validate_payment_state_transition, generate_api_key,
    generate_customer_access_link, process_stripe_webhook,
    process_onecom_webhook, process_web3_webhook
)
from rate_limit import limiter, RATE_LIMITS
from slowapi.errors import RateLimitExceeded
from invoices import (
    create_draft_invoice, finalize_invoice, mark_invoice_paid,
    create_credit_note, update_draft_invoice, generate_invoice_number
)

# ===== SETUP =====

app = FastAPI(
    title="Secure User API",
    description="Production-grade multi-tenant SaaS platform",
    version="2.0.0"
)

# Add rate limiter to app state
app.state.limiter = limiter

# Rate limit exceeded error handler
def _rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please try again later."}
    )

app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

logger = logging.getLogger(__name__)

# Initialize database tables (optional - normally use alembic)
Base.metadata.create_all(bind=engine)

# CORS configuration
FRONTEND_ORIGINS = [
    "https://dashboard.apiblockchain.io",
    "https://apiblockchain.io",
    "https://api.apiblockchain.io",
]

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

# ===== HELPERS =====

def get_token_from_header(authorization: str = Header(None)) -> str:
    """Extract Bearer token from Authorization header."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return parts[1]


def get_current_user_from_db(db: Session, token: str) -> User:
    """Verify token and get user from database."""
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
    
    user = db.query(User).filter(
        User.id == int(user_id),
        User.org_id == int(org_id)
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user


def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """Dependency: get authenticated user from request."""
    token = get_token_from_header(authorization)
    return get_current_user_from_db(db, token)


# ===== AUTHENTICATION ENDPOINTS =====

@app.post("/auth/register", response_model=TokenResponse, tags=["Authentication"])
@limiter.limit(RATE_LIMITS["register"])
async def register(
    request: Request,
    user_data: UserCreate,
    org_data: OrganizationCreate,
    db: Session = Depends(get_db)
):
    """
    Register new organization and first admin user.
    
    Creates:
    - Organization record
    - First user (admin role)
    - Returns access + refresh tokens
    """
    
    ip_address = get_client_ip(request)
    
    # Check if email already exists (globally, for simplicity)
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if slug is available
    existing_org = db.query(Organization).filter(Organization.slug == org_data.slug).first()
    if existing_org:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization slug already exists"
        )
    
    try:
        # Create organization
        org = Organization(
            name=org_data.name,
            slug=org_data.slug,
            timezone=org_data.timezone or "UTC",
            currency=org_data.currency or "EUR",
            country=org_data.country,
            legal_name=org_data.legal_name,
            vat_number=org_data.vat_number,
            subscription_tier="starter",
            subscription_status="active",
            owner_id=1  # Will update after creating user
        )
        db.add(org)
        db.flush()  # Get org.id without committing yet
        
        # Create first user (admin)
        user = User(
            org_id=org.id,
            email=user_data.email,
            password_hash=hash_password(user_data.password),
            name=user_data.name,
            role=UserRole.ADMIN,
            email_verified=True,  # Auto-verify on registration
            email_verified_at=datetime.now(timezone.utc)
        )
        db.add(user)
        db.flush()
        
        # Update org owner_id
        org.owner_id = user.id
        db.commit()
        db.refresh(user)
        db.refresh(org)
        
        # Log event
        log_audit_event(
            db=db,
            org_id=org.id,
            event_type="ORGANIZATION_CREATED",
            entity_type="organization",
            entity_id=org.id,
            user_id=user.id,
            ip_address=ip_address,
            details={"org_slug": org.slug, "user_email": user.email}
        )
        
        record_successful_login(db, org.id, user.id, ip_address)
        
        # Generate tokens
        access_token = create_access_token(user.id, org.id)
        refresh_token = create_refresh_token(user.id, org.id)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Registration failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@app.post("/auth/login", response_model=TokenResponse, tags=["Authentication"])
@limiter.limit(RATE_LIMITS["login"])
async def login(
    request: Request,
    credentials: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login with email and password.
    Returns JWT access token + refresh token.
    """
    
    ip_address = get_client_ip(request)
    
    # Find user by email
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check account lockout
    if check_account_lockout(db, user):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Account locked due to failed login attempts. Try again in 15 minutes."
        )
    
    # Verify password
    if not verify_password(credentials.password, user.password_hash):
        record_failed_login(db, user.org_id, user.id, ip_address)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Successful login
    record_successful_login(db, user.org_id, user.id, ip_address)
    
    # Generate tokens
    access_token = create_access_token(user.id, user.org_id)
    refresh_token = create_refresh_token(user.id, user.org_id)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )


@app.post("/auth/refresh", response_model=TokenResponse, tags=["Authentication"])
@limiter.limit(RATE_LIMITS["refresh_token"])
async def refresh(
    request: Request,
    req: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    """
    
    ip_address = get_client_ip(request)
    
    try:
        payload = verify_token(req.refresh_token)
    except HTTPException:
        raise
    
    user_id = int(payload.get("sub"))
    org_id = int(payload.get("org_id"))
    
    # Verify user still exists
    user = db.query(User).filter(User.id == user_id, User.org_id == org_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Generate new access token
    access_token = create_access_token(user.id, user.org_id)
    refresh_token = create_refresh_token(user.id, user.org_id)
    
    log_audit_event(
        db=db,
        org_id=org_id,
        event_type="TOKEN_REFRESHED",
        entity_type="user",
        entity_id=user_id,
        user_id=user_id,
        ip_address=ip_address
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )


@app.post("/auth/logout", tags=["Authentication"])
async def logout(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Logout and revoke tokens (placeholder)."""
    
    log_audit_event(
        db=db,
        org_id=user.org_id,
        event_type="LOGOUT",
        entity_type="user",
        entity_id=user.id,
        user_id=user.id,
        ip_address=get_client_ip(request)
    )
    
    return {"message": "Logged out successfully"}


@app.post("/auth/verify-email", response_model=EmailVerificationResponse, tags=["Authentication"])
@limiter.limit(RATE_LIMITS["email_verify"])
async def verify_email(
    request: Request,
    email_data: EmailVerificationRequest,
    db: Session = Depends(get_db)
):
    """
    Verify user email with verification token.
    
    The token should have been received via email during registration.
    Once verified, the user can fully access their account.
    
    Request body:
    ```
    {
        "email": "user@example.com",
        "token": "verification-token-from-email"
    }
    ```
    """
    
    try:
        # Verify the token using the function from auth.py
        user = verify_email_token(db, email_data.token, email_data.email)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token"
            )
        
        # Mark email as verified
        user.email_verified = True
        user.email_verified_at = datetime.now(timezone.utc)
        user.email_verification_token = None  # Clear the token
        user.email_verification_expires = None
        db.commit()
        
        # Log the verification event
        log_audit_event(
            db=db,
            org_id=user.org_id,
            event_type="EMAIL_VERIFIED",
            entity_type="user",
            entity_id=user.id,
            user_id=user.id,
            details={"email": user.email}
        )
        
        return EmailVerificationResponse(
            message="Email verified successfully",
            user={
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "email_verified": user.email_verified,
                "email_verified_at": user.email_verified_at.isoformat() if user.email_verified_at else None
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Email verification failed: {str(e)}"
        )


@app.post("/auth/password-reset/request", tags=["Authentication"])
@limiter.limit(RATE_LIMITS["password_reset"])
async def request_password_reset(
    request: Request,
    password_reset_request: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """
    Request a password reset.
    
    In a production application, this would send an email with a password reset link.
    For testing, the token is returned in the response.
    
    Request body:
    ```
    {
        "email": "user@example.com"
    }
    ```
    """
    
    # Find user by email
    user = db.query(User).filter(User.email == password_reset_request.email).first()
    
    if not user:
        # For security, don't reveal if email exists
        return {
            "message": "If an account exists with this email, a password reset link has been sent"
        }
    
    # Generate password reset token
    token, token_hash = create_password_reset_token()
    user.password_reset_token = token_hash
    user.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    db.commit()
    
    # Log the event
    log_audit_event(
        db=db,
        org_id=user.org_id,
        event_type="PASSWORD_RESET_REQUESTED",
        entity_type="user",
        entity_id=user.id,
        user_id=user.id,
        details={"email": user.email}
    )
    
    # In a real app, send email here with:
    # - Reset link: https://app.example.com/reset?token={token}&email={email}
    # - For testing, return token (NEVER do this in production!)
    
    return {
        "message": "If an account exists with this email, a password reset link has been sent",
        "token": token  # ONLY for testing! Remove in production.
    }


@app.post("/auth/password-reset/confirm", response_model=PasswordResetResponse, tags=["Authentication"])
@limiter.limit(RATE_LIMITS["password_reset"])
async def confirm_password_reset(
    request: Request,
    password_reset: PasswordReset,
    db: Session = Depends(get_db)
):
    """
    Complete password reset with token and new password.
    
    Request body:
    ```
    {
        "token": "reset-token-sent-via-email",
        "new_password": "NewSecurePassword123!"
    }
    ```
    """
    
    try:
        # For now, we need to extract the email somehow
        # In production, the token itself would encode the email or user_id
        # For this simplified version, we'll search for any user with matching reset token
        
        token_hash = hash_token(password_reset.token)
        user = db.query(User).filter(
            User.password_reset_token == token_hash
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired password reset token"
            )
        
        # Check if token has expired
        if user.password_reset_expires:
            expires = user.password_reset_expires
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            if now > expires:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Password reset token has expired"
                )
        
        # Update password
        user.password_hash = hash_password(password_reset.new_password)
        user.password_reset_token = None  # Clear the token
        user.password_reset_expires = None
        db.commit()
        
        # Log the event
        log_audit_event(
            db=db,
            org_id=user.org_id,
            event_type="PASSWORD_RESET_COMPLETED",
            entity_type="user",
            entity_id=user.id,
            user_id=user.id,
            details={"email": user.email}
        )
        
        return PasswordResetResponse(
            message="Password reset successfully",
            email=user.email
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password reset failed: {str(e)}"
        )


# ===== USER ENDPOINTS =====

@app.get("/users/me", response_model=UserDetailResponse, tags=["Users"])
async def get_current_profile(
    user: User = Depends(get_current_user)
):
    """Get current user profile."""
    return UserDetailResponse.from_orm(user)


@app.patch("/users/me", response_model=UserDetailResponse, tags=["Users"])
async def update_profile(
    update_data: UserUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user profile."""
    
    if update_data.name:
        user.name = update_data.name
    
    if update_data.email:
        # Check if email is already taken
        existing = db.query(User).filter(
            User.email == update_data.email,
            User.id != user.id,
            User.org_id == user.org_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        user.email = update_data.email
    
    db.commit()
    db.refresh(user)
    
    log_audit_event(
        db=db,
        org_id=user.org_id,
        event_type="USER_PROFILE_UPDATED",
        entity_type="user",
        entity_id=user.id,
        user_id=user.id,
        ip_address=get_client_ip(request)
    )
    
    return UserDetailResponse.from_orm(user)


@app.patch("/users/{user_id}/role", response_model=UserResponse, tags=["Users"])
async def update_user_role(
    user_id: int,
    role_update: UserRoleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user role (admin only).
    Can only change users in same organization.
    """
    
    # Check admin role
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    target_user = db.query(User).filter(
        User.id == user_id,
        User.org_id == current_user.org_id
    ).first()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    old_role = target_user.role
    target_user.role = role_update.role.value
    db.commit()
    
    log_audit_event(
        db=db,
        org_id=current_user.org_id,
        event_type="USER_ROLE_CHANGED",
        entity_type="user",
        entity_id=user_id,
        user_id=current_user.id,
        ip_address=get_client_ip(request),
        details={"from_role": old_role, "to_role": role_update.role}
    )
    
    return UserResponse.from_orm(target_user)


# ===== ORGANIZATION ENDPOINTS =====

@app.get("/org", response_model=OrganizationResponse, tags=["Organization"])
async def get_organization(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current organization details."""
    org = db.query(Organization).filter(Organization.id == user.org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    return OrganizationResponse.from_orm(org)


@app.patch("/org", response_model=OrganizationResponse, tags=["Organization"])
async def update_organization(
    update_data: OrganizationUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update organization details (admin only)."""
    
    # Check admin role
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    org = db.query(Organization).filter(Organization.id == user.org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Update fields
    if update_data.name:
        org.name = update_data.name
    if update_data.timezone:
        org.timezone = update_data.timezone
    if update_data.currency:
        org.currency = update_data.currency
    if update_data.country:
        org.country = update_data.country
    if update_data.legal_name:
        org.legal_name = update_data.legal_name
    if update_data.vat_number:
        org.vat_number = update_data.vat_number
    
    db.commit()
    db.refresh(org)
    
    log_audit_event(
        db=db,
        org_id=org.id,
        event_type="ORGANIZATION_UPDATED",
        entity_type="organization",
        entity_id=org.id,
        user_id=user.id,
        ip_address=get_client_ip(request)
    )
    
    return OrganizationResponse.from_orm(org)


# ===== INVOICE ENDPOINTS =====

@app.post("/invoices", response_model=InvoiceResponse, tags=["Invoices"])
async def create_invoice(
    invoice_data: InvoiceCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new draft invoice."""
    
    invoice = create_draft_invoice(
        db=db,
        org_id=user.org_id,
        created_by=user,
        invoice_data=invoice_data
    )
    
    return InvoiceResponse.from_orm(invoice)


@app.get("/invoices", response_model=list[InvoiceResponse], tags=["Invoices"])
async def list_invoices(
    status: str = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List invoices for current organization."""
    
    query = db.query(Invoice).filter(Invoice.org_id == user.org_id)
    
    if status:
        query = query.filter(Invoice.status == status)
    
    invoices = query.order_by(desc(Invoice.created_at)).all()
    
    return [InvoiceResponse.from_orm(inv) for inv in invoices]


@app.get("/invoices/{invoice_id}", response_model=InvoiceResponse, tags=["Invoices"])
async def get_invoice(
    invoice_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get invoice details (must belong to user's org)."""
    
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.org_id == user.org_id
    ).first()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    return InvoiceResponse.from_orm(invoice)


@app.patch("/invoices/{invoice_id}", response_model=InvoiceResponse, tags=["Invoices"])
async def update_invoice(
    invoice_id: int,
    update_data: InvoiceUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update draft invoice (can only edit drafts)."""
    
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.org_id == user.org_id
    ).first()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    invoice = update_draft_invoice(db, invoice, user, update_data)
    
    return InvoiceResponse.from_orm(invoice)


@app.post("/invoices/{invoice_id}/finalize", response_model=InvoiceResponse, tags=["Invoices"])
async def finalize_invoice_endpoint(
    invoice_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Finalize invoice (make it immutable and legally binding)."""
    
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.org_id == user.org_id
    ).first()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    invoice = finalize_invoice(db, invoice, user)
    
    return InvoiceResponse.from_orm(invoice)


@app.post("/invoices/{invoice_id}/mark-paid", response_model=InvoiceResponse, tags=["Invoices"])
async def mark_paid_endpoint(
    invoice_id: int,
    req: InvoiceMarkPaidRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark finalized invoice as paid."""
    
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.org_id == user.org_id
    ).first()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    invoice = mark_invoice_paid(db, invoice, user, req.payment_date)
    
    return InvoiceResponse.from_orm(invoice)


@app.post("/invoices/{invoice_id}/credit-note", response_model=InvoiceResponse, tags=["Invoices"])
async def credit_note_endpoint(
    invoice_id: int,
    req: InvoiceCreditNoteRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create credit note (refund) for invoice."""
    
    original_invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.org_id == user.org_id
    ).first()
    
    if not original_invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    credit_note = create_credit_note(
        db=db,
        original_invoice=original_invoice,
        percentage=req.percentage,
        user=user,
        reason=req.reason
    )
    
    return InvoiceResponse.from_orm(credit_note)


# ===== PAYMENT ENDPOINTS (PHASE 2) =====

@app.post("/create_session", response_model=PaymentSessionResponse, tags=["Payments"])
@limiter.limit(RATE_LIMITS.get("payment", "10 per minute"))
async def create_payment_session(
    request: Request,
    session_data: PaymentSessionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new payment session for customer checkout."""
    
    try:
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        # Create payment session record
        payment_session = PaymentSession(
            session_id=session_id,
            org_id=user.org_id,
            amount_cents=session_data.amount_cents,
            currency=session_data.currency,
            status="created",
            payment_status="not_started",
            payment_provider="pending",
            success_url=session_data.success_url,
            cancel_url=session_data.cancel_url,
            metadata=session_data.metadata or {}
        )
        
        db.add(payment_session)
        db.commit()
        db.refresh(payment_session)
        
        # Log audit event
        log_audit_event(
            db=db,
            org_id=user.org_id,
            action="PAYMENT_SESSION_CREATED",
            resource_type="PaymentSession",
            resource_id=session_id,
            user_id=user.id,
            details=f"Created payment session for {session_data.amount_cents} {session_data.currency}"
        )
        
        # Construct checkout URL
        checkout_url = f"/checkout?session_id={session_id}"
        
        return PaymentSessionResponse(
            session_id=session_id,
            amount_cents=session_data.amount_cents,
            currency=session_data.currency,
            status=payment_session.status,
            payment_status=payment_session.payment_status,
            payment_provider=payment_session.payment_provider,
            paid_at=payment_session.paid_at,
            checkout_url=checkout_url
        )
    
    except Exception as e:
        db.rollback()
        log_audit_event(
            db=db,
            org_id=user.org_id,
            action="PAYMENT_SESSION_CREATE_FAILED",
            resource_type="PaymentSession",
            resource_id="unknown",
            user_id=user.id,
            details=f"Error: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create payment session"
        )


@app.get("/session/{session_id}/status", response_model=SessionStatusResponse, tags=["Payments"])
async def get_session_status(
    session_id: str,
    db: Session = Depends(get_db)
):
    """Get payment session status (PUBLIC - no authentication required)."""
    
    payment_session = db.query(PaymentSession).filter(
        PaymentSession.session_id == session_id
    ).first()
    
    if not payment_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    return SessionStatusResponse(
        session_id=payment_session.session_id,
        status=payment_session.status,
        payment_status=payment_session.payment_status,
        payment_provider=payment_session.payment_provider,
        paid_at=payment_session.paid_at,
        amount_cents=payment_session.amount_cents,
        currency=payment_session.currency
    )


@app.post("/webhooks/stripe", tags=["Payments"])
async def webhook_stripe(
    payload: dict = Body(...),
    db: Session = Depends(get_db)
):
    """Handle Stripe webhook events (payment.intent.succeeded)."""
    
    try:
        # Log incoming webhook
        print(f"[Stripe Webhook] Received: {payload.get('type')}")
        
        # Handle payment_intent.succeeded event
        if payload.get("type") == "payment_intent.succeeded":
            event_data = payload.get("data", {}).get("object", {})
            session_id = event_data.get("metadata", {}).get("session_id")
            stripe_intent_id = event_data.get("id")
            
            if not session_id:
                return WebhookResponse(
                    success=False,
                    message="No session_id in webhook metadata"
                )
            
            # Find payment session
            payment_session = db.query(PaymentSession).filter(
                PaymentSession.session_id == session_id
            ).first()
            
            if not payment_session:
                return WebhookResponse(
                    success=False,
                    message=f"Session {session_id} not found"
                )
            
            # Validate state transition
            if not validate_payment_state_transition(payment_session.status, "paid"):
                return WebhookResponse(
                    success=False,
                    message=f"Invalid state transition: {payment_session.status} -> paid"
                )
            
            # Update session to paid
            payment_session.status = "paid"
            payment_session.payment_status = "completed"
            payment_session.payment_provider = "stripe"
            payment_session.stripe_intent_id = stripe_intent_id
            payment_session.paid_at = datetime.now(timezone.utc)
            
            # Update custom_metadata with webhook source
            if isinstance(payment_session.custom_metadata, dict):
                if "webhook_sources" not in payment_session.custom_metadata:
                    payment_session.custom_metadata["webhook_sources"] = []
                payment_session.custom_metadata["webhook_sources"].append({
                    "provider": "stripe",
                    "event_type": "payment_intent.succeeded",
                    "processed_at": datetime.now(timezone.utc).isoformat()
                })
            
            db.commit()
            
            # Generate API key for customer
            api_key = generate_api_key()
            
            # Generate customer access link
            customer_access = generate_customer_access_link(
                session_id=session_id,
                org_id=payment_session.org_id
            )
            
            # Log audit event
            log_audit_event(
                db=db,
                org_id=payment_session.org_id,
                action="PAYMENT_COMPLETED_STRIPE",
                resource_type="PaymentSession",
                resource_id=session_id,
                user_id=None,
                details=f"Stripe payment of {payment_session.amount_cents} {payment_session.currency} completed"
            )
            
            return WebhookResponse(
                success=True,
                session_id=session_id,
                message="Payment processed successfully",
                api_key_created=api_key,
                customer_access=customer_access
            )
        
        return WebhookResponse(
            success=False,
            message=f"Unsupported event type: {payload.get('type')}"
        )
    
    except Exception as e:
        print(f"[Stripe Webhook Error] {str(e)}")
        return WebhookResponse(
            success=False,
            message=f"Webhook processing failed: {str(e)}"
        )


@app.post("/webhooks/onecom", tags=["Payments"])
async def webhook_onecom(
    payload: dict = Body(...),
    db: Session = Depends(get_db)
):
    """Handle One.com webhook events (payment.completed)."""
    
    try:
        print(f"[One.com Webhook] Received: {payload.get('type')}")
        
        if payload.get("type") == "payment.completed":
            session_id = payload.get("reference")
            transaction_id = payload.get("transaction_id")
            status = payload.get("status")
            
            if not session_id:
                return WebhookResponse(
                    success=False,
                    message="No reference (session_id) in webhook"
                )
            
            # Find payment session
            payment_session = db.query(PaymentSession).filter(
                PaymentSession.session_id == session_id
            ).first()
            
            if not payment_session:
                return WebhookResponse(
                    success=False,
                    message=f"Session {session_id} not found"
                )
            
            # Validate state transition
            if not validate_payment_state_transition(payment_session.status, "paid"):
                return WebhookResponse(
                    success=False,
                    message=f"Invalid state transition: {payment_session.status} -> paid"
                )
            
            # Update session
            payment_session.status = "paid"
            payment_session.payment_status = "completed"
            payment_session.payment_provider = "onecom"
            payment_session.onecom_txn_id = transaction_id
            payment_session.paid_at = datetime.now(timezone.utc)
            
            # Update custom_metadata
            if isinstance(payment_session.custom_metadata, dict):
                if "webhook_sources" not in payment_session.custom_metadata:
                    payment_session.custom_metadata["webhook_sources"] = []
                payment_session.custom_metadata["webhook_sources"].append({
                    "provider": "onecom",
                    "event_type": "payment.completed",
                    "processed_at": datetime.now(timezone.utc).isoformat()
                })
            
            db.commit()
            
            # Generate API key
            api_key = generate_api_key()
            
            # Generate customer access link
            customer_access = generate_customer_access_link(
                session_id=session_id,
                org_id=payment_session.org_id
            )
            
            # Log audit event
            log_audit_event(
                db=db,
                org_id=payment_session.org_id,
                action="PAYMENT_COMPLETED_ONECOM",
                resource_type="PaymentSession",
                resource_id=session_id,
                user_id=None,
                details=f"One.com payment of {payment_session.amount_cents} {payment_session.currency} completed"
            )
            
            return WebhookResponse(
                success=True,
                session_id=session_id,
                message="One.com payment processed successfully",
                api_key_created=api_key,
                customer_access=customer_access
            )
        
        return WebhookResponse(
            success=False,
            message=f"Unsupported event type: {payload.get('type')}"
        )
    
    except Exception as e:
        print(f"[One.com Webhook Error] {str(e)}")
        return WebhookResponse(
            success=False,
            message=f"Webhook processing failed: {str(e)}"
        )


@app.post("/webhooks/web3", tags=["Payments"])
async def webhook_web3(
    payload: dict = Body(...),
    db: Session = Depends(get_db)
):
    """Handle Web3/Blockchain webhook events (payment.confirmed)."""
    
    try:
        print(f"[Web3 Webhook] Received: {payload.get('type')}")
        
        if payload.get("type") == "payment.confirmed":
            session_id = payload.get("session_id")
            tx_id = payload.get("transaction_id")
            network = payload.get("network")
            
            if not session_id:
                return WebhookResponse(
                    success=False,
                    message="No session_id in webhook"
                )
            
            # Find payment session
            payment_session = db.query(PaymentSession).filter(
                PaymentSession.session_id == session_id
            ).first()
            
            if not payment_session:
                return WebhookResponse(
                    success=False,
                    message=f"Session {session_id} not found"
                )
            
            # Validate state transition
            if not validate_payment_state_transition(payment_session.status, "paid"):
                return WebhookResponse(
                    success=False,
                    message=f"Invalid state transition: {payment_session.status} -> paid"
                )
            
            # Update session
            payment_session.status = "paid"
            payment_session.payment_status = "completed"
            payment_session.payment_provider = "web3"
            payment_session.web3_tx_id = tx_id
            payment_session.paid_at = datetime.now(timezone.utc)
            
            # Update custom_metadata
            if isinstance(payment_session.custom_metadata, dict):
                if "webhook_sources" not in payment_session.custom_metadata:
                    payment_session.custom_metadata["webhook_sources"] = []
                payment_session.custom_metadata["webhook_sources"].append({
                    "provider": "web3",
                    "event_type": "payment.confirmed",
                    "network": network,
                    "processed_at": datetime.now(timezone.utc).isoformat()
                })
            
            db.commit()
            
            # Generate API key
            api_key = generate_api_key()
            
            # Generate customer access link
            customer_access = generate_customer_access_link(
                session_id=session_id,
                org_id=payment_session.org_id
            )
            
            # Log audit event
            log_audit_event(
                db=db,
                org_id=payment_session.org_id,
                action="PAYMENT_COMPLETED_WEB3",
                resource_type="PaymentSession",
                resource_id=session_id,
                user_id=None,
                details=f"Web3 payment of {payment_session.amount_cents} {payment_session.currency} on {network} completed"
            )
            
            return WebhookResponse(
                success=True,
                session_id=session_id,
                message="Web3 payment processed successfully",
                api_key_created=api_key,
                customer_access=customer_access
            )
        
        return WebhookResponse(
            success=False,
            message=f"Unsupported event type: {payload.get('type')}"
        )
    
    except Exception as e:
        print(f"[Web3 Webhook Error] {str(e)}")
        return WebhookResponse(
            success=False,
            message=f"Webhook processing failed: {str(e)}"
        )


# ===== AUDIT LOG ENDPOINTS =====

@app.get("/audit-logs", response_model=list[AuditLogResponse], tags=["Audit"])
async def get_audit_logs(
    limit: int = 100,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """View organization audit trail (admin only)."""
    
    # Check admin role
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    logs = db.query(AuditLog).filter(
        AuditLog.org_id == user.org_id
    ).order_by(
        desc(AuditLog.created_at)
    ).offset(offset).limit(limit).all()
    
    return [AuditLogResponse.from_orm(log) for log in logs]


# ===== HEALTH CHECK =====

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


# ===== ERROR HANDLERS =====

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler."""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


