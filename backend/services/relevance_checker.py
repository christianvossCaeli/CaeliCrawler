"""Relevance checker service for pre-filtering documents before AI analysis."""

import re
from dataclasses import dataclass

import structlog

logger = structlog.get_logger()


@dataclass
class RelevanceResult:
    """Result of a relevance check."""

    is_relevant: bool
    score: float  # 0.0 to 1.0
    matched_keywords: list[str]
    reason: str


class RelevanceChecker:
    """
    Quick relevance pre-filter for documents before expensive AI analysis.

    Uses keyword matching from category search_terms to determine if a document
    is worth sending to AI for full analysis. This saves API tokens and processing
    time for clearly irrelevant documents.
    """

    # Default wind energy keywords (used when category has no search_terms)
    DEFAULT_WIND_KEYWORDS = [
        # Core wind energy terms
        "windkraft",
        "windenergie",
        "windpark",
        "windrad",
        "windenergieanlage",
        "wea",
        "repowering",
        # Planning/Regulatory
        "flächennutzungsplan",
        "bebauungsplan",
        "regionalplan",
        "raumordnung",
        "bauleitplanung",
        "teilflächennutzungsplan",
        # Restrictions/Regulations
        "höhenbegrenzung",
        "abstandsfläche",
        "abstandsregelung",
        "privilegierung",
        "§35",
        "§ 35",
        "außenbereich",
        # Permits/Legal
        "baurecht",
        "genehmigung",
        "baugenehmigung",
        "immissionsschutz",
        "bimschg",
        # Environmental
        "schallschutz",
        "artenschutz",
        "vogelschutz",
        "naturschutz",
        "umweltverträglichkeit",
        "uvp",
        # Technical
        "rotor",
        "nabenhöhe",
        "gesamthöhe",
        "megawatt",
        "mw",
    ]

    def __init__(self, keywords: list[str] | None = None, min_keywords: int = 2):
        """
        Initialize the relevance checker.

        Args:
            keywords: List of keywords to check for. If None, uses DEFAULT_WIND_KEYWORDS.
            min_keywords: Minimum number of keyword matches to consider relevant.
        """
        self.keywords = keywords or self.DEFAULT_WIND_KEYWORDS
        self.min_keywords = min_keywords
        self.logger = structlog.get_logger(service="relevance_checker")

        # Pre-compile patterns for efficient matching
        self._patterns = [re.compile(r"\b" + re.escape(kw.lower()) + r"\b", re.IGNORECASE) for kw in self.keywords]

    @classmethod
    def from_category(cls, category) -> "RelevanceChecker":
        """
        Create a RelevanceChecker from a Category model.

        Uses the category's search_terms if available, otherwise falls back to defaults.
        """
        keywords = None
        if category and hasattr(category, "search_terms") and category.search_terms:
            keywords = category.search_terms
        return cls(keywords=keywords)

    def check(self, text: str, title: str | None = None) -> RelevanceResult:
        """
        Check if text content is relevant based on keyword matching.

        Args:
            text: The main text content to analyze
            title: Optional title (given higher weight)

        Returns:
            RelevanceResult with relevance assessment
        """
        if not text:
            return RelevanceResult(
                is_relevant=False,
                score=0.0,
                matched_keywords=[],
                reason="empty_content",
            )

        # Combine title and text, give title matches more weight
        combined_text = text.lower()
        title_text = (title or "").lower()

        matched_keywords = []
        title_matches = 0
        body_matches = 0

        for i, pattern in enumerate(self._patterns):
            keyword = self.keywords[i]

            # Check title
            if title_text and pattern.search(title_text):
                matched_keywords.append(keyword)
                title_matches += 1

            # Check body (only if not already matched in title)
            elif pattern.search(combined_text):
                matched_keywords.append(keyword)
                body_matches += 1

        # Calculate score: title matches worth 2x, body matches worth 1x
        weighted_matches = (title_matches * 2) + body_matches
        max_score_matches = 10  # 10+ weighted matches = 100%
        score = min(weighted_matches / max_score_matches, 1.0)

        # Determine relevance
        total_unique_matches = len(matched_keywords)
        is_relevant = total_unique_matches >= self.min_keywords

        # Determine reason
        if is_relevant:
            reason = f"matched_{total_unique_matches}_keywords"
        elif total_unique_matches > 0:
            reason = f"insufficient_matches_{total_unique_matches}_of_{self.min_keywords}"
        else:
            reason = "no_keyword_matches"

        return RelevanceResult(
            is_relevant=is_relevant,
            score=score,
            matched_keywords=matched_keywords,
            reason=reason,
        )

    def quick_check(self, text: str) -> tuple[bool, float]:
        """
        Simplified check returning just (is_relevant, score).

        Convenience method for use in filtering pipelines.
        """
        result = self.check(text)
        return result.is_relevant, result.score


# Module-level instance with default settings
default_checker = RelevanceChecker()


def check_relevance(
    text: str,
    title: str | None = None,
    category=None,
) -> RelevanceResult:
    """
    Check content relevance using category-specific or default keywords.

    Args:
        text: Document text content
        title: Optional document title
        category: Optional Category model for category-specific keywords

    Returns:
        RelevanceResult with is_relevant, score, matched_keywords, reason
    """
    checker = RelevanceChecker.from_category(category) if category else default_checker

    return checker.check(text, title)
