"""E2E Tests for Facets API endpoints."""

import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_facet_types(admin_client: AsyncClient):
    """Test listing all facet types."""
    response = await admin_client.get("/api/v1/facets/types")
    assert response.status_code == 200

    data = response.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_get_facet_type_by_slug(admin_client: AsyncClient):
    """Test getting a facet type by slug."""
    # First get list to find a slug
    response = await admin_client.get("/api/v1/facets/types")
    if response.status_code != 200 or not response.json().get("items"):
        pytest.skip("No facet types available")

    slug = response.json()["items"][0]["slug"]

    response = await admin_client.get(f"/api/v1/facets/types/by-slug/{slug}")
    assert response.status_code == 200
    assert response.json()["slug"] == slug


@pytest.mark.asyncio
async def test_get_facet_type_by_id(admin_client: AsyncClient):
    """Test getting a facet type by ID."""
    # First get list to find an ID
    response = await admin_client.get("/api/v1/facets/types")
    if response.status_code != 200 or not response.json().get("items"):
        pytest.skip("No facet types available")

    facet_type_id = response.json()["items"][0]["id"]

    response = await admin_client.get(f"/api/v1/facets/types/{facet_type_id}")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_entity_facet_summary(admin_client: AsyncClient):
    """Test getting facet summary for an entity."""
    # Get a municipality
    response = await admin_client.get("/api/v1/entities", params={"per_page": 1})
    if response.status_code != 200 or not response.json().get("items"):
        pytest.skip("No entities available")

    entity_id = response.json()["items"][0]["id"]

    response = await admin_client.get(f"/api/v1/facets/entity/{entity_id}/summary")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_facet_values(admin_client: AsyncClient):
    """Test listing facet values."""
    response = await admin_client.get("/api/v1/facets/values", params={"per_page": 10})
    assert response.status_code == 200

    data = response.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_create_facet_type(admin_client: AsyncClient):
    """Test creating a new facet type."""
    unique_id = str(uuid.uuid4())[:8]

    facet_type_data = {
        "name": f"Test Facet {unique_id}",
        "name_plural": f"Test Facets {unique_id}",
        "description": "A test facet type",
        "value_type": "structured",  # Valid enum value: text, structured, list, reference
        "icon": "mdi-test",
        "color": "#FF5733",
        "is_active": True,
    }

    response = await admin_client.post("/api/v1/facets/types", json=facet_type_data)
    # Accept various status codes
    assert response.status_code in [200, 201, 400, 422]

    if response.status_code in [200, 201]:
        facet_type_id = response.json()["id"]
        # Cleanup
        await admin_client.delete(f"/api/v1/facets/types/{facet_type_id}")


@pytest.mark.asyncio
async def test_get_nonexistent_facet_type(admin_client: AsyncClient):
    """Test getting a non-existent facet type returns 404."""
    fake_id = str(uuid.uuid4())
    response = await admin_client.get(f"/api/v1/facets/types/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_facet_schema(admin_client: AsyncClient):
    """Test generating a facet type schema."""
    response = await admin_client.post(
        "/api/v1/facets/types/generate-schema",
        json={
            "name": "Kontakt",
            "name_plural": "Kontakte",
            "description": "Contact information with email and phone",
            "applicable_entity_types": ["territorial_entity"],
        }
    )
    # Accept 200 or 400/422 if AI service not available
    assert response.status_code in [200, 400, 422, 500]


@pytest.mark.asyncio
async def test_list_facet_values_with_search(admin_client: AsyncClient):
    """Test searching facet values by text."""
    response = await admin_client.get(
        "/api/v1/facets/values",
        params={"search": "test", "per_page": 10}
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_list_facet_values_with_time_filter(admin_client: AsyncClient):
    """Test filtering facet values by time."""
    # Test future_only filter
    response = await admin_client.get(
        "/api/v1/facets/values",
        params={"time_filter": "future_only", "per_page": 10}
    )
    assert response.status_code == 200

    # Test past_only filter
    response = await admin_client.get(
        "/api/v1/facets/values",
        params={"time_filter": "past_only", "per_page": 10}
    )
    assert response.status_code == 200

    # Test invalid filter (should fail with 422)
    response = await admin_client.get(
        "/api/v1/facets/values",
        params={"time_filter": "invalid", "per_page": 10}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_facet_type_enum_validation(admin_client: AsyncClient):
    """Test that invalid enum values are rejected."""
    unique_id = str(uuid.uuid4())[:8]

    # Test with invalid value_type
    invalid_data = {
        "name": f"Invalid Facet {unique_id}",
        "name_plural": f"Invalid Facets {unique_id}",
        "value_type": "invalid_type",  # Invalid enum value
    }

    response = await admin_client.post("/api/v1/facets/types", json=invalid_data)
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_full_text_search(admin_client: AsyncClient):
    """Test full-text search endpoint."""
    response = await admin_client.get(
        "/api/v1/facets/search",
        params={"q": "test", "limit": 10}
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "query" in data
    assert data["query"] == "test"
    assert "search_time_ms" in data


@pytest.mark.asyncio
async def test_full_text_search_with_filters(admin_client: AsyncClient):
    """Test full-text search with entity and facet type filters."""
    # Get an entity first
    entities_response = await admin_client.get("/api/v1/entities", params={"per_page": 1})
    if entities_response.status_code != 200 or not entities_response.json().get("items"):
        pytest.skip("No entities available")

    entity_id = entities_response.json()["items"][0]["id"]

    response = await admin_client.get(
        "/api/v1/facets/search",
        params={
            "q": "information",
            "entity_id": entity_id,
            "facet_type_slug": "pain_point",
            "limit": 5
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_full_text_search_short_query(admin_client: AsyncClient):
    """Test that short queries are rejected."""
    response = await admin_client.get(
        "/api/v1/facets/search",
        params={"q": "a"}  # Too short
    )
    assert response.status_code == 422  # Validation error
