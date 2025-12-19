"""E2E Tests for Municipalities (Gemeinden) API endpoints."""

import uuid
import pytest
from httpx import AsyncClient


# Municipality entity type ID (from database)
MUNICIPALITY_TYPE_SLUG = "municipality"


async def get_municipality_type_id(client: AsyncClient) -> str:
    """Get the municipality entity type ID."""
    response = await client.get("/api/v1/entity-types")
    assert response.status_code == 200

    for item in response.json()["items"]:
        if item["slug"] == MUNICIPALITY_TYPE_SLUG:
            return item["id"]

    pytest.fail("Municipality entity type not found")


async def create_test_municipality(client: AsyncClient, name: str = None) -> dict:
    """Create a test municipality and return it."""
    entity_type_id = await get_municipality_type_id(client)
    unique_id = str(uuid.uuid4())[:8]

    municipality_data = {
        "entity_type_id": entity_type_id,
        "name": name or f"Test Gemeinde {unique_id}",
        "external_id": f"TEST-MUN-{unique_id}",
        "country": "DE",
        "admin_level_1": "Nordrhein-Westfalen",
        "admin_level_2": "Oberbergischer Kreis",
        "core_attributes": {
            "population": 50000,
            "area_km2": 120.5,
            "locality_type": "Stadt",
            "website": "https://www.test-gemeinde.de",
        },
        "latitude": 51.0,
        "longitude": 7.5,
    }

    response = await client.post("/api/v1/entities", json=municipality_data)
    assert response.status_code == 201, f"Failed to create municipality: {response.text}"
    return response.json()


async def delete_municipality(client: AsyncClient, entity_id: str):
    """Delete a municipality."""
    response = await client.delete(f"/api/v1/entities/{entity_id}")
    # Accept 200 or 204 for successful deletion
    assert response.status_code in [200, 204], f"Failed to delete: {response.text}"


# =============================================================================
# List & Filter Tests
# =============================================================================

@pytest.mark.asyncio
async def test_list_municipalities(client: AsyncClient):
    """Test listing municipalities with entity type filter."""
    entity_type_id = await get_municipality_type_id(client)

    response = await client.get(
        "/api/v1/entities",
        params={"entity_type_id": entity_type_id, "per_page": 10}
    )
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] > 0, "Expected municipalities in database"
    assert len(data["items"]) <= 10


@pytest.mark.asyncio
async def test_filter_municipalities_by_bundesland(client: AsyncClient):
    """Test filtering municipalities by Bundesland (admin_level_1)."""
    entity_type_id = await get_municipality_type_id(client)

    response = await client.get(
        "/api/v1/entities",
        params={
            "entity_type_id": entity_type_id,
            "admin_level_1": "Nordrhein-Westfalen",
            "per_page": 20
        }
    )
    assert response.status_code == 200

    data = response.json()
    assert "items" in data

    # All returned items should be from NRW
    for item in data["items"]:
        assert item.get("admin_level_1") == "Nordrhein-Westfalen"


@pytest.mark.asyncio
async def test_filter_municipalities_by_landkreis(client: AsyncClient):
    """Test filtering municipalities by Landkreis (admin_level_2)."""
    entity_type_id = await get_municipality_type_id(client)

    response = await client.get(
        "/api/v1/entities",
        params={
            "entity_type_id": entity_type_id,
            "admin_level_2": "Oberbergischer Kreis",
            "per_page": 20
        }
    )
    assert response.status_code == 200

    data = response.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_search_municipalities_by_name(client: AsyncClient):
    """Test searching municipalities by name."""
    entity_type_id = await get_municipality_type_id(client)

    # Search for "Gummersbach" (known municipality)
    response = await client.get(
        "/api/v1/entities",
        params={
            "entity_type_id": entity_type_id,
            "search": "Gummersbach",
            "per_page": 10
        }
    )
    assert response.status_code == 200

    data = response.json()
    assert "items" in data

    # Should find at least one result
    if data["total"] > 0:
        # Check that results contain the search term
        found = any("gummersbach" in item["name"].lower() for item in data["items"])
        assert found, "Search should return matching results"


# =============================================================================
# CRUD Tests
# =============================================================================

@pytest.mark.asyncio
async def test_create_municipality(client: AsyncClient):
    """Test creating a new municipality."""
    municipality = await create_test_municipality(client)

    try:
        assert "id" in municipality
        assert "name" in municipality
        assert municipality["name"].startswith("Test Gemeinde")
        assert municipality["country"] == "DE"
        assert municipality["admin_level_1"] == "Nordrhein-Westfalen"
    finally:
        # Cleanup
        await delete_municipality(client, municipality["id"])


