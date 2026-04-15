"""add telegram_chat_id to patients and onboarding_tokens table

Revision ID: a1b2c3d4e5f6
Revises: f20cf3afdc1a
Create Date: 2026-04-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f20cf3afdc1a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('patients') as batch_op:
        batch_op.add_column(sa.Column('telegram_chat_id', sa.String(length=30), nullable=True))
        batch_op.create_unique_constraint('uq_patients_telegram_chat_id', ['telegram_chat_id'])

    op.create_table(
        'onboarding_tokens',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('patient_id', sa.Integer(), sa.ForeignKey('patients.id'), nullable=False),
        sa.Column('token', sa.String(length=64), nullable=False, unique=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_onboarding_tokens_token', 'onboarding_tokens', ['token'])
    op.create_index('ix_onboarding_tokens_patient_id', 'onboarding_tokens', ['patient_id'])


def downgrade() -> None:
    op.drop_index('ix_onboarding_tokens_patient_id', 'onboarding_tokens')
    op.drop_index('ix_onboarding_tokens_token', 'onboarding_tokens')
    op.drop_table('onboarding_tokens')
    with op.batch_alter_table('patients') as batch_op:
        batch_op.drop_constraint('uq_patients_telegram_chat_id', type_='unique')
        batch_op.drop_column('telegram_chat_id')
