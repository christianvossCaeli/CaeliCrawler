"""Add facet_value_history table for timeline/history tracking.

This migration introduces a dedicated table for storing time-series data
for the new HISTORY facet type, enabling tracking of values over time
(e.g., stock prices, population counts, budget data).

Revision ID: at1234567935
Revises: as1234567934
Create Date: 2024-12-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "at1234567935"
down_revision: Union[str, None] = "as1234567934"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create facet_value_history table for time-series data
    op.create_table(
        "facet_value_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "entity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("entities.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "facet_type_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("facet_types.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        # Track identification for multi-track support (e.g., "actual" vs "forecast")
        sa.Column(
            "track_key",
            sa.String(255),
            nullable=False,
            server_default="default",
        ),
        # The actual data point
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "value",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "value_label",
            sa.String(255),
            nullable=True,
            comment="Formatted value for display (e.g., '1.234,56 EUR')",
        ),
        sa.Column(
            "annotations",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
            comment="Additional metadata like notes, trend indicators",
        ),
        # Source tracking (reuses existing FacetValueSourceType enum)
        sa.Column(
            "source_type",
            sa.Enum(
                "DOCUMENT",
                "MANUAL",
                "PYSIS",
                "SMART_QUERY",
                "AI_ASSISTANT",
                "IMPORT",
                "ATTACHMENT",
                name="facetvaluesourcetype",
                create_type=False,  # Enum already exists
            ),
            nullable=False,
            server_default="MANUAL",
            index=True,
        ),
        sa.Column(
            "source_document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "source_url",
            sa.Text(),
            nullable=True,
        ),
        # AI/Quality metadata
        sa.Column(
            "confidence_score",
            sa.Float(),
            nullable=False,
            server_default="1.0",
        ),
        sa.Column(
            "ai_model_used",
            sa.String(100),
            nullable=True,
        ),
        # Human verification
        sa.Column(
            "human_verified",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "verified_by",
            sa.String(255),
            nullable=True,
        ),
        sa.Column(
            "verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
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
            nullable=False,
        ),
        # Unique constraint: One data point per entity+facet+track+timestamp
        sa.UniqueConstraint(
            "entity_id",
            "facet_type_id",
            "track_key",
            "recorded_at",
            name="uq_history_datapoint",
        ),
    )

    # Performance indexes for common query patterns
    op.create_index(
        "ix_fvh_entity_type",
        "facet_value_history",
        ["entity_id", "facet_type_id"],
    )
    op.create_index(
        "ix_fvh_entity_type_track",
        "facet_value_history",
        ["entity_id", "facet_type_id", "track_key"],
    )
    op.create_index(
        "ix_fvh_entity_type_time_desc",
        "facet_value_history",
        ["entity_id", "facet_type_id", sa.text("recorded_at DESC")],
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_fvh_entity_type_time_desc", table_name="facet_value_history")
    op.drop_index("ix_fvh_entity_type_track", table_name="facet_value_history")
    op.drop_index("ix_fvh_entity_type", table_name="facet_value_history")

    # Drop table
    op.drop_table("facet_value_history")
