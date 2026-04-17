"""add pending_action to patients

Revision ID: 446a73655e26
Revises: 822dc78fb3f0
Create Date: 2026-04-16 23:51:07.175353

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '446a73655e26'
down_revision: Union[str, Sequence[str], None] = '822dc78fb3f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('patients', sa.Column('pending_action', sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column('patients', 'pending_action')
