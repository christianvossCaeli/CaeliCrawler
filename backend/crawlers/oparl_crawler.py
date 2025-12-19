"""OParl API Crawler for German municipal council information systems."""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
import structlog

from crawlers.base import BaseCrawler, CrawlResult
from app.config import settings

logger = structlog.get_logger()


class OparlCrawler(BaseCrawler):
    """
    Crawler for OParl-compliant APIs.

    OParl is a German standard for accessing municipal council information systems.
    See: https://oparl.org/
    """

    def __init__(self):
        super().__init__()
        self.client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if not self.client:
            self.client = httpx.AsyncClient(
                timeout=60,
                headers={
                    "User-Agent": settings.crawler_user_agent,
                    "Accept": "application/json",
                },
                follow_redirects=True,
            )
        return self.client

    async def crawl(self, source, job) -> CrawlResult:
        """Crawl an OParl API endpoint."""
        from app.database import get_session_context
        from app.models import Document, ProcessingStatus

        result = CrawlResult()
        client = await self._get_client()

        try:
            # Get the OParl system endpoint
            endpoint = source.api_endpoint or source.base_url
            self.logger.info("Starting OParl crawl", endpoint=endpoint)

            # Fetch system info
            system_data = await self._fetch_json(client, endpoint)
            if not system_data:
                result.errors.append({"error": "Failed to fetch system info"})
                return result

            result.pages_crawled += 1

            # Get bodies (Körperschaften)
            bodies_url = system_data.get("body")
            if bodies_url:
                bodies = await self._fetch_paginated(client, bodies_url)
                result.pages_crawled += 1

                for body in bodies:
                    # Extract body/municipality name for clustering
                    body_name = body.get("name") or body.get("shortName")
                    self.logger.info(
                        "Processing OParl body",
                        body_name=body_name,
                        body_id=body.get("id"),
                    )

                    # Get papers (Drucksachen) for each body
                    papers_url = body.get("paper")
                    if papers_url:
                        await self._crawl_papers(
                            client, papers_url, source, job, result, body_name
                        )

                    # Get meetings (Sitzungen)
                    meetings_url = body.get("meeting")
                    if meetings_url:
                        await self._crawl_meetings(
                            client, meetings_url, source, job, result, body_name
                        )

            result.stats = {
                "endpoint": endpoint,
                "bodies_found": len(bodies) if bodies_url else 0,
            }

        except Exception as e:
            self.logger.exception("OParl crawl failed", error=str(e))
            result.errors.append({
                "error": str(e),
                "type": type(e).__name__,
            })

        finally:
            if self.client:
                await self.client.aclose()
                self.client = None

        return result

    async def _crawl_papers(
        self,
        client: httpx.AsyncClient,
        papers_url: str,
        source,
        job,
        result: CrawlResult,
        body_name: Optional[str] = None,
    ):
        """Crawl papers (Drucksachen) from OParl API."""
        from app.database import get_celery_session_context
        from app.models import Document, ProcessingStatus

        # Add modified filter if we have a last crawl date
        if source.last_crawl:
            separator = "&" if "?" in papers_url else "?"
            papers_url = f"{papers_url}{separator}modified_since={source.last_crawl.isoformat()}"

        papers = await self._fetch_paginated(client, papers_url)
        result.pages_crawled += 1

        async with get_celery_session_context() as session:
            for paper in papers:
                result.documents_found += 1

                # Extract files from paper
                files = paper.get("auxiliaryFile", []) + [paper.get("mainFile")]
                files = [f for f in files if f]  # Remove None

                for file_data in files:
                    if not file_data:
                        continue

                    file_url = file_data.get("accessUrl") or file_data.get("downloadUrl")
                    if not file_url:
                        continue

                    # Determine document type
                    mime_type = file_data.get("mimeType", "")
                    if "pdf" in mime_type.lower():
                        doc_type = "PDF"
                    elif "html" in mime_type.lower():
                        doc_type = "HTML"
                    else:
                        doc_type = mime_type.split("/")[-1].upper() or "UNKNOWN"

                    # Create document hash from URL
                    file_hash = self.compute_text_hash(file_url)

                    # Check if document already exists
                    from sqlalchemy import select
                    existing = await session.execute(
                        select(Document).where(
                            Document.source_id == source.id,
                            Document.file_hash == file_hash,
                        )
                    )
                    if existing.scalar():
                        continue  # Skip existing

                    # Create document title including municipality for clustering
                    base_title = file_data.get("name") or paper.get("name") or "Dokument"
                    if body_name:
                        title = f"[{body_name}] {base_title}"
                    else:
                        title = base_title

                    # Create new document
                    doc = Document(
                        source_id=source.id,
                        category_id=source.category_id,
                        crawl_job_id=job.id,
                        document_type=doc_type,
                        original_url=file_url,
                        title=title,
                        file_hash=file_hash,
                        processing_status=ProcessingStatus.PENDING,
                    )

                    # Try to extract date
                    date_str = paper.get("date") or paper.get("modified")
                    if date_str:
                        try:
                            doc.document_date = datetime.fromisoformat(
                                date_str.replace("Z", "+00:00")
                            )
                        except ValueError:
                            pass

                    session.add(doc)
                    result.documents_new += 1
                    result.documents_processed += 1

            await session.commit()

    async def _crawl_meetings(
        self,
        client: httpx.AsyncClient,
        meetings_url: str,
        source,
        job,
        result: CrawlResult,
        body_name: Optional[str] = None,
    ):
        """Crawl meetings (Sitzungen) from OParl API."""
        from app.database import get_celery_session_context
        from app.models import Document, ProcessingStatus
        from sqlalchemy import select

        # Add modified filter if we have a last crawl date
        if source.last_crawl:
            separator = "&" if "?" in meetings_url else "?"
            meetings_url = f"{meetings_url}{separator}modified_since={source.last_crawl.isoformat()}"

        meetings = await self._fetch_paginated(client, meetings_url, max_pages=5)
        result.pages_crawled += 1

        async with get_celery_session_context() as session:
            # Process meeting agenda items and their files
            for meeting in meetings:
                meeting_name = meeting.get("name", "Sitzung")
                meeting_date = meeting.get("start") or meeting.get("date")

                agenda_items = meeting.get("agendaItem", [])
                for item in agenda_items:
                    files = item.get("auxiliaryFile", [])
                    result.documents_found += len(files)

                    for file_data in files:
                        if not file_data:
                            continue

                        file_url = file_data.get("accessUrl") or file_data.get("downloadUrl")
                        if not file_url:
                            continue

                        # Create hash
                        file_hash = self.compute_text_hash(file_url)

                        # Check if exists
                        existing = await session.execute(
                            select(Document).where(
                                Document.source_id == source.id,
                                Document.file_hash == file_hash,
                            )
                        )
                        if existing.scalar():
                            continue

                        # Create title with municipality
                        base_title = file_data.get("name") or item.get("name") or meeting_name
                        if body_name:
                            title = f"[{body_name}] {base_title}"
                        else:
                            title = base_title

                        # Determine document type
                        mime_type = file_data.get("mimeType", "")
                        if "pdf" in mime_type.lower():
                            doc_type = "PDF"
                        else:
                            doc_type = "HTML"

                        doc = Document(
                            source_id=source.id,
                            category_id=source.category_id,
                            crawl_job_id=job.id,
                            document_type=doc_type,
                            original_url=file_url,
                            title=title,
                            file_hash=file_hash,
                            processing_status=ProcessingStatus.PENDING,
                        )

                        if meeting_date:
                            try:
                                doc.document_date = datetime.fromisoformat(
                                    meeting_date.replace("Z", "+00:00")
                                )
                            except ValueError:
                                pass

                        session.add(doc)
                        result.documents_new += 1
                        result.documents_processed += 1

            await session.commit()

    async def _fetch_json(
        self,
        client: httpx.AsyncClient,
        url: str,
    ) -> Optional[Dict[str, Any]]:
        """Fetch JSON from URL."""
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error("Failed to fetch JSON", url=url, error=str(e))
            return None

    async def _fetch_paginated(
        self,
        client: httpx.AsyncClient,
        url: str,
        max_pages: int = 10,
    ) -> List[Dict[str, Any]]:
        """Fetch paginated OParl data."""
        items = []
        current_url = url
        pages_fetched = 0

        while current_url and pages_fetched < max_pages:
            data = await self._fetch_json(client, current_url)
            if not data:
                break

            # OParl uses "data" key for items
            if "data" in data:
                items.extend(data["data"])
            elif isinstance(data, list):
                items.extend(data)

            # Get next page URL
            links = data.get("links", {})
            current_url = links.get("next")
            pages_fetched += 1

            # Rate limiting
            await asyncio.sleep(settings.crawler_default_delay)

        return items

    async def detect_changes(self, source) -> bool:
        """Detect changes by checking modified timestamps."""
        client = await self._get_client()

        try:
            endpoint = source.api_endpoint or source.base_url

            # OParl supports modified_since parameter
            if source.last_crawl:
                separator = "&" if "?" in endpoint else "?"
                check_url = f"{endpoint}{separator}modified_since={source.last_crawl.isoformat()}"

                data = await self._fetch_json(client, check_url)
                if data and data.get("data"):
                    return True  # Changes detected

            return False

        finally:
            if self.client:
                await self.client.aclose()
                self.client = None
