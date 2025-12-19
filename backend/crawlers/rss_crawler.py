"""
RSS/Atom Feed Crawler.

Crawls RSS and Atom feeds from various sources including:
- Official government gazettes (Amtsblätter)
- Municipal news feeds
- Press releases
- Parliamentary updates
"""

import asyncio
import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any, AsyncIterator, Dict, List, Optional
from xml.etree import ElementTree as ET

import httpx
import structlog

from crawlers.base import BaseCrawler, CrawlResult
from app.config import settings

logger = structlog.get_logger()


@dataclass
class FeedItem:
    """Parsed feed item (RSS or Atom)."""

    id: str
    title: str
    link: str
    description: Optional[str] = None
    content: Optional[str] = None

    # Dates
    published: Optional[datetime] = None
    updated: Optional[datetime] = None

    # Author
    author: Optional[str] = None
    author_email: Optional[str] = None

    # Classification
    categories: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    # Enclosures (attachments)
    enclosures: List[Dict[str, str]] = field(default_factory=list)

    # Source feed info
    source_title: Optional[str] = None
    source_link: Optional[str] = None

    # Computed
    content_hash: Optional[str] = None


@dataclass
class Feed:
    """Parsed feed metadata."""

    title: str
    link: str
    feed_url: str
    feed_type: str  # "rss" or "atom"

    description: Optional[str] = None
    language: Optional[str] = None
    copyright: Optional[str] = None
    generator: Optional[str] = None

    # Update info
    last_build_date: Optional[datetime] = None
    ttl: Optional[int] = None  # Time to live in minutes

    # Image
    image_url: Optional[str] = None
    image_title: Optional[str] = None

    # Items
    items: List[FeedItem] = field(default_factory=list)


