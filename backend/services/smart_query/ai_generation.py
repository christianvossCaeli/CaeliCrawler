"""AI-powered generation functions for Smart Query Service."""

import json
from typing import Any, Dict, List

import structlog

from app.config import settings
from .prompts import (
    AI_ENTITY_TYPE_PROMPT,
    AI_CATEGORY_PROMPT,
    AI_CRAWL_CONFIG_PROMPT,
    AI_FACET_TYPES_PROMPT,
    AI_SEED_ENTITIES_PROMPT,
)
from .query_interpreter import get_openai_client
from .utils import clean_json_response

logger = structlog.get_logger()


async def ai_generate_entity_type_config(
    user_intent: str,
    geographic_context: str,
) -> Dict[str, Any]:
    """
    Step 1/3: Generate EntityType configuration using LLM.

    Returns dict with: name, name_plural, description, icon, color, attribute_schema, search_focus

    Raises:
        ValueError: If Azure OpenAI is not configured
        RuntimeError: If AI generation fails
    """
    client = get_openai_client()  # Raises ValueError if not configured

    prompt = AI_ENTITY_TYPE_PROMPT.format(
        user_intent=user_intent,
        geographic_context=geographic_context or "Keine geografische Einschränkung",
    )

    try:
        response = client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1000,
        )

        content = response.choices[0].message.content.strip()
        content = clean_json_response(content)

        result = json.loads(content)
        logger.info("AI generated EntityType config", name=result.get("name"))
        return result

    except ValueError:
        raise
    except Exception as e:
        logger.error("Failed to generate EntityType config via AI", error=str(e))
        raise RuntimeError(f"KI-Service nicht erreichbar: EntityType-Generierung fehlgeschlagen - {str(e)}")


async def ai_generate_category_config(
    user_intent: str,
    entity_type_name: str,
    entity_type_description: str,
    geographic_context: str = None,
) -> Dict[str, Any]:
    """
    Step 2/3: Generate Category configuration with AI extraction prompt.

    Returns dict with: purpose, search_terms, extraction_handler, ai_extraction_prompt, suggested_tags

    Raises:
        ValueError: If Azure OpenAI is not configured
        RuntimeError: If AI generation fails
    """
    client = get_openai_client()  # Raises ValueError if not configured

    prompt = AI_CATEGORY_PROMPT.format(
        user_intent=user_intent,
        entity_type_name=entity_type_name,
        entity_type_description=entity_type_description,
        geographic_context=geographic_context or "Keine geografische Einschränkung",
    )

    try:
        response = client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000,
        )

        content = response.choices[0].message.content.strip()
        content = clean_json_response(content)

        result = json.loads(content)
        logger.info(
            "AI generated Category config",
            search_terms_count=len(result.get("search_terms", [])),
        )
        return result

    except ValueError:
        raise
    except Exception as e:
        logger.error("Failed to generate Category config via AI", error=str(e))
        raise RuntimeError(f"KI-Service nicht erreichbar: Category-Generierung fehlgeschlagen - {str(e)}")


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
    client = get_openai_client()  # Raises ValueError if not configured

    prompt = AI_CRAWL_CONFIG_PROMPT.format(
        user_intent=user_intent,
        search_focus=search_focus,
        search_terms=", ".join(search_terms[:20]),  # Limit for prompt size
    )

    try:
        response = client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=1000,
        )

        content = response.choices[0].message.content.strip()
        content = clean_json_response(content)

        result = json.loads(content)
        logger.info(
            "AI generated Crawl config",
            include_count=len(result.get("url_include_patterns", [])),
            exclude_count=len(result.get("url_exclude_patterns", [])),
        )
        return result

    except ValueError:
        raise
    except Exception as e:
        logger.error("Failed to generate Crawl config via AI", error=str(e))
        raise RuntimeError(f"KI-Service nicht erreichbar: Crawl-Config-Generierung fehlgeschlagen - {str(e)}")


async def ai_generate_facet_types(
    user_intent: str,
    entity_type_name: str,
    entity_type_description: str,
) -> Dict[str, Any]:
    """
    Generate FacetType suggestions based on user intent and EntityType.

    Returns dict with: facet_types (list), reasoning

    Raises:
        ValueError: If Azure OpenAI is not configured
        RuntimeError: If AI generation fails
    """
    client = get_openai_client()  # Raises ValueError if not configured

    prompt = AI_FACET_TYPES_PROMPT.format(
        user_intent=user_intent,
        entity_type_name=entity_type_name,
        entity_type_description=entity_type_description or "Keine Beschreibung",
    )

    try:
        response = client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1500,
        )

        content = response.choices[0].message.content.strip()
        content = clean_json_response(content)

        result = json.loads(content)
        facet_types = result.get("facet_types", [])
        logger.info(
            "AI generated FacetTypes",
            count=len(facet_types),
            slugs=[ft.get("slug") for ft in facet_types],
        )
        return result

    except ValueError:
        raise
    except Exception as e:
        logger.error("Failed to generate FacetTypes via AI", error=str(e))
        # Don't raise - FacetType generation is optional, return empty list
        return {"facet_types": [], "reasoning": f"FacetType-Generierung übersprungen: {str(e)}"}


async def ai_generate_seed_entities(
    user_intent: str,
    entity_type_name: str,
    entity_type_description: str,
    attribute_schema: Dict[str, Any],
    geographic_context: str = "Deutschland",
) -> Dict[str, Any]:
    """
    Generate seed entities based on AI knowledge.

    Uses Claude/GPT's training knowledge to generate initial entities
    for well-known lists (Bundesliga clubs, DAX companies, etc.)

    Returns dict with: entities (list), total_known, is_complete_list, reasoning

    Raises:
        ValueError: If Azure OpenAI is not configured
        RuntimeError: If AI generation fails
    """
    client = get_openai_client()  # Raises ValueError if not configured

    # Format attribute schema for the prompt
    schema_str = json.dumps(attribute_schema, indent=2, ensure_ascii=False)

    prompt = AI_SEED_ENTITIES_PROMPT.format(
        user_intent=user_intent,
        entity_type_name=entity_type_name,
        entity_type_description=entity_type_description or "Keine Beschreibung",
        attribute_schema=schema_str,
        geographic_context=geographic_context or "Deutschland",
    )

    try:
        response = client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,  # Lower temperature for factual accuracy
            max_tokens=4000,  # More tokens for longer lists
        )

        content = response.choices[0].message.content.strip()
        content = clean_json_response(content)

        result = json.loads(content)
        entities = result.get("entities", [])
        hierarchy = result.get("hierarchy", {})
        logger.info(
            "AI generated seed entities",
            count=len(entities),
            total_known=result.get("total_known"),
            is_complete=result.get("is_complete_list"),
            hierarchy_use=hierarchy.get("use_hierarchy"),
            hierarchy_parent=hierarchy.get("parent_name"),
            hierarchy_type=hierarchy.get("parent_entity_type"),
            first_entity_relations=entities[0].get("relations", []) if entities else [],
        )
        return result

    except ValueError:
        raise
    except Exception as e:
        logger.error("Failed to generate seed entities via AI", error=str(e))
        # Don't raise - seed entity generation is optional
        return {
            "entities": [],
            "total_known": 0,
            "is_complete_list": False,
            "reasoning": f"Seed-Entity-Generierung übersprungen: {str(e)}",
        }
