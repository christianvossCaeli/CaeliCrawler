"""Service for managing and retrieving model pricing.

Provides:
- Database-backed pricing with fallback to defaults
- Fuzzy matching for model names (deployment names may differ)
- Azure Retail Prices API integration for automatic sync
- LiteLLM community pricing database sync
- Staleness detection and warnings
"""

import re
from datetime import UTC, datetime
from typing import TypedDict

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.model_pricing import (
    DEFAULT_PRICING,
    ModelPricing,
    PricingProvider,
    PricingSource,
)

# LiteLLM pricing database URL (community-maintained, 1000+ models)
LITELLM_PRICING_URL = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"

# Mapping from LiteLLM provider names to our PricingProvider enum
LITELLM_PROVIDER_MAP: dict[str, PricingProvider] = {
    "openai": PricingProvider.OPENAI,
    "azure": PricingProvider.AZURE_OPENAI,
    "azure_ai": PricingProvider.AZURE_OPENAI,
    "anthropic": PricingProvider.ANTHROPIC,
}

logger = structlog.get_logger(__name__)


class PricingInfo(TypedDict):
    """Pricing information for a model."""

    provider: str
    model_name: str
    display_name: str | None
    input_price_per_1m: float
    output_price_per_1m: float
    cached_input_price_per_1m: float | None
    source: str
    source_url: str | None
    last_verified_at: str | None
    is_stale: bool
    days_since_verified: int | None


