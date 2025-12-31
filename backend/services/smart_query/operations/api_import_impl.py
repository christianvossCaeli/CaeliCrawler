"""API Import Implementation.

This module contains the complex execute_fetch_and_create function that handles
fetching data from external APIs (Wikidata SPARQL, REST APIs) and creating entities.

This is kept separate from api_import_ops.py for maintainability (400+ lines).
"""

from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()


async def execute_fetch_and_create(
    session: AsyncSession,
    fetch_data: dict[str, Any],
) -> dict[str, Any]:
    """Fetch data from an external API and create entities.

    This operation supports:
    - Wikidata SPARQL queries for German municipalities, Bundeslaender, UK councils, etc.
    - REST APIs with predefined templates (e.g., Caeli Auction Windparks)
    - Automatic parent entity creation for hierarchies
    - Bulk entity creation with proper hierarchy setup
    - Entity matching to link imported items to existing entities (e.g., Windpark -> Gemeinde)

    Args:
        session: Database session
        fetch_data: Dict with keys:
            - api_config: API configuration
                - type: "sparql", "rest"
                - template: Predefined template name (e.g., "caeli_auction_windparks")
                - query: SPARQL query or predefined query name
                - country: Country code for predefined queries
                - pagination: { limit, max_results }
            - entity_type: Target entity type slug
            - field_mapping: Mapping from API fields to entity fields
            - parent_config: Optional parent entity configuration
                - field: API field containing parent name
                - entity_type: Parent entity type slug
            - create_entity_type: Whether to create the entity type if missing
            - entity_type_config: Config for new entity type
            - match_to_parent: Whether to fuzzy match items to parent entities by name

    Returns:
        Dict with fetch and create results
    """
    from app.models import EntityType

    from ..api_fetcher import ExternalAPIFetcher, get_predefined_rest_template
    from ..entity_operations import bulk_create_entities_from_api_data, create_entity_type_from_command

    api_config = fetch_data.get("api_config", {})
    entity_type_slug = fetch_data.get("entity_type", "territorial_entity")
    field_mapping = fetch_data.get("field_mapping", {})
    parent_config = fetch_data.get("parent_config")
    create_entity_type_flag = fetch_data.get("create_entity_type", False)
    entity_type_config = fetch_data.get("entity_type_config", {})
    match_to_parent = fetch_data.get("match_to_gemeinde", False) or fetch_data.get("match_to_parent", False)

    # NEW: Hierarchical import parameters for same-entity-type hierarchies
    # hierarchy_level: Explicit level to set (1=Bundesland, 2=Gemeinde within territorial-entity)
    # parent_field: API field containing parent name for lookup WITHIN SAME entity type
    hierarchy_level = fetch_data.get("hierarchy_level")
    parent_field = fetch_data.get("parent_field")

    # Check for predefined REST API template
    template_name = api_config.get("template", "")
    if template_name:
        template_config = get_predefined_rest_template(template_name)
        if template_config:
            logger.info(f"Using predefined REST API template: {template_name}")
            # Merge template config into api_config (explicit config takes precedence)
            for key, value in template_config.items():
                if key not in api_config or not api_config[key]:
                    api_config[key] = value

            # Use template's field_mapping if not provided
            # REST templates use API_field -> entity_field format
            # Code expects entity_field -> API_field format - so we invert
            if not field_mapping and template_config.get("field_mapping"):
                template_mapping = template_config["field_mapping"]
                field_mapping = {v: k for k, v in template_mapping.items()}

            # Add name_template to field_mapping if present in template
            if template_config.get("name_template"):
                if field_mapping is None:
                    field_mapping = {}
                field_mapping["name_template"] = template_config["name_template"]

            # Use template's entity_type_config if not provided
            if not entity_type_config and template_config.get("entity_type_config"):
                entity_type_config = template_config["entity_type_config"]
                entity_type_slug = entity_type_config.get("slug", entity_type_slug)
                create_entity_type_flag = True  # Auto-create from template

            # For windpark templates, auto-enable parent matching (to Gemeinden)
            if "windpark" in template_name.lower():
                match_to_parent = True

    # Build parent_match_config if matching is enabled
    # This allows fuzzy matching of entities to parent entities by name
    parent_match_config = None
    if match_to_parent:
        # Try to get config from template
        match_field = None
        parent_entity_type = "territorial_entity"  # Default to Gemeinden

        if template_name:
            template_config = get_predefined_rest_template(template_name)
            if template_config:
                match_field = template_config.get("gemeinde_match_field") or template_config.get("parent_match_field")
                parent_entity_type = template_config.get("parent_entity_type", "territorial_entity")

        parent_match_config = {
            "field": match_field or "areaName",  # Field containing name to match
            "admin_level_field": "administrativeDivisionLevel1",  # For filtering by region
            "parent_entity_type": parent_entity_type,  # Entity type to match against
        }

    result = {
        "success": False,
        "message": "",
        "total_fetched": 0,
        "created_count": 0,
        "existing_count": 0,
        "error_count": 0,
        "matched_count": 0,  # Count of entities matched to Gemeinden
        "errors": [],
        "warnings": [],
        "entity_type": entity_type_slug,
        "parent_type": parent_config.get("entity_type") if parent_config else None,
    }

    try:
        # Step 1: Ensure entity type exists
        et_result = await session.execute(
            select(EntityType).where(EntityType.slug == entity_type_slug)
        )
        entity_type = et_result.scalar_one_or_none()

        if not entity_type:
            if create_entity_type_flag and entity_type_config:
                # Create the entity type
                entity_type, et_message = await create_entity_type_from_command(
                    session, entity_type_config
                )
                if not entity_type:
                    result["message"] = f"Entity-Typ konnte nicht erstellt werden: {et_message}"
                    return result
                result["warnings"].append(f"Entity-Typ '{entity_type_slug}' erstellt")
            else:
                result["message"] = f"Entity-Typ '{entity_type_slug}' nicht gefunden"
                return result

        # Step 2: Ensure parent entity type exists (if configured)
        if parent_config:
            parent_type_slug = parent_config.get("entity_type")
            if parent_type_slug:
                pet_result = await session.execute(
                    select(EntityType).where(EntityType.slug == parent_type_slug)
                )
                parent_entity_type = pet_result.scalar_one_or_none()

                if not parent_entity_type:
                    # Create parent entity type - use provided config or defaults
                    parent_type_config = parent_config.get("parent_type_config") or parent_config.get("entity_type_config") or {
                        "name": parent_type_slug.replace("-", " ").title(),
                        "name_plural": parent_type_slug.replace("-", " ").title() + "s",
                        "slug": parent_type_slug,
                        "icon": "mdi-map-marker",
                        "color": "#FF9800",
                        "is_primary": False,
                        "is_public": True,
                        "supports_hierarchy": False,
                    }
                    parent_entity_type, pet_message = await create_entity_type_from_command(
                        session, parent_type_config
                    )
                    if parent_entity_type:
                        result["warnings"].append(f"Parent Entity-Typ '{parent_type_slug}' erstellt")

        # Step 3: Fetch data from API
        fetcher = ExternalAPIFetcher()

        try:
            # Apply default field mappings for predefined queries
            query = api_config.get("query", "")
            country = api_config.get("country", "DE")

            # Set default field mappings based on query type
            if not field_mapping:
                if "gemeinden" in query.lower() or "municipalities" in query.lower():
                    if country == "DE":
                        field_mapping = {
                            "name": "gemeindeLabel",
                            "external_id": "ags",
                            "admin_level_1": "bundeslandLabel",
                            "population": "einwohner",
                            "area": "flaeche",
                            "latitude": "lat",
                            "longitude": "lon",
                            "website": "website",  # Official website URL
                            "country": "DE",
                        }
                    elif country == "AT":
                        field_mapping = {
                            "name": "gemeindeLabel",
                            "external_id": "gkz",
                            "admin_level_1": "bundeslandLabel",
                            "population": "einwohner",
                            "area": "flaeche",
                            "latitude": "lat",
                            "longitude": "lon",
                            "website": "website",  # Official website URL
                            "country": "AT",
                        }
                elif "bundeslaender" in query.lower() or "states" in query.lower():
                    field_mapping = {
                        "name": "bundeslandLabel",
                        "population": "einwohner",
                        "area": "flaeche",
                        "latitude": "lat",
                        "longitude": "lon",
                        "website": "website",  # Official website URL
                        "country": country,
                    }
                elif "councils" in query.lower() or "parishes" in query.lower() or "uk-local-authorit" in query.lower() or "local_authorit" in query.lower():
                    field_mapping = {
                        "name": "councilLabel",
                        "external_id": "gss_code",
                        "admin_level_1": "regionLabel",
                        "population": "einwohner",
                        "latitude": "lat",
                        "longitude": "lon",
                        "website": "website",  # Official website URL
                        "country": "GB",
                    }

            # Set default hierarchy for municipalities
            # For hierarchical entity types (like territorial-entity), we use parent_field
            # to link to the parent WITHIN THE SAME entity type, not separate entity types
            if "gemeinden" in query.lower() or "municipalities" in query.lower():
                # Check if target entity type is hierarchical
                et_check = await session.execute(
                    select(EntityType).where(EntityType.slug == entity_type_slug)
                )
                entity_type_obj = et_check.scalar_one_or_none()

                if entity_type_obj and entity_type_obj.supports_hierarchy:
                    # Use same-entity-type hierarchy via parent_field
                    if hierarchy_level is None:
                        hierarchy_level = 2  # Gemeinden are level 2
                    if parent_field is None:
                        parent_field = "bundeslandLabel" if country in ["DE", "AT"] else "regionLabel"
                    logger.info(
                        "Using hierarchical parent linking within same entity type",
                        entity_type=entity_type_slug,
                        hierarchy_level=hierarchy_level,
                        parent_field=parent_field,
                    )
                elif not parent_config:
                    # Fall back to separate entity types (legacy behavior)
                    parent_config = {
                        "field": "bundeslandLabel" if country in ["DE", "AT"] else "regionLabel",
                        "entity_type": "bundesland" if country in ["DE", "AT"] else "region",
                        "create_parent_type": True,
                        "parent_type_config": {
                            "name": "Bundesland" if country == "DE" else ("Bundesland" if country == "AT" else "Region"),
                            "name_plural": "Bundesländer" if country in ["DE", "AT"] else "Regions",
                            "slug": "bundesland" if country in ["DE", "AT"] else "region",
                            "description": "Deutsche Bundesländer" if country == "DE" else ("Österreichische Bundesländer" if country == "AT" else "UK Regions"),
                            "icon": "mdi-map-marker-radius",
                            "color": "#FF9800",
                            "is_primary": False,
                            "is_public": True,
                            "supports_hierarchy": False,
                        }
                    }

            # For Bundesländer/regions at level 1 (no parent needed within same type)
            if ("bundeslaender" in query.lower() or "states" in query.lower()) and hierarchy_level is None:
                hierarchy_level = 1  # Top-level entities

            logger.info(
                "Fetching data from external API",
                api_type=api_config.get("type"),
                query_type=query[:50] if len(query) > 50 else query,
                country=country,
            )

            fetch_result = await fetcher.fetch(api_config)

            if not fetch_result.success:
                result["message"] = f"API-Fetch fehlgeschlagen: {fetch_result.error}"
                result["errors"].append(fetch_result.error)
                return result

            result["total_fetched"] = fetch_result.total_count
            result["warnings"].extend(fetch_result.warnings)

            if not fetch_result.items:
                result["success"] = True
                result["message"] = "API lieferte keine Daten"
                return result

            logger.info(
                "API fetch successful",
                items_count=len(fetch_result.items),
            )

        finally:
            await fetcher.close()

        # Step 4: AI-based analysis of API response (if no explicit field_mapping)
        # This allows the AI to intelligently determine field mappings, DataSource creation, etc.
        use_ai_analysis = fetch_data.get("use_ai_analysis", True)  # Default: enabled

        if use_ai_analysis and not field_mapping and fetch_result.items:
            try:
                from ..ai_generation import ai_analyze_api_response

                logger.info("Starting AI analysis of API response...")

                ai_result = await ai_analyze_api_response(
                    api_items=fetch_result.items,
                    user_intent=fetch_data.get("user_intent", ""),
                    api_type=api_config.get("type", "unknown"),
                    target_entity_type=entity_type_slug,
                    sample_size=5,
                )

                # Apply AI-generated field mapping
                if ai_result.get("field_mapping"):
                    field_mapping = ai_result["field_mapping"]
                    result["ai_analysis"] = {
                        "detected_type": ai_result.get("analysis", {}).get("detected_entity_type"),
                        "confidence": ai_result.get("analysis", {}).get("confidence"),
                        "reasoning": ai_result.get("reasoning"),
                    }
                    result["warnings"].extend(ai_result.get("warnings", []))

                    logger.info(
                        "AI analysis applied",
                        field_mapping_keys=list(field_mapping.keys()),
                        detected_type=ai_result.get("analysis", {}).get("detected_entity_type"),
                    )

                # Apply AI-suggested parent config if not set
                ai_parent_config = ai_result.get("parent_config", {})
                if not parent_config and ai_parent_config.get("use_hierarchy"):
                    parent_config = {
                        "field": ai_parent_config.get("parent_field"),
                        "entity_type": ai_parent_config.get("parent_entity_type", "bundesland"),
                        "create_parent_type": ai_parent_config.get("create_parent_if_missing", True),
                    }

                # Apply AI-suggested entity type config if creating new type
                ai_et_suggestion = ai_result.get("entity_type_suggestion", {})
                if create_entity_type_flag and not entity_type_config and ai_et_suggestion:
                    entity_type_config = ai_et_suggestion

            except ValueError as e:
                # AI not configured - use fallback
                logger.warning("AI analysis skipped - not configured", error=str(e))
                result["warnings"].append("KI-Analyse übersprungen - Azure OpenAI nicht konfiguriert")
            except Exception as e:
                logger.warning("AI analysis failed, using fallback", error=str(e))
                result["warnings"].append(f"KI-Analyse fehlgeschlagen: {str(e)}")

        # Step 5: Bulk create entities
        create_result = await bulk_create_entities_from_api_data(
            session=session,
            entity_type_slug=entity_type_slug,
            items=fetch_result.items,
            field_mapping=field_mapping,
            parent_config=parent_config,
            parent_match_config=parent_match_config,
            api_config=api_config,  # For automatic DataSource creation
            hierarchy_level=hierarchy_level,  # Explicit hierarchy level (1=Bundesland, 2=Gemeinde)
            parent_field=parent_field,  # API field for parent lookup within same entity type
        )

        result["created_count"] = create_result["created_count"]
        result["existing_count"] = create_result["existing_count"]
        result["error_count"] = create_result["error_count"]
        result["errors"].extend(create_result["errors"])
        result["matched_count"] = create_result.get("parents_matched", 0)
        result["hierarchy_matched_count"] = create_result.get("hierarchy_parents_matched", 0)
        result["data_sources_created"] = create_result.get("data_sources_created", 0)
        result["hierarchy_level"] = hierarchy_level

        # Commit changes
        await session.commit()

        result["success"] = True
        matched_info = f", {result['matched_count']} mit Parent-Entities verknüpft" if result["matched_count"] > 0 else ""
        hierarchy_info = f", {result['hierarchy_matched_count']} hierarchisch verknüpft" if result.get("hierarchy_matched_count", 0) > 0 else ""
        ds_info = f", {result['data_sources_created']} Datenquellen erstellt" if result.get("data_sources_created", 0) > 0 else ""
        level_info = f" (Level {hierarchy_level})" if hierarchy_level else ""
        result["message"] = (
            f"API-Import abgeschlossen{level_info}: {result['created_count']} erstellt, "
            f"{result['existing_count']} existierten bereits, "
            f"{result['error_count']} Fehler{matched_info}{hierarchy_info}{ds_info}"
        )

        logger.info(
            "Fetch and create completed",
            entity_type=entity_type_slug,
            total_fetched=result["total_fetched"],
            created=result["created_count"],
            existing=result["existing_count"],
            errors=result["error_count"],
        )

        return result

    except Exception as e:
        logger.error("Fetch and create failed", error=str(e), exc_info=True)
        await session.rollback()
        result["message"] = f"Fehler: {str(e)}"
        return result