class RSSCrawler(BaseCrawler):
    """
    Crawler for RSS and Atom feeds.

    Supports:
    - RSS 2.0
    - RSS 1.0 (RDF)
    - Atom 1.0
    - Various extensions (Dublin Core, Content, Media)

    Example usage:
        crawler = RSSCrawler()
        result = await crawler.crawl_feed("https://example.com/feed.xml")

        # Or iterate items
        async for item in crawler.iterate_feed_items("https://example.com/feed.xml"):
            print(item.title)
    """

    # XML namespaces
    NAMESPACES = {
        "atom": "http://www.w3.org/2005/Atom",
        "dc": "http://purl.org/dc/elements/1.1/",
        "content": "http://purl.org/rss/1.0/modules/content/",
        "media": "http://search.yahoo.com/mrss/",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rss10": "http://purl.org/rss/1.0/",
    }

    def __init__(self):
        super().__init__()
        self.client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if not self.client:
            self.client = httpx.AsyncClient(
                timeout=30,
                headers={
                    "User-Agent": settings.crawler_user_agent,
                    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml",
                },
                follow_redirects=True,
            )
        return self.client

    async def close(self):
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None

    async def crawl(self, source, job) -> CrawlResult:
        """Crawl RSS/Atom feed from a data source."""
        from app.database import get_session_context
        from app.models import Document, ProcessingStatus
        from sqlalchemy import select

        result = CrawlResult()

        try:
            feed_url = source.api_endpoint or source.base_url
            self.logger.info("Crawling feed", url=feed_url)

            feed = await self.fetch_feed(feed_url)
            if not feed:
                result.errors.append({"error": "Failed to fetch feed"})
                return result

            result.pages_crawled = 1
            result.documents_found = len(feed.items)

            async with get_session_context() as session:
                for item in feed.items:
                    # Compute content hash
                    content_hash = self._compute_item_hash(item)

                    # Check if document already exists
                    existing = await session.execute(
                        select(Document).where(
                            Document.source_id == source.id,
                            Document.file_hash == content_hash,
                        )
                    )
                    if existing.scalar():
                        continue

                    # Find PDF or document attachments
                    file_url = None
                    mime_type = None
                    for enc in item.enclosures:
                        enc_type = enc.get("type", "")
                        if "pdf" in enc_type or enc.get("url", "").lower().endswith(".pdf"):
                            file_url = enc.get("url")
                            mime_type = "application/pdf"
                            break
                        elif not file_url:
                            file_url = enc.get("url")
                            mime_type = enc_type

                    # Create document
                    doc = Document(
                        source_id=source.id,
                        category_id=source.category_id,
                        crawl_job_id=job.id,
                        document_type="RSS_ITEM",
                        original_url=item.link,
                        title=item.title,
                        raw_text=item.content or item.description,
                        file_hash=content_hash,
                        processing_status=ProcessingStatus.PENDING if file_url else ProcessingStatus.COMPLETED,
                    )

                    if item.published:
                        doc.document_date = item.published

                    session.add(doc)
                    result.documents_new += 1
                    result.documents_processed += 1

                await session.commit()

            result.stats = {
                "feed_title": feed.title,
                "feed_type": feed.feed_type,
                "items_count": len(feed.items),
            }

        except Exception as e:
            self.logger.exception("RSS crawl failed", error=str(e))
            result.errors.append({"error": str(e), "type": type(e).__name__})

        finally:
            await self.close()

        return result

    async def fetch_feed(self, url: str) -> Optional[Feed]:
        """Fetch and parse a feed from URL."""
        client = await self._get_client()

        try:
            response = await client.get(url)
            response.raise_for_status()

            content = response.text
            return self.parse_feed(content, url)

        except Exception as e:
            self.logger.error("Failed to fetch feed", url=url, error=str(e))
            return None

    def parse_feed(self, content: str, feed_url: str) -> Optional[Feed]:
        """Parse RSS or Atom feed content."""
        try:
            # Clean up content
            content = self._clean_xml(content)
            root = ET.fromstring(content)

            # Detect feed type
            if root.tag == "rss" or root.tag.endswith("}rss"):
                return self._parse_rss(root, feed_url)
            elif root.tag == "{http://www.w3.org/2005/Atom}feed":
                return self._parse_atom(root, feed_url)
            elif root.tag == "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF":
                return self._parse_rss10(root, feed_url)
            else:
                self.logger.warning("Unknown feed format", root_tag=root.tag)
                return None

        except ET.ParseError as e:
            self.logger.error("XML parse error", error=str(e))
            return None

    def _clean_xml(self, content: str) -> str:
        """Clean XML content for parsing."""
        # Remove BOM
        if content.startswith("\ufeff"):
            content = content[1:]

        # Fix common XML issues
        content = re.sub(r"&(?!amp;|lt;|gt;|quot;|apos;|#)", "&amp;", content)

        return content

    def _parse_rss(self, root: ET.Element, feed_url: str) -> Feed:
        """Parse RSS 2.0 feed."""
        channel = root.find("channel")
        if channel is None:
            channel = root

        feed = Feed(
            title=self._get_text(channel, "title") or "Untitled Feed",
            link=self._get_text(channel, "link") or "",
            feed_url=feed_url,
            feed_type="rss",
            description=self._get_text(channel, "description"),
            language=self._get_text(channel, "language"),
            copyright=self._get_text(channel, "copyright"),
            generator=self._get_text(channel, "generator"),
            last_build_date=self._parse_rss_date(self._get_text(channel, "lastBuildDate")),
            ttl=int(self._get_text(channel, "ttl") or 0) or None,
        )

        # Parse image
        image = channel.find("image")
        if image is not None:
            feed.image_url = self._get_text(image, "url")
            feed.image_title = self._get_text(image, "title")

        # Parse items
        for item_elem in channel.findall("item"):
            item = self._parse_rss_item(item_elem)
            if item:
                item.source_title = feed.title
                item.source_link = feed.link
                feed.items.append(item)

        return feed

    def _parse_rss_item(self, elem: ET.Element) -> Optional[FeedItem]:
        """Parse RSS item element."""
        link = self._get_text(elem, "link")
        guid = self._get_text(elem, "guid")

        if not link and not guid:
            return None

        item = FeedItem(
            id=guid or link or "",
            title=self._get_text(elem, "title") or "Untitled",
            link=link or guid or "",
            description=self._get_text(elem, "description"),
            content=self._get_text(elem, "content:encoded", self.NAMESPACES.get("content")),
            published=self._parse_rss_date(self._get_text(elem, "pubDate")),
            author=self._get_text(elem, "author") or self._get_text(elem, "dc:creator", self.NAMESPACES.get("dc")),
        )

        # Parse categories
        for cat in elem.findall("category"):
            if cat.text:
                item.categories.append(cat.text)

        # Parse enclosures
        for enc in elem.findall("enclosure"):
            item.enclosures.append({
                "url": enc.get("url", ""),
                "type": enc.get("type", ""),
                "length": enc.get("length", ""),
            })

        # Compute hash
        item.content_hash = self._compute_item_hash(item)

        return item

    def _parse_atom(self, root: ET.Element, feed_url: str) -> Feed:
        """Parse Atom 1.0 feed."""
        ns = self.NAMESPACES["atom"]

        feed = Feed(
            title=self._get_text(root, f"{{{ns}}}title") or "Untitled Feed",
            link=self._get_atom_link(root, "alternate") or "",
            feed_url=feed_url,
            feed_type="atom",
            description=self._get_text(root, f"{{{ns}}}subtitle"),
            generator=self._get_text(root, f"{{{ns}}}generator"),
            last_build_date=self._parse_atom_date(self._get_text(root, f"{{{ns}}}updated")),
        )

        # Parse rights
        rights = self._get_text(root, f"{{{ns}}}rights")
        if rights:
            feed.copyright = rights

        # Parse entries
        for entry_elem in root.findall(f"{{{ns}}}entry"):
            item = self._parse_atom_entry(entry_elem, ns)
            if item:
                item.source_title = feed.title
                item.source_link = feed.link
                feed.items.append(item)

        return feed

    def _parse_atom_entry(self, elem: ET.Element, ns: str) -> Optional[FeedItem]:
        """Parse Atom entry element."""
        entry_id = self._get_text(elem, f"{{{ns}}}id")
        link = self._get_atom_link(elem, "alternate")

        if not entry_id and not link:
            return None

        # Get content
        content_elem = elem.find(f"{{{ns}}}content")
        content = None
        if content_elem is not None:
            if content_elem.get("type") == "html" or content_elem.get("type") == "xhtml":
                content = "".join(content_elem.itertext())
            else:
                content = content_elem.text

        # Get summary
        summary = self._get_text(elem, f"{{{ns}}}summary")

        item = FeedItem(
            id=entry_id or link or "",
            title=self._get_text(elem, f"{{{ns}}}title") or "Untitled",
            link=link or entry_id or "",
            description=summary,
            content=content,
            published=self._parse_atom_date(self._get_text(elem, f"{{{ns}}}published")),
            updated=self._parse_atom_date(self._get_text(elem, f"{{{ns}}}updated")),
        )

        # Parse author
        author_elem = elem.find(f"{{{ns}}}author")
        if author_elem is not None:
            item.author = self._get_text(author_elem, f"{{{ns}}}name")
            item.author_email = self._get_text(author_elem, f"{{{ns}}}email")

        # Parse categories
        for cat in elem.findall(f"{{{ns}}}category"):
            term = cat.get("term")
            if term:
                item.categories.append(term)

        # Parse enclosures (links with rel="enclosure")
        for link_elem in elem.findall(f"{{{ns}}}link"):
            if link_elem.get("rel") == "enclosure":
                item.enclosures.append({
                    "url": link_elem.get("href", ""),
                    "type": link_elem.get("type", ""),
                    "length": link_elem.get("length", ""),
                })

        item.content_hash = self._compute_item_hash(item)

        return item

    def _parse_rss10(self, root: ET.Element, feed_url: str) -> Feed:
        """Parse RSS 1.0 (RDF) feed."""
        rdf_ns = self.NAMESPACES["rdf"]
        rss_ns = self.NAMESPACES["rss10"]

        channel = root.find(f"{{{rss_ns}}}channel")
        if channel is None:
            channel = root

        feed = Feed(
            title=self._get_text(channel, f"{{{rss_ns}}}title") or self._get_text(channel, "title") or "Untitled",
            link=self._get_text(channel, f"{{{rss_ns}}}link") or self._get_text(channel, "link") or "",
            feed_url=feed_url,
            feed_type="rss10",
            description=self._get_text(channel, f"{{{rss_ns}}}description") or self._get_text(channel, "description"),
        )

        # Parse items
        for item_elem in root.findall(f"{{{rss_ns}}}item"):
            title = self._get_text(item_elem, f"{{{rss_ns}}}title") or self._get_text(item_elem, "title")
            link = self._get_text(item_elem, f"{{{rss_ns}}}link") or self._get_text(item_elem, "link")

            if title or link:
                item = FeedItem(
                    id=item_elem.get(f"{{{rdf_ns}}}about") or link or "",
                    title=title or "Untitled",
                    link=link or "",
                    description=self._get_text(item_elem, f"{{{rss_ns}}}description") or self._get_text(item_elem, "description"),
                )
                item.source_title = feed.title
                item.source_link = feed.link
                item.content_hash = self._compute_item_hash(item)
                feed.items.append(item)

        return feed

    def _get_text(self, elem: ET.Element, path: str, namespace: Optional[str] = None) -> Optional[str]:
        """Get text content from element."""
        if namespace:
            child = elem.find(path, {path.split(":")[0]: namespace})
        else:
            child = elem.find(path)

        if child is not None and child.text:
            return child.text.strip()
        return None

    def _get_atom_link(self, elem: ET.Element, rel: str = "alternate") -> Optional[str]:
        """Get Atom link by relation type."""
        ns = self.NAMESPACES["atom"]
        for link in elem.findall(f"{{{ns}}}link"):
            if link.get("rel", "alternate") == rel:
                return link.get("href")
        return None

    def _parse_rss_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse RSS date format (RFC 822)."""
        if not date_str:
            return None
        try:
            return parsedate_to_datetime(date_str)
        except (ValueError, TypeError):
            return None

    def _parse_atom_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse Atom date format (ISO 8601)."""
        if not date_str:
            return None

        formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
        ]

        date_str = date_str.replace("+00:00", "Z")

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

    def _compute_item_hash(self, item: FeedItem) -> str:
        """Compute hash for feed item (for change detection)."""
        content = f"{item.id}|{item.title}|{item.link}|{item.content or item.description or ''}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    async def iterate_feed_items(
        self,
        url: str,
        since: Optional[datetime] = None,
    ) -> AsyncIterator[FeedItem]:
        """
        Iterate through feed items.

        Args:
            url: Feed URL
            since: Only return items published after this date
        """
        feed = await self.fetch_feed(url)
        if not feed:
            return

        for item in feed.items:
            if since and item.published and item.published < since:
                continue
            yield item

    async def detect_changes(self, source) -> bool:
        """Check if feed has new items since last crawl."""
        feed_url = source.api_endpoint or source.base_url

        try:
            feed = await self.fetch_feed(feed_url)
            if not feed:
                return False

            # Check if any items are newer than last crawl
            if source.last_crawl:
                for item in feed.items:
                    if item.published and item.published > source.last_crawl:
                        return True
                    if item.updated and item.updated > source.last_crawl:
                        return True

            # If we can't determine by date, check content hash
            if feed.items and source.content_hash:
                new_hash = self._compute_item_hash(feed.items[0])
                return new_hash != source.content_hash

            return bool(feed.items)

        finally:
            await self.close()


