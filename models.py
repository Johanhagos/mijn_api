from sqlalchemy import (
    Column, String, DateTime, Boolean, ForeignKey, Integer, Numeric, JSON, Text, CheckConstraint, UniqueConstraint, func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base
import uuid

Base = declarative_base()


def gen_uuid():
    return str(uuid.uuid4())


class Shop(Base):
    __tablename__ = "shops"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(Text, nullable=False)
    country = Column(String(2), nullable=False)
    vat_number = Column(Text)
    address = Column(JSON, nullable=False)
    currency = Column(String(3), nullable=False, default="EUR")
    invoice_prefix = Column(Text, nullable=False)
    api_key_hash = Column(Text, nullable=False)
    plan = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    users = relationship("User", back_populates="shop")
    customers = relationship("Customer", back_populates="shop")
    products = relationship("Product", back_populates="shop")
    invoices = relationship("Invoice", back_populates="shop")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    shop_id = Column(UUID(as_uuid=False), ForeignKey("shops.id"), nullable=False)
    email = Column(Text, nullable=False)
    password_hash = Column(Text, nullable=False)
    role = Column(Text, nullable=False)  # admin | staff
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    shop = relationship("Shop", back_populates="users")


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
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("invoice_number", "shop_id", name="uq_invoice_number_per_shop"),
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

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    shop = relationship("Shop", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    invoice_id = Column(UUID(as_uuid=False), ForeignKey("invoices.id"), nullable=False)
    product_name = Column(Text, nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    vat_rate = Column(Numeric(4, 2), nullable=False)
    total = Column(Numeric(10, 2), nullable=False)

    invoice = relationship("Invoice", back_populates="items")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    shop_id = Column(UUID(as_uuid=False))
    actor = Column(Text)
    action = Column(Text)
    target = Column(Text)
    ip = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
