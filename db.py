"""
Database configuration for SQLite (testing & development)
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use SQLite for immediate testing - swap to PostgreSQL in production
DATABASE_URL = "sqlite:///./mijn_api_dev.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

    """Create all tables (development only; use Alembic for production)."""
    from models_phase1 import Base
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")


def drop_db():
    """Drop all tables (dangerous! development only)."""
    from models_phase1 import Base
    Base.metadata.drop_all(bind=engine)
    logger.warning("All database tables dropped")
