"""Add full-text search to extracted_data.

Revision ID: be1234567946
Revises: z1234567914
Create Date: 2025-01-30

Adds PostgreSQL tsvector column and GIN index for efficient full-text search
across extracted content, human corrections, and entity references.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "be1234567946"
down_revision = "z1234567914"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add tsvector column for full-text search
    op.add_column(
        "extracted_data",
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            nullable=True,
            comment="Full-text search vector (auto-generated from extracted content)",
        ),
    )

    # Create GIN index for fast full-text search
    op.create_index(
        "ix_extracted_data_search_vector",
        "extracted_data",
        ["search_vector"],
        postgresql_using="gin",
    )

    # Create function to update search_vector
    op.execute("""
        CREATE OR REPLACE FUNCTION extracted_data_search_vector_update()
        RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector(
                'german',
                COALESCE(NEW.extracted_content::text, '') || ' ' ||
                COALESCE(NEW.human_corrections::text, '') || ' ' ||
                COALESCE(NEW.entity_references::text, '')
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger to automatically update search_vector
    op.execute("""
        CREATE TRIGGER extracted_data_search_vector_trigger
        BEFORE INSERT OR UPDATE OF extracted_content, human_corrections, entity_references
        ON extracted_data
        FOR EACH ROW
        EXECUTE FUNCTION extracted_data_search_vector_update();
    """)

    # Populate search_vector for existing rows
    op.execute("""
        UPDATE extracted_data
        SET search_vector = to_tsvector(
            'german',
            COALESCE(extracted_content::text, '') || ' ' ||
            COALESCE(human_corrections::text, '') || ' ' ||
            COALESCE(entity_references::text, '')
        )
        WHERE search_vector IS NULL;
    """)


def downgrade() -> None:
    # Drop trigger
    op.execute("""
        DROP TRIGGER IF EXISTS extracted_data_search_vector_trigger ON extracted_data;
    """)

    # Drop function
    op.execute("""
        DROP FUNCTION IF EXISTS extracted_data_search_vector_update();
    """)

    # Drop index
    op.drop_index("ix_extracted_data_search_vector", table_name="extracted_data")

    # Drop column
    op.drop_column("extracted_data", "search_vector")
