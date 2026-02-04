"""
Create a minimal `invoices` table if it does not exist.

This is a one-off helper to prepare a fresh DB for existing Alembic revisions
that expect `invoices` to already exist.
"""
import os
from sqlalchemy import create_engine, text

db_url = os.getenv('DATABASE_URL')
if not db_url:
    print('Please set DATABASE_URL')
    raise SystemExit(1)

engine = create_engine(db_url)

sql = '''
CREATE TABLE IF NOT EXISTS invoices (
    id SERIAL PRIMARY KEY,
    invoice_number VARCHAR(128),
    order_number VARCHAR(128),
    seller_name VARCHAR(255),
    seller_vat VARCHAR(64),
    buyer_name VARCHAR(255),
    buyer_vat VARCHAR(64),
    date_issued TIMESTAMP WITH TIME ZONE DEFAULT now(),
    subtotal NUMERIC(12,2) DEFAULT 0,
    vat_amount NUMERIC(12,2) DEFAULT 0,
    total NUMERIC(12,2) DEFAULT 0,
    payment_system VARCHAR(32) DEFAULT 'web2',
    blockchain_tx_id VARCHAR(255),
    pdf_url TEXT,
    created_by VARCHAR(128),
    merchant_id INTEGER
);
'''

with engine.begin() as conn:
    print('Creating invoices table if missing...')
    conn.execute(text(sql))
    print('Done')
