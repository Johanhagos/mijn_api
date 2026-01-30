"""Add payment_system and blockchain_tx_id to invoices

Revision ID: 8b347b4b4b4f
Revises: 
Create Date: 2026-01-30 21:17:17.546685

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8b347b4b4b4f'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add columns: payment_system (string default 'web2') and blockchain_tx_id (nullable)
    op.add_column(
        "invoices",
        sa.Column("payment_system", sa.String(length=10), server_default=sa.text("'web2'"), nullable=False),
    )
    op.add_column(
        "invoices",
        sa.Column("blockchain_tx_id", sa.String(), nullable=True),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # Remove columns on downgrade
    op.drop_column("invoices", "blockchain_tx_id")
    op.drop_column("invoices", "payment_system")
    # ### end Alembic commands ###
