"""Event dispatcher for matching events to notification rules."""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.notification import (
    Notification,
    NotificationEventType,
    NotificationStatus,
)
from app.models.notification_rule import NotificationRule
from app.models.user import User

logger = logging.getLogger(__name__)


class NotificationEventDispatcher:
    """Dispatches events to matching notification rules.

    This service is responsible for:
    1. Finding all active rules that match an event type
    2. Evaluating rule conditions against event payload
    3. Creating notification records for matching rules
    """

    async def dispatch_event(
        self,
        session: AsyncSession,
        event_type: NotificationEventType,
        payload: dict[str, Any],
    ) -> list[str]:
        """Dispatch an event and create notifications for matching rules.

        Args:
            session: Database session
            event_type: Type of event that occurred
            payload: Event data including entity references and metadata

        Returns:
            List of created notification IDs
        """
        # Find all active rules matching this event type
        rules = await self._find_matching_rules(session, event_type)

        if not rules:
            logger.debug(f"No matching rules for event {event_type.value}")
            return []

        notification_ids: list[str] = []

        for rule in rules:
            # Check if payload matches rule conditions
            if not self._matches_conditions(rule, payload):
                continue

            # Create notification
            notification = await self._create_notification(
                session, rule, event_type, payload
            )
            notification_ids.append(str(notification.id))

            # Update rule statistics
            rule.trigger_count += 1
            rule.last_triggered = datetime.now(UTC)

        await session.commit()

        logger.info(
            f"Dispatched event {event_type.value}: "
            f"{len(notification_ids)} notifications created"
        )

        return notification_ids

    async def _find_matching_rules(
        self,
        session: AsyncSession,
        event_type: NotificationEventType,
    ) -> list[NotificationRule]:
        """Find all active rules matching the event type.

        Args:
            session: Database session
            event_type: Event type to match

        Returns:
            List of matching rules
        """
        query = (
            select(NotificationRule)
            .options(selectinload(NotificationRule.user))
            .where(
                NotificationRule.event_type == event_type,
                NotificationRule.is_active.is_(True),
            )
            .join(User)
            .where(User.notifications_enabled.is_(True), User.is_active.is_(True))
        )

        result = await session.execute(query)
        return list(result.scalars().all())

    def _matches_conditions(
        self, rule: NotificationRule, payload: dict[str, Any]
    ) -> bool:
        """Check if payload matches rule conditions.

        Args:
            rule: Notification rule with conditions
            payload: Event payload to check

        Returns:
            True if all conditions match
        """
        conditions = rule.conditions

        if not conditions:
            return True  # No conditions = always match

        # Category filter
        if "category_ids" in conditions:
            category_id = payload.get("category_id")
            if category_id and str(category_id) not in [
                str(c) for c in conditions["category_ids"]
            ]:
                return False

        # Source filter
        if "source_ids" in conditions:
            source_id = payload.get("source_id")
            if source_id and str(source_id) not in [
                str(s) for s in conditions["source_ids"]
            ]:
                return False

        # Entity filter
        if "entity_ids" in conditions:
            entity_id = payload.get("entity_id")
            if entity_id and str(entity_id) not in [
                str(e) for e in conditions["entity_ids"]
            ]:
                return False

        # Summary filter (for summary events)
        if "summary_ids" in conditions:
            summary_id = payload.get("summary_id")
            if summary_id and str(summary_id) not in [
                str(s) for s in conditions["summary_ids"]
            ]:
                return False

        # Minimum confidence filter
        if "min_confidence" in conditions:
            confidence = payload.get("confidence", 0)
            if confidence < conditions["min_confidence"]:
                return False

        # Keyword filter (any keyword must match)
        if "keywords" in conditions:
            keywords = conditions["keywords"]
            if keywords:
                text = " ".join([
                    str(payload.get("title", "")),
                    str(payload.get("text", "")),
                    str(payload.get("summary", "")),
                ]).lower()

                if not any(kw.lower() in text for kw in keywords):
                    return False

        # Location filter
        if "location_filter" in conditions:
            loc_filter = conditions["location_filter"]

            if loc_filter.get("country") and payload.get("country") != loc_filter["country"]:
                return False

            if loc_filter.get("admin_level_1"):  # noqa: SIM102
                if payload.get("admin_level_1") != loc_filter["admin_level_1"]:
                    return False

            if loc_filter.get("region") and payload.get("region") != loc_filter["region"]:
                return False

        # Event status filter (for crawl events)
        if "status_filter" in conditions:
            status = payload.get("status")
            if status and status not in conditions["status_filter"]:
                return False

        return True

    async def _create_notification(
        self,
        session: AsyncSession,
        rule: NotificationRule,
        event_type: NotificationEventType,
        payload: dict[str, Any],
    ) -> Notification:
        """Create a notification record.

        Args:
            session: Database session
            rule: Rule that triggered the notification
            event_type: Type of event
            payload: Event data

        Returns:
            Created notification
        """
        title, body = self._generate_content(event_type, payload)

        # Determine related entity type and ID based on event type
        related_entity_type = payload.get("entity_type")
        related_entity_id = self._parse_uuid(payload.get("entity_id"))

        # Special handling for summary events
        if event_type in (
            NotificationEventType.SUMMARY_UPDATED,
            NotificationEventType.SUMMARY_RELEVANT_CHANGES,
        ):
            related_entity_type = "summary"
            related_entity_id = self._parse_uuid(payload.get("summary_id"))

        notification = Notification(
            user_id=rule.user_id,
            rule_id=rule.id,
            event_type=event_type,
            channel=rule.channel,
            title=title,
            body=body,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            payload=payload,
            status=NotificationStatus.PENDING,
        )

        session.add(notification)
        return notification

    def _generate_content(
        self, event_type: NotificationEventType, payload: dict[str, Any]
    ) -> tuple[str, str]:
        """Generate notification title and body from event.

        Args:
            event_type: Type of event
            payload: Event data

        Returns:
            Tuple of (title, body)
        """
        templates = {
            NotificationEventType.NEW_DOCUMENT: (
                "Neue Dokumente gefunden",
                "Es wurden {count} neue Dokumente in der Quelle '{source_name}' gefunden.",
            ),
            NotificationEventType.DOCUMENT_CHANGED: (
                "Dokument geändert",
                "Ein Dokument in der Quelle '{source_name}' wurde geändert.",
            ),
            NotificationEventType.DOCUMENT_REMOVED: (
                "Dokument entfernt",
                "Ein Dokument wurde aus der Quelle '{source_name}' entfernt.",
            ),
            NotificationEventType.CRAWL_STARTED: (
                "Crawl gestartet",
                "Der Crawl für die Quelle '{source_name}' wurde gestartet.",
            ),
            NotificationEventType.CRAWL_COMPLETED: (
                "Crawl abgeschlossen",
                "Der Crawl für '{source_name}' wurde erfolgreich abgeschlossen. "
                "{documents_found} Dokumente gefunden, {documents_new} neu.",
            ),
            NotificationEventType.CRAWL_FAILED: (
                "Crawl fehlgeschlagen",
                "Der Crawl für '{source_name}' ist fehlgeschlagen: {error}",
            ),
            NotificationEventType.AI_ANALYSIS_COMPLETED: (
                "Analyse abgeschlossen",
                "Die AI-Analyse für das Dokument '{title}' wurde abgeschlossen.",
            ),
            NotificationEventType.HIGH_CONFIDENCE_RESULT: (
                "Relevantes Ergebnis gefunden",
                "Ein Dokument mit hoher Relevanz ({confidence:.0%}) wurde gefunden: '{title}'",
            ),
            NotificationEventType.SOURCE_STATUS_CHANGED: (
                "Quellenstatus geändert",
                "Der Status der Quelle '{source_name}' hat sich geändert: {status}",
            ),
            NotificationEventType.SOURCE_ERROR: (
                "Fehler bei Datenquelle",
                "Bei der Quelle '{source_name}' ist ein Fehler aufgetreten: {error}",
            ),
            NotificationEventType.SUMMARY_UPDATED: (
                "Zusammenfassung aktualisiert",
                "Die Zusammenfassung '{summary_name}' wurde erfolgreich aktualisiert.",
            ),
            NotificationEventType.SUMMARY_RELEVANT_CHANGES: (
                "Relevante Änderungen in Zusammenfassung",
                "In der Zusammenfassung '{summary_name}' wurden relevante Änderungen erkannt: {relevance_reason}",
            ),
        }

        title_template, body_template = templates.get(
            event_type,
            ("Benachrichtigung", "Ein Ereignis ist aufgetreten."),
        )

        # Format with payload, using defaults for missing keys
        format_data = {
            "count": payload.get("count", 0),
            "source_name": payload.get("source_name", "Unbekannte Quelle"),
            "title": payload.get("title", "Unbekannt"),
            "error": payload.get("error", "Unbekannter Fehler"),
            "documents_found": payload.get("documents_found", 0),
            "documents_new": payload.get("documents_new", 0),
            "confidence": payload.get("confidence", 0),
            "status": payload.get("status", "unbekannt"),
            "summary": payload.get("summary", "")[:200],
            # Summary events
            "summary_name": payload.get("summary_name", "Unbekannte Zusammenfassung"),
            "relevance_score": payload.get("relevance_score", 0),
            "relevance_reason": payload.get("relevance_reason", "Änderungen erkannt"),
        }

        try:
            title = title_template.format(**format_data)
            body = body_template.format(**format_data)
        except KeyError as e:
            logger.warning(f"Missing key in notification template: {e}")
            title = title_template
            body = body_template

        # Add summary if available
        if payload.get("summary"):
            body += f"\n\nZusammenfassung: {payload['summary'][:500]}"

        return title, body

    def _parse_uuid(self, value: Any) -> UUID | None:
        """Parse a value as UUID.

        Args:
            value: Value to parse

        Returns:
            UUID or None if invalid
        """
        if value is None:
            return None
        if isinstance(value, UUID):
            return value
        try:
            return UUID(str(value))
        except (ValueError, TypeError):
            return None
