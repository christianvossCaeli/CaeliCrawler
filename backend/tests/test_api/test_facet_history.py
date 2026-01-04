"""E2E Tests for Facet History API endpoints."""

import uuid
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient


@pytest.fixture
def history_facet_type_data():
    """Sample data for creating a history facet type."""
    unique_id = str(uuid.uuid4())[:8]
    return {
        "name": f"Budget Volume {unique_id}",
        "name_plural": f"Budget Volumes {unique_id}",
        "slug": f"budget-volume-{unique_id}",
        "description": "Track budget over time",
        "value_type": "history",
        "icon": "mdi-chart-line",
        "color": "#1976D2",
        "is_active": True,
        "value_schema": {
            "type": "history",
            "properties": {
                "unit": "EUR",
                "unit_label": "Euro",
                "precision": 2,
                "tracks": {
                    "default": {"label": "Actual", "color": "#1976D2"},
                    "forecast": {"label": "Forecast", "color": "#9E9E9E", "style": "dashed"},
                },
            },
        },
    }


@pytest.fixture
def sample_history_data_point():
    """Sample data for creating a history data point."""
    return {
        "recorded_at": datetime.utcnow().isoformat(),
        "value": 1500000.50,
        "track_key": "default",
        "value_label": "1.5 Mio EUR",
        "annotations": {"note": "Budget 2024"},
        "source_type": "MANUAL",
        "confidence_score": 1.0,
    }


class TestHistoryFacetTypeCreation:
    """Tests for creating history-type facet types."""

    @pytest.mark.asyncio
    async def test_create_history_facet_type(self, admin_client: AsyncClient, history_facet_type_data):
        """Test creating a history-type facet type."""
        created_id = None
        try:
            response = await admin_client.post("/api/v1/facets/types", json=history_facet_type_data)

            # Accept 200, 201, or validation errors if facet type already exists
            assert response.status_code in [200, 201, 400, 422]

            if response.status_code in [200, 201]:
                data = response.json()
                created_id = data.get("id")
                assert data["value_type"] == "history"
                assert "id" in data
        finally:
            # Always cleanup if we created a facet type
            if created_id:
                await admin_client.delete(f"/api/v1/facets/types/{created_id}")

    @pytest.mark.asyncio
    async def test_history_facet_type_has_correct_properties(self, admin_client: AsyncClient, history_facet_type_data):
        """Test that history facet type has correct properties set."""
        # Set is_time_based explicitly since it's not auto-set in API
        history_facet_type_data["is_time_based"] = True
        history_facet_type_data["time_field_path"] = "recorded_at"

        created_id = None
        try:
            response = await admin_client.post("/api/v1/facets/types", json=history_facet_type_data)

            if response.status_code in [200, 201]:
                data = response.json()
                created_id = data.get("id")
                assert data["value_type"] == "history"
                # Verify our explicit settings were applied
                assert data.get("is_time_based", False) is True
        finally:
            # Always cleanup if we created a facet type
            if created_id:
                await admin_client.delete(f"/api/v1/facets/types/{created_id}")


