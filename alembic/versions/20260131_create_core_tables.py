"""create core tables: users, payments, blockchain_transactions, audit_events

Revision ID: 20260131_create_core_tables
Revises: 
Create Date: 2026-01-31 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260131_create_core_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('username', sa.String, nullable=False, unique=True, index=True),
        sa.Column('password_hash', sa.String, nullable=False),
        sa.Column('role', sa.String, nullable=True, server_default='user'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_table(
        'payments',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('invoice_id', sa.Integer, sa.ForeignKey('invoices.id'), nullable=False, index=True),
        sa.Column('method', sa.String, nullable=False),
        sa.Column('status', sa.String, nullable=False, server_default='pending'),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('provider_ref', sa.String, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_table(
        'blockchain_transactions',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('invoice_id', sa.Integer, sa.ForeignKey('invoices.id'), nullable=False, index=True),
        sa.Column('chain', sa.String, nullable=False),
        sa.Column('tx_hash', sa.String, nullable=False, unique=True, index=True),
        sa.Column('block_number', sa.String, nullable=True),
        sa.Column('explorer_url', sa.String, nullable=True),
        sa.Column('confirmed', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_table(
        'audit_events',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('event_type', sa.String, nullable=False),
        sa.Column('actor', sa.String, nullable=True),
        sa.Column('ip_address', sa.String, nullable=True),
        sa.Column('details', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )


def downgrade():
    op.drop_table('audit_events')
    op.drop_table('blockchain_transactions')
    op.drop_table('payments')
    op.drop_table('users')
