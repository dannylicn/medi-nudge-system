"""merge_danny_upstream_and_is_critical

Revision ID: 5a2f617832e4
Revises: b1e4c7d2f8a0, ba42ae378911
Create Date: 2026-05-14 15:56:10.648219

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5a2f617832e4'
down_revision: Union[str, Sequence[str], None] = ('b1e4c7d2f8a0', 'ba42ae378911')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