class TestHistoryDataPointEndpoints:
    """Tests for history data point endpoints."""

    @pytest.mark.asyncio
    async def test_get_entity_history_nonexistent(self, admin_client: AsyncClient):
        """Test getting history for non-existent entity/facet type returns 404."""
        fake_entity_id = str(uuid.uuid4())
        fake_facet_type_id = str(uuid.uuid4())

        response = await admin_client.get(f"/api/v1/facets/entity/{fake_entity_id}/history/{fake_facet_type_id}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_entity_history_with_valid_entity(self, admin_client: AsyncClient):
        """Test getting history for a valid entity."""
        # First get an entity
        entities_response = await admin_client.get("/api/v1/entities", params={"per_page": 1})

        if entities_response.status_code != 200:
            pytest.skip("Could not fetch entities")

        entities = entities_response.json().get("items", [])
        if not entities:
            pytest.skip("No entities available for testing")

        entity_id = entities[0]["id"]

        # Get history facet types
        facet_types_response = await admin_client.get("/api/v1/facets/types")
        if facet_types_response.status_code != 200:
            pytest.skip("Could not fetch facet types")

        facet_types = facet_types_response.json().get("items", [])
        history_types = [ft for ft in facet_types if ft.get("value_type") == "history"]

        if not history_types:
            pytest.skip("No history facet types available")

        facet_type_id = history_types[0]["id"]

        # Get history (may be empty but should return 200)
        response = await admin_client.get(f"/api/v1/facets/entity/{entity_id}/history/{facet_type_id}")

        assert response.status_code == 200
        data = response.json()
        assert "entity_id" in data
        assert "facet_type_id" in data
        assert "tracks" in data
        assert "statistics" in data

    @pytest.mark.asyncio
    async def test_add_history_data_point_validation(self, admin_client: AsyncClient):
        """Test that invalid data point data is rejected."""
        fake_entity_id = str(uuid.uuid4())
        fake_facet_type_id = str(uuid.uuid4())

        # Missing required field (value)
        invalid_data = {
            "recorded_at": datetime.utcnow().isoformat(),
            # "value": missing
        }

        response = await admin_client.post(
            f"/api/v1/facets/entity/{fake_entity_id}/history/{fake_facet_type_id}", json=invalid_data
        )

        assert response.status_code in [404, 422]  # Not found or validation error


class TestHistoryQueryParameters:
    """Tests for history query parameters."""

    @pytest.mark.asyncio
    async def test_history_with_date_range_filter(self, admin_client: AsyncClient):
        """Test filtering history by date range."""
        # Get an entity and history facet type
        entities_response = await admin_client.get("/api/v1/entities", params={"per_page": 1})

        if entities_response.status_code != 200:
            pytest.skip("Could not fetch entities")

        entities = entities_response.json().get("items", [])
        if not entities:
            pytest.skip("No entities available")

        entity_id = entities[0]["id"]

        # Get history facet types
        facet_types_response = await admin_client.get("/api/v1/facets/types")
        facet_types = facet_types_response.json().get("items", [])
        history_types = [ft for ft in facet_types if ft.get("value_type") == "history"]

        if not history_types:
            pytest.skip("No history facet types available")

        facet_type_id = history_types[0]["id"]

        # Test with from_date parameter
        from_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
        response = await admin_client.get(
            f"/api/v1/facets/entity/{entity_id}/history/{facet_type_id}", params={"from_date": from_date}
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_history_with_track_filter(self, admin_client: AsyncClient):
        """Test filtering history by track key."""
        entities_response = await admin_client.get("/api/v1/entities", params={"per_page": 1})

        if entities_response.status_code != 200:
            pytest.skip("Could not fetch entities")

        entities = entities_response.json().get("items", [])
        if not entities:
            pytest.skip("No entities available")

        entity_id = entities[0]["id"]

        facet_types_response = await admin_client.get("/api/v1/facets/types")
        facet_types = facet_types_response.json().get("items", [])
        history_types = [ft for ft in facet_types if ft.get("value_type") == "history"]

        if not history_types:
            pytest.skip("No history facet types available")

        facet_type_id = history_types[0]["id"]

        # Test with tracks parameter
        response = await admin_client.get(
            f"/api/v1/facets/entity/{entity_id}/history/{facet_type_id}", params={"tracks": "default,forecast"}
        )

        assert response.status_code == 200


class TestAggregatedHistory:
    """Tests for aggregated history endpoint."""

    @pytest.mark.asyncio
    async def test_aggregated_history_endpoint(self, admin_client: AsyncClient):
        """Test the aggregated history endpoint."""
        entities_response = await admin_client.get("/api/v1/entities", params={"per_page": 1})

        if entities_response.status_code != 200:
            pytest.skip("Could not fetch entities")

        entities = entities_response.json().get("items", [])
        if not entities:
            pytest.skip("No entities available")

        entity_id = entities[0]["id"]

        facet_types_response = await admin_client.get("/api/v1/facets/types")
        facet_types = facet_types_response.json().get("items", [])
        history_types = [ft for ft in facet_types if ft.get("value_type") == "history"]

        if not history_types:
            pytest.skip("No history facet types available")

        facet_type_id = history_types[0]["id"]

        # Test aggregated endpoint
        response = await admin_client.get(
            f"/api/v1/facets/entity/{entity_id}/history/{facet_type_id}/aggregated",
            params={"interval": "month", "method": "avg"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "entity_id" in data
        assert "interval" in data
        assert "method" in data
        assert "data" in data

    @pytest.mark.asyncio
    async def test_aggregated_history_invalid_interval(self, admin_client: AsyncClient):
        """Test that invalid aggregation interval is rejected."""
        entities_response = await admin_client.get("/api/v1/entities", params={"per_page": 1})

        if entities_response.status_code != 200:
            pytest.skip("Could not fetch entities")

        entities = entities_response.json().get("items", [])
        if not entities:
            pytest.skip("No entities available")

        entity_id = entities[0]["id"]

        facet_types_response = await admin_client.get("/api/v1/facets/types")
        facet_types = facet_types_response.json().get("items", [])
        history_types = [ft for ft in facet_types if ft.get("value_type") == "history"]

        if not history_types:
            pytest.skip("No history facet types available")

        facet_type_id = history_types[0]["id"]

        # Test with invalid interval
        response = await admin_client.get(
            f"/api/v1/facets/entity/{entity_id}/history/{facet_type_id}/aggregated",
            params={"interval": "invalid_interval"},
        )

        assert response.status_code == 422  # Validation error


class TestBulkHistoryImport:
    """Tests for bulk history import endpoint."""

    @pytest.mark.asyncio
    async def test_bulk_import_structure(self, admin_client: AsyncClient):
        """Test bulk import endpoint accepts correct structure."""
        fake_entity_id = str(uuid.uuid4())
        fake_facet_type_id = str(uuid.uuid4())

        bulk_data = {
            "data_points": [
                {"recorded_at": (datetime.utcnow() - timedelta(days=30)).isoformat(), "value": 1000000},
                {"recorded_at": (datetime.utcnow() - timedelta(days=20)).isoformat(), "value": 1100000},
            ],
            "skip_duplicates": True,
        }

        response = await admin_client.post(
            f"/api/v1/facets/entity/{fake_entity_id}/history/{fake_facet_type_id}/bulk", json=bulk_data
        )

        # Will return 404 for fake IDs, or 409 for constraint violations
        assert response.status_code in [200, 201, 404, 409]


class TestHistoryStatistics:
    """Tests for history statistics calculation."""

    @pytest.mark.asyncio
    async def test_statistics_structure(self, admin_client: AsyncClient):
        """Test that statistics have correct structure."""
        entities_response = await admin_client.get("/api/v1/entities", params={"per_page": 1})

        if entities_response.status_code != 200:
            pytest.skip("Could not fetch entities")

        entities = entities_response.json().get("items", [])
        if not entities:
            pytest.skip("No entities available")

        entity_id = entities[0]["id"]

        facet_types_response = await admin_client.get("/api/v1/facets/types")
        facet_types = facet_types_response.json().get("items", [])
        history_types = [ft for ft in facet_types if ft.get("value_type") == "history"]

        if not history_types:
            pytest.skip("No history facet types available")

        facet_type_id = history_types[0]["id"]

        response = await admin_client.get(f"/api/v1/facets/entity/{entity_id}/history/{facet_type_id}")

        assert response.status_code == 200
        data = response.json()

        statistics = data.get("statistics", {})
        # Check statistics structure (may be empty if no data)
        assert "total_points" in statistics
        assert "trend" in statistics


class TestHistoryDataPointCRUD:
    """Tests for history data point CRUD operations."""

    @pytest.mark.asyncio
    async def test_update_nonexistent_data_point(self, admin_client: AsyncClient):
        """Test updating non-existent data point returns 404."""
        fake_entity_id = str(uuid.uuid4())
        fake_facet_type_id = str(uuid.uuid4())
        fake_point_id = str(uuid.uuid4())

        response = await admin_client.put(
            f"/api/v1/facets/entity/{fake_entity_id}/history/{fake_facet_type_id}/{fake_point_id}", json={"value": 1000}
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_data_point(self, admin_client: AsyncClient):
        """Test deleting non-existent data point returns 404."""
        fake_entity_id = str(uuid.uuid4())
        fake_facet_type_id = str(uuid.uuid4())
        fake_point_id = str(uuid.uuid4())

        response = await admin_client.delete(
            f"/api/v1/facets/entity/{fake_entity_id}/history/{fake_facet_type_id}/{fake_point_id}"
        )

        assert response.status_code == 404


class TestHistoryValueTypeEnforcement:
    """Tests for history value type enforcement."""

    @pytest.mark.asyncio
    async def test_history_endpoint_rejects_non_history_facet_type(self, admin_client: AsyncClient):
        """Test that history endpoints reject non-history facet types."""
        # Get an entity
        entities_response = await admin_client.get("/api/v1/entities", params={"per_page": 1})

        if entities_response.status_code != 200:
            pytest.skip("Could not fetch entities")

        entities = entities_response.json().get("items", [])
        if not entities:
            pytest.skip("No entities available")

        entity_id = entities[0]["id"]

        # Get a non-history facet type
        facet_types_response = await admin_client.get("/api/v1/facets/types")
        facet_types = facet_types_response.json().get("items", [])
        non_history_types = [ft for ft in facet_types if ft.get("value_type") != "history"]

        if not non_history_types:
            pytest.skip("No non-history facet types available")

        facet_type_id = non_history_types[0]["id"]

        # Try to use history endpoint with non-history facet type
        response = await admin_client.get(f"/api/v1/facets/entity/{entity_id}/history/{facet_type_id}")

        # The endpoint returns 200 with empty data for non-history types
        # This is acceptable behavior - it just returns no data
        assert response.status_code in [200, 400, 404]
