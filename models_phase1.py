"""
PHASE 1: Multi-Tenant PostgreSQL ORM Models
Using SQLAlchemy with Postgres backend
"""

from sqlalchemy import (
    Column, String, DateTime, Boolean, ForeignKey, Integer, Text, JSON,
    UniqueConstraint, CheckConstraint, func, Index, LargeBinary
)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime, timezone

Base = declarative_base()


class Organization(Base):
    """Multi-tenant root: each organization is isolated."""
    __tablename__ = "organizations"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False, unique=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    timezone = Column(String(50), default="UTC")
    currency = Column(String(3), default="EUR")
    
    # SaaS: subscription tracking
    subscription_tier = Column(String(50), default="starter")  # starter, growth, enterprise
    subscription_status = Column(String(50), default="active")  # active, suspended, canceled
    
    # Compliance
    vat_number = Column(String(50), nullable=True)  # for invoice issuing
    legal_name = Column(String(255), nullable=True)  # appears on invoices
    country = Column(String(2), nullable=True)  # affects default tax rates
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    users = relationship("User", back_populates="organization", foreign_keys="User.org_id")
    invoices = relationship("Invoice", back_populates="organization")
    api_keys = relationship("APIKey", back_populates="organization")
    audit_logs = relationship("AuditLog", back_populates="organization")
    tokens = relationship("TokenVersion", back_populates="organization")


class User(Base):
    """Organization users with tenant isolation."""
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("org_id", "email", name="uq_user_org_email"),
        Index("idx_user_org", "org_id"),
        Index("idx_user_email", "email"),
    )
    
    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    
    email = Column(String(255), nullable=False)
    password_hash = Column(Text, nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(50), default="user")  # admin, manager, user
    
    # Email verification
    email_verified = Column(Boolean, default=False)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    email_verification_token = Column(String(255), nullable=True)
    email_verification_expires = Column(DateTime(timezone=True), nullable=True)
    
    # Password reset
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)
    
    # Tracking
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    organization = relationship("Organization", back_populates="users", foreign_keys=[org_id])
    invoices_created = relationship("Invoice", back_populates="created_by", foreign_keys="Invoice.created_by_id")
    audit_logs = relationship("AuditLog", back_populates="user")
    tokens = relationship("TokenVersion", back_populates="user")


class Invoice(Base):
    """Immutable financial records with per-org sequential numbering."""
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("org_id", "number", name="uq_invoice_org_number"),
        Index("idx_invoice_org", "org_id"),
        Index("idx_invoice_status", "status"),
        Index("idx_invoice_customer", "customer_email"),
    )
    
    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    
    # Sequential invoice number per org: "INV-2026-0001"
    number = Column(String(50), nullable=False)
    
    # Status machine: draft → finalized → paid (or refunded, credited)
    status = Column(String(50), default="draft")  # draft, finalized, paid, refunded, credited
    
    # Creator & customer info
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    customer_email = Column(String(255), nullable=False)
    customer_name = Column(String(255), nullable=False)
    customer_country = Column(String(2), nullable=False)
    customer_vat_id = Column(String(50), nullable=True)  # For B2B reverse charge detection
    
    # Amounts (all in selected currency)
    amount_subtotal = Column(Integer, nullable=False)  # in cents/smallest unit
    amount_tax = Column(Integer, nullable=False)
    amount_total = Column(Integer, nullable=False)
    
    currency = Column(String(3), nullable=False)
    
    # Tax details (serialized per jurisdiction logic)
    tax_rate = Column(String(10), nullable=False)  # e.g. "21.0", "0.0 (reverse charge)"
    tax_breakdown = Column(JSON, nullable=True)  # per-line or per-jurisdiction breakdown
    is_reverse_charge = Column(Boolean, default=False)
    
    # Immutability: finalization locks the invoice
    finalized_at = Column(DateTime(timezone=True), nullable=True)  # NULL = not locked
    paid_at = Column(DateTime(timezone=True), nullable=True)
    due_at = Column(DateTime(timezone=True), nullable=True)
    
    # Line items (JSON for flexibility, but also have LineItem table)
    line_items = Column(JSON, nullable=False, default={})
    
    # Optional notes/memo
    notes = Column(Text, nullable=True)
    
    # PDF storage
    pdf_path = Column(String(255), nullable=True)
    
    # Credit note support: if this invoice was created from a credit, link it
    created_from_invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    
    # Tracking
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    organization = relationship("Organization", back_populates="invoices")
    created_by = relationship("User", back_populates="invoices_created", foreign_keys=[created_by_id])
    line_items_table = relationship("InvoiceLineItem", back_populates="invoice")


