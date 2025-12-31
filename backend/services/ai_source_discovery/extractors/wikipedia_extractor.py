"""Wikipedia-specific extractor for list pages."""

from urllib.parse import urlparse

import structlog

from ..models import ExtractedSource, SearchStrategy
from .base import BaseExtractor

logger = structlog.get_logger()


class WikipediaExtractor(BaseExtractor):
    """Extract data sources from Wikipedia list pages."""

    WIKIPEDIA_DOMAINS = [
        "wikipedia.org",
        "de.wikipedia.org",
        "en.wikipedia.org",
    ]

    async def can_extract(self, url: str, content_type: str = None) -> bool:
        """Check if URL is a Wikipedia page."""
        parsed = urlparse(url)
        return any(domain in parsed.netloc for domain in self.WIKIPEDIA_DOMAINS)

    async def extract(
        self,
        url: str,
        html_content: str,
        strategy: SearchStrategy,
    ) -> list[ExtractedSource]:
        """Extract data from Wikipedia list pages."""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.warning("BeautifulSoup not installed, skipping Wikipedia extraction")
            return []

        sources = []
        soup = BeautifulSoup(html_content, "html.parser")

        # Find the main content area
        content = soup.find("div", {"id": "mw-content-text"})
        if not content:
            content = soup

        # Strategy 1: Extract from infoboxes with external links
        infoboxes = content.find_all("table", class_="infobox")
        for infobox in infoboxes:
            sources.extend(self._extract_from_infobox(infobox, url))

        # Strategy 2: Extract from wikitables (common in list pages)
        wikitables = content.find_all("table", class_="wikitable")
        for table in wikitables:
            sources.extend(self._extract_from_wikitable(table, url))

        # Strategy 3: Extract from lists with external links
        lists = content.find_all(["ul", "ol"])
        for lst in lists:
            sources.extend(self._extract_from_list(lst, url))

        # Strategy 4: Extract external links section
        ext_links = content.find("span", {"id": "Weblinks"})
        if ext_links:
            parent = ext_links.find_parent()
            if parent:
                next_ul = parent.find_next_sibling("ul")
                if next_ul:
                    sources.extend(self._extract_from_list(next_ul, url))

        # Deduplicate by URL
        seen_urls = set()
        unique_sources = []
        for source in sources:
            if source.base_url not in seen_urls:
                seen_urls.add(source.base_url)
                unique_sources.append(source)

        logger.debug(
            "Wikipedia extraction completed",
            url=url,
            sources_extracted=len(unique_sources),
        )

        return unique_sources

    def _extract_from_infobox(self, infobox, base_url: str) -> list[ExtractedSource]:
        """Extract from Wikipedia infobox."""
        sources = []

        # Find title/name
        name = ""
        caption = infobox.find("caption")
        if caption:
            name = self._clean_text(caption.get_text())
        if not name:
            th = infobox.find("th", class_="infobox-above")
            if th:
                name = self._clean_text(th.get_text())

        # Find website link
        for row in infobox.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if th and td:
                header_text = self._clean_text(th.get_text()).lower()
                if any(term in header_text for term in ["website", "webseite", "homepage", "url"]):
                    link = td.find("a", href=True)
                    if link:
                        href = link["href"]
                        if href.startswith("http") and "wikipedia.org" not in href:
                            sources.append(ExtractedSource(
                                name=name or self._extract_domain(href),
                                base_url=href,
                                source_type="WEBSITE",
                                metadata={"source": "wikipedia_infobox"},
                                extraction_method="wikipedia_infobox",
                                confidence=0.85,
                            ))

        return sources

    def _extract_from_wikitable(self, table, base_url: str) -> list[ExtractedSource]:
        """Extract from Wikipedia sortable/wikitable."""
        sources = []

        # Get headers
        headers = []
        header_row = table.find("tr")
        if header_row:
            for th in header_row.find_all(["th"]):
                headers.append(self._clean_text(th.get_text()).lower())

        # Find name and website columns
        name_col = None
        url_col = None
        for i, h in enumerate(headers):
            if any(term in h for term in ["name", "verein", "club", "gemeinde", "organisation"]):
                name_col = i
            if any(term in h for term in ["website", "webseite", "homepage"]):
                url_col = i

        # Process rows
        for row in table.find_all("tr")[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue

            name = ""
            found_url = ""

            # Get name from name column or first column
            if name_col is not None and name_col < len(cells):
                name = self._clean_text(cells[name_col].get_text())
            elif cells:
                name = self._clean_text(cells[0].get_text())

            # Get URL from URL column
            if url_col is not None and url_col < len(cells):
                link = cells[url_col].find("a", href=True)
                if link and link["href"].startswith("http"):
                    found_url = link["href"]

            # If no URL column, look for external links in all cells
            if not found_url:
                for cell in cells:
                    for link in cell.find_all("a", href=True):
                        href = link["href"]
                        if href.startswith("http") and "wikipedia.org" not in href:
                            found_url = href
                            break
                    if found_url:
                        break

            if name and found_url and "wikipedia.org" not in found_url:
                sources.append(ExtractedSource(
                    name=name,
                    base_url=found_url,
                    source_type="WEBSITE",
                    metadata={"source": "wikipedia_table"},
                    extraction_method="wikipedia_table",
                    confidence=0.8,
                ))

        return sources

    def _extract_from_list(self, lst, base_url: str) -> list[ExtractedSource]:
        """Extract from ul/ol lists with external links."""
        sources = []

        for li in lst.find_all("li", recursive=False):
            external_link = None
            name = ""

            # Look for external links
            for link in li.find_all("a", href=True):
                href = link["href"]
                if href.startswith("http") and "wikipedia.org" not in href:
                    external_link = href
                    if not name:
                        name = self._clean_text(link.get_text())
                    break

            # If no name from link, try the list item text
            if external_link and not name:
                # Get text before any nested elements
                text = ""
                for child in li.children:
                    if isinstance(child, str):
                        text += child
                    elif hasattr(child, "get_text"):
                        text += child.get_text()
                        break
                name = self._clean_text(text)[:100]

            if external_link and name:
                sources.append(ExtractedSource(
                    name=name,
                    base_url=external_link,
                    source_type="WEBSITE",
                    metadata={"source": "wikipedia_list"},
                    extraction_method="wikipedia_list",
                    confidence=0.7,
                ))

        return sources
