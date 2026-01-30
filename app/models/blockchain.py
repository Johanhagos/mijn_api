from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, func
from app.db.session import Base


class BlockchainTransaction(Base):
    __tablename__ = "blockchain_transactions"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, index=True)
    chain = Column(String, nullable=False)
    tx_hash = Column(String, unique=True, nullable=False, index=True)
    block_number = Column(String, nullable=True)
    explorer_url = Column(String, nullable=True)
    confirmed = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
