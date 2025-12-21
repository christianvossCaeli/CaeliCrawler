"""Add entity attachments table and related changes.

This migration adds:
1. entity_attachments table for user-uploaded files
2. ATTACHMENT value to facet_value_source_type enum
3. source_attachment_id column to facet_values
4. ATTACHMENT_ANALYSIS value to ai_task_type enum

Revision ID: ad1234567919
Revises: ac1234567918
Create Date: 2024-12-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "ad1234567919"
down_revision: Union[str, None] = "ac1234567918"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create attachment_analysis_status enum
    attachment_analysis_status = postgresql.ENUM(
        "PENDING",
        "ANALYZING",
        "COMPLETED",
        "FAILED",
        name="attachment_analysis_status",
    )
    attachment_analysis_status.create(op.get_bind(), checkfirst=True)

    # Create entity_attachments table
    op.create_table(
        "entity_attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "entity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("file_size", sa.BigInteger, nullable=False),
        sa.Column("file_path", sa.Text, nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column(
            "uploaded_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "analysis_status",
            attachment_analysis_status,
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column("analysis_result", postgresql.JSONB, nullable=True),
        sa.Column("analysis_error", sa.Text, nullable=True),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ai_model_used", sa.String(100), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
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
    )

    # Create indexes for entity_attachments
    op.create_index(
        "ix_entity_attachments_entity_id", "entity_attachments", ["entity_id"]
    )
    op.create_index(
        "ix_entity_attachments_file_hash", "entity_attachments", ["file_hash"]
    )
    op.create_index(
        "ix_entity_attachments_uploaded_by_id",
        "entity_attachments",
        ["uploaded_by_id"],
    )
    op.create_index(
        "ix_entity_attachments_analysis_status",
        "entity_attachments",
        ["analysis_status"],
    )
    op.create_index(
        "ix_entity_attachments_entity_status",
        "entity_attachments",
        ["entity_id", "analysis_status"],
    )
    op.create_index(
        "ix_entity_attachments_created", "entity_attachments", ["created_at"]
    )

    # Add ATTACHMENT to facet_value_source_type enum
    op.execute(
        "ALTER TYPE facet_value_source_type ADD VALUE IF NOT EXISTS 'ATTACHMENT'"
    )

    # Add source_attachment_id column to facet_values
    op.add_column(
        "facet_values",
        sa.Column(
            "source_attachment_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_facet_values_source_attachment",
        "facet_values",
        "entity_attachments",
        ["source_attachment_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_facet_values_source_attachment_id",
        "facet_values",
        ["source_attachment_id"],
    )

    # Add ATTACHMENT_ANALYSIS to ai_task_type enum
    op.execute(
        "ALTER TYPE ai_task_type ADD VALUE IF NOT EXISTS 'ATTACHMENT_ANALYSIS'"
    )


def downgrade() -> None:
    # Remove index and column from facet_values
    op.drop_index("ix_facet_values_source_attachment_id", table_name="facet_values")
    op.drop_constraint(
        "fk_facet_values_source_attachment", "facet_values", type_="foreignkey"
    )
    op.drop_column("facet_values", "source_attachment_id")

    # Drop entity_attachments table and indexes
    op.drop_index("ix_entity_attachments_created", table_name="entity_attachments")
    op.drop_index(
        "ix_entity_attachments_entity_status", table_name="entity_attachments"
    )
    op.drop_index(
        "ix_entity_attachments_analysis_status", table_name="entity_attachments"
    )
    op.drop_index(
        "ix_entity_attachments_uploaded_by_id", table_name="entity_attachments"
    )
    op.drop_index("ix_entity_attachments_file_hash", table_name="entity_attachments")
    op.drop_index("ix_entity_attachments_entity_id", table_name="entity_attachments")
    op.drop_table("entity_attachments")

    # Note: PostgreSQL doesn't support removing enum values easily
    # The attachment_analysis_status enum and ATTACHMENT/ATTACHMENT_ANALYSIS values
    # will remain in the database after downgrade
