"""Add new audit_action enum values: FAVORITE_ADD, FAVORITE_REMOVE, SMART_QUERY, CONFIG_UPDATE

Revision ID: zi1234567923
Revises: zh1234567922
Create Date: 2026-01-05

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'zi1234567923'
down_revision = 'zh1234567922'
branch_labels = None
depends_on = None


def upgrade():
    # Add new audit_action enum values
    op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'FAVORITE_ADD'")
    op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'FAVORITE_REMOVE'")
    op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'SMART_QUERY'")
    op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'CONFIG_UPDATE'")


def downgrade():
    # PostgreSQL doesn't support removing enum values easily
    # This would require recreating the enum type
    pass
