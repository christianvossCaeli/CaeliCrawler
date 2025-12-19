"""
API Crawler for specialized data sources.

Routes CUSTOM_API sources to the appropriate API client based on the
api_type configuration.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional, List
from uuid import UUID

import structlog

from crawlers.base import BaseCrawler, CrawlResult
from crawlers.api_clients.base_api import APIDocument

if TYPE_CHECKING:
    from app.models import DataSource, CrawlJob, Document
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()


class APICrawler(BaseCrawler):
    """
    Crawler for specialized API sources.

    Supports:
    - govdata: GovData.de CKAN API
    - dip_bundestag: DIP Bundestag parliamentary documents
    - fragdenstaat: FragDenStaat FOI requests
    """

    async def crawl(self, source: "DataSource", job: "CrawlJob") -> CrawlResult:
        """Crawl an API source using the appropriate client."""
        from app.database import get_celery_session_context

        crawl_config = source.crawl_config or {}
        api_type = crawl_config.get("api_type", "").lower()

        self.logger.info(
            "Starting API crawl",
            api_type=api_type,
            source_id=str(source.id),
            source_name=source.name,
        )

        result = CrawlResult()

        try:
            if api_type == "govdata":
                documents = await self._crawl_govdata(source, crawl_config)
            elif api_type == "dip_bundestag":
                documents = await self._crawl_dip_bundestag(source, crawl_config)
            elif api_type == "fragdenstaat":
                documents = await self._crawl_fragdenstaat(source, crawl_config)
            else:
                self.logger.warning(
                    "Unknown API type, falling back to generic crawl",
                    api_type=api_type,
                )
                return result

            result.pages_crawled = 1
            result.documents_found = len(documents)

            # Store documents in database
            # Use celery session context since this runs inside Celery workers
            async with get_celery_session_context() as session:
                new_count, updated_count = await self._store_documents(
                    session, source, documents
                )
                result.documents_new = new_count
                result.documents_updated = updated_count
                result.documents_processed = new_count + updated_count

        except Exception as e:
            self.logger.exception("API crawl failed", error=str(e))
            result.errors.append({
                "type": type(e).__name__,
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            })

        return result

    async def _crawl_govdata(
        self, source: "DataSource", config: dict
    ) -> List[APIDocument]:
        """Crawl GovData.de."""
        from crawlers.api_clients.govdata_client import GovDataClient

        search_query = config.get("search_query", "*:*")
        max_results = config.get("max_results", 100)
        groups = config.get("groups", [])

        documents = []
        async with GovDataClient() as client:
            response = await client.search(
                query=search_query,
                rows=min(max_results, 100),
                groups=groups if groups else None,
            )
            documents.extend(response.data)

            # Paginate if needed
            offset = 100
            while response.has_more and len(documents) < max_results:
                response = await client.search(
                    query=search_query,
                    rows=min(100, max_results - len(documents)),
                    start=offset,
                    groups=groups if groups else None,
                )
                documents.extend(response.data)
                offset += 100

        self.logger.info(
            "GovData crawl completed",
            documents_found=len(documents),
        )
        return documents

    async def _crawl_dip_bundestag(
        self, source: "DataSource", config: dict
    ) -> List[APIDocument]:
        """Crawl DIP Bundestag."""
        from crawlers.api_clients.dip_bundestag_client import DIPBundestagClient

        search_query = config.get("search_query")
        wahlperiode = config.get("wahlperiode", 20)
        vorgangstyp = config.get("vorgangstyp")
        max_results = config.get("max_results", 100)

        documents = []
        async with DIPBundestagClient() as client:
            if vorgangstyp == "Kleine Anfrage":
                # Search Vorgänge for Kleine Anfragen
                response = await client.search_vorgaenge(
                    query=search_query,
                    wahlperiode=wahlperiode,
                    vorgangstyp=vorgangstyp,
                    rows=min(max_results, 100),
                )
                documents.extend(response.data)
            else:
                # Search Drucksachen
                response = await client.search_drucksachen(
                    query=search_query,
                    wahlperiode=wahlperiode,
                    rows=min(max_results, 100),
                )
                documents.extend(response.data)

                # Paginate
                offset = 100
                while response.has_more and len(documents) < max_results:
                    response = await client.search_drucksachen(
                        query=search_query,
                        wahlperiode=wahlperiode,
                        rows=min(100, max_results - len(documents)),
                        offset=offset,
                    )
                    documents.extend(response.data)
                    offset += 100

        self.logger.info(
            "DIP Bundestag crawl completed",
            documents_found=len(documents),
        )
        return documents

    async def _crawl_fragdenstaat(
        self, source: "DataSource", config: dict
    ) -> List[APIDocument]:
        """Crawl FragDenStaat."""
        from crawlers.api_clients.fragdenstaat_client import FragDenStaatClient

        search_query = config.get("search_query", "")
        status = config.get("status")
        jurisdiction = config.get("jurisdiction")
        max_results = config.get("max_results", 100)

        documents = []
        async with FragDenStaatClient() as client:
            response = await client.search(
                query=search_query,
                status=status,
                jurisdiction=jurisdiction,
                limit=min(max_results, 50),
            )
            documents.extend(response.data)

            # Paginate
            offset = 50
            while response.has_more and len(documents) < max_results:
                response = await client.search(
                    query=search_query,
                    status=status,
                    jurisdiction=jurisdiction,
                    limit=min(50, max_results - len(documents)),
                    offset=offset,
                )
                documents.extend(response.data)
                offset += 50

        self.logger.info(
            "FragDenStaat crawl completed",
            documents_found=len(documents),
        )
        return documents

    async def _store_documents(
        self,
        session: "AsyncSession",
        source: "DataSource",
        api_documents: List[APIDocument],
    ) -> tuple[int, int]:
        """Store API documents in the database."""
        import hashlib
        from app.models import Document, ProcessingStatus
        from sqlalchemy import select

        new_count = 0
        updated_count = 0

        for api_doc in api_documents:
            # Create a unique hash for deduplication based on source_id
            content_for_hash = f"{api_doc.source_id}:{api_doc.url}"
            file_hash = hashlib.sha256(content_for_hash.encode()).hexdigest()

            # Check if document already exists
            result = await session.execute(
                select(Document).where(
                    Document.source_id == source.id,
                    Document.file_hash == file_hash,
                )
            )
            existing = result.scalar_one_or_none()

            # Determine if we have a downloadable file
            has_file = bool(api_doc.file_url)

            # Use file_url for download, url as reference
            download_url = api_doc.file_url if has_file else api_doc.url

            # Determine document type from file URL or mime type
            doc_type = api_doc.document_type or "API"
            if has_file:
                if api_doc.mime_type == "application/pdf" or (api_doc.file_url and api_doc.file_url.lower().endswith(".pdf")):
                    doc_type = "PDF"
                elif api_doc.file_url and api_doc.file_url.lower().endswith((".csv", ".json", ".xml")):
                    doc_type = api_doc.file_url.split(".")[-1].upper()

            if existing:
                # Update existing document
                existing.title = api_doc.title
                if api_doc.content:
                    existing.raw_text = api_doc.content
                existing.document_date = api_doc.published_date
                # If we now have a file_url but didn't before, mark for processing
                if has_file and not existing.file_path:
                    existing.original_url = download_url
                    existing.document_type = doc_type
                    existing.processing_status = ProcessingStatus.PENDING
                updated_count += 1
                await session.commit()
            else:
                # Create new document
                # If there's a downloadable file, set PENDING to trigger download
                # If only metadata, set COMPLETED with content as raw_text
                if has_file:
                    status = ProcessingStatus.PENDING
                    raw_text = None  # Will be extracted after download
                else:
                    status = ProcessingStatus.COMPLETED
                    raw_text = api_doc.content

                doc = Document(
                    source_id=source.id,
                    category_id=source.category_id,
                    title=api_doc.title,
                    original_url=download_url or "",
                    document_type=doc_type,
                    file_hash=file_hash,
                    file_size=0,  # Will be set after download
                    raw_text=raw_text,
                    processing_status=status,
                    document_date=api_doc.published_date,
                )
                session.add(doc)

                # Commit each document individually to handle duplicates gracefully
                try:
                    await session.commit()
                    new_count += 1
                except Exception as e:
                    await session.rollback()
                    self.logger.debug(
                        "Document already exists or insert failed",
                        file_hash=file_hash[:16],
                        error=str(e)[:100],
                    )

        self.logger.info(
            "Documents stored",
            new=new_count,
            updated=updated_count,
        )
        return new_count, updated_count

    async def detect_changes(self, source: "DataSource") -> bool:
        """Detect changes - always returns True for API sources."""
        return True
