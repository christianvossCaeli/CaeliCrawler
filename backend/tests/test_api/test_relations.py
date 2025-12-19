"""E2E Tests for Relations API endpoints."""

import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_relation_types(client: AsyncClient):
    """Test listing all relation types."""
    response = await client.get("/api/v1/relations/types")
    assert response.status_code == 200

    data = response.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_get_relation_type_by_slug(client: AsyncClient):
    """Test getting a relation type by slug."""
    # First get list to find a slug
    response = await client.get("/api/v1/relations/types")
    if response.status_code != 200 or not response.json().get("items"):
        pytest.skip("No relation types available")

    slug = response.json()["items"][0]["slug"]

    response = await client.get(f"/api/v1/relations/types/by-slug/{slug}")
    assert response.status_code == 200
    assert response.json()["slug"] == slug


@pytest.mark.asyncio
async def test_get_relation_type_by_id(client: AsyncClient):
    """Test getting a relation type by ID."""
    # First get list to find an ID
    response = await client.get("/api/v1/relations/types")
    if response.status_code != 200 or not response.json().get("items"):
        pytest.skip("No relation types available")

    relation_type_id = response.json()["items"][0]["id"]

    response = await client.get(f"/api/v1/relations/types/{relation_type_id}")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_relations(client: AsyncClient):
    """Test listing all relations."""
    response = await client.get("/api/v1/relations", params={"per_page": 10})
    assert response.status_code == 200

    data = response.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_get_entity_relation_graph(client: AsyncClient):
    """Test getting relation graph for an entity."""
    # Get a municipality
    response = await client.get("/api/v1/entities", params={"per_page": 1})
    if response.status_code != 200 or not response.json().get("items"):
        pytest.skip("No entities available")

    entity_id = response.json()["items"][0]["id"]

    response = await client.get(f"/api/v1/relations/graph/{entity_id}")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_nonexistent_relation_type(client: AsyncClient):
    """Test getting a non-existent relation type returns 404."""
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/api/v1/relations/types/{fake_id}")
    assert response.status_code == 404
