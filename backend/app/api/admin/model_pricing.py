"""Admin API for managing model pricing.

Endpoints for viewing, updating, and syncing model pricing data.
Only accessible by admins.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.core.exceptions import NotFoundError
from app.database import get_session
from app.models import User
from app.models.audit_log import AuditAction
from app.models.model_pricing import OFFICIAL_PRICING_URLS, ModelPricing, PricingProvider
from app.services.audit_service import create_audit_log

logger = structlog.get_logger()
router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================


class PricingEntry(BaseModel):
    """Single pricing entry for response."""

    id: str
    provider: str
    model_name: str
    display_name: str | None
    input_price_per_1m: float
    output_price_per_1m: float
    cached_input_price_per_1m: float | None
    source: str
    source_url: str | None
    is_active: bool
    is_deprecated: bool
    is_stale: bool
    days_since_verified: int
    last_verified_at: str | None
    notes: str | None


class PricingListResponse(BaseModel):
    """List of all pricing entries."""

    entries: list[PricingEntry]
    total: int
    stale_count: int
    official_urls: dict[str, str]


class UpdatePricingRequest(BaseModel):
    """Request to update pricing for a model."""

    input_price_per_1m: float = Field(..., ge=0, description="Price per 1M input tokens in USD")
    output_price_per_1m: float = Field(..., ge=0, description="Price per 1M output tokens in USD")
    cached_input_price_per_1m: float | None = Field(None, ge=0)
    display_name: str | None = None
    notes: str | None = None


class CreatePricingRequest(BaseModel):
    """Request to create a new pricing entry."""

    provider: str = Field(..., description="Provider: azure_openai, openai, anthropic")
    model_name: str = Field(..., min_length=1, max_length=100)
    display_name: str | None = None
    input_price_per_1m: float = Field(..., ge=0)
    output_price_per_1m: float = Field(..., ge=0)
    cached_input_price_per_1m: float | None = Field(None, ge=0)
    source_url: str | None = None
    notes: str | None = None


class SyncResultResponse(BaseModel):
    """Result of a price sync operation."""

    success: bool
    updated: int
    added: int
    errors: list[str]


class SeedResultResponse(BaseModel):
    """Result of seeding default prices."""

    success: bool
    count: int
    message: str


class SyncAllResultResponse(BaseModel):
    """Result of syncing all providers."""

    success: bool
    azure_openai: SyncResultResponse
    openai: SyncResultResponse
    anthropic: SyncResultResponse
    total_updated: int
    total_added: int
    total_errors: int


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=PricingListResponse)
async def list_pricing(
    provider: str | None = None,
    include_deprecated: bool = False,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
) -> PricingListResponse:
    """Get all pricing entries."""
    query = select(ModelPricing)

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
    entries = result.scalars().all()

    pricing_list = []
    stale_count = 0

    for entry in entries:
        is_stale = entry.is_stale
        if is_stale:
            stale_count += 1

        pricing_list.append(
            PricingEntry(
                id=str(entry.id),
                provider=entry.provider.value,
                model_name=entry.model_name,
                display_name=entry.display_name,
                input_price_per_1m=entry.input_price_per_1m,
                output_price_per_1m=entry.output_price_per_1m,
                cached_input_price_per_1m=entry.cached_input_price_per_1m,
                source=entry.source.value,
                source_url=entry.source_url,
                is_active=entry.is_active,
                is_deprecated=entry.is_deprecated,
                is_stale=is_stale,
                days_since_verified=entry.days_since_verified,
                last_verified_at=entry.last_verified_at.isoformat() if entry.last_verified_at else None,
                notes=entry.notes,
            )
        )

    return PricingListResponse(
        entries=pricing_list,
        total=len(pricing_list),
        stale_count=stale_count,
        official_urls={p.value: url for p, url in OFFICIAL_PRICING_URLS.items()},
    )


@router.post("", response_model=PricingEntry)
async def create_pricing(
    request: CreatePricingRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
) -> PricingEntry:
    """Create a new pricing entry."""
    from services.model_pricing_service import ModelPricingService

    pricing = await ModelPricingService.upsert_pricing(
        session=session,
        provider=request.provider,
        model_name=request.model_name,
        display_name=request.display_name,
        input_price_per_1m=request.input_price_per_1m,
        output_price_per_1m=request.output_price_per_1m,
        cached_input_price_per_1m=request.cached_input_price_per_1m,
        source="manual",
        source_url=request.source_url,
        notes=request.notes,
    )

    # Create audit log entry
    await create_audit_log(
        session=session,
        action=AuditAction.CREATE,
        entity_type="ModelPricing",
        entity_id=pricing.id,
        entity_name=f"{request.provider}/{request.model_name}",
        user=current_user,
    )

    await session.commit()

    return PricingEntry(
        id=str(pricing.id),
        provider=pricing.provider.value,
        model_name=pricing.model_name,
        display_name=pricing.display_name,
        input_price_per_1m=pricing.input_price_per_1m,
        output_price_per_1m=pricing.output_price_per_1m,
        cached_input_price_per_1m=pricing.cached_input_price_per_1m,
        source=pricing.source.value,
        source_url=pricing.source_url,
        is_active=pricing.is_active,
        is_deprecated=pricing.is_deprecated,
        is_stale=pricing.is_stale,
        days_since_verified=pricing.days_since_verified,
        last_verified_at=pricing.last_verified_at.isoformat() if pricing.last_verified_at else None,
        notes=pricing.notes,
    )


@router.put("/{pricing_id}", response_model=PricingEntry)
async def update_pricing(
    pricing_id: str,
    request: UpdatePricingRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
) -> PricingEntry:
    """Update an existing pricing entry."""
    from uuid import UUID

    try:
        uuid_id = UUID(pricing_id)
    except ValueError:
        raise NotFoundError("Ungültige Preis-ID") from None

    result = await session.execute(select(ModelPricing).where(ModelPricing.id == uuid_id))
    pricing = result.scalar_one_or_none()

    if not pricing:
        raise NotFoundError("Preiseintrag nicht gefunden")

    # Update fields
    pricing.input_price_per_1m = request.input_price_per_1m
    pricing.output_price_per_1m = request.output_price_per_1m
    pricing.cached_input_price_per_1m = request.cached_input_price_per_1m
    pricing.last_verified_at = datetime.now(UTC)
    pricing.source = "manual"

    if request.display_name:
        pricing.display_name = request.display_name
    if request.notes is not None:
        pricing.notes = request.notes

    # Create audit log entry
    await create_audit_log(
        session=session,
        action=AuditAction.UPDATE,
        entity_type="ModelPricing",
        entity_id=uuid_id,
        entity_name=f"{pricing.provider.value}/{pricing.model_name}",
        user=current_user,
    )

    await session.commit()

    return PricingEntry(
        id=str(pricing.id),
        provider=pricing.provider.value,
        model_name=pricing.model_name,
        display_name=pricing.display_name,
        input_price_per_1m=pricing.input_price_per_1m,
        output_price_per_1m=pricing.output_price_per_1m,
        cached_input_price_per_1m=pricing.cached_input_price_per_1m,
        source=pricing.source.value,
        source_url=pricing.source_url,
        is_active=pricing.is_active,
        is_deprecated=pricing.is_deprecated,
        is_stale=pricing.is_stale,
        days_since_verified=pricing.days_since_verified,
        last_verified_at=pricing.last_verified_at.isoformat() if pricing.last_verified_at else None,
        notes=pricing.notes,
    )


@router.delete("/{pricing_id}")
async def delete_pricing(
    pricing_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
) -> dict:
    """Delete a pricing entry (soft delete - marks as deprecated)."""
    from uuid import UUID

    try:
        uuid_id = UUID(pricing_id)
    except ValueError:
        raise NotFoundError("Ungültige Preis-ID") from None

    result = await session.execute(select(ModelPricing).where(ModelPricing.id == uuid_id))
    pricing = result.scalar_one_or_none()

    if not pricing:
        raise NotFoundError("Preiseintrag nicht gefunden")

    # Create audit log entry
    await create_audit_log(
        session=session,
        action=AuditAction.DELETE,
        entity_type="ModelPricing",
        entity_id=uuid_id,
        entity_name=f"{pricing.provider.value}/{pricing.model_name}",
        user=current_user,
    )

    pricing.is_deprecated = True
    pricing.is_active = False
    await session.commit()

    return {"message": "Preiseintrag wurde als veraltet markiert"}


@router.post("/sync-azure", response_model=SyncResultResponse)
async def sync_azure_prices(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
) -> SyncResultResponse:
    """Sync Azure OpenAI prices from Azure Retail Prices API."""
    from services.model_pricing_service import ModelPricingService

    results = await ModelPricingService.sync_azure_prices(session)

    return SyncResultResponse(
        success=len(results["errors"]) == 0,
        updated=results["updated"],
        added=results["added"],
        errors=results["errors"],
    )


@router.post("/sync-all", response_model=SyncAllResultResponse)
async def sync_all_prices(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
) -> SyncAllResultResponse:
    """Sync prices from all providers (Azure API + LiteLLM for OpenAI/Anthropic)."""
    from services.model_pricing_service import ModelPricingService

    results = await ModelPricingService.sync_all_prices(session)

    return SyncAllResultResponse(
        success=results["total_errors"] == 0,
        azure_openai=SyncResultResponse(
            success=len(results["azure_openai"]["errors"]) == 0,
            updated=results["azure_openai"]["updated"],
            added=results["azure_openai"]["added"],
            errors=results["azure_openai"]["errors"],
        ),
        openai=SyncResultResponse(
            success=len(results["openai"]["errors"]) == 0,
            updated=results["openai"]["updated"],
            added=results["openai"]["added"],
            errors=results["openai"]["errors"],
        ),
        anthropic=SyncResultResponse(
            success=len(results["anthropic"]["errors"]) == 0,
            updated=results["anthropic"]["updated"],
            added=results["anthropic"]["added"],
            errors=results["anthropic"]["errors"],
        ),
        total_updated=results["total_updated"],
        total_added=results["total_added"],
        total_errors=results["total_errors"],
    )


@router.post("/sync-litellm", response_model=SyncResultResponse)
async def sync_litellm_prices(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
) -> SyncResultResponse:
    """Sync prices from LiteLLM community database.

    Fetches current model pricing from the LiteLLM GitHub repository,
    which maintains an up-to-date database of 1000+ models from various providers.
    This is the most reliable source for current OpenAI and Anthropic pricing.
    """
    from services.model_pricing_service import ModelPricingService

    results = await ModelPricingService.sync_from_litellm(session)

    return SyncResultResponse(
        success=len(results["errors"]) == 0,
        updated=results["updated"],
        added=results["added"],
        errors=results["errors"],
    )


@router.post("/seed", response_model=SeedResultResponse)
async def seed_default_pricing(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
) -> SeedResultResponse:
    """Seed default pricing data (only if table is empty)."""
    from services.model_pricing_service import ModelPricingService

    count = await ModelPricingService.seed_default_pricing(session)

    if count == 0:
        return SeedResultResponse(
            success=True,
            count=0,
            message="Preisdaten waren bereits vorhanden",
        )

    return SeedResultResponse(
        success=True,
        count=count,
        message=f"{count} Standardpreise wurden eingefügt",
    )


