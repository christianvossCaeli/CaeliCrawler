"""PySis processing tasks.

This module contains Celery tasks for processing PySis fields and converting
them to the Entity-Facet system. It handles:
- Extracting PySis field values using AI
- Converting ExtractedData to FacetValues
- Analyzing PySis fields for facets
- Enriching FacetValues from PySis data
"""

import json
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

import structlog

from app.models.llm_usage import LLMProvider, LLMTaskType
from services.llm_usage_tracker import record_llm_usage
from workers.async_runner import run_async

from .common import (
    AI_EXTRACTION_MAX_TOKENS,
    AI_EXTRACTION_TEMPERATURE,
    PYSIS_BASE_CONFIDENCE,
    PYSIS_CONFIDENCE_BOOST,
    PYSIS_DUPLICATE_SIMILARITY_THRESHOLD,
    PYSIS_MAX_CONFIDENCE,
    PYSIS_MAX_CONTEXT_LENGTH,
    PYSIS_MIN_DEDUP_TEXT_LENGTH,
    PYSIS_MIN_TEXT_LENGTH,
    PYSIS_SUMMARY_MAX_LENGTH,
    PYSIS_TEXT_REPR_MAX_LENGTH,
)

if TYPE_CHECKING:
    from openai import AsyncAzureOpenAI
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.entity import Entity
    from app.models.facet_type import FacetType
    from app.models.pysis import PySisProcess, PySisProcessField

logger = structlog.get_logger()


# =============================================================================
# Celery Task Registration
# =============================================================================


