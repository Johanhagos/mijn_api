from sqlalchemy import Column, Integer, String, DateTime, JSON, func
from app.db.session import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False)
    actor = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
