"""Add calendar widget type to summary_widget_type_enum.

Extends the widget type enum with 'calendar' for event/date-based visualizations
using Vue Cal to display temporal data in month/week/day/year views.

Revision ID: ay1234567940
Revises: ax1234567939
Create Date: 2024-12-24
"""

from typing import Sequence, Union

from alembic import op


revision: str = "ay1234567940"
down_revision: Union[str, None] = "ax1234567939"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'calendar' value to summary_widget_type_enum
    # IF NOT EXISTS prevents error if already added
    op.execute("""
        ALTER TYPE summary_widget_type_enum ADD VALUE IF NOT EXISTS 'calendar';
    """)


def downgrade() -> None:
    # Note: PostgreSQL does not support removing values from enums
    # The 'calendar' value will remain in the enum after downgrade
    # This is safe as unused enum values don't cause issues
    pass
