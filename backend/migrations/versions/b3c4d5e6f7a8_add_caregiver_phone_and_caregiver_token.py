"""add caregiver_phone_number to patients and is_caregiver to onboarding_tokens

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-04-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('patients') as batch_op:
        batch_op.add_column(sa.Column('caregiver_phone_number', sa.String(length=30), nullable=True))

    with op.batch_alter_table('onboarding_tokens') as batch_op:
        batch_op.add_column(
            sa.Column('is_caregiver', sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade() -> None:
    with op.batch_alter_table('onboarding_tokens') as batch_op:
        batch_op.drop_column('is_caregiver')

    with op.batch_alter_table('patients') as batch_op:
        batch_op.drop_column('caregiver_phone_number')
