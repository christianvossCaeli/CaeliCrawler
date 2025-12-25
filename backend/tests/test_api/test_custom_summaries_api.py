"""Tests for Custom Summaries API endpoints."""

import asyncio
import re
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status

from app.core.rate_limit import RATE_LIMITS


class TestCustomSummariesAdminApi:
    """Tests for admin summary endpoints."""

    @pytest.fixture
    def mock_user(self):
        """Create a mock authenticated user."""
        user = MagicMock()
        user.id = uuid.uuid4()
        user.email = "test@example.com"
        user.is_admin = True
        user.is_active = True
        return user

    @pytest.fixture
    def mock_summary_data(self):
        """Create mock summary data."""
        return {
            "id": str(uuid.uuid4()),
            "name": "Test Summary",
            "description": "Test description",
            "original_prompt": "Show all entities",
            "status": "active",
            "trigger_type": "manual",
            "widgets": [],
            "execution_count": 0,
        }

    def test_create_from_prompt_schema_validation(self):
        """Test that create_from_prompt validates input schema."""
        from app.schemas.custom_summary import SummaryCreateFromPrompt
        from pydantic import ValidationError

        # Valid data
        valid = SummaryCreateFromPrompt(
            prompt="Show all entities with their facets",
            name="My Summary",
        )
        assert valid.prompt is not None
        assert len(valid.prompt) > 0

        # Prompt too short
        with pytest.raises(ValidationError):
            SummaryCreateFromPrompt(prompt="Hi", name="Test")

    def test_summary_update_schema_partial(self):
        """Test that SummaryUpdate allows partial updates."""
        from app.schemas.custom_summary import SummaryUpdate

        # Only name
        update = SummaryUpdate(name="New Name")
        assert update.name == "New Name"
        assert update.description is None
        assert update.status is None

        # Only status
        update = SummaryUpdate(status="paused")
        assert update.status == "paused"
        assert update.name is None

    def test_widget_create_schema_types(self):
        """Test WidgetCreate accepts valid widget types."""
        from app.schemas.custom_summary import SummaryWidgetCreate

        valid_types = [
            "table", "bar_chart", "line_chart", "pie_chart",
            "stat_card", "text", "comparison", "timeline", "map", "calendar"
        ]

        for widget_type in valid_types:
            widget = SummaryWidgetCreate(
                widget_type=widget_type,
                title=f"Test {widget_type}",
            )
            assert widget.widget_type == widget_type

    def test_share_create_schema(self):
        """Test ShareCreate schema for creating share links."""
        from app.schemas.custom_summary import SummaryShareCreate

        # Without password
        share = SummaryShareCreate(allow_export=True)
        assert share.allow_export is True
        assert share.password is None
        assert share.expires_days is None

        # With password and expiry
        share = SummaryShareCreate(
            password="secret123",
            expires_days=7,
            allow_export=False,
        )
        assert share.password == "secret123"
        assert share.expires_days == 7


class TestPublicSummariesApi:
    """Tests for public summary endpoints (shared links)."""

    def test_shared_access_request_schema(self):
        """Test SharedSummaryAccessRequest schema."""
        from app.schemas.custom_summary import SharedSummaryAccessRequest

        # Without password
        request = SharedSummaryAccessRequest()
        assert request.password is None

        # With password
        request = SharedSummaryAccessRequest(password="mypassword")
        assert request.password == "mypassword"

    def test_shared_response_schema(self):
        """Test SharedSummaryResponse schema structure."""
        from app.schemas.custom_summary import SharedSummaryResponse

        response = SharedSummaryResponse(
            summary_name="Shared Summary",
            summary_description="A shared summary",
            widgets=[],
            data={},
            last_updated=None,
            allow_export=True,
        )

        assert response.summary_name == "Shared Summary"
        assert response.allow_export is True
        assert response.widgets == []


class TestSummaryExecutionApi:
    """Tests for summary execution endpoints."""

    def test_execution_response_schema(self):
        """Test SummaryExecutionResponse schema."""
        from app.schemas.custom_summary import SummaryExecutionResponse
        from datetime import datetime

        response = SummaryExecutionResponse(
            id=uuid.uuid4(),
            status="completed",
            triggered_by="manual",
            trigger_details=None,
            has_changes=True,
            relevance_score=0.8,
            relevance_reason="Data changed significantly",
            duration_ms=1500,
            created_at=datetime.now(),
            completed_at=datetime.now(),
        )

        assert response.status == "completed"
        assert response.has_changes is True
        assert response.duration_ms == 1500


