"""Celery tasks for AI analysis."""

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID

import structlog
from celery.exceptions import SoftTimeLimitExceeded

from workers.celery_app import celery_app
from app.config import settings

if TYPE_CHECKING:
    from openai import AsyncAzureOpenAI
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.models.entity import Entity
    from app.models.facet_type import FacetType
    from app.models.pysis import PySisProcess

logger = structlog.get_logger()

# Constants for PySis facet extraction
PYSIS_MAX_CONTEXT_LENGTH = 50000
PYSIS_TEXT_REPR_MAX_LENGTH = 2000
PYSIS_SUMMARY_MAX_LENGTH = 500
PYSIS_MIN_TEXT_LENGTH = 10
PYSIS_MIN_DEDUP_TEXT_LENGTH = 5
PYSIS_BASE_CONFIDENCE = 0.7
PYSIS_CONFIDENCE_BOOST = 0.05
PYSIS_MAX_CONFIDENCE = 0.95
PYSIS_DUPLICATE_SIMILARITY_THRESHOLD = 0.85

# Constants for AI API calls
AI_EXTRACTION_TEMPERATURE = 0.2
AI_EXTRACTION_MAX_TOKENS = 4000


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
    import asyncio

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
                document.processing_error = f"AI analysis error: {str(e)}"

            await session.commit()

    asyncio.run(_analyze())


def _get_default_prompt(category) -> str:
    """Get default extraction prompt based on category."""
    search_terms = ", ".join(category.search_terms) if category.search_terms else "relevante Informationen"
    doc_types = ", ".join(category.document_types) if category.document_types else "Dokumente"

    return f"""
Du bist ein Experte für die Analyse kommunaler Dokumente.

**Zweck dieser Analyse:** {category.purpose}

**Gesuchte Begriffe:** {search_terms}
**Dokumenttypen:** {doc_types}

Analysiere das folgende Dokument und extrahiere strukturiert:

1. **Dokumenttyp**: Welche Art von Dokument ist das?
2. **Datum**: Wann wurde das Dokument erstellt/beschlossen?
3. **Zusammenfassung**: Kurze Zusammenfassung (max 200 Wörter)
4. **Relevanz**: Wie relevant ist das Dokument für den angegebenen Zweck? (hoch/mittel/gering/keine)
5. **Kernaussagen**: Liste der wichtigsten Aussagen
6. **Erwähnte Regelungen**: Spezifische Regelungen, Beschlüsse, Vorgaben
7. **Betroffene Bereiche**: Geografische oder thematische Bereiche
8. **Referenzen**: Erwähnte Gesetze, Verordnungen, andere Dokumente

Antworte im JSON-Format.
"""


def _calculate_confidence(content: Dict[str, Any]) -> float:
    """
    Calculate confidence score based on multiple factors from AI response.

    The score determines how confident we are that the document is valuable.
    Relevant documents with good data quality should score >= 0.7.
    Non-relevant documents should score < 0.5.

    Factors:
    1. is_relevant: Primary relevance indicator (determines base score)
    2. relevanz: Secondary relevance rating with granularity
    3. outreach_priority: Business value indicator
    4. Data quality: pain_points, positive_signals, decision_makers, summary
    """
    # Base score depends on is_relevant flag
    is_relevant = content.get("is_relevant")
    if is_relevant is True:
        score = 0.72  # Start at threshold for relevant docs
    elif is_relevant is False:
        score = 0.25  # Non-relevant docs start low
    else:
        score = 0.45  # Unknown relevance

    # Factor 1: Explicit relevance rating (fine-tune the base)
    relevance = content.get("relevanz", content.get("relevance", ""))
    if isinstance(relevance, str):
        relevance_lower = relevance.lower()
        if relevance_lower == "hoch":
            score += 0.15
        elif relevance_lower == "mittel":
            score += 0.05
        elif relevance_lower == "gering":
            score -= 0.10
        elif relevance_lower == "keine":
            score -= 0.20

    # Factor 2: Outreach priority (business value)
    outreach = content.get("outreach_recommendation", {})
    if isinstance(outreach, dict):
        priority = outreach.get("priority", "")
        if isinstance(priority, str):
            priority_lower = priority.lower()
            if priority_lower == "hoch":
                score += 0.08
            elif priority_lower == "mittel":
                score += 0.03

    # Factor 3: Data quality indicators (reward rich extractions)
    # Supports multiple schema variants (ratsinformationen-nrw, kommunale-news, etc.)
    quality_bonus = 0.0

    # Summary quality (has meaningful summary)
    summary = content.get("summary", "")
    if isinstance(summary, str) and len(summary) > 50:
        quality_bonus += 0.02

    # Pain points / concerns (supports both schema variants)
    pain_points = content.get("pain_points", []) or content.get("concerns_raised", [])
    if isinstance(pain_points, list) and len(pain_points) > 0:
        quality_bonus += min(0.05, len(pain_points) * 0.015)

    # Positive signals / opportunities (supports both schema variants)
    positive_signals = content.get("positive_signals", []) or content.get("opportunities", [])
    if isinstance(positive_signals, list) and len(positive_signals) > 0:
        quality_bonus += min(0.05, len(positive_signals) * 0.015)

    # Decision makers / key_statements with person (supports both schema variants)
    decision_makers = content.get("decision_makers", [])
    if not decision_makers:
        # Fallback: Use key_statements that have a person identified
        key_statements = content.get("key_statements", [])
        if isinstance(key_statements, list):
            decision_makers = [s for s in key_statements if isinstance(s, dict) and s.get("person")]
    if isinstance(decision_makers, list) and len(decision_makers) > 0:
        quality_bonus += min(0.05, len(decision_makers) * 0.02)

    # Municipality identified
    municipality = content.get("municipality", "")
    if isinstance(municipality, str) and municipality and municipality.lower() not in ("", "unbekannt", "null"):
        quality_bonus += 0.02

    # Contact opportunity (kommunale-news schema)
    contact_opp = content.get("contact_opportunity", {})
    if isinstance(contact_opp, dict) and contact_opp.get("exists"):
        quality_bonus += 0.03

    score += quality_bonus

    # Clamp to valid range [0.1, 0.98]
    return max(0.1, min(0.98, round(score, 2)))


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
    import asyncio

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

    asyncio.run(_reanalyze())


@celery_app.task(
    bind=True,
    name="workers.ai_tasks.extract_pysis_fields",
    max_retries=3,
    default_retry_delay=60,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    rate_limit="10/m",  # 10 requests per minute to respect Azure rate limits
    soft_time_limit=600,  # 10 minutes soft limit
    time_limit=660,  # 11 minutes hard limit
)
def extract_pysis_fields(self, process_id: str, field_ids: Optional[list[str]] = None):
    """
    Extract PySis field values from municipality documents using AI.

    This task:
    1. Loads all relevant extracted data for the municipality
    2. For each enabled PySis field, generates a value using AI
    3. Updates the field's ai_extracted_value and confidence

    Args:
        process_id: UUID of the PySis process
        field_ids: Optional list of specific field UUIDs to extract
    """
    import asyncio
    asyncio.run(_extract_pysis_fields_async(process_id, field_ids, self.request.id))


