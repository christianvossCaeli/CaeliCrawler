"""Robots.txt parser and checker for ethical web crawling.

This module provides robots.txt compliance for the web crawler, ensuring
that we respect website owners' crawling preferences.

Features:
- Parses robots.txt files according to the Robots Exclusion Standard
- Caches parsed rules per domain to minimize requests
- Handles common robots.txt variations and edge cases
- Respects Crawl-delay directives
- Supports wildcard patterns in Disallow rules
"""

import asyncio
import contextlib
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from urllib.parse import urljoin, urlparse

import httpx
import structlog

logger = structlog.get_logger()


@dataclass
class RobotsRule:
    """A single robots.txt rule (Allow or Disallow)."""
    path: str
    allow: bool  # True for Allow, False for Disallow
    pattern: re.Pattern | None = None

    def __post_init__(self):
        """Compile the path pattern for matching."""
        # Convert robots.txt wildcards to regex
        # * matches any sequence of characters
        # $ anchors to end of URL
        regex_path = re.escape(self.path)
        regex_path = regex_path.replace(r"\*", ".*")
        regex_path = regex_path[:-2] + "$" if regex_path.endswith(r"\$") else regex_path + ".*"
        self.pattern = re.compile(regex_path)

    def matches(self, path: str) -> bool:
        """Check if this rule matches the given path."""
        return self.pattern.match(path) is not None


@dataclass
class RobotsDirectives:
    """Parsed robots.txt directives for a user-agent."""
    rules: list[RobotsRule] = field(default_factory=list)
    crawl_delay: float | None = None
    sitemaps: list[str] = field(default_factory=list)

    def is_allowed(self, path: str) -> bool:
        """Check if crawling the given path is allowed.

        Rules are evaluated in order of specificity (longest match wins).
        If no rules match, crawling is allowed by default.
        """
        # Find the most specific matching rule
        best_match: RobotsRule | None = None
        best_length = -1

        for rule in self.rules:
            if rule.matches(path):
                # More specific rules (longer path) take precedence
                rule_length = len(rule.path.rstrip("*$"))
                if rule_length > best_length:
                    best_length = rule_length
                    best_match = rule

        # If no rule matches, allow by default
        if best_match is None:
            return True

        return best_match.allow


@dataclass
class RobotsCache:
    """Cached robots.txt data for a domain."""
    directives: RobotsDirectives
    fetched_at: datetime
    expires_at: datetime
    fetch_failed: bool = False


