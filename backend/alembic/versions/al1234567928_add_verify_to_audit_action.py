"""Add VERIFY to audit_action enum

Revision ID: al1234567928
Revises: ak1234567927
Create Date: 2025-12-21

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'al1234567928'
down_revision = 'ak1234567927'
branch_labels = None
depends_on = None


def upgrade():
    # Add VERIFY value to audit_action enum
    op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'VERIFY'")


def downgrade():
    # PostgreSQL doesn't support removing enum values easily
    # This would require recreating the enum type
    pass