async def _extract_pysis_fields_async(process_id: str, field_ids: Optional[list[str]], celery_task_id: Optional[str] = None):
    """Async implementation of PySis field extraction."""
    from app.database import get_celery_session_context
    from app.models.pysis import PySisProcess, PySisProcessField, ValueSource
    from app.models import ExtractedData, AITask, AITaskStatus, AITaskType
    from sqlalchemy import select
    from datetime import datetime, timezone

    async with get_celery_session_context() as session:
        # Load process
        process = await session.get(PySisProcess, UUID(process_id))
        if not process:
            logger.error("PySis process not found", process_id=process_id)
            return

        # Get fields to extract
        query = select(PySisProcessField).where(
            PySisProcessField.process_id == process.id,
            PySisProcessField.ai_extraction_enabled.is_(True)
        )
        if field_ids:
            query = query.where(PySisProcessField.id.in_([UUID(f) for f in field_ids]))

        result = await session.execute(query)
        fields = result.scalars().all()

        if not fields:
            logger.info("No fields to extract", process_id=process_id)
            return

        # Create AI task for tracking
        ai_task = AITask(
            task_type=AITaskType.PYSIS_EXTRACTION,
            status=AITaskStatus.RUNNING,
            name=f"PySis Feld-Extraktion: {process.entity_name or process.name}",
            description=f"Extrahiere {len(fields)} Felder für Prozess {process.pysis_process_id}",
            process_id=process.id,
            started_at=datetime.now(timezone.utc),
            progress_total=len(fields),
            celery_task_id=celery_task_id,
        )
        session.add(ai_task)
        await session.commit()
        await session.refresh(ai_task)
        task_id = ai_task.id

        logger.info(
            "Extracting PySis fields",
            process_id=process_id,
            entity_name=process.entity_name,
            field_count=len(fields),
            ai_task_id=str(task_id),
        )

        # Get all extracted data for this location
        ext_result = await session.execute(
            select(ExtractedData)
            .where(
                ExtractedData.extracted_content["municipality"].astext.ilike(f"%{process.entity_name}%")
            )
            .where(ExtractedData.confidence_score >= 0.5)
            .order_by(ExtractedData.created_at.desc())
            .limit(30)
        )
        extractions = ext_result.scalars().all()

        if not extractions:
            # Try broader search using source_location
            ext_result = await session.execute(
                select(ExtractedData)
                .where(
                    ExtractedData.extracted_content["source_location"].astext.ilike(f"%{process.entity_name}%")
                )
                .where(ExtractedData.confidence_score >= 0.5)
                .order_by(ExtractedData.created_at.desc())
                .limit(30)
            )
            extractions = ext_result.scalars().all()

        if not extractions:
            logger.info("No extractions found for entity", entity_name=process.entity_name)
            return

        logger.info("Found extractions for location", count=len(extractions))

        # Build context from extractions
        context_parts = []
        for ext in extractions:
            content = ext.final_content
            context_parts.append(f"--- Dokument (Konfidenz: {ext.confidence_score:.0%}) ---")

            if content.get("summary"):
                context_parts.append(f"Zusammenfassung: {content.get('summary')}")

            if content.get("decision_makers"):
                dm = content.get("decision_makers")
                if isinstance(dm, list):
                    context_parts.append(f"Entscheider: {json.dumps(dm, ensure_ascii=False)}")

            if content.get("pain_points"):
                pp = content.get("pain_points")
                if isinstance(pp, list):
                    context_parts.append(f"Pain Points: {json.dumps(pp, ensure_ascii=False)}")

            if content.get("positive_signals"):
                ps = content.get("positive_signals")
                if isinstance(ps, list):
                    context_parts.append(f"Positive Signale: {json.dumps(ps, ensure_ascii=False)}")

            if content.get("current_status"):
                context_parts.append(f"Status: {content.get('current_status')}")

            if content.get("timeline"):
                context_parts.append(f"Timeline: {content.get('timeline')}")

            if content.get("outreach_recommendation"):
                outreach_rec = content.get("outreach_recommendation")
                if isinstance(outreach_rec, dict):
                    context_parts.append(f"Outreach: {json.dumps(outreach_rec, ensure_ascii=False)}")

            context_parts.append("")

        context_text = "\n".join(context_parts)

        # Limit context size
        max_context = 50000
        if len(context_text) > max_context:
            context_text = context_text[:max_context] + "\n\n[... Text gekürzt ...]"

        # Extract each field
        fields_extracted = 0
        total_confidence = 0.0
        error_count = 0

        for idx, field in enumerate(fields):
            # Update task progress
            ai_task = await session.get(AITask, task_id)
            if ai_task:
                ai_task.progress_current = idx
                ai_task.current_item = field.internal_name
                await session.commit()

            try:
                value, confidence = await _extract_single_pysis_field(
                    field,
                    context_text,
                    process.entity_name
                )

                if value:
                    # Store AI value as suggestion - don't auto-apply
                    # User must explicitly accept the suggestion
                    field.ai_extracted_value = value
                    field.confidence_score = confidence
                    fields_extracted += 1
                    total_confidence += confidence

                    logger.info(
                        "Field extracted (pending review)",
                        field=field.internal_name,
                        confidence=confidence,
                        value_length=len(value) if value else 0,
                    )

            except Exception as e:
                error_count += 1
                logger.error(
                    "Field extraction failed",
                    field=field.internal_name,
                    error=str(e),
                )

        # Update AI task as completed
        ai_task = await session.get(AITask, task_id)
        if ai_task:
            ai_task.status = AITaskStatus.COMPLETED
            ai_task.completed_at = datetime.now(timezone.utc)
            ai_task.progress_current = len(fields)
            ai_task.current_item = None
            ai_task.fields_extracted = fields_extracted
            ai_task.avg_confidence = (total_confidence / fields_extracted) if fields_extracted > 0 else None
            if error_count > 0:
                ai_task.error_message = f"{error_count} Feld(er) konnten nicht extrahiert werden"

        await session.commit()
        logger.info("PySis field extraction completed", process_id=process_id, fields_extracted=fields_extracted)


async def _extract_single_pysis_field(
    field: "PySisProcessField",
    context: str,
    location_name: str
) -> tuple[str, float]:
    """
    Extract a single PySis field value using AI.

    Returns:
        Tuple of (extracted_value, confidence_score)

    Raises:
        ValueError: If Azure OpenAI is not configured
        RuntimeError: If AI extraction fails
    """
    from services.ai_client import AzureOpenAIClientFactory

    client = AzureOpenAIClientFactory.create_client()

    # Build extraction prompt
    custom_prompt = field.ai_extraction_prompt or ""
    if custom_prompt:
        extraction_instruction = custom_prompt
    else:
        extraction_instruction = f"Extrahiere Informationen zu: {field.internal_name}"

    system_prompt = f"""Du bist ein Experte für die Extraktion von Informationen aus kommunalen Dokumenten zu Windenergie-Projekten.

Aufgabe: Extrahiere den Wert für das Feld "{field.internal_name}" für die Gemeinde {location_name}.

{extraction_instruction}

Antworte AUSSCHLIESSLICH im folgenden JSON-Format:
{{
  "value": "der extrahierte Wert als Text",
  "confidence": 0.8,
  "reasoning": "kurze Begründung warum dieser Wert extrahiert wurde"
}}

Regeln:
- "value" soll ein aussagekräftiger, gut formulierter Text sein
- "confidence" ist eine Zahl zwischen 0.0 und 1.0
- Wenn keine relevanten Informationen gefunden werden, setze "value" auf null und "confidence" auf 0.0
- Der Text in "value" soll direkt verwendbar sein (keine Platzhalter, keine Unsicherheiten)
"""

    try:
        response = await client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analysiere die folgenden Dokumente der Gemeinde {location_name}:\n\n{context}"},
            ],
            temperature=0.2,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)
        value = result.get("value")
        confidence = result.get("confidence", 0.0)

        # Ensure confidence is a float
        if isinstance(confidence, str):
            try:
                confidence = float(confidence)
            except ValueError:
                confidence = 0.5

        # Ensure confidence is in valid range
        confidence = max(0.0, min(1.0, confidence))

        return value, confidence

    except json.JSONDecodeError as e:
        logger.error("Failed to parse AI response as JSON", error=str(e))
        raise RuntimeError(f"KI-Service Fehler: AI-Antwort konnte nicht verarbeitet werden - {str(e)}")
    except Exception as e:
        logger.exception("Azure OpenAI API call failed for PySis field extraction")
        raise RuntimeError(f"KI-Service nicht erreichbar: {str(e)}")


@celery_app.task(name="workers.ai_tasks.convert_extractions_to_facets")
def convert_extractions_to_facets(
    min_confidence: float = 0.5,
    batch_size: int = 100,
    entity_type_slug: str = "territorial_entity",
):
    """
    Convert existing ExtractedData to FacetValues in the Entity-Facet system.

    This is a migration task to retroactively populate the Entity-Facet system
    from existing AI extractions.

    Args:
        min_confidence: Minimum confidence score for extractions to process
        batch_size: Number of extractions to process per batch
        entity_type_slug: Entity type to create (default: territorial_entity)
    """
    import asyncio
    asyncio.run(_convert_extractions_async(min_confidence, batch_size, entity_type_slug))