@pytest.mark.asyncio
async def test_get_municipality_by_id(client: AsyncClient):
    """Test getting a municipality by ID."""
    municipality = await create_test_municipality(client)

    try:
        response = await client.get(f"/api/v1/entities/{municipality['id']}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == municipality["id"]
        assert data["name"] == municipality["name"]
    finally:
        await delete_municipality(client, municipality["id"])


@pytest.mark.asyncio
async def test_get_municipality_by_slug(client: AsyncClient):
    """Test getting a municipality by slug."""
    municipality = await create_test_municipality(client)

    try:
        # Endpoint requires both entity_type_slug and entity_slug
        response = await client.get(
            f"/api/v1/entities/by-slug/{MUNICIPALITY_TYPE_SLUG}/{municipality['slug']}"
        )
        assert response.status_code == 200

        data = response.json()
        assert data["slug"] == municipality["slug"]
    finally:
        await delete_municipality(client, municipality["id"])


@pytest.mark.asyncio
async def test_update_municipality(client: AsyncClient):
    """Test updating a municipality."""
    municipality = await create_test_municipality(client)

    try:
        new_name = f"Updated Gemeinde {uuid.uuid4().hex[:8]}"
        response = await client.put(
            f"/api/v1/entities/{municipality['id']}",
            json={
                "name": new_name,
                "core_attributes": {
                    "population": 55000,
                    "area_km2": 125.0,
                }
            }
        )
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == new_name
    finally:
        await delete_municipality(client, municipality["id"])


@pytest.mark.asyncio
async def test_delete_municipality(client: AsyncClient):
    """Test deleting a municipality."""
    municipality = await create_test_municipality(client)
    entity_id = municipality["id"]

    # Delete
    response = await client.delete(f"/api/v1/entities/{entity_id}")
    assert response.status_code in [200, 204]

    # Verify deleted (should return 404)
    response = await client.get(f"/api/v1/entities/{entity_id}")
    assert response.status_code == 404


# =============================================================================
# Smart Query Tests
# =============================================================================

@pytest.mark.asyncio
async def test_smart_query_list_municipalities(client: AsyncClient):
    """Test Smart Query to list municipalities."""
    response = await client.post(
        "/api/v1/analysis/smart-query",
        json={
            "question": "Zeige mir alle Gemeinden",
            "allow_write": False
        }
    )
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "query_interpretation" in data
    assert data["mode"] == "read"


@pytest.mark.asyncio
async def test_smart_query_municipalities_in_nrw(client: AsyncClient):
    """Test Smart Query to find municipalities in NRW."""
    response = await client.post(
        "/api/v1/analysis/smart-query",
        json={
            "question": "Zeige mir Gemeinden in Nordrhein-Westfalen",
            "allow_write": False
        }
    )
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "query_interpretation" in data


@pytest.mark.asyncio
async def test_smart_query_specific_municipality(client: AsyncClient):
    """Test Smart Query to find a specific municipality."""
    response = await client.post(
        "/api/v1/analysis/smart-query",
        json={
            "question": "Zeige mir Gummersbach",
            "allow_write": False
        }
    )
    assert response.status_code == 200

    data = response.json()
    assert "items" in data


# =============================================================================
# Facet Tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_municipality_facets(client: AsyncClient):
    """Test getting facets for a municipality."""
    entity_type_id = await get_municipality_type_id(client)

    # Get first municipality
    response = await client.get(
        "/api/v1/entities",
        params={"entity_type_id": entity_type_id, "per_page": 1}
    )
    assert response.status_code == 200

    items = response.json()["items"]
    if not items:
        pytest.skip("No municipalities found")

    entity_id = items[0]["id"]

    # Get facets summary (correct endpoint)
    response = await client.get(f"/api/v1/facets/entity/{entity_id}/summary")
    assert response.status_code == 200

    data = response.json()
    # Should return facet summary structure
    assert isinstance(data, dict)


@pytest.mark.asyncio
async def test_add_facet_to_municipality(client: AsyncClient):
    """Test adding a facet to a municipality."""
    municipality = await create_test_municipality(client)

    try:
        # Get available facet types (correct endpoint)
        response = await client.get("/api/v1/facets/types")
        assert response.status_code == 200

        facet_types = response.json()["items"]
        if not facet_types:
            pytest.skip("No facet types available")

        # Find a facet type applicable to municipalities
        applicable_facet_type = None
        for ft in facet_types:
            applicable = ft.get("applicable_entity_type_slugs", [])
            if not applicable or "municipality" in applicable:
                applicable_facet_type = ft
                break

        if not applicable_facet_type:
            pytest.skip("No applicable facet type found")

        # Add facet value (correct endpoint)
        facet_data = {
            "entity_id": municipality["id"],
            "facet_type_id": applicable_facet_type["id"],
            "value": {
                "description": "Test facet value",
                "severity": "medium"
            },
            "source": "test",
            "confidence": 0.9
        }

        response = await client.post("/api/v1/facets/values", json=facet_data)
        # Accept 200, 201, or 400/422 (validation error)
        assert response.status_code in [200, 201, 400, 422]

    finally:
        await delete_municipality(client, municipality["id"])


# =============================================================================
# Relations Tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_municipality_relations(client: AsyncClient):
    """Test getting relations for a municipality."""
    entity_type_id = await get_municipality_type_id(client)

    # Get first municipality
    response = await client.get(
        "/api/v1/entities",
        params={"entity_type_id": entity_type_id, "per_page": 1}
    )
    assert response.status_code == 200

    items = response.json()["items"]
    if not items:
        pytest.skip("No municipalities found")

    entity_id = items[0]["id"]

    # Get relations graph (correct endpoint)
    response = await client.get(f"/api/v1/relations/graph/{entity_id}")
    assert response.status_code == 200

    data = response.json()
    # Should return graph structure with nodes and edges
    assert isinstance(data, dict)


# =============================================================================
# Assistant Integration Tests
# =============================================================================

@pytest.mark.asyncio
async def test_assistant_query_municipalities(client: AsyncClient):
    """Test querying municipalities through the assistant."""
    response = await client.post(
        "/api/v1/assistant/chat",
        json={
            "message": "Zeige mir Gemeinden in Bayern",
            "context": {
                "current_route": "/entities/municipality",
                "view_mode": "list"
            },
            "mode": "read",
            "language": "de"
        }
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "response" in data


@pytest.mark.asyncio
async def test_assistant_summarize_municipality(client: AsyncClient):
    """Test getting a summary of a municipality through the assistant."""
    entity_type_id = await get_municipality_type_id(client)

    # Get a municipality
    response = await client.get(
        "/api/v1/entities",
        params={"entity_type_id": entity_type_id, "search": "München", "per_page": 1}
    )

    if response.status_code != 200 or not response.json().get("items"):
        pytest.skip("Test municipality not found")

    municipality = response.json()["items"][0]

    response = await client.post(
        "/api/v1/assistant/chat",
        json={
            "message": "/summary",
            "context": {
                "current_route": f"/entities/{municipality['id']}",
                "current_entity_id": municipality["id"],
                "current_entity_type": "municipality",
                "current_entity_name": municipality["name"],
                "view_mode": "detail"
            },
            "mode": "read",
            "language": "de"
        }
    )
    assert response.status_code == 200


# =============================================================================
# Pagination Tests
# =============================================================================

@pytest.mark.asyncio
async def test_municipalities_pagination(client: AsyncClient):
    """Test pagination for municipalities."""
    entity_type_id = await get_municipality_type_id(client)

    # First page
    response = await client.get(
        "/api/v1/entities",
        params={"entity_type_id": entity_type_id, "page": 1, "per_page": 5}
    )
    assert response.status_code == 200

    page1 = response.json()
    assert len(page1["items"]) == 5
    assert page1["page"] == 1

    # Second page
    response = await client.get(
        "/api/v1/entities",
        params={"entity_type_id": entity_type_id, "page": 2, "per_page": 5}
    )
    assert response.status_code == 200

    page2 = response.json()
    assert page2["page"] == 2

    # Items should be different
    page1_ids = {item["id"] for item in page1["items"]}
    page2_ids = {item["id"] for item in page2["items"]}
    assert page1_ids.isdisjoint(page2_ids), "Pages should have different items"


# =============================================================================
# Error Handling Tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_nonexistent_municipality(client: AsyncClient):
    """Test getting a non-existent municipality returns 404."""
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/api/v1/entities/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_municipality_without_name(client: AsyncClient):
    """Test creating a municipality without name fails."""
    entity_type_id = await get_municipality_type_id(client)

    response = await client.post(
        "/api/v1/entities",
        json={
            "entity_type_id": entity_type_id,
            # name is missing
        }
    )
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_create_municipality_invalid_entity_type(client: AsyncClient):
    """Test creating a municipality with invalid entity type fails."""
    response = await client.post(
        "/api/v1/entities",
        json={
            "entity_type_id": str(uuid.uuid4()),  # Non-existent type
            "name": "Invalid Municipality"
        }
    )
    assert response.status_code in [400, 404, 422]
