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

import asyncio
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

# Re-export main functions for backwards compatibility
from .geographic_utils import (
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
    interpret_plan_query,
    interpret_plan_query_stream,
    get_openai_client,
    detect_compound_query,
    invalidate_types_cache,
)
from .query_executor import execute_smart_query
from .visualization_selector import VisualizationSelector
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


# Maximum number of sub-queries allowed in a compound query
MAX_COMPOUND_SUB_QUERIES = 5


async def _execute_single_sub_query(
    session: AsyncSession,
    sub_query: Dict[str, Any],
    viz_selector: VisualizationSelector,
) -> Dict[str, Any]:
    """
    Execute a single sub-query and return visualization data.

    This is an internal helper for parallel execution.

    Args:
        session: Database session
        sub_query: Sub-query configuration from compound detection
        viz_selector: Shared visualization selector instance

    Returns:
        Dict containing visualization config and data
    """
    query_id = sub_query.get("id") or str(uuid4())[:8]
    description = sub_query.get("description", "Query")
    query_config = sub_query.get("query_config", {})
    viz_hint = sub_query.get("visualization_hint")

    try:
        logger.info(
            "Executing sub-query",
            id=query_id,
            description=description,
            entity_type=query_config.get("entity_type"),
        )

        # Execute the sub-query
        result = await execute_smart_query(session, query_config)
        items = result.get("items", [])

        # Select visualization
        viz_config = await viz_selector.select_visualization(
            data=items,
            user_query=description,
            facet_types=query_config.get("facet_types", []),
            user_hint=viz_hint,
        )

        return {
            "id": query_id,
            "title": viz_config.title or description,
            "visualization": viz_config.model_dump() if hasattr(viz_config, 'model_dump') else viz_config.dict(),
            "data": items,
            "source_info": {
                "type": "internal",
                "last_updated": None,
            },
            "explanation": f"{len(items)} results found",
            "success": True,
        }

    except Exception as e:
        logger.error(
            "Sub-query execution failed",
            id=query_id,
            error=str(e),
            exc_info=True,
        )
        return {
            "id": query_id,
            "title": description,
            "visualization": {
                "type": "text",
                "title": "Error",
                "text_content": f"Query failed: {str(e)}",
            },
            "data": [],
            "source_info": None,
            "explanation": f"Error: {str(e)}",
            "success": False,
        }


