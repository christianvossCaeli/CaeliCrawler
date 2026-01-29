"""Merge duplicate Oberfranken entities.

Merges entities where short name and long name (with ", Bayern" suffix) both exist:
1. "Oberfranken-West (Region 4)" -> "Oberfranken-West (Region 4), Bayern" (1 into 21 facets)
2. "Region Oberfranken-Ost, Bayern" -> "Region Oberfranken-Ost" (1 into 15 facets)
3. "Region Oberfranken-West, Bayern" -> "Region Oberfranken-West" (3 into 27 facets)

Revision ID: zl1234567926
Revises: zk1234567925
Create Date: 2026-01-14
"""

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "zl1234567926"
down_revision = "zk1234567925"
branch_labels = None
depends_on = None

# Merge definitions: (remove_name, keep_name)
MERGES = [
    ("Oberfranken-West (Region 4)", "Oberfranken-West (Region 4), Bayern"),
    ("Region Oberfranken-Ost, Bayern", "Region Oberfranken-Ost"),
    ("Region Oberfranken-West, Bayern", "Region Oberfranken-West"),
]


def upgrade() -> None:
    """Merge duplicate Oberfranken entities."""
    conn = op.get_bind()

    for remove_name, keep_name in MERGES:
        print(f"\n  Merging '{remove_name}' into '{keep_name}'...")

        # Find the entity to keep
        result = conn.execute(
            text("""
                SELECT id FROM entities
                WHERE name = :name AND is_active = true
                LIMIT 1
            """),
            {"name": keep_name}
        )
        keep_row = result.fetchone()

        # Find the entity to remove
        result = conn.execute(
            text("""
                SELECT id FROM entities
                WHERE name = :name AND is_active = true
                LIMIT 1
            """),
            {"name": remove_name}
        )
        remove_row = result.fetchone()

        if not keep_row:
            print(f"    Entity to keep '{keep_name}' not found - skipping")
            continue

        if not remove_row:
            print(f"    Entity to remove '{remove_name}' not found - skipping")
            continue

        keep_id = keep_row[0]
        remove_id = remove_row[0]

        # Update FacetValues with entity_id
        result = conn.execute(
            text("""
                UPDATE facet_values
                SET entity_id = :keep_id
                WHERE entity_id = :remove_id
            """),
            {"keep_id": keep_id, "remove_id": remove_id}
        )
        print(f"    Updated {result.rowcount} FacetValues (entity_id)")

        # Update FacetValues with target_entity_id
        result = conn.execute(
            text("""
                UPDATE facet_values
                SET target_entity_id = :keep_id
                WHERE target_entity_id = :remove_id
            """),
            {"keep_id": keep_id, "remove_id": remove_id}
        )
        print(f"    Updated {result.rowcount} FacetValues (target_entity_id)")

        # Update entity_relations source
        result = conn.execute(
            text("""
                UPDATE entity_relations
                SET source_entity_id = :keep_id
                WHERE source_entity_id = :remove_id
            """),
            {"keep_id": keep_id, "remove_id": remove_id}
        )
        print(f"    Updated {result.rowcount} EntityRelations (source)")

        # Update entity_relations target
        result = conn.execute(
            text("""
                UPDATE entity_relations
                SET target_entity_id = :keep_id
                WHERE target_entity_id = :remove_id
            """),
            {"keep_id": keep_id, "remove_id": remove_id}
        )
        print(f"    Updated {result.rowcount} EntityRelations (target)")

        # Deactivate the duplicate
        conn.execute(
            text("""
                UPDATE entities
                SET is_active = false
                WHERE id = :remove_id
            """),
            {"remove_id": remove_id}
        )
        print(f"    Deactivated entity '{remove_name}' (merged into {keep_id})")

    print()


def downgrade() -> None:
    """Downgrade is not fully reversible as data has been merged."""
    print("  Note: Merge cannot be fully reversed. Check metadata['merged_into'] to identify merged records.")
    pass
