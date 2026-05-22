"""add_missed_dose_info_to_medications

Revision ID: 76902d052cc4
Revises: 5a2f617832e4
Create Date: 2026-05-22 15:01:52.273674

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '76902d052cc4'
down_revision: Union[str, Sequence[str], None] = '5a2f617832e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('medications', sa.Column('missed_dose_info', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('medications', 'missed_dose_info')
