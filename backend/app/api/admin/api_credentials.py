"""Admin API for managing user API credentials.

This module provides endpoints for users to manage their external API credentials
(SerpAPI, Serper, Azure OpenAI, OpenAI, Anthropic). Credentials are encrypted before
storage and can only be accessed by the owning user.

Endpoints:
- GET /status: Get configuration status for all credential types
- PUT /serpapi: Save SerpAPI credentials
- PUT /serper: Save Serper credentials
- PUT /azure-openai: Save Azure OpenAI credentials
- PUT /openai: Save standard OpenAI credentials
- PUT /anthropic: Save Anthropic credentials
- DELETE /{type}: Delete a specific credential type
- POST /test/{type}: Test a credential connection
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
from app.models.user_api_credentials import (
    API_CREDENTIAL_DESCRIPTIONS,
    ApiCredentialType,
    LLMPurpose,
    UserApiCredentials,
    UserLLMConfig,
)
from app.services.audit_service import create_audit_log
from services.credentials_resolver import ensure_search_credential_from_purpose

logger = structlog.get_logger()
router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================


class SerpApiCredentialsRequest(BaseModel):
    """Request model for SerpAPI credentials."""

    api_key: str = Field(..., min_length=10, description="SerpAPI API Key")


class SerperCredentialsRequest(BaseModel):
    """Request model for Serper credentials."""

    api_key: str = Field(..., min_length=10, description="Serper API Key")


class AzureOpenAICredentialsRequest(BaseModel):
    """Request model for Azure credentials (OpenAI or Claude).

    URLs should be complete Azure URLs that can be copied directly from Azure Portal.
    Example OpenAI chat URL: https://xxx.cognitiveservices.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-02-15
    Example Claude URL: https://xxx.services.ai.azure.com/anthropic/v1/messages
    Example embeddings URL: https://xxx.cognitiveservices.azure.com/openai/deployments/text-embedding-3-large/embeddings?api-version=2023-05-15
    """

    api_key: str = Field(..., min_length=10, description="Azure API Key")
    chat_url: str = Field(..., description="Complete Azure Chat URL (copy from Azure Portal)")
    embeddings_url: str | None = Field(default=None, description="Complete Azure Embeddings URL (only for EMBEDDINGS purpose)")
    model: str | None = Field(default=None, description="Model name (required for Azure Claude, e.g. claude-opus-4-5)")


class OpenAICredentialsRequest(BaseModel):
    """Request model for standard OpenAI credentials (not Azure)."""

    api_key: str = Field(..., min_length=10, description="OpenAI API Key")
    organization: str | None = Field(default=None, description="OpenAI Organization ID (optional)")
    model: str = Field(default="gpt-4o", description="Model to use for chat/completion")
    embeddings_model: str = Field(default="text-embedding-3-large", description="Model to use for embeddings")


class AnthropicCredentialsRequest(BaseModel):
    """Request model for Anthropic credentials."""

    endpoint: str = Field(..., description="Anthropic API Endpoint URL")
    api_key: str = Field(..., min_length=10, description="Anthropic API Key")
    model: str = Field(default="claude-opus-4-5", description="Model to use")


class CredentialStatusResponse(BaseModel):
    """Status of a single credential type."""

    type: str
    name: str
    description: str
    is_configured: bool
    is_active: bool
    last_used_at: str | None
    last_error: str | None
    fields: list[str]
    # Non-sensitive config values (endpoint, model, etc. - NOT api_key)
    config: dict[str, str] | None = None


class AllCredentialsStatusResponse(BaseModel):
    """Status of all credential types for current user."""

    serpapi: CredentialStatusResponse
    serper: CredentialStatusResponse
    azure_openai: CredentialStatusResponse
    openai: CredentialStatusResponse
    anthropic: CredentialStatusResponse


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


# Non-sensitive fields that can be returned in clear text
NON_SENSITIVE_FIELDS: dict[ApiCredentialType, list[str]] = {
    ApiCredentialType.SERPAPI: [],
    ApiCredentialType.SERPER: [],
    ApiCredentialType.AZURE_OPENAI: ["chat_url", "embeddings_url"],
    ApiCredentialType.OPENAI: ["model", "organization", "embeddings_model"],
    ApiCredentialType.ANTHROPIC: ["endpoint", "model"],
}


def mask_api_key(key: str) -> str:
    """Mask an API key, showing only last 4 characters."""
    if not key or len(key) < 8:
        return "••••••••"
    return "••••••••" + key[-4:]


def make_credential_status(
    cred_type: ApiCredentialType,
    cred: UserApiCredentials | None,
    language: str = "de",
) -> CredentialStatusResponse:
    """Create a status response for a credential type."""
    info = API_CREDENTIAL_DESCRIPTIONS.get(cred_type, {})
    desc_key = f"description_{language}"
    description = info.get(desc_key, info.get("description_de", ""))

    # Extract config values (non-sensitive in clear, api_key masked)
    config = None
    if cred and cred.encrypted_data:
        try:
            decrypted = EncryptionService.decrypt(cred.encrypted_data)
            non_sensitive = NON_SENSITIVE_FIELDS.get(cred_type, [])
            config = {}
            for k, v in decrypted.items():
                if not v:
                    continue
                if k == "api_key":
                    config["api_key_masked"] = mask_api_key(v)
                elif k in non_sensitive:
                    config[k] = v
        except Exception:
            pass  # If decryption fails, just don't include config

    return CredentialStatusResponse(
        type=cred_type.value,
        name=info.get("name", cred_type.value),
        description=description,
        is_configured=cred is not None,
        is_active=cred.is_active if cred else False,
        last_used_at=cred.last_used_at.isoformat() if cred and cred.last_used_at else None,
        last_error=cred.last_error if cred else None,
        fields=info.get("fields", []),
        config=config,
    )


async def save_credential(
    session: AsyncSession,
    user_id: Any,
    cred_type: ApiCredentialType,
    data: dict[str, Any],
    user: User | None = None,
) -> None:
    """Save or update a credential."""
    result = await session.execute(
        select(UserApiCredentials).where(
            UserApiCredentials.user_id == user_id,
            UserApiCredentials.credential_type == cred_type,
        )
    )
    existing = result.scalar_one_or_none()

    encrypted = EncryptionService.encrypt(data)

    if existing:
        existing.encrypted_data = encrypted
        existing.is_active = True
        existing.last_error = None
    else:
        session.add(
            UserApiCredentials(
                user_id=user_id,
                credential_type=cred_type,
                encrypted_data=encrypted,
                is_active=True,
            )
        )

    # Create audit log entry
    await create_audit_log(
        session=session,
        action=AuditAction.UPDATE if existing else AuditAction.CREATE,
        entity_type="ApiCredential",
        entity_name=cred_type.value,
        user=user,
    )

    await session.commit()

    logger.info(
        "credential_saved",
        user_id=str(user_id),
        credential_type=cred_type.value,
        action="update" if existing else "create",
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/status", response_model=AllCredentialsStatusResponse)
async def get_credentials_status(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
) -> AllCredentialsStatusResponse:
    """Get configuration status for all API credentials.

    Returns the status of each credential type including whether it's configured,
    active, when it was last used, and any error messages.
    """
    result = await session.execute(select(UserApiCredentials).where(UserApiCredentials.user_id == current_user.id))
    credentials = {c.credential_type: c for c in result.scalars().all()}
    migrated = False

    serpapi_cred = credentials.get(ApiCredentialType.SERPAPI)
    if not serpapi_cred or not serpapi_cred.is_active:
        migrated = (
            bool(await ensure_search_credential_from_purpose(session, current_user.id, ApiCredentialType.SERPAPI))
            or migrated
        )

    serper_cred = credentials.get(ApiCredentialType.SERPER)
    if not serper_cred or not serper_cred.is_active:
        migrated = (
            bool(await ensure_search_credential_from_purpose(session, current_user.id, ApiCredentialType.SERPER))
            or migrated
        )

    if migrated:
        result = await session.execute(select(UserApiCredentials).where(UserApiCredentials.user_id == current_user.id))
        credentials = {c.credential_type: c for c in result.scalars().all()}

    # Get user's language preference
    language = current_user.language or "de"

    return AllCredentialsStatusResponse(
        serpapi=make_credential_status(ApiCredentialType.SERPAPI, credentials.get(ApiCredentialType.SERPAPI), language),
        serper=make_credential_status(ApiCredentialType.SERPER, credentials.get(ApiCredentialType.SERPER), language),
        azure_openai=make_credential_status(
            ApiCredentialType.AZURE_OPENAI, credentials.get(ApiCredentialType.AZURE_OPENAI), language
        ),
        openai=make_credential_status(ApiCredentialType.OPENAI, credentials.get(ApiCredentialType.OPENAI), language),
        anthropic=make_credential_status(
            ApiCredentialType.ANTHROPIC, credentials.get(ApiCredentialType.ANTHROPIC), language
        ),
    )


@router.put("/serpapi", response_model=MessageResponse)
async def save_serpapi_credentials(
    data: SerpApiCredentialsRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
) -> MessageResponse:
    """Save SerpAPI credentials.

    SerpAPI is used for Google Search in AI-powered source discovery.
    """
    await check_rate_limit(request, "api_credentials", identifier=str(current_user.id))
    await save_credential(
        session,
        current_user.id,
        ApiCredentialType.SERPAPI,
        {"api_key": data.api_key},
        user=current_user,
    )
    return MessageResponse(message="SerpAPI-Zugangsdaten erfolgreich gespeichert")


@router.put("/serper", response_model=MessageResponse)
async def save_serper_credentials(
    data: SerperCredentialsRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
) -> MessageResponse:
    """Save Serper credentials.

    Serper is an alternative search API used as fallback when SerpAPI is unavailable.
    """
    await check_rate_limit(request, "api_credentials", identifier=str(current_user.id))
    await save_credential(
        session,
        current_user.id,
        ApiCredentialType.SERPER,
        {"api_key": data.api_key},
        user=current_user,
    )
    return MessageResponse(message="Serper-Zugangsdaten erfolgreich gespeichert")


@router.put("/azure-openai", response_model=MessageResponse)
async def save_azure_openai_credentials(
    data: AzureOpenAICredentialsRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
) -> MessageResponse:
    """Save Azure OpenAI credentials.

    Azure OpenAI is used for document analysis, summaries, and AI features.
    Supports both Azure OpenAI and Azure Claude via URL-based configuration.
    """
    await check_rate_limit(request, "api_credentials", identifier=str(current_user.id))
    cred_data: dict[str, str | None] = {
        "api_key": data.api_key,
        "chat_url": data.chat_url,
    }
    if data.embeddings_url:
        cred_data["embeddings_url"] = data.embeddings_url
    if data.model:
        cred_data["model"] = data.model
    await save_credential(
        session,
        current_user.id,
        ApiCredentialType.AZURE_OPENAI,
        cred_data,
        user=current_user,
    )
    return MessageResponse(message="Azure-Zugangsdaten erfolgreich gespeichert")


@router.put("/openai", response_model=MessageResponse)
async def save_openai_credentials(
    data: OpenAICredentialsRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
) -> MessageResponse:
    """Save standard OpenAI credentials (not Azure).

    OpenAI is used as an alternative to Azure OpenAI for document analysis and AI features.
    """
    await check_rate_limit(request, "api_credentials", identifier=str(current_user.id))
    cred_data = {
        "api_key": data.api_key,
        "model": data.model,
        "embeddings_model": data.embeddings_model,
    }
    if data.organization:
        cred_data["organization"] = data.organization

    await save_credential(
        session,
        current_user.id,
        ApiCredentialType.OPENAI,
        cred_data,
        user=current_user,
    )
    return MessageResponse(message="OpenAI-Zugangsdaten erfolgreich gespeichert")


@router.put("/anthropic", response_model=MessageResponse)
async def save_anthropic_credentials(
    data: AnthropicCredentialsRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
) -> MessageResponse:
    """Save Anthropic credentials.

    Anthropic Claude is used for advanced API discovery and complex analysis.
    """
    await check_rate_limit(request, "api_credentials", identifier=str(current_user.id))
    await save_credential(
        session,
        current_user.id,
        ApiCredentialType.ANTHROPIC,
        {
            "endpoint": data.endpoint.rstrip("/"),
            "api_key": data.api_key,
            "model": data.model,
        },
        user=current_user,
    )
    return MessageResponse(message="Anthropic-Zugangsdaten erfolgreich gespeichert")


@router.delete("/{credential_type}", response_model=MessageResponse)
async def delete_credential(
    credential_type: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
) -> MessageResponse:
    """Delete a specific credential type."""
    try:
        cred_type = ApiCredentialType(credential_type)
    except ValueError:
        raise ValidationError(f"Unbekannter Credential-Typ: {credential_type}") from None

    result = await session.execute(
        select(UserApiCredentials).where(
            UserApiCredentials.user_id == current_user.id,
            UserApiCredentials.credential_type == cred_type,
        )
    )
    cred = result.scalar_one_or_none()
    if not cred:
        raise NotFoundError("API-Credential", credential_type)

    if cred_type in {ApiCredentialType.SERPAPI, ApiCredentialType.SERPER}:
        result = await session.execute(
            select(UserLLMConfig).where(
                UserLLMConfig.user_id == current_user.id,
                UserLLMConfig.purpose == LLMPurpose.WEB_SEARCH,
            )
        )
        config = result.scalar_one_or_none()
        if config:
            await session.delete(config)

    # Create audit log entry
    await create_audit_log(
        session=session,
        action=AuditAction.DELETE,
        entity_type="ApiCredential",
        entity_name=credential_type,
        user=current_user,
    )

    await session.delete(cred)
    await session.commit()

    logger.info(
        "credential_deleted",
        user_id=str(current_user.id),
        credential_type=credential_type,
    )

    return MessageResponse(message=f"{credential_type}-Zugangsdaten gelöscht")


@router.post("/test/serpapi", response_model=TestResultResponse)
async def test_serpapi(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
) -> TestResultResponse:
    """Test SerpAPI credentials with a simple query."""
    from services.credentials_resolver import get_user_credentials

    creds = await get_user_credentials(session, current_user.id, ApiCredentialType.SERPAPI)
    if not creds:
        raise ValidationError("SerpAPI ist nicht konfiguriert")

    try:
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
                return TestResultResponse(
                    success=True,
                    message="SerpAPI-Verbindung erfolgreich",
                )
            else:
                error_text = response.text[:200] if response.text else "Unbekannter Fehler"
                return TestResultResponse(
                    success=False,
                    message="SerpAPI-Verbindung fehlgeschlagen",
                    error=error_text,
                )
    except Exception as e:
        return TestResultResponse(
            success=False,
            message="SerpAPI-Verbindung fehlgeschlagen",
            error=str(e),
        )


@router.post("/test/serper", response_model=TestResultResponse)
async def test_serper(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
) -> TestResultResponse:
    """Test Serper credentials with a simple query."""
    from services.credentials_resolver import get_user_credentials

    creds = await get_user_credentials(session, current_user.id, ApiCredentialType.SERPER)
    if not creds:
        raise ValidationError("Serper ist nicht konfiguriert")

    try:
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
                return TestResultResponse(
                    success=True,
                    message="Serper-Verbindung erfolgreich",
                )
            else:
                error_text = response.text[:200] if response.text else "Unbekannter Fehler"
                return TestResultResponse(
                    success=False,
                    message="Serper-Verbindung fehlgeschlagen",
                    error=error_text,
                )
    except Exception as e:
        return TestResultResponse(
            success=False,
            message="Serper-Verbindung fehlgeschlagen",
            error=str(e),
        )


@router.post("/test/azure-openai", response_model=TestResultResponse)
async def test_azure_openai(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
) -> TestResultResponse:
    """Test Azure OpenAI credentials with a simple API call."""
    from services.ai_client import get_azure_test_url
    from services.credentials_resolver import get_user_credentials

    creds = await get_user_credentials(session, current_user.id, ApiCredentialType.AZURE_OPENAI)
    if not creds:
        raise ValidationError("Azure OpenAI ist nicht konfiguriert")

    try:
        # Determine if we should test embeddings (only embeddings_url present, no chat_url)
        has_embeddings_only = creds.get("embeddings_url") and not creds.get("chat_url")
        url = get_azure_test_url(creds, for_embeddings=has_embeddings_only)
        is_embeddings = "/embeddings" in url

        async with httpx.AsyncClient(timeout=30) as client:
            if is_embeddings:
                # Test embeddings endpoint
                response = await client.post(
                    url,
                    headers={
                        "api-key": creds["api_key"],
                        "Content-Type": "application/json",
                    },
                    json={"input": "test"},
                )
            else:
                # Test chat/completions endpoint
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
                return TestResultResponse(
                    success=True,
                    message="Azure OpenAI-Verbindung erfolgreich",
                )
            else:
                error_text = response.text[:200] if response.text else "Unbekannter Fehler"
                return TestResultResponse(
                    success=False,
                    message="Azure OpenAI-Verbindung fehlgeschlagen",
                    error=error_text,
                )
    except Exception as e:
        return TestResultResponse(
            success=False,
            message="Azure OpenAI-Verbindung fehlgeschlagen",
            error=str(e),
        )


@router.post("/test/openai", response_model=TestResultResponse)
async def test_openai(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
) -> TestResultResponse:
    """Test standard OpenAI credentials with a simple API call."""
    from services.credentials_resolver import get_user_credentials

    creds = await get_user_credentials(session, current_user.id, ApiCredentialType.OPENAI)
    if not creds:
        raise ValidationError("OpenAI ist nicht konfiguriert")

    try:
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
                return TestResultResponse(
                    success=True,
                    message="OpenAI-Verbindung erfolgreich",
                )
            else:
                error_text = response.text[:200] if response.text else "Unbekannter Fehler"
                return TestResultResponse(
                    success=False,
                    message="OpenAI-Verbindung fehlgeschlagen",
                    error=error_text,
                )
    except Exception as e:
        return TestResultResponse(
            success=False,
            message="OpenAI-Verbindung fehlgeschlagen",
            error=str(e),
        )


@router.post("/test/anthropic", response_model=TestResultResponse)
async def test_anthropic(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
) -> TestResultResponse:
    """Test Anthropic credentials with a simple API call."""
    from services.credentials_resolver import get_user_credentials

    creds = await get_user_credentials(session, current_user.id, ApiCredentialType.ANTHROPIC)
    if not creds:
        raise ValidationError("Anthropic ist nicht konfiguriert")

    try:
        endpoint = creds["endpoint"].rstrip("/")
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
                    "model": creds["model"],
                    "max_tokens": 5,
                    "messages": [{"role": "user", "content": "Say 'test'"}],
                },
            )
            if response.status_code == 200:
                return TestResultResponse(
                    success=True,
                    message="Anthropic-Verbindung erfolgreich",
                )
            else:
                error_text = response.text[:200] if response.text else "Unbekannter Fehler"
                return TestResultResponse(
                    success=False,
                    message="Anthropic-Verbindung fehlgeschlagen",
                    error=error_text,
                )
    except Exception as e:
        return TestResultResponse(
            success=False,
            message="Anthropic-Verbindung fehlgeschlagen",
            error=str(e),
        )


# =============================================================================
# Preview Test Endpoints (test credentials before saving)
# =============================================================================


@router.post("/preview-test/serpapi", response_model=TestResultResponse)
async def preview_test_serpapi(
    data: SerpApiCredentialsRequest,
    _: User = Depends(require_editor),
) -> TestResultResponse:
    """Test SerpAPI credentials before saving them."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                "https://serpapi.com/search.json",
                params={
                    "engine": "google",
                    "q": "test",
                    "num": 1,
                    "api_key": data.api_key,
                },
            )
            if response.status_code == 200:
                return TestResultResponse(
                    success=True,
                    message="SerpAPI-Verbindung erfolgreich",
                )
            else:
                error_text = response.text[:200] if response.text else "Unbekannter Fehler"
                return TestResultResponse(
                    success=False,
                    message="SerpAPI-Verbindung fehlgeschlagen",
                    error=error_text,
                )
    except Exception as e:
        return TestResultResponse(
            success=False,
            message="SerpAPI-Verbindung fehlgeschlagen",
            error=str(e),
        )


