"""
AI Source Discovery Operation.

This module implements the discover_sources operation using the
command pattern framework. It serves as an example for migrating
other operations from write_executor.py.

Migration Guide:
    1. Create a new operation class inheriting from WriteOperation
    2. Implement the execute() method
    3. Add @register_operation decorator with operation name
    4. Optionally override validate() for input validation
    5. The operation is automatically available via execute_operation()
"""

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from services.ai_source_discovery import AISourceDiscoveryService

from .base import OperationResult, WriteOperation, register_operation

logger = structlog.get_logger()


@register_operation("discover_sources")
class DiscoverSourcesOperation(WriteOperation):
    """
    AI-powered data source discovery operation.

    Uses the AISourceDiscoveryService to find data sources
    based on natural language prompts.

    Command Parameters:
        - prompt: Natural language search prompt (required)
        - max_results: Maximum number of results (default: 50)
        - search_depth: "quick", "standard", or "deep" (default: "standard")

    Example Command:
        {
            "operation": "discover_sources",
            "prompt": "Alle Bundesliga-Vereine",
            "max_results": 50,
            "search_depth": "standard"
        }
    """

    def validate(self, command: dict[str, Any]) -> str | None:
        """Validate discover_sources command."""
        prompt = command.get("prompt", "")
        if not prompt or not prompt.strip():
            return "Ein Suchprompt ist erforderlich"

        max_results = command.get("max_results", 50)
        if not isinstance(max_results, int) or max_results < 1 or max_results > 200:
            return "max_results muss zwischen 1 und 200 liegen"

        search_depth = command.get("search_depth", "standard")
        if search_depth not in ["quick", "standard", "deep"]:
            return "search_depth muss 'quick', 'standard' oder 'deep' sein"

        return None

    async def execute(
        self,
        session: AsyncSession,
        command: dict[str, Any],
        user_id: UUID | None = None,
    ) -> OperationResult:
        """
        Execute the AI source discovery.

        Args:
            session: Database session (not used directly, but available)
            command: Discovery parameters
            user_id: User requesting the discovery

        Returns:
            OperationResult with discovered sources
        """
        prompt = command.get("prompt", "")
        max_results = command.get("max_results", 50)
        search_depth = command.get("search_depth", "standard")

        logger.info(
            "Executing discover_sources operation",
            prompt=prompt,
            max_results=max_results,
            search_depth=search_depth,
            user_id=str(user_id) if user_id else None,
        )

        try:
            service = AISourceDiscoveryService()
            discovery_result = await service.discover_sources(
                prompt=prompt,
                max_results=max_results,
                search_depth=search_depth,
            )

            sources_count = len(discovery_result.sources)

            return OperationResult(
                success=True,
                message=f"{sources_count} Datenquellen gefunden",
                operation="discover_sources",
                data={
                    "sources": [
                        {
                            "name": s.name,
                            "base_url": s.base_url,
                            "source_type": s.source_type,
                            "tags": s.tags,
                            "confidence": s.confidence,
                            "metadata": s.metadata,
                        }
                        for s in discovery_result.sources
                    ],
                    "search_strategy": (
                        discovery_result.search_strategy.model_dump()
                        if discovery_result.search_strategy
                        else None
                    ),
                    "stats": discovery_result.stats.model_dump(),
                    "warnings": discovery_result.warnings,
                },
            )

        except Exception as e:
            logger.error(
                "Source discovery failed",
                prompt=prompt,
                error=str(e),
                exc_info=True,
            )
            return OperationResult(
                success=False,
                message=f"Quellensuche fehlgeschlagen: {str(e)}",
                operation="discover_sources",
                error=str(e),
            )
