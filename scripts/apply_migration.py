"""
Simple migration runner: applies the SQL file at migrations/0001_add_merchant_id.sql

Usage:
  set DATABASE_URL=postgresql://user:pass@host/dbname
  python scripts/apply_migration.py

This script uses SQLAlchemy to execute the SQL against the provided DATABASE_URL.
It is intentionally minimal to avoid adding a full Alembic scaffold.
"""
import os
from sqlalchemy import create_engine, text

SQL_FILE = os.path.join(os.path.dirname(__file__), '..', 'migrations', '0001_add_merchant_id.sql')

def main():
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print('Missing DATABASE_URL environment variable')
        return 1

    with open(SQL_FILE, 'r', encoding='utf-8') as f:
        sql = f.read()

    engine = create_engine(db_url)
    with engine.connect() as conn:
        print('Applying migration...')
        dialect = engine.dialect.name
        try:
            if dialect == 'sqlite':
                # SQLite doesn't support `ADD COLUMN IF NOT EXISTS` on older versions
                stmt = 'ALTER TABLE invoices ADD COLUMN merchant_id INTEGER;'
                try:
                    conn.execute(text(stmt))
                except Exception as e:
                    # If the column already exists or SQLite returns an error we can't handle,
                    # print and continue.
                    msg = str(e)
                    if 'duplicate column name' in msg or 'already exists' in msg.lower():
                        print('merchant_id column already exists (sqlite) — skipping')
                    else:
                        raise
            else:
                conn.execute(text(sql))
            print('Migration applied successfully')
        except Exception as exc:
            print('Migration failed:', exc)
            return 2

    return 0

if __name__ == '__main__':
    raise SystemExit(main())
