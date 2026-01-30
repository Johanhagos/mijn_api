from pydantic import BaseModel
from datetime import date
from decimal import Decimal
from typing import Optional

class InvoiceCreate(BaseModel):
    order_number: str
    invoice_date: date
    payment_date: Optional[date] = None
    seller_name: str
    seller_address: str
    seller_vat_number: str
    customer_name: str
    customer_address: str
    customer_vat_number: str
    subtotal: Decimal
    vat_rate: Decimal

class InvoiceOut(InvoiceCreate):
    invoice_number: int
    vat_total: Decimal
    total: Decimal

    class Config:
        orm_mode = True
