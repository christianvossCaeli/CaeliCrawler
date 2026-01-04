"""Main AI Source Discovery Service."""

import asyncio
import ipaddress
import json
import socket
import time
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.cache import make_cache_key, search_strategy_cache
from app.core.security_logging import security_logger
from app.models.llm_usage import LLMProvider, LLMTaskType
from services.llm_usage_tracker import record_llm_usage
from services.smart_query.query_interpreter import get_openai_client
from services.smart_query.utils import clean_json_response


async def call_claude_api(prompt: str, max_tokens: int = 4000) -> str | None:
    """
    Call Claude API via Azure-hosted Anthropic endpoint.

    Args:
        prompt: The prompt to send to Claude
        max_tokens: Maximum tokens in response

    Returns:
        Response content or None on error
    """
    if not settings.anthropic_api_endpoint or not settings.anthropic_api_key:
        return None

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                settings.anthropic_api_endpoint,
                headers={
                    "api-key": settings.anthropic_api_key,
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": settings.anthropic_model,
                    "max_tokens": max_tokens,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                },
            )
            response.raise_for_status()
            data = response.json()

            # Extract content from Claude response
            if "content" in data and len(data["content"]) > 0:
                return data["content"][0].get("text", "")

            return None

    except httpx.HTTPError as e:
        structlog.get_logger().error(
            "Claude API request failed",
            error=str(e),
            status_code=getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None,
        )
        return None
    except Exception as e:
        structlog.get_logger().error("Claude API error", error=str(e))
        return None

if TYPE_CHECKING:
    pass

