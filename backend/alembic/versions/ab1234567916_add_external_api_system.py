"""Add External API integration system.

This migration introduces the External API framework:
- ExternalAPIConfig: Configuration for external API integrations
- SyncRecord: Track individual record sync state and history
- Entity extensions: last_seen_at and external_source_id fields

Revision ID: ab1234567916
Revises: aa1234567915
Create Date: 2024-12-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "ab1234567916"
down_revision: Union[str, None] = "aa1234567915"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # Step 1: Create ExternalAPIConfig table
    # =========================================================================
    op.create_table(
        "external_api_configs",
        # Primary Key
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),

        # Link to DataSource (optional - can be standalone)
        sa.Column(
            "data_source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("data_sources.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
            unique=True,
        ),

        # Basic identification
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),

        # API Configuration
        sa.Column("api_type", sa.String(100), nullable=False, index=True),
        sa.Column("api_base_url", sa.String(1000), nullable=False),
        sa.Column("api_endpoint", sa.String(1000), nullable=False),

        # Authentication
        sa.Column(
            "auth_type",
            sa.String(50),
            nullable=False,
            server_default="none",
            comment="none, basic, bearer, api_key, oauth2",
        ),
        sa.Column(
            "auth_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
            comment="Authentication configuration (env var references, not actual secrets)",
        ),

        # Sync Configuration
        sa.Column(
            "sync_interval_hours",
            sa.Integer(),
            nullable=False,
            server_default="4",
            comment="How often to sync (in hours)",
        ),
        sa.Column(
            "sync_enabled",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "last_sync_status",
            sa.String(50),
            nullable=True,
            comment="success, partial, failed",
        ),
        sa.Column("last_sync_error", sa.Text(), nullable=True),
        sa.Column(
            "last_sync_stats",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Statistics from last sync run",
        ),

        # Entity Mapping Configuration
        sa.Column(
            "entity_type_slug",
            sa.String(100),
            nullable=False,
            comment="Target EntityType slug (e.g., wind_project)",
        ),
        sa.Column(
            "id_field",
            sa.String(255),
            nullable=False,
            server_default="id",
            comment="Field in API response to use as external_id",
        ),
        sa.Column(
            "name_field",
            sa.String(255),
            nullable=False,
            server_default="name",
            comment="Field in API response to use as entity name",
        ),
        sa.Column(
            "field_mappings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
            comment="Map API fields to entity core_attributes",
        ),
        sa.Column(
            "location_fields",
            postgresql.ARRAY(sa.String(255)),
            nullable=False,
            server_default="{}",
            comment="Fields containing location data for entity linking",
        ),

        # Request Configuration
        sa.Column(
            "request_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
            comment="Additional request config (headers, params, pagination)",
        ),

        # Lifecycle Management
        sa.Column(
            "mark_missing_inactive",
            sa.Boolean(),
            nullable=False,
            server_default="true",
            comment="Mark entities as inactive if not found in API",
        ),
        sa.Column(
            "inactive_after_days",
            sa.Integer(),
            nullable=False,
            server_default="7",
            comment="Days until missing record is marked inactive",
        ),

        # AI Entity Linking
        sa.Column(
            "ai_linking_enabled",
            sa.Boolean(),
            nullable=False,
            server_default="true",
            comment="Use AI for entity linking (e.g., location interpretation)",
        ),
        sa.Column(
            "link_to_entity_types",
            postgresql.ARRAY(sa.String(100)),
            nullable=False,
            server_default="{}",
            comment="Entity types to link to (e.g., municipality)",
        ),

        # Status
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="true",
            index=True,
        ),

        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Index for finding configs due for sync
    op.create_index(
        "ix_external_api_configs_sync_due",
        "external_api_configs",
        ["sync_enabled", "last_sync_at"],
    )

    # =========================================================================
    # Step 2: Create SyncRecord table
    # =========================================================================
    op.create_table(
        "sync_records",
        # Primary Key
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),

        # Foreign Keys
        sa.Column(
            "external_api_config_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("external_api_configs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "entity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("entities.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),

        # External Identification
        sa.Column(
            "external_id",
            sa.String(500),
            nullable=False,
            index=True,
            comment="ID from the external API",
        ),

        # Sync State
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "last_modified_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Modification timestamp from API (if available)",
        ),
        sa.Column(
            "content_hash",
            sa.String(64),
            nullable=False,
            comment="SHA256 hash for change detection",
        ),

        # Status
        sa.Column(
            "sync_status",
            sa.String(50),
            nullable=False,
            server_default="active",
            index=True,
            comment="active, updated, missing, archived",
        ),
        sa.Column(
            "missing_since",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the record was first not found in API",
        ),

        # Raw Data Cache
        sa.Column(
            "raw_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
            comment="Last fetched data from API",
        ),

        # Entity Linking Results
        sa.Column(
            "linked_entity_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default="{}",
            comment="IDs of entities linked via entity linking service",
        ),
        sa.Column(
            "linking_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Metadata about entity linking (confidence, method, etc.)",
        ),

        # Error Tracking
        sa.Column(
            "last_error",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "error_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),

        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),

        # Unique constraint: one record per external_id per config
        sa.UniqueConstraint(
            "external_api_config_id",
            "external_id",
            name="uq_sync_record_config_external_id",
        ),
    )

    # Index for finding stale records
    op.create_index(
        "ix_sync_records_missing",
        "sync_records",
        ["external_api_config_id", "sync_status", "missing_since"],
    )

    # =========================================================================
    # Step 3: Extend Entity table with sync fields
    # =========================================================================

    # Add last_seen_at field
    op.add_column(
        "entities",
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When this entity was last seen in external API sync",
        ),
    )

    # Add external_source_id field (link to ExternalAPIConfig)
    op.add_column(
        "entities",
        sa.Column(
            "external_source_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            index=True,
            comment="ExternalAPIConfig that created/manages this entity",
        ),
    )
    op.create_foreign_key(
        "fk_entities_external_source_id",
        "entities",
        "external_api_configs",
        ["external_source_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Index for finding entities from external sources
    op.create_index(
        "ix_entities_external_source_active",
        "entities",
        ["external_source_id", "is_active"],
    )


def downgrade() -> None:
    # =========================================================================
    # Reverse Step 3: Remove Entity extensions
    # =========================================================================
    op.drop_index("ix_entities_external_source_active", table_name="entities")
    op.drop_constraint("fk_entities_external_source_id", "entities", type_="foreignkey")
    op.drop_column("entities", "external_source_id")
    op.drop_column("entities", "last_seen_at")

    # =========================================================================
    # Reverse Step 2: Drop SyncRecord table
    # =========================================================================
    op.drop_index("ix_sync_records_missing", table_name="sync_records")
    op.drop_table("sync_records")

    # =========================================================================
    # Reverse Step 1: Drop ExternalAPIConfig table
    # =========================================================================
    op.drop_index("ix_external_api_configs_sync_due", table_name="external_api_configs")
    op.drop_table("external_api_configs")
