"""Model pricing database for accurate cost tracking.

This module provides a database-backed pricing system with:
- Manual price management for OpenAI/Anthropic (no official API)
- Automatic sync from Azure Retail Prices API
- Staleness warnings when prices are outdated
- Audit trail of price updates

Pricing is stored per 1M tokens to match industry standard.
"""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PricingProvider(str, Enum):
    """Providers for which we track pricing."""

    AZURE_OPENAI = "AZURE_OPENAI"
    OPENAI = "OPENAI"
    ANTHROPIC = "ANTHROPIC"


class PricingSource(str, Enum):
    """How the pricing data was obtained."""

    MANUAL = "MANUAL"  # Manually entered by admin
    AZURE_API = "AZURE_API"  # Fetched from Azure Retail Prices API
    OFFICIAL_DOCS = "OFFICIAL_DOCS"  # Copied from official documentation


# Official pricing page URLs for reference
OFFICIAL_PRICING_URLS = {
    PricingProvider.AZURE_OPENAI: "https://azure.microsoft.com/en-us/pricing/details/cognitive-services/openai-service/",
    PricingProvider.OPENAI: "https://openai.com/api/pricing/",
    PricingProvider.ANTHROPIC: "https://www.anthropic.com/pricing",
}


class ModelPricing(Base):
    """
    Stores pricing information for LLM models.

    Prices are stored per 1 million tokens (industry standard).
    Supports both input and output pricing as they differ.
    """

    __tablename__ = "model_pricing"
    __table_args__ = (
        UniqueConstraint("provider", "model_name", name="uq_provider_model"),
        Index("ix_model_pricing_provider", "provider"),
        Index("ix_model_pricing_model_name", "model_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Model identification
    provider: Mapped[PricingProvider] = mapped_column(
        SQLEnum(PricingProvider, name="pricing_provider", create_constraint=True),
        nullable=False,
    )
    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Model name/ID (e.g., gpt-4o, claude-opus-4-5)",
    )
    display_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Human-readable name for UI display",
    )

    # Pricing per 1M tokens (USD)
    input_price_per_1m: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Price per 1M input tokens in USD",
    )
    output_price_per_1m: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Price per 1M output tokens in USD",
    )

    # Optional: Cached input pricing (some providers offer this)
    cached_input_price_per_1m: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Price per 1M cached input tokens in USD (if applicable)",
    )

    # Data source and freshness
    source: Mapped[PricingSource] = mapped_column(
        SQLEnum(PricingSource, name="pricing_source", create_constraint=True),
        nullable=False,
        default=PricingSource.MANUAL,
    )
    source_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="URL where the pricing was obtained from",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether this model is currently available",
    )
    is_deprecated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether this model is deprecated",
    )

    # Audit fields
    last_verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When the price was last verified as accurate",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Notes for admins
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Admin notes about this pricing entry",
    )

    def __repr__(self) -> str:
        return (
            f"<ModelPricing(provider={self.provider.value}, "
            f"model={self.model_name}, "
            f"input=${self.input_price_per_1m}/1M, "
            f"output=${self.output_price_per_1m}/1M)>"
        )

    @property
    def is_stale(self) -> bool:
        """Check if pricing data is older than 30 days."""
        from datetime import timedelta

        return datetime.now(self.last_verified_at.tzinfo) - self.last_verified_at > timedelta(days=30)

    @property
    def days_since_verified(self) -> int:
        """Number of days since last verification."""
        from datetime import timezone

        now = datetime.now(timezone.utc)
        if self.last_verified_at.tzinfo is None:
            # Assume UTC if no timezone
            verified = self.last_verified_at.replace(tzinfo=timezone.utc)
        else:
            verified = self.last_verified_at
        return (now - verified).days

    def calculate_cost_cents(self, input_tokens: int, output_tokens: int) -> int:
        """Calculate estimated cost in USD cents."""
        input_cost = (input_tokens / 1_000_000) * self.input_price_per_1m
        output_cost = (output_tokens / 1_000_000) * self.output_price_per_1m
        total_cents = (input_cost + output_cost) * 100
        return int(total_cents + 0.5)  # Round to nearest cent


