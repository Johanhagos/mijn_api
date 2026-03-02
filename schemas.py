"""
Pydantic schemas for PHASE 1 API
"""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum


# === ENUMS ===

class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    FINALIZED = "finalized"
    PAID = "paid"
    REFUNDED = "refunded"
    CREDITED = "credited"


class SubscriptionTier(str, Enum):
    STARTER = "starter"
    GROWTH = "growth"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELED = "canceled"


# === ORGANIZATION ===

class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100)
    timezone: Optional[str] = "UTC"
    currency: Optional[str] = "EUR"
    country: Optional[str] = None
    legal_name: Optional[str] = None
    vat_number: Optional[str] = None


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None
    country: Optional[str] = None
    legal_name: Optional[str] = None
    vat_number: Optional[str] = None


class OrganizationResponse(BaseModel):
    id: int
    name: str
    slug: str
    owner_id: int
    timezone: str
    currency: str
    subscription_tier: str
    subscription_status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# === USER ===

class UserCreate(BaseModel):
    """Create new user (typically by org admin during signup)."""
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=72)
    name: str = Field(..., min_length=1, max_length=255)


class UserUpdate(BaseModel):
    """Update user profile."""
    name: Optional[str] = None
    email: Optional[EmailStr] = None


class UserRoleUpdate(BaseModel):
    """Change user's role within organization."""
    role: UserRole


class UserResponse(BaseModel):
    """Public user view (no password)."""
    id: int
    email: str
    name: str
    role: str
    email_verified: bool
    last_login: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserDetailResponse(UserResponse):
    """Detailed user view for self or admins."""
    org_id: int
    updated_at: datetime


# === AUTHENTICATION ===

class LoginRequest(BaseModel):
    """Email + password login."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class PasswordResetRequest(BaseModel):
    """Request password reset (sends email)."""
    email: EmailStr


class PasswordReset(BaseModel):
    """Complete password reset with token."""
    token: str
    new_password: str = Field(..., min_length=6, max_length=72)


class PasswordChange(BaseModel):
    """Change password (requires old password)."""
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=72)


class EmailVerificationRequest(BaseModel):
    """Verify email with token."""
    token: str


# === INVOICE ===

class InvoiceLineItemCreate(BaseModel):
    """Line item for invoice."""
    description: str = Field(..., min_length=1, max_length=500)
    quantity: int = Field(default=1, ge=1)
    unit_price: int = Field(..., ge=0)  # in cents
    tax_rate: str  # e.g. "21.0"


class InvoiceLineItemResponse(InvoiceLineItemCreate):
    """Line item response."""
    id: int
    tax_amount: int
    subtotal: int
    
    class Config:
        from_attributes = True


class InvoiceCreate(BaseModel):
    """Create new invoice (draft)."""
    customer_email: EmailStr
    customer_name: str = Field(..., min_length=1, max_length=255)
    customer_country: str = Field(..., min_length=2, max_length=2)
    customer_vat_id: Optional[str] = None
    notes: Optional[str] = None
    due_at: Optional[datetime] = None
    line_items: List[InvoiceLineItemCreate] = Field(..., min_items=1)


class InvoiceUpdate(BaseModel):
    """Update draft invoice."""
    customer_email: Optional[EmailStr] = None
    customer_name: Optional[str] = None
    customer_country: Optional[str] = None
    customer_vat_id: Optional[str] = None
    notes: Optional[str] = None
    due_at: Optional[datetime] = None
    line_items: Optional[List[InvoiceLineItemCreate]] = None


class InvoiceResponse(BaseModel):
    """Invoice response."""
    id: int
    org_id: int
    number: str
    status: str
    created_by_id: int
    customer_email: str
    customer_name: str
    customer_country: str
    customer_vat_id: Optional[str]
    amount_subtotal: int
    amount_tax: int
    amount_total: int
    currency: str
    tax_rate: str
    is_reverse_charge: bool
    finalized_at: Optional[datetime]
    paid_at: Optional[datetime]
    due_at: Optional[datetime]
    notes: Optional[str]
    pdf_path: Optional[str]
    created_at: datetime
    updated_at: datetime
    line_items: List[InvoiceLineItemResponse]
    
    class Config:
        from_attributes = True


class InvoiceFinalizeRequest(BaseModel):
    """Request to finalize invoice (calculate amounts, lock)."""
    pass


class InvoiceMarkPaidRequest(BaseModel):
    """Mark invoice as paid."""
    payment_date: Optional[datetime] = None


class InvoiceCreditNoteRequest(BaseModel):
    """Create credit note from existing invoice."""
    reason: str = Field(..., min_length=1, max_length=500)
    percentage: int = Field(default=100, ge=1, le=100)  # % to credit back


# === API KEY ===

class APIKeyCreate(BaseModel):
    """Create new API key."""
    name: str = Field(..., min_length=1, max_length=255)
    permissions: List[str] = Field(default=[])


class APIKeyResponse(BaseModel):
    """API key response (without full key)."""
    id: int
    name: str
    key_prefix: str
    permissions: List[str]
    last_used_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class APIKeyWithSecret(APIKeyResponse):
    """New API key with secret (only shown once)."""
    key: str


# === AUDIT LOGS ===

class AuditLogResponse(BaseModel):
    """Audit log entry."""
    id: int
    event_type: str
    entity_type: str
    entity_id: Optional[int]
    details: Optional[dict]
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True
