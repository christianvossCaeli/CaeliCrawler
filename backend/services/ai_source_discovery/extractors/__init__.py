"""Extractors for AI Source Discovery."""

from .base import BaseExtractor
from .html_table_extractor import HTMLTableExtractor
from .wikipedia_extractor import WikipediaExtractor
from .ai_extractor import AIExtractor

__all__ = [
    "BaseExtractor",
    "HTMLTableExtractor",
    "WikipediaExtractor",
    "AIExtractor",
]