class ModelPricingService:
    """Service for model pricing operations."""

    # Cache for pricing data (refreshed on each request to DB)
    _cache: dict[str, PricingInfo] = {}
    _cache_loaded: bool = False

    @classmethod
    async def get_pricing(
        cls,
        session: AsyncSession,
        provider: str,
        model_name: str,
    ) -> PricingInfo | None:
        """
        Get pricing for a specific model.

        Uses fuzzy matching to handle deployment names that differ from model names.
        Falls back to default pricing if not found in database.

        Args:
            session: Database session
            provider: Provider name (azure_openai, openai, anthropic)
            model_name: Model name or deployment name

        Returns:
            PricingInfo dict or None if not found
        """
        # Try exact match first
        pricing = await cls._get_from_db(session, provider, model_name)
        if pricing:
            return cls._to_pricing_info(pricing)

        # Try fuzzy match
        pricing = await cls._fuzzy_match(session, provider, model_name)
        if pricing:
            return cls._to_pricing_info(pricing)

        # Fall back to defaults
        return cls._get_from_defaults(provider, model_name)

    @classmethod
    async def get_all_pricing(
        cls,
        session: AsyncSession,
        provider: str | None = None,
        include_deprecated: bool = False,
    ) -> list[PricingInfo]:
        """Get all pricing entries, optionally filtered by provider."""
        query = select(ModelPricing).where(ModelPricing.is_active.is_(True))

        if provider:
            try:
                provider_enum = PricingProvider(provider)
                query = query.where(ModelPricing.provider == provider_enum)
            except ValueError:
                pass

        if not include_deprecated:
            query = query.where(ModelPricing.is_deprecated.is_(False))

        query = query.order_by(ModelPricing.provider, ModelPricing.model_name)

        result = await session.execute(query)
        return [cls._to_pricing_info(p) for p in result.scalars().all()]

    @classmethod
    async def calculate_cost_cents(
        cls,
        session: AsyncSession,
        provider: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
    ) -> tuple[int, PricingInfo | None]:
        """
        Calculate cost in USD cents for a model usage.

        Returns:
            Tuple of (cost_cents, pricing_info)
        """
        pricing = await cls.get_pricing(session, provider, model_name)
        if not pricing:
            # Use hardcoded fallback
            return cls._calculate_fallback_cost(input_tokens, output_tokens), None

        input_cost = (input_tokens / 1_000_000) * pricing["input_price_per_1m"]
        output_cost = (output_tokens / 1_000_000) * pricing["output_price_per_1m"]
        total_cents = (input_cost + output_cost) * 100
        return int(total_cents + 0.5), pricing

    @classmethod
    async def upsert_pricing(
        cls,
        session: AsyncSession,
        provider: str,
        model_name: str,
        input_price_per_1m: float,
        output_price_per_1m: float,
        display_name: str | None = None,
        cached_input_price_per_1m: float | None = None,
        source: str = "manual",
        source_url: str | None = None,
        notes: str | None = None,
    ) -> ModelPricing:
        """Create or update pricing for a model."""
        try:
            provider_enum = PricingProvider(provider)
        except ValueError:
            raise ValueError(f"Invalid provider: {provider}") from None

        try:
            source_enum = PricingSource(source)
        except ValueError:
            source_enum = PricingSource.MANUAL

        # Check if exists
        result = await session.execute(
            select(ModelPricing).where(
                ModelPricing.provider == provider_enum,
                ModelPricing.model_name == model_name,
            )
        )
        pricing = result.scalar_one_or_none()

        now = datetime.now(UTC)

        if pricing:
            # Update existing
            pricing.input_price_per_1m = input_price_per_1m
            pricing.output_price_per_1m = output_price_per_1m
            if display_name:
                pricing.display_name = display_name
            pricing.cached_input_price_per_1m = cached_input_price_per_1m
            pricing.source = source_enum
            pricing.source_url = source_url
            pricing.last_verified_at = now
            if notes:
                pricing.notes = notes
        else:
            # Create new
            pricing = ModelPricing(
                provider=provider_enum,
                model_name=model_name,
                display_name=display_name,
                input_price_per_1m=input_price_per_1m,
                output_price_per_1m=output_price_per_1m,
                cached_input_price_per_1m=cached_input_price_per_1m,
                source=source_enum,
                source_url=source_url,
                last_verified_at=now,
                notes=notes,
            )
            session.add(pricing)

        await session.flush()
        return pricing

    @classmethod
    async def seed_default_pricing(cls, session: AsyncSession) -> int:
        """Seed default pricing data if table is empty."""
        result = await session.execute(select(ModelPricing).limit(1))
        if result.scalar_one_or_none():
            logger.info("model_pricing_already_seeded")
            return 0

        count = 0
        for entry in DEFAULT_PRICING:
            await cls.upsert_pricing(
                session=session,
                provider=entry["provider"].value,
                model_name=entry["model_name"],
                display_name=entry.get("display_name"),
                input_price_per_1m=entry["input_price_per_1m"],
                output_price_per_1m=entry["output_price_per_1m"],
                source=entry["source"].value,
                source_url=entry.get("source_url"),
            )
            count += 1

        await session.commit()
        logger.info("model_pricing_seeded", count=count)
        return count

    @classmethod
    async def sync_azure_prices(cls, session: AsyncSession) -> dict:
        """
        Sync Azure OpenAI prices from Azure Retail Prices API.

        Returns:
            Dict with sync results (updated, added, errors)
        """
        results = {"updated": 0, "added": 0, "errors": []}

        try:
            # Fetch Azure OpenAI prices
            prices = await cls._fetch_azure_prices()

            for model_name, pricing_data in prices.items():
                try:
                    await cls.upsert_pricing(
                        session=session,
                        provider="azure_openai",
                        model_name=model_name,
                        display_name=pricing_data.get("display_name"),
                        input_price_per_1m=pricing_data["input"],
                        output_price_per_1m=pricing_data["output"],
                        source="azure_api",
                        source_url="https://prices.azure.com/api/retail/prices",
                    )
                    results["updated"] += 1
                except Exception as e:
                    results["errors"].append(f"{model_name}: {str(e)}")

            await session.commit()
            logger.info("azure_prices_synced", **results)

        except Exception as e:
            logger.error("azure_price_sync_failed", error=str(e))
            results["errors"].append(f"API fetch failed: {str(e)}")

        return results

    @classmethod
    async def _fetch_azure_prices(cls) -> dict[str, dict]:
        """Fetch and parse Azure OpenAI prices from retail API."""
        prices: dict[str, dict] = {}
        next_url = "https://prices.azure.com/api/retail/prices?$filter=productName eq 'Azure OpenAI'"

        async with httpx.AsyncClient(timeout=30) as client:
            while next_url:
                response = await client.get(next_url)
                response.raise_for_status()
                data = response.json()

                for item in data.get("Items", []):
                    meter_name = item.get("meterName", "")
                    unit_price = item.get("retailPrice", 0)
                    unit = item.get("unitOfMeasure", "")

                    # Parse model name from meter name
                    model_info = cls._parse_azure_meter_name(meter_name)
                    if not model_info:
                        continue

                    model_name = model_info["model"]
                    token_type = model_info["type"]  # "input" or "output"

                    # Convert to per 1M tokens if needed
                    if "1K" in unit:
                        price_per_1m = unit_price * 1000
                    elif "1M" in unit:
                        price_per_1m = unit_price
                    else:
                        continue

                    # Initialize or update price entry
                    if model_name not in prices:
                        prices[model_name] = {
                            "input": 0.0,
                            "output": 0.0,
                            "display_name": model_info.get("display_name"),
                        }

                    prices[model_name][token_type] = price_per_1m

                next_url = data.get("NextPageLink")

        return prices

    @classmethod
    def _parse_azure_meter_name(cls, meter_name: str) -> dict | None:
        """
        Parse Azure meter name to extract model and token type.

        Examples:
            "gpt-4o Inp glbl Tokens" -> {"model": "gpt-4o", "type": "input"}
            "gpt-4.1-mini Outp regnl Tokens" -> {"model": "gpt-4.1-mini", "type": "output"}
        """
        if not meter_name or "Tokens" not in meter_name:
            return None

        # Determine token type
        token_type = "input" if "Inp" in meter_name else "output" if "Outp" in meter_name else None
        if not token_type:
            return None

        # Extract model name (everything before Inp/Outp)
        match = re.match(r"^([\w\-\.]+)\s+(?:Inp|Outp)", meter_name)
        if not match:
            return None

        model_name = match.group(1).lower().strip()

        # Normalize common patterns
        model_name = model_name.replace(" ", "-")

        return {
            "model": model_name,
            "type": token_type,
            "display_name": model_name.upper().replace("-", " "),
        }

    @classmethod
    async def _get_from_db(
        cls,
        session: AsyncSession,
        provider: str,
        model_name: str,
    ) -> ModelPricing | None:
        """Get exact match from database."""
        try:
            provider_enum = PricingProvider(provider)
        except ValueError:
            return None

        result = await session.execute(
            select(ModelPricing).where(
                ModelPricing.provider == provider_enum,
                ModelPricing.model_name == model_name,
                ModelPricing.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    @classmethod
    async def _fuzzy_match(
        cls,
        session: AsyncSession,
        provider: str,
        model_name: str,
    ) -> ModelPricing | None:
        """
        Try fuzzy matching for model names.

        Handles cases like:
        - Deployment names: "my-gpt-4o-deployment" -> "gpt-4o"
        - Version suffixes: "claude-3-5-sonnet-20240620" -> "claude-3-5-sonnet"
        """
        try:
            provider_enum = PricingProvider(provider)
        except ValueError:
            return None

        # Get all active models for this provider
        result = await session.execute(
            select(ModelPricing).where(
                ModelPricing.provider == provider_enum,
                ModelPricing.is_active.is_(True),
            )
        )
        all_models = result.scalars().all()

        model_lower = model_name.lower()

        # Try to find a match
        for pricing in all_models:
            db_model = pricing.model_name.lower()
            # Check if DB model is contained in the provided name
            if db_model in model_lower:
                return pricing
            # Check if provided name is contained in DB model
            if model_lower in db_model:
                return pricing

        return None

    @classmethod
    def _get_from_defaults(cls, provider: str, model_name: str) -> PricingInfo | None:
        """Get pricing from hardcoded defaults."""
        try:
            provider_enum = PricingProvider(provider)
        except ValueError:
            return None

        model_lower = model_name.lower()

        # Try exact match first
        for entry in DEFAULT_PRICING:
            if entry["provider"] == provider_enum and entry["model_name"].lower() == model_lower:
                return cls._default_to_pricing_info(entry)

        # Try fuzzy match
        for entry in DEFAULT_PRICING:
            if entry["provider"] != provider_enum:
                continue
            db_model = entry["model_name"].lower()
            if db_model in model_lower or model_lower in db_model:
                return cls._default_to_pricing_info(entry)

        return None

    @classmethod
    def _to_pricing_info(cls, pricing: ModelPricing) -> PricingInfo:
        """Convert ModelPricing to PricingInfo dict."""
        return PricingInfo(
            provider=pricing.provider.value,
            model_name=pricing.model_name,
            display_name=pricing.display_name,
            input_price_per_1m=pricing.input_price_per_1m,
            output_price_per_1m=pricing.output_price_per_1m,
            cached_input_price_per_1m=pricing.cached_input_price_per_1m,
            source=pricing.source.value,
            source_url=pricing.source_url,
            last_verified_at=pricing.last_verified_at.isoformat() if pricing.last_verified_at else None,
            is_stale=pricing.is_stale,
            days_since_verified=pricing.days_since_verified,
        )

    @classmethod
    def _default_to_pricing_info(cls, entry: dict) -> PricingInfo:
        """Convert default dict to PricingInfo."""
        return PricingInfo(
            provider=entry["provider"].value,
            model_name=entry["model_name"],
            display_name=entry.get("display_name"),
            input_price_per_1m=entry["input_price_per_1m"],
            output_price_per_1m=entry["output_price_per_1m"],
            cached_input_price_per_1m=None,
            source=entry["source"].value,
            source_url=entry.get("source_url"),
            last_verified_at=None,
            is_stale=True,  # Defaults are always considered stale
            days_since_verified=None,
        )

    @classmethod
    def _calculate_fallback_cost(cls, input_tokens: int, output_tokens: int) -> int:
        """Calculate cost using hardcoded fallback rates."""
        # Fallback: $1.00 input, $3.00 output per 1M tokens
        input_cost = (input_tokens / 1_000_000) * 1.00
        output_cost = (output_tokens / 1_000_000) * 3.00
        total_cents = (input_cost + output_cost) * 100
        return int(total_cents + 0.5)

    @classmethod
    async def _sync_provider_from_defaults(
        cls,
        session: AsyncSession,
        provider: PricingProvider,
        default_source_url: str,
    ) -> dict:
        """
        Sync prices for a provider from predefined defaults.

        Generic method to avoid code duplication for OpenAI/Anthropic sync.

        Args:
            session: Database session
            provider: The provider to sync
            default_source_url: Default URL if not specified in defaults

        Returns:
            Dict with sync results (updated, added, errors)
        """
        results: dict = {"updated": 0, "added": 0, "errors": []}

        try:
            for entry in DEFAULT_PRICING:
                if entry["provider"] != provider:
                    continue

                try:
                    await cls.upsert_pricing(
                        session=session,
                        provider=entry["provider"].value,
                        model_name=entry["model_name"],
                        display_name=entry.get("display_name"),
                        input_price_per_1m=entry["input_price_per_1m"],
                        output_price_per_1m=entry["output_price_per_1m"],
                        source="official_docs",
                        source_url=entry.get("source_url", default_source_url),
                    )
                    results["updated"] += 1
                except Exception as e:
                    results["errors"].append(f"{entry['model_name']}: {str(e)}")

            await session.commit()
            logger.info(f"{provider.value}_prices_synced", **results)

        except Exception as e:
            logger.error(f"{provider.value}_price_sync_failed", error=str(e))
            results["errors"].append(f"Sync failed: {str(e)}")

        return results

    @classmethod
    async def sync_openai_prices(cls, session: AsyncSession) -> dict:
        """
        Sync OpenAI prices from predefined defaults.

        Since OpenAI doesn't provide a public pricing API, we use
        the latest manually curated prices from their pricing page.

        Returns:
            Dict with sync results (updated, added, errors)
        """
        return await cls._sync_provider_from_defaults(
            session=session,
            provider=PricingProvider.OPENAI,
            default_source_url="https://openai.com/api/pricing/",
        )

    @classmethod
    async def sync_anthropic_prices(cls, session: AsyncSession) -> dict:
        """
        Sync Anthropic prices from predefined defaults.

        Since Anthropic doesn't provide a public pricing API, we use
        the latest manually curated prices from their pricing page.

        Returns:
            Dict with sync results (updated, added, errors)
        """
        return await cls._sync_provider_from_defaults(
            session=session,
            provider=PricingProvider.ANTHROPIC,
            default_source_url="https://www.anthropic.com/pricing",
        )

    @classmethod
    async def sync_all_prices(cls, session: AsyncSession) -> dict:
        """
        Sync prices from all providers.

        Returns:
            Dict with combined sync results
        """
        all_results = {
            "azure_openai": {"updated": 0, "added": 0, "errors": []},
            "openai": {"updated": 0, "added": 0, "errors": []},
            "anthropic": {"updated": 0, "added": 0, "errors": []},
            "total_updated": 0,
            "total_added": 0,
            "total_errors": 0,
        }

        # Sync each provider
        azure_result = await cls.sync_azure_prices(session)
        openai_result = await cls.sync_openai_prices(session)
        anthropic_result = await cls.sync_anthropic_prices(session)

        all_results["azure_openai"] = azure_result
        all_results["openai"] = openai_result
        all_results["anthropic"] = anthropic_result
        all_results["total_updated"] = azure_result["updated"] + openai_result["updated"] + anthropic_result["updated"]
        all_results["total_added"] = azure_result["added"] + openai_result["added"] + anthropic_result["added"]
        all_results["total_errors"] = (
            len(azure_result["errors"]) + len(openai_result["errors"]) + len(anthropic_result["errors"])
        )

        # Refresh the pricing cache after sync
        try:
            from services.llm_usage_tracker import refresh_pricing_cache

            await refresh_pricing_cache()
        except Exception as e:
            logger.warning("pricing_cache_refresh_after_sync_failed", error=str(e))

        logger.info(
            "all_prices_synced",
            total_updated=all_results["total_updated"],
            total_errors=all_results["total_errors"],
        )

        return all_results

    @classmethod
    async def sync_from_litellm(
        cls,
        session: AsyncSession,
        providers: list[str] | None = None,
    ) -> dict:
        """
        Sync prices from LiteLLM community pricing database.

        This fetches the comprehensive model_prices_and_context_window.json
        from the LiteLLM GitHub repository which contains 1000+ models
        across all major providers.

        Args:
            session: Database session
            providers: Optional list of providers to sync (default: openai, anthropic)
                      Valid values: 'openai', 'anthropic', 'azure_openai'

        Returns:
            Dict with sync results per provider
        """
        if providers is None:
            providers = ["openai", "anthropic"]

        results: dict = {
            "updated": 0,
            "added": 0,
            "skipped": 0,
            "errors": [],
            "providers_synced": providers,
        }

        try:
            # Fetch LiteLLM pricing data
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(LITELLM_PRICING_URL)
                response.raise_for_status()
                litellm_data = response.json()

            logger.info("litellm_data_fetched", model_count=len(litellm_data))

            # Process each model
            for model_key, model_data in litellm_data.items():
                try:
                    # Skip if no pricing data
                    input_cost = model_data.get("input_cost_per_token")
                    output_cost = model_data.get("output_cost_per_token")
                    if input_cost is None or output_cost is None:
                        continue

                    # Get provider and check if we should sync it
                    litellm_provider = model_data.get("litellm_provider", "")
                    our_provider = LITELLM_PROVIDER_MAP.get(litellm_provider)

                    if our_provider is None:
                        continue

                    # Check if this provider is in our sync list
                    provider_key = our_provider.value
                    if provider_key not in providers and litellm_provider not in providers:
                        continue

                    # Clean up model name (remove provider prefixes like "azure/")
                    model_name = model_key
                    if "/" in model_name:
                        model_name = model_name.split("/")[-1]

                    # Skip deployment-specific names (contain dates like -2024-)
                    # but keep version suffixes like -20241022
                    if model_name.startswith("ft:"):
                        continue  # Skip fine-tuned models

                    # Convert from per-token to per-1M-tokens
                    input_price_per_1m = float(input_cost) * 1_000_000
                    output_price_per_1m = float(output_cost) * 1_000_000

                    # Get cached input price if available
                    cached_input_cost = model_data.get("cache_read_input_token_cost")
                    cached_input_per_1m = (
                        float(cached_input_cost) * 1_000_000 if cached_input_cost is not None else None
                    )

                    # Create display name from model key
                    display_name = model_name.replace("-", " ").title()

                    # Upsert the pricing
                    await cls.upsert_pricing(
                        session=session,
                        provider=our_provider.value,
                        model_name=model_name,
                        display_name=display_name,
                        input_price_per_1m=input_price_per_1m,
                        output_price_per_1m=output_price_per_1m,
                        cached_input_price_per_1m=cached_input_per_1m,
                        source="official_docs",
                        source_url=LITELLM_PRICING_URL,
                        notes="Synced from LiteLLM community database",
                    )
                    results["updated"] += 1

                except Exception as e:
                    results["errors"].append(f"{model_key}: {str(e)}")

            await session.commit()

            # Refresh the pricing cache
            try:
                from services.llm_usage_tracker import refresh_pricing_cache

                await refresh_pricing_cache()
            except Exception as e:
                logger.warning("pricing_cache_refresh_after_litellm_sync_failed", error=str(e))

            logger.info(
                "litellm_prices_synced",
                updated=results["updated"],
                errors=len(results["errors"]),
            )

        except httpx.HTTPError as e:
            error_msg = f"Failed to fetch LiteLLM data: {str(e)}"
            logger.error("litellm_fetch_failed", error=str(e))
            results["errors"].append(error_msg)
        except Exception as e:
            error_msg = f"LiteLLM sync failed: {str(e)}"
            logger.error("litellm_sync_failed", error=str(e))
            results["errors"].append(error_msg)

        return results
