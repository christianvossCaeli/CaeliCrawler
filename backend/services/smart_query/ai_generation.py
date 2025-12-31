"""AI-powered generation functions for Smart Query Service."""

import json
import time
from typing import Any

import structlog

from app.config import settings
from app.core.exceptions import AIInterpretationError
from app.models.llm_usage import LLMProvider, LLMTaskType
from services.llm_usage_tracker import record_llm_usage

from .prompts import (
    AI_API_RESPONSE_ANALYSIS_PROMPT,
    AI_CATEGORY_PROMPT,
    AI_CRAWL_CONFIG_PROMPT,
    AI_ENTITY_TYPE_PROMPT,
    AI_FACET_TYPES_PROMPT,
    AI_SEED_ENTITIES_PROMPT,
)
from .query_interpreter import get_openai_client
from .utils import clean_json_response

logger = structlog.get_logger()


async def ai_generate_entity_type_config(
    user_intent: str,
    geographic_context: str,
) -> dict[str, Any]:
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
        start_time = time.time()
        response = client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1000,
        )

        if response.usage:
            await record_llm_usage(
                provider=LLMProvider.AZURE_OPENAI,
                model=settings.azure_openai_deployment_name,
                task_type=LLMTaskType.CHAT,
                task_name="ai_generate_entity_type_config",
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                duration_ms=int((time.time() - start_time) * 1000),
                is_error=False,
            )

        content = response.choices[0].message.content.strip()
        content = clean_json_response(content)

        result = json.loads(content)
        logger.info("AI generated EntityType config", name=result.get("name"))
        return result

    except (ValueError, AIInterpretationError):
        raise
    except Exception as e:
        logger.error("Failed to generate EntityType config via AI", error=str(e))
        raise AIInterpretationError("EntityType-Generierung", detail=str(e)) from None


async def ai_generate_category_config(
    user_intent: str,
    entity_type_name: str,
    entity_type_description: str,
    geographic_context: str = None,
) -> dict[str, Any]:
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
        start_time = time.time()
        response = client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000,
        )

        if response.usage:
            await record_llm_usage(
                provider=LLMProvider.AZURE_OPENAI,
                model=settings.azure_openai_deployment_name,
                task_type=LLMTaskType.CHAT,
                task_name="ai_generate_category_config",
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                duration_ms=int((time.time() - start_time) * 1000),
                is_error=False,
            )

        content = response.choices[0].message.content.strip()
        content = clean_json_response(content)

        result = json.loads(content)
        logger.info(
            "AI generated Category config",
            search_terms_count=len(result.get("search_terms", [])),
        )
        return result

    except (ValueError, AIInterpretationError):
        raise
    except Exception as e:
        logger.error("Failed to generate Category config via AI", error=str(e))
        raise AIInterpretationError("Category-Generierung", detail=str(e)) from None


async def ai_generate_crawl_config(
    user_intent: str,
    search_focus: str,
    search_terms: list[str],
) -> dict[str, Any]:
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
        start_time = time.time()
        response = client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=1000,
        )

        if response.usage:
            await record_llm_usage(
                provider=LLMProvider.AZURE_OPENAI,
                model=settings.azure_openai_deployment_name,
                task_type=LLMTaskType.CHAT,
                task_name="ai_generate_crawl_config",
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                duration_ms=int((time.time() - start_time) * 1000),
                is_error=False,
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

    except (ValueError, AIInterpretationError):
        raise
    except Exception as e:
        logger.error("Failed to generate Crawl config via AI", error=str(e))
        raise AIInterpretationError("Crawl-Config-Generierung", detail=str(e)) from None


async def ai_generate_facet_types(
    user_intent: str,
    entity_type_name: str,
    entity_type_description: str,
) -> dict[str, Any]:
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
        start_time = time.time()
        response = client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1500,
        )

        if response.usage:
            await record_llm_usage(
                provider=LLMProvider.AZURE_OPENAI,
                model=settings.azure_openai_deployment_name,
                task_type=LLMTaskType.CHAT,
                task_name="ai_generate_facet_types",
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                duration_ms=int((time.time() - start_time) * 1000),
                is_error=False,
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
    attribute_schema: dict[str, Any],
    geographic_context: str = "Deutschland",
) -> dict[str, Any]:
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
        start_time = time.time()
        response = client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,  # Lower temperature for factual accuracy
            max_tokens=4000,  # More tokens for longer lists
        )

        if response.usage:
            await record_llm_usage(
                provider=LLMProvider.AZURE_OPENAI,
                model=settings.azure_openai_deployment_name,
                task_type=LLMTaskType.CHAT,
                task_name="ai_generate_seed_entities",
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                duration_ms=int((time.time() - start_time) * 1000),
                is_error=False,
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


async def ai_analyze_api_response(
    api_items: list[dict[str, Any]],
    user_intent: str = "",
    api_type: str = "unknown",
    target_entity_type: str = "",
    sample_size: int = 3,
) -> dict[str, Any]:
    """
    Analyze API response and generate intelligent field mappings.

    Uses AI to analyze the structure of API data and automatically determine:
    - Field mappings for entity creation
    - Whether to create DataSources for websites
    - Hierarchy relationships
    - Suggested tags and categories

    Args:
        api_items: List of items from API response
        user_intent: Original user request
        api_type: Type of API (sparql, rest, etc.)
        target_entity_type: Target entity type if known
        sample_size: Number of items to include in sample (default 3)

    Returns:
        Dict with:
        - analysis: Detection results
        - field_mapping: Mapping from API fields to entity fields
        - additional_mappings: Extra fields for core_attributes
        - data_source_config: Config for DataSource creation
        - parent_config: Hierarchy configuration
        - entity_type_suggestion: Suggested EntityType config
        - warnings: List of warnings
        - reasoning: Explanation of decisions

    Raises:
        ValueError: If Azure OpenAI is not configured
        RuntimeError: If AI analysis fails
    """
    client = get_openai_client()  # Raises ValueError if not configured

    # Take sample of items for analysis
    sample_items = api_items[:sample_size] if len(api_items) >= sample_size else api_items
    api_sample = json.dumps(sample_items, indent=2, ensure_ascii=False, default=str)

    prompt = AI_API_RESPONSE_ANALYSIS_PROMPT.format(
        user_intent=user_intent or "Daten importieren",
        api_type=api_type,
        target_entity_type=target_entity_type or "unbekannt",
        sample_size=len(sample_items),
        api_sample=api_sample,
    )

    try:
        start_time = time.time()
        response = client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,  # Lower temperature for accurate analysis
            max_tokens=2000,
        )

        if response.usage:
            await record_llm_usage(
                provider=LLMProvider.AZURE_OPENAI,
                model=settings.azure_openai_deployment_name,
                task_type=LLMTaskType.CHAT,
                task_name="ai_analyze_api_response",
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                duration_ms=int((time.time() - start_time) * 1000),
                is_error=False,
            )

        content = response.choices[0].message.content.strip()
        content = clean_json_response(content)

        result = json.loads(content)

        # Log analysis results
        analysis = result.get("analysis", {})
        field_mapping = result.get("field_mapping", {})
        data_source_config = result.get("data_source_config", {})

        logger.info(
            "AI analyzed API response",
            detected_type=analysis.get("detected_entity_type"),
            confidence=analysis.get("confidence"),
            create_data_sources=data_source_config.get("create_data_sources"),
            website_field=data_source_config.get("website_field"),
            name_field=field_mapping.get("name"),
            warnings_count=len(result.get("warnings", [])),
        )

        return result

    except ValueError:
        raise
    except json.JSONDecodeError as e:
        logger.error("Failed to parse AI API analysis response", error=str(e))
        # Return a basic fallback mapping
        return _generate_fallback_mapping(api_items)
    except Exception as e:
        logger.error("Failed to analyze API response via AI", error=str(e))
        # Return a basic fallback mapping instead of failing
        return _generate_fallback_mapping(api_items)


