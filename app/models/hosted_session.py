from sqlalchemy import Column, String, DateTime, Numeric, Text
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


def gen_uuid():
    return str(uuid.uuid4())


class HostedSession(Base):
    __tablename__ = "hosted_sessions"

    id = Column(String, primary_key=True, default=gen_uuid)
    merchant_id = Column(String, nullable=True)
    amount = Column(Numeric(10, 2), nullable=False, default=0)
    mode = Column(String, nullable=False, default="test")
    status = Column(String, nullable=False, default="created")
    success_url = Column(Text)
    cancel_url = Column(Text)
    url = Column(Text)
    payment_system = Column(Text)
    blockchain_tx_id = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    paid_at = Column(DateTime(timezone=True))