@router.post("/preview-test/serper", response_model=TestResultResponse)
async def preview_test_serper(
    data: SerperCredentialsRequest,
    _: User = Depends(require_editor),
) -> TestResultResponse:
    """Test Serper credentials before saving them."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://google.serper.dev/search",
                headers={
                    "X-API-KEY": data.api_key,
                    "Content-Type": "application/json",
                },
                json={"q": "test", "num": 1},
            )
            if response.status_code == 200:
                return TestResultResponse(
                    success=True,
                    message="Serper-Verbindung erfolgreich",
                )
            else:
                error_text = response.text[:200] if response.text else "Unbekannter Fehler"
                return TestResultResponse(
                    success=False,
                    message="Serper-Verbindung fehlgeschlagen",
                    error=error_text,
                )
    except Exception as e:
        return TestResultResponse(
            success=False,
            message="Serper-Verbindung fehlgeschlagen",
            error=str(e),
        )


@router.post("/preview-test/azure-openai", response_model=TestResultResponse)
async def preview_test_azure_openai(
    data: AzureOpenAICredentialsRequest,
    _: User = Depends(require_editor),
) -> TestResultResponse:
    """Test Azure credentials before saving them.

    Supports both Azure OpenAI and Azure AI Foundry (Claude).
    Uses the chat_url directly - user should paste the complete URL from Azure Portal.
    """
    try:
        # Determine which URL to test based on URL content
        url = data.chat_url
        is_embeddings = "/embeddings" in url
        is_anthropic = "/anthropic/" in url

        async with httpx.AsyncClient(timeout=30) as client:
            if is_embeddings:
                # Test embeddings endpoint
                response = await client.post(
                    url,
                    headers={
                        "api-key": data.api_key,
                        "Content-Type": "application/json",
                    },
                    json={"input": "test"},
                )
                service_name = "Azure Embeddings"
            elif is_anthropic:
                # Test Azure AI Foundry Claude endpoint
                # Uses x-api-key header (NOT api-key!)
                response = await client.post(
                    url,
                    headers={
                        "x-api-key": data.api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": data.model or "claude-3-5-sonnet-v2",
                        "max_tokens": 5,
                        "messages": [{"role": "user", "content": "Say 'test'"}],
                    },
                )
                service_name = "Azure Claude"
            else:
                # Test Azure OpenAI chat/completions endpoint
                response = await client.post(
                    url,
                    headers={
                        "api-key": data.api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "messages": [{"role": "user", "content": "Say 'test'"}],
                        "max_tokens": 5,
                    },
                )
                service_name = "Azure OpenAI"

            if response.status_code == 200:
                return TestResultResponse(
                    success=True,
                    message=f"{service_name}-Verbindung erfolgreich",
                )
            else:
                error_text = response.text[:200] if response.text else "Unbekannter Fehler"
                return TestResultResponse(
                    success=False,
                    message=f"{service_name}-Verbindung fehlgeschlagen",
                    error=error_text,
                )
    except Exception as e:
        return TestResultResponse(
            success=False,
            message="Azure-Verbindung fehlgeschlagen",
            error=str(e),
        )


@router.post("/preview-test/azure-openai-embeddings", response_model=TestResultResponse)
async def preview_test_azure_openai_embeddings(
    data: AzureOpenAICredentialsRequest,
    _: User = Depends(require_editor),
) -> TestResultResponse:
    """Test Azure OpenAI embeddings credentials before saving them.

    Uses the embeddings_url directly - user should paste the complete URL from Azure Portal.
    """
    try:
        url = data.embeddings_url
        if not url:
            return TestResultResponse(
                success=False,
                message="Keine Embeddings-URL angegeben",
                error="embeddings_url is required for embeddings test",
            )

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                url,
                headers={
                    "api-key": data.api_key,
                    "Content-Type": "application/json",
                },
                json={"input": "test"},
            )
            if response.status_code == 200:
                return TestResultResponse(
                    success=True,
                    message="Azure OpenAI Embeddings-Verbindung erfolgreich",
                )
            else:
                error_text = response.text[:200] if response.text else "Unbekannter Fehler"
                return TestResultResponse(
                    success=False,
                    message="Azure OpenAI Embeddings-Verbindung fehlgeschlagen",
                    error=error_text,
                )
    except Exception as e:
        return TestResultResponse(
            success=False,
            message="Azure OpenAI Embeddings-Verbindung fehlgeschlagen",
            error=str(e),
        )


@router.post("/preview-test/openai", response_model=TestResultResponse)
async def preview_test_openai(
    data: OpenAICredentialsRequest,
    _: User = Depends(require_editor),
) -> TestResultResponse:
    """Test standard OpenAI credentials before saving them."""
    try:
        headers = {
            "Authorization": f"Bearer {data.api_key}",
            "Content-Type": "application/json",
        }
        if data.organization:
            headers["OpenAI-Organization"] = data.organization

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json={
                    "model": data.model or "gpt-4o",
                    "messages": [{"role": "user", "content": "Say 'test'"}],
                    "max_tokens": 5,
                },
            )
            if response.status_code == 200:
                return TestResultResponse(
                    success=True,
                    message="OpenAI-Verbindung erfolgreich",
                )
            else:
                error_text = response.text[:200] if response.text else "Unbekannter Fehler"
                return TestResultResponse(
                    success=False,
                    message="OpenAI-Verbindung fehlgeschlagen",
                    error=error_text,
                )
    except Exception as e:
        return TestResultResponse(
            success=False,
            message="OpenAI-Verbindung fehlgeschlagen",
            error=str(e),
        )


@router.post("/preview-test/openai-embeddings", response_model=TestResultResponse)
async def preview_test_openai_embeddings(
    data: OpenAICredentialsRequest,
    _: User = Depends(require_editor),
) -> TestResultResponse:
    """Test standard OpenAI embeddings credentials before saving them."""
    try:
        headers = {
            "Authorization": f"Bearer {data.api_key}",
            "Content-Type": "application/json",
        }
        if data.organization:
            headers["OpenAI-Organization"] = data.organization

        # Use embeddings_model for embeddings test
        model = data.embeddings_model or "text-embedding-3-large"

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers=headers,
                json={
                    "model": model,
                    "input": "test",
                },
            )
            if response.status_code == 200:
                return TestResultResponse(
                    success=True,
                    message="OpenAI Embeddings-Verbindung erfolgreich",
                )
            else:
                error_text = response.text[:200] if response.text else "Unbekannter Fehler"
                return TestResultResponse(
                    success=False,
                    message="OpenAI Embeddings-Verbindung fehlgeschlagen",
                    error=error_text,
                )
    except Exception as e:
        return TestResultResponse(
            success=False,
            message="OpenAI Embeddings-Verbindung fehlgeschlagen",
            error=str(e),
        )


@router.post("/preview-test/anthropic", response_model=TestResultResponse)
async def preview_test_anthropic(
    data: AnthropicCredentialsRequest,
    _: User = Depends(require_editor),
) -> TestResultResponse:
    """Test Anthropic credentials before saving them."""
    try:
        endpoint = (data.endpoint or "https://api.anthropic.com").rstrip("/")
        url = f"{endpoint}/v1/messages"

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                url,
                headers={
                    "x-api-key": data.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": data.model or "claude-opus-4-5",
                    "max_tokens": 5,
                    "messages": [{"role": "user", "content": "Say 'test'"}],
                },
            )
            if response.status_code == 200:
                return TestResultResponse(
                    success=True,
                    message="Anthropic-Verbindung erfolgreich",
                )
            else:
                error_text = response.text[:200] if response.text else "Unbekannter Fehler"
                return TestResultResponse(
                    success=False,
                    message="Anthropic-Verbindung fehlgeschlagen",
                    error=error_text,
                )
    except Exception as e:
        return TestResultResponse(
            success=False,
            message="Anthropic-Verbindung fehlgeschlagen",
            error=str(e),
        )
