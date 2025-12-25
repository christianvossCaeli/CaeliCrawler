"""Add custom summaries feature

Revision ID: an1234567930
Revises: am1234567929_add_missing_composite_indexes
Create Date: 2024-12-24

Adds tables for user-defined dashboard summaries:
- custom_summaries: Main summary definitions
- summary_widgets: Widget configurations per summary
- summary_executions: Execution history and cached data
- summary_shares: Shareable links with password protection

Also extends NotificationEventType with SUMMARY_UPDATED and SUMMARY_RELEVANT_CHANGES.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "an1234567930"
down_revision = "am1234567929"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enums
    op.execute("""
        CREATE TYPE summary_status_enum AS ENUM ('draft', 'active', 'paused', 'archived');
    """)
    op.execute("""
        CREATE TYPE summary_trigger_type_enum AS ENUM ('manual', 'cron', 'crawl_category', 'crawl_preset');
    """)
    op.execute("""
        CREATE TYPE summary_widget_type_enum AS ENUM (
            'table', 'bar_chart', 'line_chart', 'pie_chart',
            'stat_card', 'text', 'comparison', 'timeline', 'map'
        );
    """)
    op.execute("""
        CREATE TYPE summary_execution_status_enum AS ENUM (
            'pending', 'running', 'completed', 'failed', 'skipped'
        );
    """)

    # custom_summaries table
    op.create_table(
        "custom_summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("original_prompt", sa.Text(), nullable=False),
        sa.Column(
            "interpreted_config",
            postgresql.JSONB(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "layout_config",
            postgresql.JSONB(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "draft", "active", "paused", "archived",
                name="summary_status_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "trigger_type",
            sa.Enum(
                "manual", "cron", "crawl_category", "crawl_preset",
                name="summary_trigger_type_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="manual",
        ),
        sa.Column("schedule_cron", sa.String(100), nullable=True),
        sa.Column(
            "trigger_category_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "trigger_preset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("crawl_presets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("schedule_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("check_relevance", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("relevance_threshold", sa.Float(), nullable=False, server_default="0.3"),
        sa.Column("auto_expand", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("execution_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_data_hash", sa.String(64), nullable=True),
        sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
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

    op.create_index("ix_custom_summaries_user_id", "custom_summaries", ["user_id"])
    op.create_index("ix_custom_summaries_status", "custom_summaries", ["status"])
    op.create_index(
        "ix_custom_summaries_user_status",
        "custom_summaries",
        ["user_id", "status"],
    )
    op.create_index(
        "ix_custom_summaries_next_run",
        "custom_summaries",
        ["next_run_at", "schedule_enabled"],
    )
    op.create_index(
        "ix_custom_summaries_trigger_category",
        "custom_summaries",
        ["trigger_category_id"],
    )
    op.create_index(
        "ix_custom_summaries_trigger_preset",
        "custom_summaries",
        ["trigger_preset_id"],
    )

    # summary_widgets table
    op.create_table(
        "summary_widgets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "summary_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("custom_summaries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "widget_type",
            sa.Enum(
                "table", "bar_chart", "line_chart", "pie_chart",
                "stat_card", "text", "comparison", "timeline", "map",
                name="summary_widget_type_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("subtitle", sa.String(500), nullable=True),
        sa.Column("position_x", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("position_y", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("width", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("height", sa.Integer(), nullable=False, server_default="2"),
        sa.Column(
            "query_config",
            postgresql.JSONB(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "visualization_config",
            postgresql.JSONB(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
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

    op.create_index("ix_summary_widgets_summary_id", "summary_widgets", ["summary_id"])
    op.create_index(
        "ix_summary_widgets_summary_order",
        "summary_widgets",
        ["summary_id", "display_order"],
    )

    # summary_executions table
    op.create_table(
        "summary_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "summary_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("custom_summaries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "running", "completed", "failed", "skipped",
                name="summary_execution_status_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("triggered_by", sa.String(50), nullable=False, server_default="manual"),
        sa.Column("trigger_details", postgresql.JSONB(), nullable=True),
        sa.Column(
            "cached_data",
            postgresql.JSONB(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column("relevance_reason", sa.Text(), nullable=True),
        sa.Column("data_hash", sa.String(64), nullable=True),
        sa.Column("has_changes", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_summary_executions_summary_id",
        "summary_executions",
        ["summary_id"],
    )
    op.create_index(
        "ix_summary_executions_summary_created",
        "summary_executions",
        ["summary_id", "created_at"],
    )
    op.create_index(
        "ix_summary_executions_status_created",
        "summary_executions",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_summary_executions_celery_task_id",
        "summary_executions",
        ["celery_task_id"],
    )

    # summary_shares table
    op.create_table(
        "summary_shares",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "summary_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("custom_summaries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("share_token", sa.String(64), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("allow_export", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index("ix_summary_shares_summary_id", "summary_shares", ["summary_id"])
    op.create_index("ix_summary_shares_share_token", "summary_shares", ["share_token"])
    op.create_index(
        "ix_summary_shares_active_token",
        "summary_shares",
        ["is_active", "share_token"],
    )

    # Extend NotificationEventType enum with summary events
    # Note: PostgreSQL requires ALTER TYPE to add values
    op.execute("""
        ALTER TYPE notification_event_type ADD VALUE IF NOT EXISTS 'SUMMARY_UPDATED';
    """)
    op.execute("""
        ALTER TYPE notification_event_type ADD VALUE IF NOT EXISTS 'SUMMARY_RELEVANT_CHANGES';
    """)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("summary_shares")
    op.drop_table("summary_executions")
    op.drop_table("summary_widgets")
    op.drop_table("custom_summaries")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS summary_execution_status_enum;")
    op.execute("DROP TYPE IF EXISTS summary_widget_type_enum;")
    op.execute("DROP TYPE IF EXISTS summary_trigger_type_enum;")
    op.execute("DROP TYPE IF EXISTS summary_status_enum;")

    # Note: Cannot remove values from enum in PostgreSQL
    # SUMMARY_UPDATED and SUMMARY_RELEVANT_CHANGES will remain in notification_event_type
