"""Add name_embedding column to entities for vector similarity search.

Revision ID: a1234567915
Revises: ax1234567939
Create Date: 2024-12-23 22:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a1234567915"
down_revision: Union[str, None] = "ax1234567939"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Add name_embedding column (1536 dimensions - reduced from 3072 for index support)
    # OpenAI text-embedding-3-large supports native dimension reduction
    op.execute("""
        ALTER TABLE entities
        ADD COLUMN name_embedding vector(1536)
    """)

    # Create HNSW index for cosine similarity search
    op.execute("""
        CREATE INDEX ix_entities_name_embedding
        ON entities
        USING hnsw (name_embedding vector_cosine_ops)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_entities_name_embedding")
    op.execute("ALTER TABLE entities DROP COLUMN IF EXISTS name_embedding")
    # Note: We don't drop the vector extension as other tables might use it
