"""Tests for Custom Summaries functionality."""

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestSummaryExecutor:
    """Tests for the SummaryExecutor service."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async database session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        return session

    @pytest.fixture
    def mock_summary(self):
        """Create a mock CustomSummary object."""
        summary = MagicMock()
        summary.id = uuid.uuid4()
        summary.user_id = uuid.uuid4()
        summary.name = "Test Summary"
        summary.original_prompt = "Show all entities"
        summary.status = MagicMock(value="active")
        summary.check_relevance = True
        summary.relevance_threshold = 0.3
        summary.widgets = []
        summary.execution_count = 0
        summary.last_data_hash = None
        return summary

    @pytest.mark.asyncio
    async def test_calculate_data_hash(self):
        """Test that data hash is calculated correctly."""
        from services.summaries.executor import SummaryExecutor

        mock_session = AsyncMock()
        executor = SummaryExecutor(mock_session)

        data = {"key": "value", "nested": {"a": 1, "b": 2}}
        hash1 = executor._calculate_data_hash(data)

        # Same data should produce same hash
        hash2 = executor._calculate_data_hash({"key": "value", "nested": {"a": 1, "b": 2}})
        assert hash1 == hash2

        # Different data should produce different hash
        hash3 = executor._calculate_data_hash({"key": "different"})
        assert hash1 != hash3

        # Order shouldn't matter in dicts
        data_reordered = {"nested": {"b": 2, "a": 1}, "key": "value"}
        hash4 = executor._calculate_data_hash(data_reordered)
        assert hash1 == hash4


class TestRelevanceChecker:
    """Tests for the RelevanceChecker service."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async database session."""
        return AsyncMock()

    def test_no_change_detection(self):
        """Test that identical data returns no change."""
        from services.summaries.relevance_checker import quick_change_detection, calculate_data_hash

        old_data = {"widgets": [{"data": [1, 2, 3]}]}
        new_data = {"widgets": [{"data": [1, 2, 3]}]}

        # quick_change_detection returns (has_changed: bool, reason: str)
        has_changed, reason = quick_change_detection(old_data, new_data)

        assert has_changed is False
        assert "unverändert" in reason or "identischer Hash" in reason

    def test_significant_change_detection(self):
        """Test that significant changes are detected."""
        from services.summaries.relevance_checker import quick_change_detection

        old_data = {"widgets": [{"data": [1, 2, 3]}]}
        new_data = {"widgets": [{"data": [100, 200, 300]}]}  # Completely different

        # quick_change_detection returns (has_changed: bool, reason: str)
        has_changed, reason = quick_change_detection(old_data, new_data)

        # Should detect change
        assert has_changed is True
        assert "erkannt" in reason or "Änderung" in reason


class TestAiInterpreter:
    """Tests for the AI Interpreter service."""

    def test_ai_interpreter_module_exists(self):
        """Test that AI interpreter module and functions exist."""
        from services.summaries.ai_interpreter import interpret_summary_prompt
        from app.schemas.custom_summary import InterpretedConfig

        # Verify the function exists
        assert interpret_summary_prompt is not None
        assert callable(interpret_summary_prompt)

        # Verify InterpretedConfig schema exists with expected fields
        assert hasattr(InterpretedConfig, 'model_fields')
        assert 'summary_name' in InterpretedConfig.model_fields
        assert 'theme' in InterpretedConfig.model_fields
        assert 'widgets' in InterpretedConfig.model_fields

    def test_interpreted_config_validation(self):
        """Test InterpretedConfig validation."""
        from app.schemas.custom_summary import InterpretedConfig, InterpretedWidgetConfig

        # Test valid widget config first
        widget = InterpretedWidgetConfig(
            widget_type="table",
            title="Test Table",
            entity_type="Kommune",
            facet_types=["Einwohnerzahl"],
        )

        # Test valid InterpretedConfig
        valid_config = InterpretedConfig(
            theme="Kommunen Übersicht",
            summary_name="Test Dashboard",
            description="Test description",
            widgets=[widget],
            confidence_score=0.9,
        )
        assert valid_config.summary_name == "Test Dashboard"
        assert len(valid_config.widgets) == 1

    def test_interpreted_config_invalid_widget_type(self):
        """Test that invalid widget types are rejected."""
        from app.schemas.custom_summary import InterpretedConfig, InterpretedWidgetConfig

        # Test with invalid widget type - should raise validation error
        with pytest.raises(Exception):  # Pydantic validation error
            InterpretedWidgetConfig(
                widget_type="invalid_type",
                title="Test",
            )


