"""Add name_embedding columns to type tables for vector similarity search.

This enables efficient duplicate detection for EntityType, FacetType, Category,
and RelationType using semantic similarity instead of expensive per-request
embedding generation.

Revision ID: ba1234567942
Revises: az1234567941
Create Date: 2024-12-26 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "ba1234567942"
down_revision: Union[str, None] = "a1234567915"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure pgvector extension exists
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Add name_embedding to entity_types
    op.execute("""
        ALTER TABLE entity_types
        ADD COLUMN IF NOT EXISTS name_embedding vector(1536)
    """)

    # Add name_embedding to facet_types
    op.execute("""
        ALTER TABLE facet_types
        ADD COLUMN IF NOT EXISTS name_embedding vector(1536)
    """)

    # Add name_embedding to categories
    op.execute("""
        ALTER TABLE categories
        ADD COLUMN IF NOT EXISTS name_embedding vector(1536)
    """)

    # Add name_embedding to relation_types
    op.execute("""
        ALTER TABLE relation_types
        ADD COLUMN IF NOT EXISTS name_embedding vector(1536)
    """)

    # Create HNSW indexes for cosine similarity search
    # These indexes are small (typically < 100 rows per table) so HNSW is efficient
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_entity_types_name_embedding
        ON entity_types
        USING hnsw (name_embedding vector_cosine_ops)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_facet_types_name_embedding
        ON facet_types
        USING hnsw (name_embedding vector_cosine_ops)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_categories_name_embedding
        ON categories
        USING hnsw (name_embedding vector_cosine_ops)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_relation_types_name_embedding
        ON relation_types
        USING hnsw (name_embedding vector_cosine_ops)
    """)


def downgrade() -> None:
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS ix_entity_types_name_embedding")
    op.execute("DROP INDEX IF EXISTS ix_facet_types_name_embedding")
    op.execute("DROP INDEX IF EXISTS ix_categories_name_embedding")
    op.execute("DROP INDEX IF EXISTS ix_relation_types_name_embedding")

    # Drop columns
    op.execute("ALTER TABLE entity_types DROP COLUMN IF EXISTS name_embedding")
    op.execute("ALTER TABLE facet_types DROP COLUMN IF EXISTS name_embedding")
    op.execute("ALTER TABLE categories DROP COLUMN IF EXISTS name_embedding")
    op.execute("ALTER TABLE relation_types DROP COLUMN IF EXISTS name_embedding")
