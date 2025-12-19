"""Add ownership and visibility fields to EntityType and Category.

This migration adds user ownership and visibility control to EntityType and Category
models, enabling user-specific entity types and categories that are private by default.

Changes to entity_types:
- Add created_by_id (FK to users)
- Add owner_id (FK to users)
- Add is_public (default False for new, True for existing system types)

Changes to categories:
- Add created_by_id (FK to users)
- Add owner_id (FK to users)
- Add is_public (default False for new, True for existing)
- Add target_entity_type_id (FK to entity_types)

Revision ID: n1234567902
Revises: m1234567901
Create Date: 2024-12-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "n1234567902"
down_revision: Union[str, None] = "m1234567901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = :table_name AND column_name = :column_name
            )
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    )
    return result.scalar()


def index_exists(index_name: str) -> bool:
    """Check if an index exists."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1 FROM pg_indexes WHERE indexname = :index_name
            )
            """
        ),
        {"index_name": index_name},
    )
    return result.scalar()


def constraint_exists(constraint_name: str) -> bool:
    """Check if a constraint exists."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = :constraint_name
            )
            """
        ),
        {"constraint_name": constraint_name},
    )
    return result.scalar()


def upgrade() -> None:
    # =========================================================================
    # Step 1: Add ownership columns to entity_types
    # =========================================================================

    if not column_exists("entity_types", "created_by_id"):
        op.add_column(
            "entity_types",
            sa.Column(
                "created_by_id",
                UUID(as_uuid=True),
                nullable=True,
                comment="User who created this entity type",
            ),
        )

    if not column_exists("entity_types", "owner_id"):
        op.add_column(
            "entity_types",
            sa.Column(
                "owner_id",
                UUID(as_uuid=True),
                nullable=True,
                comment="User who owns this entity type",
            ),
        )

    if not column_exists("entity_types", "is_public"):
        op.add_column(
            "entity_types",
            sa.Column(
                "is_public",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
                comment="If true, visible to all users. If false, only visible to owner.",
            ),
        )

    # Create foreign keys for entity_types
    if not constraint_exists("fk_entity_types_created_by_id_users"):
        op.create_foreign_key(
            "fk_entity_types_created_by_id_users",
            "entity_types",
            "users",
            ["created_by_id"],
            ["id"],
            ondelete="SET NULL",
        )

    if not constraint_exists("fk_entity_types_owner_id_users"):
        op.create_foreign_key(
            "fk_entity_types_owner_id_users",
            "entity_types",
            "users",
            ["owner_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # Create indexes for entity_types
    if not index_exists("ix_entity_types_created_by_id"):
        op.create_index("ix_entity_types_created_by_id", "entity_types", ["created_by_id"])

    if not index_exists("ix_entity_types_owner_id"):
        op.create_index("ix_entity_types_owner_id", "entity_types", ["owner_id"])

    if not index_exists("ix_entity_types_is_public"):
        op.create_index("ix_entity_types_is_public", "entity_types", ["is_public"])

    # =========================================================================
    # Step 2: Add ownership columns to categories
    # =========================================================================

    if not column_exists("categories", "created_by_id"):
        op.add_column(
            "categories",
            sa.Column(
                "created_by_id",
                UUID(as_uuid=True),
                nullable=True,
                comment="User who created this category",
            ),
        )

    if not column_exists("categories", "owner_id"):
        op.add_column(
            "categories",
            sa.Column(
                "owner_id",
                UUID(as_uuid=True),
                nullable=True,
                comment="User who owns this category",
            ),
        )

    if not column_exists("categories", "is_public"):
        op.add_column(
            "categories",
            sa.Column(
                "is_public",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
                comment="If true, visible to all users. If false, only visible to owner.",
            ),
        )

    if not column_exists("categories", "target_entity_type_id"):
        op.add_column(
            "categories",
            sa.Column(
                "target_entity_type_id",
                UUID(as_uuid=True),
                nullable=True,
                comment="EntityType for extracted entities (e.g., 'event-besuche-nrw')",
            ),
        )

    # Create foreign keys for categories
    if not constraint_exists("fk_categories_created_by_id_users"):
        op.create_foreign_key(
            "fk_categories_created_by_id_users",
            "categories",
            "users",
            ["created_by_id"],
            ["id"],
            ondelete="SET NULL",
        )

    if not constraint_exists("fk_categories_owner_id_users"):
        op.create_foreign_key(
            "fk_categories_owner_id_users",
            "categories",
            "users",
            ["owner_id"],
            ["id"],
            ondelete="SET NULL",
        )

    if not constraint_exists("fk_categories_target_entity_type_id"):
        op.create_foreign_key(
            "fk_categories_target_entity_type_id",
            "categories",
            "entity_types",
            ["target_entity_type_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # Create indexes for categories
    if not index_exists("ix_categories_created_by_id"):
        op.create_index("ix_categories_created_by_id", "categories", ["created_by_id"])

    if not index_exists("ix_categories_owner_id"):
        op.create_index("ix_categories_owner_id", "categories", ["owner_id"])

    if not index_exists("ix_categories_is_public"):
        op.create_index("ix_categories_is_public", "categories", ["is_public"])

    if not index_exists("ix_categories_target_entity_type_id"):
        op.create_index("ix_categories_target_entity_type_id", "categories", ["target_entity_type_id"])

    # =========================================================================
    # Step 3: Set existing records to public
    # =========================================================================

    # All existing system entity types should be public
    op.execute("UPDATE entity_types SET is_public = TRUE WHERE is_system = TRUE")

    # All existing entity types (including non-system) should be public for backwards compatibility
    op.execute("UPDATE entity_types SET is_public = TRUE")

    # All existing categories should be public for backwards compatibility
    op.execute("UPDATE categories SET is_public = TRUE")


def downgrade() -> None:
    # =========================================================================
    # Step 1: Drop indexes from categories
    # =========================================================================

    if index_exists("ix_categories_target_entity_type_id"):
        op.drop_index("ix_categories_target_entity_type_id", table_name="categories")

    if index_exists("ix_categories_is_public"):
        op.drop_index("ix_categories_is_public", table_name="categories")

    if index_exists("ix_categories_owner_id"):
        op.drop_index("ix_categories_owner_id", table_name="categories")

    if index_exists("ix_categories_created_by_id"):
        op.drop_index("ix_categories_created_by_id", table_name="categories")

    # =========================================================================
    # Step 2: Drop foreign keys from categories
    # =========================================================================

    if constraint_exists("fk_categories_target_entity_type_id"):
        op.drop_constraint("fk_categories_target_entity_type_id", "categories", type_="foreignkey")

    if constraint_exists("fk_categories_owner_id_users"):
        op.drop_constraint("fk_categories_owner_id_users", "categories", type_="foreignkey")

    if constraint_exists("fk_categories_created_by_id_users"):
        op.drop_constraint("fk_categories_created_by_id_users", "categories", type_="foreignkey")

    # =========================================================================
    # Step 3: Drop columns from categories
    # =========================================================================

    if column_exists("categories", "target_entity_type_id"):
        op.drop_column("categories", "target_entity_type_id")

    if column_exists("categories", "is_public"):
        op.drop_column("categories", "is_public")

    if column_exists("categories", "owner_id"):
        op.drop_column("categories", "owner_id")

    if column_exists("categories", "created_by_id"):
        op.drop_column("categories", "created_by_id")

    # =========================================================================
    # Step 4: Drop indexes from entity_types
    # =========================================================================

    if index_exists("ix_entity_types_is_public"):
        op.drop_index("ix_entity_types_is_public", table_name="entity_types")

    if index_exists("ix_entity_types_owner_id"):
        op.drop_index("ix_entity_types_owner_id", table_name="entity_types")

    if index_exists("ix_entity_types_created_by_id"):
        op.drop_index("ix_entity_types_created_by_id", table_name="entity_types")

    # =========================================================================
    # Step 5: Drop foreign keys from entity_types
    # =========================================================================

    if constraint_exists("fk_entity_types_owner_id_users"):
        op.drop_constraint("fk_entity_types_owner_id_users", "entity_types", type_="foreignkey")

    if constraint_exists("fk_entity_types_created_by_id_users"):
        op.drop_constraint("fk_entity_types_created_by_id_users", "entity_types", type_="foreignkey")

    # =========================================================================
    # Step 6: Drop columns from entity_types
    # =========================================================================

    if column_exists("entity_types", "is_public"):
        op.drop_column("entity_types", "is_public")

    if column_exists("entity_types", "owner_id"):
        op.drop_column("entity_types", "owner_id")

    if column_exists("entity_types", "created_by_id"):
        op.drop_column("entity_types", "created_by_id")