class TestSummaryNotificationIntegration:
    """Tests for summary notification integration."""

    def test_notification_event_types_exist(self):
        """Test that notification event types for summaries exist."""
        from app.models.notification import NotificationEventType

        assert hasattr(NotificationEventType, "SUMMARY_UPDATED")
        assert hasattr(NotificationEventType, "SUMMARY_RELEVANT_CHANGES")

    def test_event_dispatcher_has_summary_templates(self):
        """Test that event dispatcher has templates for summary events."""
        from services.notifications.event_dispatcher import NotificationEventDispatcher
        from app.models.notification import NotificationEventType

        dispatcher = NotificationEventDispatcher()

        # Test SUMMARY_UPDATED template
        title, body = dispatcher._generate_content(
            NotificationEventType.SUMMARY_UPDATED,
            {"summary_name": "Test Summary"},
        )
        assert "Test Summary" in body
        assert "aktualisiert" in title.lower() or "updated" in title.lower()

        # Test SUMMARY_RELEVANT_CHANGES template
        title, body = dispatcher._generate_content(
            NotificationEventType.SUMMARY_RELEVANT_CHANGES,
            {"summary_name": "Test Summary", "relevance_reason": "Neue Daten verfügbar"},
        )
        assert "Test Summary" in body
        assert "Neue Daten verfügbar" in body

    def test_event_dispatcher_matches_summary_conditions(self):
        """Test that event dispatcher correctly matches summary_ids condition."""
        from services.notifications.event_dispatcher import NotificationEventDispatcher

        dispatcher = NotificationEventDispatcher()

        summary_id = str(uuid.uuid4())
        other_id = str(uuid.uuid4())

        # Create a mock rule with summary_ids condition
        mock_rule = MagicMock()
        mock_rule.conditions = {"summary_ids": [summary_id]}

        # Should match when summary_id is in the list
        payload_match = {"summary_id": summary_id, "summary_name": "Test"}
        assert dispatcher._matches_conditions(mock_rule, payload_match) is True

        # Should not match when summary_id is not in the list
        payload_no_match = {"summary_id": other_id, "summary_name": "Other"}
        assert dispatcher._matches_conditions(mock_rule, payload_no_match) is False


class TestSummaryModels:
    """Tests for summary-related database models."""

    def test_summary_status_enum(self):
        """Test that SummaryStatus enum has all required values."""
        from app.models.custom_summary import SummaryStatus

        assert hasattr(SummaryStatus, "DRAFT")
        assert hasattr(SummaryStatus, "ACTIVE")
        assert hasattr(SummaryStatus, "PAUSED")
        assert hasattr(SummaryStatus, "ARCHIVED")

    def test_summary_trigger_type_enum(self):
        """Test that SummaryTriggerType enum has all required values."""
        from app.models.custom_summary import SummaryTriggerType

        assert hasattr(SummaryTriggerType, "MANUAL")
        assert hasattr(SummaryTriggerType, "CRON")
        assert hasattr(SummaryTriggerType, "CRAWL_CATEGORY")
        assert hasattr(SummaryTriggerType, "CRAWL_PRESET")

    def test_widget_type_enum(self):
        """Test that SummaryWidgetType enum has all required values."""
        from app.models.summary_widget import SummaryWidgetType

        expected_types = [
            "TABLE", "BAR_CHART", "LINE_CHART", "PIE_CHART",
            "STAT_CARD", "TEXT", "COMPARISON", "TIMELINE", "MAP", "CALENDAR"
        ]
        for type_name in expected_types:
            assert hasattr(SummaryWidgetType, type_name)

    def test_execution_status_enum(self):
        """Test that ExecutionStatus enum has all required values."""
        from app.models.summary_execution import ExecutionStatus

        assert hasattr(ExecutionStatus, "PENDING")
        assert hasattr(ExecutionStatus, "RUNNING")
        assert hasattr(ExecutionStatus, "COMPLETED")
        assert hasattr(ExecutionStatus, "FAILED")
        assert hasattr(ExecutionStatus, "SKIPPED")


