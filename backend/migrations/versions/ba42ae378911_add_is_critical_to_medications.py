"""add_is_critical_to_medications

Revision ID: ba42ae378911
Revises: dae449f3827d
Create Date: 2026-05-12 22:18:11.148663

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ba42ae378911'
down_revision: Union[str, Sequence[str], None] = 'dae449f3827d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('medications', sa.Column('is_critical', sa.Boolean(), server_default=sa.text('false'), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('medications', 'is_critical')
