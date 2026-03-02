"""
Database migration helpers for PostgreSQL migration
This module provides helper functions to migrate from JSON file storage to PostgreSQL
"""
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from models import Shop, User as DBUser, Invoice as DBInvoice, InvoiceItem, Customer
from datetime import datetime
import hashlib
import json
from pathlib import Path


def migrate_users_from_json(db: Session, json_file: Path, default_shop_id: str) -> List[DBUser]:
    """Migrate users from JSON file to database"""
    if not json_file.exists():
        return []
    
    users_data = json.loads(json_file.read_text())
    migrated = []
    
    for user_dict in users_data:
        # Check if user already exists
        existing = db.query(DBUser).filter(DBUser.email == user_dict.get("email", user_dict["name"])).first()
        if existing:
            continue
        
        # Create new user
        user = DBUser(
            shop_id=default_shop_id,
            email=user_dict.get("email", user_dict["name"]),
            password_hash=user_dict["password"],
            role=user_dict.get("role", "user"),
            name=user_dict["name"],
            active=True,
            email_verified=False,
            token_version=1
        )
        db.add(user)
        migrated.append(user)
    
    db.commit()
    return migrated


def migrate_invoices_from_json(
    db: Session,
    json_file: Path,
    default_shop_id: str,
    default_customer_id: str
) -> List[DBInvoice]:
    """Migrate invoices from JSON file to database"""
    if not json_file.exists():
        return []
    
    invoices_data = json.loads(json_file.read_text())
    migrated = []
    
    for inv_dict in invoices_data:
        try:
            # Check if invoice already exists
            existing = db.query(DBInvoice).filter(DBInvoice.id == inv_dict["id"]).first()
            if existing:
                continue
            
            # Parse date safely
            issue_date = datetime.now().date()
            if "created_at" in inv_dict:
                try:
                    issue_date = datetime.fromisoformat(inv_dict["created_at"]).date()
                except (ValueError, TypeError) as e:
                    print(f"[WARN] Invalid date format for invoice {inv_dict['id']}: {e}")
            
            # Create invoice
            invoice = DBInvoice(
                id=inv_dict["id"],
                shop_id=default_shop_id,
                customer_id=default_customer_id,
                invoice_number=inv_dict.get("invoice_number", f"INV-{inv_dict['id'][:8]}"),
                status=inv_dict.get("status", "DRAFT").upper(),
                issue_date=issue_date,
                due_date=datetime.now().date(),
                subtotal=inv_dict.get("amount", 0),
                vat_total=0,
                total=inv_dict.get("amount", 0),
                currency="EUR",
                finalized=inv_dict.get("status") == "paid"
            )
            db.add(invoice)
            migrated.append(invoice)
        except Exception as e:
            print(f"[ERROR] Failed to migrate invoice {inv_dict.get('id', 'unknown')}: {e}")
            continue
    
    db.commit()
    return migrated


def get_or_create_default_customer(db: Session, shop_id: str) -> Customer:
    """Get or create a default customer for migration purposes"""
    customer = db.query(Customer).filter(
        Customer.shop_id == shop_id,
        Customer.name == "Default Customer"
    ).first()
    
    if not customer:
        customer = Customer(
            shop_id=shop_id,
            name="Default Customer",
            email="default@example.com",
            country="NL",
            address={"street": "", "city": "", "zip": "", "country": "NL"}
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
    
    return customer


def user_dict_from_db(user: DBUser) -> dict:
    """Convert DB user to dict for backward compatibility"""
    return {
        "id": str(user.id),
        "name": user.name or user.email,
        "email": user.email,
        "role": user.role,
        "shop_id": user.shop_id,
        "token_version": user.token_version,
        "password": user.password_hash  # For auth verification
    }


def invoice_dict_from_db(invoice: DBInvoice) -> dict:
    """Convert DB invoice to dict for backward compatibility"""
    return {
        "id": str(invoice.id),
        "invoice_number": invoice.invoice_number,
        "shop_id": str(invoice.shop_id),
        "customer_id": str(invoice.customer_id),
        "status": invoice.status,
        "subtotal": float(invoice.subtotal),
        "vat_total": float(invoice.vat_total),
        "total": float(invoice.total),
        "currency": invoice.currency,
        "issue_date": invoice.issue_date.isoformat() if invoice.issue_date else None,
        "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
        "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
        "pdf_url": invoice.pdf_url
    }
