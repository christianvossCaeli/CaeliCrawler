"""Service for AI-based analysis of entity attachments."""

import base64
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import AITask, AITaskStatus, AITaskType, Entity, FacetType
from app.models.entity_attachment import AttachmentAnalysisStatus, EntityAttachment
from app.models.llm_usage import LLMTaskType
from app.models.user_api_credentials import LLMPurpose
from services.llm_client_service import LLMClientService
from services.llm_usage_tracker import record_llm_usage

logger = structlog.get_logger()


class AttachmentAnalysisService:
    """Service for analyzing attachments with AI (Vision API for images, text extraction for PDFs)."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.storage_path = Path(settings.attachment_storage_path)

    async def analyze_attachment(
        self,
        attachment_id: UUID,
        extract_facets: bool = True,
    ) -> AITask:
        """
        Start AI analysis for an attachment.

        Creates an AITask and triggers a Celery background task.

        Args:
            attachment_id: UUID of the attachment to analyze
            extract_facets: Whether to extract facet suggestions

        Returns:
            AITask for tracking progress

        Raises:
            ValueError: If attachment not found or already analyzed
        """
        # Load attachment with entity
        attachment = await self.db.get(EntityAttachment, attachment_id)
        if not attachment:
            raise ValueError(f"Attachment nicht gefunden: {attachment_id}")

        # Check if already analyzing
        if attachment.analysis_status == AttachmentAnalysisStatus.ANALYZING:
            raise ValueError("Analyse laeuft bereits")

        # Load entity for context
        entity = await self.db.get(Entity, attachment.entity_id)
        if not entity:
            raise ValueError(f"Entity nicht gefunden: {attachment.entity_id}")

        # Create AITask for tracking
        ai_task = AITask(
            task_type=AITaskType.ATTACHMENT_ANALYSIS,
            status=AITaskStatus.PENDING,
            name=f"Attachment-Analyse: {attachment.filename}",
            description=f"Analysiere {attachment.content_type} fuer Entity '{entity.name}'",
            started_at=datetime.now(UTC),
            progress_total=3,  # 1: Load, 2: Analyze, 3: Extract facets
            result_data={
                "attachment_id": str(attachment_id),
                "entity_id": str(entity.id),
                "entity_name": entity.name,
                "filename": attachment.filename,
                "content_type": attachment.content_type,
                "extract_facets": extract_facets,
            },
        )
        self.db.add(ai_task)

        # Update attachment status
        attachment.analysis_status = AttachmentAnalysisStatus.ANALYZING

        await self.db.commit()
        await self.db.refresh(ai_task)

        # Trigger Celery task
        from workers.ai_tasks import analyze_attachment_task

        analyze_attachment_task.delay(
            attachment_id=str(attachment_id),
            task_id=str(ai_task.id),
            extract_facets=extract_facets,
        )

        logger.info(
            "Attachment analysis started",
            attachment_id=str(attachment_id),
            task_id=str(ai_task.id),
            filename=attachment.filename,
        )

        return ai_task

    async def get_analysis_status(self, attachment_id: UUID) -> dict[str, Any]:
        """Get current analysis status for an attachment."""
        attachment = await self.db.get(EntityAttachment, attachment_id)
        if not attachment:
            raise ValueError(f"Attachment nicht gefunden: {attachment_id}")

        return {
            "attachment_id": str(attachment_id),
            "status": attachment.analysis_status.value,
            "result": attachment.analysis_result,
            "error": attachment.analysis_error,
            "analyzed_at": attachment.analyzed_at.isoformat() if attachment.analyzed_at else None,
            "ai_model": attachment.ai_model_used,
        }


async def analyze_image_with_vision(
    session: AsyncSession,
    image_path: Path,
    entity_name: str,
    facet_types: list[FacetType],
) -> dict[str, Any]:
    """
    Analyze an image using Vision API.

    Args:
        session: Database session for LLM credentials
        image_path: Path to the image file
        entity_name: Name of the entity (for context)
        facet_types: Available facet types for extraction

    Returns:
        Analysis result dict with description, detected text, entities, facet suggestions
    """
    llm_service = LLMClientService(session)
    client, config = await llm_service.get_system_client(LLMPurpose.DOCUMENT_ANALYSIS)
    if not client or not config:
        raise ValueError("LLM nicht konfiguriert für Bildanalyse")

    model_name = llm_service.get_model_name(config)
    provider = llm_service.get_provider(config)

    # Read and encode image
    image_bytes = image_path.read_bytes()
    base64_image = base64.b64encode(image_bytes).decode("utf-8")

    # Determine media type
    suffix = image_path.suffix.lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    media_type = media_types.get(suffix, "image/jpeg")

    # Build facet extraction prompt
    facet_prompts = []
    for ft in facet_types:
        if ft.ai_extraction_prompt:
            facet_prompts.append(f"- {ft.name}: {ft.ai_extraction_prompt}")
        else:
            facet_prompts.append(f"- {ft.name}: {ft.description or 'Relevante Informationen'}")

    facet_list = "\n".join(facet_prompts) if facet_prompts else "Keine spezifischen Facet-Typen definiert"

    system_prompt = f"""Du bist ein Experte fuer die Analyse von Bildern im Kontext von Projektdokumentation.

