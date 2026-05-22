"""add_caregiver_notes_table

Revision ID: 0d15cace4713
Revises: ed10e823b579
Create Date: 2026-05-23 00:07:16.903510

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0d15cace4713'
down_revision: Union[str, Sequence[str], None] = 'ed10e823b579'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('caregiver_notes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('author_name', sa.String(length=200), nullable=False),
        sa.Column('author_role', sa.String(length=20), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_caregiver_notes_id', 'caregiver_notes', ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_caregiver_notes_id', table_name='caregiver_notes')
    op.drop_table('caregiver_notes')
