from sqlalchemy import (
    Column, String, DateTime, Boolean, ForeignKey, Integer, Numeric, JSON, Text, 
    CheckConstraint, UniqueConstraint, func, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base
import uuid
from datetime import datetime, timezone

Base = declarative_base()


def gen_uuid():
    return str(uuid.uuid4())


def utcnow():
    return datetime.now(timezone.utc)


class Shop(Base):
    """Organizations/Shops - multi-tenant root entity"""
    __tablename__ = "shops"
    __table_args__ = (
        Index('idx_shop_api_key', 'api_key_hash'),
    )

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(Text, nullable=False)
    country = Column(String(2), nullable=False)
    vat_number = Column(Text)
    registration_number = Column(Text)  # Business registration number
    eori_number = Column(Text)  # For EU customs
    address = Column(JSON, nullable=False)
    currency = Column(String(3), nullable=False, default="EUR")
    invoice_prefix = Column(Text, nullable=False)
    api_key_hash = Column(Text, nullable=False)
    plan = Column(Text, nullable=False, default='starter')
    email = Column(Text)  # Primary contact email
    phone = Column(Text)  # Primary contact phone
    logo_url = Column(Text)  # Company logo for invoices
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Sequential invoice numbering per organization
    last_invoice_number = Column(Integer, default=0)

    users = relationship("User", back_populates="shop")
    customers = relationship("Customer", back_populates="shop")
    products = relationship("Product", back_populates="shop")
    invoices = relationship("Invoice", back_populates="shop")
    subscriptions = relationship("Subscription", back_populates="shop")
    usage_metrics = relationship("UsageMetrics", back_populates="shop")


class User(Base):
    """Users belonging to shops/organizations"""
    __tablename__ = "users"
    __table_args__ = (
        Index('idx_user_email', 'email'),
        UniqueConstraint('email', name='uq_user_email'),
    )

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    shop_id = Column(UUID(as_uuid=False), ForeignKey("shops.id"), nullable=False)
    email = Column(Text, nullable=False)
    password_hash = Column(Text, nullable=False)
    role = Column(Text, nullable=False)  # admin | staff | merchant | user
    name = Column(Text)
    active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    email_verified_at = Column(DateTime(timezone=True))
    last_login_at = Column(DateTime(timezone=True))
    last_login_ip = Column(Text)
    token_version = Column(Integer, nullable=False, default=1)  # For invalidating all tokens
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    shop = relationship("Shop", back_populates="users")
    refresh_tokens = relationship("RefreshToken", back_populates="user")
    email_verifications = relationship("EmailVerification", back_populates="user")
    password_resets = relationship("PasswordReset", back_populates="user")


class Customer(Base):
    __tablename__ = "customers"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    shop_id = Column(UUID(as_uuid=False), ForeignKey("shops.id"), nullable=False)
    name = Column(Text, nullable=False)
    email = Column(Text)
    vat_number = Column(Text)
    address = Column(JSON, nullable=False)
    country = Column(String(2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    shop = relationship("Shop", back_populates="customers")


class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    shop_id = Column(UUID(as_uuid=False), ForeignKey("shops.id"), nullable=False)
    name = Column(Text, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    vat_rate = Column(Numeric(4, 2), nullable=False)
    sku = Column(Text)
    active = Column(Boolean, default=True)

    shop = relationship("Shop", back_populates="products")


class Invoice(Base):
    """Invoices with immutability and compliance tracking"""
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("invoice_number", "shop_id", name="uq_invoice_number_per_shop"),
        Index('idx_invoice_shop_status', 'shop_id', 'status'),
        Index('idx_invoice_customer', 'customer_id'),
    )

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    shop_id = Column(UUID(as_uuid=False), ForeignKey("shops.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=False), ForeignKey("customers.id"), nullable=False)

    invoice_number = Column(Text, nullable=False)
    status = Column(Text, nullable=False)  # DRAFT | SENT | PAID | OVERDUE | CANCELED | CREDIT_NOTE

    issue_date = Column(DateTime(timezone=False), nullable=False)
    due_date = Column(DateTime(timezone=False), nullable=False)

    subtotal = Column(Numeric(10, 2), nullable=False)
    vat_total = Column(Numeric(10, 2), nullable=False)
    total = Column(Numeric(10, 2), nullable=False)

    currency = Column(String(3), nullable=False)
    pdf_url = Column(Text)
    
    # Immutability tracking
    finalized = Column(Boolean, default=False)  # Once true, invoice cannot be edited
    finalized_at = Column(DateTime(timezone=True))
    finalized_by = Column(UUID(as_uuid=False), ForeignKey("users.id"))
    
    # Payment tracking
    payment_method = Column(String(20))  # stripe, paypal, blockchain, bank_transfer
    payment_reference = Column(Text)  # Payment ID or transaction reference
    paid_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    shop = relationship("Shop", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    history = relationship("InvoiceHistory", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceItem(Base):
    """Invoice line items with VAT breakdown"""
    __tablename__ = "invoice_items"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    invoice_id = Column(UUID(as_uuid=False), ForeignKey("invoices.id"), nullable=False)
    product_name = Column(Text, nullable=False)
    description = Column(Text)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    vat_rate = Column(Numeric(5, 2), nullable=False)
    
    # VAT breakdown per line (for compliance)
    subtotal = Column(Numeric(10, 2), nullable=False)  # quantity * unit_price
    vat_amount = Column(Numeric(10, 2), nullable=False)  # subtotal * (vat_rate / 100)
    total = Column(Numeric(10, 2), nullable=False)  # subtotal + vat_amount

    invoice = relationship("Invoice", back_populates="items")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index('idx_audit_shop_created', 'shop_id', 'created_at'),
        Index('idx_audit_actor', 'actor'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    shop_id = Column(UUID(as_uuid=False), ForeignKey("shops.id"))
    actor = Column(Text)
    action = Column(Text, nullable=False)
    target = Column(Text)
    extra_data = Column(JSON)  # Changed from 'metadata' to avoid reserved keyword
    ip = Column(Text)
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RefreshToken(Base):
    """Refresh tokens for JWT authentication with rotation support"""
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index('idx_refresh_token', 'token_hash'),
        Index('idx_refresh_user_valid', 'user_id', 'valid'),
    )

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True)
    token_version = Column(Integer, nullable=False, default=1)
    valid = Column(Boolean, nullable=False, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at = Column(DateTime(timezone=True))
    revoked_reason = Column(Text)
    ip_address = Column(Text)
    user_agent = Column(Text)

    user = relationship("User", back_populates="refresh_tokens")


class EmailVerification(Base):
    """Email verification tokens"""
    __tablename__ = "email_verifications"
    __table_args__ = (
        Index('idx_email_token', 'token'),
    )

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    token = Column(String(64), nullable=False, unique=True)
    verified = Column(Boolean, nullable=False, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    verified_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="email_verifications")


class PasswordReset(Base):
    """Password reset tokens"""
    __tablename__ = "password_resets"
    __table_args__ = (
        Index('idx_password_reset_token', 'token'),
    )

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    token = Column(String(64), nullable=False, unique=True)
    used = Column(Boolean, nullable=False, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    used_at = Column(DateTime(timezone=True))
    ip_address = Column(Text)

    user = relationship("User", back_populates="password_resets")


class Subscription(Base):
    """Subscription plans for shops/organizations"""
    __tablename__ = "subscriptions"
    __table_args__ = (
        Index('idx_subscription_shop', 'shop_id'),
        Index('idx_subscription_status', 'status'),
    )

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    shop_id = Column(UUID(as_uuid=False), ForeignKey("shops.id"), nullable=False)
    plan = Column(String(20), nullable=False)  # starter, growth, enterprise
    status = Column(String(20), nullable=False, default='active')  # active, cancelled, past_due
    stripe_subscription_id = Column(Text)
    stripe_customer_id = Column(Text)
    current_period_start = Column(DateTime(timezone=True))
    current_period_end = Column(DateTime(timezone=True))
    cancel_at_period_end = Column(Boolean, default=False)
    cancelled_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    shop = relationship("Shop", back_populates="subscriptions")
    
    # Plan limits (stored for historical reference)
    max_invoices_per_month = Column(Integer)
    max_team_members = Column(Integer)
    advanced_tax_enabled = Column(Boolean, default=False)


class UsageMetrics(Base):
    """Track usage for billing and analytics"""
    __tablename__ = "usage_metrics"
    __table_args__ = (
        Index('idx_usage_shop_period', 'shop_id', 'period_start'),
    )

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    shop_id = Column(UUID(as_uuid=False), ForeignKey("shops.id"), nullable=False)
    period_start = Column(DateTime(timezone=False), nullable=False)
    period_end = Column(DateTime(timezone=False), nullable=False)
    invoice_count = Column(Integer, default=0)
    api_request_count = Column(Integer, default=0)
    storage_bytes = Column(Numeric(15, 0), default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    shop = relationship("Shop", back_populates="usage_metrics")


class RateLimit(Base):
    """Rate limiting tracking"""
    __tablename__ = "rate_limits"
    __table_args__ = (
        Index('idx_ratelimit_key_window', 'key', 'window_start'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(255), nullable=False)  # Can be IP, user_id, api_key, etc.
    window_start = Column(DateTime(timezone=True), nullable=False)
    request_count = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class InvoiceHistory(Base):
    """Track invoice changes for immutability compliance"""
    __tablename__ = "invoice_history"
    __table_args__ = (
        Index('idx_invoice_history_invoice', 'invoice_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(UUID(as_uuid=False), ForeignKey("invoices.id"), nullable=False)
    changed_by = Column(UUID(as_uuid=False), ForeignKey("users.id"))
    change_type = Column(String(20), nullable=False)  # created, updated, finalized, voided
    snapshot = Column(JSON, nullable=False)  # Full invoice state at time of change
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    invoice = relationship("Invoice", back_populates="history")
    user = relationship("User")
