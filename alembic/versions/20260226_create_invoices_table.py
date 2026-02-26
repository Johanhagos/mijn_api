"""create invoices table

Revision ID: 20260226_create_invoices_table
Revises: merge_all_heads_20260131
Create Date: 2026-02-26 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260226_create_invoices_table'
# Make this a base revision so it can be applied before older revisions that
# assumed `invoices` existed (we set dependent migrations to reference this).
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'invoices',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('invoice_number', sa.String(), nullable=True),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('status', sa.String(), nullable=False, server_default=sa.text("'draft'")),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )


def downgrade():
    op.drop_table('invoices')
