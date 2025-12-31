"""Add LLM usage tracking tables for analytics.

This migration creates tables for tracking LLM API usage across all providers
(Azure OpenAI, Anthropic Claude) with detailed metrics for cost analysis,
performance monitoring, and budget management.

Tables created:
- llm_usage_records: Individual LLM API call records
- llm_usage_monthly_aggregates: Monthly aggregated usage data
- llm_budget_configs: Budget configuration and limits
- llm_budget_alerts: History of budget alerts sent

Revision ID: bg1234567948
Revises: bf1234567947
Create Date: 2025-01-30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "bg1234567948"
down_revision = "bf1234567947"
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    return table_name in inspector.get_table_names()


def enum_exists(enum_name: str) -> bool:
    """Check if an enum type exists in the database."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = :name"),
        {"name": enum_name}
    )
    return result.fetchone() is not None


def upgrade() -> None:
    # Create enum types if they don't exist
    if not enum_exists("llm_provider"):
        op.execute("""
            CREATE TYPE llm_provider AS ENUM ('azure_openai', 'anthropic')
        """)

    if not enum_exists("llm_task_type"):
        op.execute("""
            CREATE TYPE llm_task_type AS ENUM (
                'summarize', 'extract', 'classify', 'embedding', 'vision',
                'chat', 'plan_mode', 'discovery', 'entity_analysis',
                'attachment_analysis', 'relevance_check', 'custom'
            )
        """)

    if not enum_exists("budget_type"):
        op.execute("""
            CREATE TYPE budget_type AS ENUM ('global', 'category', 'task_type', 'model')
        """)

    # Create llm_usage_records table
    if not table_exists("llm_usage_records"):
        op.create_table(
            "llm_usage_records",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "provider",
                postgresql.ENUM("azure_openai", "anthropic", name="llm_provider", create_type=False),
                nullable=False,
            ),
            sa.Column("model", sa.String(100), nullable=False),
            sa.Column(
                "task_type",
                postgresql.ENUM(
                    "summarize", "extract", "classify", "embedding", "vision",
                    "chat", "plan_mode", "discovery", "entity_analysis",
                    "attachment_analysis", "relevance_check", "custom",
                    name="llm_task_type", create_type=False
                ),
                nullable=False,
            ),
            sa.Column("task_name", sa.String(255), nullable=True),
            sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("estimated_cost_cents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("duration_ms", sa.Integer(), nullable=True),
            sa.Column("request_id", sa.String(100), nullable=True),
            sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column(
                "metadata",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default="{}",
            ),
            sa.Column("is_error", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["document_id"], ["documents.id"], ondelete="SET NULL"
            ),
            sa.ForeignKeyConstraint(
                ["entity_id"], ["entities.id"], ondelete="SET NULL"
            ),
            sa.ForeignKeyConstraint(
                ["category_id"], ["categories.id"], ondelete="SET NULL"
            ),
            sa.ForeignKeyConstraint(
                ["user_id"], ["users.id"], ondelete="SET NULL"
            ),
        )

        # Create indexes for llm_usage_records
        op.create_index(
            "ix_llm_usage_created_at",
            "llm_usage_records",
            ["created_at"],
        )
        op.create_index(
            "ix_llm_usage_provider",
            "llm_usage_records",
            ["provider"],
        )
        op.create_index(
            "ix_llm_usage_model",
            "llm_usage_records",
            ["model"],
        )
        op.create_index(
            "ix_llm_usage_provider_model",
            "llm_usage_records",
            ["provider", "model"],
        )
        op.create_index(
            "ix_llm_usage_task_type",
            "llm_usage_records",
            ["task_type"],
        )
        op.create_index(
            "ix_llm_usage_category_id",
            "llm_usage_records",
            ["category_id"],
        )
        op.create_index(
            "ix_llm_usage_document_id",
            "llm_usage_records",
            ["document_id"],
        )
        op.create_index(
            "ix_llm_usage_entity_id",
            "llm_usage_records",
            ["entity_id"],
        )
        op.create_index(
            "ix_llm_usage_user_id",
            "llm_usage_records",
            ["user_id"],
        )
        # Functional index for daily aggregation
        op.execute("""
            CREATE INDEX ix_llm_usage_daily
            ON llm_usage_records (date_trunc('day', created_at))
        """)

    # Create llm_usage_monthly_aggregates table
    if not table_exists("llm_usage_monthly_aggregates"):
        op.create_table(
            "llm_usage_monthly_aggregates",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("year_month", sa.String(7), nullable=False),
            sa.Column(
                "provider",
                postgresql.ENUM("azure_openai", "anthropic", name="llm_provider", create_type=False),
                nullable=False,
            ),
            sa.Column("model", sa.String(100), nullable=False),
            sa.Column(
                "task_type",
                postgresql.ENUM(
                    "summarize", "extract", "classify", "embedding", "vision",
                    "chat", "plan_mode", "discovery", "entity_analysis",
                    "attachment_analysis", "relevance_check", "custom",
                    name="llm_task_type", create_type=False
                ),
                nullable=False,
            ),
            sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_completion_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_cost_cents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("avg_duration_ms", sa.Float(), nullable=False, server_default="0"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["category_id"], ["categories.id"], ondelete="SET NULL"
            ),
        )

        # Create indexes for monthly aggregates
        op.create_index(
            "ix_llm_usage_monthly_year_month",
            "llm_usage_monthly_aggregates",
            ["year_month"],
        )
        op.create_index(
            "ix_llm_usage_monthly_provider_model",
            "llm_usage_monthly_aggregates",
            ["provider", "model"],
        )

    # Create llm_budget_configs table
    if not table_exists("llm_budget_configs"):
        op.create_table(
            "llm_budget_configs",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column(
                "budget_type",
                postgresql.ENUM("global", "category", "task_type", "model", name="budget_type", create_type=False),
                nullable=False,
            ),
            sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("reference_value", sa.String(100), nullable=True),
            sa.Column("monthly_limit_cents", sa.Integer(), nullable=False),
            sa.Column("warning_threshold_percent", sa.Integer(), nullable=False, server_default="80"),
            sa.Column("critical_threshold_percent", sa.Integer(), nullable=False, server_default="95"),
            sa.Column("alert_emails", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("last_warning_sent_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_critical_sent_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
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
            sa.PrimaryKeyConstraint("id"),
        )

        # Create index on budget_type
        op.create_index(
            "ix_llm_budget_configs_budget_type",
            "llm_budget_configs",
            ["budget_type"],
        )

    # Create llm_budget_alerts table
    if not table_exists("llm_budget_alerts"):
        op.create_table(
            "llm_budget_alerts",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("budget_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("alert_type", sa.String(20), nullable=False),
            sa.Column("threshold_percent", sa.Integer(), nullable=False),
            sa.Column("current_usage_cents", sa.Integer(), nullable=False),
            sa.Column("budget_limit_cents", sa.Integer(), nullable=False),
            sa.Column("usage_percent", sa.Float(), nullable=False),
            sa.Column("recipients", postgresql.ARRAY(sa.String()), nullable=False),
            sa.Column("email_sent", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("email_error", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["budget_id"], ["llm_budget_configs.id"], ondelete="CASCADE"
            ),
        )

        # Create index on budget_id
        op.create_index(
            "ix_llm_budget_alerts_budget_id",
            "llm_budget_alerts",
            ["budget_id"],
        )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("llm_budget_alerts")
    op.drop_table("llm_budget_configs")
    op.drop_table("llm_usage_monthly_aggregates")

    # Drop indexes explicitly before dropping table
    op.execute("DROP INDEX IF EXISTS ix_llm_usage_daily")
    op.drop_table("llm_usage_records")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS budget_type")
    op.execute("DROP TYPE IF EXISTS llm_task_type")
    op.execute("DROP TYPE IF EXISTS llm_provider")
