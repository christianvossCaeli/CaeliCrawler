"""Document analysis tasks.

This module contains Celery tasks for analyzing documents using Azure OpenAI,
including document analysis, batch processing, and reanalysis of low-confidence results.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from uuid import UUID

import structlog

from app.config import settings
from workers.async_runner import run_async
from .common import _get_default_prompt, _calculate_confidence, _resolve_entity

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.models.category import Category

logger = structlog.get_logger()


# =============================================================================
# Celery Tasks
# =============================================================================


def register_tasks(celery_app):
    """Register all document analyzer tasks with the Celery app."""

    @celery_app.task(
        bind=True,
        name="workers.ai_tasks.analyze_document",
        max_retries=3,
        default_retry_delay=60,
        retry_backoff=True,
        retry_backoff_max=600,
        retry_jitter=True,
        rate_limit="10/m",  # 10 requests per minute to respect Azure rate limits
        soft_time_limit=300,  # 5 minutes soft limit for AI analysis
        time_limit=360,  # 6 minutes hard limit
    )
    def analyze_document(self, document_id: str, skip_relevance_check: bool = False):
        """
        Analyze a document using Azure OpenAI.

        Args:
            document_id: UUID of the document to analyze
            skip_relevance_check: Skip the relevance pre-filter (default: False)
        """
        from app.database import get_celery_session_context
        from app.models import Document, Category, DataSource, ExtractedData, ProcessingStatus
        from services.relevance_checker import check_relevance

        async def _analyze():
            async with get_celery_session_context() as session:
                document = await session.get(Document, UUID(document_id))
                if not document or not document.raw_text:
                    logger.warning("Document not found or has no text", document_id=document_id)
                    return

                # Get category for AI prompt
                category = await session.get(Category, document.category_id)
                if not category:
                    logger.error("Category not found", category_id=str(document.category_id))
                    return

                # Pre-filter: Quick relevance check using category keywords
                if not skip_relevance_check:
                    relevance_result = check_relevance(
                        document.raw_text,
                        title=document.title,
                        category=category,
                    )

                    if not relevance_result.is_relevant and relevance_result.score < 0.2:
                        # Document is not relevant - mark as filtered and skip AI
                        document.processing_status = ProcessingStatus.FILTERED
                        document.processing_error = f"Filtered: {relevance_result.reason}"
                        await session.commit()

                        logger.info(
                            "Document filtered (not relevant)",
                            document_id=document_id,
                            reason=relevance_result.reason,
                            score=relevance_result.score,
                            matched_keywords=relevance_result.matched_keywords,
                        )
                        return

                # Get source info
                # Note: location_name, region, admin_level_1 were removed from DataSource
                # These values are now determined by AI analysis and stored on Entity
                source = await session.get(DataSource, document.source_id)
                source_location = None  # No longer on DataSource
                source_region = None  # No longer on DataSource
                source_admin_level_1 = None  # No longer on DataSource

                # Update status
                document.processing_status = ProcessingStatus.ANALYZING

                try:
                    # Prepare prompt
                    prompt = category.ai_extraction_prompt or _get_default_prompt(category)

                    # Call Azure OpenAI
                    result = await _call_azure_openai(
                        document.raw_text,
                        prompt,
                        category.purpose,
                    )

                    if result:
                        # Enrich content with source location if not extracted by AI
                        content = result["content"]
                        if source_location:
                            # Use source location if AI didn't extract one or it's empty
                            ai_municipality = content.get("municipality", "")
                            if not ai_municipality or ai_municipality in ("", "null", "Unbekannt", None):
                                content["municipality"] = source_location
                            # Always add source location info for clustering
                            content["source_location"] = source_location
                        if source_region:
                            content["source_region"] = source_region
                        if source_admin_level_1:
                            content["source_admin_level_1"] = source_admin_level_1

                        # Process entity references from AI extraction
                        entity_references, primary_entity_id = await _process_entity_references(
                            session, content, category
                        )

                        # Save extracted data
                        extracted = ExtractedData(
                            document_id=document.id,
                            category_id=category.id,
                            extraction_type=f"{category.slug}_analysis",
                            extracted_content=content,
                            confidence_score=result.get("confidence"),
                            ai_model_used=settings.azure_openai_deployment_name,
                            ai_prompt_version="1.0",
                            raw_ai_response=result.get("raw_response"),
                            tokens_used=result.get("tokens_used"),
                            relevance_score=result.get("relevance_score"),
                            entity_references=entity_references,
                            primary_entity_id=primary_entity_id,
                        )
                        session.add(extracted)
                        await session.flush()  # Get the extracted data ID

                        logger.info(
                            "Document analyzed",
                            document_id=document_id,
                            confidence=result.get("confidence"),
                        )

                        # Convert extraction to Entity-Facet system
                        try:
                            # Use extraction_handler from category config
                            handler = category.extraction_handler or "default"
                            if handler == "event":
                                from services.event_extraction_service import convert_event_extraction_to_facets
                                facet_counts = await convert_event_extraction_to_facets(
                                    session, extracted, source, category
                                )
                            else:
                                # Default handler for pain_points, positive_signals, etc.
                                from services.entity_facet_service import convert_extraction_to_facets
                                facet_counts = await convert_extraction_to_facets(
                                    session, extracted, source
                                )
                            if sum(facet_counts.values()) > 0:
                                logger.info(
                                    "Created facet values",
                                    document_id=document_id,
                                    category=category.slug,
                                    extraction_handler=handler,
                                    facet_counts=facet_counts,
                                )
                        except Exception as facet_error:
                            logger.warning(
                                "Failed to create facet values (non-fatal)",
                                document_id=document_id,
                                error=str(facet_error),
                            )

                        # Emit notification events
                        from workers.notification_tasks import emit_event
                        confidence = result.get("confidence", 0)

                        emit_event.delay(
                            "AI_ANALYSIS_COMPLETED",
                            {
                                "entity_type": "document",
                                "entity_id": document_id,
                                "title": document.title or "Unbekanntes Dokument",
                                "confidence": confidence,
                                "category_id": str(category.id),
                            }
                        )

                        # Emit high confidence event if applicable
                        if confidence >= 0.8:
                            emit_event.delay(
                                "HIGH_CONFIDENCE_RESULT",
                                {
                                    "entity_type": "document",
                                    "entity_id": document_id,
                                    "title": document.title or "Unbekanntes Dokument",
                                    "confidence": confidence,
                                    "category_id": str(category.id),
                                    "summary": result["content"].get("summary", "")[:500],
                                }
                            )

                    document.processing_status = ProcessingStatus.COMPLETED

                except Exception as e:
                    logger.exception("AI analysis failed", document_id=document_id)
                    document.processing_status = ProcessingStatus.FAILED
                    document.processing_error = f"AI analysis error: {str(e)}"

                await session.commit()

        run_async(_analyze())

    @celery_app.task(name="workers.ai_tasks.batch_analyze")
    def batch_analyze(document_ids: list[str]):
        """Batch analyze multiple documents."""
        for doc_id in document_ids:
            analyze_document.delay(doc_id)

        logger.info("Queued batch analysis", count=len(document_ids))

    @celery_app.task(name="workers.ai_tasks.reanalyze_low_confidence")
    def reanalyze_low_confidence(threshold: float = 0.5):
        """Reanalyze documents with low confidence scores."""
        from app.database import get_celery_session_context
        from app.models import ExtractedData, Document
        from sqlalchemy import select, delete

        async def _reanalyze():
            async with get_celery_session_context() as session:
                # Find low confidence extractions
                result = await session.execute(
                    select(ExtractedData)
                    .where(ExtractedData.confidence_score < threshold)
                    .where(ExtractedData.human_verified.is_(False))
                )
                extractions = result.scalars().all()

                document_ids = set()
                for ext in extractions:
                    document_ids.add(str(ext.document_id))
                    # Delete old extraction
                    await session.delete(ext)

                await session.commit()

                # Requeue for analysis
                for doc_id in document_ids:
                    analyze_document.delay(doc_id)

                logger.info("Requeued low confidence documents", count=len(document_ids))

        run_async(_reanalyze())

    # Return task references for importing
    return analyze_document, batch_analyze, reanalyze_low_confidence


# =============================================================================
# Helper Functions
# =============================================================================


async def _process_entity_references(
    session: "AsyncSession",
    content: Dict[str, Any],
    category: "Category",
) -> tuple[List[Dict[str, Any]], Optional[UUID]]:
    """
    Process entity references from AI extraction content.

    Fully config-driven: extracts entity references based on category's
    entity_reference_config. No hard-coded field names.

    entity_reference_config schema:
    {
        "entity_types": ["territorial-entity", "person"],
        "field_mappings": {
            "field_name": "entity-type-slug"
        },
        "array_field_mappings": {
            "field_name": {
                "entity_type": "entity-type-slug",
                "name_fields": ["name", "person"],
                "role_field": "role",
                "default_role": "secondary"
            }
        }
    }

    Args:
        session: Database session
        content: AI extraction content
        category: Category with entity_reference_config

    Returns:
        Tuple of (entity_references list, primary_entity_id or None)
    """
    entity_references = []
    primary_entity_id = None

    # Get full configuration from category
    config = category.entity_reference_config
    if not config:
        # No config = no entity reference extraction
        return [], None

    # Which entity types to extract
    entity_types = config.get("entity_types", [])
    if not entity_types:
        return [], None

    # Field mappings: simple fields that contain entity names
    # Example: {"municipality": "territorial-entity", "region": "territorial-entity"}
    field_mappings = config.get("field_mappings", {})

    # Array field mappings: fields that contain arrays of entity objects
    # Example: {"decision_makers": {"entity_type": "person", "name_fields": ["name"]}}
    array_field_mappings = config.get("array_field_mappings", {})

    # Track which entity types have primary already assigned
    primary_assigned_types = set()

    # 1. Process simple field mappings
    for field_name, entity_type in field_mappings.items():
        if entity_type not in entity_types:
            continue

        field_value = content.get(field_name)
        if not field_value:
            continue

        # Handle both string values and lists
        values = field_value if isinstance(field_value, list) else [field_value]

        for value in values:
            if not isinstance(value, str):
                continue
            if value.lower() in ("", "unbekannt", "null", "none", "n/a"):
                continue

            # Determine role - first of each type is primary
            is_primary = entity_type not in primary_assigned_types
            role = "primary" if is_primary else "secondary"
            if is_primary:
                primary_assigned_types.add(entity_type)

            # Resolve to existing entity
            entity_id = await _resolve_entity(session, entity_type, value)

            entity_references.append({
                "entity_type": entity_type,
                "entity_name": value,
                "entity_id": str(entity_id) if entity_id else None,
                "role": role,
                "confidence": 0.85,
            })

            # Set primary_entity_id for first resolved entity
            if entity_id and not primary_entity_id:
                primary_entity_id = entity_id

    # 2. Process array field mappings
    for field_name, mapping in array_field_mappings.items():
        entity_type = mapping.get("entity_type")
        if not entity_type or entity_type not in entity_types:
            continue

        name_fields = mapping.get("name_fields", ["name"])
        role_field = mapping.get("role_field", "role")
        default_role = mapping.get("default_role", "secondary")

        field_values = content.get(field_name)
        if not isinstance(field_values, list):
            continue

        for item in field_values:
            name = None

            if isinstance(item, dict):
                # Extract name from configured fields
                for nf in name_fields:
                    name = item.get(nf)
                    if name:
                        break
                role = item.get(role_field, default_role)
            elif isinstance(item, str):
                name = item
                role = default_role
            else:
                continue

            if not name or (isinstance(name, str) and name.lower() in ("", "unbekannt", "null")):
                continue

            # Resolve entity
            entity_id = await _resolve_entity(session, entity_type, name)

            entity_references.append({
                "entity_type": entity_type,
                "entity_name": name,
                "entity_id": str(entity_id) if entity_id else None,
                "role": role,
                "confidence": 0.7,
            })

    # 3. Process explicit entity_references from AI response (if AI was asked to return them)
    ai_entity_refs = content.get("entity_references", [])
    if isinstance(ai_entity_refs, list):
        for ref in ai_entity_refs:
            if not isinstance(ref, dict):
                continue

            entity_type = ref.get("entity_type") or ref.get("type")
            entity_name = ref.get("entity_name") or ref.get("name")

            if not entity_type or not entity_name:
                continue
            if entity_type not in entity_types:
                continue

            # Resolve entity
            entity_id = await _resolve_entity(session, entity_type, entity_name)

            role = ref.get("role", "secondary")

            entity_references.append({
                "entity_type": entity_type,
                "entity_name": entity_name,
                "entity_id": str(entity_id) if entity_id else None,
                "role": role,
                "confidence": ref.get("confidence", 0.7),
            })

            # Set primary if marked and we don't have one yet
            if entity_id and not primary_entity_id and role == "primary":
                primary_entity_id = entity_id

    return entity_references, primary_entity_id


async def _call_azure_openai(
    text: str,
    prompt: str,
    purpose: str,
) -> Dict[str, Any]:
    """Call Azure OpenAI API for document analysis.

    Raises:
        ValueError: If Azure OpenAI is not configured
        RuntimeError: If AI call fails
    """
    from services.ai_client import AzureOpenAIClientFactory

    client = AzureOpenAIClientFactory.create_client()

    # Truncate text if too long (keep first ~100k chars)
    max_chars = 100000
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[... Text gekürzt ...]"

    try:
        response = await client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=[
                {
                    "role": "system",
                    "content": prompt,
                },
                {
                    "role": "user",
                    "content": f"Analysiere folgendes Dokument:\n\n{text}",
                },
            ],
            temperature=0.1,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )

        raw_response = response.choices[0].message.content
        content = json.loads(raw_response)

        # Calculate confidence based on multiple factors
        confidence = _calculate_confidence(content)

        return {
            "content": content,
            "confidence": confidence,
            "relevance_score": confidence,
            "raw_response": raw_response,
            "tokens_used": response.usage.total_tokens if response.usage else None,
        }

    except json.JSONDecodeError as e:
        logger.error("Failed to parse AI response as JSON", error=str(e))
        raise RuntimeError(f"KI-Service Fehler: AI-Antwort konnte nicht verarbeitet werden - {str(e)}")
    except Exception as e:
        logger.exception("Azure OpenAI API call failed")
        raise RuntimeError(f"KI-Service nicht erreichbar: {str(e)}")
