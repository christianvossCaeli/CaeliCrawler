"""Merge duplicate Hannover locations/entities.

Merges "Region Hannover" into "Hannover" by:
1. Moving all DataSource references
2. Moving all Entity references
3. Deactivating the duplicate

Revision ID: zk1234567925
Revises: zj1234567924
Create Date: 2026-01-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "zk1234567925"
down_revision = "zj1234567924"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Merge Region Hannover into Hannover."""
    conn = op.get_bind()

    # --- Handle Locations table ---
    print("\n  Checking Locations table...")

    # Find "Hannover" location (the canonical one to keep)
    result = conn.execute(
        text("""
            SELECT id, name FROM locations
            WHERE LOWER(name) = 'hannover'
            AND is_active = true
            LIMIT 1
        """)
    )
    hannover_loc = result.fetchone()

    # Find "Region Hannover" location (the duplicate to merge)
    result = conn.execute(
        text("""
            SELECT id, name FROM locations
            WHERE LOWER(name) LIKE '%region hannover%'
            AND is_active = true
            LIMIT 1
        """)
    )
    region_hannover_loc = result.fetchone()

    if hannover_loc and region_hannover_loc:
        keep_id = hannover_loc[0]
        remove_id = region_hannover_loc[0]

        print(f"  Found Location duplicates:")
        print(f"    KEEP: '{hannover_loc[1]}' (ID: {keep_id})")
        print(f"    REMOVE: '{region_hannover_loc[1]}' (ID: {remove_id})")

        # Update DataSources pointing to the duplicate
        result = conn.execute(
            text("""
                UPDATE data_sources
                SET location_id = :keep_id
                WHERE location_id = :remove_id
            """),
            {"keep_id": keep_id, "remove_id": remove_id}
        )
        print(f"    Updated {result.rowcount} DataSources")

        # Update Entities pointing to the duplicate
        result = conn.execute(
            text("""
                UPDATE entities
                SET location_id = :keep_id
                WHERE location_id = :remove_id
            """),
            {"keep_id": keep_id, "remove_id": remove_id}
        )
        print(f"    Updated {result.rowcount} Entities")

        # Deactivate the duplicate location
        conn.execute(
            text("""
                UPDATE locations
                SET is_active = false
                WHERE id = :remove_id
            """),
            {"remove_id": remove_id}
        )
        print(f"    Deactivated duplicate Location (merged into {keep_id})")

    elif hannover_loc:
        print(f"  'Hannover' Location found, but no 'Region Hannover' duplicate")
    elif region_hannover_loc:
        print(f"  'Region Hannover' found but no 'Hannover' - keeping as-is")
    else:
        print(f"  No Hannover Locations found")

    # --- Handle Entities table (if there are Entity duplicates) ---
    print("\n  Checking Entities table...")

    # Find "Hannover" entity
    result = conn.execute(
        text("""
            SELECT id, name FROM entities
            WHERE LOWER(name) = 'hannover'
            AND is_active = true
            LIMIT 1
        """)
    )
    hannover_entity = result.fetchone()

    # Find "Region Hannover" entity
    result = conn.execute(
        text("""
            SELECT id, name FROM entities
            WHERE LOWER(name) LIKE '%region hannover%'
            AND is_active = true
            LIMIT 1
        """)
    )
    region_hannover_entity = result.fetchone()

    if hannover_entity and region_hannover_entity:
        keep_id = hannover_entity[0]
        remove_id = region_hannover_entity[0]

        print(f"  Found Entity duplicates:")
        print(f"    KEEP: '{hannover_entity[1]}' (ID: {keep_id})")
        print(f"    REMOVE: '{region_hannover_entity[1]}' (ID: {remove_id})")

        # Update FacetValues pointing to the duplicate entity
        result = conn.execute(
            text("""
                UPDATE facet_values
                SET entity_id = :keep_id
                WHERE entity_id = :remove_id
            """),
            {"keep_id": keep_id, "remove_id": remove_id}
        )
        print(f"    Updated {result.rowcount} FacetValues (entity_id)")

        # Update FacetValues with target_entity_id pointing to duplicate
        result = conn.execute(
            text("""
                UPDATE facet_values
                SET target_entity_id = :keep_id
                WHERE target_entity_id = :remove_id
            """),
            {"keep_id": keep_id, "remove_id": remove_id}
        )
        print(f"    Updated {result.rowcount} FacetValues (target_entity_id)")

        # Update entity_relations
        result = conn.execute(
            text("""
                UPDATE entity_relations
                SET source_entity_id = :keep_id
                WHERE source_entity_id = :remove_id
            """),
            {"keep_id": keep_id, "remove_id": remove_id}
        )
        print(f"    Updated {result.rowcount} EntityRelations (source)")

        result = conn.execute(
            text("""
                UPDATE entity_relations
                SET target_entity_id = :keep_id
                WHERE target_entity_id = :remove_id
            """),
            {"keep_id": keep_id, "remove_id": remove_id}
        )
        print(f"    Updated {result.rowcount} EntityRelations (target)")

        # Deactivate the duplicate entity
        conn.execute(
            text("""
                UPDATE entities
                SET is_active = false
                WHERE id = :remove_id
            """),
            {"remove_id": remove_id}
        )
        print(f"    Deactivated duplicate Entity (merged into {keep_id})")

    elif hannover_entity:
        print(f"  'Hannover' Entity found, but no 'Region Hannover' duplicate")
    elif region_hannover_entity:
        print(f"  'Region Hannover' found but no 'Hannover' - keeping as-is")
    else:
        print(f"  No Hannover Entities found")

    print()


def downgrade() -> None:
    """
    Downgrade is not fully reversible as data has been merged.
    The merged_into metadata can be used to identify what was merged.
    """
    print("  Note: Merge cannot be fully reversed. Check metadata['merged_into'] to identify merged records.")
    pass