class InvoiceLineItem(Base):
    """Detailed line items (for future detail & reporting)."""
    __tablename__ = "invoice_line_items"
    __table_args__ = (
        Index("idx_line_invoice", "invoice_id"),
    )
    
    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    
    description = Column(String(500), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Integer, nullable=False)  # in cents
    
    # Tax for this line
    tax_rate = Column(String(10), nullable=False)
    tax_amount = Column(Integer, nullable=False)
    subtotal = Column(Integer, nullable=False)
    
    invoice = relationship("Invoice", back_populates="line_items_table")


class AuditLog(Base):
    """Database-backed audit trail for compliance."""
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("idx_audit_org", "org_id"),
        Index("idx_audit_user", "user_id"),
        Index("idx_audit_event", "event_type"),
        Index("idx_audit_created", "created_at"),
    )
    
    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # What happened
    event_type = Column(String(100), nullable=False)  # e.g. USER_LOGIN, INVOICE_FINALIZED, INVOICE_PAID
    entity_type = Column(String(50), nullable=False)  # invoice, user, payment, api_key
    entity_id = Column(Integer, nullable=True)
    
    # Context
    details = Column(JSON, nullable=True)  # flexible: amounts, field changes, reason, etc.
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(255), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    organization = relationship("Organization", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs")


class TokenVersion(Base):
    """Token versioning for rotation & revocation."""
    __tablename__ = "token_versions"
    __table_args__ = (
        Index("idx_token_user", "user_id"),
        Index("idx_token_org", "org_id"),
    )
    
    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Track token lifecycle
    version = Column(Integer, default=1)  # incremented on each refresh
    token_hash = Column(String(255), nullable=False)  # hash of the actual JWT
    refresh_token_hash = Column(String(255), nullable=True)
    
    is_revoked = Column(Boolean, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    organization = relationship("Organization", back_populates="tokens")
    user = relationship("User", back_populates="tokens")


class APIKey(Base):
    """Organization API keys for programmatic access."""
    __tablename__ = "api_keys"
    __table_args__ = (
        Index("idx_apikey_org", "org_id"),
        UniqueConstraint("org_id", "key_hash", name="uq_apikey_hash"),
    )
    
    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    
    name = Column(String(255), nullable=False)
    key_hash = Column(String(255), nullable=False)  # bcrypt hash of the full key
    key_prefix = Column(String(20), nullable=False)  # first 8 chars for display
    
    # Permissions: JSON array of scopes [invoices:read, invoices:write, users:read, etc.]
    permissions = Column(JSON, nullable=False, default=[])
    
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    is_revoked = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    organization = relationship("Organization", back_populates="api_keys")

class PaymentSession(Base):
    """Payment sessions for checkout flow (Phase 2)."""
    __tablename__ = "payment_sessions"
    __table_args__ = (
        Index("idx_session_org", "org_id"),
        Index("idx_session_status", "status"),
        UniqueConstraint("session_id", name="uq_session_id"),
    )
    
    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    
    # Unique session identifier
    session_id = Column(String(36), nullable=False, unique=True)  # UUID
    
    # Payment details
    amount_cents = Column(Integer, nullable=False)  # in cents
    currency = Column(String(3), nullable=False, default="EUR")
    
    # State machine: created → pending → paid (terminal)
    # or created → failed (terminal)
    status = Column(String(50), default="created")  # created, pending, paid, failed
    payment_status = Column(String(50), default="not_started")  # not_started, pending, completed
    
    # Payment provider tracking
    payment_provider = Column(String(50), nullable=True)  # stripe, onecom, web3
    stripe_intent_id = Column(String(255), nullable=True)
    onecom_txn_id = Column(String(255), nullable=True)
    web3_tx_id = Column(String(255), nullable=True)
    
    # URLs
    success_url = Column(String(500), nullable=True)
    cancel_url = Column(String(500), nullable=True)
    
    # Custom metadata
    custom_metadata = Column(JSON, nullable=False, default={})
    
    # Timestamps
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    organization = relationship("Organization")