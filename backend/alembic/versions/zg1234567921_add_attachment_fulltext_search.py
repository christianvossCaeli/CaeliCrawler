"""Add full-text search to entity_attachments.

Revision ID: zg1234567921
Revises: zf1234567920
Create Date: 2026-01-05

Adds PostgreSQL tsvector column and GIN index for efficient full-text search
on entity_attachments. Indexes filename, description, and analysis_result content.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "zg1234567921"
down_revision = "zf1234567920"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add tsvector column for full-text search
    op.add_column(
        "entity_attachments",
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            nullable=True,
            comment="Full-text search vector for filename, description, and analysis content",
        ),
    )

    # Create GIN index for fast full-text search
    op.create_index(
        "ix_entity_attachments_search_vector",
        "entity_attachments",
        ["search_vector"],
        postgresql_using="gin",
    )

    # Create function to update search_vector from multiple fields
    # Combines: filename, description, analysis_result->>'description', analysis_result->>'extracted_text'
    # Also includes detected_text array if present
    op.execute("""
        CREATE OR REPLACE FUNCTION entity_attachments_search_vector_update()
        RETURNS trigger AS $$
        DECLARE
            detected_text_str TEXT := '';
            detected_item TEXT;
        BEGIN
            -- Build string from detected_text array if it exists
            IF NEW.analysis_result ? 'detected_text' AND
               jsonb_typeof(NEW.analysis_result->'detected_text') = 'array' THEN
                FOR detected_item IN SELECT jsonb_array_elements_text(NEW.analysis_result->'detected_text')
                LOOP
                    detected_text_str := detected_text_str || ' ' || detected_item;
                END LOOP;
            END IF;

            NEW.search_vector := to_tsvector(
                'german',
                COALESCE(NEW.filename, '') || ' ' ||
                COALESCE(NEW.description, '') || ' ' ||
                COALESCE(NEW.analysis_result->>'description', '') || ' ' ||
                COALESCE(NEW.analysis_result->>'document_type', '') || ' ' ||
                COALESCE(detected_text_str, '')
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger to automatically update search_vector
    op.execute("""
        CREATE TRIGGER entity_attachments_search_vector_trigger
        BEFORE INSERT OR UPDATE OF filename, description, analysis_result
        ON entity_attachments
        FOR EACH ROW
        EXECUTE FUNCTION entity_attachments_search_vector_update();
    """)

    # Populate search_vector for existing rows
    # This handles both the simple case and detected_text array
    op.execute("""
        UPDATE entity_attachments
        SET search_vector = to_tsvector(
            'german',
            COALESCE(filename, '') || ' ' ||
            COALESCE(description, '') || ' ' ||
            COALESCE(analysis_result->>'description', '') || ' ' ||
            COALESCE(analysis_result->>'document_type', '') || ' ' ||
            COALESCE(
                (SELECT string_agg(elem::text, ' ')
                 FROM jsonb_array_elements_text(
                     CASE
                         WHEN analysis_result ? 'detected_text'
                              AND jsonb_typeof(analysis_result->'detected_text') = 'array'
                         THEN analysis_result->'detected_text'
                         ELSE '[]'::jsonb
                     END
                 ) AS elem),
                ''
            )
        )
        WHERE search_vector IS NULL;
    """)


def downgrade() -> None:
    # Drop trigger
    op.execute("""
        DROP TRIGGER IF EXISTS entity_attachments_search_vector_trigger ON entity_attachments;
    """)

    # Drop function
    op.execute("""
        DROP FUNCTION IF EXISTS entity_attachments_search_vector_update();
    """)

    # Drop index
    op.drop_index("ix_entity_attachments_search_vector", table_name="entity_attachments")

    # Drop column
    op.drop_column("entity_attachments", "search_vector")