def register_tasks(celery_app):
    """Register all PySis processor tasks with the Celery app."""

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
    def extract_pysis_fields(self, process_id: str, field_ids: list[str] | None = None):
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
        run_async(_extract_pysis_fields_async(process_id, field_ids, self.request.id))

    async def _extract_pysis_fields_async(
        process_id: str, field_ids: list[str] | None, celery_task_id: str | None = None
    ):
        """Async implementation of PySis field extraction."""
        from sqlalchemy import select

        from app.database import get_celery_session_context
        from app.models import AITask, AITaskStatus, AITaskType, ExtractedData
        from app.models.pysis import PySisProcess, PySisProcessField

        async with get_celery_session_context() as session:
            # Load process
            process = await session.get(PySisProcess, UUID(process_id))
            if not process:
                logger.error("PySis process not found", process_id=process_id)
                return

            # Get fields to extract
            query = select(PySisProcessField).where(
                PySisProcessField.process_id == process.id, PySisProcessField.ai_extraction_enabled.is_(True)
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
                started_at=datetime.now(UTC),
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
                .where(ExtractedData.extracted_content["municipality"].astext.ilike(f"%{process.entity_name}%"))
                .where(ExtractedData.confidence_score >= 0.5)
                .order_by(ExtractedData.created_at.desc())
                .limit(30)
            )
            extractions = ext_result.scalars().all()

            if not extractions:
                # Try broader search using source_location
                ext_result = await session.execute(
                    select(ExtractedData)
                    .where(ExtractedData.extracted_content["source_location"].astext.ilike(f"%{process.entity_name}%"))
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
                        session, field, context_text, process.entity_name
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
                ai_task.completed_at = datetime.now(UTC)
                ai_task.progress_current = len(fields)
                ai_task.current_item = None
                ai_task.fields_extracted = fields_extracted
                ai_task.avg_confidence = (total_confidence / fields_extracted) if fields_extracted > 0 else None
                if error_count > 0:
                    ai_task.error_message = f"{error_count} Feld(er) konnten nicht extrahiert werden"

            await session.commit()
            logger.info("PySis field extraction completed", process_id=process_id, fields_extracted=fields_extracted)

    async def _extract_single_pysis_field(
        session, field: "PySisProcessField", context: str, location_name: str
    ) -> tuple[str, float]:
        """
        Extract a single PySis field value using AI.

        Args:
            session: Database session for loading LLM credentials

        Returns:
            Tuple of (extracted_value, confidence_score)

        Raises:
            ValueError: If LLM credentials are not configured
            RuntimeError: If AI extraction fails
        """
        from app.models.user_api_credentials import LLMPurpose
        from services.llm_client_service import LLMClientService

        llm_service = LLMClientService(session)
        client, config = await llm_service.get_system_client(LLMPurpose.DOCUMENT_ANALYSIS)

        if not client or not config:
            raise ValueError(
                "Keine LLM-Credentials konfiguriert. "
                "Bitte konfigurieren Sie die API-Zugangsdaten unter /admin/api-credentials."
            )

        model_name = llm_service.get_model_name(config)

        # Build extraction prompt
        custom_prompt = field.ai_extraction_prompt or ""
        extraction_instruction = custom_prompt or f"Extrahiere Informationen zu: {field.internal_name}"

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
            start_time = time.time()
            response = await client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Analysiere die folgenden Dokumente der Gemeinde {location_name}:\n\n{context}",
                    },
                ],
                temperature=0.2,
                max_tokens=2000,
                response_format={"type": "json_object"},
            )

            if response.usage:
                await record_llm_usage(
                    provider=LLMProvider.AZURE_OPENAI,
                    model=model_name,
                    task_type=LLMTaskType.EXTRACT,
                    task_name="_extract_single_pysis_field",
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                    duration_ms=int((time.time() - start_time) * 1000),
                    is_error=False,
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
            raise RuntimeError(f"KI-Service Fehler: AI-Antwort konnte nicht verarbeitet werden - {str(e)}") from None
        except Exception as e:
            logger.exception("Azure OpenAI API call failed for PySis field extraction")
            await record_llm_usage(
                provider=LLMProvider.AZURE_OPENAI,
                model=model_name,
                task_type=LLMTaskType.EXTRACT,
                task_name="_extract_single_pysis_field",
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                duration_ms=0,
                is_error=True,
            )
            raise RuntimeError(f"KI-Service nicht erreichbar: {str(e)}") from None

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
        run_async(_convert_extractions_async(min_confidence, batch_size, entity_type_slug))

    async def _convert_extractions_async(
        min_confidence: float,
        batch_size: int,
        entity_type_slug: str,
    ):
        """Async implementation of extraction to facet conversion."""
        from sqlalchemy import func, select

        from app.database import get_celery_session_context
        from app.models import DataSource, ExtractedData
        from services.entity_facet_service import convert_extraction_to_facets

        async with get_celery_session_context() as session:
            # Count total extractions to process
            count_result = await session.execute(
                select(func.count(ExtractedData.id)).where(ExtractedData.confidence_score >= min_confidence)
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
                            content.get("municipality") or content.get("source_location")
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
        existing_task_id: str | None = None,
    ):
        """
        Analyze PySis fields and create FacetValues.

        Args:
            process_id: UUID of the PySis process
            include_empty: Include empty fields in analysis
            min_confidence: Minimum field confidence
            existing_task_id: Existing AITask ID (to avoid duplicate creation)
        """
        run_async(
            _analyze_pysis_for_facets_async(
                process_id,
                include_empty,
                min_confidence,
                self.request.id,
                existing_task_id,
            )
        )

    async def _analyze_pysis_for_facets_async(
        process_id: str,
        include_empty: bool,
        min_confidence: float,
        celery_task_id: str | None = None,
        existing_task_id: str | None = None,
    ):
        """Async implementation of PySis-to-Facets analysis."""
        from sqlalchemy import select

        from app.database import get_celery_session_context
        from app.models import AITask, AITaskStatus, AITaskType, Entity, FacetType
        from app.models.pysis import PySisProcess

        async with get_celery_session_context() as session:
            # Helper to mark task as failed if it exists
            async def fail_task_if_exists(error_msg: str):
                if existing_task_id:
                    task = await session.get(AITask, UUID(existing_task_id))
                    if task:
                        task.status = AITaskStatus.FAILED
                        task.error_message = error_msg
                        task.completed_at = datetime.now(UTC)
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
                    ai_task.description = (
                        f"Extrahiere {len(facet_types)} Facet-Typen aus {len(process.fields)} PySis-Feldern"
                    )
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
                    started_at=datetime.now(UTC),
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

                field_data.append(
                    {
                        "name": field.internal_name,
                        "pysis_name": field.pysis_field_name,
                        "value": value,
                        "source": field.value_source.value if field.value_source else "UNKNOWN",
                        "confidence": field.confidence_score,
                    }
                )

            if not field_data:
                ai_task.status = AITaskStatus.COMPLETED
                ai_task.completed_at = datetime.now(UTC)
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
                    session,
                    field_data,
                    entity.name,
                    facet_types,
                )
            except Exception as e:
                ai_task = await session.get(AITask, task_id)
                ai_task.status = AITaskStatus.FAILED
                ai_task.error_message = str(e)
                ai_task.completed_at = datetime.now(UTC)
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
            ai_task.completed_at = datetime.now(UTC)
            ai_task.fields_extracted = sum(facet_counts.values())
            await session.commit()

            logger.info(
                "PySis to facets analysis completed",
                process_id=process_id,
                entity_name=entity.name,
                facet_counts=facet_counts,
            )

    async def _extract_facets_from_pysis_fields_dynamic(
        session,
        fields: list[dict[str, Any]],
        entity_name: str,
        facet_types: list["FacetType"],
    ) -> dict[str, Any]:
        """
        Extract facets from PySis field values using AI with dynamic FacetTypes.

        Args:
            session: Database session for loading LLM credentials
            fields: List of PySis field data
            entity_name: Name of the entity (e.g., municipality)
            facet_types: List of FacetType objects to extract

        Returns:
            Dict with slug as key and list of extracted items as value
        """
        from app.models.user_api_credentials import LLMPurpose
        from services.llm_client_service import LLMClientService

        llm_service = LLMClientService(session)
        client, config = await llm_service.get_system_client(LLMPurpose.DOCUMENT_ANALYSIS)

        if not client or not config:
            raise ValueError(
                "Keine LLM-Credentials konfiguriert. "
                "Bitte konfigurieren Sie die API-Zugangsdaten unter /admin/api-credentials."
            )

        model_name = llm_service.get_model_name(config)

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

            facet_descriptions.append(f"{idx}. {ft.name.upper()} (slug: {ft.slug})\n   {instruction}{schema_desc}")

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
            start_time = time.time()
            response = await client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": fields_text},
                ],
                temperature=AI_EXTRACTION_TEMPERATURE,
                max_tokens=AI_EXTRACTION_MAX_TOKENS,
                response_format={"type": "json_object"},
            )

            if response.usage:
                await record_llm_usage(
                    provider=LLMProvider.AZURE_OPENAI,
                    model=model_name,
                    task_type=LLMTaskType.EXTRACT,
                    task_name="_extract_facets_from_pysis_fields_dynamic",
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                    duration_ms=int((time.time() - start_time) * 1000),
                    is_error=False,
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
            raise RuntimeError(f"KI-Service Fehler: AI-Antwort konnte nicht verarbeitet werden - {str(e)}") from None
        except RuntimeError:
            raise  # Re-raise our own RuntimeErrors
        except Exception as e:
            logger.exception("Azure OpenAI API call failed for PySis facet extraction")
            await record_llm_usage(
                provider=LLMProvider.AZURE_OPENAI,
                model=model_name,
                task_type=LLMTaskType.EXTRACT,
                task_name="_extract_facets_from_pysis_fields_dynamic",
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                duration_ms=0,
                is_error=True,
            )
            raise RuntimeError(f"KI-Service nicht erreichbar: {str(e)}") from None

    def _build_pysis_source_metadata(
        item_source_fields: list[str],
        pysis_fields_dict: dict[str, Any],
    ) -> dict[str, Any]:
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
        source_field_values = {field: value for field in item_source_fields if (value := pysis_fields_dict.get(field))}
        if source_field_values:
            metadata["pysis_fields"] = source_field_values

        return metadata

    async def _create_facets_from_pysis_extraction_dynamic(
        session: "AsyncSession",
        entity: "Entity",
        extractions: dict[str, Any],
        facet_types: list["FacetType"],
        task_id: UUID,
        process: Optional["PySisProcess"] = None,
        field_data: list[dict[str, Any]] | None = None,
    ) -> dict[str, int]:
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
            check_facet_value_quality,
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
                if (key := (f.get("pysis_name") or f.get("name"))) and (value := f.get("value"))
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
                    # Quality check before creating facet value
                    quality = check_facet_value_quality(text_content, ft.slug, base_confidence)
                    if not quality.is_valid:
                        logger.debug(
                            "PySiS facet rejected by quality check",
                            facet_type=ft.slug,
                            reason=quality.rejection_reason,
                        )
                        continue

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
                        confidence_score=quality.adjusted_confidence,
                        source_type=FacetValueSourceType.PYSIS,
                        facet_type=ft,  # Pass FacetType for entity reference resolution
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
                        dedup_parts = [str(val) for f in ft.deduplication_fields if (val := item.get(f))]
                        if dedup_parts:
                            dedup_text = " ".join(dedup_parts)

                    # Quality check before other validations
                    quality = check_facet_value_quality(item, ft.slug, base_confidence)
                    if not quality.is_valid:
                        logger.debug(
                            "PySiS facet item rejected by quality check",
                            facet_type=ft.slug,
                            reason=quality.rejection_reason,
                        )
                        continue

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
                    value_with_metadata = {k: v for k, v in item.items() if k != "source_fields"}
                    value_with_metadata.update(pysis_base_metadata)
                    value_with_metadata.update(_build_pysis_source_metadata(item_source_fields, pysis_fields_dict))

                    # Apply adjusted confidence from quality check with PySiS boost
                    final_confidence = min(PYSIS_MAX_CONFIDENCE, quality.adjusted_confidence + PYSIS_CONFIDENCE_BOOST)

                    await create_facet_value(
                        session,
                        entity_id=entity.id,
                        facet_type_id=ft.id,
                        value=value_with_metadata,
                        text_representation=text_repr[:PYSIS_TEXT_REPR_MAX_LENGTH],
                        confidence_score=final_confidence,
                        source_type=FacetValueSourceType.PYSIS,
                        facet_type=ft,  # Pass FacetType for entity reference resolution
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
        facet_type_id: str | None = None,
        overwrite_existing: bool = False,
        existing_task_id: str | None = None,
    ):
        """
        Enrich existing FacetValues with data from PySis fields.

        Args:
            entity_id: UUID of the entity
            facet_type_id: Optional - only enrich this FacetType
            overwrite_existing: Replace existing field values
            existing_task_id: Existing AITask ID (to avoid duplicate creation)
        """
        run_async(
            _enrich_facet_values_from_pysis_async(
                entity_id,
                facet_type_id,
                overwrite_existing,
                self.request.id,
                existing_task_id,
            )
        )

    async def _enrich_facet_values_from_pysis_async(
        entity_id: str,
        facet_type_id: str | None,
        overwrite_existing: bool,
        celery_task_id: str | None = None,
        existing_task_id: str | None = None,
    ):
        """Async implementation of FacetValue enrichment from PySis."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        from app.database import get_celery_session_context
        from app.models import AITask, AITaskStatus, AITaskType, Entity, FacetValue
        from app.models.pysis import PySisProcess

        async with get_celery_session_context() as session:
            # Helper to mark task as failed if it exists
            async def fail_task_if_exists(error_msg: str):
                if existing_task_id:
                    task = await session.get(AITask, UUID(existing_task_id))
                    if task:
                        task.status = AITaskStatus.FAILED
                        task.error_message = error_msg
                        task.completed_at = datetime.now(UTC)
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
                        pysis_fields.append(
                            {
                                "name": field.internal_name,
                                "pysis_name": field.pysis_field_name,
                                "value": value,
                                "confidence": field.confidence_score,
                            }
                        )

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
                    started_at=datetime.now(UTC),
                    progress_total=len(facet_values),
                    celery_task_id=celery_task_id,
                )
                session.add(ai_task)
                await session.commit()
                await session.refresh(ai_task)

            task_id = ai_task.id

            # 5. Initialize LLM client
            from app.models.user_api_credentials import LLMPurpose
            from services.llm_client_service import LLMClientService

            try:
                llm_service = LLMClientService(session)
                client, config = await llm_service.get_system_client(LLMPurpose.DOCUMENT_ANALYSIS)

                if not client or not config:
                    raise ValueError(
                        "Keine LLM-Credentials konfiguriert. "
                        "Bitte konfigurieren Sie die API-Zugangsdaten unter /admin/api-credentials."
                    )

                model_name = llm_service.get_model_name(config)
            except ValueError as e:
                ai_task.status = AITaskStatus.FAILED
                ai_task.error_message = str(e)
                ai_task.completed_at = datetime.now(UTC)
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
                        model_name,
                        fv.value or {},
                        facet_type.value_schema,
                        pysis_fields,
                        entity.name,
                        overwrite_existing,
                    )

                    if enriched_value and enriched_value != fv.value:
                        fv.value = enriched_value
                        fv.updated_at = datetime.now(UTC)
                        fv.ai_model_used = model_name

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
                    logger.error("Failed to enrich FacetValue", facet_value_id=str(fv.id), error=str(e))

            # 7. Complete task
            ai_task = await session.get(AITask, task_id)
            ai_task.status = AITaskStatus.COMPLETED
            ai_task.completed_at = datetime.now(UTC)
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
        model_name: str,
        current_value: dict[str, Any],
        value_schema: dict[str, Any],
        pysis_fields: list[dict[str, Any]],
        entity_name: str,
        overwrite_existing: bool,
    ) -> dict[str, Any] | None:
        """
        Enrich a single FacetValue using AI.

        Args:
            client: Azure OpenAI client
            model_name: Model deployment name
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

            missing_fields.append(
                {
                    "name": field_name,
                    "type": field_def.get("type", "string"),
                    "description": field_def.get("description", ""),
                }
            )

        if not missing_fields:
            return None

        # Build prompt
        pysis_text = "\n".join(
            [
                f"- {f['name']}: {f['value']}"
                for f in pysis_fields[:30]  # Limit context
            ]
        )

        missing_fields_text = "\n".join([f"- {f['name']} ({f['type']}): {f['description']}" for f in missing_fields])

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
            start_time = time.time()
            response = await client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "Du extrahierst strukturierte Daten aus Textfeldern. Antworte nur mit JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=1000,
                response_format={"type": "json_object"},
            )

            if response.usage:
                await record_llm_usage(
                    provider=LLMProvider.AZURE_OPENAI,
                    model=model_name,
                    task_type=LLMTaskType.EXTRACT,
                    task_name="_enrich_single_facet_value",
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                    duration_ms=int((time.time() - start_time) * 1000),
                    is_error=False,
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
            await record_llm_usage(
                provider=LLMProvider.AZURE_OPENAI,
                model=model_name,
                task_type=LLMTaskType.EXTRACT,
                task_name="_enrich_single_facet_value",
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                duration_ms=0,
                is_error=True,
            )
            return None

    # Return task references
    return (
        extract_pysis_fields,
        convert_extractions_to_facets,
        analyze_pysis_fields_for_facets,
        enrich_facet_values_from_pysis,
    )
