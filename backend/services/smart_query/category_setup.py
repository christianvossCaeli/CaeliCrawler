"""Category setup operations for Smart Query Service."""

import uuid as uuid_module
from collections.abc import Callable
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Category, DataSource, DataSourceCategory, Entity, EntityType, FacetType
from app.models.data_source import SourceStatus
from app.models.entity_relation import EntityRelation
from app.models.relation_type import RelationType

from .ai_generation import (
    ai_generate_category_config,
    ai_generate_crawl_config,
    ai_generate_entity_type_config,
    ai_generate_facet_types,
    ai_generate_seed_entities,
)
from .crawl_operations import find_matching_data_sources
from .geographic_utils import expand_search_terms, resolve_geographic_alias
from .schema_generator import (
    generate_ai_extraction_prompt,
    generate_entity_type_schema,
    generate_url_patterns,
)
from .utils import generate_slug

logger = structlog.get_logger()

# Configuration for AI Source Discovery integration
# The number of sources depends on the use case type:
# - ENTITY_COLLECTION: "Gemeinden in NRW" → many sources (one per entity)
# - TOPIC_MONITORING: "PlayStation news" → few high-quality sources
AI_DISCOVERY_MIN_CONFIDENCE = 0.6  # Minimum confidence for auto-import
AI_DISCOVERY_TOPIC_LIMIT = 15  # Max sources for topic monitoring
AI_DISCOVERY_ENTITY_LIMIT = 500  # Higher limit for entity collection


def classify_query_type(user_intent: str, search_terms: list) -> str:
    """
    Classify query as ENTITY_COLLECTION or TOPIC_MONITORING.

    ENTITY_COLLECTION: Collecting data about many individual entities
    - "Alle Gemeinden in NRW"
    - "Windkraftanlagen in Deutschland"
    - "Bundesliga-Vereine"

    TOPIC_MONITORING: Monitoring a topic from few authoritative sources
    - "PlayStation Neuerscheinungen"
    - "Kryptowährungskurse"
    - "IT-Stellenangebote"

    Returns:
        "entity_collection" or "topic_monitoring"
    """
    intent_lower = user_intent.lower()

    # Entity collection indicators
    entity_keywords = [
        "alle ",
        "sämtliche",
        "jede ",
        "jeden ",
        "jedes ",
        "gemeinde",
        "kommune",
        "stadt",
        "städte",
        "landkreis",
        "unternehmen",
        "firmen",
        "vereine",
        "mitglieder",
        "standorte",
        "filialen",
        "niederlassungen",
        "windkraft",
        "anlagen",
        "projekte",
    ]

    # Topic monitoring indicators
    topic_keywords = [
        "neuerscheinung",
        "release",
        "news",
        "nachrichten",
        "kurse",
        "preise",
        "ergebnisse",
        "spieltag",
        "stellenangebot",
        "job",
        "karriere",
        "wetter",
        "prognose",
        "vorhersage",
        "aktuell",
        "live",
        "täglich",
        "wöchentlich",
        "monatlich",
    ]

    entity_score = sum(1 for kw in entity_keywords if kw in intent_lower)
    topic_score = sum(1 for kw in topic_keywords if kw in intent_lower)

    # Check for geographic scope that suggests entity collection
    geographic_scope = any(
        x in intent_lower
        for x in [
            "in deutschland",
            "in nrw",
            "in bayern",
            "in hessen",
            "bundesweit",
            "landesweit",
            "regional",
        ]
    )

    if entity_score > topic_score or geographic_scope and entity_score > 0:
        return "entity_collection"
    else:
        return "topic_monitoring"


