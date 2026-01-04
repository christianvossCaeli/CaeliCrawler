"""Add purpose-based LLM configuration system.

This migration adds:
1. llm_purpose enum for LLM usage purposes (web_search, document_analysis, embeddings, etc.)
2. llm_provider enum for available LLM providers (serpapi, serper, azure_openai, openai, anthropic)
3. user_llm_config table for storing purpose-based configuration per user
4. Updates api_credential_type enum to include 'openai'

The new user_llm_config table allows users to configure different providers
for different purposes, rather than just storing provider credentials globally.

Revision ID: bm1234567954
Revises: bl1234567953
Create Date: 2026-01-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "bm1234567954"
down_revision: Union[str, None] = "bl1234567953"
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


def enum_value_exists(enum_name: str, value: str) -> bool:
    """Check if a value exists in a PostgreSQL enum."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text("""
            SELECT 1 FROM pg_enum e
            JOIN pg_type t ON e.enumtypid = t.oid
            WHERE t.typname = :enum_name AND e.enumlabel = :value
        """),
        {"enum_name": enum_name, "value": value},
    )
    return result.scalar() is not None


def upgrade() -> None:
    # 1. Add 'openai' to api_credential_type enum if not exists
    if enum_exists("api_credential_type") and not enum_value_exists("api_credential_type", "openai"):
        op.execute("ALTER TYPE api_credential_type ADD VALUE IF NOT EXISTS 'openai'")

    # 2. Create llm_purpose enum
    if not enum_exists("llm_purpose"):
        llm_purpose = postgresql.ENUM(
            "web_search",
            "document_analysis",
            "embeddings",
            "assistant",
            "plan_mode",
            "api_discovery",
            name="llm_purpose",
        )
        llm_purpose.create(op.get_bind())

    # 3. Create llm_provider enum
    if not enum_exists("llm_provider"):
        llm_provider = postgresql.ENUM(
            "serpapi",
            "serper",
            "azure_openai",
            "openai",
            "anthropic",
            name="llm_provider",
        )
        llm_provider.create(op.get_bind())

    # 4. Create user_llm_config table
    if not table_exists("user_llm_config"):
        op.create_table(
            "user_llm_config",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "purpose",
                postgresql.ENUM(
                    "web_search",
                    "document_analysis",
                    "embeddings",
                    "assistant",
                    "plan_mode",
                    "api_discovery",
                    name="llm_purpose",
                    create_type=False,
                ),
                nullable=False,
                comment="The purpose for which this configuration is used",
            ),
            sa.Column(
                "provider",
                postgresql.ENUM(
                    "serpapi",
                    "serper",
                    "azure_openai",
                    "openai",
                    "anthropic",
                    name="llm_provider",
                    create_type=False,
                ),
                nullable=False,
                comment="The provider to use for this purpose",
            ),
            sa.Column(
                "encrypted_data",
                sa.Text(),
                nullable=False,
                comment="Fernet-encrypted JSON containing provider-specific credentials",
            ),
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
            sa.Column(
                "last_used_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
            sa.Column(
                "last_error",
                sa.Text(),
                nullable=True,
                comment="Last error message for debugging",
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
        )

        # Add unique constraint: one configuration per user per purpose
        op.create_unique_constraint(
            "uq_user_llm_purpose",
            "user_llm_config",
            ["user_id", "purpose"],
        )

        # Add composite index for efficient lookups
        op.create_index(
            "ix_user_llm_config_user_purpose",
            "user_llm_config",
            ["user_id", "purpose"],
        )


def downgrade() -> None:
    # Drop user_llm_config table
    if table_exists("user_llm_config"):
        op.drop_index("ix_user_llm_config_user_purpose", table_name="user_llm_config")
        op.drop_table("user_llm_config")

    # Drop llm_provider enum
    if enum_exists("llm_provider"):
        llm_provider = postgresql.ENUM(
            "serpapi",
            "serper",
            "azure_openai",
            "openai",
            "anthropic",
            name="llm_provider",
        )
        llm_provider.drop(op.get_bind())

    # Drop llm_purpose enum
    if enum_exists("llm_purpose"):
        llm_purpose = postgresql.ENUM(
            "web_search",
            "document_analysis",
            "embeddings",
            "assistant",
            "plan_mode",
            "api_discovery",
            name="llm_purpose",
        )
        llm_purpose.drop(op.get_bind())

    # Note: We don't remove 'openai' from api_credential_type enum as it might be in use
