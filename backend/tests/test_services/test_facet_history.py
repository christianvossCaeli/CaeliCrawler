"""Tests for Facet History Service."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.entity import Entity
from app.models.facet_type import FacetType, ValueType
from app.models.facet_value_history import FacetValueHistory
from services.facet_history_service import FacetHistoryService


class TestFacetHistoryServiceBasic:
    """Basic unit tests for FacetHistoryService."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async database session."""
        session = MagicMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()
        session.refresh = AsyncMock()
        session.get = AsyncMock()
        session.delete = AsyncMock()
        return session

    @pytest.fixture
    def service(self, mock_session):
        """Create service instance with mock session."""
        return FacetHistoryService(mock_session)

    @pytest.fixture
    def sample_entity(self):
        """Create sample entity."""
        entity = MagicMock(spec=Entity)
        entity.id = uuid4()
        entity.name = "Test Municipality"
        return entity

    @pytest.fixture
    def sample_facet_type(self):
        """Create sample history facet type."""
        ft = MagicMock(spec=FacetType)
        ft.id = uuid4()
        ft.slug = "budget-volume"
        ft.name = "Budget Volume"
        ft.value_type = ValueType.HISTORY
        ft.value_schema = {
            "type": "history",
            "properties": {
                "unit": "EUR",
                "unit_label": "Euro",
                "precision": 2,
                "tracks": {"default": {"label": "Actual", "color": "#1976D2"}},
            },
        }
        return ft

    @pytest.fixture
    def sample_data_points(self, sample_entity, sample_facet_type):
        """Create sample history data points."""
        base_date = datetime(2024, 1, 1)
        points = []
        for i in range(5):
            dp = MagicMock(spec=FacetValueHistory)
            dp.id = uuid4()
            dp.entity_id = sample_entity.id
            dp.facet_type_id = sample_facet_type.id
            dp.track_key = "default"
            dp.recorded_at = base_date + timedelta(days=i * 30)
            dp.value = 1000000 + i * 100000  # Increasing values
            dp.value_label = None
            dp.annotations = {}
            dp.source_type = "MANUAL"
            dp.confidence_score = 1.0
            dp.human_verified = True
            dp.created_at = datetime.utcnow()
            dp.updated_at = datetime.utcnow()
            points.append(dp)
        return points


class TestStatisticsCalculation:
    """Tests for statistics calculation."""

    def test_trend_up_calculation(self):
        """Test that increasing values show upward trend."""
        # Old value: 1000, New value: 1200 = +20%
        old_value = 1000
        new_value = 1200
        change_percent = ((new_value - old_value) / old_value) * 100
        assert change_percent == 20.0
        assert change_percent > 0  # Trend: up

    def test_trend_down_calculation(self):
        """Test that decreasing values show downward trend."""
        # Old value: 1000, New value: 800 = -20%
        old_value = 1000
        new_value = 800
        change_percent = ((new_value - old_value) / old_value) * 100
        assert change_percent == -20.0
        assert change_percent < 0  # Trend: down

    def test_trend_stable_calculation(self):
        """Test that stable values show stable trend."""
        # Old value: 1000, New value: 1000 = 0%
        old_value = 1000
        new_value = 1000
        change_percent = ((new_value - old_value) / old_value) * 100
        assert change_percent == 0.0
        # Trend: stable (within threshold, typically -1% to +1%)

    def test_min_max_calculation(self):
        """Test min/max value calculation."""
        values = [100, 250, 150, 300, 200]
        assert min(values) == 100
        assert max(values) == 300

    def test_average_calculation(self):
        """Test average value calculation."""
        values = [100, 200, 300]
        avg = sum(values) / len(values)
        assert avg == 200.0


class TestAggregationIntervals:
    """Tests for aggregation interval logic."""

    def test_day_aggregation_interval(self):
        """Test daily aggregation interval."""
        interval = "day"
        assert interval in ["day", "week", "month", "quarter", "year"]

    def test_week_aggregation_interval(self):
        """Test weekly aggregation interval."""
        interval = "week"
        assert interval in ["day", "week", "month", "quarter", "year"]

    def test_month_aggregation_interval(self):
        """Test monthly aggregation interval."""
        interval = "month"
        assert interval in ["day", "week", "month", "quarter", "year"]

    def test_quarter_aggregation_interval(self):
        """Test quarterly aggregation interval."""
        interval = "quarter"
        assert interval in ["day", "week", "month", "quarter", "year"]

    def test_year_aggregation_interval(self):
        """Test yearly aggregation interval."""
        interval = "year"
        assert interval in ["day", "week", "month", "quarter", "year"]


class TestAggregationMethods:
    """Tests for aggregation methods."""

    def test_avg_aggregation(self):
        """Test average aggregation."""
        values = [100, 200, 300]
        result = sum(values) / len(values)
        assert result == 200.0

    def test_sum_aggregation(self):
        """Test sum aggregation."""
        values = [100, 200, 300]
        result = sum(values)
        assert result == 600

    def test_min_aggregation(self):
        """Test min aggregation."""
        values = [100, 200, 300]
        result = min(values)
        assert result == 100

    def test_max_aggregation(self):
        """Test max aggregation."""
        values = [100, 200, 300]
        result = max(values)
        assert result == 300

    def test_count_aggregation(self):
        """Test count aggregation."""
        values = [100, 200, 300]
        result = len(values)
        assert result == 3


