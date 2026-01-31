from sqlalchemy import Column, Integer, String, Date, Numeric, Enum as SAEnum, ForeignKey
from app.db.session import Base
import enum


class CustomerType(str, enum.Enum):
    individual = "individual"
    business = "business"


class PaymentSystem(str, enum.Enum):
    web2 = "web2"
    web3 = "web3"


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(Integer, unique=True, index=True)
    order_number = Column(String, index=True)
    invoice_date = Column(Date)
    payment_date = Column(Date, nullable=True)

    # Seller (bedrijf dat factureert)
    seller_name = Column(String)
    seller_address = Column(String)
    seller_vat_number = Column(String)
    seller_logo_url = Column(String, nullable=True)

    # Customer / Klant
    customer_type = Column(SAEnum(CustomerType), default=CustomerType.individual)
    customer_name = Column(String)
    customer_address = Column(String)
    customer_vat_number = Column(String, nullable=True)

    subtotal = Column(Numeric(12, 2))
    vat_rate = Column(Numeric(5, 2))
    vat_total = Column(Numeric(12, 2))
    total = Column(Numeric(12, 2))

    # Payment system: web2 (traditional) or web3 (blockchain)
    payment_system = Column(SAEnum(PaymentSystem), default=PaymentSystem.web2)
    blockchain_tx_id = Column(String, nullable=True)  # only for web3 payments
    # Merchant ownership
    merchant_id = Column(Integer, ForeignKey("users.id"), nullable=True)
