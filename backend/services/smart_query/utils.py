"""Utility functions for Smart Query Service."""

import re
import unicodedata


def generate_slug(name: str) -> str:
    """Generate a URL-safe slug from a name."""
    # Normalize unicode characters
    normalized = unicodedata.normalize("NFKD", name)
    # Convert to ASCII
    ascii_str = normalized.encode("ascii", "ignore").decode("ascii")
    # Convert to lowercase and replace spaces/special chars
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_str.lower())
    # Remove leading/trailing hyphens
    return slug.strip("-")


def clean_json_response(content: str) -> str:
    """Clean up markdown code blocks from AI response."""
    if "```" in content:
        # Extract content between ``` markers
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
        if match:  # noqa: SIM108
            content = match.group(1)
        else:
            # Fallback: remove leading ```json and trailing ```
            content = content.replace("```json", "").replace("```", "")
    return content.strip()
