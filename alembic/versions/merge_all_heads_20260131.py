"""merge multiple heads

Revision ID: merge_all_heads_20260131
Revises: 0001_add_merchant_id,20260131_create_core_tables,26408a28e1e5
Create Date: 2026-01-31 00:10:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'merge_all_heads_20260131'
down_revision = ('0001_add_merchant_id', '20260131_create_core_tables', '26408a28e1e5')
branch_labels = None
depends_on = None


def upgrade():
    # Merge head-only revision: no DB changes required
    pass


def downgrade():
    # No-op downgrade
    pass
