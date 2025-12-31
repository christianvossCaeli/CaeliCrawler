"""HTML Table extractor for structured data in tables."""


import structlog

from ..models import ExtractedSource, SearchStrategy
from .base import BaseExtractor

logger = structlog.get_logger()


class HTMLTableExtractor(BaseExtractor):
    """Extract data sources from HTML tables."""

    async def can_extract(self, url: str, content_type: str = None) -> bool:
        """Check if content might contain HTML tables."""
        # Can handle any HTML content
        if content_type and "text/html" in content_type:
            return True
        return True  # Default to trying HTML extraction

    async def extract(
        self,
        url: str,
        html_content: str,
        strategy: SearchStrategy,
    ) -> list[ExtractedSource]:
        """Extract data from HTML tables."""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.warning("BeautifulSoup not installed, skipping HTML table extraction")
            return []

        sources = []
        soup = BeautifulSoup(html_content, "html.parser")

        # Find all tables
        tables = soup.find_all("table")

        for table in tables:
            # Get headers
            headers = []
            header_row = table.find("tr")
            if header_row:
                for th in header_row.find_all(["th", "td"]):
                    headers.append(self._clean_text(th.get_text()).lower())

            # Find columns with names and URLs
            name_col = self._find_column_index(headers, ["name", "name", "titel", "bezeichnung", "organisation"])
            url_col = self._find_column_index(headers, ["website", "url", "link", "webseite", "homepage"])

            # If no explicit URL column, we'll look for links in any column
            has_url_col = url_col is not None

            # Process rows
            rows = table.find_all("tr")[1:]  # Skip header
            for row in rows:
                cells = row.find_all(["td", "th"])
                if not cells:
                    continue

                name = ""
                found_url = ""
                metadata = {}

                # Extract name
                if name_col is not None and name_col < len(cells):
                    name = self._clean_text(cells[name_col].get_text())
                    # Check if name cell has a link
                    link = cells[name_col].find("a", href=True)
                    if link and not found_url:
                        found_url = self._normalize_url(link["href"], url)

                # Extract explicit URL
                if has_url_col and url_col < len(cells):
                    link = cells[url_col].find("a", href=True)
                    if link:
                        found_url = self._normalize_url(link["href"], url)
                    else:
                        # Try text content as URL
                        text = self._clean_text(cells[url_col].get_text())
                        if text.startswith(("http://", "https://", "www.")):
                            found_url = self._normalize_url(text, url)

                # If no URL found yet, look in all cells
                if not found_url:
                    for cell in cells:
                        link = cell.find("a", href=True)
                        if link:
                            href = link["href"]
                            if self._is_valid_url(self._normalize_url(href, url)):
                                # Prefer external links
                                normalized = self._normalize_url(href, url)
                                if self._extract_domain(normalized) != self._extract_domain(url):
                                    found_url = normalized
                                    if not name:
                                        name = self._clean_text(link.get_text())
                                    break

                # Skip if no valid URL or name
                if not found_url or not name:
                    continue

                # Skip internal links
                if self._extract_domain(found_url) == self._extract_domain(url):
                    continue

                # Extract additional metadata from other columns
                for i, cell in enumerate(cells):
                    if i != name_col and i != url_col and i < len(headers):
                        header = headers[i] if i < len(headers) else f"col_{i}"
                        value = self._clean_text(cell.get_text())
                        if value and len(value) < 200:  # Skip very long values
                            metadata[header] = value

                sources.append(ExtractedSource(
                    name=name,
                    base_url=found_url,
                    source_type="WEBSITE",
                    metadata=metadata,
                    extraction_method="html_table",
                    confidence=0.7,
                ))

        logger.debug(
            "HTML table extraction completed",
            url=url,
            tables_found=len(tables),
            sources_extracted=len(sources),
        )

        return sources

    def _find_column_index(self, headers: list[str], candidates: list[str]) -> int | None:
        """Find index of column matching any of the candidates."""
        for candidate in candidates:
            for i, header in enumerate(headers):
                if candidate in header:
                    return i
        return None
