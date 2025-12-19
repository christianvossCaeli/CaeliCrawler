"""Add crawler efficiency features

- Add last_modified_header and etag_header to data_sources for HTTP conditional requests
- Add FILTERED status to processing_status enum for skipped documents

Revision ID: e1234567893
Revises: d1234567892
Create Date: 2025-12-18 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e1234567893'
down_revision: Union[str, None] = 'd1234567892'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add HTTP conditional request headers to data_sources
    op.add_column('data_sources', sa.Column('last_modified_header', sa.String(255), nullable=True,
                                             comment='HTTP Last-Modified header from last crawl'))
    op.add_column('data_sources', sa.Column('etag_header', sa.String(255), nullable=True,
                                             comment='HTTP ETag header from last crawl'))

    # Add FILTERED status to processing_status enum
    # PostgreSQL requires special handling for adding enum values
    op.execute("ALTER TYPE processing_status ADD VALUE IF NOT EXISTS 'FILTERED'")


def downgrade() -> None:
    # Remove columns from data_sources
    op.drop_column('data_sources', 'etag_header')
    op.drop_column('data_sources', 'last_modified_header')

    # Note: PostgreSQL doesn't support removing enum values easily
    # The FILTERED value will remain in the enum but won't be used
