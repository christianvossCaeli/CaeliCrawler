"""Remove entity and location fields from data_sources.

DataSources are now decoupled from Entities. The relationship is:
DataSource -> Category -> AI Analysis -> Entity + FacetValues

Traceability remains via: Entity.facet_values -> Document -> DataSource

Revision ID: af1234567921
Revises: ae1234567920
Create Date: 2024-12-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "af1234567921"
down_revision: Union[str, None] = "ae1234567920"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop foreign key constraints first (using actual constraint names from database)
    op.drop_constraint(
        "fk_data_sources_entity_id_entities", "data_sources", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_data_sources_location_id_locations", "data_sources", type_="foreignkey"
    )

    # Drop indexes
    op.drop_index("ix_data_sources_entity_id", table_name="data_sources")
    op.drop_index("ix_data_sources_location_id", table_name="data_sources")
    op.drop_index("ix_data_sources_country", table_name="data_sources")
    op.drop_index("ix_data_sources_location_name", table_name="data_sources")
    op.drop_index("ix_data_sources_region", table_name="data_sources")
    op.drop_index("ix_data_sources_admin_level_1", table_name="data_sources")

    # Drop columns
    op.drop_column("data_sources", "entity_id")
    op.drop_column("data_sources", "location_id")
    op.drop_column("data_sources", "country")
    op.drop_column("data_sources", "location_name")
    op.drop_column("data_sources", "region")
    op.drop_column("data_sources", "admin_level_1")


def downgrade() -> None:
    # Re-add columns
    op.add_column(
        "data_sources",
        sa.Column(
            "admin_level_1",
            sa.String(100),
            nullable=True,
            comment="State/Region/Bundesland (e.g., 'Nordrhein-Westfalen')",
        ),
    )
    op.add_column(
        "data_sources",
        sa.Column(
            "region",
            sa.String(255),
            nullable=True,
            comment="Region for broader clustering (e.g., 'Münsterland')",
        ),
    )
    op.add_column(
        "data_sources",
        sa.Column(
            "location_name",
            sa.String(255),
            nullable=True,
            comment="Location name for result clustering (e.g., 'Münster')",
        ),
    )
    op.add_column(
        "data_sources",
        sa.Column(
            "country",
            sa.String(2),
            nullable=True,
            comment="ISO 3166-1 alpha-2 country code",
        ),
    )
    op.add_column(
        "data_sources",
        sa.Column(
            "location_id",
            UUID(as_uuid=True),
            nullable=True,
            comment="FK to location for geographic clustering",
        ),
    )
    op.add_column(
        "data_sources",
        sa.Column(
            "entity_id",
            UUID(as_uuid=True),
            nullable=True,
            comment="FK to entity (municipality/person/organization/event)",
        ),
    )

    # Re-add indexes
    op.create_index("ix_data_sources_admin_level_1", "data_sources", ["admin_level_1"])
    op.create_index("ix_data_sources_region", "data_sources", ["region"])
    op.create_index("ix_data_sources_location_name", "data_sources", ["location_name"])
    op.create_index("ix_data_sources_country", "data_sources", ["country"])
    op.create_index("ix_data_sources_location_id", "data_sources", ["location_id"])
    op.create_index("ix_data_sources_entity_id", "data_sources", ["entity_id"])

    # Re-add foreign key constraints
    op.create_foreign_key(
        "data_sources_location_id_fkey",
        "data_sources",
        "locations",
        ["location_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "data_sources_entity_id_fkey",
        "data_sources",
        "entities",
        ["entity_id"],
        ["id"],
        ondelete="SET NULL",
    )
