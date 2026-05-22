"""add_role_and_patient_id_to_users

Revision ID: ed10e823b579
Revises: 76902d052cc4
Create Date: 2026-05-22 22:09:38.272559

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ed10e823b579'
down_revision: Union[str, Sequence[str], None] = '76902d052cc4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('role', sa.String(length=20), server_default='admin', nullable=False))
    op.add_column('users', sa.Column('patient_id', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'patient_id')
    op.drop_column('users', 'role')
