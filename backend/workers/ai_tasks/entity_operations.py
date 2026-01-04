"""Entity operation tasks.

This module contains Celery tasks for entity-related AI operations:
- Analyzing entity data for facet enrichment
- Analyzing entity attachments (images, PDFs)
"""

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

import structlog
from celery.exceptions import SoftTimeLimitExceeded

from app.config import settings
from app.models.llm_usage import LLMProvider, LLMTaskType
from services.llm_usage_tracker import record_llm_usage
from workers.async_runner import run_async

if TYPE_CHECKING:
    from app.models.facet_type import FacetType

logger = structlog.get_logger()


# =============================================================================
# Celery Task Registration
# =============================================================================


def register_tasks(celery_app):
    """Register all entity operation tasks with the Celery app."""

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
        source_types: list[str],
        target_facet_types: list[str],
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
        run_async(
            _analyze_entity_data_for_facets_async(
                entity_id,
                source_types,
                target_facet_types,
                task_id,
            )
        )

    async def _analyze_entity_data_for_facets_async(
        entity_id: str,
        source_types: list[str],
        target_facet_types: list[str],
        task_id: str,
    ):
        """Async implementation of entity data analysis."""
        from sqlalchemy import select

        from app.database import get_celery_session_context
        from app.models import AITask, AITaskStatus, Entity, FacetType
        from services.entity_data_facet_service import (
            collect_entity_data,
            compute_value_hash,
            get_existing_facets,
        )

        async with get_celery_session_context() as session:
            # Helper to mark task as failed
            async def fail_task(error_msg: str):
                task = await session.get(AITask, UUID(task_id))
                if task:
                    task.status = AITaskStatus.FAILED
                    task.error_message = error_msg
                    task.completed_at = datetime.now(UTC)
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
                    select(FacetType).where(FacetType.slug.in_(target_facet_types)).where(FacetType.is_active.is_(True))
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

                collected_data = await collect_entity_data(session, UUID(entity_id), source_types)

                ai_task.progress_current = len(source_types)
                ai_task.current_item = "Lade bestehende Facets..."
                await session.commit()

                # 5. Get existing facets for deduplication
                existing_facets = await get_existing_facets(session, UUID(entity_id))
                existing_hashes = {compute_value_hash(f["value"]) for f in existing_facets}

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
                        text_repr = item.get("description") or item.get("text") or item.get("name") or str(item)

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
                                updates.append(
                                    {
                                        "facet_value_id": matching_existing["id"],
                                        "facet_type": ft_slug,
                                        "facet_type_name": ft.name,
                                        "current_value": current_val,
                                        "proposed_value": item,
                                        "changes": changes,
                                        "text": str(text_repr)[:500],
                                        "confidence": item.get("confidence", 0.7),
                                    }
                                )
                        elif item_hash not in existing_hashes:
                            # This is a new facet
                            new_facets.append(
                                {
                                    "facet_type": ft_slug,
                                    "facet_type_name": ft.name,
                                    "value": item,
                                    "text": str(text_repr)[:500],
                                    "confidence": item.get("confidence", 0.7),
                                    "ai_model": settings.azure_openai_deployment_name,
                                }
                            )

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
                ai_task.completed_at = datetime.now(UTC)
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
        collected_data: dict[str, Any],
        existing_facets: list[dict[str, Any]],
        facet_types: list["FacetType"],
        entity_name: str,
    ) -> dict[str, Any]:
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
                context_parts.append(f"{direction} {rel_name}: {target.get('name', 'Unbekannt')}")
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
                existing_context += (
                    f"- {ef.get('facet_type_name', ef.get('facet_type', ''))}: {ef.get('text', '')[:100]}\n"
                )

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

        start_time = time.time()

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

            # Track LLM usage
            if response.usage:
                await record_llm_usage(
                    provider=LLMProvider.AZURE_OPENAI,
                    model=settings.azure_openai_deployment_name,
                    task_type=LLMTaskType.ENTITY_ANALYSIS,
                    task_name="entity_data_ai_analysis",
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                    duration_ms=int((time.time() - start_time) * 1000),
                    is_error=False,
                )

            result = json.loads(response.choices[0].message.content)
            return result

        except json.JSONDecodeError as e:
            logger.error("Failed to parse AI response", error=str(e))
            raise RuntimeError("KI-Service Fehler: AI-Antwort konnte nicht verarbeitet werden") from None
        except Exception as e:
            # Track error
            await record_llm_usage(
                provider=LLMProvider.AZURE_OPENAI,
                model=settings.azure_openai_deployment_name,
                task_type=LLMTaskType.ENTITY_ANALYSIS,
                task_name="entity_data_ai_analysis",
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                duration_ms=int((time.time() - start_time) * 1000),
                is_error=True,
                error_message=str(e),
            )
            logger.exception("AI analysis failed")
            raise RuntimeError(f"KI-Service nicht erreichbar: {str(e)}") from None

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
        run_async(_analyze_attachment_async(attachment_id, task_id, extract_facets))

    async def _analyze_attachment_async(
        attachment_id: str,
        task_id: str,
        extract_facets: bool,
    ):
        """Async implementation of attachment analysis."""
        from sqlalchemy import select

        from app.database import get_celery_session_context
        from app.models import AITask, AITaskStatus, Entity, FacetType
        from app.models.entity_attachment import AttachmentAnalysisStatus, EntityAttachment

        async with get_celery_session_context() as session:
            # Helper to mark task as failed
            async def fail_task(error_msg: str):
                ai_task = await session.get(AITask, UUID(task_id))
                if ai_task:
                    ai_task.status = AITaskStatus.FAILED
                    ai_task.error_message = error_msg
                    ai_task.completed_at = datetime.now(UTC)
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
                attachment.analyzed_at = datetime.now(UTC)
                attachment.ai_model_used = analysis_result.get("ai_model_used")

                # 7. Update task as completed
                if ai_task:
                    ai_task.status = AITaskStatus.COMPLETED
                    ai_task.completed_at = datetime.now(UTC)
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
                    },
                )

            except SoftTimeLimitExceeded:
                logger.warning("Attachment analysis timed out", attachment_id=attachment_id)
                await fail_task("Analyse-Timeout ueberschritten")

            except Exception as e:
                logger.exception("Attachment analysis failed", attachment_id=attachment_id)
                await fail_task(f"Analyse fehlgeschlagen: {str(e)}")

    # Return task references
    return (
        analyze_entity_data_for_facets,
        analyze_attachment_task,
    )
