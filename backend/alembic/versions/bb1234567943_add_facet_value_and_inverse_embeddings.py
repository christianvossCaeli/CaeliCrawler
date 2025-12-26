"""Add text_embedding to facet_values and name_inverse_embedding to relation_types.

This enables:
- Semantic duplicate detection for FacetValues using stored embeddings
- Bidirectional similarity search for RelationTypes (name + name_inverse)

Revision ID: bb1234567943
Revises: ba1234567942
Create Date: 2024-12-26 15:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "bb1234567943"
down_revision: Union[str, None] = "ba1234567942"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure pgvector extension exists
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Add text_embedding to facet_values
    op.execute("""
        ALTER TABLE facet_values
        ADD COLUMN IF NOT EXISTS text_embedding vector(1536)
    """)

    # Add name_inverse_embedding to relation_types
    op.execute("""
        ALTER TABLE relation_types
        ADD COLUMN IF NOT EXISTS name_inverse_embedding vector(1536)
    """)

    # Create HNSW index for facet_values text_embedding
    # Using entity_id + facet_type_id partial index would be ideal but HNSW doesn't support it
    # So we create a standard HNSW index
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_facet_values_text_embedding
        ON facet_values
        USING hnsw (text_embedding vector_cosine_ops)
    """)

    # Create HNSW index for relation_types name_inverse_embedding
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_relation_types_name_inverse_embedding
        ON relation_types
        USING hnsw (name_inverse_embedding vector_cosine_ops)
    """)


def downgrade() -> None:
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS ix_facet_values_text_embedding")
    op.execute("DROP INDEX IF EXISTS ix_relation_types_name_inverse_embedding")

    # Drop columns
    op.execute("ALTER TABLE facet_values DROP COLUMN IF EXISTS text_embedding")
    op.execute("ALTER TABLE relation_types DROP COLUMN IF EXISTS name_inverse_embedding")
