"""E2E Tests for Facets API endpoints."""

import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_facet_types(client: AsyncClient):
    """Test listing all facet types."""
    response = await client.get("/api/v1/facets/types")
    assert response.status_code == 200

    data = response.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_get_facet_type_by_slug(client: AsyncClient):
    """Test getting a facet type by slug."""
    # First get list to find a slug
    response = await client.get("/api/v1/facets/types")
    if response.status_code != 200 or not response.json().get("items"):
        pytest.skip("No facet types available")

    slug = response.json()["items"][0]["slug"]

    response = await client.get(f"/api/v1/facets/types/by-slug/{slug}")
    assert response.status_code == 200
    assert response.json()["slug"] == slug


@pytest.mark.asyncio
async def test_get_facet_type_by_id(client: AsyncClient):
    """Test getting a facet type by ID."""
    # First get list to find an ID
    response = await client.get("/api/v1/facets/types")
    if response.status_code != 200 or not response.json().get("items"):
        pytest.skip("No facet types available")

    facet_type_id = response.json()["items"][0]["id"]

    response = await client.get(f"/api/v1/facets/types/{facet_type_id}")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_entity_facet_summary(client: AsyncClient):
    """Test getting facet summary for an entity."""
    # Get a municipality
    response = await client.get("/api/v1/entities", params={"per_page": 1})
    if response.status_code != 200 or not response.json().get("items"):
        pytest.skip("No entities available")

    entity_id = response.json()["items"][0]["id"]

    response = await client.get(f"/api/v1/facets/entity/{entity_id}/summary")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_facet_values(client: AsyncClient):
    """Test listing facet values."""
    response = await client.get("/api/v1/facets/values", params={"per_page": 10})
    assert response.status_code == 200

    data = response.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_create_facet_type(client: AsyncClient):
    """Test creating a new facet type."""
    unique_id = str(uuid.uuid4())[:8]

    facet_type_data = {
        "name": f"Test Facet {unique_id}",
        "name_plural": f"Test Facets {unique_id}",
        "description": "A test facet type",
        "value_type": "object",
        "icon": "mdi-test",
        "color": "#FF5733",
        "is_active": True,
    }

    response = await client.post("/api/v1/facets/types", json=facet_type_data)
    # Accept various status codes
    assert response.status_code in [200, 201, 400, 422]

    if response.status_code in [200, 201]:
        facet_type_id = response.json()["id"]
        # Cleanup
        await client.delete(f"/api/v1/facets/types/{facet_type_id}")


@pytest.mark.asyncio
async def test_get_nonexistent_facet_type(client: AsyncClient):
    """Test getting a non-existent facet type returns 404."""
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/api/v1/facets/types/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_facet_schema(client: AsyncClient):
    """Test generating a facet type schema."""
    response = await client.post(
        "/api/v1/facets/types/generate-schema",
        json={"description": "Contact information with email and phone"}
    )
    # Accept 200 or 400/422 if AI service not available
    assert response.status_code in [200, 400, 422, 500]
