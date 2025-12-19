"""AI-powered generation functions for Smart Query Service."""

import json
import os
from typing import Any, Dict, List

import structlog

from .prompts import AI_ENTITY_TYPE_PROMPT, AI_CATEGORY_PROMPT, AI_CRAWL_CONFIG_PROMPT
from .query_interpreter import get_openai_client

logger = structlog.get_logger()


async def ai_generate_entity_type_config(
    user_intent: str,
    geographic_context: str,
) -> Dict[str, Any]:
    """
    Step 1/3: Generate EntityType configuration using LLM.

    Returns dict with: name, name_plural, description, icon, color, attribute_schema, search_focus
    """
    client = get_openai_client()
    if not client:
        logger.warning("Azure OpenAI client not configured, using fallback")
        return {
            "name": "Neue Kategorie",
            "name_plural": "Neue Kategorien",
            "description": user_intent,
            "icon": "mdi-folder",
            "color": "#2196F3",
            "attribute_schema": {"type": "object", "properties": {}},
            "search_focus": "general",
        }

    prompt = AI_ENTITY_TYPE_PROMPT.format(
        user_intent=user_intent,
        geographic_context=geographic_context or "Keine geografische Einschränkung",
    )

    try:
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1000,
        )

        content = response.choices[0].message.content.strip()
        # Clean up markdown code blocks if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()

        result = json.loads(content)
        logger.info("AI generated EntityType config", name=result.get("name"))
        return result

    except Exception as e:
        logger.error("Failed to generate EntityType config via AI", error=str(e))
        return {
            "name": "Neue Kategorie",
            "name_plural": "Neue Kategorien",
            "description": user_intent,
            "icon": "mdi-folder",
            "color": "#2196F3",
            "attribute_schema": {"type": "object", "properties": {}},
            "search_focus": "general",
        }


async def ai_generate_category_config(
    user_intent: str,
    entity_type_name: str,
    entity_type_description: str,
) -> Dict[str, Any]:
    """
    Step 2/3: Generate Category configuration with AI extraction prompt.

    Returns dict with: purpose, search_terms, extraction_handler, ai_extraction_prompt
    """
    client = get_openai_client()
    if not client:
        logger.warning("Azure OpenAI client not configured, using fallback")
        return {
            "purpose": user_intent,
            "search_terms": ["Event", "Veranstaltung", "Konferenz"],
            "extraction_handler": "default",
            "ai_extraction_prompt": f"Extrahiere relevante Informationen zu: {user_intent}",
        }

    prompt = AI_CATEGORY_PROMPT.format(
        user_intent=user_intent,
        entity_type_name=entity_type_name,
        entity_type_description=entity_type_description,
    )

    try:
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000,
        )

        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()

        result = json.loads(content)
        logger.info(
            "AI generated Category config",
            search_terms_count=len(result.get("search_terms", [])),
        )
        return result

    except Exception as e:
        logger.error("Failed to generate Category config via AI", error=str(e))
        return {
            "purpose": user_intent,
            "search_terms": ["Event", "Veranstaltung", "Konferenz"],
            "extraction_handler": "default",
            "ai_extraction_prompt": f"Extrahiere relevante Informationen zu: {user_intent}",
        }


async def ai_generate_crawl_config(
    user_intent: str,
    search_focus: str,
    search_terms: List[str],
) -> Dict[str, Any]:
    """
    Step 3/3: Generate URL patterns for crawling using AI.

    Returns dict with: url_include_patterns, url_exclude_patterns, reasoning

    Raises:
        ValueError: If Azure OpenAI is not configured
        RuntimeError: If AI generation fails
    """
    client = get_openai_client()
    if not client:
        raise ValueError("Azure OpenAI client not configured - AI is required for Smart Query")

    prompt = AI_CRAWL_CONFIG_PROMPT.format(
        user_intent=user_intent,
        search_focus=search_focus,
        search_terms=", ".join(search_terms[:20]),  # Limit for prompt size
    )

    try:
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=1000,
        )

        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()

        result = json.loads(content)
        logger.info(
            "AI generated Crawl config",
            include_count=len(result.get("url_include_patterns", [])),
            exclude_count=len(result.get("url_exclude_patterns", [])),
        )
        return result

    except Exception as e:
        logger.error("Failed to generate Crawl config via AI", error=str(e))
        raise RuntimeError(f"AI Crawl-Config generation failed: {str(e)}")