# Default pricing data (fallback when database is empty)
# Last updated: January 2025
# Sources: Official pricing pages
DEFAULT_PRICING = [
    # OpenAI Models
    {
        "provider": PricingProvider.OPENAI,
        "model_name": "gpt-4o",
        "display_name": "GPT-4o",
        "input_price_per_1m": 2.50,
        "output_price_per_1m": 10.00,
        "source": PricingSource.OFFICIAL_DOCS,
        "source_url": "https://openai.com/api/pricing/",
    },
    {
        "provider": PricingProvider.OPENAI,
        "model_name": "gpt-4o-mini",
        "display_name": "GPT-4o Mini",
        "input_price_per_1m": 0.15,
        "output_price_per_1m": 0.60,
        "source": PricingSource.OFFICIAL_DOCS,
        "source_url": "https://openai.com/api/pricing/",
    },
    {
        "provider": PricingProvider.OPENAI,
        "model_name": "gpt-4.1",
        "display_name": "GPT-4.1",
        "input_price_per_1m": 2.00,
        "output_price_per_1m": 8.00,
        "source": PricingSource.OFFICIAL_DOCS,
        "source_url": "https://openai.com/api/pricing/",
    },
    {
        "provider": PricingProvider.OPENAI,
        "model_name": "gpt-4.1-mini",
        "display_name": "GPT-4.1 Mini",
        "input_price_per_1m": 0.40,
        "output_price_per_1m": 1.60,
        "source": PricingSource.OFFICIAL_DOCS,
        "source_url": "https://openai.com/api/pricing/",
    },
    {
        "provider": PricingProvider.OPENAI,
        "model_name": "gpt-4.1-nano",
        "display_name": "GPT-4.1 Nano",
        "input_price_per_1m": 0.10,
        "output_price_per_1m": 0.40,
        "source": PricingSource.OFFICIAL_DOCS,
        "source_url": "https://openai.com/api/pricing/",
    },
    {
        "provider": PricingProvider.OPENAI,
        "model_name": "o1",
        "display_name": "o1",
        "input_price_per_1m": 15.00,
        "output_price_per_1m": 60.00,
        "source": PricingSource.OFFICIAL_DOCS,
        "source_url": "https://openai.com/api/pricing/",
    },
    {
        "provider": PricingProvider.OPENAI,
        "model_name": "o1-mini",
        "display_name": "o1 Mini",
        "input_price_per_1m": 1.10,
        "output_price_per_1m": 4.40,
        "source": PricingSource.OFFICIAL_DOCS,
        "source_url": "https://openai.com/api/pricing/",
    },
    {
        "provider": PricingProvider.OPENAI,
        "model_name": "o3-mini",
        "display_name": "o3 Mini",
        "input_price_per_1m": 1.10,
        "output_price_per_1m": 4.40,
        "source": PricingSource.OFFICIAL_DOCS,
        "source_url": "https://openai.com/api/pricing/",
    },
    {
        "provider": PricingProvider.OPENAI,
        "model_name": "text-embedding-3-large",
        "display_name": "Embedding 3 Large",
        "input_price_per_1m": 0.13,
        "output_price_per_1m": 0.0,
        "source": PricingSource.OFFICIAL_DOCS,
        "source_url": "https://openai.com/api/pricing/",
    },
    {
        "provider": PricingProvider.OPENAI,
        "model_name": "text-embedding-3-small",
        "display_name": "Embedding 3 Small",
        "input_price_per_1m": 0.02,
        "output_price_per_1m": 0.0,
        "source": PricingSource.OFFICIAL_DOCS,
        "source_url": "https://openai.com/api/pricing/",
    },
    # Anthropic Models
    {
        "provider": PricingProvider.ANTHROPIC,
        "model_name": "claude-opus-4-5",
        "display_name": "Claude Opus 4.5",
        "input_price_per_1m": 15.00,
        "output_price_per_1m": 75.00,
        "source": PricingSource.OFFICIAL_DOCS,
        "source_url": "https://www.anthropic.com/pricing",
    },
    {
        "provider": PricingProvider.ANTHROPIC,
        "model_name": "claude-sonnet-4",
        "display_name": "Claude Sonnet 4",
        "input_price_per_1m": 3.00,
        "output_price_per_1m": 15.00,
        "source": PricingSource.OFFICIAL_DOCS,
        "source_url": "https://www.anthropic.com/pricing",
    },
    {
        "provider": PricingProvider.ANTHROPIC,
        "model_name": "claude-3-5-sonnet",
        "display_name": "Claude 3.5 Sonnet",
        "input_price_per_1m": 3.00,
        "output_price_per_1m": 15.00,
        "source": PricingSource.OFFICIAL_DOCS,
        "source_url": "https://www.anthropic.com/pricing",
    },
    {
        "provider": PricingProvider.ANTHROPIC,
        "model_name": "claude-3-5-haiku",
        "display_name": "Claude 3.5 Haiku",
        "input_price_per_1m": 0.80,
        "output_price_per_1m": 4.00,
        "source": PricingSource.OFFICIAL_DOCS,
        "source_url": "https://www.anthropic.com/pricing",
    },
    {
        "provider": PricingProvider.ANTHROPIC,
        "model_name": "claude-3-opus",
        "display_name": "Claude 3 Opus",
        "input_price_per_1m": 15.00,
        "output_price_per_1m": 75.00,
        "source": PricingSource.OFFICIAL_DOCS,
        "source_url": "https://www.anthropic.com/pricing",
    },
    {
        "provider": PricingProvider.ANTHROPIC,
        "model_name": "claude-3-haiku",
        "display_name": "Claude 3 Haiku",
        "input_price_per_1m": 0.25,
        "output_price_per_1m": 1.25,
        "source": PricingSource.OFFICIAL_DOCS,
        "source_url": "https://www.anthropic.com/pricing",
    },
    # Azure OpenAI (same pricing as OpenAI for most models)
    {
        "provider": PricingProvider.AZURE_OPENAI,
        "model_name": "gpt-4o",
        "display_name": "GPT-4o (Azure)",
        "input_price_per_1m": 2.50,
        "output_price_per_1m": 10.00,
        "source": PricingSource.AZURE_API,
        "source_url": "https://azure.microsoft.com/en-us/pricing/details/cognitive-services/openai-service/",
    },
    {
        "provider": PricingProvider.AZURE_OPENAI,
        "model_name": "gpt-4o-mini",
        "display_name": "GPT-4o Mini (Azure)",
        "input_price_per_1m": 0.15,
        "output_price_per_1m": 0.60,
        "source": PricingSource.AZURE_API,
        "source_url": "https://azure.microsoft.com/en-us/pricing/details/cognitive-services/openai-service/",
    },
    {
        "provider": PricingProvider.AZURE_OPENAI,
        "model_name": "gpt-4.1",
        "display_name": "GPT-4.1 (Azure)",
        "input_price_per_1m": 2.00,
        "output_price_per_1m": 8.00,
        "source": PricingSource.AZURE_API,
        "source_url": "https://azure.microsoft.com/en-us/pricing/details/cognitive-services/openai-service/",
    },
    {
        "provider": PricingProvider.AZURE_OPENAI,
        "model_name": "gpt-4.1-mini",
        "display_name": "GPT-4.1 Mini (Azure)",
        "input_price_per_1m": 0.40,
        "output_price_per_1m": 1.60,
        "source": PricingSource.AZURE_API,
        "source_url": "https://azure.microsoft.com/en-us/pricing/details/cognitive-services/openai-service/",
    },
    {
        "provider": PricingProvider.AZURE_OPENAI,
        "model_name": "text-embedding-3-large",
        "display_name": "Embedding 3 Large (Azure)",
        "input_price_per_1m": 0.13,
        "output_price_per_1m": 0.0,
        "source": PricingSource.AZURE_API,
        "source_url": "https://azure.microsoft.com/en-us/pricing/details/cognitive-services/openai-service/",
    },
]
