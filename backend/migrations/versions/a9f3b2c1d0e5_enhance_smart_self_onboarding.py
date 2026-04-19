"""enhance smart self onboarding

Revision ID: a9f3b2c1d0e5
Revises: dae449f3827d
Create Date: 2026-04-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9f3b2c1d0e5'
down_revision: Union[str, Sequence[str], None] = 'dae449f3827d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'nudge_campaigns',
        sa.Column('campaign_type', sa.String(length=50), nullable=False, server_default='refill_reminder'),
    )
    op.add_column(
        'patient_medications',
        sa.Column('med_info_card_sent_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('patient_medications', 'med_info_card_sent_at')
    op.drop_column('nudge_campaigns', 'campaign_type')
