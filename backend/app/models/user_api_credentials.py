"""User API Credentials model for storing encrypted external API keys.

This module implements a purpose-based API configuration system where users
can configure different providers for different purposes (e.g., document analysis,
embeddings, assistant chat, etc.).
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class LLMPurpose(str, enum.Enum):
    """Purposes for which LLM APIs can be configured.

    Each purpose can have a different provider configured.
    """

    # Web Search - for AI-powered source discovery
    WEB_SEARCH = "WEB_SEARCH"

    # Document Analysis - summarization, extraction, classification, vision
    DOCUMENT_ANALYSIS = "DOCUMENT_ANALYSIS"

    # Embeddings - semantic search, similarity matching
    EMBEDDINGS = "EMBEDDINGS"

    # Assistant - interactive chat assistant
    ASSISTANT = "ASSISTANT"

    # Plan Mode - Smart Query complex reasoning
    PLAN_MODE = "PLAN_MODE"

    # API Discovery - finding OParl endpoints
    API_DISCOVERY = "API_DISCOVERY"


class LLMProvider(str, enum.Enum):
    """Available LLM/API providers."""

    # Web Search Providers
    SERPAPI = "SERPAPI"
    SERPER = "SERPER"

    # LLM Providers
    AZURE_OPENAI = "AZURE_OPENAI"
    OPENAI = "OPENAI"
    ANTHROPIC = "ANTHROPIC"


# Which providers are valid for which purposes
PURPOSE_VALID_PROVIDERS: dict[LLMPurpose, list[LLMProvider]] = {
    LLMPurpose.WEB_SEARCH: [LLMProvider.SERPAPI, LLMProvider.SERPER],
    LLMPurpose.DOCUMENT_ANALYSIS: [LLMProvider.AZURE_OPENAI, LLMProvider.OPENAI, LLMProvider.ANTHROPIC],
    LLMPurpose.EMBEDDINGS: [LLMProvider.AZURE_OPENAI, LLMProvider.OPENAI],
    LLMPurpose.ASSISTANT: [LLMProvider.AZURE_OPENAI, LLMProvider.OPENAI, LLMProvider.ANTHROPIC],
    LLMPurpose.PLAN_MODE: [LLMProvider.ANTHROPIC, LLMProvider.AZURE_OPENAI, LLMProvider.OPENAI],
    LLMPurpose.API_DISCOVERY: [LLMProvider.ANTHROPIC, LLMProvider.AZURE_OPENAI, LLMProvider.OPENAI],
}

# Provider field requirements - core fields always required
PROVIDER_FIELDS: dict[LLMProvider, list[str]] = {
    LLMProvider.SERPAPI: ["api_key"],
    LLMProvider.SERPER: ["api_key"],
    LLMProvider.AZURE_OPENAI: ["endpoint", "api_key", "api_version", "deployment_name"],
    LLMProvider.OPENAI: ["api_key", "model"],
    LLMProvider.ANTHROPIC: ["endpoint", "api_key", "model"],
}

# Optional fields per provider (only validated if provided)
PROVIDER_OPTIONAL_FIELDS: dict[LLMProvider, list[str]] = {
    LLMProvider.SERPAPI: [],
    LLMProvider.SERPER: [],
    LLMProvider.AZURE_OPENAI: ["embeddings_deployment"],
    LLMProvider.OPENAI: ["organization", "embeddings_model"],
    LLMProvider.ANTHROPIC: [],
}

# Fields required for EMBEDDINGS purpose (in addition to core fields)
EMBEDDINGS_REQUIRED_FIELDS: dict[LLMProvider, list[str]] = {
    LLMProvider.AZURE_OPENAI: ["embeddings_deployment"],
    LLMProvider.OPENAI: ["embeddings_model"],
}

# Human-readable descriptions for purposes
PURPOSE_DESCRIPTIONS: dict[LLMPurpose, dict[str, str]] = {
    LLMPurpose.WEB_SEARCH: {
        "name_de": "Web-Suche",
        "name_en": "Web Search",
        "description_de": "Automatische Suche nach OParl-Endpunkten und kommunalen Datenquellen im Web.",
        "description_en": "Automatic search for OParl endpoints and municipal data sources on the web.",
        "icon": "mdi-magnify",
    },
    LLMPurpose.DOCUMENT_ANALYSIS: {
        "name_de": "Dokumentenanalyse",
        "name_en": "Document Analysis",
        "description_de": "Zusammenfassungen, Datenextraktion, Klassifizierung und Bildanalyse von Dokumenten.",
        "description_en": "Summaries, data extraction, classification, and image analysis of documents.",
        "icon": "mdi-file-document-outline",
    },
    LLMPurpose.EMBEDDINGS: {
        "name_de": "Embeddings (Semantische Suche)",
        "name_en": "Embeddings (Semantic Search)",
        "description_de": "Vektorisierung von Texten für ähnlichkeitsbasierte Suche und Matching.",
        "description_en": "Vectorization of texts for similarity-based search and matching.",
        "icon": "mdi-vector-polyline",
    },
    LLMPurpose.ASSISTANT: {
        "name_de": "KI-Assistent",
        "name_en": "AI Assistant",
        "description_de": "Interaktiver Chat-Assistent für Fragen und Analysen.",
        "description_en": "Interactive chat assistant for questions and analyses.",
        "icon": "mdi-robot",
    },
    LLMPurpose.PLAN_MODE: {
        "name_de": "Plan-Mode (Smart Query)",
        "name_en": "Plan Mode (Smart Query)",
        "description_de": "Komplexe Datenabfragen mit mehrstufiger Planung und Ausführung.",
        "description_en": "Complex data queries with multi-step planning and execution.",
        "icon": "mdi-brain",
    },
    LLMPurpose.API_DISCOVERY: {
        "name_de": "API-Entdeckung",
        "name_en": "API Discovery",
        "description_de": "Erweiterte Erkennung und Validierung von API-Endpunkten.",
        "description_en": "Advanced detection and validation of API endpoints.",
        "icon": "mdi-api",
    },
}

# Human-readable descriptions for providers
PROVIDER_DESCRIPTIONS: dict[LLMProvider, dict[str, str]] = {
    LLMProvider.SERPAPI: {
        "name": "SerpAPI",
        "description_de": "Google-Suche über SerpAPI.",
        "description_en": "Google Search via SerpAPI.",
    },
    LLMProvider.SERPER: {
        "name": "Serper",
        "description_de": "Alternative Google-Suche API mit günstigeren Preisen.",
        "description_en": "Alternative Google Search API with lower pricing.",
    },
    LLMProvider.AZURE_OPENAI: {
        "name": "Azure OpenAI",
        "description_de": "Microsoft Azure gehosteter OpenAI Service mit Enterprise-Features.",
        "description_en": "Microsoft Azure hosted OpenAI Service with enterprise features.",
    },
    LLMProvider.OPENAI: {
        "name": "OpenAI",
        "description_de": "Direkter Zugang zur OpenAI API.",
        "description_en": "Direct access to OpenAI API.",
    },
    LLMProvider.ANTHROPIC: {
        "name": "Anthropic Claude",
        "description_de": "Claude-Modelle von Anthropic für komplexe Analysen.",
        "description_en": "Claude models from Anthropic for complex analyses.",
    },
}


# Legacy alias for backwards compatibility
ApiCredentialType = LLMProvider
API_CREDENTIAL_DESCRIPTIONS = {
    provider: {
        "name": info["name"],
        "description_de": info["description_de"],
        "description_en": info["description_en"],
        "fields": PROVIDER_FIELDS.get(provider, []),
    }
    for provider, info in PROVIDER_DESCRIPTIONS.items()
}


class UserLLMConfig(Base):
    """User-specific LLM configuration per purpose.

    Each user can configure one provider per purpose. The credentials
    are encrypted using Fernet symmetric encryption before storage.

    The encrypted_data field contains a JSON object with provider-specific fields:
    - SerpAPI/Serper: {"api_key": "..."}
    - Azure OpenAI: {"endpoint": "...", "api_key": "...", "api_version": "...",
                     "deployment_name": "...", "embeddings_deployment": "..."}
    - OpenAI: {"api_key": "...", "organization": "...", "model": "...", "embeddings_model": "..."}
    - Anthropic: {"endpoint": "...", "api_key": "...", "model": "..."}
    """

    __tablename__ = "user_llm_config"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    purpose: Mapped[LLMPurpose] = mapped_column(
        Enum(LLMPurpose, name="llm_purpose"),
        nullable=False,
    )

    provider: Mapped[LLMProvider] = mapped_column(
        Enum(LLMProvider, name="llm_provider"),
        nullable=False,
    )

    # Encrypted credentials (Fernet-encrypted JSON)
    encrypted_data: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Usage tracking
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Error tracking
    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="llm_configs",
    )

    # Constraints: One configuration per user per purpose
    __table_args__ = (
        UniqueConstraint("user_id", "purpose", name="uq_user_llm_purpose"),
    )

    def __repr__(self) -> str:
        return f"<UserLLMConfig {self.purpose.value}={self.provider.value} for user {self.user_id}>"

    @classmethod
    def get_purpose_info(cls, purpose: LLMPurpose, language: str = "de") -> dict[str, Any]:
        """Get human-readable info for a purpose."""
        info = PURPOSE_DESCRIPTIONS.get(purpose, {})
        return {
            "name": info.get(f"name_{language}", info.get("name_de", purpose.value)),
            "description": info.get(f"description_{language}", info.get("description_de", "")),
            "icon": info.get("icon", "mdi-cog"),
            "valid_providers": [p.value for p in PURPOSE_VALID_PROVIDERS.get(purpose, [])],
        }

    @classmethod
    def get_provider_info(cls, provider: LLMProvider, language: str = "de") -> dict[str, Any]:
        """Get human-readable info for a provider."""
        info = PROVIDER_DESCRIPTIONS.get(provider, {})
        return {
            "name": info.get("name", provider.value),
            "description": info.get(f"description_{language}", info.get("description_de", "")),
            "fields": PROVIDER_FIELDS.get(provider, []),
        }


# Legacy model alias - keep for migration compatibility
class UserApiCredentials(Base):
    """Legacy model - use UserLLMConfig instead.

    This model is kept for backwards compatibility during migration.
    """

    __tablename__ = "user_api_credentials"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    credential_type: Mapped[LLMProvider] = mapped_column(
        Enum(LLMProvider, name="api_credential_type"),
        nullable=False,
    )

    encrypted_data: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="api_credentials",
    )

    __table_args__ = (
        UniqueConstraint("user_id", "credential_type", name="uq_user_credential_type"),
    )

    def __repr__(self) -> str:
        return f"<UserApiCredentials {self.credential_type.value} for user {self.user_id}>"

    @classmethod
    def get_description(cls, credential_type: LLMProvider, language: str = "de") -> dict[str, Any]:
        """Get human-readable description for a credential type."""
        info = API_CREDENTIAL_DESCRIPTIONS.get(credential_type, {})
        desc_key = f"description_{language}" if f"description_{language}" in info else "description_de"
        return {
            "name": info.get("name", credential_type.value),
            "description": info.get(desc_key, ""),
            "fields": info.get("fields", []),
        }