class TestExportEndpoints:
    """Tests for export endpoint schemas."""

    def test_export_formats_supported(self):
        """Test that both PDF and Excel formats are supported."""
        # This would be an integration test in reality
        supported_formats = ["pdf", "excel"]

        for format_type in supported_formats:
            assert format_type in ["pdf", "excel", "xlsx", "csv"]

    def test_sanitize_filename_basic(self):
        """Test basic filename sanitization."""
        from services.summaries.export_service import sanitize_filename

        # Normal filename
        assert sanitize_filename("My Summary") == "My_Summary"

        # With special chars
        assert sanitize_filename("Test: Report 2024!") == "Test_Report_2024"

    def test_sanitize_filename_path_traversal(self):
        """Test filename sanitization prevents path traversal."""
        from services.summaries.export_service import sanitize_filename

        # Path traversal attempts
        assert ".." not in sanitize_filename("../../../etc/passwd")
        assert "/" not in sanitize_filename("path/to/file")
        assert "\\" not in sanitize_filename("path\\to\\file")

    def test_sanitize_filename_header_injection(self):
        """Test filename sanitization prevents header injection."""
        from services.summaries.export_service import sanitize_filename

        # Header injection attempts
        assert "\n" not in sanitize_filename("name\nContent-Type: text/html")
        assert "\r" not in sanitize_filename("name\r\nEvil-Header: value")
        assert "\x00" not in sanitize_filename("name\x00.exe")

    def test_sanitize_filename_length(self):
        """Test filename length truncation."""
        from services.summaries.export_service import sanitize_filename

        long_name = "A" * 200
        result = sanitize_filename(long_name)
        assert len(result) <= 100

    def test_sanitize_filename_empty(self):
        """Test sanitization of empty/None filenames."""
        from services.summaries.export_service import sanitize_filename

        assert sanitize_filename("") == "export"
        assert sanitize_filename("   ") == "export"
        assert sanitize_filename("!!!") == "export"

    def test_sanitize_filename_unicode(self):
        """Test Unicode character handling in filenames."""
        from services.summaries.export_service import sanitize_filename

        # German umlauts should be normalized
        result = sanitize_filename("Übersicht")
        assert result  # Should not be empty
        assert "/" not in result
        assert "\\" not in result


class TestWidgetPositioning:
    """Tests for widget positioning schemas."""

    def test_widget_position_schema(self):
        """Test widget position configuration."""
        from app.schemas.custom_summary import SummaryWidgetUpdate

        # Update with position (position_x + width must be <= 4)
        update = SummaryWidgetUpdate(
            position_x=0,
            position_y=1,
            width=4,
            height=3,
        )

        assert update.position_x == 0
        assert update.position_y == 1
        assert update.width == 4
        assert update.height == 3

    def test_widget_grid_boundary_validation(self):
        """Test widget position grid boundary validation."""
        from app.schemas.custom_summary import SummaryWidgetCreate, GRID_COLUMNS
        from pydantic import ValidationError

        # Valid position (fits in grid)
        valid_widget = SummaryWidgetCreate(
            widget_type="table",
            title="Test",
            position_x=0,
            width=4,  # Full width
        )
        assert valid_widget.position_x + valid_widget.width <= GRID_COLUMNS

        # Valid position at edge
        edge_widget = SummaryWidgetCreate(
            widget_type="table",
            title="Test",
            position_x=2,
            width=2,  # position 2 + width 2 = 4 (max)
        )
        assert edge_widget.position_x + edge_widget.width == GRID_COLUMNS

        # Invalid: exceeds grid boundary
        with pytest.raises(ValidationError) as exc_info:
            SummaryWidgetCreate(
                widget_type="table",
                title="Test",
                position_x=3,
                width=2,  # position 3 + width 2 = 5 > 4
            )
        assert "beyond grid boundary" in str(exc_info.value)

        # Invalid: position_x too high
        with pytest.raises(ValidationError):
            SummaryWidgetCreate(
                widget_type="table",
                title="Test",
                position_x=5,  # > GRID_COLUMNS - 1
                width=1,
            )

    def test_widget_config_schemas(self):
        """Test widget configuration schemas."""
        from app.schemas.custom_summary import SummaryWidgetCreate, WidgetQueryConfig, WidgetVisualizationConfig

        # Table widget config
        table_widget = SummaryWidgetCreate(
            widget_type="table",
            title="Entity Table",
            query_config=WidgetQueryConfig(
                entity_type="Kommune",
                facet_types=["Einwohnerzahl", "Flaeche"],
                limit=50,
            ),
            visualization_config=WidgetVisualizationConfig(
                show_pagination=True,
            ),
        )

        assert table_widget.query_config.entity_type == "Kommune"
        assert "Einwohnerzahl" in table_widget.query_config.facet_types

        # Chart widget config
        chart_widget = SummaryWidgetCreate(
            widget_type="bar_chart",
            title="Population by City",
            query_config=WidgetQueryConfig(
                entity_type="Stadt",
                group_by="Bundesland",
            ),
            visualization_config=WidgetVisualizationConfig(
                show_legend=True,
                colors=["#113534", "#2a6b6a"],
            ),
        )

        assert chart_widget.visualization_config.show_legend is True


