"""Centralized service for resolving user API credentials.

This service retrieves and decrypts user-specific API credentials
for use in Celery tasks, API calls, and other services that need
external API access.

Supports two modes:
1. Legacy provider-based credentials (UserApiCredentials) - for backwards compatibility
2. Purpose-based configuration (UserLLMConfig) - new recommended approach

Azure OpenAI credentials support both URL-based (new) and component-based (legacy) formats.
Use normalize_azure_credentials() from ai_client to get a consistent format.

Example usage:
    from services.ai_client import (
        create_async_client_for_user,
        normalize_azure_credentials,
        get_deployment_name,
    )

    async with get_session() as session:
        # Recommended: Use get_openai_compatible_config for normalized config
        config = await get_openai_compatible_config(session, user_id, LLMPurpose.DOCUMENT_ANALYSIS)
        if config and config["type"] == "azure":
            client = create_async_client_for_user(config)
            deployment = get_deployment_name(config)

        # Alternative: Get raw credentials and normalize manually
        raw_creds = await get_azure_openai_config(session, user_id)
        if raw_creds:
            config = normalize_azure_credentials(raw_creds)
            client = create_async_client_for_user(config)

        # Or require credentials (raises error if not configured)
        config = await require_config_for_purpose(
            session, user_id,
            LLMPurpose.DOCUMENT_ANALYSIS,
        )
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import EncryptionError, EncryptionService
from app.core.exceptions import ConfigurationError
from app.models.user_api_credentials import (
    PURPOSE_DESCRIPTIONS,
    ApiCredentialType,
    LLMProvider,
    LLMPurpose,
    UserApiCredentials,
    UserLLMConfig,
)

logger = structlog.get_logger()


async def get_user_credentials(
    session: AsyncSession,
    user_id: UUID,
    credential_type: ApiCredentialType,
) -> dict[str, Any] | None:
    """Get decrypted credentials for a user.

    Args:
        session: Database session
        user_id: User UUID
        credential_type: Type of credential to retrieve

    Returns:
        Decrypted credential dict, or None if not configured
    """
    result = await session.execute(
        select(UserApiCredentials).where(
            UserApiCredentials.user_id == user_id,
            UserApiCredentials.credential_type == credential_type,
            UserApiCredentials.is_active.is_(True),
        )
    )
    cred = result.scalar_one_or_none()

    if not cred:
        logger.debug(
            "credential_not_found",
            user_id=str(user_id),
            credential_type=credential_type.value,
        )
        return None

    try:
        return EncryptionService.decrypt(cred.encrypted_data)
    except EncryptionError as e:
        logger.error(
            "credential_decryption_failed",
            user_id=str(user_id),
            credential_type=credential_type.value,
            error=str(e),
        )
        return None


async def require_user_credentials(
    session: AsyncSession,
    user_id: UUID,
    credential_type: ApiCredentialType,
    service_name: str = "",
) -> dict[str, Any]:
    """Get credentials or raise error if not configured.

    This is the preferred method when credentials are required for an operation.
    It provides a clear error message to the user about what needs to be configured.

    Args:
        session: Database session
        user_id: User UUID
        credential_type: Type of credential to retrieve
        service_name: Human-readable name for error messages (e.g., "Azure OpenAI")

    Returns:
        Decrypted credential dict

    Raises:
        ConfigurationError: If credentials are not configured or decryption fails
    """
    creds = await get_user_credentials(session, user_id, credential_type)
    if not creds:
        display_name = service_name or credential_type.value.replace("_", " ").title()
        raise ConfigurationError(
            f"{display_name} ist nicht konfiguriert. "
            f"Bitte konfigurieren Sie Ihre API-Zugangsdaten unter Einstellungen > API-Zugangsdaten."
        )
    return creds


async def get_azure_openai_config(
    session: AsyncSession,
    user_id: UUID,
) -> dict[str, Any] | None:
    """Get Azure OpenAI configuration for a user.

    Returns dict with keys (URL-based format):
        - type: "azure"
        - endpoint: Azure OpenAI endpoint URL (extracted from URL)
        - api_key: API key
        - api_version: API version (extracted from URL)
        - deployment_name: Deployment name (extracted from URL)
        - embeddings_deployment: Embeddings deployment name (optional)
        - chat_url: Original chat URL
        - embeddings_url: Original embeddings URL (optional)

    Note: Both URL-based (new) and component-based (legacy) credentials
    are supported. Use normalize_azure_credentials() if you need a
    consistent format.

    Returns:
        Configuration dict or None if not configured
    """
    return await get_user_credentials(session, user_id, ApiCredentialType.AZURE_OPENAI)


async def get_anthropic_config(
    session: AsyncSession,
    user_id: UUID,
) -> dict[str, Any] | None:
    """Get Anthropic configuration for a user.

    Returns dict with keys:
        - endpoint: API endpoint URL
        - api_key: API key
        - model: Model name (e.g., "claude-opus-4-5")

    Returns:
        Configuration dict or None if not configured
    """
    return await get_user_credentials(session, user_id, ApiCredentialType.ANTHROPIC)


async def ensure_search_credential_from_purpose(
    session: AsyncSession,
    user_id: UUID,
    provider: LLMProvider,
) -> str | None:
    """Ensure legacy search credentials exist for WEB_SEARCH purpose config.

    Returns the migrated API key if copied, otherwise None.
    """
    if provider not in (LLMProvider.SERPAPI, LLMProvider.SERPER):
        return None

    result = await session.execute(
        select(UserApiCredentials).where(
            UserApiCredentials.user_id == user_id,
            UserApiCredentials.credential_type == provider,
        )
    )
    existing = result.scalar_one_or_none()
    if existing and existing.is_active:
        return None

    config = await get_config_for_purpose(session, user_id, LLMPurpose.WEB_SEARCH)
    if not config or config["provider"] != provider:
        return None

    api_key = config.get("credentials", {}).get("api_key")
    if not api_key:
        return None

    encrypted = EncryptionService.encrypt({"api_key": api_key})

    if existing:
        existing.encrypted_data = encrypted
        existing.is_active = True
        existing.last_error = None
    else:
        session.add(
            UserApiCredentials(
                user_id=user_id,
                credential_type=provider,
                encrypted_data=encrypted,
                is_active=True,
            )
        )

    await session.commit()
    logger.info(
        "search_credentials_migrated",
        user_id=str(user_id),
        provider=provider.value,
    )
    return api_key


async def get_search_api_config(
    session: AsyncSession,
    user_id: UUID,
) -> tuple[str, str] | None:
    """Get best available search API config.

    Tries SerpAPI first, then falls back to Serper.

    Returns:
        Tuple of (api_type, api_key) where api_type is "serpapi" or "serper",
        or None if no search API is configured
    """
    # Try SerpAPI first (preferred)
    serpapi_key = await get_serpapi_key(session, user_id)
    if serpapi_key:
        return ("serpapi", serpapi_key)

    # Fall back to Serper
    serper_key = await get_serper_key(session, user_id)
    if serper_key:
        return ("serper", serper_key)

    return None


async def get_serpapi_key(
    session: AsyncSession,
    user_id: UUID,
) -> str | None:
    """Get SerpAPI key for a user.

    Returns:
        API key string or None if not configured
    """
    creds = await get_user_credentials(session, user_id, ApiCredentialType.SERPAPI)
    if creds and creds.get("api_key"):
        return creds["api_key"]

    migrated_key = await ensure_search_credential_from_purpose(session, user_id, LLMProvider.SERPAPI)
    if migrated_key:
        return migrated_key

    return None


async def get_serper_key(
    session: AsyncSession,
    user_id: UUID,
) -> str | None:
    """Get Serper API key for a user.

    Returns:
        API key string or None if not configured
    """
    creds = await get_user_credentials(session, user_id, ApiCredentialType.SERPER)
    if creds and creds.get("api_key"):
        return creds["api_key"]

    migrated_key = await ensure_search_credential_from_purpose(session, user_id, LLMProvider.SERPER)
    if migrated_key:
        return migrated_key

    return None


async def update_credential_usage(
    session: AsyncSession,
    user_id: UUID,
    credential_type: ApiCredentialType,
    error: str | None = None,
) -> None:
    """Update last_used_at and optionally last_error for a credential.

    This should be called after using a credential to track usage
    and record any errors for debugging.

    Args:
        session: Database session
        user_id: User UUID
        credential_type: Type of credential
        error: Optional error message if the API call failed
    """
    result = await session.execute(
        select(UserApiCredentials).where(
            UserApiCredentials.user_id == user_id,
            UserApiCredentials.credential_type == credential_type,
        )
    )
    cred = result.scalar_one_or_none()

    if cred:
        cred.last_used_at = datetime.now(UTC)
        cred.last_error = error
        await session.commit()


async def check_user_has_credentials(
    session: AsyncSession,
    user_id: UUID,
    credential_types: list[ApiCredentialType] | None = None,
) -> dict[ApiCredentialType, bool]:
    """Check which credentials a user has configured.

    Args:
        session: Database session
        user_id: User UUID
        credential_types: Optional list of types to check. If None, checks all types.

    Returns:
        Dictionary mapping credential type to whether it's configured
    """
    types_to_check = credential_types or list(ApiCredentialType)

    result = await session.execute(
        select(UserApiCredentials.credential_type).where(
            UserApiCredentials.user_id == user_id,
            UserApiCredentials.is_active.is_(True),
        )
    )
    configured_types = {row[0] for row in result.fetchall()}

    return {cred_type: cred_type in configured_types for cred_type in types_to_check}


async def get_all_user_credentials_status(
    session: AsyncSession,
    user_id: UUID,
) -> list[dict[str, Any]]:
    """Get status of all credential types for a user.

    Returns:
        List of dicts with type, is_configured, is_active, last_used_at, last_error
    """
    result = await session.execute(
        select(UserApiCredentials).where(
            UserApiCredentials.user_id == user_id,
        )
    )
    credentials = {cred.credential_type: cred for cred in result.scalars().all()}

    status_list = []
    for cred_type in ApiCredentialType:
        cred = credentials.get(cred_type)
        status_list.append(
            {
                "type": cred_type.value,
                "is_configured": cred is not None,
                "is_active": cred.is_active if cred else False,
                "last_used_at": cred.last_used_at.isoformat() if cred and cred.last_used_at else None,
                "last_error": cred.last_error if cred else None,
            }
        )

    return status_list


# =============================================================================
# Purpose-based Configuration (New)
# =============================================================================


async def get_config_for_purpose(
    session: AsyncSession,
    user_id: UUID,
    purpose: LLMPurpose,
) -> dict[str, Any] | None:
    """Get decrypted configuration for a purpose.

    This is the new recommended way to get credentials.

    Args:
        session: Database session
        user_id: User UUID
        purpose: LLM purpose (e.g., DOCUMENT_ANALYSIS, EMBEDDINGS)

    Returns:
        Dict with 'provider' (LLMProvider) and 'credentials' (decrypted dict),
        or None if not configured
    """
    result = await session.execute(
        select(UserLLMConfig).where(
            UserLLMConfig.user_id == user_id,
            UserLLMConfig.purpose == purpose,
            UserLLMConfig.is_active.is_(True),
        )
    )
    config = result.scalar_one_or_none()

    if not config:
        logger.debug(
            "llm_config_not_found",
            user_id=str(user_id),
            purpose=purpose.value,
        )
        return None

    try:
        credentials = EncryptionService.decrypt(config.encrypted_data)
        return {
            "provider": config.provider,
            "credentials": credentials,
        }
    except EncryptionError as e:
        logger.error(
            "llm_config_decryption_failed",
            user_id=str(user_id),
            purpose=purpose.value,
            error=str(e),
        )
        return None


async def require_config_for_purpose(
    session: AsyncSession,
    user_id: UUID,
    purpose: LLMPurpose,
) -> dict[str, Any]:
    """Get configuration for a purpose or raise error if not configured.

    Args:
        session: Database session
        user_id: User UUID
        purpose: LLM purpose

    Returns:
        Dict with 'provider' (LLMProvider) and 'credentials' (decrypted dict)

    Raises:
        ConfigurationError: If purpose is not configured or decryption fails
    """
    config = await get_config_for_purpose(session, user_id, purpose)
    if not config:
        purpose_info = PURPOSE_DESCRIPTIONS.get(purpose, {})
        display_name = purpose_info.get("name_de", purpose.value)
        raise ConfigurationError(
            f"'{display_name}' ist nicht konfiguriert. "
            f"Bitte konfigurieren Sie die API-Zugangsdaten unter Einstellungen > API-Konfiguration."
        )
    return config


async def get_llm_config_for_purpose(
    session: AsyncSession,
    user_id: UUID,
    purpose: LLMPurpose,
) -> tuple[LLMProvider, dict[str, Any]] | None:
    """Get provider and credentials for a purpose.

    Convenience function that returns a tuple instead of dict.

    Returns:
        Tuple of (provider, credentials) or None if not configured
    """
    config = await get_config_for_purpose(session, user_id, purpose)
    if not config:
        return None
    return config["provider"], config["credentials"]


async def update_purpose_config_usage(
    session: AsyncSession,
    user_id: UUID,
    purpose: LLMPurpose,
    error: str | None = None,
) -> None:
    """Update last_used_at and optionally last_error for a purpose config.

    Args:
        session: Database session
        user_id: User UUID
        purpose: LLM purpose
        error: Optional error message if the API call failed
    """
    result = await session.execute(
        select(UserLLMConfig).where(
            UserLLMConfig.user_id == user_id,
            UserLLMConfig.purpose == purpose,
        )
    )
    config = result.scalar_one_or_none()

    if config:
        config.last_used_at = datetime.now(UTC)
        config.last_error = error
        await session.commit()


async def check_user_has_purpose_configs(
    session: AsyncSession,
    user_id: UUID,
    purposes: list[LLMPurpose] | None = None,
) -> dict[LLMPurpose, bool]:
    """Check which purposes a user has configured.

    Args:
        session: Database session
        user_id: User UUID
        purposes: Optional list of purposes to check. If None, checks all purposes.

    Returns:
        Dictionary mapping purpose to whether it's configured
    """
    purposes_to_check = purposes or list(LLMPurpose)

    result = await session.execute(
        select(UserLLMConfig.purpose).where(
            UserLLMConfig.user_id == user_id,
            UserLLMConfig.is_active.is_(True),
        )
    )
    configured_purposes = {row[0] for row in result.fetchall()}

    return {purpose: purpose in configured_purposes for purpose in purposes_to_check}


async def get_all_purpose_configs_status(
    session: AsyncSession,
    user_id: UUID,
) -> list[dict[str, Any]]:
    """Get status of all purpose configurations for a user.

    Returns:
        List of dicts with purpose, provider, is_configured, is_active,
        last_used_at, last_error
    """
    result = await session.execute(
        select(UserLLMConfig).where(
            UserLLMConfig.user_id == user_id,
        )
    )
    configs = {config.purpose: config for config in result.scalars().all()}

    status_list = []
    for purpose in LLMPurpose:
        config = configs.get(purpose)
        purpose_info = PURPOSE_DESCRIPTIONS.get(purpose, {})
        status_list.append(
            {
                "purpose": purpose.value,
                "purpose_name": purpose_info.get("name_de", purpose.value),
                "provider": config.provider.value if config else None,
                "is_configured": config is not None,
                "is_active": config.is_active if config else False,
                "last_used_at": config.last_used_at.isoformat() if config and config.last_used_at else None,
                "last_error": config.last_error if config else None,
            }
        )

    return status_list


# =============================================================================
# Hybrid resolver (tries new system first, falls back to legacy)
# =============================================================================


async def get_openai_compatible_config(
    session: AsyncSession,
    user_id: UUID,
    purpose: LLMPurpose,
) -> dict[str, Any] | None:
    """Get OpenAI-compatible configuration for a purpose.

    Tries purpose-based config first, then falls back to legacy provider-based.
    Returns a normalized config dict that works with OpenAI/Azure OpenAI clients.

    Args:
        session: Database session
        user_id: User UUID
        purpose: LLM purpose

    Returns:
        Dict with normalized OpenAI config, or None if not configured.
        For Azure: {type: "azure", endpoint, api_key, api_version, deployment_name, embeddings_deployment}
        For OpenAI: {type: "openai", api_key, organization?, model, embeddings_model}
    """
    from services.ai_client import normalize_azure_credentials

    def _normalize_openai_creds(creds: dict[str, Any]) -> dict[str, Any]:
        """Helper to normalize OpenAI credentials."""
        return {
            "type": "openai",
            "api_key": creds.get("api_key"),
            "organization": creds.get("organization"),
            "model": creds.get("model", "gpt-4o"),
            "embeddings_model": creds.get("embeddings_model", "text-embedding-3-large"),
        }

    # Try new purpose-based config first
    config = await get_config_for_purpose(session, user_id, purpose)
    if config:
        provider = config["provider"]
        creds = config["credentials"]

        if provider == LLMProvider.AZURE_OPENAI:
            return normalize_azure_credentials(creds)
        elif provider == LLMProvider.OPENAI:
            return _normalize_openai_creds(creds)

    # Fall back to legacy provider-based config
    # Try Azure OpenAI first
    azure_creds = await get_user_credentials(session, user_id, ApiCredentialType.AZURE_OPENAI)
    if azure_creds:
        return normalize_azure_credentials(azure_creds)

    # Try standard OpenAI
    openai_creds = await get_user_credentials(session, user_id, ApiCredentialType.OPENAI)
    if openai_creds:
        return _normalize_openai_creds(openai_creds)

    return None


async def get_anthropic_compatible_config(
    session: AsyncSession,
    user_id: UUID,
    purpose: LLMPurpose,
) -> dict[str, Any] | None:
    """Get Anthropic configuration for a purpose.

    Tries purpose-based config first, then falls back to legacy.

    Returns:
        Dict with {endpoint, api_key, model} or None
    """
    # Try new purpose-based config first
    config = await get_config_for_purpose(session, user_id, purpose)
    if config and config["provider"] == LLMProvider.ANTHROPIC:
        creds = config["credentials"]
        return {
            "endpoint": creds.get("endpoint", "https://api.anthropic.com"),
            "api_key": creds.get("api_key"),
            "model": creds.get("model", "claude-opus-4-5"),
        }

    # Fall back to legacy
    return await get_anthropic_config(session, user_id)


async def get_search_config_for_purpose(
    session: AsyncSession,
    user_id: UUID,
) -> tuple[str, str] | None:
    """Get search API configuration (for WEB_SEARCH purpose).

    Uses SerpAPI as primary and Serper as fallback across both systems.

    Returns:
        Tuple of (api_type, api_key) where api_type is "serpapi" or "serper",
        or None if no search API is configured
    """
    return await get_search_api_config(session, user_id)