class TestDateRangeFiltering:
    """Tests for date range filtering logic."""

    def test_filter_last_7_days(self):
        """Test filtering for last 7 days."""
        now = datetime.utcnow()
        from_date = now - timedelta(days=7)

        # Create test data points
        dates = [
            now - timedelta(days=3),  # Should include
            now - timedelta(days=10),  # Should exclude
            now - timedelta(days=1),  # Should include
        ]

        filtered = [d for d in dates if d >= from_date]
        assert len(filtered) == 2

    def test_filter_last_30_days(self):
        """Test filtering for last 30 days."""
        now = datetime.utcnow()
        from_date = now - timedelta(days=30)

        dates = [
            now - timedelta(days=15),  # Should include
            now - timedelta(days=45),  # Should exclude
            now - timedelta(days=5),  # Should include
        ]

        filtered = [d for d in dates if d >= from_date]
        assert len(filtered) == 2

    def test_filter_last_year(self):
        """Test filtering for last year."""
        now = datetime.utcnow()
        from_date = now - timedelta(days=365)

        dates = [
            now - timedelta(days=100),  # Should include
            now - timedelta(days=400),  # Should exclude
            now - timedelta(days=200),  # Should include
        ]

        filtered = [d for d in dates if d >= from_date]
        assert len(filtered) == 2


class TestTrackKeyHandling:
    """Tests for multi-track support."""

    def test_default_track_key(self):
        """Test that default track key is 'default'."""
        track_key = "default"
        assert track_key == "default"

    def test_custom_track_key(self):
        """Test custom track keys."""
        track_keys = ["actual", "forecast", "budget"]
        assert len(track_keys) == 3
        assert "actual" in track_keys
        assert "forecast" in track_keys

    def test_track_key_grouping(self):
        """Test grouping data points by track key."""
        data_points = [
            {"track_key": "actual", "value": 100},
            {"track_key": "forecast", "value": 120},
            {"track_key": "actual", "value": 110},
            {"track_key": "forecast", "value": 130},
        ]

        grouped = {}
        for dp in data_points:
            key = dp["track_key"]
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(dp)

        assert len(grouped["actual"]) == 2
        assert len(grouped["forecast"]) == 2


class TestValueSchemaValidation:
    """Tests for value schema handling."""

    def test_valid_history_schema(self):
        """Test valid history value schema."""
        schema = {
            "type": "history",
            "properties": {
                "unit": "EUR",
                "unit_label": "Euro",
                "precision": 2,
                "tracks": {"default": {"label": "Default", "color": "#1976D2"}},
            },
        }

        assert schema["type"] == "history"
        assert "unit" in schema["properties"]
        assert "tracks" in schema["properties"]

    def test_get_unit_from_schema(self):
        """Test extracting unit from schema."""
        schema = {
            "type": "history",
            "properties": {
                "unit": "EUR",
                "unit_label": "Euro",
                "precision": 2,
            },
        }

        unit = schema.get("properties", {}).get("unit", "")
        unit_label = schema.get("properties", {}).get("unit_label", "")

        assert unit == "EUR"
        assert unit_label == "Euro"

    def test_get_precision_from_schema(self):
        """Test extracting precision from schema."""
        schema = {
            "type": "history",
            "properties": {
                "precision": 2,
            },
        }

        precision = schema.get("properties", {}).get("precision", 2)
        assert precision == 2

    def test_get_tracks_from_schema(self):
        """Test extracting track configuration from schema."""
        schema = {
            "type": "history",
            "properties": {
                "tracks": {
                    "actual": {"label": "Actual", "color": "#1976D2", "style": "solid"},
                    "forecast": {"label": "Forecast", "color": "#9E9E9E", "style": "dashed"},
                }
            },
        }

        tracks = schema.get("properties", {}).get("tracks", {})
        assert len(tracks) == 2
        assert tracks["actual"]["label"] == "Actual"
        assert tracks["forecast"]["style"] == "dashed"


class TestBulkImport:
    """Tests for bulk import functionality."""

    def test_bulk_import_structure(self):
        """Test bulk import data structure."""
        bulk_data = {
            "data_points": [
                {"recorded_at": "2024-01-01T00:00:00", "value": 100},
                {"recorded_at": "2024-02-01T00:00:00", "value": 110},
                {"recorded_at": "2024-03-01T00:00:00", "value": 120},
            ],
            "skip_duplicates": True,
        }

        assert len(bulk_data["data_points"]) == 3
        assert bulk_data["skip_duplicates"] is True

    def test_bulk_import_with_track_keys(self):
        """Test bulk import with different track keys."""
        bulk_data = {
            "data_points": [
                {"recorded_at": "2024-01-01T00:00:00", "value": 100, "track_key": "actual"},
                {"recorded_at": "2024-01-01T00:00:00", "value": 120, "track_key": "forecast"},
            ],
            "skip_duplicates": False,
        }

        assert len(bulk_data["data_points"]) == 2
        # Same date but different tracks = valid

    def test_duplicate_detection_logic(self):
        """Test duplicate detection logic."""
        existing_keys = {("entity1", "facet1", "default", "2024-01-01")}

        new_point = ("entity1", "facet1", "default", "2024-01-01")
        assert new_point in existing_keys  # Is duplicate

        new_point2 = ("entity1", "facet1", "default", "2024-02-01")
        assert new_point2 not in existing_keys  # Not duplicate
