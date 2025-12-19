"""Delete all PySis field templates.

This migration removes all existing field templates from the database
as the feature is being disabled via feature flag.

Revision ID: v1234567910
Revises: u1234567909
Create Date: 2024-12-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "v1234567910"
down_revision: Union[str, None] = "u1234567909"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Delete all field templates
    # First, remove template references from processes
    op.execute(sa.text("""
        UPDATE pysis_processes SET template_id = NULL WHERE template_id IS NOT NULL
    """))

    # Then delete all templates
    op.execute(sa.text("""
        DELETE FROM pysis_field_templates
    """))


def downgrade() -> None:
    # Templates cannot be restored - they would need to be recreated manually
    pass
