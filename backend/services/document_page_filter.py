"""
Document page filter for efficient LLM cost reduction.

Filters document pages by keyword relevance before sending to LLM,
similar to how website crawling filters HTML pages.
"""

from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF
import structlog
from bs4 import BeautifulSoup

from app.models.category import Category
from services.relevance_checker import RelevanceChecker, RelevanceResult

logger = structlog.get_logger(service="document_page_filter")


@dataclass
class PageData:
    """Data for a single document page."""

    page_number: int  # 1-indexed
    text: str
    char_count: int
    relevance_result: RelevanceResult | None = None

    @property
    def score(self) -> float:
        """Get relevance score (0.0 if not checked)."""
        return self.relevance_result.score if self.relevance_result else 0.0

    @property
    def is_relevant(self) -> bool:
        """Check if page is relevant."""
        return self.relevance_result.is_relevant if self.relevance_result else False

    @property
    def matched_keywords(self) -> list[str]:
        """Get matched keywords."""
        return self.relevance_result.matched_keywords if self.relevance_result else []


@dataclass
class PageFilterResult:
    """Result of page filtering operation."""

    relevant_pages: list[PageData]  # Pages with keyword matches (sorted by score)
    total_pages: int  # Total page count in document
    total_relevant: int  # Total count of pages with keyword matches
    has_more: bool  # More relevant pages than max_pages?
    status: str  # "ready", "needs_review", "has_more"
    all_pages: list[PageData] = field(default_factory=list)  # All pages with text

    @property
    def page_numbers(self) -> list[int]:
        """Get list of relevant page numbers."""
        return [p.page_number for p in self.relevant_pages]

    @property
    def combined_text(self) -> str:
        """Get combined text from relevant pages with page markers."""
        parts = []
        for page in self.relevant_pages:
            parts.append(f"--- Seite {page.page_number} ---\n{page.text}")
        return "\n\n".join(parts)

    def get_note(self) -> str | None:
        """Generate user-facing note based on status."""
        if self.status == "needs_review":
            return "Keine Schlagwörter gefunden - manuelle Analyse erforderlich"
        elif self.status == "has_more":
            remaining = self.total_relevant - len(self.relevant_pages)
            return f"{remaining} weitere relevante Seiten verfügbar"
        return None