# Common German government RSS feeds
GERMAN_GOVERNMENT_FEEDS = [
    # Bundesregierung
    {
        "name": "Bundesregierung - Aktuelles",
        "url": "https://www.bundesregierung.de/breg-de/service/rss/970312-970312",
        "category": "Bund",
    },
    {
        "name": "Bundesregierung - Pressemitteilungen",
        "url": "https://www.bundesregierung.de/breg-de/service/rss/992800-992800",
        "category": "Bund",
    },

    # Ministerien
    {
        "name": "BMWi - Wirtschaft",
        "url": "https://www.bmwi.de/SiteGlobals/BMWI/Functions/RSSFeed/DE/RSSNewsfeed/Rss_news.xml",
        "category": "Wirtschaft",
    },
    {
        "name": "BMUV - Umwelt",
        "url": "https://www.bmuv.de/rss-feed",
        "category": "Umwelt",
    },
    {
        "name": "BMJ - Justiz",
        "url": "https://www.bmj.de/DE/Service/RSS/rss_node.html",
        "category": "Justiz",
    },

    # Bundestag
    {
        "name": "Bundestag - hib (heute im bundestag)",
        "url": "https://www.bundestag.de/rss/hib",
        "category": "Parlament",
    },
    {
        "name": "Bundestag - Pressemitteilungen",
        "url": "https://www.bundestag.de/rss/pm",
        "category": "Parlament",
    },

    # Bundesrat
    {
        "name": "Bundesrat - Pressemitteilungen",
        "url": "https://www.bundesrat.de/DE/Service/RSS/rss_node.html",
        "category": "Parlament",
    },

    # Bundesanzeiger
    {
        "name": "Bundesanzeiger",
        "url": "https://www.bundesanzeiger.de/pub/de/rss",
        "category": "Amtsblatt",
    },
]
