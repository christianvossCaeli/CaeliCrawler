"""Add filterable location columns to entities table.

This migration adds dedicated columns for country, admin_level_1, and admin_level_2
to the entities table for efficient filtering. Previously, this data was only stored
in the core_attributes JSONB field.

Changes:
- Add country (ISO 3166-1 alpha-2 code, e.g., DE, GB)
- Add admin_level_1 (Bundesland, Region, State)
- Add admin_level_2 (Landkreis, District)
- Migrate existing data from core_attributes
- Create composite index for efficient filtering

Revision ID: m1234567901
Revises: l1234567900
Create Date: 2024-12-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "m1234567901"
down_revision: Union[str, None] = "l1234567900"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # Step 1: Add new columns (nullable initially)
    # =========================================================================

    op.add_column(
        "entities",
        sa.Column(
            "country",
            sa.String(2),
            nullable=True,
            comment="ISO 3166-1 alpha-2 country code (DE, GB, etc.)",
        ),
    )
    op.add_column(
        "entities",
        sa.Column(
            "admin_level_1",
            sa.String(100),
            nullable=True,
            comment="First-level admin division (Bundesland, Region, State)",
        ),
    )
    op.add_column(
        "entities",
        sa.Column(
            "admin_level_2",
            sa.String(100),
            nullable=True,
            comment="Second-level admin division (Landkreis, District)",
        ),
    )

    # =========================================================================
    # Step 2: Migrate existing data from core_attributes
    # =========================================================================

    # Migrate country (ensure uppercase)
    op.execute("""
        UPDATE entities
        SET country = UPPER(core_attributes->>'country')
        WHERE core_attributes->>'country' IS NOT NULL
          AND country IS NULL
    """)

    # Migrate admin_level_1
    op.execute("""
        UPDATE entities
        SET admin_level_1 = core_attributes->>'admin_level_1'
        WHERE core_attributes->>'admin_level_1' IS NOT NULL
          AND admin_level_1 IS NULL
    """)

    # Migrate admin_level_2
    op.execute("""
        UPDATE entities
        SET admin_level_2 = core_attributes->>'admin_level_2'
        WHERE core_attributes->>'admin_level_2' IS NOT NULL
          AND admin_level_2 IS NULL
    """)

    # =========================================================================
    # Step 3: Create indexes for efficient filtering
    # =========================================================================

    op.create_index("ix_entities_country", "entities", ["country"])
    op.create_index("ix_entities_admin_level_1", "entities", ["admin_level_1"])
    op.create_index("ix_entities_admin_level_2", "entities", ["admin_level_2"])

    # Composite index for common filter combinations
    op.create_index(
        "ix_entities_country_admin_levels",
        "entities",
        ["country", "admin_level_1", "admin_level_2"],
    )


def downgrade() -> None:
    # =========================================================================
    # Step 1: Migrate data back to core_attributes (preserve data)
    # =========================================================================

    op.execute("""
        UPDATE entities
        SET core_attributes = jsonb_set(
            COALESCE(core_attributes, '{}'::jsonb),
            '{country}',
            to_jsonb(country)
        )
        WHERE country IS NOT NULL
          AND (core_attributes->>'country' IS NULL OR core_attributes->>'country' = '')
    """)

    op.execute("""
        UPDATE entities
        SET core_attributes = jsonb_set(
            COALESCE(core_attributes, '{}'::jsonb),
            '{admin_level_1}',
            to_jsonb(admin_level_1)
        )
        WHERE admin_level_1 IS NOT NULL
          AND (core_attributes->>'admin_level_1' IS NULL OR core_attributes->>'admin_level_1' = '')
    """)

    op.execute("""
        UPDATE entities
        SET core_attributes = jsonb_set(
            COALESCE(core_attributes, '{}'::jsonb),
            '{admin_level_2}',
            to_jsonb(admin_level_2)
        )
        WHERE admin_level_2 IS NOT NULL
          AND (core_attributes->>'admin_level_2' IS NULL OR core_attributes->>'admin_level_2' = '')
    """)

    # =========================================================================
    # Step 2: Drop indexes
    # =========================================================================

    op.drop_index("ix_entities_country_admin_levels", table_name="entities")
    op.drop_index("ix_entities_admin_level_2", table_name="entities")
    op.drop_index("ix_entities_admin_level_1", table_name="entities")
    op.drop_index("ix_entities_country", table_name="entities")

    # =========================================================================
    # Step 3: Drop columns
    # =========================================================================

    op.drop_column("entities", "admin_level_2")
    op.drop_column("entities", "admin_level_1")
    op.drop_column("entities", "country")
