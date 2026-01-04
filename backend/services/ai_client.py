"""Azure OpenAI Client Factory and Helper Functions.

This module centralizes Azure OpenAI client creation and common AI operations
to avoid code duplication across the codebase.

IMPORTANT: Global system-level Azure OpenAI credentials have been removed.
All AI operations now require user-specific credentials configured via the
API Credentials UI (/admin/api-credentials).

Use the user-aware factory functions:
- create_sync_client_for_user(azure_config) - For sync contexts
- create_async_client_for_user(azure_config) - For async contexts

Get user credentials via:
    from services.credentials_resolver import get_azure_openai_config
    config = await get_azure_openai_config(session, user_id)
"""

import json
import time
from typing import Any

import structlog
from openai import AsyncAzureOpenAI, AzureOpenAI

from app.models.llm_usage import LLMProvider, LLMTaskType
from services.llm_usage_tracker import record_llm_usage

logger = structlog.get_logger()

# Error message for deprecated global client usage
_DEPRECATED_MSG = (
    "Globale Azure OpenAI Credentials wurden entfernt. "
    "Bitte konfigurieren Sie Ihre API-Zugangsdaten unter /admin/api-credentials. "
    "Verwenden Sie create_sync_client_for_user() oder create_async_client_for_user() "
    "mit den User-Credentials aus dem credentials_resolver."
)


class SyncAzureOpenAIClientFactory:
    """DEPRECATED: Factory for creating synchronous Azure OpenAI clients.

    This class is deprecated. Use create_sync_client_for_user() instead
    with user-specific credentials from the credentials_resolver.

    Example:
        from services.credentials_resolver import get_azure_openai_config
        from services.ai_client import create_sync_client_for_user

        config = await get_azure_openai_config(session, user_id)
        if config:
            client = create_sync_client_for_user(config)
    """

    _instance: AzureOpenAI | None = None

    @classmethod
    def create_client(cls) -> AzureOpenAI:
        """DEPRECATED: Global credentials have been removed.

        Raises:
            ValueError: Always - use create_sync_client_for_user() instead
        """
        raise ValueError(_DEPRECATED_MSG)

    @classmethod
    def get_client(cls) -> AzureOpenAI:
        """DEPRECATED: Global credentials have been removed.

        Raises:
            ValueError: Always - use create_sync_client_for_user() instead
        """
        raise ValueError(_DEPRECATED_MSG)

    @classmethod
    def reset_client(cls) -> None:
        """Reset the shared client instance (useful for testing)."""
        cls._instance = None


# Convenience function - DEPRECATED
def get_sync_openai_client() -> AzureOpenAI:
    """DEPRECATED: Use create_sync_client_for_user() instead.

    Raises:
        ValueError: Always - use create_sync_client_for_user() instead
    """
    raise ValueError(_DEPRECATED_MSG)


class AzureOpenAIClientFactory:
    """DEPRECATED: Factory for creating Azure OpenAI clients.

    This class is deprecated. Use create_async_client_for_user() instead
    with user-specific credentials from the credentials_resolver.

    Example:
        from services.credentials_resolver import get_azure_openai_config
        from services.ai_client import create_async_client_for_user

        config = await get_azure_openai_config(session, user_id)
        if config:
            client = create_async_client_for_user(config)
    """

    _instance: AsyncAzureOpenAI | None = None

    @classmethod
    def create_client(cls) -> AsyncAzureOpenAI:
        """DEPRECATED: Global credentials have been removed.

        Raises:
            ValueError: Always - use create_async_client_for_user() instead
        """
        raise ValueError(_DEPRECATED_MSG)

    @classmethod
    def get_client(cls) -> AsyncAzureOpenAI:
        """DEPRECATED: Global credentials have been removed.

        Raises:
            ValueError: Always - use create_async_client_for_user() instead
        """
        raise ValueError(_DEPRECATED_MSG)

    @classmethod
    def reset_client(cls) -> None:
        """Reset the shared client instance (useful for testing)."""
        cls._instance = None


