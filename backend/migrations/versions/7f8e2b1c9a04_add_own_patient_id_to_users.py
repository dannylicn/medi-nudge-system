"""add_own_patient_id_to_users

Revision ID: 7f8e2b1c9a04
Revises: 2c7f9a1b4d6e
Create Date: 2026-05-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7f8e2b1c9a04"
down_revision: Union[str, Sequence[str], None] = "2c7f9a1b4d6e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("users")}
    if "own_patient_id" not in columns:
        with op.batch_alter_table("users") as batch_op:
            batch_op.add_column(sa.Column("own_patient_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_users_own_patient_id_patients",
                "patients",
                ["own_patient_id"],
                ["id"],
            )


def downgrade() -> None:
    """Downgrade schema."""
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("users")}
    if "own_patient_id" in columns:
        with op.batch_alter_table("users") as batch_op:
            batch_op.drop_column("own_patient_id")
