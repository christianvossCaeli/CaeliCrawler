"""AI Source Discovery Service.

KI-gesteuerter Datenquellen-Import basierend auf natürlichen Prompts.
Sucht im Web nach relevanten Datenquellen und extrahiert diese automatisch.
"""

from .discovery_service import AISourceDiscoveryService
from .models import (
    SearchStrategy,
    SearchResult,
    ExtractedSource,
    SourceWithTags,
    DiscoveryResult,
    DiscoveryRequest,
    DiscoveryImportRequest,
)

__all__ = [
    "AISourceDiscoveryService",
    "SearchStrategy",
    "SearchResult",
    "ExtractedSource",
    "SourceWithTags",
    "DiscoveryResult",
    "DiscoveryRequest",
    "DiscoveryImportRequest",
]
