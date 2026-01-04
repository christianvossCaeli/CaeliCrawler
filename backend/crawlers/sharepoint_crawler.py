"""SharePoint Crawler for SharePoint Online document libraries.

Crawls documents from SharePoint Online using the Microsoft Graph API.
"""

import asyncio
import fnmatch
import hashlib
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import aiofiles
import structlog

from app.config import settings
from crawlers.base import BaseCrawler, CrawlResult
from external_apis.clients.sharepoint_client import (
    SharePointClient,
    SharePointFile,
    SharePointNotFoundError,
    parse_sharepoint_site_url,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models import CrawlJob, DataSource

logger = structlog.get_logger(__name__)


class SharePointCrawler(BaseCrawler):
    """Crawler for SharePoint Online document libraries.

    Connects to SharePoint via Microsoft Graph API and downloads
    documents from configured document libraries.

    Configuration (in crawl_config):
        site_url: SharePoint site URL (e.g., "contoso.sharepoint.com:/sites/Documents")
        drive_name: Name of the document library (default: first drive)
        folder_path: Path within the drive to crawl (default: root)
        file_extensions: List of extensions to include (e.g., [".pdf", ".docx"])
        recursive: Whether to include subfolders (default: true)
        exclude_patterns: Patterns to exclude (e.g., ["~$*", "*.tmp"])
        max_files: Maximum number of files to crawl (default: 1000)
    """

    # Document types we can process
    SUPPORTED_EXTENSIONS = {
        ".pdf": "PDF",
        ".docx": "DOCX",
        ".doc": "DOC",
        ".html": "HTML",
        ".htm": "HTML",
        ".txt": "TXT",
        ".rtf": "RTF",
        ".xlsx": "XLSX",
        ".xls": "XLS",
        ".pptx": "PPTX",
        ".ppt": "PPT",
    }

    # Batch processing settings
    BATCH_SIZE = 10  # Number of files to download in parallel
    MAX_CONCURRENT_DOWNLOADS = 5  # Semaphore limit for concurrent downloads

    async def crawl(self, source: "DataSource", job: "CrawlJob") -> CrawlResult:
        """Crawl a SharePoint document library."""
        from app.database import get_celery_session_context

        crawl_config = source.crawl_config or {}
        result = CrawlResult()

        # Parse configuration
        site_url = crawl_config.get("site_url", settings.sharepoint_default_site_url)
        if not site_url:
            self.logger.error("No SharePoint site URL configured")
            result.errors.append(
                {
                    "type": "ConfigurationError",
                    "message": "No SharePoint site URL configured",
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )
            return result

        drive_name = crawl_config.get("drive_name")
        folder_path = crawl_config.get("folder_path", "")
        file_extensions = crawl_config.get("file_extensions", list(self.SUPPORTED_EXTENSIONS.keys()))
        recursive = crawl_config.get("recursive", True)
        exclude_patterns = crawl_config.get("exclude_patterns", ["~$*", "*.tmp", ".DS_Store"])
        max_files = crawl_config.get("max_files", 1000)

        # Parse explicit file paths (one per line)
        file_paths_text = crawl_config.get("file_paths_text", "")
        explicit_file_paths = (
            [p.strip() for p in file_paths_text.split("\n") if p.strip() and not p.strip().startswith("#")]
            if file_paths_text
            else []
        )

        self.logger.info(
            "Starting SharePoint crawl",
            source_id=str(source.id),
            source_name=source.name,
            site_url=site_url,
            folder_path=folder_path,
            recursive=recursive,
            explicit_files=len(explicit_file_paths),
        )

        try:
            # Parse site URL components
            hostname, site_path = parse_sharepoint_site_url(site_url)

            async with SharePointClient() as client:
                # Get site
                site = await client.get_site_by_url(hostname, site_path)
                self.logger.debug("Connected to SharePoint site", site_name=site.display_name)

                # Get drive (document library)
                if drive_name:
                    drive = await client.get_drive_by_name(site.id, drive_name)
                    if not drive:
                        raise SharePointNotFoundError(f"Document library not found: {drive_name}")
                else:
                    drives = await client.list_drives(site.id)
                    if not drives:
                        raise SharePointNotFoundError("No document libraries found in site")
                    drive = drives[0]

                self.logger.debug(
                    "Using document library",
                    drive_name=drive.name,
                    drive_id=drive.id,
                )

                files: list[SharePointFile] = []

                # Fetch explicitly specified files first
                if explicit_file_paths:
                    self.logger.info(
                        "Fetching explicit file paths",
                        count=len(explicit_file_paths),
                    )
                    for file_path in explicit_file_paths:
                        file_obj = await client.get_file_by_path(
                            site_id=site.id,
                            drive_id=drive.id,
                            file_path=file_path,
                        )
                        if file_obj:
                            files.append(file_obj)
                        else:
                            result.errors.append(
                                {
                                    "type": "FileNotFound",
                                    "message": f"File not found: {file_path}",
                                    "timestamp": datetime.now(UTC).isoformat(),
                                }
                            )

                # List files from folder (if folder_path is set or no explicit files)
                if folder_path or not explicit_file_paths:
                    folder_files = await client.list_files(
                        site_id=site.id,
                        drive_id=drive.id,
                        folder_path=folder_path,
                        recursive=recursive,
                        file_extensions=file_extensions,
                    )
                    # Avoid duplicates (by file ID)
                    existing_ids = {f.id for f in files}
                    for f in folder_files:
                        if f.id not in existing_ids:
                            files.append(f)

                # Filter out excluded patterns and limit
                files = self._filter_files(files, exclude_patterns)[:max_files]

                result.pages_crawled = 1
                result.documents_found = len(files)

                self.logger.info(
                    "Found SharePoint files",
                    total_files=len(files),
                    explicit_files=len(explicit_file_paths) if explicit_file_paths else 0,
                )

                # Process files in batches with parallel downloads
                async with get_celery_session_context() as session:
                    semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_DOWNLOADS)

                    for batch_start in range(0, len(files), self.BATCH_SIZE):
                        batch = files[batch_start : batch_start + self.BATCH_SIZE]

                        self.logger.debug(
                            "Processing batch",
                            batch_start=batch_start,
                            batch_size=len(batch),
                            total_files=len(files),
                        )

                        # Process batch in parallel
                        tasks = [
                            self._process_file_with_semaphore(
                                semaphore=semaphore,
                                session=session,
                                client=client,
                                source=source,
                                job=job,
                                file=file,
                            )
                            for file in batch
                        ]

                        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                        # Collect results
                        for file, file_result in zip(batch, batch_results, strict=False):
                            if isinstance(file_result, Exception):
                                self.logger.warning(
                                    "Failed to process SharePoint file",
                                    file_name=file.name,
                                    error=str(file_result),
                                )
                                result.errors.append(
                                    {
                                        "type": type(file_result).__name__,
                                        "message": str(file_result),
                                        "file": file.name,
                                        "timestamp": datetime.now(UTC).isoformat(),
                                    }
                                )
                            else:
                                is_new, success = file_result
                                if success:
                                    if is_new:
                                        result.documents_new += 1
                                    else:
                                        result.documents_updated += 1
                                    result.documents_processed += 1

        except Exception as e:
            self.logger.exception("SharePoint crawl failed", error=str(e))
            result.errors.append(
                {
                    "type": type(e).__name__,
                    "message": str(e),
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )

        self.logger.info(
            "SharePoint crawl completed",
            documents_new=result.documents_new,
            documents_updated=result.documents_updated,
            errors=len(result.errors),
        )

        return result

    async def _process_file_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        session: "AsyncSession",
        client: SharePointClient,
        source: "DataSource",
        job: "CrawlJob",
        file: SharePointFile,
    ) -> tuple[bool, bool]:
        """Process a file with semaphore for concurrency control.

        Args:
            semaphore: Semaphore for limiting concurrent downloads.
            session: Database session.
            client: SharePoint client.
            source: Data source.
            job: Crawl job.
            file: SharePoint file to process.

        Returns:
            Tuple of (is_new, success).
        """
        async with semaphore:
            return await self._process_file(
                session=session,
                client=client,
                source=source,
                job=job,
                file=file,
            )

    def _filter_files(
        self,
        files: list[SharePointFile],
        exclude_patterns: list[str],
    ) -> list[SharePointFile]:
        """Filter files by exclude patterns using fnmatch.

        Args:
            files: List of SharePoint files.
            exclude_patterns: Glob patterns to exclude (e.g., ["~$*", "*.tmp"]).

        Returns:
            Filtered list of files.
        """
        if not exclude_patterns:
            return files

        return [
            file
            for file in files
            if not any(fnmatch.fnmatch(file.name.lower(), pattern.lower()) for pattern in exclude_patterns)
        ]

    async def _process_file(
        self,
        session: "AsyncSession",
        client: SharePointClient,
        source: "DataSource",
        job: "CrawlJob",
        file: SharePointFile,
    ) -> tuple[bool, bool]:
        """Process a single SharePoint file.

        Downloads the file and creates/updates the Document record.

        Args:
            session: Database session.
            client: SharePoint client.
            source: Data source.
            job: Crawl job.
            file: SharePoint file to process.

        Returns:
            Tuple of (is_new, success) where is_new indicates if document
            was newly created, and success indicates if processing succeeded.
        """
        from sqlalchemy import select

        from app.models import Document, ProcessingStatus

        # Create unique hash based on SharePoint item ID and source
        content_for_hash = f"sharepoint:{source.id}:{file.id}"
        file_hash = hashlib.sha256(content_for_hash.encode()).hexdigest()

        # Check if document already exists
        result = await session.execute(
            select(Document).where(
                Document.source_id == source.id,
                Document.file_hash == file_hash,
            )
        )
        existing = result.scalar_one_or_none()

        # Determine document type from extension
        ext = os.path.splitext(file.name)[1].lower()
        doc_type = self.SUPPORTED_EXTENSIONS.get(ext, "UNKNOWN")

        # Download file
        if file.download_url:
            # Use pre-authenticated URL (faster)
            content = await client.download_file_by_url(file.download_url)
        else:
            # Use API download
            content = await client.download_file(
                site_id=file.site_id,
                drive_id=file.drive_id,
                item_id=file.id,
            )

        # Save file to storage
        file_path = await self._save_file(
            source_id=source.id,
            category_id=job.category_id,
            file_name=file.name,
            content=content,
        )

        if existing:
            # Update existing document
            existing.title = file.name
            existing.file_path = file_path
            existing.file_size = len(content)
            existing.document_date = file.modified_at
            existing.original_url = file.web_url
            existing.processing_status = ProcessingStatus.PENDING  # Re-process
            existing.updated_at = datetime.now(UTC)
            await session.commit()
            return (False, True)  # Not new, but successful
        else:
            # Create new document
            doc = Document(
                source_id=source.id,
                category_id=job.category_id,
                title=file.name,
                original_url=file.web_url,
                document_type=doc_type,
                file_path=file_path,
                file_hash=file_hash,
                file_size=len(content),
                processing_status=ProcessingStatus.PENDING,
                document_date=file.modified_at,
            )
            session.add(doc)

            try:
                await session.commit()
                return (True, True)  # New and successful
            except Exception as e:
                await session.rollback()
                self.logger.debug(
                    "Document already exists or insert failed",
                    file_hash=file_hash[:16],
                    error=str(e)[:100],
                )
                return (False, False)  # Not new, not successful

    async def _save_file(
        self,
        source_id: "UUID",
        category_id: "UUID",
        file_name: str,
        content: bytes,
    ) -> str:
        """Save file content to storage.

        Args:
            source_id: Data source ID.
            category_id: Category ID for organizing files.
            file_name: Original file name.
            content: File content as bytes.

        Returns:
            Relative file path within storage.
        """
        # Create storage path
        storage_base = Path(settings.document_storage_path)
        category_dir = storage_base / str(category_id)
        category_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        file_hash = hashlib.sha256(content).hexdigest()[:12]
        ext = os.path.splitext(file_name)[1]
        safe_name = re.sub(r"[^\w\-.]", "_", file_name)
        unique_name = f"{file_hash}_{safe_name}"

        # Ensure path doesn't exceed filesystem limits
        if len(unique_name) > 200:
            unique_name = f"{file_hash}{ext}"

        file_path = category_dir / unique_name

        # Write file
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        self.logger.debug(
            "Saved SharePoint file",
            file_name=file_name,
            file_path=str(file_path),
            size=len(content),
        )

        # Return relative path
        return str(file_path.relative_to(storage_base))

    async def detect_changes(self, source: "DataSource") -> bool:
        """Detect if there are changes in the SharePoint library.

        Uses the Graph API delta endpoint for efficient change detection.

        Args:
            source: Data source with SharePoint configuration.

        Returns:
            True if changes detected, False otherwise.
        """
        crawl_config = source.crawl_config or {}
        site_url = crawl_config.get("site_url", settings.sharepoint_default_site_url)

        if not site_url:
            return True  # Can't check, assume changes

        try:
            hostname, site_path = parse_sharepoint_site_url(site_url)

            async with SharePointClient() as client:
                site = await client.get_site_by_url(hostname, site_path)
                drives = await client.list_drives(site.id)

                if not drives:
                    return False

                drive = drives[0]

                # Get delta token from previous crawl (stored in extra_data)
                delta_token = source.extra_data.get("sharepoint_delta_token") if source.extra_data else None

                # Check for changes
                changed_files, new_token = await client.get_delta(
                    site_id=site.id,
                    drive_id=drive.id,
                    delta_token=delta_token,
                )

                # Store new token (will be persisted on next crawl)
                if new_token:
                    if not source.extra_data:
                        source.extra_data = {}
                    source.extra_data["sharepoint_delta_token"] = new_token

                return len(changed_files) > 0

        except Exception as e:
            self.logger.warning(
                "SharePoint change detection failed",
                error=str(e),
            )
            return True  # Assume changes if detection fails
