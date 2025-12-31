"""Cleanup orphaned facet type slugs from analysis_templates

Revision ID: ao1234567931
Revises: an1234567930
Create Date: 2025-12-21

This migration removes orphaned facet type slugs from the
facet_config JSONB field in analysis_templates table.
These orphaned references occur when a facet_type is deleted
but the AnalysisTemplate references were not cleaned up.
"""
from alembic import op
import sqlalchemy as sa
import json

# revision identifiers, used by Alembic.
revision = 'ao1234567931'
down_revision = 'an1234567930b'
branch_labels = None
depends_on = None


def upgrade():
    # Get connection for raw SQL execution
    conn = op.get_bind()

    # Get all valid facet type slugs
    valid_facet_slugs_result = conn.execute(
        sa.text("SELECT slug FROM facet_types")
    )
    valid_facet_slugs = {row[0] for row in valid_facet_slugs_result}

    # Get all analysis templates with their facet_config
    templates_result = conn.execute(
        sa.text("""
            SELECT id, facet_config
            FROM analysis_templates
            WHERE facet_config IS NOT NULL
              AND jsonb_array_length(facet_config) > 0
        """)
    )

    # Process each template and remove orphaned facet slugs
    for row in templates_result:
        template_id = row[0]
        facet_config = row[1] or []

        # Filter out orphaned facet slugs
        cleaned_config = [
            fc for fc in facet_config
            if fc.get("facet_type_slug") in valid_facet_slugs
        ]

        # Only update if there were orphaned slugs
        if len(cleaned_config) != len(facet_config):
            orphaned = {
                fc.get("facet_type_slug")
                for fc in facet_config
                if fc.get("facet_type_slug") not in valid_facet_slugs
            }
            print(f"AnalysisTemplate {template_id}: Removing orphaned facet slugs: {orphaned}")

            conn.execute(
                sa.text("""
                    UPDATE analysis_templates
                    SET facet_config = :config::jsonb,
                        updated_at = NOW()
                    WHERE id = :template_id
                """),
                {"config": json.dumps(cleaned_config), "template_id": template_id}
            )


def downgrade():
    # Data migration - cannot be reversed
    # Orphaned slugs are intentionally removed and cannot be restored
    pass
