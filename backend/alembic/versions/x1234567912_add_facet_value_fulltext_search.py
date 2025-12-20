"""Add full-text search to facet_values.

Revision ID: x1234567912
Revises: w1234567911
Create Date: 2025-01-20

Adds PostgreSQL tsvector column and GIN index for efficient full-text search
on facet_values.text_representation field.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "x1234567912"
down_revision = "w1234567911"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add tsvector column for full-text search
    op.add_column(
        "facet_values",
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            nullable=True,
            comment="Full-text search vector (auto-generated from text_representation)",
        ),
    )

    # Create GIN index for fast full-text search
    op.create_index(
        "ix_facet_values_search_vector",
        "facet_values",
        ["search_vector"],
        postgresql_using="gin",
    )

    # Create function to update search_vector
    op.execute("""
        CREATE OR REPLACE FUNCTION facet_values_search_vector_update()
        RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector('german', COALESCE(NEW.text_representation, ''));
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger to automatically update search_vector
    op.execute("""
        CREATE TRIGGER facet_values_search_vector_trigger
        BEFORE INSERT OR UPDATE OF text_representation
        ON facet_values
        FOR EACH ROW
        EXECUTE FUNCTION facet_values_search_vector_update();
    """)

    # Populate search_vector for existing rows
    op.execute("""
        UPDATE facet_values
        SET search_vector = to_tsvector('german', COALESCE(text_representation, ''))
        WHERE search_vector IS NULL;
    """)


def downgrade() -> None:
    # Drop trigger
    op.execute("""
        DROP TRIGGER IF EXISTS facet_values_search_vector_trigger ON facet_values;
    """)

    # Drop function
    op.execute("""
        DROP FUNCTION IF EXISTS facet_values_search_vector_update();
    """)

    # Drop index
    op.drop_index("ix_facet_values_search_vector", table_name="facet_values")

    # Drop column
    op.drop_column("facet_values", "search_vector")