from .api_validator import validate_api_suggestions  # noqa: E402
from .extractors import AIExtractor, HTMLTableExtractor, WikipediaExtractor  # noqa: E402
from .models import (  # noqa: E402
    APISuggestion,
    APIValidationResult,
    DiscoveryResult,
    DiscoveryResultV2,
    DiscoveryStats,
    ExtractedSource,
    SearchResult,
    SearchStrategy,
    SourceWithTags,
    ValidatedAPISource,
)
from .prompts import (  # noqa: E402
    AI_API_SUGGESTION_PROMPT,
    AI_SEARCH_STRATEGY_PROMPT,
    AI_TAG_GENERATION_PROMPT,
)
from .search_providers import SerpAPISearchProvider, SerperSearchProvider  # noqa: E402

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
        return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved)

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

    def __init__(
        self,
        serpapi_key: str | None = None,
        serper_key: str | None = None,
    ):
        """Initialize the AI Source Discovery Service.

        Args:
            serpapi_key: SerpAPI API key for primary search. If None, SerpAPI is disabled.
            serper_key: Serper API key for fallback search. If None, Serper is disabled.

        Example usage with user credentials:
            from services.credentials_resolver import get_search_api_config

            search_config = await get_search_api_config(session, user_id)
            if search_config:
                api_type, api_key = search_config
                if api_type == "serpapi":
                    service = AISourceDiscoveryService(serpapi_key=api_key)
                else:
                    service = AISourceDiscoveryService(serper_key=api_key)
        """
        # Search providers with fallback chain: SerpAPI → Serper
        self.primary_search_provider = SerpAPISearchProvider(api_key=serpapi_key)
        self.fallback_search_provider = SerperSearchProvider(api_key=serper_key)
        self.extractors = [
            WikipediaExtractor(),
            HTMLTableExtractor(),
            AIExtractor(),
        ]

    async def _search_with_fallback(
        self,
        queries: list[str],
        num_results: int = 10,
    ) -> list[SearchResult]:
        """
        Execute web search with automatic fallback.

        Tries SerpAPI first, falls back to Serper.dev if:
        - SerpAPI returns no results
        - SerpAPI is rate-limited (HTTP 429)
        - SerpAPI key is not configured

        Args:
            queries: List of search queries
            num_results: Number of results per query

        Returns:
            List of SearchResult objects
        """
        # Try primary provider (SerpAPI)
        results = await self.primary_search_provider.search(
            queries=queries,
            num_results=num_results,
        )

        if results:
            logger.info(
                "Primary search provider succeeded",
                provider="SerpAPI",
                results_count=len(results),
            )
            return results

        # Fallback to Serper.dev
        logger.warning(
            "Primary search provider returned no results, trying fallback",
            primary="SerpAPI",
            fallback="Serper.dev",
        )

        results = await self.fallback_search_provider.search(
            queries=queries,
            num_results=num_results,
        )

        if results:
            logger.info(
                "Fallback search provider succeeded",
                provider="Serper.dev",
                results_count=len(results),
            )
        else:
            logger.error(
                "Both search providers returned no results",
                queries=queries,
            )

        return results

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

        # Step 2: Search the web (with automatic fallback)
        logger.info("Searching web", queries=queries)
        search_results = await self._search_with_fallback(
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

        start_time = time.time()
        response = client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=[{"role": "user", "content": strategy_prompt}],
            temperature=0.5,
            max_tokens=1000,
        )

        if response.usage:
            await record_llm_usage(
                provider=LLMProvider.AZURE_OPENAI,
                model=settings.azure_openai_deployment_name,
                task_type=LLMTaskType.DISCOVERY,
                task_name="_generate_search_strategy",
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                duration_ms=int((time.time() - start_time) * 1000),
                is_error=False,
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
            # Intelligente Quellenbegrenzung durch KI
            expected_entity_count=data.get("expected_entity_count", 50),
            recommended_max_sources=data.get("recommended_max_sources", 50),
            reasoning=data.get("reasoning", ""),
        )

        # Cache the generated strategy
        search_strategy_cache.set(cache_key, strategy.model_dump())
        logger.debug("Cached search strategy", prompt=prompt)

        return strategy

    async def _extract_from_pages(
        self,
        search_results: list[SearchResult],
        strategy: SearchStrategy,
        max_concurrent: int = 5,
    ) -> list[ExtractedSource]:
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
        all_sources: list[ExtractedSource] = []
        semaphore = asyncio.Semaphore(max_concurrent)

        async with httpx.AsyncClient(timeout=30.0) as client:
            async def fetch_and_extract(result: SearchResult) -> list[ExtractedSource]:
                """Fetch a single page and extract sources."""
                sources: list[ExtractedSource] = []

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
        sources: list[ExtractedSource],
    ) -> list[ExtractedSource]:
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
        sources: list[ExtractedSource],
        prompt: str,
        strategy: SearchStrategy,
    ) -> list[SourceWithTags]:
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
        sources: list[ExtractedSource],
        prompt: str,
        base_tags: list[str],
    ) -> dict[str, list[str]]:
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

        start_time = time.time()
        response = client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=[{"role": "user", "content": tag_prompt}],
            temperature=0.3,
            max_tokens=2000,
        )

        if response.usage:
            await record_llm_usage(
                provider=LLMProvider.AZURE_OPENAI,
                model=settings.azure_openai_deployment_name,
                task_type=LLMTaskType.DISCOVERY,
                task_name="_generate_tags_with_llm",
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                duration_ms=int((time.time() - start_time) * 1000),
                is_error=False,
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

    def _extract_base_tags(self, prompt: str) -> list[str]:
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

    # ================================================================
    # KI-FIRST DISCOVERY (V2)
    # ================================================================

    async def discover_sources_v2(
        self,
        prompt: str,
        max_results: int = 50,
        search_depth: str = "standard",
        skip_api_discovery: bool = False,
        db: AsyncSession | None = None,
    ) -> DiscoveryResultV2:
        """
        KI-First Discovery: Zuerst APIs via KI finden, dann SERP als Fallback.

        Flow:
        1. Gespeicherte Vorlagen prüfen (Keyword-Matching)
        2. KI generiert API-Vorschläge
        3. API-Vorschläge validieren
        4. Bei Erfolg → Daten direkt von API
        5. Bei Misserfolg → SERP Fallback

        Args:
            prompt: Natural language prompt
            max_results: Maximum number of sources to return
            search_depth: quick, standard, deep
            skip_api_discovery: If True, skip to SERP directly
            db: Optional database session for template lookup

        Returns:
            DiscoveryResultV2 with API sources and/or web sources
        """
        stats = DiscoveryStats()
        warnings: list[str] = []
        api_sources: list[ValidatedAPISource] = []
        api_suggestions: list[APISuggestion] = []
        api_validations: list[APIValidationResult] = []
        used_fallback = False
        from_template = False

        # Step 1: Check saved templates (Keyword-Matching)
        if db and not skip_api_discovery:
            template_suggestions = await self._check_saved_templates(db, prompt)
            if template_suggestions:
                logger.info(
                    "Found matching templates",
                    count=len(template_suggestions),
                    templates=[s.api_name for s in template_suggestions],
                )
                api_suggestions = template_suggestions
                from_template = True

        # Step 2: Generate API suggestions via LLM (only if no templates found)
        if not skip_api_discovery and not from_template:
            logger.info("Generating API suggestions via LLM", prompt=prompt)
            try:
                api_suggestions = await self._generate_api_suggestions(prompt)
                logger.info(
                    "Generated API suggestions",
                    count=len(api_suggestions),
                    apis=[s.api_name for s in api_suggestions],
                )
            except Exception as e:
                logger.warning("Failed to generate API suggestions", error=str(e))
                warnings.append(f"KI-API-Vorschläge konnten nicht generiert werden: {str(e)}")

        # Step 3: Validate API suggestions
        if api_suggestions:
            logger.info("Validating API suggestions", count=len(api_suggestions))
            api_validations = await validate_api_suggestions(api_suggestions)

            # Step 4: Extract data from valid APIs
            for validation in api_validations:
                if validation.is_valid and validation.item_count and validation.item_count > 0:
                    logger.info(
                        "Valid API found",
                        api_name=validation.suggestion.api_name,
                        items=validation.item_count,
                    )

                    # Fetch full data from API
                    extracted_items = await self._fetch_full_api_data(
                        validation.suggestion,
                        validation.field_mapping,
                        max_results,
                    )

                    # Generate tags for this API source
                    tags = self._extract_base_tags(prompt)
                    tags.append(validation.suggestion.api_type.lower())

                    api_sources.append(ValidatedAPISource(
                        api_suggestion=validation.suggestion,
                        validation=validation,
                        extracted_items=extracted_items,
                        tags=tags,
                    ))

        # Step 5: If no valid APIs found, fallback to SERP
        web_sources: list[SourceWithTags] = []
        search_strategy: SearchStrategy | None = None

        if not api_sources:
            logger.info("No valid APIs found, falling back to SERP")
            used_fallback = True

            # Use existing SERP-based discovery
            serp_result = await self.discover_sources(
                prompt=prompt,
                max_results=max_results,
                search_depth=search_depth,
            )
            web_sources = serp_result.sources
            search_strategy = serp_result.search_strategy
            stats = serp_result.stats
            warnings.extend(serp_result.warnings)
        else:
            # Calculate stats for API discovery
            stats.sources_extracted = sum(
                len(s.extracted_items) for s in api_sources
            )
            stats.sources_validated = len(api_sources)

        return DiscoveryResultV2(
            api_sources=api_sources,
            web_sources=web_sources,
            api_suggestions=api_suggestions,
            api_validations=api_validations,
            search_strategy=search_strategy,
            stats=stats,
            warnings=warnings,
            used_fallback=used_fallback,
            from_template=from_template,
        )

    async def _generate_api_suggestions(self, prompt: str) -> list[APISuggestion]:
        """
        Generate API suggestions using LLM.

        Uses Claude if configured (better API knowledge), falls back to OpenAI.

        Args:
            prompt: User's natural language prompt

        Returns:
            List of API suggestions
        """
        api_prompt = AI_API_SUGGESTION_PROMPT.format(prompt=prompt)
        content = None

        # Try Claude first if configured (better API knowledge)
        if settings.ai_discovery_use_claude and settings.anthropic_api_endpoint:
            logger.info("Using Claude for API suggestions", prompt=prompt[:100])
            claude_response = await call_claude_api(api_prompt, max_tokens=4000)
            if claude_response:
                content = clean_json_response(claude_response)
                logger.info("Claude API suggestions received", length=len(content))

        # Fall back to OpenAI if Claude not available or failed
        if content is None:
            try:
                client = get_openai_client()
                logger.info("Using OpenAI for API suggestions (Claude not available)")

                start_time = time.time()
                response = client.chat.completions.create(
                    model=settings.azure_openai_deployment_name,
                    messages=[{"role": "user", "content": api_prompt}],
                    temperature=0.3,
                    max_tokens=2000,
                )

                if response.usage:
                    await record_llm_usage(
                        provider=LLMProvider.AZURE_OPENAI,
                        model=settings.azure_openai_deployment_name,
                        task_type=LLMTaskType.DISCOVERY,
                        task_name="_generate_api_suggestions",
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens,
                        total_tokens=response.usage.total_tokens,
                        duration_ms=int((time.time() - start_time) * 1000),
                        is_error=False,
                    )

                content = response.choices[0].message.content.strip()
                content = clean_json_response(content)
            except ValueError:
                logger.warning("No LLM configured, cannot generate API suggestions")
                return []
            except Exception as e:
                logger.error("OpenAI API suggestions failed", error=str(e))
                return []

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse API suggestions JSON", error=str(e), content=content[:500])
            return []

        if not isinstance(data, list):
            logger.warning("API suggestions response is not a list", type=type(data))
            return []

        suggestions = []
        for item in data:
            try:
                suggestion = APISuggestion(
                    api_name=item.get("api_name", "Unknown"),
                    base_url=item.get("base_url", ""),
                    endpoint=item.get("endpoint", ""),
                    description=item.get("description", ""),
                    api_type=item.get("api_type", "REST"),
                    auth_required=item.get("auth_required", False),
                    confidence=item.get("confidence", 0.5),
                    expected_fields=item.get("expected_fields", []),
                    documentation_url=item.get("documentation_url"),
                )
                if suggestion.base_url and suggestion.endpoint:
                    suggestions.append(suggestion)
            except Exception as e:
                logger.warning("Failed to parse API suggestion", error=str(e), item=item)

        return suggestions

    async def _fetch_full_api_data(
        self,
        suggestion: APISuggestion,
        field_mapping: dict[str, str],
        max_items: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Fetch full data from a validated API.

        Args:
            suggestion: The validated API suggestion
            field_mapping: Detected field mapping
            max_items: Maximum items to fetch

        Returns:
            List of extracted items with normalized field names
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(
                    suggestion.full_url,
                    headers={
                        "User-Agent": "CaeliCrawler/1.0 (Data Import)",
                        "Accept": "application/json",
                    },
                )

                if response.status_code != 200:
                    logger.warning(
                        "API fetch failed",
                        api=suggestion.api_name,
                        status=response.status_code,
                    )
                    return []

                data = response.json()

                # Extract items from response
                items = self._extract_items_from_response(data)

                # Apply field mapping and limit
                normalized_items = []
                for item in items[:max_items]:
                    normalized = self._apply_field_mapping(item, field_mapping)
                    if normalized.get("name"):  # Must have a name
                        normalized_items.append(normalized)

                return normalized_items

        except Exception as e:
            logger.error(
                "Failed to fetch API data",
                api=suggestion.api_name,
                error=str(e),
            )
            return []

    def _extract_items_from_response(self, data: Any) -> list[dict]:
        """Extract list of items from API response."""
        # Direct array
        if isinstance(data, list):
            return data

        if not isinstance(data, dict):
            return []

        # Common wrapper fields
        wrapper_fields = [
            "data", "items", "results", "records", "entries",
            "teams", "matches", "bodies", "members", "list",
        ]

        for field in wrapper_fields:
            if field in data and isinstance(data[field], list):
                return data[field]

        # Check for any list field
        for _key, value in data.items():
            if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                return value

        return []

    def _apply_field_mapping(
        self,
        item: dict[str, Any],
        field_mapping: dict[str, str],
    ) -> dict[str, Any]:
        """Apply field mapping to normalize item fields."""
        normalized = {}

        # Apply explicit mapping
        for source_field, target_field in field_mapping.items():
            if source_field in item:
                normalized[target_field] = item[source_field]

        # Copy unmapped fields to metadata
        metadata = {}
        for key, value in item.items():
            if key not in field_mapping:
                metadata[key] = value

        if metadata:
            normalized["metadata"] = metadata

        return normalized

    async def _check_saved_templates(
        self,
        db: AsyncSession,
        prompt: str,
        min_match_score: float = 0.3,
    ) -> list[APISuggestion]:
        """
        Check saved API templates for keyword matches.

        Args:
            db: Database session
            prompt: User's search prompt
            min_match_score: Minimum match score (0.0-1.0) to include template

        Returns:
            List of APISuggestion objects from matching templates
        """
        from sqlalchemy.orm import selectinload

        from app.models.api_configuration import APIConfiguration

        try:
            # Get all active template configurations
            result = await db.execute(
                select(APIConfiguration)
                .options(selectinload(APIConfiguration.data_source))
                .where(
                    APIConfiguration.is_active,
                    APIConfiguration.is_template,
                )
            )
            configs = result.scalars().all()

            if not configs:
                return []

            # Score configurations against prompt
            matched_configs = []
            for config in configs:
                score = config.matches_prompt(prompt)
                if score >= min_match_score:
                    matched_configs.append((config, score))

            if not matched_configs:
                return []

            # Sort by score (highest first)
            matched_configs.sort(key=lambda x: x[1], reverse=True)

            # Convert configurations to APISuggestion objects
            suggestions = []
            for config, score in matched_configs:
                # Get name and base_url from associated data_source
                api_name = config.data_source.name if config.data_source else f"API {str(config.id)[:8]}"
                base_url = config.data_source.base_url if config.data_source else ""
                description = config.data_source.description if config.data_source else ""

                suggestion = APISuggestion(
                    api_name=api_name,
                    base_url=base_url,
                    endpoint=config.endpoint,
                    description=description,
                    api_type=config.api_type,
                    auth_required=config.auth_type != "none",
                    confidence=min(1.0, score + config.confidence * 0.5),  # Combine scores
                    expected_fields=list(config.field_mappings.keys()) if config.field_mappings else [],
                    documentation_url=config.documentation_url,
                )
                suggestions.append(suggestion)

            logger.info(
                "Template matching results",
                prompt=prompt,
                matched_count=len(suggestions),
                templates=[s.api_name for s in suggestions],
            )

            return suggestions

        except Exception as e:
            logger.warning("Failed to check saved templates", error=str(e))
            return []
