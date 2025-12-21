"""Add api_templates table for KI-First Discovery.

Stores validated API configurations that can be reused for future discoveries.
Templates can be created automatically (from successful KI-First discoveries)
or manually by administrators.

Revision ID: ak1234567927
Revises: aj1234567926
Create Date: 2024-12-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = "ak1234567927"
down_revision: Union[str, None] = "aj1234567926"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    # Skip if table already exists (idempotent)
    if table_exists("api_templates"):
        return

    # Create API type enum
    api_type_enum = sa.Enum("REST", "GRAPHQL", "SPARQL", "OPARL", name="api_type_enum")
    api_type_enum.create(op.get_bind(), checkfirst=True)

    # Create template status enum
    template_status_enum = sa.Enum(
        "ACTIVE", "INACTIVE", "FAILED", "PENDING", name="template_status_enum"
    )
    template_status_enum.create(op.get_bind(), checkfirst=True)

    # Create api_templates table
    op.create_table(
        "api_templates",
        # Primary key
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        # Basic info
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        # API configuration
        sa.Column(
            "api_type",
            api_type_enum,
            nullable=False,
            server_default="REST",
        ),
        sa.Column("base_url", sa.Text, nullable=False),
        sa.Column("endpoint", sa.Text, nullable=False),
        sa.Column("documentation_url", sa.Text, nullable=True),
        # Authentication
        sa.Column("auth_required", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("auth_config", JSONB, nullable=True),
        # Field mapping and keywords
        sa.Column(
            "field_mapping",
            JSONB,
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "keywords",
            JSONB,
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "default_tags",
            JSONB,
            nullable=False,
            server_default="[]",
        ),
        # Status and validation
        sa.Column(
            "status",
            template_status_enum,
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("last_validated", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_validation_error", sa.Text, nullable=True),
        sa.Column("validation_item_count", sa.Integer, nullable=True),
        # Usage tracking
        sa.Column("usage_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_used", sa.DateTime(timezone=True), nullable=True),
        # Confidence and source
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.8"),
        sa.Column("source", sa.String(50), nullable=False, server_default="'manual'"),
        # Creator (optional)
        sa.Column("created_by_id", UUID(as_uuid=True), nullable=True),
        # Timestamps
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
            onupdate=sa.func.now(),
            nullable=False,
        ),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
    )

    # Create indexes
    op.create_index(
        "ix_api_templates_name",
        "api_templates",
        ["name"],
    )
    op.create_index(
        "ix_api_templates_status",
        "api_templates",
        ["status"],
    )
    op.create_index(
        "ix_api_templates_api_type",
        "api_templates",
        ["api_type"],
    )
    op.create_index(
        "ix_api_templates_usage_count",
        "api_templates",
        ["usage_count"],
    )
    # GIN index for keyword search
    op.create_index(
        "ix_api_templates_keywords_gin",
        "api_templates",
        ["keywords"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_api_templates_keywords_gin", table_name="api_templates")
    op.drop_index("ix_api_templates_usage_count", table_name="api_templates")
    op.drop_index("ix_api_templates_api_type", table_name="api_templates")
    op.drop_index("ix_api_templates_status", table_name="api_templates")
    op.drop_index("ix_api_templates_name", table_name="api_templates")

    # Drop table
    op.drop_table("api_templates")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS template_status_enum")
    op.execute("DROP TYPE IF EXISTS api_type_enum")
