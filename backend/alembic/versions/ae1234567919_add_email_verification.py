"""Add email verification fields to users.

Adds:
1. email_verified - boolean flag
2. email_verification_token - token for verification links
3. email_verification_sent_at - timestamp for rate limiting

Revision ID: ae1234567919
Revises: ad1234567918
Create Date: 2024-12-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ae1234567919"
down_revision: Union[str, None] = "ad1234567918"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add email_verified column - existing users are assumed verified
    op.add_column(
        "users",
        sa.Column(
            "email_verified",
            sa.Boolean(),
            nullable=False,
            server_default="true",  # Existing users are grandfathered in
        ),
    )

    # Add email_verification_token column
    op.add_column(
        "users",
        sa.Column(
            "email_verification_token",
            sa.String(255),
            nullable=True,
        ),
    )

    # Add email_verification_sent_at column for rate limiting
    op.add_column(
        "users",
        sa.Column(
            "email_verification_sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "email_verification_sent_at")
    op.drop_column("users", "email_verification_token")
    op.drop_column("users", "email_verified")
