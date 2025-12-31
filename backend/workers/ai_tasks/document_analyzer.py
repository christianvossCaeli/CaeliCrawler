"""Document analysis tasks.

This module contains Celery tasks for analyzing documents using Azure OpenAI,
including document analysis, batch processing, and reanalysis of low-confidence results.
"""

import json
import time
from typing import TYPE_CHECKING, Any
from uuid import UUID

import structlog
from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy import select

from app.config import settings
from app.models.llm_usage import LLMProvider, LLMTaskType
from services.llm_usage_tracker import record_llm_usage
from workers.async_runner import run_async

from .common import (
    DEFAULT_ARRAY_FIELD_MAPPINGS,
    DEFAULT_FIELD_MAPPINGS,
    DEFAULT_NESTED_FIELD_MAPPINGS,
    _calculate_confidence,
    _create_entity_facet_value,
    _get_active_entity_type_slugs,
    _get_default_prompt,
    _resolve_entity,
    _resolve_entity_smart,
)

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
        from app.models import Category, DataSource, Document, ExtractedData, ProcessingStatus
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

                    # Determine which text to analyze (page-based or full)
                    text_to_analyze, page_info = await _get_text_for_analysis(
                        document, session
                    )

                    # Enhance prompt with page context if using page-based analysis
                    if page_info and page_info.get("page_numbers"):
                        prompt = _enhance_prompt_with_page_context(prompt, page_info)

                    # Call Azure OpenAI
                    result = await _call_azure_openai(
                        text_to_analyze,
                        prompt,
                        category.purpose,
                        document_id=document.id,
                        category_id=category.id,
                    )

                    # Update analyzed_pages atomically with pessimistic locking
                    # to prevent race conditions with concurrent analysis tasks
                    if page_info and page_info.get("page_numbers"):
                        await _update_analyzed_pages_atomic(
                            document.id,
                            page_info["page_numbers"],
                            document.total_relevant_pages,
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
                        # Also creates FacetValues linking non-primary entities to primary entity
                        entity_references, primary_entity_id = await _process_entity_references(
                            session, content, category, document_id=document.id
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

                except SoftTimeLimitExceeded:
                    # Handle soft time limit - graceful shutdown
                    logger.warning(
                        "Document analysis soft time limit exceeded",
                        document_id=document_id,
                    )
                    document.processing_status = ProcessingStatus.FAILED
                    document.processing_error = "AI analysis exceeded time limit (5 minutes)"

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
        from sqlalchemy import select

        from app.database import get_celery_session_context
        from app.models import ExtractedData

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
    content: dict[str, Any],
    category: "Category",
    document_id: UUID | None = None,
) -> tuple[list[dict[str, Any]], UUID | None]:
    """
    Process entity references from AI extraction content.

    Fully config-driven: extracts entity references based on category's
    entity_reference_config. When no config is provided, falls back to
    DEFAULT_FIELD_MAPPINGS, DEFAULT_NESTED_FIELD_MAPPINGS and
    DEFAULT_ARRAY_FIELD_MAPPINGS from common.py.

    Also creates FacetValues to link extracted entities back to the primary
    entity when a matching FacetType exists. The FacetType matching is generic -
    it finds any FacetType with allows_entity_reference=True and matching
    target_entity_type_slugs / applicable_entity_type_slugs.

    Args:
        session: Database session
        content: AI extraction content (any JSON structure)
        category: Category with optional entity_reference_config
        document_id: Source document ID for FacetValue creation

    Returns:
        Tuple of (entity_references list, primary_entity_id or None)
    """
    entity_references = []
    primary_entity_id = None

    # Get full configuration from category or use defaults
    config = category.entity_reference_config or {}

    # Get active entity types from database dynamically
    active_entity_types = await _get_active_entity_type_slugs(session)

    # Which entity types to extract (use config or active types from DB)
    entity_types = config.get("entity_types") or active_entity_types

    # Field mappings: simple fields that contain entity names
    # Merge defaults with config (config takes precedence)
    field_mappings = {**DEFAULT_FIELD_MAPPINGS, **config.get("field_mappings", {})}

    # Nested field mappings: dot notation paths for nested fields
    nested_field_mappings = {**DEFAULT_NESTED_FIELD_MAPPINGS, **config.get("nested_field_mappings", {})}

    # Array field mappings: fields that contain arrays of entity objects
    # Merge defaults with config (config takes precedence)
    array_field_mappings = {**DEFAULT_ARRAY_FIELD_MAPPINGS, **config.get("array_field_mappings", {})}

    # Track which entity types have primary already assigned
    primary_assigned_types = set()

    def get_nested_value(data: dict, path: str):
        """Get value from nested dict using dot notation path."""
        parts = path.split(".")
        current = data
        for part in parts:
            if not isinstance(current, dict):
                return None
            current = current.get(part)
            if current is None:
                return None
        return current

    async def process_field_value(field_value, entity_type, source_field):
        """Process a field value and extract entity references."""
        nonlocal primary_entity_id

        if not field_value:
            return

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
                "source_field": source_field,
            })

            # Set primary_entity_id for first resolved entity
            if entity_id and not primary_entity_id:
                primary_entity_id = entity_id

    # 1. Process simple field mappings (top-level)
    for field_name, entity_type in field_mappings.items():
        if entity_type not in entity_types:
            continue
        field_value = content.get(field_name)
        await process_field_value(field_value, entity_type, field_name)

    # 2. Process nested field mappings (dot notation paths)
    for field_path, entity_type in nested_field_mappings.items():
        if entity_type not in entity_types:
            continue
        field_value = get_nested_value(content, field_path)
        await process_field_value(field_value, entity_type, field_path)

    # 3. Process array field mappings
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

            # Smart entity resolution: Search across all types and classify if needed
            # The entity_type from mapping is used as fallback/hint
            entity_id, actual_entity_type = await _resolve_entity_smart(
                session,
                name,
                allowed_types=None,  # Search all types
                auto_create=True,
                default_type=entity_type,  # Fallback to configured type
            )

            entity_references.append({
                "entity_type": actual_entity_type,
                "entity_name": name,
                "entity_id": str(entity_id) if entity_id else None,
                "role": role,
                "confidence": 0.7,
                "source_field": field_name,
            })

    # 4. Process explicit entity_references from AI response (if AI was asked to return them)
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

    # 5. Create FacetValues for non-primary entities linked to primary entity
    # This creates bidirectional relationships: primary entity gets facets for linked entities
    if primary_entity_id:
        for ref in entity_references:
            # Skip primary entities - they don't get linked as facets
            if ref.get("role") == "primary":
                continue

            # Skip if no resolved entity_id
            target_entity_id = ref.get("entity_id")
            if not target_entity_id:
                continue

            # Create FacetValue linking this entity to the primary entity
            # This is generic - it finds a matching FacetType based on entity types
            await _create_entity_facet_value(
                session=session,
                primary_entity_id=primary_entity_id,
                target_entity_id=UUID(target_entity_id),
                target_entity_type_slug=ref.get("entity_type", ""),
                target_entity_name=ref.get("entity_name", ""),
                role=ref.get("role", "secondary"),
                document_id=document_id,
                category_id=category.id if category else None,
                confidence_score=ref.get("confidence", 0.7),
            )

    # 6. Category-based fallback: If no entities found, use default_entity_id from config
    if not primary_entity_id and config.get("default_entity_id"):
        try:
            default_entity_id = UUID(str(config["default_entity_id"]))
            # Verify the entity exists
            from app.models import Entity
            result = await session.execute(
                select(Entity).where(Entity.id == default_entity_id)
            )
            default_entity = result.scalar_one_or_none()
            if default_entity:
                primary_entity_id = default_entity_id
                logger.info(
                    f"Using category default entity fallback: {default_entity.name} "
                    f"(ID: {default_entity_id})"
                )
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid default_entity_id in category config: {e}")

    return entity_references, primary_entity_id


