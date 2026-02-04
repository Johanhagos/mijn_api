-- Add merchant_id to invoices for merchant ownership
-- Run this against your SQL database (Postgres, SQLite, etc.)

-- Add nullable merchant_id column
ALTER TABLE invoices
ADD COLUMN IF NOT EXISTS merchant_id INTEGER;

-- Optionally add FK constraint if `users` table exists (Postgres syntax)
-- ALTER TABLE invoices
-- ADD CONSTRAINT invoices_merchant_id_fkey FOREIGN KEY (merchant_id) REFERENCES users(id);
