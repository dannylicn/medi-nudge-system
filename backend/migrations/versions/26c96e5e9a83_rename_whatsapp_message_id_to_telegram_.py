"""rename whatsapp_message_id to telegram_message_id

Revision ID: 26c96e5e9a83
Revises: 4e74cc366ee6
Create Date: 2026-04-11 19:08:39.145689

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '26c96e5e9a83'
down_revision: Union[str, Sequence[str], None] = '4e74cc366ee6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('outbound_messages') as batch_op:
        batch_op.alter_column('whatsapp_message_id', new_column_name='telegram_message_id')


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('outbound_messages') as batch_op:
        batch_op.alter_column('telegram_message_id', new_column_name='whatsapp_message_id')
