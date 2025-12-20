"""Azure OpenAI Client Factory and Helper Functions.

This module centralizes Azure OpenAI client creation and common AI operations
to avoid code duplication across the codebase.
"""

import json
from typing import Any, Dict, List, Optional

import structlog
from openai import AsyncAzureOpenAI

from app.config import settings

logger = structlog.get_logger()


class AzureOpenAIClientFactory:
    """Factory for creating Azure OpenAI clients with consistent configuration."""

    _instance: Optional[AsyncAzureOpenAI] = None

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
    messages: List[Dict[str, str]],
    temperature: float = 0.1,
    max_tokens: int = 4096,
    operation_name: str = "AI call",
) -> Dict[str, Any]:
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
    try:
        response = await client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
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
        )
    except RuntimeError:
        # Re-raise our own RuntimeErrors
        raise
    except Exception as e:
        logger.exception(f"Azure OpenAI API call failed: {operation_name}")
        raise RuntimeError(f"KI-Service nicht erreichbar: {str(e)}")


def get_tokens_used(response) -> Optional[int]:
    """Extract total tokens used from API response."""
    if response and hasattr(response, "usage") and response.usage:
        return response.usage.total_tokens
    return None
