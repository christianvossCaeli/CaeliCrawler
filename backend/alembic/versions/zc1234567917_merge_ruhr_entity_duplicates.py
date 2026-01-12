"""Merge duplicate Ruhr entities.

This migration merges duplicate entities that refer to the same
geographic/administrative regions in the Ruhr area. The duplicates
were created by AI extraction with slightly different naming conventions.

Merge Groups:
1. Metropole Ruhr: 4 variants -> 1
2. Regionalverband Ruhr (territorial_entity): 5 variants -> 1
3. Ruhrgebiet: 3 variants -> 1

Total: 12 entities merged into 3, removing 9 duplicates.

Revision ID: zc1234567917
Revises: zb1234567916
Create Date: 2026-01-04
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "zc1234567917"
down_revision = "zb1234567916"
branch_labels = None
depends_on = None

# Merge Groups - target_id is the entity to keep
MERGE_GROUPS = [
    {
        "name": "Metropole Ruhr",
        "target_id": "fc2554e5-16cd-436d-9197-48e0b329f9d3",
        "duplicate_ids": [
            "0dd43bd1-e4bd-4c28-968c-491b4d91f380",  # Metropole Ruhr / Nordrhein-Westfalen
            "e26c5a2d-40a5-411f-8e22-ae5467799314",  # Metropole Ruhr / Regionalverband Ruhr
            "5572b27d-e848-44c2-b748-83a17ae4f2bb",  # Metropole Ruhr / Regionalverband Ruhr (RVR)
        ],
    },
    {
        "name": "Regionalverband Ruhr (territorial_entity)",
        "target_id": "b6b8f872-e9b1-4bd4-a2fd-d69cfad0a6f9",
        "duplicate_ids": [
            "20a1f17e-b949-4b96-b73c-2458a389c223",  # Regionalverband Ruhr (RVR) - territorial_entity
            "44aa4239-5d8e-4410-abc4-b5ac98bcaa17",  # Regionalverband Ruhr (RVR), Nordrhein-Westfalen
            "721d7cc8-5c7e-4a2f-8be4-a1ad997a6dbe",  # Regionalverband Ruhr (Metropole Ruhr), NRW
            "09f66dd9-5b7b-4340-b2d0-a2b6aeac6201",  # Region Ruhr / Regionalverband Ruhr (RVR)
        ],
    },
    {
        "name": "Ruhrgebiet",
        "target_id": "eae003b1-aa49-402d-b95c-85756b80f649",
        "duplicate_ids": [
            "43bdf62d-6922-4c75-a333-93ff81bd555d",  # Ruhrgebiet, Nordrhein-Westfalen
            "c22c587d-bbc6-420f-98f3-c50d7fd55389",  # Ruhrgebiet und angrenzende Regionen (NRW)
        ],
    },
]

# All tables with foreign keys to entities
FK_TABLES = [
    ("entity_attachments", "entity_id"),
    ("entity_relations", "source_entity_id"),
    ("entity_relations", "target_entity_id"),
    ("extracted_data", "primary_entity_id"),
    ("facet_value_history", "entity_id"),
    ("facet_values", "entity_id"),
    ("facet_values", "target_entity_id"),
    ("llm_usage_records", "entity_id"),
    ("pysis_processes", "entity_id"),
    ("sync_records", "entity_id"),
    ("user_favorites", "entity_id"),
    ("entities", "parent_id"),
    ("assistant_reminders", "entity_id"),
]


def upgrade() -> None:
    """Merge duplicate entities by reassigning references and soft-deleting duplicates."""
    for group in MERGE_GROUPS:
        target_id = group["target_id"]
        duplicate_ids = group["duplicate_ids"]

        if not duplicate_ids:
            continue

        # Create SQL-safe list of duplicate IDs
        dup_list = ", ".join(f"'{d}'" for d in duplicate_ids)

        # Special handling for facet_values:
        # Delete duplicate facet_values that would violate unique constraint
        # when merged (same entity_id + facet_type_id + text_representation hash)
        op.execute(
            f"""
            DELETE FROM facet_values fv
            WHERE fv.entity_id IN ({dup_list})
              AND EXISTS (
                  SELECT 1 FROM facet_values existing
                  WHERE existing.entity_id = '{target_id}'
                    AND existing.facet_type_id = fv.facet_type_id
                    AND md5(existing.text_representation) = md5(fv.text_representation)
              )
            """
        )

        # Update all foreign key references from duplicates to target
        for table, column in FK_TABLES:
            op.execute(
                f"""
                UPDATE {table}
                SET {column} = '{target_id}'
                WHERE {column} IN ({dup_list})
                """
            )

        # Soft-delete duplicate entities (set is_active = false)
        op.execute(
            f"""
            UPDATE entities
            SET is_active = false,
                updated_at = NOW()
            WHERE id IN ({dup_list})
            """
        )


def downgrade() -> None:
    """Reactivate soft-deleted entities (references cannot be restored)."""
    # Collect all duplicate IDs
    all_duplicate_ids = []
    for group in MERGE_GROUPS:
        all_duplicate_ids.extend(group["duplicate_ids"])

    if all_duplicate_ids:
        dup_list = ", ".join(f"'{d}'" for d in all_duplicate_ids)
        op.execute(
            f"""
            UPDATE entities
            SET is_active = true,
                updated_at = NOW()
            WHERE id IN ({dup_list})
            """
        )
