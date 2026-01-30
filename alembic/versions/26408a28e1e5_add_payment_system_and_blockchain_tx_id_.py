"""Add payment_system and blockchain_tx_id to invoices

Revision ID: 26408a28e1e5
Revises: 8b347b4b4b4f
Create Date: 2026-01-30 21:17:51.304842

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '26408a28e1e5'
down_revision: Union[str, Sequence[str], None] = '8b347b4b4b4f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
