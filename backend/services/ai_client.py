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
import re
import time
from typing import Any
from urllib.parse import parse_qs, urlparse

import structlog
from openai import AsyncAzureOpenAI, AzureOpenAI

from app.models.llm_usage import LLMProvider, LLMTaskType
from services.llm_usage_tracker import record_llm_usage

logger = structlog.get_logger()


# =============================================================================
# Azure URL Parsing Helpers
# =============================================================================


def parse_azure_url(url: str) -> dict[str, str]:
    """Parse an Azure URL into its components.

    Supports both Azure OpenAI and Azure Claude (Anthropic) URLs:

    Azure OpenAI:
        https://xxx.cognitiveservices.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-02-15

    Azure Claude:
        https://xxx.services.ai.azure.com/anthropic/v1/messages

    Args:
        url: Complete Azure URL

    Returns:
        Dict with keys: endpoint, deployment (optional), api_version, provider_type ("openai" or "anthropic")

    Raises:
        ValueError: If URL is not a valid Azure URL
    """
    try:
        parsed = urlparse(url)

        # Extract base endpoint (scheme + host)
        endpoint = f"{parsed.scheme}://{parsed.netloc}"

        # Try Azure OpenAI format: /openai/deployments/{deployment}/{operation}
        openai_match = re.match(
            r"/openai/deployments/([^/]+)/(chat/completions|embeddings|completions)",
            parsed.path,
        )
        if openai_match:
            deployment = openai_match.group(1)
            operation_type = openai_match.group(2)

            # Parse api-version from query string
            query_params = parse_qs(parsed.query)
            api_version = query_params.get("api-version", ["2024-02-15"])[0]

            return {
                "endpoint": endpoint,
                "deployment": deployment,
                "api_version": api_version,
                "operation_type": operation_type,
                "provider_type": "openai",
            }

        # Try Azure Claude format: /anthropic/v1/messages
        anthropic_match = re.match(r"/anthropic/v1/(messages|completions)", parsed.path)
        if anthropic_match:
            return {
                "endpoint": endpoint,
                "deployment": None,
                "api_version": "2024-06-01",  # Default for Azure Claude
                "operation_type": anthropic_match.group(1),
                "provider_type": "anthropic",
            }

        raise ValueError(f"Unrecognized Azure URL format: {parsed.path}")

    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Could not parse Azure URL: {url}. Error: {e}") from e


# Backward compatibility alias
def parse_azure_openai_url(url: str) -> dict[str, str]:
    """Parse an Azure OpenAI URL into its components.

    DEPRECATED: Use parse_azure_url instead which also supports Azure Claude URLs.
    """
    result = parse_azure_url(url)
    if result.get("provider_type") != "openai":
        raise ValueError(f"Expected Azure OpenAI URL, got {result.get('provider_type')} URL")
    return result


