"""Add aliases column to entity_types table.

Adds multilingual alias support for entity types, allowing
automatic deduplication when creating new entity types with
alternative names (e.g., "Ort" -> "territorial_entity").

Revision ID: bi1234567950
Revises: bh1234567949
Create Date: 2025-12-30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

# revision identifiers, used by Alembic.
revision = "bi1234567950"
down_revision = "bh1234567949"
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # Skip if column already exists (idempotent)
    if column_exists("entity_types", "aliases"):
        return

    # Add aliases column
    op.add_column(
        "entity_types",
        sa.Column(
            "aliases",
            ARRAY(sa.String(100)),
            nullable=False,
            server_default="{}",
            comment="Alternative names for this entity type (multilingual, lowercase)",
        ),
    )

    # Populate aliases for territorial_entity with common location terms
    op.execute("""
        UPDATE entity_types SET aliases = ARRAY[
            'ort', 'orte', 'location', 'locations', 'standort', 'standorte',
            'stadt', 'städte', 'city', 'cities', 'kommune', 'kommunen',
            'gemeinde', 'gemeinden', 'municipality', 'municipalities',
            'region', 'regionen', 'regions', 'gebiet', 'gebiete',
            'lieu', 'lieux', 'place', 'places', 'ubicación', 'ubicaciones',
            'territorio', 'territorios', 'localidad', 'localidades'
        ] WHERE slug = 'territorial_entity'
    """)

    # Add GIN index for efficient array containment queries
    op.create_index(
        "ix_entity_types_aliases",
        "entity_types",
        ["aliases"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_entity_types_aliases", table_name="entity_types")
    op.drop_column("entity_types", "aliases")