AUFGABE:
Analysiere das Bild und extrahiere relevante Informationen fuer die Entity "{entity_name}".

ZU EXTRAHIERENDE INFORMATIONEN:
1. Beschreibung: Eine detaillierte Beschreibung des Bildinhalts
2. Erkannter Text: Alle im Bild sichtbaren Texte (OCR)
3. Entitaeten: Personen, Organisationen, Orte, Daten die erkannt werden
4. Facet-Vorschlaege basierend auf folgenden Typen:
{facet_list}

ANTWORTFORMAT (JSON):
{{
  "description": "Detaillierte Beschreibung des Bildinhalts",
  "detected_text": ["Text 1", "Text 2", ...],
  "entities": {{
    "persons": ["Name 1", ...],
    "organizations": ["Org 1", ...],
    "locations": ["Ort 1", ...],
    "dates": ["Datum 1", ...]
  }},
  "facet_suggestions": [
    {{
      "facet_type_slug": "slug",
      "value": {{"text": "...", "type": "..."}},
      "confidence": 0.8,
      "source_text": "Relevanter Bildausschnitt/Text"
    }}
  ],
  "image_type": "Foto/Karte/Diagramm/Screenshot/etc.",
  "quality_notes": "Notizen zur Bildqualitaet"
}}
"""

    start_time = time.time()
    try:
        response = await client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{base64_image}",
                                "detail": "high",
                            },
                        },
                        {
                            "type": "text",
                            "text": f"Analysiere dieses Bild fuer die Entity '{entity_name}'.",
                        },
                    ],
                },
            ],
            temperature=0.2,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )

        if response.usage:
            await record_llm_usage(
                provider=provider,
                model=model_name,
                task_type=LLMTaskType.ATTACHMENT_ANALYSIS,
                task_name="analyze_image_with_vision",
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                duration_ms=int((time.time() - start_time) * 1000),
                is_error=False,
            )
    except Exception:
        await record_llm_usage(
            provider=provider,
            model=model_name,
            task_type=LLMTaskType.ATTACHMENT_ANALYSIS,
            task_name="analyze_image_with_vision",
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            duration_ms=int((time.time() - start_time) * 1000),
            is_error=True,
        )
        raise

    import json

    result = json.loads(response.choices[0].message.content)
    result["ai_model_used"] = model_name
    result["tokens_used"] = response.usage.total_tokens if response.usage else None

    return result


async def analyze_pdf_with_ai(
    session: AsyncSession,
    pdf_path: Path,
    entity_name: str,
    facet_types: list[FacetType],
) -> dict[str, Any]:
    """
    Analyze a PDF by extracting text and analyzing with AI.

    Args:
        session: Database session for LLM credentials
        pdf_path: Path to the PDF file
        entity_name: Name of the entity (for context)
        facet_types: Available facet types for extraction

    Returns:
        Analysis result dict
    """
    # Extract text from PDF
    extracted_text = await extract_pdf_text(pdf_path)

    if not extracted_text or len(extracted_text.strip()) < 50:
        return {
            "description": "PDF enthaelt keinen extrahierbaren Text",
            "detected_text": [],
            "entities": {},
            "facet_suggestions": [],
            "raw_text": extracted_text,
            "extraction_error": "Kein oder zu wenig Text extrahiert",
        }

    llm_service = LLMClientService(session)
    client, config = await llm_service.get_system_client(LLMPurpose.DOCUMENT_ANALYSIS)
    if not client or not config:
        raise ValueError("LLM nicht konfiguriert für PDF-Analyse")

    model_name = llm_service.get_model_name(config)
    provider = llm_service.get_provider(config)

    # Build facet extraction prompt
    facet_prompts = []
    for ft in facet_types:
        if ft.ai_extraction_prompt:
            facet_prompts.append(f"- {ft.name} ({ft.slug}): {ft.ai_extraction_prompt}")
        else:
            facet_prompts.append(f"- {ft.name} ({ft.slug}): {ft.description or 'Relevante Informationen'}")

    facet_list = "\n".join(facet_prompts) if facet_prompts else "Keine spezifischen Facet-Typen definiert"

    # Truncate text if too long
    max_chars = 80000
    truncated = False
    if len(extracted_text) > max_chars:
        extracted_text = extracted_text[:max_chars]
        truncated = True

    system_prompt = f"""Du bist ein Experte fuer die Analyse von PDF-Dokumenten im Kontext von Projektdokumentation.

