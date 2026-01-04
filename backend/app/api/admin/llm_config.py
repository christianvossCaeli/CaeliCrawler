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

    await session.delete(config)
    await session.commit()

    purpose_name = PURPOSE_DESCRIPTIONS.get(llm_purpose, {}).get(
        f"name_{current_user.language or 'de'}",
        PURPOSE_DESCRIPTIONS.get(llm_purpose, {}).get("name_de", purpose),
    )

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

    result = await session.execute(
        select(UserLLMConfig).where(
            UserLLMConfig.user_id == current_user.id,
            UserLLMConfig.purpose == llm_purpose,
            UserLLMConfig.is_active.is_(True),
        )
    )
    config = result.scalar_one_or_none()

    language = current_user.language or "de"
    purpose_info = PURPOSE_DESCRIPTIONS.get(llm_purpose, {})
    purpose_name = purpose_info.get(f"name_{language}", purpose_info.get("name_de", purpose))

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
