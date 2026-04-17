"""add dose_logs table

Revision ID: dae449f3827d
Revises: 446a73655e26
Create Date: 2026-04-17 08:54:34.728796

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dae449f3827d'
down_revision: Union[str, Sequence[str], None] = '446a73655e26'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('dose_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.Integer(), nullable=False),
    sa.Column('medication_id', sa.Integer(), nullable=False),
    sa.Column('patient_medication_id', sa.Integer(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('source', sa.String(length=30), nullable=False),
    sa.Column('logged_at', sa.DateTime(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['medication_id'], ['medications.id'], ),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.ForeignKeyConstraint(['patient_medication_id'], ['patient_medications.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dose_logs_id'), 'dose_logs', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_dose_logs_id'), table_name='dose_logs')
    op.drop_table('dose_logs')
