"""
Invoice management utilities for PHASE 1
Handles sequential numbering, immutability, tax calculations, credit notes
"""

import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from models_phase1 import Invoice, InvoiceLineItem, Organization, User
from schemas import (
    InvoiceLineItemCreate, InvoiceCreate, InvoiceUpdate,
    InvoiceFinalizeRequest, InvoiceMarkPaidRequest
)
from auth import log_audit_event

# ===== INVOICE NUMBERING =====

def generate_invoice_number(db: Session, org: Organization) -> str:
    """Generate next sequential invoice number for org: INV-2026-0001"""
    year = datetime.now(timezone.utc).year
    
    # Get highest number for this year
    last_invoice = db.query(Invoice).filter(
        Invoice.org_id == org.id,
        Invoice.number.like(f"INV-{year}-%")
    ).order_by(Invoice.number.desc()).first()
    
    if last_invoice:
        # Extract sequence number from "INV-2026-0042" -> 42
        seq_str = last_invoice.number.split("-")[-1]
        next_seq = int(seq_str) + 1
    else:
        next_seq = 1
    
    return f"INV-{year}-{next_seq:04d}"


# ===== TAX CALCULATION =====

def determine_tax_jurisdiction(
    seller_country: str,
    buyer_country: str,
    buyer_vat_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Determine tax jurisdiction and rate.
    Returns: {
        "tax_rate": "21.0",
        "is_reverse_charge": false,
        "jurisdiction": "NL",
        "explanation": "Domestic (EU) - NL VAT 21%"
    }
    """
    # Import from main.py eventually, for now simplified version
    EU_VAT_RATES = {
        'AT': 20.0, 'BE': 21.0, 'BG': 20.0, 'HR': 25.0, 'CY': 19.0,
        'CZ': 21.0, 'DK': 25.0, 'EE': 22.0, 'FI': 25.5, 'FR': 20.0,
        'DE': 19.0, 'GR': 24.0, 'HU': 27.0, 'IE': 23.0, 'IT': 22.0,
        'LV': 21.0, 'LT': 21.0, 'LU': 17.0, 'MT': 18.0, 'NL': 21.0,
        'PL': 23.0, 'PT': 23.0, 'RO': 19.0, 'SK': 20.0, 'SI': 22.0,
        'ES': 21.0, 'SE': 25.0,
    }
    
    seller = (seller_country or 'NL').upper()
    buyer = (buyer_country or seller).upper()
    
    seller_in_eu = seller in EU_VAT_RATES
    buyer_in_eu = buyer in EU_VAT_RATES
    
    # === EU → EU (same country) ===
    if seller == buyer and seller_in_eu:
        rate = EU_VAT_RATES.get(seller, 21.0)
        return {
            "tax_rate": f"{rate}",
            "is_reverse_charge": False,
            "jurisdiction": seller,
            "explanation": f"Domestic (EU) - {seller} VAT {rate}%"
        }
    
    # === EU → EU (different countries) ===
    if seller_in_eu and buyer_in_eu and seller != buyer:
        if buyer_vat_id:
            # B2B with VAT ID → reverse charge
            return {
                "tax_rate": "0.0",
                "is_reverse_charge": True,
                "jurisdiction": buyer,
                "explanation": f"EU B2B Reverse Charge - {seller} to {buyer}"
            }
        else:
            # B2C → charge seller's VAT
            rate = EU_VAT_RATES.get(seller, 21.0)
            return {
                "tax_rate": f"{rate}",
                "is_reverse_charge": False,
                "jurisdiction": seller,
                "explanation": f"EU B2C - {seller} VAT {rate}%"
            }
    
    # === EU → Outside EU ===
    if seller_in_eu and not buyer_in_eu:
        return {
            "tax_rate": "0.0",
            "is_reverse_charge": False,
            "jurisdiction": seller,
            "explanation": f"Export from {seller} - 0% VAT"
        }
    
    # === Outside EU → EU ===
    if not seller_in_eu and buyer_in_eu:
        rate = EU_VAT_RATES.get(buyer, 21.0)
        return {
            "tax_rate": f"{rate}",
            "is_reverse_charge": False,
            "jurisdiction": buyer,
            "explanation": f"Import to {buyer} - {buyer} VAT {rate}%"
        }
    
    # === Default (outside EU) ===
    return {
        "tax_rate": "0.0",
        "is_reverse_charge": False,
        "jurisdiction": seller,
        "explanation": f"International - {seller}"
    }


def calculate_invoice_amounts(
    line_items: List[InvoiceLineItemCreate],
    seller_country: str,
    buyer_country: str,
    buyer_vat_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Calculate invoice totals with tax.
    Returns: {
        "subtotal": 10000,  (cents)
        "tax_amount": 2100,
        "total": 12100,
        "tax_rate": "21.0",
        "is_reverse_charge": false,
        "tax_breakdown": {...}
    }
    """
    tax_info = determine_tax_jurisdiction(seller_country, buyer_country, buyer_vat_id)
    tax_rate_pct = float(tax_info["tax_rate"])
    
    subtotal = 0
    for item in line_items:
        subtotal += (item.quantity * item.unit_price)
    
    # For simplicity: single tax rate per invoice
    # In production: per-line tax rates
    tax_amount = int(subtotal * (tax_rate_pct / 100))
    total = subtotal + tax_amount
    
    return {
        "subtotal": subtotal,
        "tax_amount": tax_amount,
        "total": total,
        "tax_rate": tax_info["tax_rate"],
        "is_reverse_charge": tax_info["is_reverse_charge"],
        "tax_breakdown": {
            "jurisdiction": tax_info["jurisdiction"],
            "explanation": tax_info["explanation"],
            "rate_pct": tax_rate_pct
        }
    }


# ===== INVOICE OPERATIONS =====

def create_draft_invoice(
    db: Session,
    org_id: int,
    created_by: User,
    invoice_data: InvoiceCreate
) -> Invoice:
    """Create new draft invoice."""
    
    # Get organization
    org = db.query(Organization).get(org_id)
    if not org:
        raise ValueError("Organization not found")
    
    # Generate number
    invoice_number = generate_invoice_number(db, org)
    
    # Calculate amounts
    amounts = calculate_invoice_amounts(
        line_items=invoice_data.line_items,
        seller_country=org.country or 'NL',
        buyer_country=invoice_data.customer_country,
        buyer_vat_id=invoice_data.customer_vat_id
    )
    
    # Serialize line items
    line_items_json = [
        {
            "description": item.description,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "tax_rate": item.tax_rate,
            "tax_amount": int(item.unit_price * item.quantity * (float(item.tax_rate) / 100)),
            "subtotal": item.unit_price * item.quantity
        }
        for item in invoice_data.line_items
    ]
    
    # Create invoice
    invoice = Invoice(
        org_id=org_id,
        number=invoice_number,
        status="draft",
        created_by_id=created_by.id,
        customer_email=invoice_data.customer_email,
        customer_name=invoice_data.customer_name,
        customer_country=invoice_data.customer_country,
        customer_vat_id=invoice_data.customer_vat_id,
        amount_subtotal=amounts["subtotal"],
        amount_tax=amounts["tax_amount"],
        amount_total=amounts["total"],
        currency=org.currency,
        tax_rate=amounts["tax_rate"],
        is_reverse_charge=amounts["is_reverse_charge"],
        tax_breakdown=amounts["tax_breakdown"],
        line_items=line_items_json,
        notes=invoice_data.notes,
        due_at=invoice_data.due_at
    )
    
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    
    # Audit log
    log_audit_event(
        db=db,
        org_id=org_id,
        event_type="INVOICE_CREATED",
        entity_type="invoice",
        entity_id=invoice.id,
        user_id=created_by.id,
        details={
            "number": invoice_number,
            "customer": invoice_data.customer_email,
            "amount": amounts["total"]
        }
    )
    
    return invoice


def finalize_invoice(
    db: Session,
    invoice: Invoice,
    user: User
) -> Invoice:
    """
    Finalize invoice: lock it, prevent further edits.
    This is when the invoice becomes a legal document.
    """
    
    if invoice.status != "draft":
        raise ValueError(f"Cannot finalize invoice in {invoice.status} status")
    
    invoice.status = "finalized"
    invoice.finalized_at = datetime.now(timezone.utc)
    db.commit()
    
    # Audit log
    log_audit_event(
        db=db,
        org_id=invoice.org_id,
        event_type="INVOICE_FINALIZED",
        entity_type="invoice",
        entity_id=invoice.id,
        user_id=user.id,
        details={
            "number": invoice.number,
            "amount": invoice.amount_total
        }
    )
    
    return invoice


def mark_invoice_paid(
    db: Session,
    invoice: Invoice,
    user: User,
    payment_date: Optional[datetime] = None
) -> Invoice:
    """Mark finalized invoice as paid."""
    
    if invoice.status == "draft":
        raise ValueError("Cannot mark draft invoice as paid; finalize first")
    
    if invoice.status in ("paid", "refunded", "credited"):
        raise ValueError(f"Invoice already has status {invoice.status}")
    
    invoice.status = "paid"
    invoice.paid_at = payment_date or datetime.now(timezone.utc)
    db.commit()
    
    # Audit log
    log_audit_event(
        db=db,
        org_id=invoice.org_id,
        event_type="INVOICE_PAID",
        entity_type="invoice",
        entity_id=invoice.id,
        user_id=user.id,
        details={
            "number": invoice.number,
            "amount": invoice.amount_total,
            "payment_date": invoice.paid_at.isoformat()
        }
    )
    
    return invoice


def create_credit_note(
    db: Session,
    original_invoice: Invoice,
    percentage: int,
    user: User,
    reason: str
) -> Invoice:
    """
    Create credit note (reduce customer's balance by returning credit).
    percentage: 0-100, how much to credit back
    """
    
    if original_invoice.status == "draft":
        raise ValueError("Cannot create credit note for draft invoice")
    
    # Calculate credit amounts
    credit_subtotal = int(original_invoice.amount_subtotal * (percentage / 100))
    credit_tax = int(original_invoice.amount_tax * (percentage / 100))
    credit_total = credit_subtotal + credit_tax
    
    # Create credit note as new invoice
    org = original_invoice.organization
    credit_number = generate_invoice_number(db, org)
    
    # Negative line items
    credit_line_items = []
    if isinstance(original_invoice.line_items, str):
        original_items = json.loads(original_invoice.line_items)
    else:
        original_items = original_invoice.line_items
    
    for item in original_items:
        credit_qty = int(item.get("quantity", 1) * (percentage / 100))
        credit_line_items.append({
            "description": f"Credit: {item.get('description', 'Item')}",
            "quantity": -credit_qty if credit_qty > 0 else 0,
            "unit_price": item.get("unit_price", 0),
            "tax_rate": item.get("tax_rate", "0"),
            "tax_amount": -int(item.get("tax_amount", 0) * (percentage / 100)),
            "subtotal": -int(item.get("subtotal", 0) * (percentage / 100))
        })
    
    credit_note = Invoice(
        org_id=original_invoice.org_id,
        number=credit_number,
        status="finalized",
        created_by_id=user.id,
        customer_email=original_invoice.customer_email,
        customer_name=original_invoice.customer_name,
        customer_country=original_invoice.customer_country,
        customer_vat_id=original_invoice.customer_vat_id,
        amount_subtotal=-credit_subtotal,
        amount_tax=-credit_tax,
        amount_total=-credit_total,
        currency=original_invoice.currency,
        tax_rate=original_invoice.tax_rate,
        is_reverse_charge=original_invoice.is_reverse_charge,
        tax_breakdown=original_invoice.tax_breakdown,
        line_items=credit_line_items,
        notes=f"Credit note: {reason}",
        finalized_at=datetime.now(timezone.utc),
        created_from_invoice_id=original_invoice.id
    )
    
    db.add(credit_note)
    db.commit()
    db.refresh(credit_note)
    
    # Audit log
    log_audit_event(
        db=db,
        org_id=original_invoice.org_id,
        event_type="CREDIT_NOTE_CREATED",
        entity_type="invoice",
        entity_id=credit_note.id,
        user_id=user.id,
        details={
            "original_number": original_invoice.number,
            "credit_number": credit_number,
            "percentage": percentage,
            "reason": reason,
            "credit_amount": credit_total
        }
    )
    
    return credit_note


def update_draft_invoice(
    db: Session,
    invoice: Invoice,
    user: User,
    update_data: InvoiceUpdate
) -> Invoice:
    """Update draft invoice (can only edit drafts)."""
    
    if invoice.status != "draft":
        raise ValueError(f"Cannot edit invoice in {invoice.status} status; only drafts are editable")
    
    # Update fields
    if update_data.customer_email:
        invoice.customer_email = update_data.customer_email
    if update_data.customer_name:
        invoice.customer_name = update_data.customer_name
    if update_data.customer_country:
        invoice.customer_country = update_data.customer_country
    if update_data.customer_vat_id is not None:
        invoice.customer_vat_id = update_data.customer_vat_id
    if update_data.notes is not None:
        invoice.notes = update_data.notes
    if update_data.due_at is not None:
        invoice.due_at = update_data.due_at
    
    # Recalculate if line items changed
    if update_data.line_items:
        invoice.line_items = [
            {
                "description": item.description,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "tax_rate": item.tax_rate,
                "tax_amount": int(item.unit_price * item.quantity * (float(item.tax_rate) / 100)),
                "subtotal": item.unit_price * item.quantity
            }
            for item in update_data.line_items
        ]
        
        # Recalculate amounts
        amounts = calculate_invoice_amounts(
            line_items=update_data.line_items,
            seller_country=invoice.organization.country or 'NL',
            buyer_country=invoice.customer_country,
            buyer_vat_id=invoice.customer_vat_id
        )
        invoice.amount_subtotal = amounts["subtotal"]
        invoice.amount_tax = amounts["tax_amount"]
        invoice.amount_total = amounts["total"]
        invoice.tax_rate = amounts["tax_rate"]
        invoice.tax_breakdown = amounts["tax_breakdown"]
    
    db.commit()
    
    # Audit log
    log_audit_event(
        db=db,
        org_id=invoice.org_id,
        event_type="INVOICE_UPDATED",
        entity_type="invoice",
        entity_id=invoice.id,
        user_id=user.id,
        details={"number": invoice.number}
    )
    
    return invoice
