from pydantic import BaseModel, Field
from datetime import date
from decimal import Decimal
from typing import Optional
from enum import Enum as PyEnum
from typing import Optional


class CustomerType(str, PyEnum):
    individual = "individual"
    business = "business"


class PaymentSystem(str, PyEnum):
    web2 = "web2"
    web3 = "web3"


class InvoiceCreate(BaseModel):
    order_number: str
    invoice_date: date
    payment_date: Optional[date] = None
    seller_name: str
    seller_address: str
    seller_vat_number: str
    seller_logo_url: Optional[str] = None
    customer_type: CustomerType = Field(default=CustomerType.individual)
    customer_name: str
    customer_address: str
    customer_vat_number: Optional[str] = None  # only required for B2B
    subtotal: Decimal
    vat_rate: Decimal
    payment_system: "PaymentSystem" = Field(default="web2")
    blockchain_tx_id: Optional[str] = None  # only needed for web3


class InvoiceOut(InvoiceCreate):
    invoice_number: int
    vat_total: Decimal
    total: Decimal
    payment_system: "PaymentSystem"
    blockchain_tx_id: Optional[str] = None

    class Config:
        orm_mode = True
