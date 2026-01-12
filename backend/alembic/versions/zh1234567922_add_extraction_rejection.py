"""Add rejection fields to extracted_data.

Revision ID: zh1234567922
Revises: zg1234567921
Create Date: 2026-01-05

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "zh1234567922"
down_revision = "zg1234567921"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add rejection fields to extracted_data table."""
    # Add is_rejected boolean field
    op.add_column(
        "extracted_data",
        sa.Column(
            "is_rejected",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Whether this extraction was rejected by human review",
        ),
    )

    # Add rejected_by field
    op.add_column(
        "extracted_data",
        sa.Column(
            "rejected_by",
            sa.String(255),
            nullable=True,
            comment="Name/email of user who rejected",
        ),
    )

    # Add rejected_at timestamp
    op.add_column(
        "extracted_data",
        sa.Column(
            "rejected_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when rejection occurred",
        ),
    )

    # Add rejection_reason text field
    op.add_column(
        "extracted_data",
        sa.Column(
            "rejection_reason",
            sa.Text(),
            nullable=True,
            comment="Optional reason for rejection",
        ),
    )

    # Create index on is_rejected for efficient filtering
    op.create_index(
        "ix_extracted_data_is_rejected",
        "extracted_data",
        ["is_rejected"],
    )


def downgrade() -> None:
    """Remove rejection fields from extracted_data table."""
    op.drop_index("ix_extracted_data_is_rejected", table_name="extracted_data")
    op.drop_column("extracted_data", "rejection_reason")
    op.drop_column("extracted_data", "rejected_at")
    op.drop_column("extracted_data", "rejected_by")
    op.drop_column("extracted_data", "is_rejected")