async def _convert_extractions_async(
    min_confidence: float,
    batch_size: int,
    entity_type_slug: str,
):
    """Async implementation of extraction to facet conversion."""
    from app.database import get_celery_session_context
    from app.models import ExtractedData, DataSource, Entity, FacetValue
    from services.entity_facet_service import convert_extraction_to_facets
    from sqlalchemy import select, func
    from sqlalchemy.orm import joinedload

    async with get_celery_session_context() as session:
        # Count total extractions to process
        count_result = await session.execute(
            select(func.count(ExtractedData.id))
            .where(ExtractedData.confidence_score >= min_confidence)
        )
        total_count = count_result.scalar()

        logger.info(
            "Starting extraction to facet conversion",
            total_extractions=total_count,
            min_confidence=min_confidence,
            batch_size=batch_size,
        )

        processed = 0
        total_facets = {"pain_point": 0, "positive_signal": 0, "contact": 0, "summary": 0}
        skipped = 0
        errors = 0

        offset = 0
        while True:
            # Fetch batch of extractions
            result = await session.execute(
                select(ExtractedData)
                .where(ExtractedData.confidence_score >= min_confidence)
                .order_by(ExtractedData.created_at.desc())
                .offset(offset)
                .limit(batch_size)
            )
            extractions = result.scalars().all()

            if not extractions:
                break

            for extraction in extractions:
                try:
                    # Get source for location info
                    source = None
                    if extraction.document_id:
                        from app.models import Document
                        doc = await session.get(Document, extraction.document_id)
                        if doc and doc.source_id:
                            source = await session.get(DataSource, doc.source_id)

                    # Check if municipality can be determined
                    # Note: source.location_name was removed - municipality must come from AI extraction
                    content = extraction.final_content
                    municipality_name = (
                        content.get("municipality")
                        or content.get("source_location")
                        # source.location_name no longer available
                    )

                    if not municipality_name or municipality_name.lower() in ("", "unbekannt", "null"):
                        skipped += 1
                        continue

                    # Convert to facets
                    counts = await convert_extraction_to_facets(session, extraction, source)

                    for key, count in counts.items():
                        total_facets[key] = total_facets.get(key, 0) + count

                    processed += 1

                    if processed % 50 == 0:
                        logger.info(
                            "Conversion progress",
                            processed=processed,
                            total=total_count,
                            facets_created=sum(total_facets.values()),
                        )

                except Exception as e:
                    errors += 1
                    logger.warning(
                        "Failed to convert extraction",
                        extraction_id=str(extraction.id),
                        error=str(e),
                    )

            await session.commit()
            offset += batch_size

        logger.info(
            "Extraction to facet conversion completed",
            processed=processed,
            skipped=skipped,
            errors=errors,
            total_facets=total_facets,
        )


@celery_app.task(
    bind=True,
    name="workers.ai_tasks.analyze_pysis_fields_for_facets",
    max_retries=3,
    default_retry_delay=60,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    rate_limit="10/m",  # 10 requests per minute to respect Azure rate limits
    soft_time_limit=600,  # 10 minutes soft limit
    time_limit=660,  # 11 minutes hard limit
)
def analyze_pysis_fields_for_facets(
    self,
    process_id: str,
    include_empty: bool = False,
    min_confidence: float = 0.0,
    existing_task_id: Optional[str] = None,
):
    """
    Analyze PySis fields and create FacetValues.

    Args:
        process_id: UUID of the PySis process
        include_empty: Include empty fields in analysis
        min_confidence: Minimum field confidence
        existing_task_id: Existing AITask ID (to avoid duplicate creation)
    """
    import asyncio
    asyncio.run(_analyze_pysis_for_facets_async(
        process_id,
        include_empty,
        min_confidence,
        self.request.id,
        existing_task_id,
    ))


async def _analyze_pysis_for_facets_async(
    process_id: str,
    include_empty: bool,
    min_confidence: float,
    celery_task_id: Optional[str] = None,
    existing_task_id: Optional[str] = None,
):
    """Async implementation of PySis-to-Facets analysis."""
    from app.database import get_celery_session_context
    from app.models.pysis import PySisProcess, PySisProcessField
    from app.models import AITask, AITaskStatus, AITaskType, Entity, FacetType
    from sqlalchemy import select
    from datetime import datetime, timezone

    async with get_celery_session_context() as session:
        # Helper to mark task as failed if it exists
        async def fail_task_if_exists(error_msg: str):
            if existing_task_id:
                task = await session.get(AITask, UUID(existing_task_id))
                if task:
                    task.status = AITaskStatus.FAILED
                    task.error_message = error_msg
                    task.completed_at = datetime.now(timezone.utc)
                    await session.commit()

        # 1. Load process
        process = await session.get(PySisProcess, UUID(process_id))
        if not process:
            logger.error("PySis process not found", process_id=process_id)
            await fail_task_if_exists(f"PySis-Prozess nicht gefunden: {process_id}")
            return

        if not process.entity_id:
            logger.error("Process has no entity", process_id=process_id)
            await fail_task_if_exists("PySis-Prozess hat keine verknüpfte Entity")
            return

        # Load entity
        entity = await session.get(Entity, process.entity_id)
        if not entity:
            logger.error("Entity not found", entity_id=str(process.entity_id))
            await fail_task_if_exists(f"Entity nicht gefunden: {process.entity_id}")
            return

        # 2. Load all active FacetTypes with AI extraction enabled
        facet_types_result = await session.execute(
            select(FacetType)
            .where(FacetType.is_active.is_(True))
            .where(FacetType.ai_extraction_enabled.is_(True))
            .order_by(FacetType.display_order)
        )
        facet_types = facet_types_result.scalars().all()

        if not facet_types:
            logger.warning("No active FacetTypes with AI extraction enabled")
            await fail_task_if_exists("Keine aktiven FacetTypes mit AI-Extraktion gefunden")
            return

        # 3. Get or create AI task for tracking
        if existing_task_id:
            # Use existing task from service layer
            ai_task = await session.get(AITask, UUID(existing_task_id))
            if ai_task:
                ai_task.status = AITaskStatus.RUNNING
                ai_task.description = f"Extrahiere {len(facet_types)} Facet-Typen aus {len(process.fields)} PySis-Feldern"
                ai_task.progress_total = len(facet_types)
                ai_task.celery_task_id = celery_task_id
                await session.commit()
            else:
                logger.warning("Existing task not found, creating new", existing_task_id=existing_task_id)
                existing_task_id = None

        if not existing_task_id:
            # Create new task (fallback or direct call)
            ai_task = AITask(
                task_type=AITaskType.PYSIS_TO_FACETS,
                status=AITaskStatus.RUNNING,
                name=f"PySis-Facet-Analyse: {entity.name}",
                description=f"Extrahiere {len(facet_types)} Facet-Typen aus {len(process.fields)} PySis-Feldern",
                process_id=process.id,
                started_at=datetime.now(timezone.utc),
                progress_total=len(facet_types),
                celery_task_id=celery_task_id,
            )
            session.add(ai_task)
            await session.commit()
            await session.refresh(ai_task)

        task_id = ai_task.id

        # 4. Collect field values
        field_data = []
        for field in process.fields:
            value = field.current_value or field.pysis_value or field.ai_extracted_value

            if not value and not include_empty:
                continue

            if field.confidence_score and field.confidence_score < min_confidence:
                continue

            field_data.append({
                "name": field.internal_name,
                "pysis_name": field.pysis_field_name,
                "value": value,
                "source": field.value_source.value if field.value_source else "UNKNOWN",
                "confidence": field.confidence_score,
            })

        if not field_data:
            ai_task.status = AITaskStatus.COMPLETED
            ai_task.completed_at = datetime.now(timezone.utc)
            ai_task.error_message = "Keine Felder zum Analysieren"
            await session.commit()
            return

        logger.info(
            "Analyzing PySis fields for facets",
            process_id=process_id,
            entity_name=entity.name,
            field_count=len(field_data),
            facet_type_count=len(facet_types),
        )

        # 5. Run AI analysis with dynamic FacetTypes
        try:
            facet_extractions = await _extract_facets_from_pysis_fields_dynamic(
                field_data,
                entity.name,
                facet_types,
            )
        except Exception as e:
            ai_task = await session.get(AITask, task_id)
            ai_task.status = AITaskStatus.FAILED
            ai_task.error_message = str(e)
            ai_task.completed_at = datetime.now(timezone.utc)
            await session.commit()
            raise

        # 6. Create FacetValues dynamically
        facet_counts = await _create_facets_from_pysis_extraction_dynamic(
            session,
            entity,
            facet_extractions,
            facet_types,
            task_id,
            process=process,
            field_data=field_data,
        )

        # 7. Complete task
        ai_task = await session.get(AITask, task_id)
        ai_task.status = AITaskStatus.COMPLETED
        ai_task.completed_at = datetime.now(timezone.utc)
        ai_task.fields_extracted = sum(facet_counts.values())
        await session.commit()

        logger.info(
            "PySis to facets analysis completed",
            process_id=process_id,
            entity_name=entity.name,
            facet_counts=facet_counts,
        )


