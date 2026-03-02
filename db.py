"""
Database configuration and session management for PHASE 1
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import logging

logger = logging.getLogger(__name__)

# Database URL from environment, with fallback for local development
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/mijn_api_db"
)

# For production, enforce SSL
if os.getenv("RAILWAY_ENVIRONMENT") == "production":
    if "sslmode" not in DATABASE_URL:
        DATABASE_URL += "?sslmode=require"

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Test connections before using
    echo=os.getenv("SQL_ECHO") == "1",  # Debug: echo SQL queries
)

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    expire_on_commit=False,
)


def get_db() -> Session:
    """Dependency: inject database session into FastAPI endpoints."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables (development only; use Alembic for production)."""
    from models_phase1 import Base
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")


def drop_db():
    """Drop all tables (dangerous! development only)."""
    from models_phase1 import Base
    Base.metadata.drop_all(bind=engine)
    logger.warning("All database tables dropped")
