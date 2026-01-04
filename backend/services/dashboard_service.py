"""Dashboard Service - Statistics and preferences for the dashboard."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AITask,
    AITaskStatus,
    AuditAction,
    AuditLog,
    CrawlJob,
    Document,
    Entity,
    EntityType,
    FacetType,
    FacetValue,
    JobStatus,
    ProcessingStatus,
    User,
)
from app.models.user_dashboard import UserDashboardPreference
from app.schemas.dashboard import (
    ActivityFeedResponse,
    ActivityItem,
    AITaskStats,
    ChartDataPoint,
    ChartDataResponse,
    CrawlerStats,
    DashboardPreferencesResponse,
    DashboardPreferencesUpdate,
    DashboardStatsResponse,
    DocumentStats,
    EntityStats,
    FacetStats,
    InsightItem,
    InsightsResponse,
    WidgetConfig,
    WidgetPosition,
)

logger = structlog.get_logger()


# Default widget configuration for new users
DEFAULT_WIDGETS = [
    WidgetConfig(
        id="stats-entities",
        type="stats-entities",
        enabled=True,
        position=WidgetPosition(x=0, y=0, w=1, h=1),
    ),
    WidgetConfig(
        id="stats-facets",
        type="stats-facets",
        enabled=True,
        position=WidgetPosition(x=1, y=0, w=1, h=1),
    ),
    WidgetConfig(
        id="stats-documents",
        type="stats-documents",
        enabled=True,
        position=WidgetPosition(x=2, y=0, w=1, h=1),
    ),
    WidgetConfig(
        id="stats-crawler",
        type="stats-crawler",
        enabled=True,
        position=WidgetPosition(x=3, y=0, w=1, h=1),
    ),
    WidgetConfig(
        id="activity-feed",
        type="activity-feed",
        enabled=True,
        position=WidgetPosition(x=0, y=1, w=2, h=2),
    ),
    WidgetConfig(
        id="crawler-status",
        type="crawler-status",
        enabled=True,
        position=WidgetPosition(x=2, y=1, w=2, h=2),
    ),
    WidgetConfig(
        id="insights",
        type="insights",
        enabled=True,
        position=WidgetPosition(x=0, y=3, w=2, h=1),
    ),
    WidgetConfig(
        id="chart-distribution",
        type="chart-distribution",
        enabled=True,
        position=WidgetPosition(x=2, y=3, w=2, h=1),
    ),
]


class DashboardService:
    """Service for dashboard data and user preferences."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========== Preferences Management ==========

    async def get_preferences(self, user_id: UUID) -> DashboardPreferencesResponse:
        """Get dashboard preferences for a user, creating defaults if needed."""
        result = await self.db.execute(
            select(UserDashboardPreference).where(UserDashboardPreference.user_id == user_id)
        )
        pref = result.scalar_one_or_none()

        if pref is None:
            # Create default preferences
            pref = await self._create_default_preferences(user_id)

        widgets = [WidgetConfig(**w) for w in pref.widget_config.get("widgets", [])]

        return DashboardPreferencesResponse(
            widgets=widgets,
            updated_at=pref.updated_at,
        )

    async def update_preferences(
        self, user_id: UUID, update: DashboardPreferencesUpdate
    ) -> DashboardPreferencesResponse:
        """Update dashboard preferences for a user."""
        result = await self.db.execute(
            select(UserDashboardPreference).where(UserDashboardPreference.user_id == user_id)
        )
        pref = result.scalar_one_or_none()

        widget_config = {
            "widgets": [w.model_dump() for w in update.widgets],
            "version": 1,
        }

        if pref is None:
            pref = UserDashboardPreference(
                user_id=user_id,
                widget_config=widget_config,
            )
            self.db.add(pref)
        else:
            pref.widget_config = widget_config

        await self.db.commit()
        await self.db.refresh(pref)

        return DashboardPreferencesResponse(
            widgets=update.widgets,
            updated_at=pref.updated_at,
        )

    async def _create_default_preferences(self, user_id: UUID) -> UserDashboardPreference:
        """Create default preferences for a new user."""
        widget_config = {
            "widgets": [w.model_dump() for w in DEFAULT_WIDGETS],
            "version": 1,
        }
        pref = UserDashboardPreference(
            user_id=user_id,
            widget_config=widget_config,
        )
        self.db.add(pref)
        await self.db.commit()
        await self.db.refresh(pref)
        return pref

    # ========== Statistics ==========

    async def get_stats(self) -> DashboardStatsResponse:
        """Get aggregated statistics for the dashboard."""
        entity_stats = await self._get_entity_stats()
        facet_stats = await self._get_facet_stats()
        document_stats = await self._get_document_stats()
        crawler_stats = await self._get_crawler_stats()
        ai_stats = await self._get_ai_task_stats()

        return DashboardStatsResponse(
            entities=entity_stats,
            facets=facet_stats,
            documents=document_stats,
            crawler=crawler_stats,
            ai_tasks=ai_stats,
            updated_at=datetime.now(UTC),
        )

    async def _get_entity_stats(self) -> EntityStats:
        """Get entity statistics.

        Only counts entities belonging to ACTIVE EntityTypes to match
        what users see in the EntitiesView.
        """
        try:
            # Get active entity type IDs first
            active_et_result = await self.db.execute(select(EntityType.id).where(EntityType.is_active.is_(True)))
            active_et_ids = [row[0] for row in active_et_result.fetchall()]

            # Total count (only from active entity types)
            result = await self.db.execute(
                select(func.count(Entity.id)).where(Entity.entity_type_id.in_(active_et_ids))
            )
            total = result.scalar() or 0

            # Active count (entities that are active AND belong to active entity types)
            result = await self.db.execute(
                select(func.count(Entity.id))
                .where(Entity.is_active.is_(True))
                .where(Entity.entity_type_id.in_(active_et_ids))
            )
            active = result.scalar() or 0

            # By type (only active entity types)
            result = await self.db.execute(
                select(EntityType.name, func.count(Entity.id))
                .join(Entity, Entity.entity_type_id == EntityType.id)
                .where(EntityType.is_active.is_(True))
                .group_by(EntityType.id, EntityType.name)
            )
            by_type = {row[0]: row[1] for row in result.all()}

            return EntityStats(
                total=total,
                active=active,
                inactive=total - active,
                by_type=by_type,
            )
        except Exception as e:
            logger.error("entity_stats_error", error=str(e))
            return EntityStats(total=0, active=0, inactive=0, by_type={})

    async def _get_facet_stats(self) -> FacetStats:
        """Get facet value statistics."""
        try:
            # Total count
            result = await self.db.execute(select(func.count(FacetValue.id)))
            total = result.scalar() or 0

            # Verified count
            result = await self.db.execute(select(func.count(FacetValue.id)).where(FacetValue.human_verified.is_(True)))
            verified = result.scalar() or 0

            # By type
            result = await self.db.execute(
                select(FacetType.name, func.count(FacetValue.id))
                .join(FacetValue, FacetValue.facet_type_id == FacetType.id)
                .group_by(FacetType.id, FacetType.name)
            )
            by_type = {row[0]: row[1] for row in result.all()}

            verification_rate = (verified / total * 100) if total > 0 else 0.0

            return FacetStats(
                total=total,
                verified=verified,
                verification_rate=round(verification_rate, 1),
                by_type=by_type,
            )
        except Exception as e:
            logger.error("facet_stats_error", error=str(e))
            return FacetStats(total=0, verified=0, verification_rate=0.0, by_type={})

    async def _get_document_stats(self) -> DocumentStats:
        """Get document processing statistics."""
        try:
            # Total count
            result = await self.db.execute(select(func.count(Document.id)))
            total = result.scalar() or 0

            # By status
            result = await self.db.execute(
                select(Document.processing_status, func.count(Document.id)).group_by(Document.processing_status)
            )
            by_status = {row[0].value: row[1] for row in result.all()}

            # Processing rate (completed / total)
            completed = by_status.get(ProcessingStatus.COMPLETED.value, 0)
            processing_rate = (completed / total * 100) if total > 0 else 0.0

            return DocumentStats(
                total=total,
                by_status=by_status,
                processing_rate=round(processing_rate, 1),
            )
        except Exception as e:
            logger.error("document_stats_error", error=str(e))
            return DocumentStats(total=0, by_status={}, processing_rate=0.0)

    async def _get_crawler_stats(self) -> CrawlerStats:
        """Get crawler job statistics."""
        try:
            # Total jobs
            result = await self.db.execute(select(func.count(CrawlJob.id)))
            total_jobs = result.scalar() or 0

            # Running jobs
            result = await self.db.execute(select(func.count(CrawlJob.id)).where(CrawlJob.status == JobStatus.RUNNING))
            running = result.scalar() or 0

            # Completed jobs
            result = await self.db.execute(
                select(func.count(CrawlJob.id)).where(CrawlJob.status == JobStatus.COMPLETED)
            )
            completed = result.scalar() or 0

            # Failed jobs
            result = await self.db.execute(select(func.count(CrawlJob.id)).where(CrawlJob.status == JobStatus.FAILED))
            failed = result.scalar() or 0

            # Total documents
            result = await self.db.execute(select(func.sum(CrawlJob.documents_found)))
            total_docs = result.scalar() or 0

            # Average duration (calculate in SQL since duration_seconds is a Python property)
            result = await self.db.execute(
                select(func.avg(func.extract("epoch", CrawlJob.completed_at - CrawlJob.started_at))).where(
                    CrawlJob.status == JobStatus.COMPLETED,
                    CrawlJob.completed_at.is_not(None),
                    CrawlJob.started_at.is_not(None),
                )
            )
            avg_duration = result.scalar()

            return CrawlerStats(
                total_jobs=total_jobs,
                running_jobs=running,
                completed_jobs=completed,
                failed_jobs=failed,
                total_documents=total_docs,
                avg_duration_seconds=float(avg_duration) if avg_duration else None,
            )
        except Exception as e:
            logger.error("crawler_stats_error", error=str(e))
            return CrawlerStats(
                total_jobs=0,
                running_jobs=0,
                completed_jobs=0,
                failed_jobs=0,
                total_documents=0,
                avg_duration_seconds=None,
            )

    async def _get_ai_task_stats(self) -> AITaskStats:
        """Get AI task statistics."""
        try:
            # Total tasks
            result = await self.db.execute(select(func.count(AITask.id)))
            total = result.scalar() or 0

            # Running
            result = await self.db.execute(select(func.count(AITask.id)).where(AITask.status == AITaskStatus.RUNNING))
            running = result.scalar() or 0

            # Completed
            result = await self.db.execute(select(func.count(AITask.id)).where(AITask.status == AITaskStatus.COMPLETED))
            completed = result.scalar() or 0

            # Failed
            result = await self.db.execute(select(func.count(AITask.id)).where(AITask.status == AITaskStatus.FAILED))
            failed = result.scalar() or 0

            # Average confidence
            result = await self.db.execute(
                select(func.avg(AITask.avg_confidence)).where(AITask.status == AITaskStatus.COMPLETED)
            )
            avg_conf = result.scalar()

            return AITaskStats(
                total=total,
                running=running,
                completed=completed,
                failed=failed,
                avg_confidence=float(avg_conf) if avg_conf else None,
            )
        except Exception as e:
            logger.error("ai_task_stats_error", error=str(e))
            return AITaskStats(total=0, running=0, completed=0, failed=0, avg_confidence=None)

    # ========== Activity Feed ==========

    async def get_activity_feed(self, limit: int = 20, offset: int = 0) -> ActivityFeedResponse:
        """Get recent activity from the audit log."""
        try:
            # Get total count
            result = await self.db.execute(select(func.count(AuditLog.id)))
            total = result.scalar() or 0

            # Get recent activities
            result = await self.db.execute(
                select(AuditLog).order_by(desc(AuditLog.created_at)).offset(offset).limit(limit)
            )
            logs = result.scalars().all()

            items = []
            for log in logs:
                message = self._format_activity_message(log)
                items.append(
                    ActivityItem(
                        id=log.id,
                        action=log.action.value if log.action else "UNKNOWN",
                        entity_type=log.entity_type,
                        entity_id=log.entity_id,
                        entity_name=log.changes.get("name") if log.changes else None,
                        user_email=log.user_email,
                        message=message,
                        timestamp=log.created_at,
                    )
                )

            return ActivityFeedResponse(
                items=items,
                total=total,
                has_more=(offset + limit) < total,
            )
        except Exception as e:
            logger.error("activity_feed_error", error=str(e))
            return ActivityFeedResponse(items=[], total=0, has_more=False)

    def _format_activity_message(self, log: AuditLog) -> str:
        """Format a human-readable activity message."""
        action_map = {
            AuditAction.CREATE: "erstellt",
            AuditAction.UPDATE: "aktualisiert",
            AuditAction.DELETE: "gelöscht",
            AuditAction.VERIFY: "verifiziert",
        }
        action_text = action_map.get(log.action, str(log.action.value) if log.action else "bearbeitet")
        entity_type = log.entity_type or "Eintrag"
        entity_name = ""
        if log.changes and "name" in log.changes:
            entity_name = f" '{log.changes['name']}'"

        user = log.user_email or "System"
        return f"{user} hat {entity_type}{entity_name} {action_text}"

    # ========== Insights ==========

    async def get_insights(self, user: User, period_days: int = 7) -> InsightsResponse:
        """Get personalized insights for a user."""
        items = []
        last_login = user.last_login
        since = last_login or (datetime.now(UTC) - timedelta(days=period_days))

        try:
            # New entities since last login
            result = await self.db.execute(select(func.count(Entity.id)).where(Entity.created_at >= since))
            new_entities = result.scalar() or 0

            if new_entities > 0:
                items.append(
                    InsightItem(
                        type="new_entities",
                        title="Neue Entities",
                        count=new_entities,
                        message=f"{new_entities} neue Entities seit Ihrem letzten Besuch",
                        link="/entities",
                    )
                )

            # New facet values
            result = await self.db.execute(select(func.count(FacetValue.id)).where(FacetValue.created_at >= since))
            new_facets = result.scalar() or 0

            if new_facets > 0:
                items.append(
                    InsightItem(
                        type="new_facets",
                        title="Neue Facetten",
                        count=new_facets,
                        message=f"{new_facets} neue Facetten-Werte hinzugefügt",
                        link="/results",
                    )
                )

            # Completed crawl jobs
            result = await self.db.execute(
                select(func.count(CrawlJob.id)).where(
                    and_(
                        CrawlJob.completed_at >= since,
                        CrawlJob.status == JobStatus.COMPLETED,
                    )
                )
            )
            completed_jobs = result.scalar() or 0

            if completed_jobs > 0:
                items.append(
                    InsightItem(
                        type="completed_crawls",
                        title="Abgeschlossene Crawls",
                        count=completed_jobs,
                        message=f"{completed_jobs} Crawl-Jobs abgeschlossen",
                        link="/crawler",
                    )
                )

            # Unverified facets (action needed)
            result = await self.db.execute(
                select(func.count(FacetValue.id)).where(FacetValue.human_verified.is_(False))
            )
            unverified = result.scalar() or 0

            if unverified > 10:
                items.append(
                    InsightItem(
                        type="action_needed",
                        title="Verifizierung ausstehend",
                        count=unverified,
                        message=f"{unverified} Facetten-Werte warten auf Verifizierung",
                        link="/results",
                    )
                )

        except Exception as e:
            logger.error("insights_error", error=str(e))

        return InsightsResponse(
            items=items,
            last_login=last_login,
            period_days=period_days,
        )

    # ========== Chart Data ==========

    async def get_chart_data(self, chart_type: str) -> ChartDataResponse:
        """Get data for a specific chart type."""
        if chart_type == "entity-distribution":
            return await self._get_entity_distribution_chart()
        elif chart_type == "facet-distribution":
            return await self._get_facet_distribution_chart()
        elif chart_type == "crawler-trend":
            return await self._get_crawler_trend_chart()
        else:
            return ChartDataResponse(
                chart_type=chart_type,
                title="Unknown Chart",
                data=[],
            )

    async def _get_entity_distribution_chart(self) -> ChartDataResponse:
        """Get entity distribution by type (only active entity types)."""
        try:
            result = await self.db.execute(
                select(EntityType.name, func.count(Entity.id))
                .join(Entity, Entity.entity_type_id == EntityType.id)
                .where(EntityType.is_active.is_(True))
                .group_by(EntityType.id, EntityType.name)
                .order_by(desc(func.count(Entity.id)))
                .limit(10)
            )
            rows = result.all()

            colors = [
                "#1976D2",
                "#388E3C",
                "#FBC02D",
                "#D32F2F",
                "#7B1FA2",
                "#0097A7",
                "#F57C00",
                "#455A64",
                "#C2185B",
                "#512DA8",
            ]

            data = [
                ChartDataPoint(
                    label=row[0],
                    value=float(row[1]),
                    color=colors[i % len(colors)],
                )
                for i, row in enumerate(rows)
            ]

            total = sum(d.value for d in data)

            return ChartDataResponse(
                chart_type="pie",
                title="Entity-Verteilung nach Typ",
                data=data,
                total=total,
            )
        except Exception as e:
            logger.error("entity_distribution_chart_error", error=str(e))
            return ChartDataResponse(
                chart_type="pie",
                title="Entity-Verteilung nach Typ",
                data=[],
            )

    async def _get_facet_distribution_chart(self) -> ChartDataResponse:
        """Get facet distribution by type."""
        try:
            result = await self.db.execute(
                select(FacetType.name, func.count(FacetValue.id))
                .join(FacetValue, FacetValue.facet_type_id == FacetType.id)
                .group_by(FacetType.id, FacetType.name)
                .order_by(desc(func.count(FacetValue.id)))
                .limit(10)
            )
            rows = result.all()

            data = [ChartDataPoint(label=row[0], value=float(row[1])) for row in rows]

            return ChartDataResponse(
                chart_type="bar",
                title="Facetten nach Typ",
                data=data,
            )
        except Exception as e:
            logger.error("facet_distribution_chart_error", error=str(e))
            return ChartDataResponse(
                chart_type="bar",
                title="Facetten nach Typ",
                data=[],
            )

    async def _get_crawler_trend_chart(self) -> ChartDataResponse:
        """Get crawler job trend over the last 30 days."""
        try:
            thirty_days_ago = datetime.now(UTC) - timedelta(days=30)

            result = await self.db.execute(
                select(
                    func.date_trunc("day", CrawlJob.started_at).label("day"),
                    func.count(CrawlJob.id),
                )
                .where(CrawlJob.started_at >= thirty_days_ago)
                .group_by("day")
                .order_by("day")
            )
            rows = result.all()

            data = [
                ChartDataPoint(
                    label=row[0].strftime("%d.%m") if row[0] else "",
                    value=float(row[1]),
                )
                for row in rows
            ]

            return ChartDataResponse(
                chart_type="line",
                title="Crawl-Jobs (letzte 30 Tage)",
                data=data,
            )
        except Exception as e:
            logger.error("crawler_trend_chart_error", error=str(e))
            return ChartDataResponse(
                chart_type="line",
                title="Crawl-Jobs (letzte 30 Tage)",
                data=[],
            )