async def _extract_facets_from_pysis_fields_dynamic(
    fields: List[Dict[str, Any]],
    entity_name: str,
    facet_types: List["FacetType"],
) -> Dict[str, Any]:
    """
    Extract facets from PySis field values using AI with dynamic FacetTypes.

    Args:
        fields: List of PySis field data
        entity_name: Name of the entity (e.g., municipality)
        facet_types: List of FacetType objects to extract

    Returns:
        Dict with slug as key and list of extracted items as value
    """
    from services.ai_client import AzureOpenAIClientFactory

    client = AzureOpenAIClientFactory.create_client()

    # Prepare field values as structured text
    fields_text = "PYSIS-FELDER:\n\n"
    for f in fields:
        field_name = f.get("name", "Unbekannt")
        pysis_name = f.get("pysis_name", "unknown")
        field_value = f.get("value", "")

        fields_text += f"--- {field_name} ({pysis_name}) ---\n"
        fields_text += f"Wert: {field_value}\n"
        if f.get("confidence") is not None:
            fields_text += f"Konfidenz: {f['confidence']:.0%}\n"
        fields_text += "\n"

    # Limit context size
    if len(fields_text) > PYSIS_MAX_CONTEXT_LENGTH:
        fields_text = fields_text[:PYSIS_MAX_CONTEXT_LENGTH] + "\n\n[... Text gekürzt ...]"

    # Build dynamic facet type descriptions
    facet_descriptions = []
    response_schema = {}

    for idx, ft in enumerate(facet_types, 1):
        # Use custom ai_extraction_prompt if available, otherwise build from name/description
        if ft.ai_extraction_prompt:
            instruction = ft.ai_extraction_prompt
        else:
            instruction = f"Extrahiere Informationen zu: {ft.name}"
            if ft.description:
                instruction += f" - {ft.description}"

        # Build schema description from value_schema
        schema_desc = ""
        if ft.value_schema and isinstance(ft.value_schema, dict):
            props = ft.value_schema.get("properties", {})
            if props:
                schema_fields = []
                for prop_name, prop_def in props.items():
                    prop_type = prop_def.get("type", "string")
                    prop_desc = prop_def.get("description", "")
                    if prop_desc:
                        schema_fields.append(f"  - {prop_name}: {prop_desc}")
                    else:
                        schema_fields.append(f"  - {prop_name} ({prop_type})")
                if schema_fields:
                    schema_desc = "\n   Felder:\n" + "\n".join(schema_fields)

        facet_descriptions.append(
            f"{idx}. {ft.name.upper()} (slug: {ft.slug})\n"
            f"   {instruction}{schema_desc}"
        )

        # Build response schema hint
        if ft.value_type == "text":
            response_schema[ft.slug] = "string oder null"
        else:
            response_schema[ft.slug] = "[{...}, {...}] (Array von Objekten)"

    facet_list = "\n\n".join(facet_descriptions)
    response_format_hint = json.dumps(response_schema, ensure_ascii=False, indent=2)

    system_prompt = f"""Du bist ein Experte für die Analyse von Projektdaten.

AUFGABE:
Analysiere die folgenden PySis-Feldwerte für "{entity_name}" und extrahiere strukturierte Informationen.

Du sollst folgende Kategorien von Informationen extrahieren:

{facet_list}

WICHTIGE REGELN:
- Extrahiere NUR Informationen, die tatsächlich in den Felddaten enthalten sind
- Erfinde KEINE Informationen
- Wenn keine Informationen für eine Kategorie vorhanden sind, gib ein leeres Array [] oder null zurück
- Jeder extrahierte Eintrag sollte eine aussagekräftige Beschreibung oder einen Wert haben
- WICHTIG: Für jeden extrahierten Eintrag MUSS ein "source_fields" Array angegeben werden, das die pysis_name(n) der Felder enthält, aus denen die Information stammt

ANTWORTFORMAT (JSON):
{{
{response_format_hint},
  "extraction_confidence": 0.8,
  "extraction_notes": "Kurze Notiz zur Qualität der Extraktion"
}}

BEISPIEL für einen extrahierten Kontakt:
{{
  "name": "Max Mustermann",
  "role": "Projektleiter",
  "source_fields": ["zustndigkeitpm", "chat.participants"]
}}
"""

    try:
        response = await client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": fields_text},
            ],
            temperature=AI_EXTRACTION_TEMPERATURE,
            max_tokens=AI_EXTRACTION_MAX_TOKENS,
            response_format={"type": "json_object"},
        )

        # Validate response structure
        if not response.choices:
            raise RuntimeError("KI-Service Fehler: Leere Antwort vom AI-Service")

        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("KI-Service Fehler: Keine Inhalte in der AI-Antwort")

        result = json.loads(content)
        return result

    except json.JSONDecodeError as e:
        logger.error("Failed to parse AI response", error=str(e))
        raise RuntimeError(f"KI-Service Fehler: AI-Antwort konnte nicht verarbeitet werden - {str(e)}")
    except RuntimeError:
        raise  # Re-raise our own RuntimeErrors
    except Exception as e:
        logger.exception("Azure OpenAI API call failed for PySis facet extraction")
        raise RuntimeError(f"KI-Service nicht erreichbar: {str(e)}")


