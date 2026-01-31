from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func
from app.db.session import Base


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    key_hash = Column(String, nullable=False, unique=True, index=True)
    label = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
