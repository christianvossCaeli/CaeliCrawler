"""AI-powered extractor using LLM for unstructured content."""

import json
from typing import List

import structlog

from app.config import settings
from services.smart_query.query_interpreter import get_openai_client
from services.smart_query.utils import clean_json_response
from .base import BaseExtractor
from ..models import ExtractedSource, SearchStrategy
from ..prompts import AI_EXTRACTION_PROMPT

logger = structlog.get_logger()


class AIExtractor(BaseExtractor):
    """Extract data sources using LLM for complex/unstructured content."""

    MAX_CONTENT_LENGTH = 15000  # Characters to send to LLM

    async def can_extract(self, url: str, content_type: str = None) -> bool:
        """AI extractor can be used as fallback for any content."""
        return True

    async def extract(
        self,
        url: str,
        html_content: str,
        strategy: SearchStrategy,
    ) -> List[ExtractedSource]:
        """Extract data using LLM analysis."""
        try:
            client = get_openai_client()
        except ValueError:
            logger.warning("OpenAI client not configured, skipping AI extraction")
            return []

        # Convert HTML to text
        text_content = self._html_to_text(html_content)

        # Truncate if too long
        if len(text_content) > self.MAX_CONTENT_LENGTH:
            text_content = text_content[: self.MAX_CONTENT_LENGTH] + "\n[...truncated...]"

        # Build prompt
        entity_schema = json.dumps(strategy.entity_schema, ensure_ascii=False)
        prompt = AI_EXTRACTION_PROMPT.format(
            entity_schema=entity_schema,
            content=text_content,
        )

        try:
            response = client.chat.completions.create(
                model=settings.azure_openai_deployment_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=4000,
            )

            content = response.choices[0].message.content.strip()
            content = clean_json_response(content)

            # Parse response
            extracted_items = json.loads(content)

            if not isinstance(extracted_items, list):
                logger.warning("AI extraction did not return a list", response=content[:200])
                return []

            sources = []
            for item in extracted_items:
                if not isinstance(item, dict):
                    continue

                name = item.get("name", "")
                website = item.get("website", "") or item.get("url", "") or item.get("base_url", "")

                if not name or not website:
                    continue

                # Normalize URL
                if website.startswith("www."):
                    website = f"https://{website}"

                if not website.startswith(("http://", "https://")):
                    continue

                # Extract additional metadata
                metadata = {k: v for k, v in item.items() if k not in ["name", "website", "url", "base_url"]}
                metadata["source"] = "ai_extraction"

                sources.append(ExtractedSource(
                    name=name,
                    base_url=website,
                    source_type="WEBSITE",
                    metadata=metadata,
                    extraction_method="ai",
                    confidence=0.75,
                ))

            logger.debug(
                "AI extraction completed",
                url=url,
                sources_extracted=len(sources),
            )

            return sources

        except json.JSONDecodeError as e:
            logger.error("Failed to parse AI extraction response", error=str(e))
            return []
        except Exception as e:
            logger.error("AI extraction failed", url=url, error=str(e))
            return []

    def _html_to_text(self, html_content: str) -> str:
        """Convert HTML to plain text."""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html_content, "html.parser")

            # Remove script, style, nav, footer elements
            for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                element.decompose()

            # Get text
            text = soup.get_text(separator="\n")

            # Clean up whitespace
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            return "\n".join(lines)

        except ImportError:
            # Fallback: basic tag removal
            import re
            text = re.sub(r"<[^>]+>", " ", html_content)
            text = re.sub(r"\s+", " ", text)
            return text.strip()
