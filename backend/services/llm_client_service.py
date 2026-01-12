"""
Centralized LLM Client Service.

This service provides a unified interface for creating LLM clients using
database-stored credentials. It supports both OpenAI and Azure OpenAI.

IMPORTANT: This service should be used instead of directly accessing
settings.azure_openai_* environment variables.

Usage:
    from services.llm_client_service import LLMClientService, LLMPurpose

    # Get client for embeddings
    client_service = LLMClientService(session)
    client, config = await client_service.get_client_for_purpose(user_id, LLMPurpose.EMBEDDINGS)

    # Or for system-wide operations (uses first available admin config)
    client, config = await client_service.get_system_client(LLMPurpose.EMBEDDINGS)
"""

import uuid
from typing import Any

import structlog
from openai import AsyncAzureOpenAI, AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.user_api_credentials import LLMProvider, LLMPurpose

from .credentials_resolver import get_openai_compatible_config

logger = structlog.get_logger(__name__)


class LLMClientService:
    """Service for creating LLM clients using database-stored credentials."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._client_cache: dict[str, tuple[Any, dict]] = {}

    async def get_client_for_purpose(
        self,
        user_id: uuid.UUID,
        purpose: LLMPurpose,
    ) -> tuple[AsyncOpenAI | AsyncAzureOpenAI | None, dict[str, Any] | None]:
        """
        Get an LLM client for a specific user and purpose.

        Args:
            user_id: User UUID
            purpose: LLM purpose (EMBEDDINGS, DOCUMENT_ANALYSIS, etc.)

        Returns:
            Tuple of (client, config) or (None, None) if no credentials configured
        """
        config = await get_openai_compatible_config(self.session, user_id, purpose)
        if not config:
            logger.warning(
                "No LLM credentials configured for user",
                user_id=str(user_id),
                purpose=purpose.value,
            )
            return None, None

        client = self._create_client(config)
        return client, config

    async def get_system_client(
        self,
        purpose: LLMPurpose,
    ) -> tuple[AsyncOpenAI | AsyncAzureOpenAI | None, dict[str, Any] | None]:
        """
        Get an LLM client for system-wide operations.

        This uses the first available admin user's credentials.
        Useful for background jobs that don't have a user context.

        Args:
            purpose: LLM purpose

        Returns:
            Tuple of (client, config) or (None, None) if no credentials configured
        """
        # Find first admin user with credentials
        admin_user = await self._get_admin_with_credentials()
        if not admin_user:
            logger.error("No admin user with LLM credentials found for system operation")
            return None, None

        return await self.get_client_for_purpose(admin_user.id, purpose)

    async def _get_admin_with_credentials(self) -> User | None:
        """Find an admin user who has LLM credentials configured."""
        from app.models.user_api_credentials import UserLLMConfig

        # Find admin users with active LLM configs
        result = await self.session.execute(
            select(User)
            .join(UserLLMConfig, UserLLMConfig.user_id == User.id)
            .where(
                User.is_active.is_(True),
                User.is_superuser.is_(True),
                UserLLMConfig.is_active.is_(True),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    def _create_client(self, config: dict[str, Any]) -> AsyncOpenAI | AsyncAzureOpenAI:
        """Create the appropriate client based on config type."""
        provider_type = config.get("type", "azure")

        if provider_type == "azure":
            # Check if this is Azure Claude (Anthropic on Azure)
            azure_provider = config.get("azure_provider", "openai")
            if azure_provider == "anthropic":
                raise ValueError(
                    "Azure Claude (Anthropic on Azure) is not supported via the OpenAI client. "
                    "Please use standard Azure OpenAI URLs for this feature, or configure "
                    "direct Anthropic API credentials for Plan-Mode/API-Discovery purposes."
                )

            return AsyncAzureOpenAI(
                azure_endpoint=config["endpoint"],
                api_key=config["api_key"],
                api_version=config.get("api_version", "2025-04-01-preview"),
            )
        elif provider_type == "openai":
            return AsyncOpenAI(
                api_key=config["api_key"],
                organization=config.get("organization"),
            )
        else:
            raise ValueError(f"Unknown LLM provider type: {provider_type}")

    def get_model_name(self, config: dict[str, Any], for_embeddings: bool = False) -> str:
        """Get the model/deployment name from config."""
        provider_type = config.get("type", "azure")

        if provider_type == "azure":
            if for_embeddings:
                return config.get("embeddings_deployment", config.get("deployment_name"))
            return config.get("deployment_name")
        elif provider_type == "openai":
            if for_embeddings:
                return config.get("embeddings_model", "text-embedding-3-large")
            return config.get("model", "gpt-4o")
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")

    def get_provider(self, config: dict[str, Any]) -> LLMProvider:
        """Get the LLMProvider enum from config."""
        provider_type = config.get("type", "azure")
        if provider_type == "azure":
            return LLMProvider.AZURE_OPENAI
        elif provider_type == "openai":
            return LLMProvider.OPENAI
        else:
            return LLMProvider.AZURE_OPENAI  # fallback


async def get_embedding_client(
    session: AsyncSession,
    user_id: uuid.UUID | None = None,
) -> tuple[AsyncOpenAI | AsyncAzureOpenAI | None, dict[str, Any] | None]:
    """
    Convenience function to get an embedding client.

    If no user_id provided, uses system client (first admin with credentials).
    """
    service = LLMClientService(session)

    if user_id:
        return await service.get_client_for_purpose(user_id, LLMPurpose.EMBEDDINGS)
    else:
        return await service.get_system_client(LLMPurpose.EMBEDDINGS)


async def get_document_analysis_client(
    session: AsyncSession,
    user_id: uuid.UUID | None = None,
) -> tuple[AsyncOpenAI | AsyncAzureOpenAI | None, dict[str, Any] | None]:
    """Convenience function to get a document analysis client."""
    service = LLMClientService(session)

    if user_id:
        return await service.get_client_for_purpose(user_id, LLMPurpose.DOCUMENT_ANALYSIS)
    else:
        return await service.get_system_client(LLMPurpose.DOCUMENT_ANALYSIS)


async def get_assistant_client(
    session: AsyncSession,
    user_id: uuid.UUID | None = None,
) -> tuple[AsyncOpenAI | AsyncAzureOpenAI | None, dict[str, Any] | None]:
    """Convenience function to get an assistant client."""
    service = LLMClientService(session)

    if user_id:
        return await service.get_client_for_purpose(user_id, LLMPurpose.ASSISTANT)
    else:
        return await service.get_system_client(LLMPurpose.ASSISTANT)
