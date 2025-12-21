"""AI Source Discovery Service.

KI-gesteuerter Datenquellen-Import basierend auf natürlichen Prompts.
Sucht im Web nach relevanten Datenquellen und extrahiert diese automatisch.

V2: KI-First Ansatz mit API-Vorschlägen und Validierung.
"""

from .discovery_service import AISourceDiscoveryService
from .models import (
    # Original models
    SearchStrategy,
    SearchResult,
    ExtractedSource,
    SourceWithTags,
    DiscoveryResult,
    DiscoveryRequest,
    DiscoveryImportRequest,
    # V2 models (KI-First)
    APISuggestion,
    APIValidationResult,
    ValidatedAPISource,
    DiscoveryResultV2,
)
from .api_validator import APIValidator, validate_api_suggestions

__all__ = [
    # Service
    "AISourceDiscoveryService",
    # Original models
    "SearchStrategy",
    "SearchResult",
    "ExtractedSource",
    "SourceWithTags",
    "DiscoveryResult",
    "DiscoveryRequest",
    "DiscoveryImportRequest",
    # V2 models (KI-First)
    "APISuggestion",
    "APIValidationResult",
    "ValidatedAPISource",
    "DiscoveryResultV2",
    # V2 utilities
    "APIValidator",
    "validate_api_suggestions",
]
