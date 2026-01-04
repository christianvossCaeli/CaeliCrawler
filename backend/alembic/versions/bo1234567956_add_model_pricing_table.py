"""Add model_pricing table for accurate cost tracking.

This migration creates a database-backed pricing system with:
- Support for multiple providers (Azure OpenAI, OpenAI, Anthropic)
- Manual and automatic price management
- Staleness tracking and audit fields

Revision ID: bo1234567956
Revises: bn1234567955
Create Date: 2026-01-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "bo1234567956"
down_revision: Union[str, None] = "bn1234567955"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists."""
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    return table_name in inspector.get_table_names()


def enum_exists(enum_name: str) -> bool:
    """Check if a PostgreSQL enum type exists."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = :enum_name"),
        {"enum_name": enum_name},
    )
    return result.scalar() is not None


def upgrade() -> None:
    # Create pricing_provider enum
    if not enum_exists("pricing_provider"):
        pricing_provider = postgresql.ENUM(
            "azure_openai",
            "openai",
            "anthropic",
            name="pricing_provider",
        )
        pricing_provider.create(op.get_bind())

    # Create pricing_source enum
    if not enum_exists("pricing_source"):
        pricing_source = postgresql.ENUM(
            "manual",
            "azure_api",
            "official_docs",
            name="pricing_source",
        )
        pricing_source.create(op.get_bind())

    # Create model_pricing table
    if not table_exists("model_pricing"):
        op.create_table(
            "model_pricing",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            # Model identification
            sa.Column(
                "provider",
                postgresql.ENUM(
                    "azure_openai",
                    "openai",
                    "anthropic",
                    name="pricing_provider",
                    create_type=False,
                ),
                nullable=False,
            ),
            sa.Column(
                "model_name",
                sa.String(100),
                nullable=False,
                comment="Model name/ID (e.g., gpt-4o, claude-opus-4-5)",
            ),
            sa.Column(
                "display_name",
                sa.String(100),
                nullable=True,
                comment="Human-readable name for UI display",
            ),
            # Pricing per 1M tokens (USD)
            sa.Column(
                "input_price_per_1m",
                sa.Float(),
                nullable=False,
                comment="Price per 1M input tokens in USD",
            ),
            sa.Column(
                "output_price_per_1m",
                sa.Float(),
                nullable=False,
                comment="Price per 1M output tokens in USD",
            ),
            sa.Column(
                "cached_input_price_per_1m",
                sa.Float(),
                nullable=True,
                comment="Price per 1M cached input tokens in USD",
            ),
            # Data source
            sa.Column(
                "source",
                postgresql.ENUM(
                    "manual",
                    "azure_api",
                    "official_docs",
                    name="pricing_source",
                    create_type=False,
                ),
                nullable=False,
                server_default="manual",
            ),
            sa.Column(
                "source_url",
                sa.Text(),
                nullable=True,
                comment="URL where the pricing was obtained from",
            ),
            # Status
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
            sa.Column(
                "is_deprecated",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            # Audit fields
            sa.Column(
                "last_verified_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
                comment="When the price was last verified as accurate",
            ),
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
                onupdate=sa.func.now(),
            ),
            sa.Column(
                "notes",
                sa.Text(),
                nullable=True,
                comment="Admin notes about this pricing entry",
            ),
        )

        # Unique constraint: one price per provider/model combination
        op.create_unique_constraint(
            "uq_provider_model",
            "model_pricing",
            ["provider", "model_name"],
        )

        # Indexes for efficient lookups
        op.create_index(
            "ix_model_pricing_provider",
            "model_pricing",
            ["provider"],
        )
        op.create_index(
            "ix_model_pricing_model_name",
            "model_pricing",
            ["model_name"],
        )


def downgrade() -> None:
    if table_exists("model_pricing"):
        op.drop_index("ix_model_pricing_model_name", table_name="model_pricing")
        op.drop_index("ix_model_pricing_provider", table_name="model_pricing")
        op.drop_table("model_pricing")

    if enum_exists("pricing_source"):
        pricing_source = postgresql.ENUM(
            "manual",
            "azure_api",
            "official_docs",
            name="pricing_source",
        )
        pricing_source.drop(op.get_bind())

    if enum_exists("pricing_provider"):
        pricing_provider = postgresql.ENUM(
            "azure_openai",
            "openai",
            "anthropic",
            name="pricing_provider",
        )
        pricing_provider.drop(op.get_bind())
