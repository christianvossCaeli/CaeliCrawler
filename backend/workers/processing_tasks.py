"""Celery tasks for document processing."""

import hashlib
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID

import structlog
from celery.exceptions import SoftTimeLimitExceeded

from workers.celery_app import celery_app
from app.config import settings

logger = structlog.get_logger()


@celery_app.task(
    bind=True,
    name="workers.processing_tasks.process_document",
    max_retries=3,
    default_retry_delay=30,
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def process_document(self, document_id: str):
    """
    Process a single document (download, extract text).

    Args:
        document_id: UUID of the document to process
    """
    from app.database import get_celery_session_context
    from app.models import Document, ProcessingStatus
    import asyncio

    async def _process():
        async with get_celery_session_context() as session:
            document = await session.get(Document, UUID(document_id))
            if not document:
                logger.error("Document not found", document_id=document_id)
                return

            document.processing_status = ProcessingStatus.PROCESSING
            await session.commit()

            try:
                # Download if not already downloaded
                if not document.file_path or not os.path.exists(document.file_path):
                    await _download_document(document)
                    document.downloaded_at = datetime.now(timezone.utc)

                # Extract text and title based on document type
                text, title = await _extract_text_and_title(document)
                # Clean text: remove null bytes which cause PostgreSQL errors
                if text:
                    text = text.replace('\x00', '')
                document.raw_text = text

                # Set title if not already set and we extracted one
                if not document.title and title:
                    document.title = title[:255]  # Limit to field size

                # Update status
                document.processing_status = ProcessingStatus.COMPLETED
                document.processed_at = datetime.now(timezone.utc)

                logger.info(
                    "Document processed",
                    document_id=document_id,
                    type=document.document_type,
                    text_length=len(text) if text else 0,
                )

            except SoftTimeLimitExceeded:
                # Handle soft time limit - graceful shutdown
                logger.warning(
                    "Document processing soft time limit exceeded",
                    document_id=document_id,
                )
                document.processing_status = ProcessingStatus.FAILED
                document.processing_error = "Processing exceeded time limit"

            except Exception as e:
                logger.exception("Document processing failed", document_id=document_id)
                document.processing_status = ProcessingStatus.FAILED
                document.processing_error = str(e)

            await session.commit()

            # Trigger AI analysis if text was extracted
            if document.processing_status == ProcessingStatus.COMPLETED and document.raw_text:
                from workers.ai_tasks import analyze_document
                analyze_document.delay(document_id)

    asyncio.run(_process())


async def _download_document(document) -> str:
    """Download a document and return the file path."""
    import httpx

    # Create storage directory
    storage_path = Path(settings.document_storage_path)
    category_path = storage_path / str(document.category_id)
    category_path.mkdir(parents=True, exist_ok=True)

    # Generate filename
    extension = document.document_type.lower()
    filename = f"{document.id}.{extension}"
    file_path = category_path / filename

    # Download
    async with httpx.AsyncClient() as client:
        response = await client.get(
            document.original_url,
            follow_redirects=True,
            timeout=60,
            headers={"User-Agent": settings.crawler_user_agent},
        )
        response.raise_for_status()

        with open(file_path, "wb") as f:
            f.write(response.content)

    document.file_path = str(file_path)
    document.file_size = os.path.getsize(file_path)

    return str(file_path)


async def _extract_text_and_title(document) -> tuple[Optional[str], Optional[str]]:
    """Extract text and title from a document based on its type.

    Returns:
        Tuple of (text, title). Title may be None if not found.
    """
    if not document.file_path:
        return None, None

    doc_type = document.document_type.upper()

    if doc_type == "PDF":
        return await _extract_pdf_text_and_title(document.file_path)
    elif doc_type == "HTML":
        return await _extract_html_text_and_title(document.file_path)
    elif doc_type in ("DOC", "DOCX"):
        text = await _extract_docx_text(document.file_path)
        return text, None  # DOCX title extraction not implemented
    else:
        logger.warning(f"Unsupported document type: {doc_type}")
        return None, None


def _is_valid_title(text: str) -> bool:
    """Check if text is a valid title (contains enough alphanumeric chars).

    A valid title must:
    - Be at least 5 characters long
    - Contain at least 50% alphanumeric characters (including German umlauts)

    Args:
        text: The text to validate

    Returns:
        True if the text is a valid title, False otherwise
    """
    if not text or len(text) < 5:
        return False
    # Count alphanumeric characters (including German umlauts)
    alnum_count = sum(1 for c in text if c.isalnum() or c in 'äöüÄÖÜß')
    # Require at least 50% alphanumeric content
    return alnum_count / len(text) >= 0.5


# Pre-compiled regex patterns for title extraction (compiled once at module load)
_FILENAME_SEPARATOR_PATTERN = re.compile(r'[_-]+')
_UUID_HEX_PATTERN = re.compile(r'\b[a-f0-9]{8,}\b', re.IGNORECASE)


def _title_from_filename(file_path: str) -> Optional[str]:
    """Extract a readable title from the filename.

    Transforms a file path like '/path/to/my_document_abc123.pdf'
    into a readable title like 'my document'.

    Args:
        file_path: Path to the file

    Returns:
        Extracted title or None if no valid title can be extracted
    """
    filename = Path(file_path).stem  # filename without extension
    # Replace underscores and hyphens with spaces
    title = _FILENAME_SEPARATOR_PATTERN.sub(' ', filename)
    # Remove UUIDs and long hex strings
    title = _UUID_HEX_PATTERN.sub('', title)
    # Remove extra spaces and trim
    title = ' '.join(title.split())

    if _is_valid_title(title):
        return title[:200]  # Truncate to reasonable length
    return None


async def _extract_pdf_text_and_title(file_path: str) -> tuple[str, Optional[str]]:
    """Extract text and title from PDF using PyMuPDF."""
    import fitz  # PyMuPDF

    text_parts = []
    title = None

    with fitz.open(file_path) as doc:
        # Try to get title from metadata
        metadata = doc.metadata
        if metadata:
            title = metadata.get("title") or metadata.get("subject")
            if title:
                title = title.strip()
                if not _is_valid_title(title) or title.lower() in ("untitled", "microsoft word"):
                    title = None

        # Extract text from all pages
        for page in doc:
            text_parts.append(page.get_text())

        # If no title from metadata, try first line of first page
        if not title and text_parts:
            first_lines = text_parts[0].strip().split("\n")
            for line in first_lines[:3]:
                line = line.strip()
                if _is_valid_title(line) and len(line) < 200:
                    title = line
                    break

    # Last resort: try to get title from filename
    if not title:
        title = _title_from_filename(file_path)

    return "\n".join(text_parts), title


async def _extract_html_text_and_title(file_path: str) -> tuple[str, Optional[str]]:
    """Extract text and title from HTML."""
    from bs4 import BeautifulSoup

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f.read(), "lxml")

    # Extract title
    title = None
    title_tag = soup.find("title")
    if title_tag:
        title = title_tag.get_text(strip=True)
    if not title:
        h1_tag = soup.find("h1")
        if h1_tag:
            title = h1_tag.get_text(strip=True)

    # Remove script and style elements for text extraction
    for element in soup(["script", "style", "nav", "footer", "header"]):
        element.decompose()

    text = soup.get_text(separator="\n", strip=True)
    return text, title


