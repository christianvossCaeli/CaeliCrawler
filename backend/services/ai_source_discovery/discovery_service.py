"""Main AI Source Discovery Service."""

import asyncio
import ipaddress
import json
import socket
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from uuid import UUID

import httpx
import structlog

from app.config import settings
from app.core.cache import search_strategy_cache, make_cache_key
from app.core.retry import with_retry, LLM_RETRY_CONFIG, NETWORK_RETRY_CONFIG
from app.core.security_logging import security_logger
from services.smart_query.query_interpreter import get_openai_client
from services.smart_query.utils import clean_json_response
from .models import (
    DiscoveryResult,
    DiscoveryStats,
    ExtractedSource,
    SearchResult,
    SearchStrategy,
    SourceWithTags,
)
from .prompts import AI_SEARCH_STRATEGY_PROMPT, AI_TAG_GENERATION_PROMPT
from .search_providers import SerperSearchProvider
from .extractors import HTMLTableExtractor, WikipediaExtractor, AIExtractor

logger = structlog.get_logger()

# SSRF Protection: Blocked hosts and private IP ranges
BLOCKED_HOSTS = {'localhost', '127.0.0.1', '0.0.0.0', '::1', '[::1]'}


def is_safe_url(url: str) -> bool:
    """
    Validate URL to prevent SSRF attacks.

    Blocks:
    - localhost and loopback addresses
    - Private IP ranges (10.x, 172.16-31.x, 192.168.x)
    - Link-local addresses
    - Internal hostnames

    Args:
        url: URL to validate

    Returns:
        True if URL is safe to fetch, False otherwise
    """
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname

        if not hostname:
            return False

        # Block known internal hostnames
        if hostname.lower() in BLOCKED_HOSTS:
            return False

        # Block internal domain patterns
        hostname_lower = hostname.lower()
        if any(pattern in hostname_lower for pattern in [
            'internal', 'intranet', 'local', 'private', 'corp'
        ]):
            return False

        # Try to resolve hostname and check IP
        try:
            # First check if hostname is already an IP
            ip = ipaddress.ip_address(hostname)
        except ValueError:
            # Not an IP, try DNS resolution
            try:
                resolved = socket.gethostbyname(hostname)
                ip = ipaddress.ip_address(resolved)
            except socket.gaierror:
                # Can't resolve - allow (might be valid external domain)
                return True

        # Block private, loopback, link-local, and reserved IPs
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return False

        return True

    except Exception as e:
        logger.warning("URL validation error", url=url, error=str(e))
        return False


