"""API import operations for Smart Query Service.

Operations:
- fetch_and_create_from_api: Fetch data from APIs and create entities

Note: The fetch_and_create_from_api operation is complex (400+ lines) and is
kept as a standalone function for maintainability. The Command class
delegates to this function.
"""

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from .base import OperationResult, WriteOperation, register_operation

logger = structlog.get_logger()


@register_operation("fetch_and_create_from_api")
class FetchAndCreateFromApiOperation(WriteOperation):
    """Fetch data from external APIs and create entities.

    Supports:
    - Wikidata SPARQL queries (DE/AT/GB municipalities, states, councils)
    - REST APIs with predefined templates
    - Automatic parent entity creation for hierarchies
    - Entity matching to link imported items to existing entities
    """

    async def execute(
        self,
        session: AsyncSession,
        command: dict[str, Any],
        user_id: UUID | None = None,
    ) -> OperationResult:
        # Import the complex implementation from the dedicated module
        from .api_import_impl import execute_fetch_and_create

        fetch_data = command.get("fetch_and_create_data", {})
        result = await execute_fetch_and_create(session, fetch_data)

        created_items = []
        if result.get("success"):
            created_items.append({
                "type": "api_import",
                "created_count": result.get("created_count", 0),
                "existing_count": result.get("existing_count", 0),
                "entity_type": result.get("entity_type"),
            })

        return OperationResult(
            success=result.get("success", False),
            message=result.get("message", ""),
            created_items=created_items,
            data={
                "created_count": result.get("created_count", 0),
                "existing_count": result.get("existing_count", 0),
                "error_count": result.get("error_count", 0),
                "total_fetched": result.get("total_fetched", 0),
                "entity_type": result.get("entity_type"),
                "parent_type": result.get("parent_type"),
                "matched_count": result.get("matched_count", 0),
                "warnings": result.get("warnings", []),
            },
        )


# Note: discover_sources is already registered in discovery.py
