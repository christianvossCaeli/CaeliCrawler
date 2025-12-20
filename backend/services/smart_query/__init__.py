"""
Smart Query Service - Modularized Package

This package provides AI-powered natural language queries and data manipulation
for the Entity-Facet system.

Modules:
- geographic_utils: Geographic alias resolution and search term expansion
- prompts: AI prompt templates
- schema_generator: Entity type schemas and extraction prompts
- utils: Utility functions (slug generation, JSON cleaning)
- entity_operations: Entity, Facet, Relation CRUD operations
- query_interpreter: AI-powered query interpretation
- query_executor: Smart query execution engine
- ai_generation: AI-powered configuration generation
- crawl_operations: Crawl command execution
- category_setup: Category setup with AI generation
- write_executor: Write command execution

Usage:
    from services.smart_query import SmartQueryService, smart_query, smart_write
"""

from typing import Any, Dict, Optional
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

# Re-export main functions for backwards compatibility
from .geographic_utils import (
    GERMAN_STATE_ALIASES,
    resolve_geographic_alias,
    expand_search_terms,
)
from .utils import generate_slug
from .schema_generator import (
    generate_entity_type_schema,
    generate_ai_extraction_prompt,
    generate_url_patterns,
)
from .entity_operations import (
    create_entity_type_from_command,
    find_entity_by_name,
    create_entity_from_command,
    create_facet_from_command,
    create_relation_from_command,
)
from .query_interpreter import (
    interpret_query,
    interpret_write_command,
    get_openai_client,
)
from .query_executor import execute_smart_query
from .ai_generation import (
    ai_generate_entity_type_config,
    ai_generate_category_config,
    ai_generate_crawl_config,
)
from .crawl_operations import (
    find_matching_data_sources,
    find_sources_for_crawl,
    execute_crawl_command,
)
from .category_setup import (
    create_category_setup_with_ai,
    create_category_setup,
)
from .write_executor import (
    execute_write_command,
    execute_combined_operations,
)

logger = structlog.get_logger()


class SmartQueryService:
    """
    Service class for smart query functionality.

    Provides KI-gestützte natürliche Sprache Abfragen.
    """

    def __init__(self, db: AsyncSession):
        """Initialize the SmartQueryService with a database session."""
        self.db = db
        self.logger = logger.bind(service="SmartQueryService")

    async def execute_query(
        self,
        query: str,
    ) -> Dict[str, Any]:
        """
        Execute a natural language query (read-only).

        Args:
            query: Natural language query string

        Returns:
            Query results as dictionary
        """
        self.logger.info("executing_query", query=query)
        return await smart_query(self.db, query, allow_write=False)

    async def smart_query(
        self,
        query: str,
        allow_write: bool = False,
        current_user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Execute a natural language query with optional write support.

        Args:
            query: Natural language query string
            allow_write: Whether to allow write operations
            current_user_id: Optional user ID for tracking

        Returns:
            Query results as dictionary
        """
        self.logger.info("smart_query", query=query, allow_write=allow_write)
        return await smart_query(self.db, query, allow_write=allow_write, current_user_id=current_user_id)


async def smart_query(
    session: AsyncSession,
    question: str,
    allow_write: bool = False,
    current_user_id: Optional[UUID] = None,
) -> Dict[str, Any]:
    """
    Execute a natural language query against the Entity-Facet system.

    1. Checks if this is a write command (if allow_write=True)
    2. If write: interprets and executes the command
    3. If read: interprets the question and executes the query
    4. Returns structured results
    """
    # First, check if this is a write command
    if allow_write:
        write_command = await interpret_write_command(question)
        if write_command and write_command.get("operation", "none") != "none":
            logger.info(
                "Executing write command",
                question=question,
                command=write_command,
            )
            result = await execute_write_command(session, write_command, current_user_id)
            result["original_question"] = question
            result["mode"] = "write"
            result["interpretation"] = write_command
            return result

    # Fall through to read query - pass session for dynamic prompt generation
    query_params = await interpret_query(question, session=session)

    if not query_params:
        # Return error when AI interpretation fails
        logger.error("AI interpretation failed", question=question)
        return {
            "error": True,
            "message": "KI-Interpretation fehlgeschlagen. Bitte versuchen Sie es erneut oder formulieren Sie die Anfrage anders.",
            "original_question": question,
            "mode": "read",
            "items": [],
            "total": 0,
        }

    logger.info(
        "Smart query interpreted",
        question=question,
        interpretation=query_params,
    )

    # Execute the query
    results = await execute_smart_query(session, query_params)
    results["original_question"] = question
    results["mode"] = "read"

    return results


async def smart_write(
    session: AsyncSession,
    command: str,
    current_user_id: Optional[UUID] = None,
) -> Dict[str, Any]:
    """
    Execute a write command in natural language.

    Convenience function that always allows write operations.
    """
    return await smart_query(session, command, allow_write=True, current_user_id=current_user_id)


# Export all public symbols
__all__ = [
    # Main service class
    "SmartQueryService",
    # Main functions
    "smart_query",
    "smart_write",
    # Geographic utilities
    "GERMAN_STATE_ALIASES",
    "resolve_geographic_alias",
    "expand_search_terms",
    # Utilities
    "generate_slug",
    # Schema generation
    "generate_entity_type_schema",
    "generate_ai_extraction_prompt",
    "generate_url_patterns",
    # Entity operations
    "create_entity_type_from_command",
    "find_entity_by_name",
    "create_entity_from_command",
    "create_facet_from_command",
    "create_relation_from_command",
    # Query interpretation
    "interpret_query",
    "interpret_write_command",
    "get_openai_client",
    # Query execution
    "execute_smart_query",
    # AI generation
    "ai_generate_entity_type_config",
    "ai_generate_category_config",
    "ai_generate_crawl_config",
    # Crawl operations
    "find_matching_data_sources",
    "find_sources_for_crawl",
    "execute_crawl_command",
    # Category setup
    "create_category_setup_with_ai",
    "create_category_setup",
    # Write execution
    "execute_write_command",
    "execute_combined_operations",
]
