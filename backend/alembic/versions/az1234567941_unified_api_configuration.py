"""Unified API Configuration model.

This migration consolidates ExternalAPIConfig and APITemplate into a single
APIConfiguration model, always linked to a DataSource.

Revision ID: az1234567941
Revises: ay1234567940
Create Date: 2024-12-25

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "az1234567941"
down_revision: Union[str, None] = "ay1234567940"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            """
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_name = :table_name AND column_name = :column_name
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    )
    return result.scalar() > 0


def table_exists(table_name: str) -> bool:
    """Check if a table exists."""
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            """
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name = :table_name
            """
        ),
        {"table_name": table_name},
    )
    return result.scalar() > 0


def upgrade() -> None:
    # ==========================================================================
    # Step 1: Create the new api_configurations table
    # ==========================================================================
    op.create_table(
        "api_configurations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "data_source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("data_sources.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        # Connection Configuration
        sa.Column("api_type", sa.String(50), nullable=False, server_default="rest"),
        sa.Column("endpoint", sa.String(1000), nullable=False, server_default=""),
        sa.Column("auth_type", sa.String(50), nullable=False, server_default="none"),
        sa.Column(
            "auth_config",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "request_config",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        # Import Mode
        sa.Column(
            "import_mode", sa.String(20), nullable=False, server_default="entities"
        ),
        # Entity Configuration
        sa.Column("entity_type_slug", sa.String(100), nullable=True),
        sa.Column("id_field", sa.String(255), nullable=False, server_default="id"),
        sa.Column("name_field", sa.String(255), nullable=False, server_default="name"),
        sa.Column(
            "field_mappings",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "location_fields",
            postgresql.ARRAY(sa.String(255)),
            nullable=False,
            server_default=sa.text("'{}'::varchar[]"),
        ),
        # Facet Configuration
        sa.Column(
            "facet_mappings",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "entity_matching",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        # Sync Configuration
        sa.Column("sync_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "sync_interval_hours", sa.Integer, nullable=False, server_default="24"
        ),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_status", sa.String(50), nullable=True),
        sa.Column("last_sync_error", sa.Text, nullable=True),
        sa.Column("last_sync_stats", postgresql.JSONB, nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        # Lifecycle
        sa.Column(
            "mark_missing_inactive", sa.Boolean, nullable=False, server_default="true"
        ),
        sa.Column("inactive_after_days", sa.Integer, nullable=False, server_default="7"),
        # AI Features
        sa.Column(
            "ai_linking_enabled", sa.Boolean, nullable=False, server_default="true"
        ),
        sa.Column(
            "link_to_entity_types",
            postgresql.ARRAY(sa.String(100)),
            nullable=False,
            server_default=sa.text("'{}'::varchar[]"),
        ),
        # KI-Discovery
        sa.Column(
            "keywords",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.8"),
        sa.Column("is_template", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("documentation_url", sa.Text, nullable=True),
        # Status
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Create indexes
    op.create_index(
        "ix_api_configurations_sync_due",
        "api_configurations",
        ["sync_enabled", "last_sync_at"],
    )
    op.create_index(
        "ix_api_configurations_data_source",
        "api_configurations",
        ["data_source_id"],
    )
    op.create_index(
        "ix_api_configurations_is_active",
        "api_configurations",
        ["is_active"],
    )

    # ==========================================================================
    # Step 2: Migrate data from external_api_configs (if exists)
    # ==========================================================================
    if table_exists("external_api_configs"):
        # First, create DataSources for configs that don't have one
        op.execute(
            sa.text(
                """
                INSERT INTO data_sources (id, name, source_type, base_url, status, created_at, updated_at)
                SELECT
                    gen_random_uuid(),
                    eac.name,
                    'REST_API',
                    eac.api_base_url,
                    'ACTIVE',
                    eac.created_at,
                    eac.updated_at
                FROM external_api_configs eac
                WHERE eac.data_source_id IS NULL
                """
            )
        )

        # Now migrate the configs
        op.execute(
            sa.text(
                """
                INSERT INTO api_configurations (
                    id,
                    data_source_id,
                    api_type,
                    endpoint,
                    auth_type,
                    auth_config,
                    request_config,
                    import_mode,
                    entity_type_slug,
                    id_field,
                    name_field,
                    field_mappings,
                    location_fields,
                    facet_mappings,
                    entity_matching,
                    sync_enabled,
                    sync_interval_hours,
                    last_sync_at,
                    last_sync_status,
                    last_sync_error,
                    last_sync_stats,
                    mark_missing_inactive,
                    inactive_after_days,
                    ai_linking_enabled,
                    link_to_entity_types,
                    is_active,
                    created_at,
                    updated_at
                )
                SELECT
                    eac.id,
                    COALESCE(
                        eac.data_source_id,
                        (SELECT id FROM data_sources WHERE base_url = eac.api_base_url LIMIT 1)
                    ),
                    eac.api_type,
                    COALESCE(eac.api_endpoint, ''),
                    COALESCE(eac.auth_type, 'none'),
                    COALESCE(eac.auth_config, '{}'::jsonb),
                    COALESCE(eac.request_config, '{}'::jsonb),
                    'entities',
                    eac.entity_type_slug,
                    COALESCE(eac.id_field, 'id'),
                    COALESCE(eac.name_field, 'name'),
                    COALESCE(eac.field_mappings, '{}'::jsonb),
                    COALESCE(eac.location_fields, '{}'::varchar[]),
                    COALESCE(eac.facet_mappings, '{}'::jsonb),
                    '{}'::jsonb,
                    COALESCE(eac.sync_enabled, true),
                    COALESCE(eac.sync_interval_hours, 24),
                    eac.last_sync_at,
                    eac.last_sync_status,
                    eac.last_sync_error,
                    eac.last_sync_stats,
                    COALESCE(eac.mark_missing_inactive, true),
                    COALESCE(eac.inactive_after_days, 7),
                    COALESCE(eac.ai_linking_enabled, true),
                    COALESCE(eac.link_to_entity_types, '{}'::varchar[]),
                    COALESCE(eac.is_active, true),
                    eac.created_at,
                    eac.updated_at
                FROM external_api_configs eac
                WHERE EXISTS (
                    SELECT 1 FROM data_sources ds
                    WHERE ds.id = eac.data_source_id
                    OR ds.base_url = eac.api_base_url
                )
                """
            )
        )

    # ==========================================================================
    # Step 3: Migrate data from api_templates (if exists)
    # ==========================================================================
    if table_exists("api_templates"):
        # Create DataSources for templates
        op.execute(
            sa.text(
                """
                INSERT INTO data_sources (id, name, source_type, base_url, status, created_at, updated_at)
                SELECT
                    gen_random_uuid(),
                    at.name,
                    'REST_API',
                    at.base_url,
                    'ACTIVE',
                    at.created_at,
                    at.updated_at
                FROM api_templates at
                WHERE NOT EXISTS (
                    SELECT 1 FROM data_sources ds WHERE ds.base_url = at.base_url
                )
                """
            )
        )

        # Now migrate templates that have facet_mapping
        op.execute(
            sa.text(
                """
                INSERT INTO api_configurations (
                    id,
                    data_source_id,
                    api_type,
                    endpoint,
                    auth_type,
                    auth_config,
                    import_mode,
                    entity_type_slug,
                    facet_mappings,
                    entity_matching,
                    sync_enabled,
                    sync_interval_hours,
                    last_sync_at,
                    last_sync_status,
                    last_sync_stats,
                    keywords,
                    confidence,
                    is_template,
                    documentation_url,
                    is_active,
                    created_at,
                    updated_at
                )
                SELECT
                    at.id,
                    (SELECT id FROM data_sources WHERE base_url = at.base_url LIMIT 1),
                    LOWER(at.api_type),
                    COALESCE(at.endpoint, ''),
                    CASE WHEN at.auth_required THEN 'bearer' ELSE 'none' END,
                    COALESCE(at.auth_config, '{}'::jsonb),
                    CASE
                        WHEN at.facet_mapping IS NOT NULL AND at.facet_mapping != '{}'::jsonb
                        THEN 'facets'
                        ELSE 'entities'
                    END,
                    COALESCE((at.entity_matching->>'entity_type_slug')::varchar, NULL),
                    COALESCE(at.facet_mapping, '{}'::jsonb),
                    COALESCE(at.entity_matching, '{}'::jsonb),
                    COALESCE(at.schedule_enabled, false),
                    CASE
                        WHEN at.schedule_cron IS NOT NULL THEN 24
                        ELSE 0
                    END,
                    at.last_sync_at,
                    at.last_sync_status,
                    at.last_sync_stats,
                    COALESCE(at.keywords, '[]'::jsonb),
                    COALESCE(at.confidence, 0.8),
                    true,
                    at.documentation_url,
                    at.status = 'ACTIVE',
                    at.created_at,
                    at.updated_at
                FROM api_templates at
                WHERE NOT EXISTS (
                    SELECT 1 FROM api_configurations ac WHERE ac.id = at.id
                )
                AND EXISTS (
                    SELECT 1 FROM data_sources ds WHERE ds.base_url = at.base_url
                )
                """
            )
        )

    # ==========================================================================
    # Step 4: Add api_configuration_id to entities
    # ==========================================================================
    if not column_exists("entities", "api_configuration_id"):
        op.add_column(
            "entities",
            sa.Column(
                "api_configuration_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("api_configurations.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
        op.create_index(
            "ix_entities_api_configuration_id",
            "entities",
            ["api_configuration_id"],
        )

        # Migrate data from external_source_id if column exists
        if column_exists("entities", "external_source_id"):
            op.execute(
                sa.text(
                    """
                    UPDATE entities e
                    SET api_configuration_id = ac.id
                    FROM api_configurations ac
                    WHERE e.external_source_id = ac.id
                    """
                )
            )

    # ==========================================================================
    # Step 5: Update sync_records to use api_configuration_id
    # ==========================================================================
    if table_exists("sync_records"):
        if not column_exists("sync_records", "api_configuration_id"):
            op.add_column(
                "sync_records",
                sa.Column(
                    "api_configuration_id",
                    postgresql.UUID(as_uuid=True),
                    nullable=True,
                ),
            )

            # Migrate data from external_api_config_id
            if column_exists("sync_records", "external_api_config_id"):
                op.execute(
                    sa.text(
                        """
                        UPDATE sync_records sr
                        SET api_configuration_id = ac.id
                        FROM api_configurations ac
                        WHERE sr.external_api_config_id = ac.id
                        """
                    )
                )

            # Add FK constraint
            op.create_foreign_key(
                "fk_sync_records_api_configuration",
                "sync_records",
                "api_configurations",
                ["api_configuration_id"],
                ["id"],
                ondelete="CASCADE",
            )

            # Make column non-nullable after migration
            op.alter_column(
                "sync_records",
                "api_configuration_id",
                nullable=False,
            )

            # Create new index
            op.create_index(
                "ix_sync_records_api_configuration_id",
                "sync_records",
                ["api_configuration_id"],
            )

    # ==========================================================================
    # Step 6: Drop old columns and constraints (cleanup)
    # ==========================================================================

    # Drop old FK from entities if exists
    if column_exists("entities", "external_source_id"):
        try:
            op.drop_constraint(
                "entities_external_source_id_fkey", "entities", type_="foreignkey"
            )
        except Exception:
            pass
        try:
            op.drop_index("ix_entities_external_source_id", "entities")
        except Exception:
            pass
        op.drop_column("entities", "external_source_id")

    # Drop old column from sync_records if exists
    if column_exists("sync_records", "external_api_config_id"):
        try:
            op.drop_constraint(
                "sync_records_external_api_config_id_fkey",
                "sync_records",
                type_="foreignkey",
            )
        except Exception:
            pass
        try:
            op.drop_constraint(
                "uq_sync_record_config_external_id", "sync_records", type_="unique"
            )
        except Exception:
            pass
        try:
            op.drop_index("ix_sync_records_missing", "sync_records")
        except Exception:
            pass
        op.drop_column("sync_records", "external_api_config_id")

        # Recreate unique constraint with new column
        op.create_unique_constraint(
            "uq_sync_record_config_external_id",
            "sync_records",
            ["api_configuration_id", "external_id"],
        )

        # Recreate missing index with new column
        op.create_index(
            "ix_sync_records_missing",
            "sync_records",
            ["api_configuration_id", "sync_status", "missing_since"],
        )

    # Note: We keep the old tables for now, can be dropped in a later migration
    # op.drop_table("external_api_configs")
    # op.drop_table("api_templates")


def downgrade() -> None:
    # This is a complex migration - downgrade would require significant work
    # For now, just drop the new table and columns

    # Drop FK from sync_records
    if column_exists("sync_records", "api_configuration_id"):
        try:
            op.drop_constraint(
                "fk_sync_records_api_configuration", "sync_records", type_="foreignkey"
            )
        except Exception:
            pass
        try:
            op.drop_index("ix_sync_records_api_configuration_id", "sync_records")
        except Exception:
            pass
        op.drop_column("sync_records", "api_configuration_id")

    # Drop FK from entities
    if column_exists("entities", "api_configuration_id"):
        try:
            op.drop_index("ix_entities_api_configuration_id", "entities")
        except Exception:
            pass
        op.drop_column("entities", "api_configuration_id")

    # Drop indexes and table
    try:
        op.drop_index("ix_api_configurations_sync_due", "api_configurations")
    except Exception:
        pass
    try:
        op.drop_index("ix_api_configurations_data_source", "api_configurations")
    except Exception:
        pass
    try:
        op.drop_index("ix_api_configurations_is_active", "api_configurations")
    except Exception:
        pass

    if table_exists("api_configurations"):
        op.drop_table("api_configurations")
