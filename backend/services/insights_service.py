"""Insights Service - Proactive insights for the AI Assistant."""

import structlog
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Entity,
    EntityType,
    FacetType,
    FacetValue,
)
from app.schemas.assistant import AssistantContext

logger = structlog.get_logger()


class Insight:
    """Represents a single insight for the user."""

    def __init__(
        self,
        insight_type: str,
        icon: str,
        message: str,
        action: Optional[Dict[str, Any]] = None,
        priority: int = 0,
        color: str = "primary"
    ):
        self.type = insight_type
        self.icon = icon
        self.message = message
        self.action = action or {}
        self.priority = priority
        self.color = color

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "icon": self.icon,
            "message": self.message,
            "action": self.action,
            "priority": self.priority,
            "color": self.color,
        }


class InsightsService:
    """Service for generating proactive insights based on user context and data."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_insights(
        self,
        context: AssistantContext,
        user_id: Optional[UUID] = None,
        last_login: Optional[datetime] = None,
        language: str = "de"
    ) -> List[Dict[str, Any]]:
        """
        Get contextual insights for the current user.

        Args:
            context: Current app context
            user_id: Optional user ID for personalized insights
            last_login: User's last login timestamp for new data detection
            language: Language for messages ('de' or 'en')

        Returns:
            List of insight dictionaries
        """
        insights: List[Insight] = []

        # 1. New data insights (since last login)
        if last_login:
            new_data_insights = await self._get_new_data_insights(last_login, language)
            insights.extend(new_data_insights)

        # 2. Context-based insights
        if context.current_entity_id:
            entity_insights = await self._get_entity_insights(
                context.current_entity_id,
                context.current_entity_type,
                language
            )
            insights.extend(entity_insights)
        elif context.view_mode.value == "dashboard":
            dashboard_insights = await self._get_dashboard_insights(language)
            insights.extend(dashboard_insights)
        elif context.view_mode.value == "list" and context.current_entity_type:
            list_insights = await self._get_list_insights(
                context.current_entity_type,
                language
            )
            insights.extend(list_insights)

        # 3. General data quality insights
        quality_insights = await self._get_data_quality_insights(language)
        insights.extend(quality_insights)

        # Sort by priority and return top 3
        insights.sort(key=lambda x: x.priority, reverse=True)
        return [i.to_dict() for i in insights[:3]]

    async def _get_new_data_insights(
        self,
        since: datetime,
        language: str
    ) -> List[Insight]:
        """Get insights about new data since a timestamp."""
        insights = []

        try:
            # Count new facet values (pain points specifically)
            result = await self.db.execute(
                select(func.count(FacetValue.id))
                .where(FacetValue.created_at >= since)
            )
            new_facets = result.scalar() or 0

            if new_facets > 0:
                msg = (
                    f"{new_facets} neue Facet-Werte seit deinem letzten Login"
                    if language == "de"
                    else f"{new_facets} new facet values since your last login"
                )
                insights.append(Insight(
                    insight_type="new_data",
                    icon="mdi-bell-ring",
                    message=msg,
                    action={"type": "query", "value": "Zeige neue Änderungen"},
                    priority=8,
                    color="info"
                ))

            # Count new entities
            result = await self.db.execute(
                select(func.count(Entity.id))
                .where(Entity.created_at >= since)
            )
            new_entities = result.scalar() or 0

            if new_entities > 0:
                msg = (
                    f"{new_entities} neue Entities hinzugefügt"
                    if language == "de"
                    else f"{new_entities} new entities added"
                )
                insights.append(Insight(
                    insight_type="new_data",
                    icon="mdi-plus-circle",
                    message=msg,
                    action={"type": "query", "value": "Zeige neue Entities"},
                    priority=7,
                    color="success"
                ))

        except Exception as e:
            logger.error("new_data_insights_error", error=str(e))

        return insights

    async def _get_entity_insights(
        self,
        entity_id: str,
        entity_type: Optional[str],
        language: str
    ) -> List[Insight]:
        """Get insights specific to the current entity."""
        insights = []

        try:
            # Get entity
            result = await self.db.execute(
                select(Entity)
                .options(selectinload(Entity.entity_type))
                .where(Entity.id == entity_id)
            )
            entity = result.scalar_one_or_none()

            if not entity:
                return insights

            # Count facets
            result = await self.db.execute(
                select(func.count(FacetValue.id))
                .where(FacetValue.entity_id == entity.id)
            )
            facet_count = result.scalar() or 0

            if facet_count == 0:
                msg = (
                    "Diese Entity hat noch keine Facets. Möchtest du welche hinzufügen?"
                    if language == "de"
                    else "This entity has no facets yet. Would you like to add some?"
                )
                insights.append(Insight(
                    insight_type="action_needed",
                    icon="mdi-alert-circle-outline",
                    message=msg,
                    action={"type": "navigate", "value": f"/entities/{entity_type}/{entity.slug}/edit"},
                    priority=6,
                    color="warning"
                ))

            # Check for unverified facets
            result = await self.db.execute(
                select(func.count(FacetValue.id))
                .where(
                    and_(
                        FacetValue.entity_id == entity.id,
                        FacetValue.human_verified.is_(False)
                    )
                )
            )
            unverified = result.scalar() or 0

            if unverified > 0:
                msg = (
                    f"{unverified} Facet-Werte warten auf Verifizierung"
                    if language == "de"
                    else f"{unverified} facet values pending verification"
                )
                insights.append(Insight(
                    insight_type="action_needed",
                    icon="mdi-check-circle-outline",
                    message=msg,
                    action={"type": "query", "value": f"Zeige ungeprüfte Facets von {entity.name}"},
                    priority=7,
                    color="warning"
                ))

        except Exception as e:
            logger.error("entity_insights_error", error=str(e))

        return insights

    async def _get_dashboard_insights(self, language: str) -> List[Insight]:
        """Get insights for the dashboard view."""
        insights = []

        try:
            # Total entity count
            result = await self.db.execute(select(func.count(Entity.id)))
            total_entities = result.scalar() or 0

            # Total facet count
            result = await self.db.execute(select(func.count(FacetValue.id)))
            total_facets = result.scalar() or 0

            msg = (
                f"System enthält {total_entities} Entities mit {total_facets} Facet-Werten"
                if language == "de"
                else f"System contains {total_entities} entities with {total_facets} facet values"
            )
            insights.append(Insight(
                insight_type="info",
                icon="mdi-database",
                message=msg,
                action={"type": "query", "value": "Zeige Übersicht"},
                priority=3,
                color="primary"
            ))

            # Recent activity (last 7 days)
            week_ago = datetime.now(timezone.utc) - timedelta(days=7)
            result = await self.db.execute(
                select(func.count(FacetValue.id))
                .where(FacetValue.created_at >= week_ago)
            )
            recent_changes = result.scalar() or 0

            if recent_changes > 0:
                msg = (
                    f"{recent_changes} Änderungen in den letzten 7 Tagen"
                    if language == "de"
                    else f"{recent_changes} changes in the last 7 days"
                )
                insights.append(Insight(
                    insight_type="activity",
                    icon="mdi-chart-line",
                    message=msg,
                    action={"type": "query", "value": "Zeige letzte Aktivitäten"},
                    priority=5,
                    color="success"
                ))

        except Exception as e:
            logger.error("dashboard_insights_error", error=str(e))

        return insights

    async def _get_list_insights(
        self,
        entity_type: str,
        language: str
    ) -> List[Insight]:
        """Get insights for entity list views."""
        insights = []

        try:
            # Get entity type
            result = await self.db.execute(
                select(EntityType).where(EntityType.slug == entity_type)
            )
            etype = result.scalar_one_or_none()

            if not etype:
                return insights

            # Count entities of this type
            result = await self.db.execute(
                select(func.count(Entity.id))
                .where(Entity.type_id == etype.id)
            )
            count = result.scalar() or 0

            type_name = etype.name_plural or etype.name
            msg = (
                f"{count} {type_name} im System"
                if language == "de"
                else f"{count} {type_name} in the system"
            )
            insights.append(Insight(
                insight_type="info",
                icon="mdi-format-list-bulleted",
                message=msg,
                action={"type": "query", "value": f"Zeige alle {type_name}"},
                priority=2,
                color="primary"
            ))

        except Exception as e:
            logger.error("list_insights_error", error=str(e))

        return insights

    async def _get_data_quality_insights(self, language: str) -> List[Insight]:
        """Get insights about data quality issues."""
        insights = []

        try:
            # Count entities without facets
            subquery = (
                select(FacetValue.entity_id)
                .distinct()
            )
            result = await self.db.execute(
                select(func.count(Entity.id))
                .where(Entity.id.not_in(subquery))
            )
            empty_entities = result.scalar() or 0

            if empty_entities > 10:
                msg = (
                    f"{empty_entities} Entities haben noch keine Facets"
                    if language == "de"
                    else f"{empty_entities} entities have no facets yet"
                )
                insights.append(Insight(
                    insight_type="data_quality",
                    icon="mdi-alert-outline",
                    message=msg,
                    action={"type": "query", "value": "Zeige Entities ohne Facets"},
                    priority=4,
                    color="warning"
                ))

        except Exception as e:
            logger.error("data_quality_insights_error", error=str(e))

        return insights
