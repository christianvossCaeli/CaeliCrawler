"""Admin API for managing user LLM configurations per purpose.

This module provides endpoints for users to configure which LLM provider
to use for each purpose (e.g., document analysis, embeddings, assistant, etc.).

Each purpose can have one provider configured with encrypted credentials.

Endpoints:
- GET /purposes: Get all available purposes with their valid providers
- GET /status: Get configuration status for all purposes
- GET /{purpose}: Get configuration for a specific purpose
- PUT /{purpose}: Save configuration for a purpose
- DELETE /{purpose}: Delete configuration for a purpose
- POST /test/{purpose}: Test a configuration
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_editor
from app.core.encryption import EncryptionService
from app.core.exceptions import NotFoundError, ValidationError
from app.core.rate_limit import check_rate_limit
from app.database import get_session
from app.models import User
from app.models.audit_log import AuditAction
from app.services.audit_service import create_audit_log
from app.models.user_api_credentials import (
    EMBEDDINGS_REQUIRED_FIELDS,
    PROVIDER_DESCRIPTIONS,
    PROVIDER_FIELDS,
    PROVIDER_OPTIONAL_FIELDS,
    PURPOSE_DESCRIPTIONS,
    PURPOSE_VALID_PROVIDERS,
    LLMProvider,
    LLMPurpose,
    UserLLMConfig,
)
from services.credentials_resolver import get_search_api_config

logger = structlog.get_logger()
router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================


class ProviderInfo(BaseModel):
    """Information about an LLM provider."""

    value: str
    name: str
    description: str
    fields: list[str]  # Core required fields
    optional_fields: list[str] = []  # Optional fields (e.g., organization for OpenAI)
    embeddings_fields: list[str] = []  # Required only for EMBEDDINGS purpose


class PurposeInfo(BaseModel):
    """Information about an LLM purpose with its valid providers."""

    value: str
    name: str
    description: str
    icon: str
    valid_providers: list[ProviderInfo]


class AllPurposesResponse(BaseModel):
    """List of all available purposes."""

    purposes: list[PurposeInfo]


class PurposeConfigStatus(BaseModel):
    """Configuration status for a single purpose."""

    purpose: str
    purpose_name: str
    purpose_description: str
    purpose_icon: str
    is_configured: bool
    provider: str | None
    provider_name: str | None
    is_active: bool
    last_used_at: str | None
    last_error: str | None


class AllConfigStatusResponse(BaseModel):
    """Configuration status for all purposes."""

    configs: list[PurposeConfigStatus]


class SaveConfigRequest(BaseModel):
    """Request to save a configuration for a purpose."""

    provider: str = Field(..., description="Provider to use for this purpose")
    credentials: dict[str, str] = Field(..., description="Provider-specific credentials")


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


class TestResultResponse(BaseModel):
    """Result of a connection test."""

    success: bool
    message: str
    error: str | None = None


# =============================================================================
# Helper Functions
# =============================================================================


def get_purpose_info(purpose: LLMPurpose, language: str = "de") -> PurposeInfo:
    """Get information about a purpose with its valid providers."""
    info = PURPOSE_DESCRIPTIONS.get(purpose, {})
    valid_providers = PURPOSE_VALID_PROVIDERS.get(purpose, [])

    return PurposeInfo(
        value=purpose.value,
        name=info.get(f"name_{language}", info.get("name_de", purpose.value)),
        description=info.get(f"description_{language}", info.get("description_de", "")),
        icon=info.get("icon", "mdi-cog"),
        valid_providers=[
            ProviderInfo(
                value=p.value,
                name=PROVIDER_DESCRIPTIONS.get(p, {}).get("name", p.value),
                description=PROVIDER_DESCRIPTIONS.get(p, {}).get(
                    f"description_{language}",
                    PROVIDER_DESCRIPTIONS.get(p, {}).get("description_de", ""),
                ),
                fields=PROVIDER_FIELDS.get(p, []),
                optional_fields=PROVIDER_OPTIONAL_FIELDS.get(p, []),
                embeddings_fields=EMBEDDINGS_REQUIRED_FIELDS.get(p, []),
            )
            for p in valid_providers
        ],
    )


def get_config_status(
    purpose: LLMPurpose,
    config: UserLLMConfig | None,
    language: str = "de",
) -> PurposeConfigStatus:
    """Create a status response for a purpose configuration."""
    purpose_info = PURPOSE_DESCRIPTIONS.get(purpose, {})
    provider_info = PROVIDER_DESCRIPTIONS.get(config.provider, {}) if config else {}

    return PurposeConfigStatus(
        purpose=purpose.value,
        purpose_name=purpose_info.get(f"name_{language}", purpose_info.get("name_de", purpose.value)),
        purpose_description=purpose_info.get(f"description_{language}", purpose_info.get("description_de", "")),
        purpose_icon=purpose_info.get("icon", "mdi-cog"),
        is_configured=config is not None,
        provider=config.provider.value if config else None,
        provider_name=provider_info.get("name") if config else None,
        is_active=config.is_active if config else False,
        last_used_at=config.last_used_at.isoformat() if config and config.last_used_at else None,
        last_error=config.last_error if config else None,
    )


def validate_provider_for_purpose(purpose: LLMPurpose, provider: LLMProvider) -> None:
    """Validate that a provider is valid for a purpose."""
    valid_providers = PURPOSE_VALID_PROVIDERS.get(purpose, [])
    if provider not in valid_providers:
        valid_names = [PROVIDER_DESCRIPTIONS.get(p, {}).get("name", p.value) for p in valid_providers]
        raise ValidationError(
            f"Provider '{provider.value}' ist nicht gültig für '{purpose.value}'. "
            f"Gültige Provider: {', '.join(valid_names)}"
        )


def validate_credentials(
    provider: LLMProvider,
    credentials: dict[str, str],
    purpose: LLMPurpose | None = None,
) -> None:
    """Validate that all required fields are provided for a provider.

    Args:
        provider: The LLM provider
        credentials: The credentials dict
        purpose: Optional purpose - if EMBEDDINGS, additional fields are required
    """
    required_fields = list(PROVIDER_FIELDS.get(provider, []))

    # For EMBEDDINGS purpose, add embeddings-specific required fields
    if purpose == LLMPurpose.EMBEDDINGS:
        embeddings_fields = EMBEDDINGS_REQUIRED_FIELDS.get(provider, [])
        required_fields.extend(embeddings_fields)

    missing = [f for f in required_fields if not credentials.get(f)]

    # api_key is always required
    if ("api_key" not in credentials or not credentials["api_key"]) and "api_key" not in missing:
        missing.append("api_key")

    if missing:
        raise ValidationError(f"Fehlende Pflichtfelder: {', '.join(missing)}")


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/purposes", response_model=AllPurposesResponse)
async def get_all_purposes(
    current_user: User = Depends(require_editor),
) -> AllPurposesResponse:
    """Get all available LLM purposes with their valid providers.

    This endpoint provides metadata about all purposes and which providers
    can be configured for each purpose.
    """
    language = current_user.language or "de"

    return AllPurposesResponse(purposes=[get_purpose_info(purpose, language) for purpose in LLMPurpose])


@router.get("/status", response_model=AllConfigStatusResponse)
async def get_all_config_status(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
) -> AllConfigStatusResponse:
    """Get configuration status for all purposes.

    Returns the status of each purpose including whether it's configured,
    which provider is used, and any error messages.
    """
    result = await session.execute(select(UserLLMConfig).where(UserLLMConfig.user_id == current_user.id))
    configs = {c.purpose: c for c in result.scalars().all()}

    language = current_user.language or "de"

    return AllConfigStatusResponse(
        configs=[get_config_status(purpose, configs.get(purpose), language) for purpose in LLMPurpose]
    )


@router.get("/{purpose}", response_model=PurposeConfigStatus)
async def get_purpose_config(
    purpose: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
) -> PurposeConfigStatus:
    """Get configuration for a specific purpose."""
    try:
        llm_purpose = LLMPurpose(purpose)
    except ValueError:
        raise ValidationError(f"Unbekannter Zweck: {purpose}") from None

    result = await session.execute(
        select(UserLLMConfig).where(
            UserLLMConfig.user_id == current_user.id,
            UserLLMConfig.purpose == llm_purpose,
        )
    )
    config = result.scalar_one_or_none()

    language = current_user.language or "de"
    return get_config_status(llm_purpose, config, language)


@router.put("/{purpose}", response_model=MessageResponse)
async def save_purpose_config(
    purpose: str,
    data: SaveConfigRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
) -> MessageResponse:
    """Save configuration for a purpose.

    Validates that the provider is valid for the purpose and that
    all required credential fields are provided.
    """
    await check_rate_limit(request, "api_credentials", identifier=str(current_user.id))

    # Parse and validate purpose
    try:
        llm_purpose = LLMPurpose(purpose)
    except ValueError:
        raise ValidationError(f"Unbekannter Zweck: {purpose}") from None

    # Parse and validate provider
    try:
        provider = LLMProvider(data.provider)
    except ValueError:
        raise ValidationError(f"Unbekannter Provider: {data.provider}") from None

    validate_provider_for_purpose(llm_purpose, provider)
    validate_credentials(provider, data.credentials, llm_purpose)

    # Check for existing config
    result = await session.execute(
        select(UserLLMConfig).where(
            UserLLMConfig.user_id == current_user.id,
            UserLLMConfig.purpose == llm_purpose,
        )
    )
    existing = result.scalar_one_or_none()

    # Encrypt credentials
    encrypted = EncryptionService.encrypt(data.credentials)

    if existing:
        existing.provider = provider
        existing.encrypted_data = encrypted
        existing.is_active = True
        existing.last_error = None
    else:
        session.add(
            UserLLMConfig(
                user_id=current_user.id,
                purpose=llm_purpose,
                provider=provider,
                encrypted_data=encrypted,
                is_active=True,
            )
        )

    # Create audit log entry
    await create_audit_log(
        session=session,
        action=AuditAction.CONFIG_UPDATE,
        entity_type="LLMConfig",
        entity_name=f"{llm_purpose.value}/{provider.value}",
        user=current_user,
    )

    await session.commit()

    purpose_name = PURPOSE_DESCRIPTIONS.get(llm_purpose, {}).get(
        f"name_{current_user.language or 'de'}",
        PURPOSE_DESCRIPTIONS.get(llm_purpose, {}).get("name_de", purpose),
    )

    logger.info(
        "llm_config_saved",
        user_id=str(current_user.id),
        purpose=llm_purpose.value,
        provider=provider.value,
        action="update" if existing else "create",
    )

    return MessageResponse(message=f"Konfiguration für '{purpose_name}' erfolgreich gespeichert")


@router.delete("/{purpose}", response_model=MessageResponse)
async def delete_purpose_config(
    purpose: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
) -> MessageResponse:
    """Delete configuration for a purpose."""
    try:
        llm_purpose = LLMPurpose(purpose)
    except ValueError:
        raise ValidationError(f"Unbekannter Zweck: {purpose}") from None

    result = await session.execute(
        select(UserLLMConfig).where(
            UserLLMConfig.user_id == current_user.id,
            UserLLMConfig.purpose == llm_purpose,
        )
    )
    config = result.scalar_one_or_none()

    if not config:
        raise NotFoundError("LLM-Konfiguration", purpose)

    purpose_name = PURPOSE_DESCRIPTIONS.get(llm_purpose, {}).get(
        f"name_{current_user.language or 'de'}",
        PURPOSE_DESCRIPTIONS.get(llm_purpose, {}).get("name_de", purpose),
    )

    # Create audit log entry
    await create_audit_log(
        session=session,
        action=AuditAction.DELETE,
        entity_type="LLMConfig",
        entity_name=purpose,
        user=current_user,
    )

    await session.delete(config)
    await session.commit()

    logger.info(
        "llm_config_deleted",
        user_id=str(current_user.id),
        purpose=purpose,
    )

    return MessageResponse(message=f"Konfiguration für '{purpose_name}' gelöscht")


@router.post("/test/{purpose}", response_model=TestResultResponse)
async def test_purpose_config(
    purpose: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
) -> TestResultResponse:
    """Test the configuration for a purpose.

    Performs a simple API call to verify that the credentials work.
    """
    try:
        llm_purpose = LLMPurpose(purpose)
    except ValueError:
        raise ValidationError(f"Unbekannter Zweck: {purpose}") from None

    result = await session.execute(
        select(UserLLMConfig).where(
            UserLLMConfig.user_id == current_user.id,
            UserLLMConfig.purpose == llm_purpose,
        )
    )
    config = result.scalar_one_or_none()

    if not config:
        purpose_name = PURPOSE_DESCRIPTIONS.get(llm_purpose, {}).get("name_de", purpose)
        raise ValidationError(f"'{purpose_name}' ist nicht konfiguriert")

    # Decrypt credentials
    try:
        creds = EncryptionService.decrypt(config.encrypted_data)
    except Exception as e:
        return TestResultResponse(
            success=False,
            message="Entschlüsselung fehlgeschlagen",
            error=str(e),
        )

    # Test based on provider
    provider = config.provider

    try:
        if provider == LLMProvider.SERPAPI:
            return await _test_serpapi(creds)
        elif provider == LLMProvider.SERPER:
            return await _test_serper(creds)
        elif provider == LLMProvider.AZURE_OPENAI:
            return await _test_azure_openai(creds)
        elif provider == LLMProvider.OPENAI:
            return await _test_openai(creds)
        elif provider == LLMProvider.ANTHROPIC:
            return await _test_anthropic(creds)
        else:
            return TestResultResponse(
                success=False,
                message="Unbekannter Provider",
                error=f"Provider '{provider.value}' wird nicht unterstützt",
            )
    except Exception as e:
        return TestResultResponse(
            success=False,
            message="Verbindungstest fehlgeschlagen",
            error=str(e),
        )


# =============================================================================
# Test Helpers
# =============================================================================


async def _test_serpapi(creds: dict[str, Any]) -> TestResultResponse:
    """Test SerpAPI credentials."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            "https://serpapi.com/search.json",
            params={
                "engine": "google",
                "q": "test",
                "num": 1,
                "api_key": creds["api_key"],
            },
        )
        if response.status_code == 200:
            return TestResultResponse(success=True, message="SerpAPI-Verbindung erfolgreich")
        return TestResultResponse(
            success=False,
            message="SerpAPI-Verbindung fehlgeschlagen",
            error=response.text[:200] if response.text else "Unbekannter Fehler",
        )