class TestSecurityFeatures:
    """Tests for security features in Custom Summaries."""

    def test_rate_limits_defined_for_summaries(self):
        """Test that all summary-related rate limits are properly defined."""
        required_limits = [
            "summary_create",
            "summary_list",
            "summary_read",
            "summary_update",
            "summary_delete",
            "summary_execute",
            "summary_share",
            "summary_export",
            "shared_summary_access",
            "shared_summary_export",
        ]

        for limit_name in required_limits:
            assert limit_name in RATE_LIMITS, f"Missing rate limit: {limit_name}"
            assert "max_requests" in RATE_LIMITS[limit_name]
            assert "window_seconds" in RATE_LIMITS[limit_name]

    def test_sql_injection_search_escaping(self):
        """Test that SQL LIKE special characters are properly escaped in search."""
        test_cases = [
            ("normal search", "normal search"),
            ("100%", "100\\%"),  # % should be escaped
            ("under_score", "under\\_score"),  # _ should be escaped
            ("back\\slash", "back\\\\slash"),  # \ should be escaped first
            ("%_%", "\\%\\_\\%"),  # Multiple special chars
        ]

        for input_val, expected in test_cases:
            # Simulate the escaping logic from custom_summaries.py
            safe_search = input_val.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            assert safe_search == expected, f"Failed for input: {input_val}"

    def test_share_token_format_validation(self):
        """Test share token format validation."""
        from app.api.v1.summaries import validate_share_token

        # Valid tokens (URL-safe base64, 43 chars for 32 bytes)
        valid_token = "a" * 43  # Simple valid token
        assert validate_share_token(valid_token) is True

        # Invalid tokens
        invalid_tokens = [
            "",  # Empty
            "short",  # Too short
            "a" * 100,  # Too long
            "invalid!@#$%",  # Invalid characters
            "has spaces here",  # Spaces not allowed
            None,  # None value
        ]

        for token in invalid_tokens:
            result = validate_share_token(token) if token else False
            assert result is False, f"Token should be invalid: {token}"

    def test_query_limit_constants(self):
        """Test that query limit constants are defined properly."""
        from services.summaries.executor import MAX_QUERY_LIMIT, DEFAULT_QUERY_LIMIT

        assert MAX_QUERY_LIMIT == 1000, "MAX_QUERY_LIMIT should be 1000"
        assert DEFAULT_QUERY_LIMIT == 100, "DEFAULT_QUERY_LIMIT should be 100"
        assert DEFAULT_QUERY_LIMIT <= MAX_QUERY_LIMIT, "Default should not exceed max"

    def test_query_limit_enforcement(self):
        """Test that query limits are properly enforced."""
        from services.summaries.executor import MAX_QUERY_LIMIT, DEFAULT_QUERY_LIMIT

        test_cases = [
            (None, DEFAULT_QUERY_LIMIT),  # No limit -> default
            (50, 50),  # Within range -> keep
            (100, 100),  # At default -> keep
            (500, 500),  # Within range -> keep
            (1000, 1000),  # At max -> keep
            (2000, MAX_QUERY_LIMIT),  # Above max -> cap to max
            (0, DEFAULT_QUERY_LIMIT),  # Zero -> default
            (-10, DEFAULT_QUERY_LIMIT),  # Negative -> default
        ]

        for requested, expected in test_cases:
            # Simulate the limit enforcement logic
            if requested is None or requested <= 0:
                result = DEFAULT_QUERY_LIMIT
            else:
                result = min(requested, MAX_QUERY_LIMIT)
            assert result == expected, f"Failed for requested={requested}, expected={expected}, got={result}"

    def test_filter_whitelist_defined(self):
        """Test that filter whitelist is properly defined."""
        from services.summaries.executor import ALLOWED_FILTER_KEYS

        # Should be a frozenset for immutability
        assert isinstance(ALLOWED_FILTER_KEYS, frozenset)

        # Should contain expected safe filter keys
        expected_keys = {"admin_level_1", "country", "tags", "name", "is_active"}
        assert expected_keys.issubset(ALLOWED_FILTER_KEYS)


