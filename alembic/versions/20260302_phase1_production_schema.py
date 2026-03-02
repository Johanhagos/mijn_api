"""phase1_production_grade_schema

Revision ID: 20260302_phase1
Revises: merge_all_heads_20260131
Create Date: 2026-03-02 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260302_phase1'
down_revision = 'merge_all_heads_20260131'
branch_labels = None
depends_on = None


def upgrade():
    # Enhance shops table
    op.add_column('shops', sa.Column('registration_number', sa.Text(), nullable=True))
    op.add_column('shops', sa.Column('eori_number', sa.Text(), nullable=True))
    op.add_column('shops', sa.Column('email', sa.Text(), nullable=True))
    op.add_column('shops', sa.Column('phone', sa.Text(), nullable=True))
    op.add_column('shops', sa.Column('logo_url', sa.Text(), nullable=True))
    op.add_column('shops', sa.Column('active', sa.Boolean(), nullable=True, server_default='true'))
    op.add_column('shops', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('shops', sa.Column('last_invoice_number', sa.Integer(), nullable=True, server_default='0'))
    op.create_index('idx_shop_api_key', 'shops', ['api_key_hash'])

    # Enhance users table
    op.add_column('users', sa.Column('name', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('active', sa.Boolean(), nullable=True, server_default='true'))
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('users', sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('last_login_ip', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('token_version', sa.Integer(), nullable=True, server_default='1'))
    op.add_column('users', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('idx_user_email', 'users', ['email'])
    op.create_unique_constraint('uq_user_email', 'users', ['email'])

    # Enhance invoices table - immutability and finalization
    op.add_column('invoices', sa.Column('finalized', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('invoices', sa.Column('finalized_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('invoices', sa.Column('finalized_by', postgresql.UUID(as_uuid=False), nullable=True))
    op.add_column('invoices', sa.Column('payment_method', sa.String(length=20), nullable=True))
    op.add_column('invoices', sa.Column('payment_reference', sa.Text(), nullable=True))
    op.add_column('invoices', sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('invoices', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key('fk_invoice_finalized_by', 'invoices', 'users', ['finalized_by'], ['id'])
    op.create_index('idx_invoice_shop_status', 'invoices', ['shop_id', 'status'])
    op.create_index('idx_invoice_customer', 'invoices', ['customer_id'])

    # Enhance invoice_items table - VAT breakdown
    op.add_column('invoice_items', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('invoice_items', sa.Column('subtotal', sa.Numeric(10, 2), nullable=True))
    op.add_column('invoice_items', sa.Column('vat_amount', sa.Numeric(10, 2), nullable=True))
    op.alter_column('invoice_items', 'vat_rate', type_=sa.Numeric(5, 2))

    # Create refresh_tokens table
    op.create_table(
        'refresh_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('token_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('token_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('valid', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_reason', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.Text(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
    )
    op.create_index('idx_refresh_token', 'refresh_tokens', ['token_hash'])
    op.create_index('idx_refresh_user_valid', 'refresh_tokens', ['user_id', 'valid'])

    # Create email_verifications table
    op.create_table(
        'email_verifications',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('token', sa.String(64), nullable=False, unique=True),
        sa.Column('verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
    )
    op.create_index('idx_email_token', 'email_verifications', ['token'])

    # Create password_resets table
    op.create_table(
        'password_resets',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('token', sa.String(64), nullable=False, unique=True),
        sa.Column('used', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ip_address', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
    )
    op.create_index('idx_password_reset_token', 'password_resets', ['token'])

    # Create subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('shop_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('plan', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('stripe_subscription_id', sa.Text(), nullable=True),
        sa.Column('stripe_customer_id', sa.Text(), nullable=True),
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancel_at_period_end', sa.Boolean(), server_default='false'),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('max_invoices_per_month', sa.Integer(), nullable=True),
        sa.Column('max_team_members', sa.Integer(), nullable=True),
        sa.Column('advanced_tax_enabled', sa.Boolean(), server_default='false'),
        sa.ForeignKeyConstraint(['shop_id'], ['shops.id']),
    )
    op.create_index('idx_subscription_shop', 'subscriptions', ['shop_id'])
    op.create_index('idx_subscription_status', 'subscriptions', ['status'])

    # Create usage_metrics table
    op.create_table(
        'usage_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('shop_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=False), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=False), nullable=False),
        sa.Column('invoice_count', sa.Integer(), server_default='0'),
        sa.Column('api_request_count', sa.Integer(), server_default='0'),
        sa.Column('storage_bytes', sa.Numeric(15, 0), server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['shop_id'], ['shops.id']),
    )
    op.create_index('idx_usage_shop_period', 'usage_metrics', ['shop_id', 'period_start'])

    # Create rate_limits table
    op.create_table(
        'rate_limits',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('key', sa.String(255), nullable=False),
        sa.Column('window_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('request_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_ratelimit_key_window', 'rate_limits', ['key', 'window_start'])

    # Create invoice_history table
    op.create_table(
        'invoice_history',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('changed_by', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('change_type', sa.String(20), nullable=False),
        sa.Column('snapshot', postgresql.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id']),
        sa.ForeignKeyConstraint(['changed_by'], ['users.id']),
    )
    op.create_index('idx_invoice_history_invoice', 'invoice_history', ['invoice_id'])

    # Enhance audit_logs table
    op.add_column('audit_logs', sa.Column('extra_data', postgresql.JSON(), nullable=True))
    op.add_column('audit_logs', sa.Column('user_agent', sa.Text(), nullable=True))
    op.create_index('idx_audit_shop_created', 'audit_logs', ['shop_id', 'created_at'])
    op.create_index('idx_audit_actor', 'audit_logs', ['actor'])


def downgrade():
    # Drop new tables
    op.drop_table('invoice_history')
    op.drop_table('rate_limits')
    op.drop_table('usage_metrics')
    op.drop_table('subscriptions')
    op.drop_table('password_resets')
    op.drop_table('email_verifications')
    op.drop_table('refresh_tokens')

    # Remove added columns from existing tables
    op.drop_column('audit_logs', 'user_agent')
    op.drop_column('audit_logs', 'extra_data')
    
    op.drop_column('invoice_items', 'vat_amount')
    op.drop_column('invoice_items', 'subtotal')
    op.drop_column('invoice_items', 'description')
    
    op.drop_column('invoices', 'updated_at')
    op.drop_column('invoices', 'paid_at')
    op.drop_column('invoices', 'payment_reference')
    op.drop_column('invoices', 'payment_method')
    op.drop_column('invoices', 'finalized_by')
    op.drop_column('invoices', 'finalized_at')
    op.drop_column('invoices', 'finalized')
    
    op.drop_column('users', 'updated_at')
    op.drop_column('users', 'token_version')
    op.drop_column('users', 'last_login_ip')
    op.drop_column('users', 'last_login_at')
    op.drop_column('users', 'email_verified_at')
    op.drop_column('users', 'email_verified')
    op.drop_column('users', 'active')
    op.drop_column('users', 'name')
    
    op.drop_column('shops', 'last_invoice_number')
    op.drop_column('shops', 'updated_at')
    op.drop_column('shops', 'active')
    op.drop_column('shops', 'logo_url')
    op.drop_column('shops', 'phone')
    op.drop_column('shops', 'email')
    op.drop_column('shops', 'eori_number')
    op.drop_column('shops', 'registration_number')