def _generate_fallback_mapping(api_items: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Generate a basic fallback mapping when AI analysis fails.

    Attempts to detect common field patterns automatically.
    """
    if not api_items:
        return {
            "analysis": {"detected_entity_type": "unknown", "confidence": 0.0},
            "field_mapping": {},
            "warnings": ["Keine Daten für Analyse verfügbar"],
        }

    # Get all keys from first item
    sample = api_items[0]
    keys = list(sample.keys())

    field_mapping = {}

    # Try to detect name field
    name_candidates = ["name", "label", "title", "bezeichnung", "Name", "Label"]
    for key in keys:
        if any(candidate.lower() in key.lower() for candidate in name_candidates):
            field_mapping["name"] = key
            break

    # Try to detect ID field
    id_candidates = ["id", "Id", "ID", "code", "Code", "key", "slug", "ags", "gkz"]
    for key in keys:
        if any(candidate.lower() == key.lower() for candidate in id_candidates):
            field_mapping["external_id"] = key
            break

    # Try to detect website field
    url_candidates = ["website", "url", "homepage", "web", "Website", "URL"]
    for key in keys:
        if any(candidate.lower() in key.lower() for candidate in url_candidates):
            field_mapping["website"] = key
            break

    # Try to detect admin level
    admin_candidates = ["bundesland", "state", "region", "administrativeDivision", "land"]
    for key in keys:
        if any(candidate.lower() in key.lower() for candidate in admin_candidates):
            field_mapping["admin_level_1"] = key
            break

    # Try to detect coordinates
    lat_candidates = ["lat", "latitude", "breite"]
    lon_candidates = ["lon", "lng", "longitude", "laenge"]
    for key in keys:
        if any(candidate.lower() in key.lower() for candidate in lat_candidates):
            field_mapping["latitude"] = key
        if any(candidate.lower() in key.lower() for candidate in lon_candidates):
            field_mapping["longitude"] = key

    # Determine if we should create data sources
    create_data_sources = "website" in field_mapping

    return {
        "analysis": {
            "detected_entity_type": "unknown",
            "detected_structure": "flat",
            "confidence": 0.5,
            "data_quality": "unknown",
        },
        "field_mapping": field_mapping,
        "additional_mappings": {},
        "data_source_config": {
            "create_data_sources": create_data_sources,
            "website_field": field_mapping.get("website"),
            "suggested_tags": [],
            "suggested_category_slugs": [],
        },
        "parent_config": {
            "use_hierarchy": "admin_level_1" in field_mapping,
            "parent_field": field_mapping.get("admin_level_1"),
            "parent_entity_type": "bundesland",
            "create_parent_if_missing": True,
        },
        "warnings": ["Fallback-Mapping verwendet - KI-Analyse fehlgeschlagen"],
        "reasoning": "Automatisches Pattern-Matching auf API-Feldnamen",
    }
