"""
News Crawler for municipal websites and RSS feeds.

Specialized crawler for extracting news articles, press releases,
and announcements from municipal websites. Supports:
- RSS/Atom feeds
- HTML news pages (with keyword filtering)
- Press release sections
"""

import asyncio
import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

import httpx
from bs4 import BeautifulSoup
import structlog

from crawlers.base import BaseCrawler, CrawlResult
from app.config import settings

if TYPE_CHECKING:
    from app.models import DataSource, CrawlJob

logger = structlog.get_logger()


@dataclass
class NewsArticle:
    """Extracted news article."""
    url: str
    title: str
    content: str
    published_date: Optional[datetime] = None
    author: Optional[str] = None
    summary: Optional[str] = None


class NewsCrawler(BaseCrawler):
    """
    Crawler for municipal news and press releases.

    Optimized for extracting structured content from:
    - RSS/Atom feeds
    - Municipal "Aktuelles" / "News" sections
    - Press release pages
    """

    def __init__(self):
        super().__init__()
        self.articles: List[NewsArticle] = []

    async def crawl(self, source: "DataSource", job: "CrawlJob") -> CrawlResult:
        """Crawl news source for articles."""
        from app.database import get_celery_session_context
        from app.models import Document, ProcessingStatus, Category

        result = CrawlResult()
        config = source.crawl_config or {}

        # Get keywords from category for filtering
        async with get_celery_session_context() as session:
            category = await session.get(Category, source.category_id)
            keywords = category.search_terms if category else []

        crawl_type = config.get("crawl_type", "auto")  # auto, rss, html
        max_articles = config.get("max_articles", 50)
        rss_url = config.get("rss_url", source.base_url)
        news_path = config.get("news_path", "/aktuelles")  # Common patterns
        filter_keywords = config.get("filter_keywords", keywords)

        self.articles = []

        try:
            self.logger.info(
                "Starting news crawl",
                url=source.base_url,
                crawl_type=crawl_type,
                keywords=filter_keywords[:5] if filter_keywords else [],
            )

            if crawl_type == "rss" or crawl_type == "auto":
                # Try RSS first
                rss_articles = await self._crawl_rss(rss_url, max_articles)
                if rss_articles:
                    self.articles.extend(rss_articles)
                    self.logger.info("Found articles via RSS", count=len(rss_articles))
                elif crawl_type == "auto":
                    # Fallback to HTML if RSS fails
                    html_articles = await self._crawl_html_news(
                        source.base_url, news_path, max_articles
                    )
                    self.articles.extend(html_articles)
                    self.logger.info("Found articles via HTML", count=len(html_articles))
            else:
                # HTML only
                html_articles = await self._crawl_html_news(
                    source.base_url, news_path, max_articles
                )
                self.articles.extend(html_articles)

            # Filter by keywords if specified
            if filter_keywords:
                self.articles = self._filter_by_keywords(self.articles, filter_keywords)
                self.logger.info(
                    "Articles after keyword filtering",
                    count=len(self.articles),
                )

            result.pages_crawled = 1
            result.documents_found = len(self.articles)

            # Save articles as documents
            async with get_celery_session_context() as session:
                new_count, updated_count = await self._store_articles(
                    session, source, job
                )
                result.documents_new = new_count
                result.documents_updated = updated_count
                result.documents_processed = new_count + updated_count

            result.stats = {
                "articles_found": len(self.articles),
                "articles_stored": result.documents_new + result.documents_updated,
            }

        except Exception as e:
            self.logger.exception("News crawl failed", error=str(e))
            result.errors.append({
                "error": str(e),
                "type": type(e).__name__,
                "timestamp": datetime.utcnow().isoformat(),
            })

        return result

    async def _crawl_rss(self, rss_url: str, max_articles: int) -> List[NewsArticle]:
        """Parse RSS/Atom feed for articles."""
        articles = []

        try:
            async with httpx.AsyncClient(
                timeout=30,
                headers={"User-Agent": settings.crawler_user_agent},
                follow_redirects=True,
            ) as client:
                response = await client.get(rss_url)
                response.raise_for_status()

                # Parse XML
                root = ElementTree.fromstring(response.content)

                # Handle RSS 2.0
                if root.tag == "rss":
                    channel = root.find("channel")
                    if channel:
                        for item in channel.findall("item")[:max_articles]:
                            article = self._parse_rss_item(item)
                            if article:
                                articles.append(article)

                # Handle Atom
                elif "atom" in root.tag.lower() or root.tag == "feed":
                    ns = {"atom": "http://www.w3.org/2005/Atom"}
                    for entry in root.findall("atom:entry", ns)[:max_articles]:
                        article = self._parse_atom_entry(entry, ns)
                        if article:
                            articles.append(article)
                    # Fallback without namespace
                    if not articles:
                        for entry in root.findall("entry")[:max_articles]:
                            article = self._parse_atom_entry_simple(entry)
                            if article:
                                articles.append(article)

        except ElementTree.ParseError as e:
            self.logger.warning("Failed to parse RSS", error=str(e), url=rss_url)
        except Exception as e:
            self.logger.warning("RSS fetch failed", error=str(e), url=rss_url)

        return articles

    def _parse_rss_item(self, item) -> Optional[NewsArticle]:
        """Parse RSS 2.0 item."""
        title = item.findtext("title")
        link = item.findtext("link")
        description = item.findtext("description")
        pub_date = item.findtext("pubDate")
        content = item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded")

        if not title or not link:
            return None

        # Parse date
        published = None
        if pub_date:
            try:
                from email.utils import parsedate_to_datetime
                published = parsedate_to_datetime(pub_date)
            except Exception:
                pass

        return NewsArticle(
            url=link,
            title=title.strip(),
            content=self._clean_html(content or description or ""),
            published_date=published,
            summary=self._clean_html(description or "")[:500] if description else None,
        )

    def _parse_atom_entry(self, entry, ns: Dict) -> Optional[NewsArticle]:
        """Parse Atom entry with namespace."""
        title = entry.findtext("atom:title", namespaces=ns)
        link_elem = entry.find("atom:link[@rel='alternate']", ns)
        if link_elem is None:
            link_elem = entry.find("atom:link", ns)
        link = link_elem.get("href") if link_elem is not None else None
        summary = entry.findtext("atom:summary", namespaces=ns)
        content = entry.findtext("atom:content", namespaces=ns)
        updated = entry.findtext("atom:updated", namespaces=ns)

        if not title or not link:
            return None

        # Parse date
        published = None
        if updated:
            try:
                published = datetime.fromisoformat(updated.replace("Z", "+00:00"))
            except Exception:
                pass

        return NewsArticle(
            url=link,
            title=title.strip(),
            content=self._clean_html(content or summary or ""),
            published_date=published,
            summary=self._clean_html(summary or "")[:500] if summary else None,
        )

    def _parse_atom_entry_simple(self, entry) -> Optional[NewsArticle]:
        """Parse Atom entry without namespace."""
        title = entry.findtext("title")
        link_elem = entry.find("link[@rel='alternate']")
        if link_elem is None:
            link_elem = entry.find("link")
        link = link_elem.get("href") if link_elem is not None else None
        summary = entry.findtext("summary")
        content = entry.findtext("content")
        updated = entry.findtext("updated")

        if not title or not link:
            return None

        published = None
        if updated:
            try:
                published = datetime.fromisoformat(updated.replace("Z", "+00:00"))
            except Exception:
                pass

        return NewsArticle(
            url=link,
            title=title.strip(),
            content=self._clean_html(content or summary or ""),
            published_date=published,
            summary=self._clean_html(summary or "")[:500] if summary else None,
        )

    async def _crawl_html_news(
        self, base_url: str, news_path: str, max_articles: int
    ) -> List[NewsArticle]:
        """Crawl HTML news page for articles."""
        articles = []

        # Common news page paths to try
        news_paths = [
            news_path,
            "/aktuelles",
            "/news",
            "/presse",
            "/pressemitteilungen",
            "/nachrichten",
        ]

        async with httpx.AsyncClient(
            timeout=30,
            headers={"User-Agent": settings.crawler_user_agent},
            follow_redirects=True,
        ) as client:
            for path in news_paths:
                news_url = urljoin(base_url, path)
                try:
                    response = await client.get(news_url)
                    if response.status_code != 200:
                        continue

                    soup = BeautifulSoup(response.text, "lxml")

                    # Find article links - common patterns
                    article_links = self._find_article_links(soup, news_url)

                    for link_url in article_links[:max_articles]:
                        if len(articles) >= max_articles:
                            break

                        try:
                            article = await self._extract_article(client, link_url)
                            if article:
                                articles.append(article)
                        except Exception as e:
                            self.logger.warning(
                                "Failed to extract article",
                                url=link_url,
                                error=str(e)
                            )

                        # Rate limiting
                        await asyncio.sleep(settings.crawler_default_delay)

                    if articles:
                        break  # Found articles, stop trying other paths

                except Exception as e:
                    self.logger.warning(
                        "Failed to crawl news page",
                        url=news_url,
                        error=str(e)
                    )

        return articles

    def _find_article_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Find article links in a news listing page."""
        links = []
        base_domain = urlparse(base_url).netloc

        # Look for common article containers
        article_selectors = [
            "article a[href]",
            ".news-item a[href]",
            ".news-list a[href]",
            ".article-list a[href]",
            ".press-release a[href]",
            "main a[href]",
            "#content a[href]",
        ]

        for selector in article_selectors:
            for link in soup.select(selector):
                href = link.get("href")
                if not href:
                    continue

                full_url = urljoin(base_url, href)

                # Same domain check
                if urlparse(full_url).netloc != base_domain:
                    continue

                # Skip common non-article patterns
                if any(skip in full_url.lower() for skip in [
                    "/login", "/register", "/search", "/kontakt", "/impressum",
                    "/datenschutz", ".pdf", ".jpg", ".png", "#"
                ]):
                    continue

                if full_url not in links:
                    links.append(full_url)

        return links

    async def _extract_article(
        self, client: httpx.AsyncClient, url: str
    ) -> Optional[NewsArticle]:
        """Extract article content from a page."""
        response = await client.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        # Extract title
        title = None
        title_elem = soup.find("h1") or soup.find("title")
        if title_elem:
            title = title_elem.get_text(strip=True)

        if not title:
            return None

        # Extract main content
        content = ""
        content_selectors = [
            "article",
            ".article-content",
            ".news-content",
            ".content",
            "main",
            "#content",
        ]

        for selector in content_selectors:
            elem = soup.select_one(selector)
            if elem:
                # Remove navigation, footer, etc.
                for remove in elem.select("nav, footer, aside, .sidebar"):
                    remove.decompose()
                content = elem.get_text(separator="\n", strip=True)
                break

        if not content:
            # Fallback: get all paragraph text
            paragraphs = soup.find_all("p")
            content = "\n".join(p.get_text(strip=True) for p in paragraphs)

        # Extract date
        published = None
        date_patterns = [
            r"(\d{1,2})\.(\d{1,2})\.(\d{4})",  # DD.MM.YYYY
            r"(\d{4})-(\d{2})-(\d{2})",  # YYYY-MM-DD
        ]

        # Look for date in meta tags
        date_meta = soup.find("meta", {"property": "article:published_time"})
        if date_meta and date_meta.get("content"):
            try:
                published = datetime.fromisoformat(
                    date_meta["content"].replace("Z", "+00:00")
                )
            except Exception:
                pass

        # Look for date in text
        if not published:
            page_text = soup.get_text()
            for pattern in date_patterns:
                match = re.search(pattern, page_text)
                if match:
                    try:
                        if "." in pattern:
                            published = datetime(
                                int(match.group(3)),
                                int(match.group(2)),
                                int(match.group(1))
                            )
                        else:
                            published = datetime(
                                int(match.group(1)),
                                int(match.group(2)),
                                int(match.group(3))
                            )
                        break
                    except Exception:
                        pass

        return NewsArticle(
            url=url,
            title=title,
            content=content[:50000],  # Limit content length
            published_date=published,
        )

    def _filter_by_keywords(
        self, articles: List[NewsArticle], keywords: List[str]
    ) -> List[NewsArticle]:
        """Filter articles by keywords (case-insensitive)."""
        if not keywords:
            return articles

        filtered = []
        keywords_lower = [k.lower() for k in keywords]

        for article in articles:
            text_to_search = (
                f"{article.title} {article.content} {article.summary or ''}"
            ).lower()

            if any(kw in text_to_search for kw in keywords_lower):
                filtered.append(article)

        return filtered

    def _clean_html(self, html_content: str) -> str:
        """Remove HTML tags and clean up text."""
        if not html_content:
            return ""
        soup = BeautifulSoup(html_content, "lxml")
        return soup.get_text(separator=" ", strip=True)

    async def _store_articles(
        self, session, source: "DataSource", job: "CrawlJob"
    ) -> tuple[int, int]:
        """Store articles as documents."""
        from app.models import Document, ProcessingStatus
        from sqlalchemy import select

        new_count = 0
        updated_count = 0

        for article in self.articles:
            # Create hash from URL
            file_hash = hashlib.sha256(
                f"{source.id}:{article.url}".encode()
            ).hexdigest()

            # Check if exists
            result = await session.execute(
                select(Document).where(
                    Document.source_id == source.id,
                    Document.file_hash == file_hash,
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update if content changed
                if existing.raw_text != article.content:
                    existing.title = article.title
                    existing.raw_text = article.content
                    existing.document_date = article.published_date
                    existing.processing_status = ProcessingStatus.COMPLETED
                    updated_count += 1
                    await session.commit()
            else:
                # Create new
                doc = Document(
                    source_id=source.id,
                    category_id=job.category_id,  # Use job's category
                    crawl_job_id=job.id,
                    document_type="HTML",
                    original_url=article.url,
                    title=article.title,
                    file_hash=file_hash,
                    file_size=len(article.content.encode("utf-8")),
                    raw_text=article.content,
                    document_date=article.published_date,
                    processing_status=ProcessingStatus.COMPLETED,  # Already has text
                )
                session.add(doc)

                try:
                    await session.commit()
                    new_count += 1
                except Exception as e:
                    await session.rollback()
                    self.logger.debug(
                        "Article already exists",
                        url=article.url,
                        error=str(e)[:100],
                    )

        return new_count, updated_count

    async def detect_changes(self, source: "DataSource") -> bool:
        """Detect changes by checking RSS feed or page content."""
        try:
            async with httpx.AsyncClient(
                timeout=30,
                headers={"User-Agent": settings.crawler_user_agent},
                follow_redirects=True,
            ) as client:
                # Try RSS first
                config = source.crawl_config or {}
                rss_url = config.get("rss_url", source.base_url)

                response = await client.get(rss_url)
                response.raise_for_status()

                new_hash = self.compute_hash(response.content)

                if source.content_hash and source.content_hash != new_hash:
                    return True

                return False

        except Exception as e:
            self.logger.error("Change detection failed", error=str(e))
            return True  # Assume changes on error
