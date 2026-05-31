"""add_on_delete_cascade_to_token_fks

Revision ID: 4dd9b045d9d8
Revises: 5a61177eee13
Create Date: 2026-05-31 17:09:27.729819

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '4dd9b045d9d8'
down_revision: Union[str, Sequence[str], None] = '5a61177eee13'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint('one_time_tokens_user_id_fkey', 'one_time_tokens', type_='foreignkey')
    op.create_foreign_key(
        'one_time_tokens_user_id_fkey',
        'one_time_tokens', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE',
    )

    op.drop_constraint('refresh_tokens_user_id_fkey', 'refresh_tokens', type_='foreignkey')
    op.create_foreign_key(
        'refresh_tokens_user_id_fkey',
        'refresh_tokens', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('refresh_tokens_user_id_fkey', 'refresh_tokens', type_='foreignkey')
    op.create_foreign_key(
        'refresh_tokens_user_id_fkey',
        'refresh_tokens', 'users',
        ['user_id'], ['id'],
    )

    op.drop_constraint('one_time_tokens_user_id_fkey', 'one_time_tokens', type_='foreignkey')
    op.create_foreign_key(
        'one_time_tokens_user_id_fkey',
        'one_time_tokens', 'users',
        ['user_id'], ['id'],
    )