class AISourceDiscoveryService:
    """
    KI-gesteuerter Datenquellen-Discovery Service.

    Workflow:
    1. KI generiert Suchstrategie aus Prompt
    2. Web-Suche nach relevanten Listen/APIs
    3. Extraktion der Datenquellen aus gefundenen Seiten
    4. Tag-Generierung für jede Quelle
    5. Deduplizierung und Validierung
    """

    def __init__(self):
        self.search_provider = SerperSearchProvider()
        self.extractors = [
            WikipediaExtractor(),
            HTMLTableExtractor(),
            AIExtractor(),
        ]

    async def discover_sources(
        self,
        prompt: str,
        max_results: int = 50,
        search_depth: str = "standard",  # quick, standard, deep
    ) -> DiscoveryResult:
        """
        Main method: Find data sources based on natural language prompt.

        Args:
            prompt: Natural language prompt (e.g., "Alle Bundesliga-Vereine")
            max_results: Maximum number of sources to return
            search_depth: quick (3 queries), standard (5), deep (8)

        Returns:
            DiscoveryResult with found sources and statistics
        """
        stats = DiscoveryStats()
        warnings = []

        # Step 1: Generate search strategy
        logger.info("Generating search strategy", prompt=prompt)
        try:
            strategy = await self._generate_search_strategy(prompt)
        except Exception as e:
            logger.error("Failed to generate search strategy", error=str(e))
            return DiscoveryResult(
                sources=[],
                search_strategy=None,
                stats=stats,
                warnings=[f"Suchstrategie konnte nicht generiert werden: {str(e)}"],
            )

        # Adjust query count based on depth
        query_counts = {"quick": 3, "standard": 5, "deep": 8}
        queries = strategy.search_queries[: query_counts.get(search_depth, 5)]

        # Step 2: Search the web
        logger.info("Searching web", queries=queries)
        search_results = await self.search_provider.search(
            queries=queries,
            num_results=10 if search_depth != "deep" else 15,
        )
        stats.pages_searched = len(search_results)

        if not search_results:
            warnings.append("Keine Suchergebnisse gefunden")
            return DiscoveryResult(
                sources=[],
                search_strategy=strategy,
                stats=stats,
                warnings=warnings,
            )

        # Step 3: Extract sources from found pages
        logger.info("Extracting sources from pages", count=len(search_results))
        extracted_sources = await self._extract_from_pages(search_results, strategy)
        stats.sources_extracted = len(extracted_sources)

        if not extracted_sources:
            warnings.append("Keine Datenquellen aus Suchergebnissen extrahiert")
            return DiscoveryResult(
                sources=[],
                search_strategy=strategy,
                stats=stats,
                warnings=warnings,
            )

        # Step 4: Deduplicate
        unique_sources = self._deduplicate_sources(extracted_sources)
        stats.duplicates_removed = len(extracted_sources) - len(unique_sources)

        # Step 5: Generate tags
        logger.info("Generating tags", count=len(unique_sources))
        sources_with_tags = await self._generate_tags(
            unique_sources,
            prompt,
            strategy,
        )

        # Limit results
        sources_with_tags = sources_with_tags[:max_results]
        stats.sources_validated = len(sources_with_tags)

        logger.info(
            "Discovery completed",
            prompt=prompt,
            total_sources=len(sources_with_tags),
            stats=stats.model_dump(),
        )

        return DiscoveryResult(
            sources=sources_with_tags,
            search_strategy=strategy,
            stats=stats,
            warnings=warnings,
        )

    async def _generate_search_strategy(self, prompt: str) -> SearchStrategy:
        """Generate search strategy using LLM with caching."""
        # Check cache first
        cache_key = f"strategy:{make_cache_key(prompt)}"
        cached = search_strategy_cache.get(cache_key)
        if cached is not None:
            logger.debug("Using cached search strategy", prompt=prompt)
            return SearchStrategy(**cached)

        try:
            client = get_openai_client()
        except ValueError:
            # Fallback strategy without LLM
            logger.warning("OpenAI not configured, using fallback strategy")
            strategy = SearchStrategy(
                search_queries=[prompt, f"{prompt} Liste", f"{prompt} Wikipedia"],
                expected_data_type="organizations",
                preferred_sources=["wikipedia", "official"],
                entity_schema={"name": "string", "website": "url"},
                base_tags=self._extract_base_tags(prompt),
            )
            # Cache fallback strategy too
            search_strategy_cache.set(cache_key, strategy.model_dump())
            return strategy

        strategy_prompt = AI_SEARCH_STRATEGY_PROMPT.format(prompt=prompt)

        response = client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=[{"role": "user", "content": strategy_prompt}],
            temperature=0.5,
            max_tokens=1000,
        )

        content = response.choices[0].message.content.strip()
        content = clean_json_response(content)

        data = json.loads(content)

        strategy = SearchStrategy(
            search_queries=data.get("search_queries", [prompt]),
            expected_data_type=data.get("expected_data_type", "organizations"),
            preferred_sources=data.get("preferred_sources", ["wikipedia"]),
            entity_schema=data.get("entity_schema", {"name": "string", "website": "url"}),
            base_tags=data.get("base_tags", []),
        )

        # Cache the generated strategy
        search_strategy_cache.set(cache_key, strategy.model_dump())
        logger.debug("Cached search strategy", prompt=prompt)

        return strategy

    async def _extract_from_pages(
        self,
        search_results: List[SearchResult],
        strategy: SearchStrategy,
        max_concurrent: int = 5,
    ) -> List[ExtractedSource]:
        """
        Extract data sources from found pages.

        Uses parallel HTTP requests with concurrency limiting for performance.
        Includes SSRF protection to prevent access to internal resources.

        Args:
            search_results: List of search results to process
            strategy: Search strategy with extraction configuration
            max_concurrent: Maximum number of concurrent HTTP requests

        Returns:
            List of extracted sources from all pages
        """
        all_sources: List[ExtractedSource] = []
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_and_extract(result: SearchResult) -> List[ExtractedSource]:
            """Fetch a single page and extract sources."""
            sources: List[ExtractedSource] = []

            # SSRF Protection: Validate URL before fetching
            if not is_safe_url(result.url):
                security_logger.log_ssrf_blocked(
                    user_id=None,  # User context not available here
                    url=result.url,
                    reason="URL failed safety validation (private IP or blocked hostname)",
                )
                return sources

            async with semaphore:
                try:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.get(
                            result.url,
                            follow_redirects=True,
                            headers={"User-Agent": "CaeliCrawler/1.0 (Data Discovery)"},
                        )

                        if response.status_code != 200:
                            return sources

                        # Validate final URL after redirects (SSRF check)
                        final_url = str(response.url)
                        if not is_safe_url(final_url):
                            security_logger.log_ssrf_redirect_blocked(
                                user_id=None,
                                original_url=result.url,
                                redirect_url=final_url,
                                reason="Redirect target failed safety validation",
                            )
                            return sources

                        content_type = response.headers.get("content-type", "")
                        html_content = response.text

                        # Try extractors in order of specificity
                        for extractor in self.extractors:
                            if await extractor.can_extract(result.url, content_type):
                                extracted = await extractor.extract(
                                    result.url,
                                    html_content,
                                    strategy,
                                )
                                if extracted:
                                    sources.extend(extracted)
                                    logger.debug(
                                        "Extracted sources",
                                        url=result.url,
                                        extractor=extractor.__class__.__name__,
                                        count=len(extracted),
                                    )
                                    break  # Use first successful extractor

                except httpx.HTTPError as e:
                    logger.warning("Failed to fetch page", url=result.url, error=str(e))
                except Exception as e:
                    logger.warning("Error extracting from page", url=result.url, error=str(e))

            return sources

        # Execute all fetches in parallel with semaphore limiting
        results = await asyncio.gather(
            *[fetch_and_extract(result) for result in search_results],
            return_exceptions=True,
        )

        # Collect results, filtering out exceptions
        for result in results:
            if isinstance(result, list):
                all_sources.extend(result)
            elif isinstance(result, Exception):
                logger.warning("Extraction task failed", error=str(result))

        return all_sources

    def _deduplicate_sources(
        self,
        sources: List[ExtractedSource],
    ) -> List[ExtractedSource]:
        """Remove duplicate sources based on URL."""
        seen_urls = set()
        unique = []

        for source in sources:
            # Normalize URL for comparison
            normalized = self._normalize_url(source.base_url)
            if normalized not in seen_urls:
                seen_urls.add(normalized)
                unique.append(source)

        return unique

    async def _generate_tags(
        self,
        sources: List[ExtractedSource],
        prompt: str,
        strategy: SearchStrategy,
    ) -> List[SourceWithTags]:
        """Generate tags for each source using LLM."""
        if not sources:
            return []

        # Try LLM-based tag generation
        try:
            client = get_openai_client()
            source_tags = await self._generate_tags_with_llm(
                client, sources, prompt, strategy.base_tags
            )
        except (ValueError, Exception) as e:
            logger.warning("LLM tag generation failed, using fallback", error=str(e))
            source_tags = {}

        # Convert to SourceWithTags
        result = []
        for source in sources:
            additional_tags = source_tags.get(source.name, [])
            all_tags = list(set(strategy.base_tags + additional_tags))

            result.append(SourceWithTags(
                name=source.name,
                base_url=source.base_url,
                source_type=source.source_type,
                tags=all_tags,
                metadata=source.metadata,
                confidence=source.confidence,
            ))

        return result

    async def _generate_tags_with_llm(
        self,
        client,
        sources: List[ExtractedSource],
        prompt: str,
        base_tags: List[str],
    ) -> Dict[str, List[str]]:
        """Generate tags using LLM."""
        # Prepare sources summary
        sources_text = "\n".join(
            f"- {s.name}: {s.base_url}"
            for s in sources[:50]  # Limit to avoid token limits
        )

        tag_prompt = AI_TAG_GENERATION_PROMPT.format(
            prompt=prompt,
            base_tags=", ".join(base_tags),
            sources=sources_text,
        )

        response = client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=[{"role": "user", "content": tag_prompt}],
            temperature=0.3,
            max_tokens=2000,
        )

        content = response.choices[0].message.content.strip()
        content = clean_json_response(content)

        data = json.loads(content)
        return data.get("source_tags", {})

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication."""
        parsed = urlparse(url)
        # Remove www, trailing slashes, common tracking params
        domain = parsed.netloc.replace("www.", "")
        path = parsed.path.rstrip("/")
        return f"{domain}{path}".lower()

    def _extract_base_tags(self, prompt: str) -> List[str]:
        """Extract basic tags from prompt without LLM."""
        tags = []
        prompt_lower = prompt.lower()

        # Geographic tags
        geo_map = {
            "deutschland": "de",
            "deutsche": "de",
            "deutsch": "de",
            "germany": "de",
            "german": "de",
            "österreich": "at",
            "austria": "at",
            "schweiz": "ch",
            "nrw": "nrw",
            "bayern": "bayern",
            "berlin": "berlin",
        }
        for term, tag in geo_map.items():
            if term in prompt_lower:
                tags.append(tag)

        # Type tags
        type_map = {
            "gemeinde": "kommunal",
            "kommune": "kommunal",
            "stadt": "kommunal",
            "verein": "verein",
            "unternehmen": "unternehmen",
            "firma": "unternehmen",
            "universität": "bildung",
            "hochschule": "bildung",
        }
        for term, tag in type_map.items():
            if term in prompt_lower:
                tags.append(tag)

        return list(set(tags))
