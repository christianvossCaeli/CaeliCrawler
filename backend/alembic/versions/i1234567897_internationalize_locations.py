"""Internationalize locations - rename municipalities to locations with country support.

Revision ID: i1234567897
Revises: h1234567896
Create Date: 2024-12-18

This migration transforms the Germany-specific municipality system into
an international location system supporting multiple countries.

Changes:
- Rename municipalities table to locations
- Add country field (ISO 3166-1 alpha-2)
- Generalize field names (ags -> official_code, state -> admin_level_1, etc.)
- Update related tables (data_sources, pysis_processes)
- Migrate existing German data with country='DE'
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "i1234567897"
down_revision: Union[str, None] = "h1234567896"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================
    # STEP 1: Update municipalities table
    # =========================================

    # Add new columns
    op.add_column(
        "municipalities",
        sa.Column("country", sa.String(2), nullable=True, index=True,
                  comment="ISO 3166-1 alpha-2 country code"),
    )
    op.add_column(
        "municipalities",
        sa.Column("locality_type", sa.String(50), nullable=True,
                  comment="Type of locality (municipality, city, town, parish, etc.)"),
    )
    op.add_column(
        "municipalities",
        sa.Column("country_metadata", postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default="{}",
                  comment="Country-specific metadata"),
    )

    # Migrate existing German data
    op.execute("UPDATE municipalities SET country = 'DE' WHERE country IS NULL")

    # Migrate rs to country_metadata for German records
    op.execute("""
        UPDATE municipalities
        SET country_metadata = jsonb_build_object('rs', rs)
        WHERE rs IS NOT NULL AND country = 'DE'
    """)

    # Set locality_type for existing records
    op.execute("UPDATE municipalities SET locality_type = 'municipality' WHERE locality_type IS NULL")

    # Make country NOT NULL after migration
    op.alter_column("municipalities", "country", nullable=False)

    # Drop old indexes BEFORE renaming columns (indexes reference old column names)
    op.drop_index("ix_municipalities_ags", table_name="municipalities")
    op.drop_constraint("uq_municipalities_rs", "municipalities", type_="unique")

    # Rename columns
    op.alter_column("municipalities", "ags", new_column_name="official_code")
    op.alter_column("municipalities", "state", new_column_name="admin_level_1")
    op.alter_column("municipalities", "district", new_column_name="admin_level_2")

    # Drop rs column (now in country_metadata)
    op.drop_column("municipalities", "rs")

    # Expand official_code size (from 8 to 50 chars for international codes)
    op.alter_column("municipalities", "official_code",
                    type_=sa.String(50), existing_type=sa.String(8))

    # Create new composite index
    op.create_index(
        "ix_locations_country_official_code",
        "municipalities",
        ["country", "official_code"],
        unique=True,
        postgresql_where=sa.text("official_code IS NOT NULL"),
    )
    op.create_index(
        "ix_locations_country_admin_level_1",
        "municipalities",
        ["country", "admin_level_1"],
    )

    # Rename table
    op.rename_table("municipalities", "locations")

    # =========================================
    # STEP 2: Update data_sources table
    # =========================================

    # Add country column
    op.add_column(
        "data_sources",
        sa.Column("country", sa.String(2), nullable=True, index=True,
                  comment="ISO 3166-1 alpha-2 country code"),
    )

    # Set country for existing records
    op.execute("UPDATE data_sources SET country = 'DE' WHERE country IS NULL")

    # Drop old indexes and foreign key BEFORE renaming columns
    op.drop_constraint("fk_data_sources_municipality_id", "data_sources", type_="foreignkey")
    op.drop_index("ix_data_sources_municipality_id", table_name="data_sources")
    op.drop_index("ix_data_sources_municipality", table_name="data_sources")
    op.drop_index("ix_data_sources_bundesland", table_name="data_sources")

    # Rename columns
    op.alter_column("data_sources", "municipality_id", new_column_name="location_id")
    op.alter_column("data_sources", "municipality", new_column_name="location_name")
    op.alter_column("data_sources", "bundesland", new_column_name="admin_level_1")

    # Create new foreign key and indexes
    op.create_foreign_key(
        "data_sources_location_id_fkey",
        "data_sources",
        "locations",
        ["location_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_data_sources_location_id", "data_sources", ["location_id"])
    op.create_index("ix_data_sources_location_name", "data_sources", ["location_name"])
    op.create_index("ix_data_sources_admin_level_1", "data_sources", ["admin_level_1"])

    # =========================================
    # STEP 3: Update pysis_processes table
    # =========================================

    # Drop old constraints and indexes BEFORE renaming columns
    op.drop_constraint("fk_pysis_processes_municipality_id", "pysis_processes", type_="foreignkey")
    op.drop_constraint("uq_municipality_pysis_process", "pysis_processes", type_="unique")
    op.drop_index("ix_pysis_processes_municipality_id", table_name="pysis_processes")
    op.drop_index("ix_pysis_processes_municipality", table_name="pysis_processes")

    # Rename columns
    op.alter_column("pysis_processes", "municipality_id", new_column_name="location_id")
    op.alter_column("pysis_processes", "municipality", new_column_name="location_name")

    # Create new constraints and indexes
    op.create_unique_constraint(
        "uq_location_pysis_process",
        "pysis_processes",
        ["location_name", "pysis_process_id"],
    )
    op.create_foreign_key(
        "pysis_processes_location_id_fkey",
        "pysis_processes",
        "locations",
        ["location_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_pysis_processes_location_id", "pysis_processes", ["location_id"])
    op.create_index("ix_pysis_processes_location_name", "pysis_processes", ["location_name"])


def downgrade() -> None:
    # =========================================
    # Reverse STEP 3: pysis_processes
    # =========================================
    op.drop_index("ix_pysis_processes_location_name", table_name="pysis_processes")
    op.create_index("ix_pysis_processes_municipality", "pysis_processes", ["location_name"])

    op.drop_index("ix_pysis_processes_location_id", table_name="pysis_processes")
    op.create_index("ix_pysis_processes_municipality_id", "pysis_processes", ["location_id"])

    op.drop_constraint("pysis_processes_location_id_fkey", "pysis_processes", type_="foreignkey")
    op.create_foreign_key(
        "pysis_processes_municipality_id_fkey",
        "pysis_processes",
        "locations",  # Note: will be renamed back
        ["location_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("uq_location_pysis_process", "pysis_processes", type_="unique")
    op.create_unique_constraint(
        "uq_municipality_pysis_process",
        "pysis_processes",
        ["location_name", "pysis_process_id"],
    )

    op.alter_column("pysis_processes", "location_name", new_column_name="municipality")
    op.alter_column("pysis_processes", "location_id", new_column_name="municipality_id")

    # =========================================
    # Reverse STEP 2: data_sources
    # =========================================
    op.drop_index("ix_data_sources_admin_level_1", table_name="data_sources")
    op.create_index("ix_data_sources_bundesland", "data_sources", ["admin_level_1"])

    op.drop_index("ix_data_sources_location_name", table_name="data_sources")
    op.create_index("ix_data_sources_municipality", "data_sources", ["location_name"])

    op.drop_index("ix_data_sources_location_id", table_name="data_sources")
    op.create_index("ix_data_sources_municipality_id", "data_sources", ["location_id"])

    op.drop_constraint("data_sources_location_id_fkey", "data_sources", type_="foreignkey")
    op.create_foreign_key(
        "data_sources_municipality_id_fkey",
        "data_sources",
        "locations",  # Note: will be renamed back
        ["location_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.alter_column("data_sources", "admin_level_1", new_column_name="bundesland")
    op.alter_column("data_sources", "location_name", new_column_name="municipality")
    op.alter_column("data_sources", "location_id", new_column_name="municipality_id")

    op.drop_column("data_sources", "country")

    # =========================================
    # Reverse STEP 1: locations -> municipalities
    # =========================================
    op.rename_table("locations", "municipalities")

    op.drop_index("ix_locations_country_admin_level_1", table_name="municipalities")
    op.drop_index("ix_locations_country_official_code", table_name="municipalities")

    # Re-add rs column
    op.add_column(
        "municipalities",
        sa.Column("rs", sa.String(12), nullable=True, unique=True,
                  comment="Regionalschlüssel (12-stellig)"),
    )

    # Restore rs from country_metadata
    op.execute("""
        UPDATE municipalities
        SET rs = country_metadata->>'rs'
        WHERE country_metadata->>'rs' IS NOT NULL
    """)

    # Rename columns back
    op.alter_column("municipalities", "admin_level_2", new_column_name="district")
    op.alter_column("municipalities", "admin_level_1", new_column_name="state")
    op.alter_column("municipalities", "official_code",
                    type_=sa.String(8), existing_type=sa.String(50))
    op.alter_column("municipalities", "official_code", new_column_name="ags")

    # Recreate original unique constraint
    op.create_unique_constraint("municipalities_ags_key", "municipalities", ["ags"])

    # Drop new columns
    op.drop_column("municipalities", "country_metadata")
    op.drop_column("municipalities", "locality_type")
    op.drop_column("municipalities", "country")

    # Update foreign keys to point back to municipalities table
    op.drop_constraint("pysis_processes_municipality_id_fkey", "pysis_processes", type_="foreignkey")
    op.create_foreign_key(
        "pysis_processes_municipality_id_fkey",
        "pysis_processes",
        "municipalities",
        ["municipality_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("data_sources_municipality_id_fkey", "data_sources", type_="foreignkey")
    op.create_foreign_key(
        "data_sources_municipality_id_fkey",
        "data_sources",
        "municipalities",
        ["municipality_id"],
        ["id"],
        ondelete="SET NULL",
    )