async def _test_serper(creds: dict[str, Any]) -> TestResultResponse:
    """Test Serper credentials."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": creds["api_key"],
                "Content-Type": "application/json",
            },
            json={"q": "test", "num": 1},
        )
        if response.status_code == 200:
            return TestResultResponse(success=True, message="Serper-Verbindung erfolgreich")
        return TestResultResponse(
            success=False,
            message="Serper-Verbindung fehlgeschlagen",
            error=response.text[:200] if response.text else "Unbekannter Fehler",
        )


async def _test_azure_openai(creds: dict[str, Any]) -> TestResultResponse:
    """Test Azure OpenAI credentials."""
    endpoint = creds["endpoint"].rstrip("/")
    deployment = creds["deployment_name"]
    api_version = creds.get("api_version", "2025-04-01-preview")

    url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            url,
            headers={
                "api-key": creds["api_key"],
                "Content-Type": "application/json",
            },
            json={
                "messages": [{"role": "user", "content": "Say 'test'"}],
                "max_tokens": 5,
            },
        )
        if response.status_code == 200:
            return TestResultResponse(success=True, message="Azure OpenAI-Verbindung erfolgreich")
        return TestResultResponse(
            success=False,
            message="Azure OpenAI-Verbindung fehlgeschlagen",
            error=response.text[:200] if response.text else "Unbekannter Fehler",
        )


async def _test_openai(creds: dict[str, Any]) -> TestResultResponse:
    """Test standard OpenAI credentials."""
    headers = {
        "Authorization": f"Bearer {creds['api_key']}",
        "Content-Type": "application/json",
    }
    if creds.get("organization"):
        headers["OpenAI-Organization"] = creds["organization"]

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json={
                "model": creds.get("model", "gpt-4o"),
                "messages": [{"role": "user", "content": "Say 'test'"}],
                "max_tokens": 5,
            },
        )
        if response.status_code == 200:
            return TestResultResponse(success=True, message="OpenAI-Verbindung erfolgreich")
        return TestResultResponse(
            success=False,
            message="OpenAI-Verbindung fehlgeschlagen",
            error=response.text[:200] if response.text else "Unbekannter Fehler",
        )


async def _test_anthropic(creds: dict[str, Any]) -> TestResultResponse:
    """Test Anthropic credentials."""
    endpoint = creds.get("endpoint", "https://api.anthropic.com").rstrip("/")
    url = f"{endpoint}/v1/messages"

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            url,
            headers={
                "x-api-key": creds["api_key"],
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": creds.get("model", "claude-opus-4-5"),
                "max_tokens": 5,
                "messages": [{"role": "user", "content": "Say 'test'"}],
            },
        )
        if response.status_code == 200:
            return TestResultResponse(success=True, message="Anthropic-Verbindung erfolgreich")
        return TestResultResponse(
            success=False,
            message="Anthropic-Verbindung fehlgeschlagen",
            error=response.text[:200] if response.text else "Unbekannter Fehler",
        )


# =============================================================================
# Active Configuration Endpoint (for UI badges)
# =============================================================================


class ActiveConfigResponse(BaseModel):
    """Active configuration info for displaying in UI."""

    purpose: str
    purpose_name: str
    is_configured: bool
    provider: str | None = None
    provider_name: str | None = None
    model: str | None = None
    pricing_input_per_1m: float | None = None
    pricing_output_per_1m: float | None = None


@router.get("/active/{purpose}", response_model=ActiveConfigResponse)
async def get_active_config(
    purpose: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
) -> ActiveConfigResponse:
    """Get active configuration for a purpose with pricing info.

    This endpoint is designed for displaying provider badges in the UI.
    It returns the currently configured provider and model along with
    pricing information for cost estimation.
    """
    from services.llm_usage_tracker import get_model_pricing

    try:
        llm_purpose = LLMPurpose(purpose)
    except ValueError:
        raise ValidationError(f"Unbekannter Zweck: {purpose}") from None

    language = current_user.language or "de"
    purpose_info = PURPOSE_DESCRIPTIONS.get(llm_purpose, {})
    purpose_name = purpose_info.get(f"name_{language}", purpose_info.get("name_de", purpose))

    if llm_purpose == LLMPurpose.WEB_SEARCH:
        search_config = await get_search_api_config(session, current_user.id)
        if not search_config:
            return ActiveConfigResponse(
                purpose=purpose,
                purpose_name=purpose_name,
                is_configured=False,
            )

        api_type, _ = search_config
        provider = LLMProvider.SERPAPI if api_type == "serpapi" else LLMProvider.SERPER
        provider_info = PROVIDER_DESCRIPTIONS.get(provider, {})
        return ActiveConfigResponse(
            purpose=purpose,
            purpose_name=purpose_name,
            is_configured=True,
            provider=provider.value,
            provider_name=provider_info.get("name", provider.value),
        )

    result = await session.execute(
        select(UserLLMConfig).where(
            UserLLMConfig.user_id == current_user.id,
            UserLLMConfig.purpose == llm_purpose,
            UserLLMConfig.is_active.is_(True),
        )
    )
    config = result.scalar_one_or_none()

    if not config:
        return ActiveConfigResponse(
            purpose=purpose,
            purpose_name=purpose_name,
            is_configured=False,
        )

    # Get provider info
    provider_info = PROVIDER_DESCRIPTIONS.get(config.provider, {})

    # Decrypt to get model name
    model = None
    try:
        creds = EncryptionService.decrypt(config.encrypted_data)
        # Get model name based on provider type
        if config.provider == LLMProvider.AZURE_OPENAI:
            model = creds.get("deployment_name")
        elif config.provider == LLMProvider.OPENAI:
            model = creds.get("model", "gpt-4o")
        elif config.provider == LLMProvider.ANTHROPIC:
            model = creds.get("model", "claude-opus-4-5")
    except Exception:  # noqa: S110
        pass  # Decryption failures are expected when credentials are not set

    # Get pricing for the model
    pricing = None
    if model:
        pricing = get_model_pricing(model)

    return ActiveConfigResponse(
        purpose=purpose,
        purpose_name=purpose_name,
        is_configured=True,
        provider=config.provider.value,
        provider_name=provider_info.get("name", config.provider.value),
        model=model,
        pricing_input_per_1m=pricing["input"] if pricing else None,
        pricing_output_per_1m=pricing["output"] if pricing else None,
    )


# =============================================================================
# Embedding Generation Endpoints
# =============================================================================


class EmbeddingStatsResponse(BaseModel):
    """Statistics about embeddings in the database."""

    entities_total: int
    entities_with_embedding: int
    entities_missing: int
    entity_types_total: int
    entity_types_with_embedding: int
    facet_types_total: int
    facet_types_with_embedding: int
    categories_total: int
    categories_with_embedding: int
    relation_types_total: int
    relation_types_with_embedding: int
    facet_values_total: int
    facet_values_with_embedding: int
    is_configured: bool
    task_running: bool
    task_id: str | None = None


class GenerateEmbeddingsRequest(BaseModel):
    """Request to generate embeddings."""

    target: str = Field(
        default="all",
        description="Target for generation: 'all', 'entities', 'types', 'facet_values'",
    )
    force: bool = Field(
        default=False,
        description="Regenerate all embeddings (even existing ones)",
    )


class GenerateEmbeddingsResponse(BaseModel):
    """Response after starting embedding generation."""

    task_id: str
    message: str


@router.get("/embeddings/stats", response_model=EmbeddingStatsResponse)
async def get_embedding_stats(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
) -> EmbeddingStatsResponse:
    """Get statistics about embeddings in the database.

    Returns counts of entities/types with and without embeddings,
    and whether the EMBEDDINGS purpose is configured.
    """
    from sqlalchemy import func

    from app.models import Category, Entity, EntityType, FacetType, FacetValue, RelationType
    from workers.ai_tasks import get_embedding_task_status

    # Check if EMBEDDINGS is configured
    result = await session.execute(
        select(UserLLMConfig).where(
            UserLLMConfig.user_id == current_user.id,
            UserLLMConfig.purpose == LLMPurpose.EMBEDDINGS,
            UserLLMConfig.is_active.is_(True),
        )
    )
    is_configured = result.scalar_one_or_none() is not None

    # Entity stats
    entities_total = await session.scalar(select(func.count(Entity.id)))
    entities_with = await session.scalar(
        select(func.count(Entity.id)).where(Entity.name_embedding.isnot(None))
    )

    # EntityType stats
    entity_types_total = await session.scalar(select(func.count(EntityType.id)))
    entity_types_with = await session.scalar(
        select(func.count(EntityType.id)).where(EntityType.name_embedding.isnot(None))
    )

    # FacetType stats
    facet_types_total = await session.scalar(select(func.count(FacetType.id)))
    facet_types_with = await session.scalar(
        select(func.count(FacetType.id)).where(FacetType.name_embedding.isnot(None))
    )

    # Category stats
    categories_total = await session.scalar(select(func.count(Category.id)))
    categories_with = await session.scalar(
        select(func.count(Category.id)).where(Category.name_embedding.isnot(None))
    )

    # RelationType stats
    relation_types_total = await session.scalar(select(func.count(RelationType.id)))
    relation_types_with = await session.scalar(
        select(func.count(RelationType.id)).where(RelationType.name_embedding.isnot(None))
    )

    # FacetValue stats
    facet_values_total = await session.scalar(select(func.count(FacetValue.id)))
    facet_values_with = await session.scalar(
        select(func.count(FacetValue.id)).where(FacetValue.text_embedding.isnot(None))
    )

    # Check if task is running
    task_status = get_embedding_task_status()

    return EmbeddingStatsResponse(
        entities_total=entities_total or 0,
        entities_with_embedding=entities_with or 0,
        entities_missing=(entities_total or 0) - (entities_with or 0),
        entity_types_total=entity_types_total or 0,
        entity_types_with_embedding=entity_types_with or 0,
        facet_types_total=facet_types_total or 0,
        facet_types_with_embedding=facet_types_with or 0,
        categories_total=categories_total or 0,
        categories_with_embedding=categories_with or 0,
        relation_types_total=relation_types_total or 0,
        relation_types_with_embedding=relation_types_with or 0,
        facet_values_total=facet_values_total or 0,
        facet_values_with_embedding=facet_values_with or 0,
        is_configured=is_configured,
        task_running=task_status.get("running", False),
        task_id=task_status.get("task_id"),
    )


@router.post("/embeddings/generate", response_model=GenerateEmbeddingsResponse)
async def generate_embeddings(
    data: GenerateEmbeddingsRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
) -> GenerateEmbeddingsResponse:
    """Start embedding generation as a background task.

    This endpoint queues a Celery task to generate embeddings for the specified target.
    The task runs in the background and can be monitored via the stats endpoint.

    Args:
        data: Generation parameters (target, force)

    Returns:
        Task ID and confirmation message
    """
    from workers.ai_tasks import generate_embeddings_task, get_embedding_task_status

    # Check if EMBEDDINGS is configured
    result = await session.execute(
        select(UserLLMConfig).where(
            UserLLMConfig.user_id == current_user.id,
            UserLLMConfig.purpose == LLMPurpose.EMBEDDINGS,
            UserLLMConfig.is_active.is_(True),
        )
    )
    if not result.scalar_one_or_none():
        raise ValidationError("Embeddings-Provider ist nicht konfiguriert")

    # Check if task is already running
    task_status = get_embedding_task_status()
    if task_status.get("running"):
        raise ValidationError(
            f"Embedding-Generierung läuft bereits (Task-ID: {task_status.get('task_id')})"
        )

    # Validate target
    valid_targets = {"all", "entities", "types", "facet_values"}
    if data.target not in valid_targets:
        raise ValidationError(f"Ungültiges Ziel: {data.target}. Gültig: {', '.join(valid_targets)}")

    # Create audit log
    await create_audit_log(
        session=session,
        action=AuditAction.CONFIG_UPDATE,
        entity_type="Embeddings",
        entity_name=f"generate/{data.target}",
        user=current_user,
        details={"target": data.target, "force": data.force},
    )
    await session.commit()

    # Queue the task
    task = generate_embeddings_task.delay(
        target=data.target,
        force=data.force,
        user_id=str(current_user.id),
    )

    logger.info(
        "embedding_generation_started",
        task_id=task.id,
        target=data.target,
        force=data.force,
        user_id=str(current_user.id),
    )

    target_labels = {
        "all": "alle Embeddings",
        "entities": "Entity-Embeddings",
        "types": "Typ-Embeddings",
        "facet_values": "Facetten-Wert-Embeddings",
    }

    return GenerateEmbeddingsResponse(
        task_id=task.id,
        message=f"Generierung von {target_labels.get(data.target, data.target)} gestartet",
    )