# =============================================================================
# Page-based Analysis Helpers
# =============================================================================


async def _get_text_for_analysis(
    document, session
) -> tuple[str, dict[str, Any] | None]:
    """
    Get the text to analyze, using page-based filtering if available.

    Returns:
        Tuple of (text_to_analyze, page_info_dict or None)
        page_info contains: page_numbers, total_pages, is_partial
    """
    from pathlib import Path

    from app.config import settings
    from services.document_page_filter import DocumentPageFilter

    # Check if we have page-based analysis info
    if not document.relevant_pages or document.page_analysis_status == "pending":
        # No page filtering available, use full document
        return document.raw_text, None

    # Use page-based analysis
    if not document.file_path:
        # File path not set, fall back to raw_text
        return document.raw_text, None

    file_path = Path(document.file_path)

    # Security: Validate path is within allowed storage directory
    try:
        storage_base = Path(settings.document_storage_path).resolve()
        resolved_path = file_path.resolve()
        resolved_path.relative_to(storage_base)  # Raises ValueError if outside
    except ValueError:
        logger.error(
            "Path traversal attempt blocked",
            document_id=str(document.id),
            file_path=str(document.file_path),
        )
        return document.raw_text, None

    if not resolved_path.exists():
        # File not available, fall back to raw_text
        return document.raw_text, None

    # Determine content type
    content_type_map = {
        "PDF": "application/pdf",
        "HTML": "text/html",
        "DOC": "application/msword",
        "DOCX": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    content_type = content_type_map.get(document.document_type.upper(), "text/plain")

    try:
        # Get category for filter
        from app.models.category import Category
        category = await session.get(Category, document.category_id)
        page_filter = DocumentPageFilter.from_category(category)

        # Extract pages
        pages = page_filter.extract_pages(resolved_path, content_type)

        # Get only the relevant pages (not yet analyzed)
        analyzed = set(document.analyzed_pages or [])
        relevant_to_analyze = [
            p for p in pages
            if p.page_number in document.relevant_pages
            and p.page_number not in analyzed
        ]

        if not relevant_to_analyze:
            # All relevant pages already analyzed, use full text for any remaining
            return document.raw_text, None

        # Sort by page number for coherent reading
        relevant_to_analyze.sort(key=lambda p: p.page_number)

        # Build text with page markers
        text_parts = []
        page_numbers = []
        for page in relevant_to_analyze:
            text_parts.append(f"=== SEITE {page.page_number} von {document.page_count or len(pages)} ===\n{page.text}")
            page_numbers.append(page.page_number)

        combined_text = "\n\n".join(text_parts)

        page_info = {
            "page_numbers": page_numbers,
            "total_pages": document.page_count or len(pages),
            "total_relevant": document.total_relevant_pages or len(document.relevant_pages),
            "is_partial": len(page_numbers) < (document.total_relevant_pages or len(document.relevant_pages)),
        }

        logger.info(
            "Using page-based analysis",
            document_id=str(document.id),
            pages_to_analyze=page_numbers,
            total_relevant=page_info["total_relevant"],
        )

        return combined_text, page_info

    except Exception as e:
        logger.warning(
            "Page-based extraction failed, using full text",
            document_id=str(document.id),
            error=str(e),
        )
        return document.raw_text, None


def _enhance_prompt_with_page_context(prompt: str, page_info: dict[str, Any]) -> str:
    """
    Enhance the extraction prompt with page context information.

    Adds instructions for the AI to include page references in its responses.
    """
    page_numbers = page_info.get("page_numbers", [])
    total_pages = page_info.get("total_pages", 0)
    is_partial = page_info.get("is_partial", False)

    page_context = f"""
**WICHTIG - Seiten-basierte Analyse:**
Du analysierst ausgewählte Seiten eines Dokuments mit {total_pages} Gesamtseiten.
Analysierte Seiten: {', '.join(map(str, page_numbers))}
{'Dies ist eine Teil-Analyse. Weitere relevante Seiten existieren.' if is_partial else ''}

**Anforderungen für deine Antwort:**
1. Gib bei JEDER extrahierten Information die Seitenzahl an (z.B. "Seite 5")
2. Verwende das Format: "Information [Seite X]" oder füge ein "source_page" Feld hinzu
3. Falls wichtiger Kontext auf anderen Seiten fehlen könnte, gib das im Feld "suggested_additional_pages" an (Array von Seitenzahlen)
4. Sei AUSFÜHRLICH in deinen Beschreibungen - gib konkrete Details, Zahlen, Namen und Zusammenhänge an
5. Die Zusammenfassung sollte mindestens 150 Wörter umfassen und die wichtigsten Punkte detailliert darstellen

"""
    return page_context + prompt


async def _update_analyzed_pages_atomic(
    document_id: UUID,
    new_pages: list[int],
    total_relevant: int | None = None,
) -> tuple[str, str | None]:
    """
    Atomically update analyzed_pages with pessimistic locking.

    This prevents race conditions when multiple tasks analyze pages
    of the same document concurrently.

    Args:
        document_id: UUID of the document
        new_pages: List of page numbers that were just analyzed
        total_relevant: Total number of relevant pages (for status update)

    Returns:
        Tuple of (new_status, note_message)
    """
    from sqlalchemy import select

    from app.database import get_celery_session_context
    from app.models import Document

    async with get_celery_session_context() as session:
        # Lock the row for update
        stmt = (
            select(Document)
            .where(Document.id == document_id)
            .with_for_update()
        )
        result = await session.execute(stmt)
        document = result.scalar_one_or_none()

        if not document:
            logger.warning("Document not found for page update", document_id=str(document_id))
            return "pending", None

        # Merge existing and new pages
        existing = set(document.analyzed_pages or [])
        existing.update(new_pages)
        document.analyzed_pages = sorted(existing)

        # Update status based on progress
        new_status = document.page_analysis_status
        note = document.page_analysis_note

        analyzed_count = len(document.analyzed_pages)
        total = total_relevant or document.total_relevant_pages or 0

        if total > 0 and analyzed_count >= total:
            new_status = "complete"
            note = None
        elif document.page_analysis_status == "has_more" and total > 0:
            remaining = total - analyzed_count
            if remaining > 0:
                note = f"{remaining} weitere relevante Seiten verfügbar"
            else:
                new_status = "complete"
                note = None

        document.page_analysis_status = new_status
        document.page_analysis_note = note

        await session.commit()

        logger.info(
            "Updated analyzed_pages atomically",
            document_id=str(document_id),
            new_pages=new_pages,
            total_analyzed=analyzed_count,
            status=new_status,
        )

        return new_status, note


async def _call_azure_openai(
    text: str,
    prompt: str,
    purpose: str,
    document_id: UUID | None = None,
    category_id: UUID | None = None,
) -> dict[str, Any]:
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

    start_time = time.time()

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

        # Track LLM usage
        duration_ms = int((time.time() - start_time) * 1000)
        if response.usage:
            await record_llm_usage(
                provider=LLMProvider.AZURE_OPENAI,
                model=settings.azure_openai_deployment_name,
                task_type=LLMTaskType.EXTRACT,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                duration_ms=duration_ms,
                document_id=document_id,
                category_id=category_id,
                task_name=f"analyze_document_{purpose}",
                is_error=False,
            )

        return {
            "content": content,
            "confidence": confidence,
            "relevance_score": confidence,
            "raw_response": raw_response,
            "tokens_used": response.usage.total_tokens if response.usage else None,
        }

    except json.JSONDecodeError as e:
        logger.error("Failed to parse AI response as JSON", error=str(e))
        raise RuntimeError(f"KI-Service Fehler: AI-Antwort konnte nicht verarbeitet werden - {str(e)}") from None
    except Exception as e:
        logger.exception("Azure OpenAI API call failed")
        # Track error
        duration_ms = int((time.time() - start_time) * 1000)
        await record_llm_usage(
            provider=LLMProvider.AZURE_OPENAI,
            model=settings.azure_openai_deployment_name,
            task_type=LLMTaskType.EXTRACT,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            duration_ms=duration_ms,
            document_id=document_id,
            category_id=category_id,
            task_name=f"analyze_document_{purpose}",
            is_error=True,
            error_message=str(e),
        )
        raise RuntimeError(f"KI-Service nicht erreichbar: {str(e)}") from None