async def execute_compound_query(
    session: AsyncSession,
    compound_detection: Dict[str, Any],
    original_question: str,
) -> Dict[str, Any]:
    """
    Execute a compound query by running multiple sub-queries in parallel.

    Compound queries allow users to request multiple distinct datasets
    in a single natural language query (e.g., "show table AND chart").

    Best Practices Applied:
    - Parallel Execution: Sub-queries run concurrently via asyncio.gather()
    - Fail-Safe: Individual failures don't block other sub-queries
    - Rate Limiting: Max sub-queries capped to prevent resource exhaustion

    Args:
        session: Database session
        compound_detection: Result from detect_compound_query() containing:
            - sub_queries: List of query configurations
            - reasoning: AI explanation for the decomposition
        original_question: The original user question

    Returns:
        CompoundQueryResponse-compatible dict with:
        - success: Overall operation success
        - is_compound: True (marker for frontend)
        - visualizations: List of visualization configs with data
        - explanation: AI reasoning
        - suggested_actions: Follow-up suggestions
    """
    sub_queries = compound_detection.get("sub_queries", [])

    # Validate and limit sub-queries
    if not sub_queries:
        logger.warning("Compound query has no sub-queries")
        return {
            "success": False,
            "is_compound": True,
            "visualizations": [],
            "explanation": "No sub-queries detected",
            "suggested_actions": [],
            "original_question": original_question,
            "mode": "read",
            "error": "No sub-queries found in compound detection",
        }

    if len(sub_queries) > MAX_COMPOUND_SUB_QUERIES:
        logger.warning(
            "Too many sub-queries, limiting",
            requested=len(sub_queries),
            max_allowed=MAX_COMPOUND_SUB_QUERIES,
        )
        sub_queries = sub_queries[:MAX_COMPOUND_SUB_QUERIES]

    # Create shared visualization selector
    viz_selector = VisualizationSelector()

    # Execute all sub-queries in parallel
    logger.info(
        "Executing compound query",
        sub_query_count=len(sub_queries),
        question=original_question[:100],
    )

    tasks = [
        _execute_single_sub_query(session, sq, viz_selector)
        for sq in sub_queries
    ]

    visualizations = await asyncio.gather(*tasks)

    # Count successes for overall status
    success_count = sum(1 for v in visualizations if v.get("success", False))
    overall_success = success_count > 0

    # Remove internal success flag from visualizations
    for viz in visualizations:
        viz.pop("success", None)

    logger.info(
        "Compound query complete",
        total_sub_queries=len(sub_queries),
        successful=success_count,
        failed=len(sub_queries) - success_count,
    )

    return {
        "success": overall_success,
        "is_compound": True,
        "visualizations": list(visualizations),
        "explanation": compound_detection.get("reasoning"),
        "suggested_actions": [],
        "original_question": original_question,
        "mode": "read",
    }


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
    mode: Optional[str] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Execute a natural language query against the Entity-Facet system.

    1. If mode="plan": uses the Plan Mode assistant for interactive prompt help
    2. Checks if this is a write command (if allow_write=True)
    3. If write: interprets and executes the command
    4. If read: interprets the question and executes the query
    5. Returns structured results

    Args:
        session: Database session
        question: Natural language query/command
        allow_write: Whether to allow write operations
        current_user_id: Optional user ID for tracking
        mode: Optional mode override ("plan" for Plan Mode)
        conversation_history: Optional conversation history for Plan Mode
    """
    # Plan Mode - interactive assistant for prompt formulation
    if mode == "plan":
        logger.info(
            "Plan mode query",
            question=question[:100],
            history_length=len(conversation_history) if conversation_history else 0,
        )
        result = await interpret_plan_query(
            question=question,
            session=session,
            conversation_history=conversation_history,
        )
        result["original_question"] = question
        result["mode"] = "plan"
        return result

    # First, check if this is a write command
    if allow_write:
        write_command = await interpret_write_command(question, session)
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

    # Check if this is a compound query (multiple visualizations requested)
    try:
        compound_detection = await detect_compound_query(question, session=session)

        if compound_detection.get("is_compound") and compound_detection.get("sub_queries"):
            logger.info(
                "Compound query detected",
                question=question[:100],
                sub_query_count=len(compound_detection.get("sub_queries", [])),
                reasoning=compound_detection.get("reasoning", "")[:100],
            )
            return await execute_compound_query(session, compound_detection, question)

    except Exception as e:
        logger.warning(
            "Compound query detection failed, falling back to single query",
            error=str(e),
        )

    # Fall through to single read query - pass session for dynamic prompt generation
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

    # Execute the single query
    results = await execute_smart_query(session, query_params)

    # Apply visualization selection for single queries too
    viz_selector = VisualizationSelector()
    items = results.get("items", [])
    facet_types = query_params.get("facet_types", [])

    try:
        viz_config = await viz_selector.select_visualization(
            data=items,
            user_query=question,
            facet_types=facet_types,
        )
        results["visualization"] = viz_config.model_dump() if hasattr(viz_config, 'model_dump') else viz_config.dict()
    except Exception as e:
        logger.warning("Visualization selection failed", error=str(e))
        # Default to table visualization
        results["visualization"] = {
            "type": "table",
            "title": "Ergebnis",
        }

    results["original_question"] = question
    results["mode"] = "read"
    results["is_compound"] = False

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


async def smart_plan(
    session: AsyncSession,
    question: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Execute a Plan Mode query.

    The Plan Mode is an interactive assistant that helps users formulate
    the correct prompts for Smart Query. It uses Claude Opus and knows
    both the code implementation and database contents.

    Args:
        session: Database session
        question: User's question about how to use Smart Query
        conversation_history: Previous messages in the conversation

    Returns:
        Dict with:
        - success: Whether the request succeeded
        - message: The assistant's response
        - has_generated_prompt: Whether a ready prompt was generated
        - generated_prompt: The generated prompt (if any)
        - suggested_mode: "read" or "write" (if prompt generated)
    """
    return await smart_query(
        session,
        question,
        mode="plan",
        conversation_history=conversation_history,
    )


# Export all public symbols
__all__ = [
    # Main service class
    "SmartQueryService",
    # Main functions
    "smart_query",
    "smart_write",
    "smart_plan",
    # Geographic utilities
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
    "interpret_plan_query",
    "interpret_plan_query_stream",
    "get_openai_client",
    "detect_compound_query",
    "invalidate_types_cache",
    # Query execution
    "execute_smart_query",
    "execute_compound_query",
    # Visualization
    "VisualizationSelector",
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
