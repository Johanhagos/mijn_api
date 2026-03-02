"""Initial migration: PHASE 1 multi-tenant schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-03-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial multi-tenant PostgreSQL schema."""
    
    # === ORGANIZATIONS ===
    op.create_table(
        'organizations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False, unique=True),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('timezone', sa.String(50), server_default='UTC'),
        sa.Column('currency', sa.String(3), server_default='EUR'),
        sa.Column('subscription_tier', sa.String(50), server_default='starter'),
        sa.Column('subscription_status', sa.String(50), server_default='active'),
        sa.Column('vat_number', sa.String(50), nullable=True),
        sa.Column('legal_name', sa.String(255), nullable=True),
        sa.Column('country', sa.String(2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # === USERS ===
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.Text(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), server_default='user'),
        sa.Column('email_verified', sa.Boolean(), server_default=False),
        sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('email_verification_token', sa.String(255), nullable=True),
        sa.Column('email_verification_expires', sa.DateTime(timezone=True), nullable=True),
        sa.Column('password_reset_token', sa.String(255), nullable=True),
        sa.Column('password_reset_expires', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id']),
        sa.UniqueConstraint('org_id', 'email', name='uq_user_org_email')
    )
    op.create_index('idx_user_org', 'users', ['org_id'])
    op.create_index('idx_user_email', 'users', ['email'])
    
    # === INVOICES ===
    op.create_table(
        'invoices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('number', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), server_default='draft'),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('customer_email', sa.String(255), nullable=False),
        sa.Column('customer_name', sa.String(255), nullable=False),
        sa.Column('customer_country', sa.String(2), nullable=False),
        sa.Column('customer_vat_id', sa.String(50), nullable=True),
        sa.Column('amount_subtotal', sa.Integer(), nullable=False),
        sa.Column('amount_tax', sa.Integer(), nullable=False),
        sa.Column('amount_total', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('tax_rate', sa.String(10), nullable=False),
        sa.Column('tax_breakdown', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_reverse_charge', sa.Boolean(), server_default=False),
        sa.Column('finalized_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('due_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('line_items', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('pdf_path', sa.String(255), nullable=True),
        sa.Column('created_from_invoice_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id']),
        sa.ForeignKeyConstraint(['created_from_invoice_id'], ['invoices.id']),
        sa.UniqueConstraint('org_id', 'number', name='uq_invoice_org_number')
    )
    op.create_index('idx_invoice_org', 'invoices', ['org_id'])
    op.create_index('idx_invoice_status', 'invoices', ['status'])
    op.create_index('idx_invoice_customer', 'invoices', ['customer_email'])
    
    # === INVOICE LINE ITEMS ===
    op.create_table(
        'invoice_line_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('description', sa.String(500), nullable=False),
        sa.Column('quantity', sa.Integer(), server_default='1'),
        sa.Column('unit_price', sa.Integer(), nullable=False),
        sa.Column('tax_rate', sa.String(10), nullable=False),
        sa.Column('tax_amount', sa.Integer(), nullable=False),
        sa.Column('subtotal', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'])
    )
    op.create_index('idx_line_invoice', 'invoice_line_items', ['invoice_id'])
    
    # === AUDIT_LOGS ===
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('user_agent', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'])
    )
    op.create_index('idx_audit_org', 'audit_logs', ['org_id'])
    op.create_index('idx_audit_user', 'audit_logs', ['user_id'])
    op.create_index('idx_audit_event', 'audit_logs', ['event_type'])
    op.create_index('idx_audit_created', 'audit_logs', ['created_at'])
    
    # === TOKEN_VERSIONS ===
    op.create_table(
        'token_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('version', sa.Integer(), server_default='1'),
        sa.Column('token_hash', sa.String(255), nullable=False),
        sa.Column('refresh_token_hash', sa.String(255), nullable=True),
        sa.Column('is_revoked', sa.Boolean(), server_default=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'])
    )
    op.create_index('idx_token_user', 'token_versions', ['user_id'])
    op.create_index('idx_token_org', 'token_versions', ['org_id'])
    
    # === API_KEYS ===
    op.create_table(
        'api_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('key_hash', sa.String(255), nullable=False),
        sa.Column('key_prefix', sa.String(20), nullable=False),
        sa.Column('permissions', postgresql.JSON(astext_type=sa.Text()), server_default='[]'),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_revoked', sa.Boolean(), server_default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id']),
        sa.UniqueConstraint('org_id', 'key_hash', name='uq_apikey_hash')
    )
    op.create_index('idx_apikey_org', 'api_keys', ['org_id'])
    
    # === Add org_id FK to organizations.owner_id ===
    # (This must be done after users table exists)
    op.create_foreign_key(
        'fk_org_owner',
        'organizations', 'users',
        ['owner_id'], ['id']
    )


def downgrade() -> None:
    """Rollback initial schema."""
    op.drop_table('api_keys')
    op.drop_table('token_versions')
    op.drop_table('audit_logs')
    op.drop_table('invoice_line_items')
    op.drop_table('invoices')
    op.drop_table('users')
    op.drop_table('organizations')
