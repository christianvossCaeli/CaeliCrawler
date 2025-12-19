"""Celery tasks for AI analysis."""

import json
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from celery import shared_task
import structlog

from workers.celery_app import celery_app
from app.config import settings

logger = structlog.get_logger()


@celery_app.task(bind=True, name="workers.ai_tasks.analyze_document")
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

            # Get source for location info
            source = await session.get(DataSource, document.source_id)
            source_location = source.location_name if source else None
            source_region = source.region if source else None
            source_admin_level_1 = source.admin_level_1 if source else None

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
                        handler = getattr(category, 'extraction_handler', 'default') or 'default'
                        if handler == "event":
                            from services.event_extraction_service import convert_event_extraction_to_facets
                            facet_counts = await convert_event_extraction_to_facets(
                                session, extracted, source
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
) -> Optional[Dict[str, Any]]:
    """Call Azure OpenAI API for document analysis."""
    from openai import AsyncAzureOpenAI

    if not settings.azure_openai_api_key:
        logger.warning("Azure OpenAI not configured")
        return None

    client = AsyncAzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
    )

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
        return None
    except Exception as e:
        logger.exception("Azure OpenAI API call failed")
        raise


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
                .where(ExtractedData.human_verified == False)
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


@celery_app.task(bind=True, name="workers.ai_tasks.extract_pysis_fields")
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
            PySisProcessField.ai_extraction_enabled == True
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
                or_ = content.get("outreach_recommendation")
                if isinstance(or_, dict):
                    context_parts.append(f"Outreach: {json.dumps(or_, ensure_ascii=False)}")

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
) -> tuple[Optional[str], float]:
    """
    Extract a single PySis field value using AI.

    Returns:
        Tuple of (extracted_value, confidence_score)
    """
    from openai import AsyncAzureOpenAI

    if not settings.azure_openai_api_key:
        logger.warning("Azure OpenAI not configured")
        return None, 0.0

    client = AsyncAzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
    )

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
        return None, 0.0
    except Exception as e:
        logger.exception("Azure OpenAI API call failed for PySis field extraction")
        raise


@celery_app.task(name="workers.ai_tasks.convert_extractions_to_facets")
def convert_extractions_to_facets(
    min_confidence: float = 0.5,
    batch_size: int = 100,
    entity_type_slug: str = "municipality",
):
    """
    Convert existing ExtractedData to FacetValues in the Entity-Facet system.

    This is a migration task to retroactively populate the Entity-Facet system
    from existing AI extractions.

    Args:
        min_confidence: Minimum confidence score for extractions to process
        batch_size: Number of extractions to process per batch
        entity_type_slug: Entity type to create (default: municipality)
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
                    content = extraction.final_content
                    municipality_name = (
                        content.get("municipality")
                        or content.get("source_location")
                        or (source.location_name if source else None)
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


@celery_app.task(name="workers.ai_tasks.sync_entity_from_source")
def sync_entity_from_source(source_id: str):
    """
    Synchronize Entity from a DataSource's location_name.

    Creates or updates the Entity and links the source to it.

    Args:
        source_id: UUID of the DataSource
    """
    import asyncio
    asyncio.run(_sync_entity_from_source_async(source_id))


async def _sync_entity_from_source_async(source_id: str):
    """Async implementation of entity synchronization."""
    from app.database import get_celery_session_context
    from app.models import DataSource
    from services.entity_facet_service import link_source_to_entity

    async with get_celery_session_context() as session:
        source = await session.get(DataSource, UUID(source_id))
        if not source:
            logger.warning("Source not found", source_id=source_id)
            return

        entity = await link_source_to_entity(session, source)
        await session.commit()

        if entity:
            logger.info(
                "Synchronized entity from source",
                source_id=source_id,
                entity_id=str(entity.id),
                entity_name=entity.name,
            )
        else:
            logger.debug("No entity created for source", source_id=source_id)


@celery_app.task(name="workers.ai_tasks.batch_sync_entities_from_sources")
def batch_sync_entities_from_sources():
    """
    Batch synchronize all DataSources to Entities.

    Creates Entity records for all sources with location_name and links them.
    """
    import asyncio
    asyncio.run(_batch_sync_entities_async())


async def _batch_sync_entities_async():
    """Async implementation of batch entity synchronization."""
    from app.database import get_celery_session_context
    from app.models import DataSource
    from services.entity_facet_service import link_source_to_entity
    from sqlalchemy import select

    async with get_celery_session_context() as session:
        # Get all sources with location_name but no entity_id
        result = await session.execute(
            select(DataSource)
            .where(DataSource.location_name.isnot(None))
            .where(DataSource.location_name != "")
            .where(DataSource.entity_id.is_(None))
        )
        sources = result.scalars().all()

        logger.info("Starting batch entity sync", source_count=len(sources))

        linked = 0
        errors = 0

        for source in sources:
            try:
                entity = await link_source_to_entity(session, source)
                if entity:
                    linked += 1
            except Exception as e:
                errors += 1
                logger.warning(
                    "Failed to link source to entity",
                    source_id=str(source.id),
                    error=str(e),
                )

        await session.commit()

        logger.info(
            "Batch entity sync completed",
            linked=linked,
            errors=errors,
            total_sources=len(sources),
        )
