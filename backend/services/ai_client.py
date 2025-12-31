"""Azure OpenAI Client Factory and Helper Functions.

This module centralizes Azure OpenAI client creation and common AI operations
to avoid code duplication across the codebase.

Provides both sync and async client factories:
- AzureOpenAIClientFactory: Async client for async contexts (FastAPI endpoints, async tasks)
- SyncAzureOpenAIClientFactory: Sync client for sync contexts (Celery workers, streaming)
"""

import json
import time
from typing import Any

import structlog
from openai import AsyncAzureOpenAI, AzureOpenAI

from app.config import settings
from app.models.llm_usage import LLMProvider, LLMTaskType
from services.llm_usage_tracker import record_llm_usage

logger = structlog.get_logger()


class SyncAzureOpenAIClientFactory:
    """Factory for creating synchronous Azure OpenAI clients.

    Use this for:
    - Celery workers (sync context)
    - Streaming responses (SSE)
    - Any non-async code paths
    """

    _instance: AzureOpenAI | None = None

    @classmethod
    def create_client(cls) -> AzureOpenAI:
        """Create a new sync Azure OpenAI client instance.

        Returns:
            Configured AzureOpenAI client

        Raises:
            ValueError: If Azure OpenAI is not configured
        """
        if not settings.azure_openai_api_key:
            raise ValueError(
                "KI-Service nicht erreichbar: Azure OpenAI ist nicht konfiguriert"
            )

        return AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )

    @classmethod
    def get_client(cls) -> AzureOpenAI:
        """Get a shared sync Azure OpenAI client instance (singleton).

        Returns:
            Shared AzureOpenAI client

        Raises:
            ValueError: If Azure OpenAI is not configured
        """
        if cls._instance is None:
            cls._instance = cls.create_client()
        return cls._instance

    @classmethod
    def reset_client(cls) -> None:
        """Reset the shared client instance (useful for testing)."""
        cls._instance = None


# Convenience function for backward compatibility
def get_sync_openai_client() -> AzureOpenAI:
    """Get a shared sync Azure OpenAI client.

    This is a convenience function that wraps SyncAzureOpenAIClientFactory.get_client().

    Returns:
        Shared AzureOpenAI client

    Raises:
        ValueError: If Azure OpenAI is not configured
    """
    return SyncAzureOpenAIClientFactory.get_client()


class AzureOpenAIClientFactory:
    """Factory for creating Azure OpenAI clients with consistent configuration."""

    _instance: AsyncAzureOpenAI | None = None

    @classmethod
    def create_client(cls) -> AsyncAzureOpenAI:
        """
        Create a new Azure OpenAI client instance.

        Returns:
            Configured AsyncAzureOpenAI client

        Raises:
            ValueError: If Azure OpenAI is not configured
        """
        if not settings.azure_openai_api_key:
            raise ValueError(
                "KI-Service nicht erreichbar: Azure OpenAI ist nicht konfiguriert"
            )

        return AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )

    @classmethod
    def get_client(cls) -> AsyncAzureOpenAI:
        """
        Get a shared Azure OpenAI client instance (singleton pattern).

        This is useful for reusing connections within a single request.

        Returns:
            Shared AsyncAzureOpenAI client

        Raises:
            ValueError: If Azure OpenAI is not configured
        """
        if cls._instance is None:
            cls._instance = cls.create_client()
        return cls._instance

    @classmethod
    def reset_client(cls) -> None:
        """Reset the shared client instance (useful for testing)."""
        cls._instance = None


async def call_ai_with_json_response(
    client: AsyncAzureOpenAI,
    messages: list[dict[str, str]],
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
        temperature: Model temperature (0.0-2.0)
        max_tokens: Maximum tokens in response
        operation_name: Name for error messages

    Returns:
        Parsed JSON response as dict

    Raises:
        RuntimeError: If AI call fails or response cannot be parsed
    """
    deployment = settings.azure_openai_deployment_name
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