class RobotsTxtChecker:
    """
    Checks URLs against robots.txt rules.

    Usage:
        checker = RobotsTxtChecker(user_agent="MyCrawler/1.0")

        # Check if URL is allowed
        if await checker.can_fetch("https://example.com/page"):
            # OK to crawl
            pass

        # Get recommended crawl delay
        delay = await checker.get_crawl_delay("https://example.com")
    """

    # Cache expiration time
    CACHE_TTL_SECONDS = 3600  # 1 hour

    # Timeout for fetching robots.txt
    FETCH_TIMEOUT = 10.0

    # Default crawl delay if none specified
    DEFAULT_CRAWL_DELAY = 1.0

    def __init__(
        self,
        user_agent: str = "CaeliCrawler/1.0",
        respect_robots: bool = True,
    ):
        """
        Initialize the robots.txt checker.

        Args:
            user_agent: The user agent string to match in robots.txt
            respect_robots: If False, skip robots.txt checks entirely
        """
        self.user_agent = user_agent
        self.respect_robots = respect_robots
        self._cache: dict[str, RobotsCache] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self.logger = logger.bind(component="RobotsTxtChecker")

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    async def _get_lock(self, domain: str) -> asyncio.Lock:
        """Get or create a lock for a domain."""
        if domain not in self._locks:
            self._locks[domain] = asyncio.Lock()
        return self._locks[domain]

    def _is_cache_valid(self, domain: str) -> bool:
        """Check if cached robots.txt is still valid."""
        if domain not in self._cache:
            return False
        cache_entry = self._cache[domain]
        return datetime.now(UTC) < cache_entry.expires_at

    def _parse_robots_txt(self, content: str) -> RobotsDirectives:
        """
        Parse robots.txt content into directives.

        Handles:
        - User-agent matching (including wildcards)
        - Allow and Disallow rules
        - Crawl-delay directive
        - Sitemap directive
        """
        directives = RobotsDirectives()
        current_agents: list[str] = []
        in_matching_block = False

        lines = content.strip().split("\n")

        for line in lines:
            # Remove comments
            line = line.split("#")[0].strip()
            if not line:
                continue

            # Parse directive
            if ":" not in line:
                continue

            key, value = line.split(":", 1)
            key = key.strip().lower()
            value = value.strip()

            if key == "user-agent":
                # Start of a new user-agent block
                if current_agents and in_matching_block:
                    # We were in a matching block, now starting a new one
                    # Keep the rules we collected
                    pass
                current_agents = [value.lower()]
                # Check if this agent matches us
                in_matching_block = self._matches_user_agent(value)

            elif key == "disallow" and in_matching_block:
                if value:  # Empty Disallow means allow all
                    directives.rules.append(RobotsRule(path=value, allow=False))

            elif key == "allow" and in_matching_block:
                if value:
                    directives.rules.append(RobotsRule(path=value, allow=True))

            elif key == "crawl-delay" and in_matching_block:
                with contextlib.suppress(ValueError):
                    directives.crawl_delay = float(value)

            elif key == "sitemap":
                directives.sitemaps.append(value)

        return directives

    def _matches_user_agent(self, agent: str) -> bool:
        """Check if a User-agent directive matches our user agent."""
        agent = agent.lower().strip()

        # Wildcard matches all
        if agent == "*":
            return True

        # Check if our user agent contains the directive value
        # This is more lenient than strict matching
        our_agent = self.user_agent.lower()
        return agent in our_agent or our_agent.startswith(agent)

    async def _fetch_robots_txt(self, domain: str) -> str | None:
        """Fetch robots.txt from a domain."""
        robots_url = urljoin(domain, "/robots.txt")

        try:
            async with httpx.AsyncClient(timeout=self.FETCH_TIMEOUT) as client:
                response = await client.get(robots_url)

                if response.status_code == 200:
                    return response.text
                elif response.status_code in (403, 404):
                    # No robots.txt or access denied - allow all
                    return None
                else:
                    self.logger.warning(
                        "robots_txt_fetch_failed",
                        url=robots_url,
                        status=response.status_code,
                    )
                    return None

        except Exception as e:
            self.logger.warning(
                "robots_txt_fetch_error",
                url=robots_url,
                error=str(e),
            )
            return None

    async def _ensure_loaded(self, domain: str) -> RobotsDirectives:
        """Ensure robots.txt for domain is loaded and cached."""
        # Check cache first (without lock for performance)
        if self._is_cache_valid(domain):
            return self._cache[domain].directives

        # Acquire lock for this domain to prevent duplicate fetches
        lock = await self._get_lock(domain)
        async with lock:
            # Double-check cache after acquiring lock
            if self._is_cache_valid(domain):
                return self._cache[domain].directives

            # Fetch and parse
            now = datetime.now(UTC)
            expires = now + timedelta(seconds=self.CACHE_TTL_SECONDS)

            content = await self._fetch_robots_txt(domain)

            if content is None:
                # No robots.txt - create empty directives (allow all)
                directives = RobotsDirectives()
                self._cache[domain] = RobotsCache(
                    directives=directives,
                    fetched_at=now,
                    expires_at=expires,
                    fetch_failed=True,
                )
            else:
                directives = self._parse_robots_txt(content)
                self._cache[domain] = RobotsCache(
                    directives=directives,
                    fetched_at=now,
                    expires_at=expires,
                )
                self.logger.info(
                    "robots_txt_loaded",
                    domain=domain,
                    rules_count=len(directives.rules),
                    crawl_delay=directives.crawl_delay,
                )

            return directives

    async def can_fetch(self, url: str) -> bool:
        """
        Check if the URL can be fetched according to robots.txt.

        Args:
            url: Full URL to check

        Returns:
            True if crawling is allowed, False otherwise
        """
        if not self.respect_robots:
            return True

        try:
            domain = self._get_domain(url)
            path = urlparse(url).path or "/"

            directives = await self._ensure_loaded(domain)
            allowed = directives.is_allowed(path)

            if not allowed:
                self.logger.debug(
                    "url_blocked_by_robots",
                    url=url,
                    path=path,
                )

            return allowed

        except Exception as e:
            self.logger.error(
                "robots_check_error",
                url=url,
                error=str(e),
            )
            # On error, allow the fetch (fail open)
            return True

    async def get_crawl_delay(self, url: str) -> float:
        """
        Get the recommended crawl delay for a domain.

        Args:
            url: URL to get crawl delay for

        Returns:
            Crawl delay in seconds
        """
        if not self.respect_robots:
            return self.DEFAULT_CRAWL_DELAY

        try:
            domain = self._get_domain(url)
            directives = await self._ensure_loaded(domain)

            if directives.crawl_delay is not None:
                return directives.crawl_delay
            return self.DEFAULT_CRAWL_DELAY

        except Exception:
            return self.DEFAULT_CRAWL_DELAY

    def clear_cache(self):
        """Clear the robots.txt cache."""
        self._cache.clear()

    def get_cache_stats(self) -> dict[str, int]:
        """Get cache statistics."""
        now = datetime.now(UTC)
        valid = sum(1 for c in self._cache.values() if now < c.expires_at)
        return {
            "total_entries": len(self._cache),
            "valid_entries": valid,
            "expired_entries": len(self._cache) - valid,
        }