async def _extract_docx_text(file_path: str) -> str:
    """Extract text from DOCX."""
    from docx import Document as DocxDocument

    doc = DocxDocument(file_path)
    return "\n".join(para.text for para in doc.paragraphs)


@celery_app.task(name="workers.processing_tasks.process_pending_documents")
def process_pending_documents():
    """Process all pending documents."""
    from app.database import get_celery_session_context
    from app.models import Document, ProcessingStatus
    from sqlalchemy import select
    import asyncio

    async def _process_pending():
        async with get_celery_session_context() as session:
            # Get pending documents (limit batch size)
            result = await session.execute(
                select(Document)
                .where(Document.processing_status == ProcessingStatus.PENDING)
                .limit(50)
            )
            documents = result.scalars().all()

            for doc in documents:
                # Queue processing task
                process_document.delay(str(doc.id))

            logger.info("Queued pending documents for processing", count=len(documents))

    asyncio.run(_process_pending())


@celery_app.task(name="workers.processing_tasks.reprocess_failed")
def reprocess_failed_documents():
    """Reprocess failed documents."""
    from app.database import get_celery_session_context
    from app.models import Document, ProcessingStatus
    from sqlalchemy import select, update
    import asyncio

    async def _reprocess():
        async with get_celery_session_context() as session:
            # Reset failed documents to pending
            result = await session.execute(
                update(Document)
                .where(Document.processing_status == ProcessingStatus.FAILED)
                .values(
                    processing_status=ProcessingStatus.PENDING,
                    processing_error=None,
                )
                .returning(Document.id)
            )
            document_ids = [row[0] for row in result.fetchall()]
            await session.commit()

            # Queue for processing
            for doc_id in document_ids:
                process_document.delay(str(doc_id))

            logger.info("Requeued failed documents", count=len(document_ids))

    asyncio.run(_reprocess())
