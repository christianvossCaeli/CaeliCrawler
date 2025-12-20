"""Category setup operations for Smart Query Service."""

import uuid as uuid_module
from typing import Any, Callable, Dict, Optional
from uuid import UUID

import structlog
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EntityType, Category, DataSourceCategory

from .geographic_utils import resolve_geographic_alias, expand_search_terms
from .schema_generator import (
    generate_entity_type_schema,
    generate_ai_extraction_prompt,
    generate_url_patterns,
)
from .ai_generation import (
    ai_generate_entity_type_config,
    ai_generate_category_config,
    ai_generate_crawl_config,
)
from .crawl_operations import find_matching_data_sources
from .utils import generate_slug

logger = structlog.get_logger()


async def create_category_setup_with_ai(
    session: AsyncSession,
    user_intent: str,
    geographic_filter: Dict[str, Any],
    current_user_id: Optional[UUID] = None,
    progress_callback: Optional[Callable] = None,
) -> Dict[str, Any]:
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
        "ai_extraction_prompt": "",
        "url_patterns": {},
        "search_terms": [],
        "warnings": [],
    }

    def report_progress(step: int, message: str, success: bool = True):
        result["steps"].append({
            "step": step,
            "total": 3,
            "message": message,
            "success": success,
        })
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

        # Check for duplicates
        existing_et = await session.execute(
            select(EntityType).where(
                or_(EntityType.name == name, EntityType.slug == slug)
            )
        )
        if existing_et.scalar():
            # Add suffix to make unique
            name = f"{name} ({geographic_context})"
            slug = generate_slug(name)

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
            is_public=False,
            created_by_id=current_user_id,
            owner_id=current_user_id,
        )
        session.add(entity_type)
        await session.flush()

        result["entity_type_id"] = str(entity_type.id)
        result["entity_type_name"] = entity_type.name
        result["entity_type_slug"] = entity_type.slug
        result["steps"][-1]["result"] = f"EntityType '{name}' erstellt"

        # =========================================================================
        # STEP 2/3: Generate Category Configuration
        # =========================================================================
        report_progress(2, "Generiere Category & AI-Extraktions-Prompt...")

        cat_config = await ai_generate_category_config(
            user_intent,
            entity_type.name,
            entity_type.description,
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
        # CREATE CATEGORY
        # =========================================================================
        cat_name = name
        cat_slug = slug

        existing_cat = await session.execute(
            select(Category).where(
                or_(Category.name == cat_name, Category.slug == cat_slug)
            )
        )
        if existing_cat.scalar():
            cat_name = f"{name} (Crawl)"
            cat_slug = f"{slug}-crawl"

        category = Category(
            id=uuid_module.uuid4(),
            name=cat_name,
            slug=cat_slug,
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
            is_public=False,
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
        # LINK DATA SOURCES
        # =========================================================================
        matching_sources = await find_matching_data_sources(session, geographic_filter)

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
        result["success"] = True
        result["message"] = f"Erfolgreich erstellt: EntityType '{entity_type.name}', Category '{category.name}', {linked_count} Datenquellen verknüpft"

        logger.info(
            "AI-powered category setup completed",
            entity_type=entity_type.name,
            category=category.name,
            sources=linked_count,
        )

        return result

    except Exception as e:
        logger.error("Failed to create category setup with AI", error=str(e))
        result["message"] = f"Fehler: {str(e)}"
        return result


async def create_category_setup(
    session: AsyncSession,
    setup_data: Dict[str, Any],
    current_user_id: Optional[UUID] = None,
) -> Dict[str, Any]:
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

        # 3. Check for duplicate EntityType
        existing_et = await session.execute(
            select(EntityType).where(
                or_(EntityType.name == name, EntityType.slug == slug)
            )
        )
        if existing_et.scalar():
            result["message"] = f"EntityType '{name}' existiert bereits"
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
            is_public=False,  # Private by default
            created_by_id=current_user_id,
            owner_id=current_user_id,
        )
        session.add(entity_type)
        await session.flush()

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

        # 8. Check for duplicate Category
        existing_cat = await session.execute(
            select(Category).where(
                or_(Category.name == name, Category.slug == slug)
            )
        )
        if existing_cat.scalar():
            # Use a slightly different name/slug for category
            cat_name = f"{name} (Crawl)"
            cat_slug = f"{slug}-crawl"
        else:
            cat_name = name
            cat_slug = slug

        # 9. Create Category with URL patterns and expanded search terms
        category = Category(
            id=uuid_module.uuid4(),
            name=cat_name,
            slug=cat_slug,
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
            is_public=False,  # Private by default
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
        result["message"] = f"Setup erstellt: EntityType '{entity_type.name}', Category '{category.name}', {linked_count} DataSources verknüpft"
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
                f"Keine DataSources für Filter '{admin_level}' gefunden. "
                "Bitte DataSources manuell hinzufügen."
            )

        return result

    except Exception as e:
        logger.error("Category setup failed", error=str(e), exc_info=True)
        result["message"] = f"Fehler: {str(e)}"
        return result