AUFGABE:
Analysiere den extrahierten Text und extrahiere relevante Informationen fuer die Entity "{entity_name}".

ZU EXTRAHIERENDE INFORMATIONEN:
1. Zusammenfassung: Eine kurze Zusammenfassung des Dokuments (max 300 Woerter)
2. Dokumenttyp: Art des Dokuments (Beschluss, Protokoll, Bericht, etc.)
3. Entitaeten: Personen, Organisationen, Orte, Daten
4. Facet-Vorschlaege basierend auf folgenden Typen:
{facet_list}

ANTWORTFORMAT (JSON):
{{
  "description": "Zusammenfassung des Dokuments",
  "document_type": "Dokumenttyp",
  "detected_text": ["Wichtiger Textausschnitt 1", ...],
  "entities": {{
    "persons": ["Name 1", ...],
    "organizations": ["Org 1", ...],
    "locations": ["Ort 1", ...],
    "dates": ["Datum 1", ...]
  }},
  "facet_suggestions": [
    {{
      "facet_type_slug": "slug",
      "value": {{"text": "...", "type": "..."}},
      "confidence": 0.8,
      "source_text": "Relevanter Textausschnitt"
    }}
  ],
  "key_findings": ["Kernaussage 1", ...],
  "relevance_score": 0.8
}}
"""

    start_time = time.time()
    try:
        response = await client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Analysiere folgenden PDF-Text fuer die Entity '{entity_name}':\n\n{extracted_text}",
                },
            ],
            temperature=0.2,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )

        if response.usage:
            await record_llm_usage(
                provider=provider,
                model=model_name,
                task_type=LLMTaskType.ATTACHMENT_ANALYSIS,
                task_name="analyze_pdf_with_ai",
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                duration_ms=int((time.time() - start_time) * 1000),
                is_error=False,
            )
    except Exception:
        await record_llm_usage(
            provider=provider,
            model=model_name,
            task_type=LLMTaskType.ATTACHMENT_ANALYSIS,
            task_name="analyze_pdf_with_ai",
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            duration_ms=int((time.time() - start_time) * 1000),
            is_error=True,
        )
        raise

    import json

    result = json.loads(response.choices[0].message.content)
    result["ai_model_used"] = model_name
    result["tokens_used"] = response.usage.total_tokens if response.usage else None
    result["text_truncated"] = truncated
    result["original_text_length"] = len(extracted_text)

    return result


async def extract_pdf_text(pdf_path: Path) -> str:
    """
    Extract text from a PDF file using pymupdf.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Extracted text content
    """
    try:
        import fitz  # pymupdf

        text_parts = []

        with fitz.open(pdf_path) as doc:
            for page_num, page in enumerate(doc):
                text = page.get_text()
                if text.strip():
                    text_parts.append(f"--- Seite {page_num + 1} ---\n{text}")

        return "\n\n".join(text_parts)

    except ImportError:
        logger.warning("pymupdf not installed, PDF text extraction not available")
        return ""
    except Exception as e:
        logger.error("PDF text extraction failed", error=str(e), path=str(pdf_path))
        return ""


async def extract_facet_suggestions(
    analysis_result: dict[str, Any],
    entity_id: UUID,
    facet_types: list[FacetType],
    db: AsyncSession,
) -> list[dict[str, Any]]:
    """
    Extract and validate facet suggestions from analysis result.

    Args:
        analysis_result: Result from image/PDF analysis
        entity_id: Entity UUID
        facet_types: Available facet types
        db: Database session

    Returns:
        List of validated facet suggestions
    """
    suggestions = analysis_result.get("facet_suggestions", [])
    if not suggestions:
        return []

    # Build facet type lookup
    ft_by_slug = {ft.slug: ft for ft in facet_types}

    validated = []
    for suggestion in suggestions:
        slug = suggestion.get("facet_type_slug")
        if not slug or slug not in ft_by_slug:
            continue

        ft = ft_by_slug[slug]
        value = suggestion.get("value", {})
        confidence = suggestion.get("confidence", 0.5)

        # Ensure minimum confidence
        if confidence < 0.3:
            continue

        # Validate value has content
        text_repr = value.get("text") or value.get("description") or value.get("name") or str(value)

        if not text_repr or len(str(text_repr)) < 3:
            continue

        validated.append(
            {
                "facet_type_id": str(ft.id),
                "facet_type_slug": slug,
                "facet_type_name": ft.name,
                "value": value,
                "text_representation": str(text_repr)[:500],
                "confidence": confidence,
                "source_text": suggestion.get("source_text", ""),
            }
        )

    return validated