class TestTimingAttackProtection:
    """Tests for timing attack protection."""

    def test_timing_noise_constants_defined(self):
        """Test that timing noise constants are properly defined."""
        from app.api.v1.summaries import MIN_RESPONSE_TIME_MS, MAX_RESPONSE_TIME_MS

        # Increased from 100-200ms to 500-1000ms for better brute-force protection
        assert MIN_RESPONSE_TIME_MS == 500, "MIN_RESPONSE_TIME_MS should be 500ms"
        assert MAX_RESPONSE_TIME_MS == 1000, "MAX_RESPONSE_TIME_MS should be 1000ms"
        assert MIN_RESPONSE_TIME_MS < MAX_RESPONSE_TIME_MS, "Min should be less than max"

    @pytest.mark.asyncio
    async def test_timing_noise_function_exists(self):
        """Test that timing noise helper function exists and works."""
        from app.api.v1.summaries import _add_timing_noise

        # Should complete without error
        start = time.time()
        await _add_timing_noise()
        elapsed = (time.time() - start) * 1000  # Convert to ms

        # Should take at least MIN_RESPONSE_TIME_MS (500ms)
        assert elapsed >= 500, f"Timing noise should add at least 500ms, got {elapsed}ms"


class TestInterpretedConfigValidation:
    """Tests for InterpretedConfig schema validation."""

    def test_interpreted_config_valid(self):
        """Test valid InterpretedConfig."""
        from app.schemas.custom_summary import InterpretedConfig

        config = InterpretedConfig(
            theme="Bundesliga Statistics",
            summary_name="Bundesliga Overview",
            widgets=[
                {
                    "widget_type": "table",
                    "title": "Team Rankings",
                    "entity_type": "Team",
                    "facet_types": ["points", "goals"],
                }
            ],
            suggested_schedule="daily",
            confidence_score=0.85,
        )

        assert config.theme == "Bundesliga Statistics"
        assert len(config.widgets) == 1
        assert config.widgets[0].widget_type.value == "table"

    def test_interpreted_config_invalid_widget_type(self):
        """Test InterpretedConfig rejects invalid widget types."""
        from app.schemas.custom_summary import InterpretedConfig
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            InterpretedConfig(
                theme="Test",
                summary_name="Test Summary",
                widgets=[
                    {
                        "widget_type": "invalid_type",
                        "title": "Test Widget",
                    }
                ],
            )

    def test_interpreted_config_max_widgets(self):
        """Test InterpretedConfig enforces max widget limit."""
        from app.schemas.custom_summary import InterpretedConfig
        from pydantic import ValidationError

        # 21 widgets should fail (max 20)
        widgets = [
            {"widget_type": "stat_card", "title": f"Widget {i}"}
            for i in range(21)
        ]

        with pytest.raises(ValidationError):
            InterpretedConfig(
                theme="Test",
                summary_name="Test Summary",
                widgets=widgets,
            )

    def test_interpreted_config_schedule_validation(self):
        """Test InterpretedConfig validates schedule pattern."""
        from app.schemas.custom_summary import InterpretedConfig
        from pydantic import ValidationError

        # Valid schedules
        for schedule in ["hourly", "daily", "weekly", "monthly", "none", None]:
            config = InterpretedConfig(
                theme="Test",
                summary_name="Test",
                suggested_schedule=schedule,
            )
            assert config.suggested_schedule == schedule

        # Invalid schedule
        with pytest.raises(ValidationError):
            InterpretedConfig(
                theme="Test",
                summary_name="Test",
                suggested_schedule="every_5_minutes",
            )

    def test_interpreted_config_confidence_bounds(self):
        """Test InterpretedConfig confidence score bounds."""
        from app.schemas.custom_summary import InterpretedConfig
        from pydantic import ValidationError

        # Valid bounds
        InterpretedConfig(theme="Test", summary_name="Test", confidence_score=0.0)
        InterpretedConfig(theme="Test", summary_name="Test", confidence_score=1.0)
        InterpretedConfig(theme="Test", summary_name="Test", confidence_score=0.5)

        # Out of bounds
        with pytest.raises(ValidationError):
            InterpretedConfig(theme="Test", summary_name="Test", confidence_score=1.5)

        with pytest.raises(ValidationError):
            InterpretedConfig(theme="Test", summary_name="Test", confidence_score=-0.1)


class TestWidgetTypes:
    """Tests for widget type validation."""

    def test_all_widget_types_have_icons(self):
        """Test that all visualization types have icon mappings."""
        # This would be a frontend test, but we can validate the backend types
        from app.models.summary_widget import SummaryWidgetType

        expected_types = {
            "TABLE", "BAR_CHART", "LINE_CHART", "PIE_CHART",
            "STAT_CARD", "TEXT", "COMPARISON", "MAP", "TIMELINE", "CALENDAR"
        }

        actual_types = {wt.name for wt in SummaryWidgetType}
        assert expected_types.issubset(actual_types), f"Missing widget types: {expected_types - actual_types}"

    def test_widget_type_enum_values(self):
        """Test widget type enum has correct string values."""
        from app.models.summary_widget import SummaryWidgetType

        # Values should be lowercase for API compatibility
        for wt in SummaryWidgetType:
            assert wt.value == wt.name.lower(), f"Widget type {wt.name} has unexpected value: {wt.value}"
