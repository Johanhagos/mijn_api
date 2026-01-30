from sqlalchemy import Column, Integer, String, Date, Numeric
from app.db.session import Base

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(Integer, unique=True, index=True)
    order_number = Column(String, index=True)
    invoice_date = Column(Date)
    payment_date = Column(Date, nullable=True)
    seller_name = Column(String)
    seller_address = Column(String)
    seller_vat_number = Column(String)
    customer_name = Column(String)
    customer_address = Column(String)
    customer_vat_number = Column(String)
    subtotal = Column(Numeric(12, 2))
    vat_rate = Column(Numeric(5, 2))
    vat_total = Column(Numeric(12, 2))
    total = Column(Numeric(12, 2))
