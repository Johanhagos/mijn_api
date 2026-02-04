import os
from sqlalchemy import create_engine, text

db_url = os.getenv('DATABASE_URL')
if not db_url:
    print('Please set DATABASE_URL')
    raise SystemExit(1)

engine = create_engine(db_url)
with engine.begin() as conn:
    print('Dropping columns if they exist...')
    conn.execute(text('ALTER TABLE invoices DROP COLUMN IF EXISTS payment_system'))
    conn.execute(text('ALTER TABLE invoices DROP COLUMN IF EXISTS blockchain_tx_id'))
    print('Done')