async def create_category_setup_with_ai(
    session: AsyncSession,
    user_intent: str,
    geographic_filter: dict[str, Any],
    current_user_id: UUID | None = None,
    progress_callback: Callable | None = None,
) -> dict[str, Any]:
    """
    Execute CREATE_CATEGORY_SETUP with full AI generation (3 LLM calls).

    Args:
        session: Database session
        user_intent: Original user query
        geographic_filter: Geographic constraints (admin_level_1, country)
        current_user_id: User ID for ownership
        progress_callback: Optional callback(step, total, message) for progress updates

    Returns:
        Result dict with created entities and progress info
    """
    result = {
        "success": False,
        "message": "",
        "steps": [],
        "entity_type_id": None,
        "entity_type_name": None,
        "entity_type_slug": None,
        "category_id": None,
        "category_name": None,
        "category_slug": None,
        "linked_data_source_count": 0,
        "discovered_data_source_count": 0,  # Sources found via AI Discovery
        "ai_discovered_sources": [],  # Details of discovered sources
        "ai_extraction_prompt": "",
        "url_patterns": {},
        "search_terms": [],
        "facet_types_created": [],  # FacetTypes created for this EntityType
        "facet_types_count": 0,  # Number of FacetTypes created
        "seed_entities_created": [],  # Seed entities created from AI knowledge
        "seed_entities_count": 0,  # Number of seed entities created
        "seed_relations_count": 0,  # Number of relations created for seed entities
        "hierarchy_parent_id": None,  # Parent entity ID if hierarchy is used
        "warnings": [],
    }

    # Total steps: 1=EntityType, 2=Category, 3=CrawlConfig, 4=AI Source Discovery, 5=FacetTypes, 6=Seed Entities
    total_steps = 6

    def report_progress(step: int, message: str, success: bool = True):
        result["steps"].append(
            {
                "step": step,
                "total": total_steps,
                "message": message,
                "success": success,
            }
        )
        if progress_callback:
            progress_callback(step, 3, message)
        logger.info(f"Smart Query Progress [{step}/3]: {message}")

    try:
        # Resolve geographic context
        admin_level_1 = geographic_filter.get("admin_level_1")
        if not admin_level_1 and geographic_filter.get("admin_level_1_alias"):
            admin_level_1 = resolve_geographic_alias(geographic_filter["admin_level_1_alias"])
        geographic_context = admin_level_1 or "Deutschland"

        # =========================================================================
        # STEP 1/3: Generate EntityType Configuration
        # =========================================================================
        report_progress(1, "Generiere EntityType-Konfiguration...")

        et_config = await ai_generate_entity_type_config(user_intent, geographic_context)

        name = et_config.get("name", "Neue Kategorie").strip()
        slug = generate_slug(name)

        # Import similarity functions for duplicate detection
        from app.utils.similarity import find_similar_entity_types, get_hierarchy_mapping

        entity_type = None

        # 1. Check if this is actually a hierarchy level of an existing type
        # E.g., "Stadt" should use "territorial_entity" instead of creating a new type
        hierarchy_mapping = get_hierarchy_mapping(name)
        if hierarchy_mapping:
            parent_type_slug = hierarchy_mapping["parent_type_slug"]
            hierarchy_level = hierarchy_mapping["hierarchy_level"]
            level_name = hierarchy_mapping["level_name"]

            parent_type_result = await session.execute(
                select(EntityType).where(
                    EntityType.slug == parent_type_slug,
                    EntityType.is_active.is_(True),
                )
            )
            parent_type = parent_type_result.scalar_one_or_none()

            if parent_type:
                logger.info(
                    "Using existing hierarchical EntityType instead of creating duplicate",
                    requested_name=name,
                    parent_type=parent_type.name,
                    hierarchy_level=hierarchy_level,
                )
                entity_type = parent_type
                result["steps"][-1]["result"] = (
                    f"'{level_name}' ist Hierarchie-Level {hierarchy_level} von '{parent_type.name}'. "
                    f"Verwende bestehenden Typ."
                )

        # 2. Check for exact duplicates (if not already found via hierarchy)
        if not entity_type:
            existing_et = await session.execute(
                select(EntityType).where(or_(EntityType.name == name, EntityType.slug == slug))
            )
            existing_type = existing_et.scalar()
            if existing_type:
                logger.info(
                    "Using existing EntityType (exact match)",
                    requested_name=name,
                    existing_name=existing_type.name,
                )
                entity_type = existing_type
                result["steps"][-1]["result"] = f"EntityType '{existing_type.name}' existiert bereits"

        # 3. Check for semantically similar EntityTypes (AI-based)
        if not entity_type:
            similar_types = await find_similar_entity_types(session, name, threshold=0.7)
            if similar_types:
                best_match, score, reason = similar_types[0]
                logger.info(
                    "Using existing EntityType (semantic similarity)",
                    requested_name=name,
                    matched_name=best_match.name,
                    similarity_score=score,
                )
                entity_type = best_match
                result["steps"][-1]["result"] = f"Ähnlicher EntityType '{best_match.name}' gefunden ({reason})"

        # 4. Only create new EntityType if no existing match found
        if not entity_type:
            entity_type = EntityType(
                id=uuid_module.uuid4(),
                name=name,
                slug=slug,
                name_plural=et_config.get("name_plural", name),
                description=et_config.get("description", user_intent),
                icon=et_config.get("icon", "mdi-folder"),
                color=et_config.get("color", "#2196F3"),
                display_order=100,
                is_primary=True,
                supports_hierarchy=False,
                attribute_schema=et_config.get("attribute_schema", {}),
                is_active=True,
                is_system=False,
                is_public=True,
                created_by_id=current_user_id,
                owner_id=current_user_id,
            )
            session.add(entity_type)
            await session.flush()

            # Generate embedding for semantic similarity search
            from app.utils.similarity import generate_embedding

            try:
                embedding = await generate_embedding(name)
                if embedding:
                    entity_type.name_embedding = embedding
                    logger.info("Generated embedding for new EntityType", name=name)
            except Exception as e:
                logger.warning("Failed to generate embedding for EntityType", name=name, error=str(e))

            result["steps"][-1]["result"] = f"EntityType '{name}' erstellt"

        result["entity_type_id"] = str(entity_type.id)
        result["entity_type_name"] = entity_type.name
        result["entity_type_slug"] = entity_type.slug

        # =========================================================================
        # STEP 2/3: Generate Category Configuration
        # =========================================================================
        report_progress(2, "Generiere Category & AI-Extraktions-Prompt...")

        cat_config = await ai_generate_category_config(
            user_intent,
            entity_type.name,
            entity_type.description,
            geographic_context=geographic_context,
        )

        search_terms = cat_config.get("search_terms", [])
        ai_prompt = cat_config.get("ai_extraction_prompt", "")
        extraction_handler = cat_config.get("extraction_handler", "default")

        # =========================================================================
        # STEP 3/3: Generate Crawl Configuration
        # =========================================================================
        report_progress(3, "Generiere URL-Filter & Crawl-Konfiguration...")

        crawl_config = await ai_generate_crawl_config(
            user_intent,
            et_config.get("search_focus", "general"),
            search_terms,
        )

        url_include_patterns = crawl_config.get("url_include_patterns", [])
        url_exclude_patterns = crawl_config.get("url_exclude_patterns", [])

        # =========================================================================
        # CREATE CATEGORY (or use existing if duplicate detected)
        # =========================================================================
        from app.utils.similarity import find_similar_categories

        # Check for exact duplicate Category
        existing_cat_result = await session.execute(
            select(Category).where(or_(Category.name == name, Category.slug == slug))
        )
        existing_category = existing_cat_result.scalar()

        # Check for semantically similar Categories (AI-based)
        if not existing_category:
            similar_categories = await find_similar_categories(session, name, threshold=0.85)
            if similar_categories:
                existing_category = similar_categories[0][0]
                logger.info(
                    "Found semantically similar Category",
                    new_name=name,
                    existing_name=existing_category.name,
                    similarity=round(similar_categories[0][1], 3),
                )

        if existing_category:
            # Use existing category instead of creating a new one
            category = existing_category
            logger.info(
                "Using existing Category instead of creating duplicate",
                category_id=str(category.id),
                category_name=category.name,
                requested_name=name,
            )
            result["warnings"].append(
                f"Bestehende Kategorie '{category.name}' wird verwendet statt '{name}' neu zu erstellen"
            )
        else:
            # Create new Category
            category = Category(
                id=uuid_module.uuid4(),
                name=name,
                slug=slug,
                description=f"KI-generiert: {user_intent}",
                purpose=cat_config.get("purpose", user_intent),
                search_terms=search_terms,
                document_types=["html", "pdf"],
                url_include_patterns=url_include_patterns,
                url_exclude_patterns=url_exclude_patterns,
                languages=["de"],
                ai_extraction_prompt=ai_prompt,
                extraction_handler=extraction_handler,
                schedule_cron="0 2 * * *",
                is_active=True,
                is_public=True,  # Always visible in frontend
                created_by_id=current_user_id,
                owner_id=current_user_id,
                target_entity_type_id=entity_type.id,
            )
            session.add(category)
        await session.flush()

        result["category_id"] = str(category.id)
        result["category_name"] = category.name
        result["category_slug"] = category.slug
        result["ai_extraction_prompt"] = ai_prompt
        result["search_terms"] = search_terms
        result["url_patterns"] = {
            "include": url_include_patterns,
            "exclude": url_exclude_patterns,
            "reasoning": crawl_config.get("reasoning", ""),
        }

        # =========================================================================
        # STEP 4/4: AI SOURCE DISCOVERY - Find and create new data sources
        # Only run if no existing sources match the search terms
        # =========================================================================
        report_progress(4, "Prüfe existierende Datenquellen...")

        discovered_sources = []
        discovered_count = 0

        # First check if we already have matching sources
        existing_matching_sources = await find_matching_data_sources(session, geographic_filter)

        # Also check sources matching search terms
        if search_terms:
            search_term_conditions = [DataSource.name.ilike(f"%{term}%") for term in search_terms[:5]]
            if search_term_conditions:
                term_sources_result = await session.execute(
                    select(DataSource).where(
                        or_(*search_term_conditions),
                        DataSource.status.in_([SourceStatus.ACTIVE, SourceStatus.PENDING]),
                    )
                )
                for source in term_sources_result.scalars().all():
                    if source not in existing_matching_sources:
                        existing_matching_sources.append(source)

        # Only run AI Discovery if we have few or no existing sources
        should_discover = len(existing_matching_sources) < 3

        if should_discover:
            report_progress(4, "Suche automatisch nach relevanten Datenquellen...")
            try:
                # Build discovery prompt from search terms and user intent
                discovery_prompt = f"{user_intent}. Suchbegriffe: {', '.join(search_terms)}"

                # Import here to avoid circular imports
                from services.ai_source_discovery.discovery_service import AISourceDiscoveryService

                # Get user's search API credentials
                serpapi_key = None
                serper_key = None

                if current_user_id:
                    from services.credentials_resolver import get_serpapi_key, get_serper_key

                    serpapi_key = await get_serpapi_key(session, current_user_id)
                    serper_key = await get_serper_key(session, current_user_id)

                discovery_service = AISourceDiscoveryService(
                    serpapi_key=serpapi_key,
                    serper_key=serper_key,
                )
                discovery_result = await discovery_service.discover_sources(
                    prompt=discovery_prompt,
                    max_results=200,  # Get more, AI will determine actual limit
                    search_depth="standard",
                )

                # Use AI-recommended source limit from search strategy
                # The AI analyzes the query and determines appropriate limits:
                # - "Bundesliga-Vereine" → ~25 sources (18 teams × 1.5)
                # - "Gemeinden in NRW" → ~500 sources (400 Gemeinden × 1.25)
                # - "PlayStation News" → ~15 sources (topic monitoring)
                if discovery_result.search_strategy:
                    source_limit = discovery_result.search_strategy.recommended_max_sources
                    expected_entities = discovery_result.search_strategy.expected_entity_count
                    reasoning = discovery_result.search_strategy.reasoning
                    logger.info(
                        "AI-determined source limit",
                        expected_entities=expected_entities,
                        source_limit=source_limit,
                        reasoning=reasoning,
                        user_intent=user_intent[:100],
                    )
                else:
                    # Fallback to keyword-based classification
                    query_type = classify_query_type(user_intent, search_terms)
                    source_limit = (
                        AI_DISCOVERY_ENTITY_LIMIT if query_type == "entity_collection" else AI_DISCOVERY_TOPIC_LIMIT
                    )
                    logger.info(
                        "Fallback query classification",
                        query_type=query_type,
                        source_limit=source_limit,
                    )

                # Sort sources by confidence (highest first)
                sorted_sources = sorted(
                    discovery_result.sources,
                    key=lambda s: s.confidence,
                    reverse=True,
                )

                # Process discovered sources with intelligent limiting
                for source_data in sorted_sources:
                    # Enforce AI-recommended source limit
                    if discovered_count >= source_limit:
                        logger.info(
                            "AI source limit reached",
                            limit=source_limit,
                            discovered=discovered_count,
                        )
                        break

                    # Skip low-confidence sources
                    if source_data.confidence < AI_DISCOVERY_MIN_CONFIDENCE:
                        continue

                    # Check if URL already exists in database
                    existing_source = await session.execute(
                        select(DataSource).where(DataSource.base_url == source_data.base_url)
                    )
                    if existing_source.scalar():
                        # Source exists, will be linked below
                        continue

                    # Validate URL with HTTP check (follows redirects, checks for 404 etc.)
                    from app.core.url_validator import validate_url_http

                    is_valid, error_msg, final_url = await validate_url_http(
                        source_data.base_url,
                        follow_redirects=True,
                        timeout=10.0,
                    )

                    if not is_valid:
                        logger.warning(
                            "Skipping invalid AI-discovered URL",
                            url=source_data.base_url,
                            error=error_msg,
                        )
                        result["warnings"].append(f"URL übersprungen ({error_msg}): {source_data.base_url[:50]}")
                        continue

                    # Use the final URL after redirects
                    validated_url = final_url or source_data.base_url

                    # Check again if the final URL already exists
                    if validated_url != source_data.base_url:
                        existing_final = await session.execute(
                            select(DataSource).where(DataSource.base_url == validated_url)
                        )
                        if existing_final.scalar():
                            logger.info(
                                "URL redirects to existing source",
                                original=source_data.base_url,
                                final=validated_url,
                            )
                            continue

                    # Create new DataSource from discovered source
                    from app.models.data_source import SourceType

                    # Determine source type
                    src_type = SourceType.WEBSITE
                    if source_data.source_type:
                        try:
                            src_type = SourceType(source_data.source_type)
                        except ValueError:
                            src_type = SourceType.WEBSITE

                    new_source = DataSource(
                        id=uuid_module.uuid4(),
                        name=source_data.name[:200] if source_data.name else f"AI-Discovered: {validated_url[:50]}",
                        base_url=validated_url,  # Use validated/redirected URL
                        source_type=src_type,
                        tags=source_data.tags or [],
                        status=SourceStatus.PENDING,
                        priority=1,  # Give AI-discovered sources low priority
                        extra_data={
                            "ai_discovered": True,
                            "discovery_confidence": source_data.confidence,
                            "discovery_prompt": discovery_prompt[:500],
                            "original_url": source_data.base_url if source_data.base_url != validated_url else None,
                        },
                    )
                    session.add(new_source)
                    discovered_sources.append(
                        {
                            "name": new_source.name,
                            "url": new_source.base_url,
                            "confidence": source_data.confidence,
                            "tags": source_data.tags,
                        }
                    )
                    discovered_count += 1

                await session.flush()

                result["ai_discovered_sources"] = discovered_sources
                result["discovered_data_source_count"] = discovered_count
                result["steps"][-1]["result"] = f"{discovered_count} neue Quellen entdeckt"

                if discovery_result.warnings:
                    result["warnings"].extend(discovery_result.warnings)

            except Exception as e:
                logger.warning("AI Source Discovery failed, continuing without", error=str(e))
                result["warnings"].append(f"AI Source Discovery übersprungen: {str(e)}")
                result["steps"][-1]["success"] = False
                result["steps"][-1]["result"] = f"Übersprungen: {str(e)}"
        else:
            # Already have enough matching sources, skip AI Discovery
            result["steps"][-1]["result"] = (
                f"Übersprungen: {len(existing_matching_sources)} passende Quellen bereits vorhanden"
            )
            logger.info(
                "AI Source Discovery skipped - sufficient existing sources",
                existing_count=len(existing_matching_sources),
                search_terms=search_terms,
            )

        # =========================================================================
        # LINK ALL DATA SOURCES (existing + newly discovered)
        # =========================================================================
        # Use the existing_matching_sources we already found above
        # Re-query to include any newly created sources from AI Discovery
        all_sources_to_link = list(existing_matching_sources)

        # Also fetch any newly created AI-discovered sources
        if discovered_count > 0:
            new_sources_result = await session.execute(
                select(DataSource).where(
                    DataSource.extra_data["ai_discovered"].astext == "true",
                    DataSource.status.in_([SourceStatus.ACTIVE, SourceStatus.PENDING]),
                )
            )
            for source in new_sources_result.scalars().all():
                if source not in all_sources_to_link:
                    all_sources_to_link.append(source)

        matching_sources = all_sources_to_link

        linked_count = 0
        for source in matching_sources:
            existing_link = await session.execute(
                select(DataSourceCategory).where(
                    DataSourceCategory.data_source_id == source.id,
                    DataSourceCategory.category_id == category.id,
                )
            )
            if not existing_link.scalar():
                link = DataSourceCategory(
                    id=uuid_module.uuid4(),
                    data_source_id=source.id,
                    category_id=category.id,
                )
                session.add(link)
                linked_count += 1

        await session.flush()  # Let caller handle commit for transaction control

        result["linked_data_source_count"] = linked_count

        # =========================================================================
        # STEP 5/5: Generate and Create FacetTypes
        # =========================================================================
        report_progress(5, "Generiere FacetTypes für EntityType...")

        facet_types_created = []
        facet_types_count = 0

        try:
            # Generate FacetType suggestions via AI
            ft_config = await ai_generate_facet_types(
                user_intent=user_intent,
                entity_type_name=entity_type.name,
                entity_type_description=entity_type.description,
            )

            suggested_facet_types = ft_config.get("facet_types", [])

            for ft_data in suggested_facet_types:
                ft_slug = ft_data.get("slug", "").strip()
                ft_name = ft_data.get("name", "").strip()

                if not ft_slug or not ft_name:
                    continue

                # Check if FacetType already exists
                existing_ft = await session.execute(select(FacetType).where(FacetType.slug == ft_slug))
                existing = existing_ft.scalar_one_or_none()

                if existing:
                    # FacetType exists - just add EntityType to applicable_entity_type_slugs
                    if entity_type.slug not in (existing.applicable_entity_type_slugs or []):
                        existing.applicable_entity_type_slugs = (existing.applicable_entity_type_slugs or []) + [
                            entity_type.slug
                        ]
                        facet_types_created.append(
                            {
                                "id": str(existing.id),
                                "name": existing.name,
                                "slug": existing.slug,
                                "is_new": False,
                            }
                        )
                        facet_types_count += 1
                        logger.info(
                            "Linked existing FacetType to EntityType",
                            facet_type=existing.slug,
                            entity_type=entity_type.slug,
                        )
                else:
                    # Check for semantically similar FacetTypes before creating
                    from app.utils.similarity import find_similar_facet_types

                    similar_types = await find_similar_facet_types(session, ft_name, threshold=0.7)

                    if similar_types:
                        # Use existing similar FacetType instead of creating duplicate
                        best_match, score, reason = similar_types[0]
                        if entity_type.slug not in (best_match.applicable_entity_type_slugs or []):
                            best_match.applicable_entity_type_slugs = (
                                best_match.applicable_entity_type_slugs or []
                            ) + [entity_type.slug]
                        facet_types_created.append(
                            {
                                "id": str(best_match.id),
                                "name": best_match.name,
                                "slug": best_match.slug,
                                "is_new": False,
                                "matched_from": ft_name,
                                "similarity_score": score,
                            }
                        )
                        facet_types_count += 1
                        logger.info(
                            "Linked similar FacetType to EntityType (avoided duplicate)",
                            requested_name=ft_name,
                            matched_name=best_match.name,
                            similarity_score=score,
                            entity_type=entity_type.slug,
                        )
                    else:
                        # Create new FacetType - no similar type found
                        new_facet_type = FacetType(
                            id=uuid_module.uuid4(),
                            name=ft_name,
                            slug=ft_slug,
                            name_plural=ft_data.get("name_plural", f"{ft_name}s"),
                            description=ft_data.get("description", f"FacetType: {ft_name}"),
                            icon=ft_data.get("icon", "mdi-tag"),
                            color=ft_data.get("color", "#2196F3"),
                            value_type=ft_data.get("value_type", "object"),
                            value_schema=ft_data.get("value_schema", {}),
                            applicable_entity_type_slugs=[entity_type.slug],
                            is_time_based=ft_data.get("is_time_based", True),
                            ai_extraction_enabled=True,
                            ai_extraction_prompt=ft_data.get(
                                "ai_extraction_prompt", f"Extrahiere {ft_name} aus dem Dokument."
                            ),
                            is_active=True,
                            is_system=False,
                        )
                        session.add(new_facet_type)

                        # Generate embedding for future similarity checks
                        from app.utils.similarity import generate_embedding

                        embedding = await generate_embedding(ft_name)
                        if embedding:
                            new_facet_type.name_embedding = embedding

                        facet_types_created.append(
                            {
                                "id": str(new_facet_type.id),
                                "name": new_facet_type.name,
                                "slug": new_facet_type.slug,
                                "is_new": True,
                            }
                        )
                        facet_types_count += 1
                        logger.info(
                            "Created new FacetType",
                            facet_type=new_facet_type.slug,
                            entity_type=entity_type.slug,
                        )

            await session.flush()
            result["steps"][-1]["result"] = f"{facet_types_count} FacetTypes erstellt/verknüpft"

        except Exception as ft_error:
            logger.warning("FacetType generation failed, continuing without", error=str(ft_error))
            result["warnings"].append(f"FacetType-Generierung übersprungen: {str(ft_error)}")
            result["steps"][-1]["success"] = False
            result["steps"][-1]["result"] = f"Übersprungen: {str(ft_error)}"

        result["facet_types_created"] = facet_types_created
        result["facet_types_count"] = facet_types_count

        # =========================================================================
        # STEP 6/6: Generate Seed Entities from AI Knowledge
        # =========================================================================
        report_progress(6, "Generiere Seed-Entities aus KI-Wissen...")

        seed_entities_created = []
        seed_entities_count = 0
        seed_relations_count = 0
        hierarchy_parent_id = None
        created_entities_map = {}  # name -> Entity for relation lookup

        try:
            # Generate seed entities via AI
            seed_config = await ai_generate_seed_entities(
                user_intent=user_intent,
                entity_type_name=entity_type.name,
                entity_type_description=entity_type.description,
                attribute_schema=entity_type.attribute_schema or {},
                geographic_context=geographic_context,
            )

            suggested_entities = seed_config.get("entities", [])
            hierarchy_config = seed_config.get("hierarchy", {})

            # Debug logging for seed entity generation
            logger.info(
                "AI seed entity generation result",
                entity_count=len(suggested_entities),
                hierarchy_use=hierarchy_config.get("use_hierarchy"),
                hierarchy_parent=hierarchy_config.get("parent_name"),
                hierarchy_reasoning=hierarchy_config.get("hierarchy_reasoning"),
                sample_entity_with_relations=suggested_entities[0] if suggested_entities else None,
            )

            # Handle hierarchy if enabled and suggested
            from unicodedata import normalize as unicode_normalize

            use_hierarchy = hierarchy_config.get("use_hierarchy", False)
            parent_name = hierarchy_config.get("parent_name")

            # Auto-enable hierarchy for specific geographic contexts
            # (not "Deutschland" or empty - those are too broad)
            if settings.feature_entity_hierarchy and geographic_context:
                is_specific_region = (
                    geographic_context != "Deutschland"
                    and geographic_context != "Keine geografische Einschränkung"
                    and len(geographic_context) > 2  # Not just a country code
                )

                if is_specific_region and not use_hierarchy:
                    logger.info(
                        "Auto-enabling hierarchy for specific geographic context",
                        geographic_context=geographic_context,
                    )
                    use_hierarchy = True
                    parent_name = geographic_context

            if settings.feature_entity_hierarchy and use_hierarchy and parent_name:
                # Use AI-suggested parent_type or default to territorial_entity for geographic entities
                parent_type_slug = hierarchy_config.get("parent_entity_type", "territorial_entity")

                # Look up parent entity type
                parent_et_result = await session.execute(select(EntityType).where(EntityType.slug == parent_type_slug))
                parent_entity_type = parent_et_result.scalar_one_or_none()

                # Fallback to territorial_entity if parent type not found
                if not parent_entity_type and parent_type_slug != "territorial_entity":
                    logger.info(
                        "EntityType not found, falling back to territorial_entity",
                        requested_type=parent_type_slug,
                    )
                    parent_type_slug = "territorial_entity"
                    parent_et_result = await session.execute(
                        select(EntityType).where(EntityType.slug == "territorial_entity")
                    )
                    parent_entity_type = parent_et_result.scalar_one_or_none()

                if parent_entity_type:
                    # Look up or create parent entity
                    parent_normalized = unicode_normalize("NFKD", parent_name.lower())
                    parent_result = await session.execute(
                        select(Entity).where(
                            Entity.entity_type_id == parent_entity_type.id,
                            Entity.name_normalized == parent_normalized,
                        )
                    )
                    parent_entity = parent_result.scalar_one_or_none()

                    if not parent_entity:
                        # Create parent entity
                        parent_entity = Entity(
                            id=uuid_module.uuid4(),
                            entity_type_id=parent_entity_type.id,
                            name=parent_name,
                            name_normalized=parent_normalized,
                            slug=generate_slug(parent_name),
                            country="DE",
                            is_active=True,
                            hierarchy_level=0,
                        )
                        session.add(parent_entity)
                        await session.flush()
                        logger.info("Created hierarchy parent entity", name=parent_name)

                    hierarchy_parent_id = parent_entity.id

                    # Enable hierarchy on EntityType
                    entity_type.supports_hierarchy = True

            # Create seed entities
            for entity_data in suggested_entities:
                entity_name = entity_data.get("name", "").strip()

                if not entity_name:
                    continue

                # Generate normalized name and slug
                name_normalized = unicode_normalize("NFKD", entity_name.lower())
                entity_slug = generate_slug(entity_name)

                # Check if entity already exists
                existing_entity = await session.execute(
                    select(Entity).where(
                        Entity.entity_type_id == entity_type.id,
                        Entity.name_normalized == name_normalized,
                    )
                )

                if existing_entity.scalar_one_or_none():
                    # Entity already exists, skip
                    continue

                # Build hierarchy path if parent exists
                hierarchy_path = None
                hierarchy_level = 0
                if hierarchy_parent_id:
                    hierarchy_path = f"/{geographic_context}/{entity_name}"
                    hierarchy_level = 1

                # Create new entity
                new_entity = Entity(
                    id=uuid_module.uuid4(),
                    entity_type_id=entity_type.id,
                    name=entity_name,
                    name_normalized=name_normalized,
                    slug=entity_slug,
                    external_id=entity_data.get("external_id"),
                    core_attributes=entity_data.get("core_attributes", {}),
                    latitude=entity_data.get("latitude"),
                    longitude=entity_data.get("longitude"),
                    admin_level_1=entity_data.get("admin_level_1") or geographic_context,
                    country=entity_data.get("country", "DE"),
                    is_active=True,
                    created_by_id=current_user_id,
                    owner_id=current_user_id,
                    parent_id=hierarchy_parent_id,
                    hierarchy_path=hierarchy_path,
                    hierarchy_level=hierarchy_level,
                )
                session.add(new_entity)
                created_entities_map[entity_name] = new_entity
                seed_entities_created.append(
                    {
                        "id": str(new_entity.id),
                        "name": new_entity.name,
                        "external_id": new_entity.external_id,
                        "relations": entity_data.get("relations", []),
                    }
                )
                seed_entities_count += 1

            await session.flush()

            # Create relations if feature enabled
            if settings.feature_auto_entity_relations:
                logger.info(
                    "Processing relations for seed entities",
                    feature_enabled=settings.feature_auto_entity_relations,
                    entities_with_relations=[
                        {"name": e["name"], "relations_count": len(e.get("relations", []))}
                        for e in seed_entities_created
                    ],
                )
                for entity_info in seed_entities_created:
                    source_entity = created_entities_map.get(entity_info["name"])
                    if not source_entity:
                        continue

                    for rel_data in entity_info.get("relations", []):
                        rel_type_slug = rel_data.get("relation_type", "located_in")
                        target_name = rel_data.get("target_name", "").strip()
                        target_type_slug = rel_data.get("target_type", "territorial_entity")

                        if not target_name:
                            continue

                        # Find or skip target entity
                        target_normalized = unicode_normalize("NFKD", target_name.lower())

                        # Look up target entity type
                        target_et_result = await session.execute(
                            select(EntityType).where(EntityType.slug == target_type_slug)
                        )
                        target_entity_type = target_et_result.scalar_one_or_none()

                        if not target_entity_type:
                            continue

                        # Look up target entity
                        target_result = await session.execute(
                            select(Entity).where(
                                Entity.entity_type_id == target_entity_type.id,
                                Entity.name_normalized == target_normalized,
                            )
                        )
                        target_entity = target_result.scalar_one_or_none()

                        if not target_entity:
                            # Create target entity if it doesn't exist
                            target_entity = Entity(
                                id=uuid_module.uuid4(),
                                entity_type_id=target_entity_type.id,
                                name=target_name,
                                name_normalized=target_normalized,
                                slug=generate_slug(target_name),
                                country="DE",
                                is_active=True,
                            )
                            session.add(target_entity)
                            await session.flush()

                        # Find or create relation type for this entity type combination
                        # First, try to find an existing relation type that matches
                        # source and target entity types
                        rel_type_result = await session.execute(
                            select(RelationType).where(
                                RelationType.slug == rel_type_slug,
                                RelationType.source_entity_type_id == source_entity.entity_type_id,
                                RelationType.target_entity_type_id == target_entity_type.id,
                            )
                        )
                        relation_type = rel_type_result.scalar_one_or_none()

                        if not relation_type:
                            # Check if we have a template relation type with this slug
                            template_result = await session.execute(
                                select(RelationType).where(RelationType.slug == rel_type_slug)
                            )
                            template_result.first()

                            # Create a new relation type for this entity type combination
                            rel_type_names = {
                                "located_in": ("befindet sich in", "enthält"),
                                "member_of": ("ist Mitglied von", "hat Mitglied"),
                                "works_for": ("arbeitet für", "beschäftigt"),
                            }
                            name, name_inverse = rel_type_names.get(
                                rel_type_slug, (rel_type_slug.replace("_", " "), rel_type_slug.replace("_", " "))
                            )

                            # Create unique slug for this entity type combination
                            new_slug = f"{rel_type_slug}_{entity_type.slug}_{target_type_slug}"

                            # Check if this specific combination already exists
                            existing_combo = await session.execute(
                                select(RelationType).where(RelationType.slug == new_slug)
                            )
                            existing_combo_type = existing_combo.scalar_one_or_none()
                            if existing_combo_type:
                                relation_type = existing_combo_type
                            else:
                                relation_type = RelationType(
                                    id=uuid_module.uuid4(),
                                    slug=new_slug,
                                    name=name,
                                    name_inverse=name_inverse,
                                    source_entity_type_id=source_entity.entity_type_id,
                                    target_entity_type_id=target_entity_type.id,
                                    is_active=True,
                                    is_system=False,
                                )
                                session.add(relation_type)
                                await session.flush()
                                logger.info(
                                    "Created new RelationType for entity combination",
                                    slug=new_slug,
                                    source_type=entity_type.slug,
                                    target_type=target_type_slug,
                                )

                        # Check if relation already exists
                        existing_rel = await session.execute(
                            select(EntityRelation).where(
                                EntityRelation.source_entity_id == source_entity.id,
                                EntityRelation.target_entity_id == target_entity.id,
                                EntityRelation.relation_type_id == relation_type.id,
                            )
                        )

                        if not existing_rel.scalar_one_or_none():
                            # Create relation
                            new_relation = EntityRelation(
                                id=uuid_module.uuid4(),
                                source_entity_id=source_entity.id,
                                target_entity_id=target_entity.id,
                                relation_type_id=relation_type.id,
                            )
                            session.add(new_relation)
                            seed_relations_count += 1

                await session.flush()

            # Update step result
            is_complete = seed_config.get("is_complete_list", False)
            total_known = seed_config.get("total_known", seed_entities_count)
            completeness_note = "vollständig" if is_complete else f"({seed_entities_count} von ~{total_known})"
            relation_note = f", {seed_relations_count} Relations" if seed_relations_count > 0 else ""
            hierarchy_note = " (hierarchisch)" if hierarchy_parent_id else ""
            result["steps"][-1]["result"] = (
                f"{seed_entities_count} Seed-Entities erstellt {completeness_note}{relation_note}{hierarchy_note}"
            )

            if seed_config.get("data_quality_note"):
                result["warnings"].append(f"Seed-Entities: {seed_config['data_quality_note']}")

        except Exception as seed_error:
            logger.warning("Seed entity generation failed, continuing without", error=str(seed_error))
            result["warnings"].append(f"Seed-Entity-Generierung übersprungen: {str(seed_error)}")
            result["steps"][-1]["success"] = False
            result["steps"][-1]["result"] = f"Übersprungen: {str(seed_error)}"

        result["seed_entities_created"] = seed_entities_created
        result["seed_entities_count"] = seed_entities_count
        result["seed_relations_count"] = seed_relations_count
        result["hierarchy_parent_id"] = str(hierarchy_parent_id) if hierarchy_parent_id else None
        result["success"] = True

        linked_count + discovered_count
        result["message"] = (
            f"Erfolgreich erstellt: EntityType '{entity_type.name}', "
            f"Category '{category.name}', "
            f"{discovered_count} neue Quellen entdeckt, "
            f"{linked_count} Datenquellen verknüpft, "
            f"{facet_types_count} FacetTypes, "
            f"{seed_entities_count} Seed-Entities"
            f"{f', {seed_relations_count} Relations' if seed_relations_count > 0 else ''}"
        )

        logger.info(
            "AI-powered category setup completed",
            entity_type=entity_type.name,
            category=category.name,
            discovered_sources=discovered_count,
            linked_sources=linked_count,
            facet_types=facet_types_count,
            seed_entities=seed_entities_count,
            seed_relations=seed_relations_count,
            hierarchy_parent=str(hierarchy_parent_id) if hierarchy_parent_id else None,
        )

        return result

    except Exception as e:
        logger.error("Failed to create category setup with AI", error=str(e))
        result["message"] = f"Fehler: {str(e)}"
        return result


