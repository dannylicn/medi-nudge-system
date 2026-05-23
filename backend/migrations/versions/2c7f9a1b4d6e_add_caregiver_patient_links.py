"""add_caregiver_patient_links

Revision ID: 2c7f9a1b4d6e
Revises: 0d15cace4713
Create Date: 2026-05-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2c7f9a1b4d6e"
down_revision: Union[str, Sequence[str], None] = "0d15cace4713"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "caregiver_patient_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("caregiver_user_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("relationship", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["caregiver_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("caregiver_user_id", "patient_id"),
    )
    op.create_index("ix_caregiver_patient_links_id", "caregiver_patient_links", ["id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_caregiver_patient_links_id", table_name="caregiver_patient_links")
    op.drop_table("caregiver_patient_links")
