"""Initialize DB schema for local/production deployment.

Run this with the same Python environment used to run the app.
Example:
  DATA_DIR=/var/lib/apiblockchain DATABASE_URL=postgresql://user:pass@db:5432/apibc \ 
    venv/bin/python scripts/init_db.py
"""
from app.db.session import engine, Base
import app.models.hosted_session as hs
import models as legacy_models

def main():
    # Import Base from app.db.session (already defined there)
    # Create all tables known to SQLAlchemy metadata
    Base.metadata.create_all(bind=engine)
    print("DB initialized")

if __name__ == '__main__':
    main()
