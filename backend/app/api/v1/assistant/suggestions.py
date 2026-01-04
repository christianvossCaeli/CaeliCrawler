"""Suggestions and Insights API endpoints for the AI Chat Assistant."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user_optional
from app.database import get_session
from app.models import EntityType as EntityTypeModel
from app.models import FacetType
from app.models.user import User
from app.schemas.assistant import SLASH_COMMANDS, SlashCommand

router = APIRouter(tags=["assistant-suggestions"])


@router.get("/commands", response_model=list[SlashCommand])
async def get_commands() -> list[SlashCommand]:
    """
    Get list of available slash commands.

    Returns all slash commands that can be used in the assistant chat.
    """
    return SLASH_COMMANDS


@router.get("/suggestions")
async def get_suggestions(
    route: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Get contextual suggestions based on current location.

    Returns suggested queries and actions based on where the user is in the app.
    Dynamically includes available facet types in suggestions.
    """
    # Load active facet types for dynamic suggestions
    facet_result = await session.execute(
        select(FacetType)
        .where(FacetType.is_active.is_(True))
        .order_by(FacetType.display_order)
        .limit(5)
    )
    facet_types = facet_result.scalars().all()
    primary_facet = facet_types[0] if facet_types else None

    suggestions = []

    if entity_id:
        # On entity detail page
        suggestions = [
            {"label": "Zusammenfassung", "query": "/summary"},
        ]
        # Add dynamic facet suggestions
        for ft in facet_types[:2]:
            suggestions.append({"label": ft.name, "query": f"Zeige {ft.name_plural or ft.name}"})
        suggestions.append({"label": "Relationen", "query": "Zeige alle Relationen"})
    elif entity_type:
        # On entity list page - load entity type name
        type_result = await session.execute(
            select(EntityTypeModel).where(EntityTypeModel.slug == entity_type)
        )
        et = type_result.scalar_one_or_none()
        type_name = et.name_plural if et else entity_type

        suggestions = [
            {"label": f"Alle {type_name}", "query": f"Zeige alle {type_name}"},
        ]
        # Add dynamic facet filter suggestions
        if primary_facet:
            suggestions.append({
                "label": f"Mit {primary_facet.name_plural or primary_facet.name}",
                "query": f"{type_name} mit {primary_facet.name_plural or primary_facet.name}"
            })
        suggestions.append({"label": "Suchen", "query": "/search "})
    elif "dashboard" in route or route == "/":
        # On dashboard
        suggestions = [
            {"label": "Übersicht", "query": "Zeige mir eine Übersicht"},
        ]
        # Add dynamic facet suggestions
        for ft in facet_types[:2]:
            suggestions.append({
                "label": f"Aktuelle {ft.name_plural or ft.name}",
                "query": f"Zeige aktuelle {ft.name_plural or ft.name}"
            })
        suggestions.append({"label": "Hilfe", "query": "/help"})
    else:
        # Default
        suggestions = [
            {"label": "Hilfe", "query": "/help"},
            {"label": "Suchen", "query": "/search "},
        ]

    return {"suggestions": suggestions, "available_facet_types": [
        {"slug": ft.slug, "name": ft.name, "name_plural": ft.name_plural, "icon": ft.icon}
        for ft in facet_types
    ]}


@router.get("/insights")
async def get_insights(
    route: str,
    view_mode: str = "unknown",
    entity_type: str | None = None,
    entity_id: str | None = None,
    language: str = Query("de", description="Language for insights: de or en"),
    session: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user_optional),
) -> dict:
    """
    Get proactive insights based on current context.

    Returns contextual insights and suggestions based on:
    - Current view mode (dashboard, list, detail)
    - Current entity being viewed
    - Recent data changes
    - Data quality indicators

    Maximum 3 insights are returned, sorted by priority.
    """
    from app.schemas.assistant import AssistantContext, ViewMode
    from services.insights_service import InsightsService

    # Build context
    context = AssistantContext(
        current_route=route,
        current_entity_id=entity_id,
        current_entity_type=entity_type,
        current_entity_name=None,
        view_mode=ViewMode(view_mode) if view_mode in [e.value for e in ViewMode] else ViewMode.UNKNOWN,
        available_actions=[]
    )

    # Get user's last login for new data detection
    last_login = None
    if current_user:
        last_login = current_user.last_login

    # Validate language
    valid_language = language if language in ("de", "en") else "de"

    # Get insights
    insights_service = InsightsService(session)
    insights = await insights_service.get_user_insights(
        context=context,
        user_id=current_user.id if current_user else None,
        last_login=last_login,
        language=valid_language
    )

    return {"insights": insights}
