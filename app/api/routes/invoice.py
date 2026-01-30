from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal
from app.schemas.invoice import InvoiceCreate, InvoiceOut
from app.models.invoice import Invoice
from app.db.session import get_db

router = APIRouter(prefix="/invoice", tags=["Invoice"])

@router.post("/create", response_model=InvoiceOut)
def create_invoice(invoice_in: InvoiceCreate, db: Session = Depends(get_db)):
    # Auto-incrementing invoice number
    last_invoice = db.query(Invoice).order_by(Invoice.invoice_number.desc()).first()
    invoice_number = 1 if not last_invoice else (last_invoice.invoice_number or 0) + 1

    vat_total = (invoice_in.subtotal * invoice_in.vat_rate) / Decimal("100")
    total = invoice_in.subtotal + vat_total

    invoice = Invoice(
        invoice_number=invoice_number,
        order_number=invoice_in.order_number,
        invoice_date=invoice_in.invoice_date,
        payment_date=invoice_in.payment_date,
        seller_name=invoice_in.seller_name,
        seller_address=invoice_in.seller_address,
        seller_vat_number=invoice_in.seller_vat_number,
        customer_name=invoice_in.customer_name,
        customer_address=invoice_in.customer_address,
        customer_vat_number=invoice_in.customer_vat_number,
        subtotal=invoice_in.subtotal,
        vat_rate=invoice_in.vat_rate,
        vat_total=vat_total,
        total=total
    )

    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice
