from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
import os

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./test.db")  # fallback lokaal

# Use a shared in-memory SQLite DB for tests when the URL is sqlite:///:memory:
# This ensures that multiple connections (created by SessionLocal and TestClient)
# see the same in-memory database.
if DATABASE_URL.startswith("sqlite") and ":memory:" in DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=True,
        future=True,
    )
else:
    # Configure pooling for non-SQLite databases. Pool sizing can be tuned
    # via environment variables (sensible defaults are provided).
    pool_size = int(os.environ.get("DB_POOL_SIZE", "5"))
    max_overflow = int(os.environ.get("DB_MAX_OVERFLOW", "10"))
    pool_timeout = int(os.environ.get("DB_POOL_TIMEOUT", "30"))
    pool_pre_ping = os.environ.get("DB_POOL_PRE_PING", "1") in ("1", "true", "True", "yes")

    # For file-backed sqlite use the plain create_engine. For real DBs use pooling.
    if DATABASE_URL.startswith("sqlite"):
        engine = create_engine(DATABASE_URL, echo=True, future=True)
    else:
        engine = create_engine(
            DATABASE_URL,
            echo=True,
            future=True,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_pre_ping=pool_pre_ping,
        )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
