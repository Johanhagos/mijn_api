"""add merchant_id to invoices

Revision ID: 0001_add_merchant_id
Revises: 
Create Date: 2026-01-31 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_add_merchant_id'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add nullable merchant_id column to invoices
    op.add_column('invoices', sa.Column('merchant_id', sa.Integer(), nullable=True))
    # If you want a FK to users.id, uncomment the following line
    # op.create_foreign_key('invoices_merchant_id_fkey', 'invoices', 'users', ['merchant_id'], ['id'])


def downgrade():
    # Remove merchant_id column
    # If FK was created, Alembic will drop it automatically when column removed in many DBs.
    try:
        op.drop_column('invoices', 'merchant_id')
    except Exception:
        # best-effort downgrade
        pass