async def call_ai_with_json_response(
    client: AsyncAzureOpenAI,
    messages: list[dict[str, str]],
    deployment: str,
    temperature: float = 0.1,
    max_tokens: int = 4096,
    operation_name: str = "AI call",
) -> dict[str, Any]:
    """
    Call Azure OpenAI API with JSON response format.

    This is a helper function that handles common error cases and JSON parsing.

    Args:
        client: AsyncAzureOpenAI client instance
        messages: List of message dicts with 'role' and 'content'
        deployment: The deployment name to use (from user's azure_config)
        temperature: Model temperature (0.0-2.0)
        max_tokens: Maximum tokens in response
        operation_name: Name for error messages

    Returns:
        Parsed JSON response as dict

    Raises:
        RuntimeError: If AI call fails or response cannot be parsed
    """
    start_time = time.time()
    try:
        response = await client.chat.completions.create(
            model=deployment,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )

        # Record successful LLM usage
        if response.usage:
            await record_llm_usage(
                provider=LLMProvider.AZURE_OPENAI,
                model=deployment,
                task_type=LLMTaskType.CUSTOM,
                task_name="ai_client_generic_call",
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                duration_ms=int((time.time() - start_time) * 1000),
                is_error=False,
            )

        # Validate response structure
        if not response.choices:
            raise RuntimeError(f"{operation_name} Fehler: Leere Antwort vom AI-Service")

        content = response.choices[0].message.content
        if not content:
            raise RuntimeError(
                f"{operation_name} Fehler: Keine Inhalte in der AI-Antwort"
            )

        return json.loads(content)

    except json.JSONDecodeError as e:
        logger.error(
            "Failed to parse AI response as JSON",
            error=str(e),
            operation=operation_name,
        )
        raise RuntimeError(
            f"KI-Service Fehler: AI-Antwort konnte nicht verarbeitet werden - {str(e)}"
        ) from None
    except RuntimeError:
        # Re-raise our own RuntimeErrors
        raise
    except Exception as e:
        # Record error LLM usage
        await record_llm_usage(
            provider=LLMProvider.AZURE_OPENAI,
            model=deployment,
            task_type=LLMTaskType.CUSTOM,
            task_name="ai_client_generic_call",
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            duration_ms=int((time.time() - start_time) * 1000),
            is_error=True,
            error_message=str(e),
        )
        logger.exception(f"Azure OpenAI API call failed: {operation_name}")
        raise RuntimeError(f"KI-Service nicht erreichbar: {str(e)}") from None


def get_tokens_used(response) -> int | None:
    """Extract total tokens used from API response."""
    if response and hasattr(response, "usage") and response.usage:
        return response.usage.total_tokens
    return None


# =============================================================================
# User-Aware Client Factories
# =============================================================================


def create_sync_client_for_user(azure_config: dict[str, Any]) -> AzureOpenAI:
    """Create a sync Azure OpenAI client using user-specific credentials.

    This is the preferred method for creating clients in contexts where
    user credentials should be used instead of system-wide settings.

    Args:
        azure_config: Dict with keys:
            - endpoint: Azure OpenAI endpoint URL
            - api_key: API key
            - api_version: API version (e.g., "2025-04-01-preview")
            - deployment_name: Default deployment name
            - embeddings_deployment: Embeddings deployment name (optional)

    Returns:
        Configured AzureOpenAI client

    Raises:
        ValueError: If required config keys are missing

    Example:
        from services.credentials_resolver import get_azure_openai_config

        config = await get_azure_openai_config(session, user_id)
        if config:
            client = create_sync_client_for_user(config)
    """
    required_keys = ["endpoint", "api_key", "api_version"]
    missing_keys = [k for k in required_keys if not azure_config.get(k)]
    if missing_keys:
        raise ValueError(
            f"Azure OpenAI Konfiguration unvollständig. Fehlende Felder: {', '.join(missing_keys)}"
        )

    return AzureOpenAI(
        azure_endpoint=azure_config["endpoint"],
        api_key=azure_config["api_key"],
        api_version=azure_config["api_version"],
    )


def create_async_client_for_user(azure_config: dict[str, Any]) -> AsyncAzureOpenAI:
    """Create an async Azure OpenAI client using user-specific credentials.

    This is the preferred method for creating clients in async contexts where
    user credentials should be used instead of system-wide settings.

    Args:
        azure_config: Dict with keys:
            - endpoint: Azure OpenAI endpoint URL
            - api_key: API key
            - api_version: API version (e.g., "2025-04-01-preview")
            - deployment_name: Default deployment name
            - embeddings_deployment: Embeddings deployment name (optional)

    Returns:
        Configured AsyncAzureOpenAI client

    Raises:
        ValueError: If required config keys are missing

    Example:
        from services.credentials_resolver import get_azure_openai_config

        config = await get_azure_openai_config(session, user_id)
        if config:
            client = create_async_client_for_user(config)
    """
    required_keys = ["endpoint", "api_key", "api_version"]
    missing_keys = [k for k in required_keys if not azure_config.get(k)]
    if missing_keys:
        raise ValueError(
            f"Azure OpenAI Konfiguration unvollständig. Fehlende Felder: {', '.join(missing_keys)}"
        )

    return AsyncAzureOpenAI(
        azure_endpoint=azure_config["endpoint"],
        api_key=azure_config["api_key"],
        api_version=azure_config["api_version"],
    )


def get_deployment_name(azure_config: dict[str, Any]) -> str:
    """Get the deployment name from user config.

    Args:
        azure_config: User's Azure OpenAI configuration

    Returns:
        Deployment name for chat/completion operations
    """
    return azure_config.get("deployment_name", "gpt-4o")


def get_embeddings_deployment(azure_config: dict[str, Any]) -> str:
    """Get the embeddings deployment name from user config.

    Args:
        azure_config: User's Azure OpenAI configuration

    Returns:
        Deployment name for embeddings operations
    """
    return azure_config.get("embeddings_deployment", "text-embedding-3-large")