async def create_category_setup(
    session: AsyncSession,
    setup_data: dict[str, Any],
    current_user_id: UUID | None = None,
) -> dict[str, Any]:
    """Execute CREATE_CATEGORY_SETUP operation - creates EntityType + Category + links DataSources."""
    result = {
        "success": False,
        "message": "",
        "entity_type_id": None,
        "entity_type_name": None,
        "entity_type_slug": None,
        "category_id": None,
        "category_name": None,
        "category_slug": None,
        "linked_data_source_count": 0,
        "ai_extraction_prompt": "",
        "warnings": [],
    }

    try:
        # 1. Extract and validate data
        name = setup_data.get("name", "").strip()
        purpose = setup_data.get("purpose", "").strip()
        user_intent = setup_data.get("user_intent", purpose)
        search_focus = setup_data.get("search_focus", "general")
        search_terms = setup_data.get("search_terms", [])
        geographic_filter = setup_data.get("geographic_filter", {})
        extraction_handler = setup_data.get("extraction_handler", "default")

        if not name:
            result["message"] = "Name ist erforderlich"
            return result

        if not purpose:
            purpose = user_intent or f"Automatisch erstellt: {name}"

        # 2. Generate slug
        slug = generate_slug(name)

        # 3. Check for duplicate EntityType (exact match)
        existing_et = await session.execute(
            select(EntityType).where(or_(EntityType.name == name, EntityType.slug == slug))
        )
        if existing_et.scalar():
            result["message"] = f"EntityType '{name}' existiert bereits"
            return result

        # 3b. Check for semantically similar EntityTypes (AI-based)
        from app.utils.similarity import find_similar_categories, find_similar_entity_types, get_hierarchy_mapping

        # Check if this is a hierarchy level of an existing type
        hierarchy_mapping = get_hierarchy_mapping(name)
        if hierarchy_mapping:
            parent_slug = hierarchy_mapping["parent_type_slug"]
            parent_result = await session.execute(
                select(EntityType).where(EntityType.slug == parent_slug, EntityType.is_active.is_(True))
            )
            parent_type = parent_result.scalar_one_or_none()
            if parent_type:
                level_name = hierarchy_mapping["level_name"]
                result["message"] = (
                    f"'{level_name}' ist eine Hierarchie-Ebene von '{parent_type.name}'. "
                    f"Verwende den bestehenden Typ statt einen neuen zu erstellen."
                )
                return result

        # Check for semantically similar types
        similar_types = await find_similar_entity_types(session, name, threshold=0.85)
        if similar_types:
            best_match, score, reason = similar_types[0]
            result["message"] = f"Ähnlicher EntityType '{best_match.name}' existiert bereits ({reason})"
            result["warnings"].append(f"Verwende stattdessen: {best_match.slug}")
            return result

        # 4. Generate attribute schema
        attribute_schema = generate_entity_type_schema(search_focus, user_intent)

        # 4b. Generate URL patterns for crawling
        url_include_patterns, url_exclude_patterns = generate_url_patterns(search_focus, user_intent)

        # 4c. Expand search terms (e.g., "Entscheider" -> concrete roles)
        expanded_search_terms = expand_search_terms(search_focus, search_terms)

        # 5. Create EntityType
        entity_type = EntityType(
            id=uuid_module.uuid4(),
            name=name,
            slug=slug,
            name_plural=f"{name}",  # Same as name for custom types
            description=f"Automatisch erstellt: {user_intent}",
            icon="mdi-calendar" if search_focus == "event_attendance" else "mdi-folder",
            color="#2196F3" if search_focus == "event_attendance" else "#4CAF50",
            display_order=100,  # After system types
            is_primary=True,
            supports_hierarchy=False,
            attribute_schema=attribute_schema,
            is_active=True,
            is_system=False,
            is_public=True,  # Always visible in frontend
            created_by_id=current_user_id,
            owner_id=current_user_id,
        )
        session.add(entity_type)
        await session.flush()

        # Generate embedding for semantic similarity search
        from app.utils.similarity import generate_embedding

        try:
            embedding = await generate_embedding(name)
            if embedding:
                entity_type.name_embedding = embedding
        except Exception as e:
            logger.warning("Failed to generate embedding for EntityType", name=name, error=str(e))

        logger.info(
            "Created EntityType",
            entity_type_id=str(entity_type.id),
            name=entity_type.name,
        )

        # 6. Generate AI extraction prompt
        ai_prompt = generate_ai_extraction_prompt(user_intent, search_focus, name)

        # 7. Determine extraction handler
        if search_focus == "event_attendance":
            extraction_handler = "event"

        # 8. Check for duplicate Category (exact match)
        existing_cat_result = await session.execute(
            select(Category).where(or_(Category.name == name, Category.slug == slug))
        )
        existing_category = existing_cat_result.scalar()

        # 8b. Check for semantically similar Categories (AI-based)
        if not existing_category:
            similar_categories = await find_similar_categories(session, name, threshold=0.85)
            if similar_categories:
                existing_category = similar_categories[0][0]
                logger.info(
                    "Found semantically similar Category",
                    new_name=name,
                    existing_name=existing_category.name,
                    similarity=round(similar_categories[0][1], 3),
                )

        # 9. Use existing Category or create new one
        if existing_category:
            # Use existing category instead of creating a new one
            category = existing_category
            logger.info(
                "Using existing Category instead of creating duplicate",
                category_id=str(category.id),
                category_name=category.name,
                requested_name=name,
            )
            result["warnings"].append(
                f"Bestehende Kategorie '{category.name}' wird verwendet statt '{name}' neu zu erstellen"
            )
        else:
            # Create new Category with URL patterns and expanded search terms
            category = Category(
                id=uuid_module.uuid4(),
                name=name,
                slug=slug,
                description=f"Automatisch erstellt: {user_intent}",
                purpose=purpose,
                search_terms=expanded_search_terms or ["Event", "Veranstaltung", "Konferenz", "Tagung"],
                document_types=["html", "pdf"],
                url_include_patterns=url_include_patterns,
                url_exclude_patterns=url_exclude_patterns,
                languages=["de"],
                ai_extraction_prompt=ai_prompt,
                extraction_handler=extraction_handler,
                schedule_cron="0 2 * * *",
                is_active=True,
                is_public=True,  # Always visible in frontend
                created_by_id=current_user_id,
                owner_id=current_user_id,
                target_entity_type_id=entity_type.id,
            )
            session.add(category)
        await session.flush()

        logger.info(
            "Created Category",
            category_id=str(category.id),
            name=category.name,
        )

        # 10. Find and link matching DataSources
        matching_sources = await find_matching_data_sources(session, geographic_filter)

        linked_count = 0
        for source in matching_sources:
            # Check if link already exists
            existing_link = await session.execute(
                select(DataSourceCategory).where(
                    DataSourceCategory.data_source_id == source.id,
                    DataSourceCategory.category_id == category.id,
                )
            )
            if not existing_link.scalar():
                link = DataSourceCategory(
                    id=uuid_module.uuid4(),
                    data_source_id=source.id,
                    category_id=category.id,
                    is_primary=False,
                )
                session.add(link)
                linked_count += 1

        await session.flush()

        # 11. Build result
        result["success"] = True
        result["message"] = (
            f"Setup erstellt: EntityType '{entity_type.name}', Category '{category.name}', {linked_count} DataSources verknüpft"
        )
        result["entity_type_id"] = str(entity_type.id)
        result["entity_type_name"] = entity_type.name
        result["entity_type_slug"] = entity_type.slug
        result["category_id"] = str(category.id)
        result["category_name"] = category.name
        result["category_slug"] = category.slug
        result["linked_data_source_count"] = linked_count
        result["ai_extraction_prompt"] = ai_prompt

        if linked_count == 0:
            admin_level = geographic_filter.get("admin_level_1") or geographic_filter.get("admin_level_1_alias")
            result["warnings"].append(
                f"Keine DataSources für Filter '{admin_level}' gefunden. Bitte DataSources manuell hinzufügen."
            )

        return result

    except Exception as e:
        logger.error("Category setup failed", error=str(e), exc_info=True)
        result["message"] = f"Fehler: {str(e)}"
        return result