class DocumentPageFilter:
    """
    Filters document pages by keyword relevance.

    Uses the existing RelevanceChecker to check each page for keywords,
    then returns only the most relevant pages for LLM analysis.
    """

    DEFAULT_MAX_PAGES = 10

    def __init__(self, relevance_checker: RelevanceChecker):
        """
        Initialize with a relevance checker.

        Args:
            relevance_checker: RelevanceChecker instance (usually from category)
        """
        self.checker = relevance_checker
        self.logger = logger

    @classmethod
    def from_category(cls, category: Category | None) -> "DocumentPageFilter":
        """Create a DocumentPageFilter from a Category."""
        checker = RelevanceChecker.from_category(category)
        return cls(checker)

    def extract_pdf_pages(self, file_path: Path) -> list[PageData]:
        """
        Extract text from each page of a PDF.

        Args:
            file_path: Path to PDF file

        Returns:
            List of PageData for each page
        """
        pages = []
        try:
            with fitz.open(file_path) as doc:
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    text = page.get_text()
                    pages.append(
                        PageData(
                            page_number=page_num + 1,  # 1-indexed
                            text=text,
                            char_count=len(text),
                        )
                    )
        except Exception as e:
            self.logger.error("pdf_extraction_failed", path=str(file_path), error=str(e))
            raise

        return pages

    def extract_html_sections(self, file_path: Path) -> list[PageData]:
        """
        Extract sections from an HTML file.

        For HTML, we treat the whole document as one "page" since
        HTML doesn't have page structure. The filtering still works
        because we're just checking for keywords.

        Args:
            file_path: Path to HTML file

        Returns:
            List with single PageData (HTML = 1 section)
        """
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()

            soup = BeautifulSoup(content, "html.parser")

            # Remove non-content elements
            for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                element.decompose()

            text = soup.get_text(separator="\n", strip=True)

            return [
                PageData(
                    page_number=1,
                    text=text,
                    char_count=len(text),
                )
            ]
        except Exception as e:
            self.logger.error("html_extraction_failed", path=str(file_path), error=str(e))
            raise

    def extract_pages(self, file_path: Path, content_type: str) -> list[PageData]:
        """
        Extract pages/sections from a document.

        Args:
            file_path: Path to document
            content_type: MIME type of document

        Returns:
            List of PageData
        """
        if content_type == "application/pdf":
            return self.extract_pdf_pages(file_path)
        elif content_type.startswith("text/html"):
            return self.extract_html_sections(file_path)
        else:
            # For other types, treat as single page with raw text
            try:
                with open(file_path, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                return [
                    PageData(
                        page_number=1,
                        text=text,
                        char_count=len(text),
                    )
                ]
            except Exception as e:
                self.logger.error(
                    "text_extraction_failed",
                    path=str(file_path),
                    content_type=content_type,
                    error=str(e),
                )
                raise

    def check_page_relevance(self, page: PageData, title: str | None = None) -> PageData:
        """
        Check relevance of a single page.

        Args:
            page: PageData to check
            title: Optional document title (used for relevance scoring)

        Returns:
            PageData with relevance_result populated
        """
        result = self.checker.check(page.text, title=title)
        page.relevance_result = result
        return page

    def filter_relevant_pages(
        self,
        pages: list[PageData],
        title: str | None = None,
        max_pages: int = DEFAULT_MAX_PAGES,
    ) -> PageFilterResult:
        """
        Filter pages by keyword relevance.

        Args:
            pages: List of PageData to filter
            title: Optional document title
            max_pages: Maximum number of pages to return (default: 10, max: 100)

        Returns:
            PageFilterResult with filtered pages and metadata

        Raises:
            ValueError: If max_pages is invalid
        """
        # Input validation
        if not isinstance(max_pages, int) or max_pages < 1:
            raise ValueError("max_pages must be a positive integer")
        if max_pages > 100:
            self.logger.warning(
                "max_pages capped to 100",
                requested=max_pages,
            )
            max_pages = 100

        if not pages:
            return PageFilterResult(
                relevant_pages=[],
                total_pages=0,
                total_relevant=0,
                has_more=False,
                status="needs_review",
                all_pages=[],
            )

        # Check relevance for each page
        for page in pages:
            self.check_page_relevance(page, title=title)

        # Filter relevant pages
        relevant = [p for p in pages if p.is_relevant]

        # Sort by score (highest first)
        relevant.sort(key=lambda p: p.score, reverse=True)

        total_relevant = len(relevant)
        has_more = total_relevant > max_pages

        # Determine status
        if total_relevant == 0:
            status = "needs_review"
        elif has_more:
            status = "has_more"
        else:
            status = "ready"

        # Limit to max_pages
        limited_relevant = relevant[:max_pages]

        self.logger.info(
            "page_filter_result",
            total_pages=len(pages),
            total_relevant=total_relevant,
            returned_pages=len(limited_relevant),
            status=status,
        )

        return PageFilterResult(
            relevant_pages=limited_relevant,
            total_pages=len(pages),
            total_relevant=total_relevant,
            has_more=has_more,
            status=status,
            all_pages=pages,
        )

    def filter_document(
        self,
        file_path: Path,
        content_type: str,
        title: str | None = None,
        max_pages: int = DEFAULT_MAX_PAGES,
    ) -> PageFilterResult:
        """
        Extract and filter pages from a document file.

        Convenience method that combines extraction and filtering.

        Args:
            file_path: Path to document
            content_type: MIME type
            title: Optional document title
            max_pages: Maximum pages to return

        Returns:
            PageFilterResult
        """
        pages = self.extract_pages(file_path, content_type)
        return self.filter_relevant_pages(pages, title=title, max_pages=max_pages)

    def get_remaining_pages(
        self,
        all_pages: list[PageData],
        analyzed_pages: list[int],
        max_pages: int = DEFAULT_MAX_PAGES,
    ) -> list[PageData]:
        """
        Get relevant pages that haven't been analyzed yet.

        Used for incremental analysis when user requests more pages.

        Args:
            all_pages: All pages with relevance info
            analyzed_pages: List of page numbers already analyzed
            max_pages: Maximum pages to return

        Returns:
            List of PageData for pages to analyze next
        """
        # Filter to relevant pages not yet analyzed
        remaining = [p for p in all_pages if p.is_relevant and p.page_number not in analyzed_pages]

        # Sort by score
        remaining.sort(key=lambda p: p.score, reverse=True)

        return remaining[:max_pages]
