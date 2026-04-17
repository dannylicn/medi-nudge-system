"""add voice profile and patient voice fields

Revision ID: 822dc78fb3f0
Revises: b3c4d5e6f7a8
Create Date: 2026-04-16 17:05:04.661263

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '822dc78fb3f0'
down_revision: Union[str, Sequence[str], None] = 'b3c4d5e6f7a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('voice_profiles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.Integer(), nullable=False),
    sa.Column('donor_name', sa.String(length=200), nullable=True),
    sa.Column('donor_telegram_id', sa.String(length=30), nullable=True),
    sa.Column('elevenlabs_voice_id', sa.String(length=100), nullable=True),
    sa.Column('sample_file_path', sa.String(length=500), nullable=True),
    sa.Column('patient_consent_at', sa.DateTime(), nullable=True),
    sa.Column('donor_consent_at', sa.DateTime(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_voice_profiles_id'), 'voice_profiles', ['id'], unique=False)
    op.add_column('patients', sa.Column('nudge_delivery_mode', sa.String(length=10), server_default='text', nullable=False))
    op.add_column('patients', sa.Column('selected_voice_id', sa.String(length=100), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('patients', 'selected_voice_id')
    op.drop_column('patients', 'nudge_delivery_mode')
    op.drop_index(op.f('ix_voice_profiles_id'), table_name='voice_profiles')
    op.drop_table('voice_profiles')
