"""add fire_at to nudge_campaigns

Revision ID: b1e4c7d2f8a0
Revises: a9f3b2c1d0e5
Create Date: 2026-04-19 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b1e4c7d2f8a0'
down_revision: Union[str, Sequence[str], None] = 'a9f3b2c1d0e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'nudge_campaigns',
        sa.Column('fire_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('nudge_campaigns', 'fire_at')