def create_azure_config_from_urls(
    chat_url: str,
    api_key: str,
    embeddings_url: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Create a normalized Azure config dict from URL-based credentials.

    Supports both Azure OpenAI and Azure Claude (Anthropic) URLs.

    Args:
        chat_url: Complete URL for chat/completions endpoint
        api_key: Azure API key
        embeddings_url: Optional URL for embeddings endpoint (Azure OpenAI only)
        model: Model name (required for Azure Claude, e.g., "claude-opus-4-5")

    Returns:
        Dict compatible with LLMClientService._create_client
    """
    chat_parsed = parse_azure_url(chat_url)
    provider_type = chat_parsed.get("provider_type", "openai")

    config: dict[str, Any] = {
        "type": "azure",
        "azure_provider": provider_type,  # "openai" or "anthropic"
        "endpoint": chat_parsed["endpoint"],
        "api_key": api_key,
        "api_version": chat_parsed["api_version"],
        "chat_url": chat_url,
    }

    if provider_type == "openai":
        # Azure OpenAI - deployment from URL
        config["deployment_name"] = chat_parsed["deployment"]

        if embeddings_url:
            embeddings_parsed = parse_azure_url(embeddings_url)
            config["embeddings_deployment"] = embeddings_parsed.get("deployment")
            config["embeddings_url"] = embeddings_url
        else:
            config["embeddings_deployment"] = chat_parsed["deployment"]

    elif provider_type == "anthropic":
        # Azure Claude - requires model name and uses different API
        if not model:
            raise ValueError("Model name is required for Azure Claude (e.g., 'claude-opus-4-5')")
        config["model"] = model
        config["deployment_name"] = None  # No deployment for Azure Claude
        logger.warning(
            "azure_claude_url_detected",
            msg="Azure Claude URLs detected. This requires Anthropic API format, not OpenAI.",
        )

    return config


def normalize_azure_credentials(creds: dict[str, Any]) -> dict[str, Any]:
    """Normalize Azure credentials to a consistent format.

    Supports both URL-based (new) and component-based (legacy) credential formats.
    Also supports Azure Claude (Anthropic on Azure) via URL detection.

    Args:
        creds: Credentials dict (either URL-based or component-based)

    Returns:
        Normalized config dict with all required fields
    """
    chat_url = creds.get("chat_url", "").strip() if creds.get("chat_url") else ""
    embeddings_url = creds.get("embeddings_url", "").strip() if creds.get("embeddings_url") else ""

    if chat_url:
        # New URL-based format - parse and normalize
        return create_azure_config_from_urls(
            chat_url=chat_url,
            api_key=creds["api_key"],
            embeddings_url=embeddings_url or None,
            model=creds.get("model"),  # Required for Azure Claude
        )
    elif embeddings_url:
        # Embeddings-only configuration (no chat URL)
        # Derive config from embeddings URL
        embeddings_parsed = parse_azure_url(embeddings_url)
        return {
            "type": "azure",
            "azure_provider": embeddings_parsed.get("provider_type", "openai"),
            "endpoint": embeddings_parsed["endpoint"],
            "api_key": creds["api_key"],
            "api_version": embeddings_parsed.get("api_version", "2025-04-01-preview"),
            "deployment_name": None,  # No chat deployment
            "embeddings_deployment": embeddings_parsed.get("deployment"),
            "embeddings_url": embeddings_url,
        }
    else:
        # Legacy component-based format - already normalized
        return {
            "type": "azure",
            "endpoint": creds.get("endpoint"),
            "api_key": creds.get("api_key"),
            "api_version": creds.get("api_version", "2025-04-01-preview"),
            "deployment_name": creds.get("deployment_name"),
            "embeddings_deployment": creds.get("embeddings_deployment"),
        }


def get_azure_test_url(creds: dict[str, Any], for_embeddings: bool = False) -> str:
    """Get the appropriate test URL from Azure credentials.

    Args:
        creds: Credentials dict (either URL-based or component-based)
        for_embeddings: If True, return embeddings URL; otherwise chat URL

    Returns:
        Complete URL for testing
    """
    if for_embeddings and creds.get("embeddings_url"):
        return creds["embeddings_url"]

    if creds.get("chat_url"):
        return creds["chat_url"]

    # Legacy format - construct URL
    endpoint = creds["endpoint"].rstrip("/")
    deployment = creds["deployment_name"] if not for_embeddings else creds.get("embeddings_deployment", creds["deployment_name"])
    api_version = creds.get("api_version", "2025-04-01-preview")
    operation = "embeddings" if for_embeddings else "chat/completions"

    return f"{endpoint}/openai/deployments/{deployment}/{operation}?api-version={api_version}"

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
            raise RuntimeError(f"{operation_name} Fehler: Keine Inhalte in der AI-Antwort")

        return json.loads(content)

    except json.JSONDecodeError as e:
        logger.error(
            "Failed to parse AI response as JSON",
            error=str(e),
            operation=operation_name,
        )
        raise RuntimeError(f"KI-Service Fehler: AI-Antwort konnte nicht verarbeitet werden - {str(e)}") from None
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
        raise ValueError(f"Azure OpenAI Konfiguration unvollständig. Fehlende Felder: {', '.join(missing_keys)}")

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
        raise ValueError(f"Azure OpenAI Konfiguration unvollständig. Fehlende Felder: {', '.join(missing_keys)}")

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
