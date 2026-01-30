from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, func
from app.db.session import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, index=True)
    method = Column(String, nullable=False)  # card, ideal, sepa, crypto
    status = Column(String, nullable=False, default="pending")  # pending, confirmed, failed
    amount = Column(Numeric(12, 2), nullable=False)
    provider_ref = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
