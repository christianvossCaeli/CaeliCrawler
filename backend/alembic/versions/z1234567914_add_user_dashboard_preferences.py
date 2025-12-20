"""Add user_dashboard_preferences table for widget configuration.

Revision ID: z1234567914
Revises: y1234567913
Create Date: 2025-01-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "z1234567914"
down_revision = "y1234567913"
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    # Skip if table already exists (idempotent)
    if table_exists("user_dashboard_preferences"):
        return

    # Create user_dashboard_preferences table
    op.create_table(
        "user_dashboard_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "widget_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
    )

    # Create unique index on user_id (one preference per user)
    op.create_index(
        "ix_user_dashboard_preferences_user_id",
        "user_dashboard_preferences",
        ["user_id"],
        unique=True,
    )


def downgrade() -> None:
    # Drop index
    op.drop_index(
        "ix_user_dashboard_preferences_user_id",
        table_name="user_dashboard_preferences",
    )

    # Drop table
    op.drop_table("user_dashboard_preferences")
