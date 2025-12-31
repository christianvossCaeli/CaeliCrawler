"""Base class for content extractors."""

from abc import ABC, abstractmethod
from urllib.parse import urljoin, urlparse

from ..models import ExtractedSource, SearchStrategy


class BaseExtractor(ABC):
    """Abstract base class for content extractors."""

    @abstractmethod
    async def can_extract(self, url: str, content_type: str = None) -> bool:
        """
        Check if this extractor can handle the given URL/content.

        Args:
            url: URL of the page
            content_type: Optional content type header

        Returns:
            True if extractor can handle this content
        """
        pass

    @abstractmethod
    async def extract(
        self,
        url: str,
        html_content: str,
        strategy: SearchStrategy,
    ) -> list[ExtractedSource]:
        """
        Extract data sources from the content.

        Args:
            url: URL of the page
            html_content: HTML content of the page
            strategy: Search strategy with expected schema

        Returns:
            List of ExtractedSource objects
        """
        pass

    def _normalize_url(self, url: str, base_url: str) -> str:
        """Normalize a URL, making it absolute if relative."""
        if not url:
            return ""

        # Already absolute
        if url.startswith(("http://", "https://")):
            return url

        # Protocol-relative
        if url.startswith("//"):
            return f"https:{url}"

        # Relative URL
        return urljoin(base_url, url)

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return ""

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and not internal/anchor."""
        if not url:
            return False

        # Skip anchors, javascript, mailto, tel
        if url.startswith(("#", "javascript:", "mailto:", "tel:")):
            return False

        # Must be HTTP(S)
        return bool(url.startswith(("http://", "https://")))

    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        if not text:
            return ""

        # Remove extra whitespace
        import re
        text = re.sub(r"\s+", " ", text)
        return text.strip()
