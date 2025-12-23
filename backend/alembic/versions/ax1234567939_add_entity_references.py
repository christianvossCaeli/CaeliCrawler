"""Add entity references to extracted_data and display_fields to categories.

Generic Entity-Reference System:
- ExtractedData.entity_references: JSONB array of entity references
- ExtractedData.primary_entity_id: FK to primary referenced entity
- Category.display_fields: Configuration for result display columns
- Category.entity_reference_config: Config for entity reference extraction

Revision ID: ax1234567939
Revises: aw1234567938
Create Date: 2024-12-23
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision: str = "ax1234567939"
down_revision: Union[str, None] = "aw1234567938"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in the table."""
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # === ExtractedData table ===

    # Add entity_references JSONB column
    if not column_exists("extracted_data", "entity_references"):
        op.add_column(
            "extracted_data",
            sa.Column(
                "entity_references",
                JSONB,
                nullable=True,
                comment="AI-extracted entity references: [{entity_type, entity_name, entity_id, role, confidence}]",
            ),
        )

    # Add primary_entity_id FK column
    if not column_exists("extracted_data", "primary_entity_id"):
        op.add_column(
            "extracted_data",
            sa.Column(
                "primary_entity_id",
                UUID(as_uuid=True),
                nullable=True,
                comment="Primary entity referenced in this extraction",
            ),
        )

        # Create FK constraint
        op.create_foreign_key(
            "fk_extracted_data_primary_entity",
            "extracted_data",
            "entities",
            ["primary_entity_id"],
            ["id"],
            ondelete="SET NULL",
        )

        # Create index for primary_entity_id
        op.create_index(
            "ix_extracted_data_primary_entity_id",
            "extracted_data",
            ["primary_entity_id"],
        )

    # === Categories table ===

    # Add display_fields JSONB column
    if not column_exists("categories", "display_fields"):
        op.add_column(
            "categories",
            sa.Column(
                "display_fields",
                JSONB,
                nullable=True,
                comment="Configuration for result display columns: {columns: [{key, label, type, width}]}",
            ),
        )

    # Add entity_reference_config JSONB column
    if not column_exists("categories", "entity_reference_config"):
        op.add_column(
            "categories",
            sa.Column(
                "entity_reference_config",
                JSONB,
                nullable=True,
                comment="Config for entity reference extraction: {entity_types: ['territorial-entity']}",
            ),
        )


def downgrade() -> None:
    # === Categories table ===
    if column_exists("categories", "entity_reference_config"):
        op.drop_column("categories", "entity_reference_config")

    if column_exists("categories", "display_fields"):
        op.drop_column("categories", "display_fields")

    # === ExtractedData table ===
    if column_exists("extracted_data", "primary_entity_id"):
        op.drop_index("ix_extracted_data_primary_entity_id", table_name="extracted_data")
        op.drop_constraint("fk_extracted_data_primary_entity", "extracted_data", type_="foreignkey")
        op.drop_column("extracted_data", "primary_entity_id")

    if column_exists("extracted_data", "entity_references"):
        op.drop_column("extracted_data", "entity_references")
