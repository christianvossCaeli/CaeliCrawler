"""Add language preference to users

Revision ID: o1234567903
Revises: n1234567902
Create Date: 2024-12-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'o1234567903'
down_revision: Union[str, None] = 'n1234567902'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add language column with default 'de' for existing users
    op.add_column(
        'users',
        sa.Column(
            'language',
            sa.String(5),
            nullable=False,
            server_default='de'
        )
    )


def downgrade() -> None:
    op.drop_column('users', 'language')
