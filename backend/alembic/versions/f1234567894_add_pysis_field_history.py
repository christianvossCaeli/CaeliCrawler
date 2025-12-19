"""Add PySis field history table

Tracks all changes to field values for auditing and undo functionality.

Revision ID: f1234567894
Revises: e1234567893
Create Date: 2025-12-18 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = 'f1234567894'
down_revision: Union[str, None] = 'e1234567893'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use raw SQL to create table with existing enum type
    op.execute("""
        CREATE TABLE pysis_field_history (
            id UUID PRIMARY KEY,
            field_id UUID NOT NULL REFERENCES pysis_process_fields(id) ON DELETE CASCADE,
            value TEXT,
            source pysis_value_source NOT NULL,
            confidence_score FLOAT,
            action VARCHAR(50) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
        )
    """)
    op.execute("CREATE INDEX ix_pysis_field_history_field_id ON pysis_field_history(field_id)")


def downgrade() -> None:
    op.drop_table('pysis_field_history')
