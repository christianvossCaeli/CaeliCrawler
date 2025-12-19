"""Add URL filter patterns to categories.

Revision ID: h1234567896
Revises: g1234567895_add_ai_tasks
Create Date: 2024-12-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "h1234567896"
down_revision: Union[str, None] = "g1234567895"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add URL filter patterns to categories
    op.add_column(
        "categories",
        sa.Column(
            "url_include_patterns",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
            comment="Regex patterns - URLs must match at least one (if set)",
        ),
    )
    op.add_column(
        "categories",
        sa.Column(
            "url_exclude_patterns",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
            comment="Regex patterns - URLs matching any will be skipped",
        ),
    )

    # Pre-populate "Ratsinformationen NRW" category with sensible URL filters
    op.execute("""
        UPDATE categories
        SET
            url_include_patterns = '["/(rat|politik|sitzung|ausschuss|buerger|gremien|beschluss|vorlage|antrag|niederschrift|protokoll|tagesordnung)/"]'::jsonb,
            url_exclude_patterns = '["/(impressum|datenschutz|kontakt|suche|login|archiv|2[0-1][0-9]{2}/|/en/|/fr/)/"]'::jsonb
        WHERE slug = 'ratsinformationen-nrw'
    """)


def downgrade() -> None:
    op.drop_column("categories", "url_exclude_patterns")
    op.drop_column("categories", "url_include_patterns")