class TestSummaryTasks:
    """Tests for Celery summary tasks."""

    def test_calculate_next_run_cron(self):
        """Test cron expression parsing for next run calculation."""
        from workers.summary_tasks import calculate_next_run

        # Daily at midnight
        next_run = calculate_next_run("0 0 * * *")
        assert next_run is not None
        assert isinstance(next_run, datetime)
        assert next_run > datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_check_scheduled_summaries_no_due(self):
        """Test that check_scheduled_summaries handles no due summaries."""
        # Patch at the correct location where it's imported
        with patch("app.database.get_celery_session_context") as mock_context:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            mock_session.execute = AsyncMock(return_value=mock_result)

            mock_context.return_value.__aenter__.return_value = mock_session

            from workers.summary_tasks import check_scheduled_summaries
            # The task exists and is properly defined
            assert check_scheduled_summaries is not None
            assert hasattr(check_scheduled_summaries, 'delay')


class TestSummaryApiSchemas:
    """Tests for summary API Pydantic schemas."""

    def test_summary_create_schema(self):
        """Test SummaryCreateFromPrompt schema validation."""
        from app.schemas.custom_summary import SummaryCreateFromPrompt

        # Valid data - using SummaryCreateFromPrompt for prompt-based creation
        valid_data = {
            "prompt": "Show all entities with their properties",
            "name": "My Summary",
        }
        schema = SummaryCreateFromPrompt(**valid_data)
        assert schema.prompt == valid_data["prompt"]
        assert schema.name == valid_data["name"]

    def test_summary_create_full_schema(self):
        """Test SummaryCreate schema with all required fields."""
        from app.schemas.custom_summary import SummaryCreate

        # Valid data - using SummaryCreate for manual creation
        valid_data = {
            "name": "My Summary",
            "original_prompt": "Show all entities with their properties",
        }
        schema = SummaryCreate(**valid_data)
        assert schema.name == valid_data["name"]
        assert schema.original_prompt == valid_data["original_prompt"]

    def test_summary_update_schema(self):
        """Test SummaryUpdate schema allows partial updates."""
        from app.schemas.custom_summary import SummaryUpdate

        # Partial update with just name
        partial_data = {"name": "New Name"}
        schema = SummaryUpdate(**partial_data)
        assert schema.name == "New Name"
        assert schema.description is None

    def test_widget_create_schema(self):
        """Test SummaryWidgetCreate schema validation."""
        from app.schemas.custom_summary import SummaryWidgetCreate

        valid_data = {
            "widget_type": "table",
            "title": "Test Widget",
            "query_config": {"entity_type": "Kommune"},
        }
        schema = SummaryWidgetCreate(**valid_data)
        assert schema.widget_type == "table"
        assert schema.title == "Test Widget"


