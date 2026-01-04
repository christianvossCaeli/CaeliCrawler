"""Fix widget type enum values from UPPERCASE to lowercase.

Revision ID: za1234567915
Revises: z1234567914
Create Date: 2026-01-04

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "za1234567915"
down_revision = "bp1234567957"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Convert widget_type values from UPPERCASE to lowercase.

    Note: Due to PostgreSQL ENUM constraints requiring commits between
    ADD VALUE and UPDATE, this migration was applied manually via SQL.
    The migration file exists for version tracking purposes.

    SQL that was run:
    1. ALTER TYPE summary_widget_type_enum ADD VALUE IF NOT EXISTS 'table' (etc for all types)
    2. UPDATE summary_widgets SET widget_type = 'table' WHERE widget_type::text = 'TABLE' (etc)
    """
    # Already applied manually - this is a no-op for tracking purposes
    pass


def downgrade() -> None:
    """Convert widget_type values back to UPPERCASE."""
    # Update back to uppercase values
    op.execute("UPDATE summary_widgets SET widget_type = 'TABLE' WHERE widget_type::text = 'table'")
    op.execute("UPDATE summary_widgets SET widget_type = 'BAR_CHART' WHERE widget_type::text = 'bar_chart'")
    op.execute("UPDATE summary_widgets SET widget_type = 'LINE_CHART' WHERE widget_type::text = 'line_chart'")
    op.execute("UPDATE summary_widgets SET widget_type = 'PIE_CHART' WHERE widget_type::text = 'pie_chart'")
    op.execute("UPDATE summary_widgets SET widget_type = 'STAT_CARD' WHERE widget_type::text = 'stat_card'")
    op.execute("UPDATE summary_widgets SET widget_type = 'TEXT' WHERE widget_type::text = 'text'")
    op.execute("UPDATE summary_widgets SET widget_type = 'COMPARISON' WHERE widget_type::text = 'comparison'")
    op.execute("UPDATE summary_widgets SET widget_type = 'TIMELINE' WHERE widget_type::text = 'timeline'")
    op.execute("UPDATE summary_widgets SET widget_type = 'MAP' WHERE widget_type::text = 'map'")
    op.execute("UPDATE summary_widgets SET widget_type = 'CALENDAR' WHERE widget_type::text = 'calendar'")