def _build_pysis_source_metadata(
    item_source_fields: List[str],
    pysis_fields_dict: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build metadata dict with source field names and their values.

    Args:
        item_source_fields: List of PySis field names that contributed to this item
        pysis_fields_dict: Dict mapping field names to their values

    Returns:
        Dict with pysis_field_names and pysis_fields (if values exist)
    """
    if not item_source_fields:
        return {}

    metadata = {"pysis_field_names": item_source_fields}

    # Include actual values from those fields (use walrus operator to avoid double .get())
    source_field_values = {
        field: value
        for field in item_source_fields
        if (value := pysis_fields_dict.get(field))
    }
    if source_field_values:
        metadata["pysis_fields"] = source_field_values

    return metadata


async def _create_facets_from_pysis_extraction_dynamic(
    session: "AsyncSession",
    entity: "Entity",
    extractions: Dict[str, Any],
    facet_types: List["FacetType"],
    task_id: UUID,
    process: Optional["PySisProcess"] = None,
    field_data: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, int]:
    """
    Create FacetValues from AI extraction dynamically based on FacetTypes.

    Args:
        session: Database session
        entity: Entity to attach facets to
        extractions: Dict with slug as key and extracted data as value
        facet_types: List of FacetType objects
        task_id: AI task ID for progress tracking
        process: PySisProcess object for metadata
        field_data: List of field dicts with name, pysis_name, value, etc.

    Returns:
        Dict with facet type slug as key and count of created facets as value
    """
    from app.models import AITask
    from app.models.facet_value import FacetValueSourceType
    from services.entity_facet_service import (
        check_duplicate_facet,
        create_facet_value,
    )

    counts = {}
    base_confidence = extractions.get("extraction_confidence", PYSIS_BASE_CONFIDENCE)

    # Build base PySis metadata (process info only)
    pysis_base_metadata = {}
    if process:
        pysis_base_metadata["pysis_process_id"] = str(process.id)
        pysis_base_metadata["pysis_process_title"] = process.name or "PySis Prozess"

    # Build a dict of field values for looking up source field values
    # Use walrus operator to avoid double .get() calls
    pysis_fields_dict = {}
    if field_data:
        pysis_fields_dict = {
            key: value
            for f in field_data
            if (key := (f.get("pysis_name") or f.get("name")))
            and (value := f.get("value"))
        }

    for idx, ft in enumerate(facet_types):
        counts[ft.slug] = 0

        # Get extracted data for this facet type
        extracted_data = extractions.get(ft.slug)
        if not extracted_data:
            continue

        # Handle different value types
        if ft.value_type == "text":
            # Single text value (like summary) - can be string or dict with text+source_fields
            text_content = None
            item_source_fields = []

            if isinstance(extracted_data, str) and len(extracted_data) > PYSIS_MIN_TEXT_LENGTH:
                text_content = extracted_data
            elif isinstance(extracted_data, dict):
                text_content = extracted_data.get("text") or extracted_data.get("description")
                item_source_fields = extracted_data.get("source_fields", [])

            if text_content and len(text_content) > PYSIS_MIN_TEXT_LENGTH:
                # Build metadata with specific source fields
                value_with_metadata = {
                    "text": text_content,
                    **pysis_base_metadata,
                    **_build_pysis_source_metadata(item_source_fields, pysis_fields_dict),
                }

                await create_facet_value(
                    session,
                    entity_id=entity.id,
                    facet_type_id=ft.id,
                    value=value_with_metadata,
                    text_representation=text_content[:PYSIS_SUMMARY_MAX_LENGTH],
                    confidence_score=base_confidence,
                    source_type=FacetValueSourceType.PYSIS,
                )
                counts[ft.slug] = 1
        else:
            # List of structured values
            if not isinstance(extracted_data, list):
                extracted_data = [extracted_data] if extracted_data else []

            for item in extracted_data:
                if not isinstance(item, dict):
                    continue

                # Extract source_fields from item (added by AI) - use get() to avoid mutating input
                item_source_fields = item.get("source_fields", [])

                # Get text representation for deduplication
                # Try common field names
                text_repr = (
                    item.get("description")
                    or item.get("text")
                    or item.get("name")
                    or item.get("title")
                    or str(item)
                )

                if not text_repr or len(str(text_repr)) < PYSIS_MIN_DEDUP_TEXT_LENGTH:
                    continue

                text_repr = str(text_repr)

                # Check for duplicates using deduplication_fields if configured
                dedup_text = text_repr
                if ft.deduplication_fields:
                    # Use walrus operator to avoid double .get() calls
                    dedup_parts = [
                        str(val) for f in ft.deduplication_fields
                        if (val := item.get(f))
                    ]
                    if dedup_parts:
                        dedup_text = " ".join(dedup_parts)

                is_dupe = await check_duplicate_facet(
                    session,
                    entity.id,
                    ft.id,
                    dedup_text,
                    similarity_threshold=PYSIS_DUPLICATE_SIMILARITY_THRESHOLD,
                )
                if is_dupe:
                    logger.debug(
                        "Skipping duplicate facet",
                        facet_type=ft.slug,
                        text_preview=dedup_text[:50],
                    )
                    continue

                # Build metadata with specific source fields for this item
                # Filter out source_fields from item since we store it separately as pysis_field_names
                value_with_metadata = {
                    k: v for k, v in item.items() if k != "source_fields"
                }
                value_with_metadata.update(pysis_base_metadata)
                value_with_metadata.update(
                    _build_pysis_source_metadata(item_source_fields, pysis_fields_dict)
                )

                await create_facet_value(
                    session,
                    entity_id=entity.id,
                    facet_type_id=ft.id,
                    value=value_with_metadata,
                    text_representation=text_repr[:PYSIS_TEXT_REPR_MAX_LENGTH],
                    confidence_score=min(
                        PYSIS_MAX_CONFIDENCE,
                        base_confidence + PYSIS_CONFIDENCE_BOOST
                    ),
                    source_type=FacetValueSourceType.PYSIS,
                )
                counts[ft.slug] += 1

        # Update progress after processing each facet type (batch commit)
        if counts[ft.slug] > 0:
            ai_task = await session.get(AITask, task_id)
            if ai_task:
                ai_task.progress_current = idx + 1
                ai_task.current_item = ft.name
                await session.commit()

    return counts


@celery_app.task(
    bind=True,
    name="workers.ai_tasks.enrich_facet_values_from_pysis",
    max_retries=3,
    default_retry_delay=60,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    rate_limit="10/m",  # 10 requests per minute to respect Azure rate limits
    soft_time_limit=600,  # 10 minutes soft limit
    time_limit=660,  # 11 minutes hard limit
)
def enrich_facet_values_from_pysis(
    self,
    entity_id: str,
    facet_type_id: Optional[str] = None,
    overwrite_existing: bool = False,
    existing_task_id: Optional[str] = None,
):
    """
    Enrich existing FacetValues with data from PySis fields.

    Args:
        entity_id: UUID of the entity
        facet_type_id: Optional - only enrich this FacetType
        overwrite_existing: Replace existing field values
        existing_task_id: Existing AITask ID (to avoid duplicate creation)
    """
    import asyncio
    asyncio.run(_enrich_facet_values_from_pysis_async(
        entity_id,
        facet_type_id,
        overwrite_existing,
        self.request.id,
        existing_task_id,
    ))


async def _enrich_facet_values_from_pysis_async(
    entity_id: str,
    facet_type_id: Optional[str],
    overwrite_existing: bool,
    celery_task_id: Optional[str] = None,
    existing_task_id: Optional[str] = None,
):
    """Async implementation of FacetValue enrichment from PySis."""
    from app.database import get_celery_session_context
    from app.models.pysis import PySisProcess
    from app.models import AITask, AITaskStatus, AITaskType, Entity, FacetType, FacetValue
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from datetime import datetime, timezone

    async with get_celery_session_context() as session:
        # Helper to mark task as failed if it exists
        async def fail_task_if_exists(error_msg: str):
            if existing_task_id:
                task = await session.get(AITask, UUID(existing_task_id))
                if task:
                    task.status = AITaskStatus.FAILED
                    task.error_message = error_msg
                    task.completed_at = datetime.now(timezone.utc)
                    await session.commit()

        entity = await session.get(Entity, UUID(entity_id))
        if not entity:
            logger.error("Entity not found", entity_id=entity_id)
            await fail_task_if_exists(f"Entity nicht gefunden: {entity_id}")
            return

        # 1. Load PySis processes for this entity
        pysis_result = await session.execute(
            select(PySisProcess)
            .options(selectinload(PySisProcess.fields))
            .where(PySisProcess.entity_id == UUID(entity_id))
        )
        processes = pysis_result.scalars().all()

        if not processes:
            logger.warning("No PySis processes found for entity", entity_id=entity_id)
            await fail_task_if_exists(f"Keine PySis-Prozesse für Entity gefunden: {entity.name}")
            return

        # 2. Collect all PySis field data
        pysis_fields = []
        for process in processes:
            for field in process.fields:
                value = field.current_value or field.pysis_value or field.ai_extracted_value
                if value:
                    pysis_fields.append({
                        "name": field.internal_name,
                        "pysis_name": field.pysis_field_name,
                        "value": value,
                        "confidence": field.confidence_score,
                    })

        if not pysis_fields:
            logger.info("No PySis field values found", entity_id=entity_id)
            await fail_task_if_exists("Keine PySis-Feldwerte zum Anreichern gefunden")
            return

        # 3. Load FacetValues to enrich
        query = (
            select(FacetValue)
            .options(selectinload(FacetValue.facet_type))
            .where(FacetValue.entity_id == UUID(entity_id))
            .where(FacetValue.is_active.is_(True))
        )
        if facet_type_id:
            query = query.where(FacetValue.facet_type_id == UUID(facet_type_id))

        result = await session.execute(query)
        facet_values = result.scalars().all()

        if not facet_values:
            logger.info("No FacetValues to enrich")
            await fail_task_if_exists("Keine FacetValues zum Anreichern gefunden")
            return

        # 4. Get or create AI task for tracking
        if existing_task_id:
            # Use existing task from service layer
            ai_task = await session.get(AITask, UUID(existing_task_id))
            if ai_task:
                ai_task.status = AITaskStatus.RUNNING
                ai_task.description = f"Reichere {len(facet_values)} FacetValues mit PySis-Daten an"
                ai_task.progress_total = len(facet_values)
                ai_task.celery_task_id = celery_task_id
                await session.commit()
            else:
                logger.warning("Existing task not found, creating new", existing_task_id=existing_task_id)
                existing_task_id = None

        if not existing_task_id:
            # Create new task (fallback or direct call)
            ai_task = AITask(
                task_type=AITaskType.PYSIS_TO_FACETS,
                status=AITaskStatus.RUNNING,
                name=f"FacetValue-Anreicherung: {entity.name}",
                description=f"Reichere {len(facet_values)} FacetValues mit PySis-Daten an",
                started_at=datetime.now(timezone.utc),
                progress_total=len(facet_values),
                celery_task_id=celery_task_id,
            )
            session.add(ai_task)
            await session.commit()
            await session.refresh(ai_task)

        task_id = ai_task.id

        # 5. Initialize Azure OpenAI client
        from services.ai_client import AzureOpenAIClientFactory
        try:
            client = AzureOpenAIClientFactory.create_client()
        except ValueError as e:
            ai_task.status = AITaskStatus.FAILED
            ai_task.error_message = str(e)
            ai_task.completed_at = datetime.now(timezone.utc)
            await session.commit()
            return

        # 6. Process each FacetValue
        enriched_count = 0
        for idx, fv in enumerate(facet_values):
            # Update progress
            ai_task = await session.get(AITask, task_id)
            ai_task.progress_current = idx + 1
            ai_task.current_item = fv.text_representation[:100] if fv.text_representation else None
            await session.commit()

            # Load FacetType for schema
            facet_type = fv.facet_type
            if not facet_type or not facet_type.value_schema:
                continue

            # Analyze and enrich
            try:
                enriched_value = await _enrich_single_facet_value(
                    client,
                    fv.value or {},
                    facet_type.value_schema,
                    pysis_fields,
                    entity.name,
                    overwrite_existing,
                )

                if enriched_value and enriched_value != fv.value:
                    fv.value = enriched_value
                    fv.updated_at = datetime.now(timezone.utc)
                    fv.ai_model_used = settings.azure_openai_deployment_name

                    # Update text representation
                    text_repr = (
                        enriched_value.get("description")
                        or enriched_value.get("text")
                        or enriched_value.get("name")
                        or str(enriched_value)
                    )
                    if text_repr:
                        fv.text_representation = str(text_repr)[:2000]

                    enriched_count += 1
                    await session.commit()

            except Exception as e:
                logger.error(
                    "Failed to enrich FacetValue",
                    facet_value_id=str(fv.id),
                    error=str(e)
                )

        # 7. Complete task
        ai_task = await session.get(AITask, task_id)
        ai_task.status = AITaskStatus.COMPLETED
        ai_task.completed_at = datetime.now(timezone.utc)
        ai_task.fields_extracted = enriched_count
        await session.commit()

        logger.info(
            "FacetValue enrichment completed",
            entity_id=entity_id,
            enriched=enriched_count,
            total=len(facet_values),
        )


async def _enrich_single_facet_value(
    client: "AsyncAzureOpenAI",
    current_value: Dict[str, Any],
    value_schema: Dict[str, Any],
    pysis_fields: List[Dict[str, Any]],
    entity_name: str,
    overwrite_existing: bool,
) -> Optional[Dict[str, Any]]:
    """
    Enrich a single FacetValue using AI.

    Args:
        client: Azure OpenAI client
        current_value: Current value dict
        value_schema: JSON Schema defining expected structure
        pysis_fields: Available PySis field data
        entity_name: Name of the entity
        overwrite_existing: Whether to overwrite existing values

    Returns:
        Enriched value dict or None if no changes
    """
    # Identify missing or empty fields
    schema_properties = value_schema.get("properties", {})
    missing_fields = []

    for field_name, field_def in schema_properties.items():
        current_field_value = current_value.get(field_name)
        # Skip fields that have values unless overwrite is enabled
        if current_field_value and not overwrite_existing:
            continue
        # Skip internal fields
        if field_name in ["id", "created_at", "updated_at"]:
            continue

        missing_fields.append({
            "name": field_name,
            "type": field_def.get("type", "string"),
            "description": field_def.get("description", ""),
        })

    if not missing_fields:
        return None

    # Build prompt
    pysis_text = "\n".join([
        f"- {f['name']}: {f['value']}"
        for f in pysis_fields[:30]  # Limit context
    ])

    missing_fields_text = "\n".join([
        f"- {f['name']} ({f['type']}): {f['description']}"
        for f in missing_fields
    ])

    prompt = f"""Analysiere die PySis-Daten für "{entity_name}" und extrahiere fehlende Informationen.

AKTUELLE WERTE:
{json.dumps(current_value, ensure_ascii=False, indent=2)}

FEHLENDE FELDER (zu befüllen):
{missing_fields_text}

VERFÜGBARE PYSIS-DATEN:
{pysis_text}

Ergänze die fehlenden Felder basierend auf den verfügbaren Daten.
Antworte im JSON-Format mit NUR den neuen/aktualisierten Feldern.
Wenn keine passenden Daten gefunden werden, gib ein leeres Objekt {{}} zurück.
Erfinde KEINE Informationen."""

    try:
        response = await client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=[
                {"role": "system", "content": "Du extrahierst strukturierte Daten aus Textfeldern. Antworte nur mit JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=1000,
            response_format={"type": "json_object"},
        )

        enriched = json.loads(response.choices[0].message.content)

        if enriched:
            # Merge with current value
            result = current_value.copy()
            for key, value in enriched.items():
                if key in schema_properties and value:
                    result[key] = value
            return result

        return None

    except Exception as e:
        logger.error("AI enrichment failed", error=str(e))
        return None


# =============================================================================
# Entity Data Analysis for Facet Enrichment
# =============================================================================


@celery_app.task(
    bind=True,
    name="workers.ai_tasks.analyze_entity_data_for_facets",
    max_retries=3,
    default_retry_delay=60,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    rate_limit="10/m",
    soft_time_limit=600,
    time_limit=660,
)
def analyze_entity_data_for_facets(
    self,
    entity_id: str,
    source_types: List[str],
    target_facet_types: List[str],
    task_id: str,
):
    """
    Analyze entity data from multiple sources and create facet suggestions.

    This task:
    1. Collects data from specified sources (relations, documents, extractions, pysis)
    2. Analyzes with AI to extract facet suggestions
    3. Stores preview in AITask.result_data (no direct writes)

    Args:
        entity_id: UUID of the entity
        source_types: List of source types to analyze
        target_facet_types: List of facet type slugs to generate
        task_id: AITask ID for progress tracking
    """
    import asyncio
    asyncio.run(_analyze_entity_data_for_facets_async(
        entity_id,
        source_types,
        target_facet_types,
        task_id,
    ))


async def _analyze_entity_data_for_facets_async(
    entity_id: str,
    source_types: List[str],
    target_facet_types: List[str],
    task_id: str,
):
    """Async implementation of entity data analysis."""
    from app.database import get_celery_session_context
    from app.models import AITask, AITaskStatus, Entity, FacetType
    from sqlalchemy import select
    from services.entity_data_facet_service import (
        collect_entity_data,
        get_existing_facets,
        compute_value_hash,
    )

    async with get_celery_session_context() as session:
        # Helper to mark task as failed
        async def fail_task(error_msg: str):
            task = await session.get(AITask, UUID(task_id))
            if task:
                task.status = AITaskStatus.FAILED
                task.error_message = error_msg
                task.completed_at = datetime.now(timezone.utc)
                await session.commit()

        try:
            # 1. Load and validate task
            ai_task = await session.get(AITask, UUID(task_id))
            if not ai_task:
                logger.error("AI task not found", task_id=task_id)
                return

            ai_task.status = AITaskStatus.RUNNING
            await session.commit()

            # 2. Load entity
            entity = await session.get(Entity, UUID(entity_id))
            if not entity:
                await fail_task(f"Entity nicht gefunden: {entity_id}")
                return

            # 3. Load facet types
            ft_result = await session.execute(
                select(FacetType)
                .where(FacetType.slug.in_(target_facet_types))
                .where(FacetType.is_active.is_(True))
            )
            facet_types = ft_result.scalars().all()
            facet_type_map = {ft.slug: ft for ft in facet_types}

            if not facet_types:
                await fail_task("Keine gültigen Facet-Typen gefunden")
                return

            # 4. Collect data from sources
            ai_task.current_item = "Sammle Daten..."
            ai_task.progress_total = len(source_types) + 2  # +2 for AI analysis + existing facets
            ai_task.progress_current = 0
            await session.commit()

            collected_data = await collect_entity_data(
                session, UUID(entity_id), source_types
            )

            ai_task.progress_current = len(source_types)
            ai_task.current_item = "Lade bestehende Facets..."
            await session.commit()

            # 5. Get existing facets for deduplication
            existing_facets = await get_existing_facets(session, UUID(entity_id))
            existing_hashes = {
                compute_value_hash(f["value"]) for f in existing_facets
            }

            ai_task.progress_current = len(source_types) + 1
            ai_task.current_item = "Analysiere mit KI..."
            await session.commit()

            # 6. Run AI analysis
            ai_result = await _run_entity_data_ai_analysis(
                collected_data,
                existing_facets,
                facet_types,
                entity.name,
            )

            # 7. Process AI result into preview format
            new_facets = []
            updates = []

            for ft_slug, items in ai_result.get("facets", {}).items():
                if ft_slug not in facet_type_map:
                    continue

                ft = facet_type_map[ft_slug]

                if not isinstance(items, list):
                    items = [items] if items else []

                for item in items:
                    if not isinstance(item, dict):
                        continue

                    # Get text representation
                    text_repr = (
                        item.get("description")
                        or item.get("text")
                        or item.get("name")
                        or str(item)
                    )

                    if not text_repr or len(str(text_repr)) < 5:
                        continue

                    # Check if this matches an existing facet
                    item_hash = compute_value_hash(item)
                    matching_existing = None

                    for existing in existing_facets:
                        if existing["facet_type"] == ft_slug:
                            # Check for potential update
                            existing_text = existing.get("text", "")
                            if _texts_similar(str(text_repr), existing_text):
                                matching_existing = existing
                                break

                    if matching_existing:
                        # This is an update to existing facet
                        # Compare values to find changes
                        current_val = matching_existing.get("value", {})
                        changes = []
                        for key, new_val in item.items():
                            if key in ["source_fields", "confidence"]:
                                continue
                            old_val = current_val.get(key)
                            if new_val != old_val and new_val:
                                changes.append(key)

                        if changes:
                            updates.append({
                                "facet_value_id": matching_existing["id"],
                                "facet_type": ft_slug,
                                "facet_type_name": ft.name,
                                "current_value": current_val,
                                "proposed_value": item,
                                "changes": changes,
                                "text": str(text_repr)[:500],
                                "confidence": item.get("confidence", 0.7),
                            })
                    elif item_hash not in existing_hashes:
                        # This is a new facet
                        new_facets.append({
                            "facet_type": ft_slug,
                            "facet_type_name": ft.name,
                            "value": item,
                            "text": str(text_repr)[:500],
                            "confidence": item.get("confidence", 0.7),
                            "ai_model": settings.azure_openai_deployment_name,
                        })

            # 8. Store preview in result_data
            ai_task.result_data = {
                **ai_task.result_data,
                "new_facets": new_facets,
                "updates": updates,
                "analysis_summary": {
                    "sources_analyzed": source_types,
                    "facet_types_checked": target_facet_types,
                    "existing_facets_count": len(existing_facets),
                    "new_suggestions": len(new_facets),
                    "update_suggestions": len(updates),
                },
            }
            ai_task.status = AITaskStatus.COMPLETED
            ai_task.completed_at = datetime.now(timezone.utc)
            ai_task.progress_current = ai_task.progress_total
            ai_task.current_item = None
            await session.commit()

            logger.info(
                "Entity data analysis completed",
                entity_id=entity_id,
                task_id=task_id,
                new_facets=len(new_facets),
                updates=len(updates),
            )

        except Exception as e:
            logger.exception("Entity data analysis failed", entity_id=entity_id)
            await fail_task(f"Analyse fehlgeschlagen: {str(e)}")


async def _run_entity_data_ai_analysis(
    collected_data: Dict[str, Any],
    existing_facets: List[Dict[str, Any]],
    facet_types: List["FacetType"],
    entity_name: str,
) -> Dict[str, Any]:
    """
    Run AI analysis on collected entity data.

    Args:
        collected_data: Data collected from various sources
        existing_facets: Existing facet values for deduplication context
        facet_types: Target facet types to generate
        entity_name: Name of the entity

    Returns:
        Dict with "facets" key containing extracted data per facet type
    """
    from services.ai_client import AzureOpenAIClientFactory

    client = AzureOpenAIClientFactory.create_client()

    # Build context from collected data
    context_parts = [f"DATEN FÜR ENTITY: {entity_name}\n"]

    sources = collected_data.get("sources", {})

    # Add relations
    if "relations" in sources and sources["relations"]:
        context_parts.append("\n=== VERKNÜPFUNGEN ===")
        for rel in sources["relations"][:30]:  # Limit
            direction = "→" if rel["direction"] == "outgoing" else "←"
            rel_name = rel.get("relation_name", rel.get("relation_type", "verknüpft"))
            target = rel.get("related_entity", {})
            context_parts.append(
                f"{direction} {rel_name}: {target.get('name', 'Unbekannt')}"
            )
            if rel.get("attributes"):
                context_parts.append(f"   Attribute: {json.dumps(rel['attributes'], ensure_ascii=False)}")
            # Include related entity's facets
            for facet in target.get("facets", [])[:5]:
                context_parts.append(f"   - {facet.get('text', '')[:100]}")

    # Add documents
    if "documents" in sources and sources["documents"]:
        context_parts.append("\n=== DOKUMENTE ===")
        for doc in sources["documents"][:20]:
            context_parts.append(f"- {doc.get('title', 'Unbekannt')} ({doc.get('type', '')})")
            if doc.get("text_preview"):
                context_parts.append(f"  {doc['text_preview'][:500]}")

    # Add extractions
    if "extractions" in sources and sources["extractions"]:
        context_parts.append("\n=== KI-EXTRAKTIONEN ===")
        for ext in sources["extractions"][:20]:
            content = ext.get("content", {})
            context_parts.append(f"- Typ: {ext.get('type', 'unbekannt')}")
            # Add relevant content fields
            for key in ["summary", "pain_points", "positive_signals", "decision_makers"]:
                if key in content and content[key]:
                    context_parts.append(f"  {key}: {json.dumps(content[key], ensure_ascii=False)[:500]}")

    # Add PySIS data
    if "pysis" in sources and sources["pysis"]:
        context_parts.append("\n=== PYSIS-DATEN ===")
        for process in sources["pysis"]:
            context_parts.append(f"Prozess: {process.get('name', 'Unbekannt')}")
            for field in process.get("fields", [])[:30]:
                context_parts.append(f"  - {field['name']}: {field['value']}")

    context_text = "\n".join(context_parts)

    # Limit context
    if len(context_text) > 60000:
        context_text = context_text[:60000] + "\n\n[... Text gekürzt ...]"

    # Build facet type descriptions
    facet_descriptions = []
    for ft in facet_types:
        desc = f"- {ft.name} (slug: {ft.slug})"
        if ft.ai_extraction_prompt:
            desc += f": {ft.ai_extraction_prompt}"
        elif ft.description:
            desc += f": {ft.description}"
        facet_descriptions.append(desc)

    # Add existing facets context
    existing_context = ""
    if existing_facets:
        existing_context = "\n\nBEREITS VORHANDENE FACETS (nicht duplizieren, aber erweitern wenn neue Infos):\n"
        for ef in existing_facets[:30]:
            existing_context += f"- {ef.get('facet_type_name', ef.get('facet_type', ''))}: {ef.get('text', '')[:100]}\n"

    system_prompt = f"""Du bist ein Experte für die Extraktion strukturierter Informationen aus Projektdaten.

AUFGABE:
Analysiere die folgenden Daten für "{entity_name}" und extrahiere relevante Informationen für die angegebenen Facet-Typen.

ZU EXTRAHIERENDE FACET-TYPEN:
{chr(10).join(facet_descriptions)}
{existing_context}

WICHTIGE REGELN:
1. Extrahiere NUR Informationen, die tatsächlich in den Daten enthalten sind
2. Erfinde KEINE Informationen
3. Dupliziere KEINE bereits vorhandenen Facets - ergänze nur wenn neue Informationen verfügbar sind
4. Für jeden extrahierten Eintrag gib eine "confidence" (0.0-1.0) an
5. Bei Kontakten: Versuche Name, Rolle, E-Mail, Telefon zu extrahieren
6. Bei Pain Points: Beschreibe das Problem und den Typ (z.B. "Genehmigung", "Widerstand", etc.)

ANTWORTFORMAT (JSON):
{{
  "facets": {{
    "<facet_slug>": [
      {{"description": "...", "type": "...", "confidence": 0.8}},
      ...
    ],
    ...
  }},
  "analysis_notes": "Kurze Notiz zur Analyse"
}}"""

    try:
        response = await client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context_text},
            ],
            temperature=0.2,
            max_tokens=4000,
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)
        return result

    except json.JSONDecodeError as e:
        logger.error("Failed to parse AI response", error=str(e))
        raise RuntimeError(f"KI-Service Fehler: AI-Antwort konnte nicht verarbeitet werden")
    except Exception as e:
        logger.exception("AI analysis failed")
        raise RuntimeError(f"KI-Service nicht erreichbar: {str(e)}")


def _texts_similar(text1: str, text2: str, threshold: float = 0.7) -> bool:
    """Check if two texts are similar using simple word overlap."""
    if not text1 or not text2:
        return False

    # Normalize
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())

    if not words1 or not words2:
        return False

    # Jaccard similarity
    intersection = len(words1 & words2)
    union = len(words1 | words2)

    return (intersection / union) >= threshold if union > 0 else False


# =============================================================================
# Entity Attachment Analysis
# =============================================================================


@celery_app.task(
    bind=True,
    name="workers.ai_tasks.analyze_attachment_task",
    max_retries=3,
    default_retry_delay=60,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    rate_limit="5/m",  # 5 requests per minute for vision API
    soft_time_limit=300,  # 5 minutes soft limit
    time_limit=360,  # 6 minutes hard limit
)
def analyze_attachment_task(
    self,
    attachment_id: str,
    task_id: str,
    extract_facets: bool = True,
):
    """
    Analyze an entity attachment with AI.

    For images: Uses Vision API to analyze content
    For PDFs: Extracts text and analyzes with standard AI

    Args:
        attachment_id: UUID of the attachment
        task_id: AITask ID for progress tracking
        extract_facets: Whether to extract facet suggestions
    """
    import asyncio
    asyncio.run(_analyze_attachment_async(attachment_id, task_id, extract_facets))


async def _analyze_attachment_async(
    attachment_id: str,
    task_id: str,
    extract_facets: bool,
):
    """Async implementation of attachment analysis."""
    from pathlib import Path
    from app.database import get_celery_session_context
    from app.models import AITask, AITaskStatus, Entity, FacetType
    from app.models.entity_attachment import AttachmentAnalysisStatus, EntityAttachment
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    async with get_celery_session_context() as session:
        # Helper to mark task as failed
        async def fail_task(error_msg: str):
            ai_task = await session.get(AITask, UUID(task_id))
            if ai_task:
                ai_task.status = AITaskStatus.FAILED
                ai_task.error_message = error_msg
                ai_task.completed_at = datetime.now(timezone.utc)
            attachment = await session.get(EntityAttachment, UUID(attachment_id))
            if attachment:
                attachment.analysis_status = AttachmentAnalysisStatus.FAILED
                attachment.analysis_error = error_msg
            await session.commit()

        try:
            # 1. Load attachment
            attachment = await session.get(EntityAttachment, UUID(attachment_id))
            if not attachment:
                await fail_task(f"Attachment nicht gefunden: {attachment_id}")
                return

            # Update task progress
            ai_task = await session.get(AITask, UUID(task_id))
            if ai_task:
                ai_task.status = AITaskStatus.RUNNING
                ai_task.progress_current = 1
                ai_task.current_item = "Lade Datei..."
                ai_task.celery_task_id = analyze_attachment_task.request.id
                await session.commit()

            # 2. Load entity and facet types
            entity = await session.get(Entity, attachment.entity_id)
            if not entity:
                await fail_task(f"Entity nicht gefunden: {attachment.entity_id}")
                return

            # Get entity type to find applicable facet types
            facet_types = []
            if extract_facets:
                ft_result = await session.execute(
                    select(FacetType)
                    .where(FacetType.is_active.is_(True))
                    .where(FacetType.ai_extraction_enabled.is_(True))
                )
                facet_types = ft_result.scalars().all()

            # 3. Get file path
            storage_path = Path(settings.attachment_storage_path)
            file_path = storage_path / attachment.file_path

            if not file_path.exists():
                await fail_task(f"Datei nicht gefunden: {attachment.file_path}")
                return

            # Update progress
            if ai_task:
                ai_task.progress_current = 2
                ai_task.current_item = "Analysiere mit KI..."
                await session.commit()

            # 4. Analyze based on type
            from services.attachment_analysis_service import (
                analyze_image_with_vision,
                analyze_pdf_with_ai,
                extract_facet_suggestions,
            )

            if attachment.is_image:
                logger.info(
                    "Analyzing image attachment",
                    attachment_id=attachment_id,
                    filename=attachment.filename,
                )
                analysis_result = await analyze_image_with_vision(
                    file_path,
                    entity.name,
                    facet_types,
                )
            elif attachment.is_pdf:
                logger.info(
                    "Analyzing PDF attachment",
                    attachment_id=attachment_id,
                    filename=attachment.filename,
                )
                analysis_result = await analyze_pdf_with_ai(
                    file_path,
                    entity.name,
                    facet_types,
                )
            else:
                await fail_task(f"Nicht unterstuetzter Dateityp: {attachment.content_type}")
                return

            # 5. Extract facet suggestions
            if extract_facets and facet_types:
                if ai_task:
                    ai_task.progress_current = 3
                    ai_task.current_item = "Extrahiere Facet-Vorschlaege..."
                    await session.commit()

                facet_suggestions = await extract_facet_suggestions(
                    analysis_result,
                    attachment.entity_id,
                    facet_types,
                    session,
                )
                analysis_result["facet_suggestions"] = facet_suggestions

            # 6. Update attachment with result
            attachment.analysis_status = AttachmentAnalysisStatus.COMPLETED
            attachment.analysis_result = analysis_result
            attachment.analyzed_at = datetime.now(timezone.utc)
            attachment.ai_model_used = analysis_result.get("ai_model_used")

            # 7. Update task as completed
            if ai_task:
                ai_task.status = AITaskStatus.COMPLETED
                ai_task.completed_at = datetime.now(timezone.utc)
                ai_task.progress_current = ai_task.progress_total
                ai_task.current_item = None
                ai_task.result_data = {
                    **ai_task.result_data,
                    "analysis_result": {
                        "description": analysis_result.get("description", "")[:500],
                        "facet_suggestions_count": len(analysis_result.get("facet_suggestions", [])),
                        "entities_found": bool(analysis_result.get("entities")),
                    },
                }

            await session.commit()

            logger.info(
                "Attachment analysis completed",
                attachment_id=attachment_id,
                filename=attachment.filename,
                facet_suggestions=len(analysis_result.get("facet_suggestions", [])),
            )

            # Emit notification event
            from workers.notification_tasks import emit_event
            emit_event.delay(
                "AI_ANALYSIS_COMPLETED",
                {
                    "entity_type": "attachment",
                    "entity_id": attachment_id,
                    "title": f"Attachment analysiert: {attachment.filename}",
                    "entity_name": entity.name,
                }
            )

        except SoftTimeLimitExceeded:
            logger.warning("Attachment analysis timed out", attachment_id=attachment_id)
            await fail_task("Analyse-Timeout ueberschritten")

        except Exception as e:
            logger.exception("Attachment analysis failed", attachment_id=attachment_id)
            await fail_task(f"Analyse fehlgeschlagen: {str(e)}")