class TestExportService:
    """Tests for the export service."""

    def test_sanitize_sheet_name(self):
        """Test sheet name sanitization for Excel exports."""
        from services.summaries.export_service import SummaryExportService

        service = SummaryExportService(AsyncMock())

        # Test with special characters
        name = "Test / Sheet: [with] special *chars*"
        sanitized = service._sanitize_sheet_name(name)

        # Should not contain invalid characters
        assert "/" not in sanitized
        assert ":" not in sanitized
        assert "[" not in sanitized
        assert "]" not in sanitized
        assert "*" not in sanitized

    def test_sanitize_sheet_name_max_length(self):
        """Test sheet name truncation to 31 characters."""
        from services.summaries.export_service import SummaryExportService

        service = SummaryExportService(AsyncMock())

        # Test with long name
        long_name = "This is a very long sheet name that exceeds 31 characters"
        sanitized = service._sanitize_sheet_name(long_name)

        assert len(sanitized) <= 31
        assert sanitized.endswith("...")

    def test_sanitize_sheet_name_empty(self):
        """Test sheet name sanitization with empty input."""
        from services.summaries.export_service import SummaryExportService

        service = SummaryExportService(AsyncMock())

        # Test with only invalid characters
        sanitized = service._sanitize_sheet_name("/*?:[]")
        assert sanitized == "Sheet"


class TestExecutorFilterWhitelist:
    """Tests for the executor's filter whitelist functionality."""

    def test_allowed_filter_keys_exist(self):
        """Test that ALLOWED_FILTER_KEYS is defined."""
        from services.summaries.executor import ALLOWED_FILTER_KEYS

        assert "admin_level_1" in ALLOWED_FILTER_KEYS
        assert "country" in ALLOWED_FILTER_KEYS
        assert "tags" in ALLOWED_FILTER_KEYS
        assert "name" in ALLOWED_FILTER_KEYS
        assert "is_active" in ALLOWED_FILTER_KEYS

    def test_unknown_filter_key_not_in_whitelist(self):
        """Test that unknown keys are not in the whitelist."""
        from services.summaries.executor import ALLOWED_FILTER_KEYS

        # These should NOT be in the whitelist
        assert "sql_injection" not in ALLOWED_FILTER_KEYS
        assert "__class__" not in ALLOWED_FILTER_KEYS
        assert "drop_table" not in ALLOWED_FILTER_KEYS


class TestExecutorErrorHandling:
    """Tests for executor error handling."""

    @pytest.mark.asyncio
    async def test_executor_handles_missing_summary(self):
        """Test that executor raises ValueError for missing summary."""
        from services.summaries.executor import SummaryExecutor

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        executor = SummaryExecutor(mock_session)

        with pytest.raises(ValueError) as exc_info:
            await executor.execute_summary(uuid.uuid4())

        assert "not found" in str(exc_info.value)


class TestCrawlIntegration:
    """Tests for crawl integration with summaries."""

    def test_on_crawl_completed_task_exists(self):
        """Test that on_crawl_completed task is defined."""
        from workers.summary_tasks import on_crawl_completed
        assert on_crawl_completed is not None

    def test_on_preset_completed_task_exists(self):
        """Test that on_preset_completed task is defined."""
        from workers.summary_tasks import on_preset_completed
        assert on_preset_completed is not None


class TestSummaryHelpers:
    """Tests for summary helper functions."""

    def test_should_notify_user(self):
        """Test the should_notify_user helper function."""
        from services.summaries import should_notify_user
        from services.summaries.relevance_checker import RelevanceCheckResult

        # Should notify when score exceeds threshold
        high_score_result = RelevanceCheckResult(
            should_update=True,
            score=0.8,
            reason="Significant changes detected",
        )
        assert should_notify_user(high_score_result, notification_threshold=0.5) is True

        # Should not notify when score is below threshold
        low_score_result = RelevanceCheckResult(
            should_update=True,
            score=0.3,
            reason="Minor changes",
        )
        assert should_notify_user(low_score_result, notification_threshold=0.5) is False

        # Should not notify when should_update is False
        no_update_result = RelevanceCheckResult(
            should_update=False,
            score=0.9,
            reason="No changes needed",
        )
        assert should_notify_user(no_update_result, notification_threshold=0.5) is False
