"""Extractors for AI Source Discovery."""

from .ai_extractor import AIExtractor
from .base import BaseExtractor
from .html_table_extractor import HTMLTableExtractor
from .wikipedia_extractor import WikipediaExtractor

__all__ = [
    "BaseExtractor",
    "HTMLTableExtractor",
    "WikipediaExtractor",
    "AIExtractor",
]
