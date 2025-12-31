"""Tests for Entities API endpoints."""

import uuid

import pytest
from httpx import AsyncClient


async def create_test_entity_type(admin_client: AsyncClient) -> str:
    """Create a test entity type and return its ID."""
    unique_id = str(uuid.uuid4())[:8]
    response = await admin_client.post(
        "/api/v1/entity-types",
        json={
            "name": f"Test Type {unique_id}",
            "name_plural": f"Test Types {unique_id}",
            "icon": "mdi-test",
            "color": "#00FF00",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.asyncio
async def test_list_entities(admin_client: AsyncClient):
    """Test listing entities."""
    response = await admin_client.get("/api/v1/entities")
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data


@pytest.mark.asyncio
async def test_create_and_delete_entity(admin_client: AsyncClient):
    """Test creating and deleting an entity."""
    entity_type_id = await create_test_entity_type(admin_client)
    unique_id = str(uuid.uuid4())[:8]

    entity_data = {
        "entity_type_id": entity_type_id,
        "name": f"Test Entity {unique_id}",
        "external_id": f"TEST-{unique_id}",
    }

    # Create
    response = await admin_client.post("/api/v1/entities", json=entity_data)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == entity_data["name"]
    assert data["entity_type_id"] == entity_type_id
    entity_id = data["id"]

    # Delete entity
    await admin_client.delete(f"/api/v1/entities/{entity_id}")

    # Cleanup entity type
    await admin_client.delete(f"/api/v1/entity-types/{entity_type_id}")


@pytest.mark.asyncio
async def test_get_entity_by_id(admin_client: AsyncClient):
    """Test getting entity by ID."""
    entity_type_id = await create_test_entity_type(admin_client)
    unique_id = str(uuid.uuid4())[:8]

    # Create
    create_response = await admin_client.post("/api/v1/entities", json={
        "entity_type_id": entity_type_id,
        "name": f"Test Entity {unique_id}",
    })
    assert create_response.status_code == 201
    entity_id = create_response.json()["id"]

    # Get by ID
    response = await admin_client.get(f"/api/v1/entities/{entity_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == entity_id

    # Cleanup
    await admin_client.delete(f"/api/v1/entities/{entity_id}")
    await admin_client.delete(f"/api/v1/entity-types/{entity_type_id}")


@pytest.mark.asyncio
async def test_update_entity(admin_client: AsyncClient):
    """Test updating an entity."""
    entity_type_id = await create_test_entity_type(admin_client)
    unique_id = str(uuid.uuid4())[:8]

    # Create
    create_response = await admin_client.post("/api/v1/entities", json={
        "entity_type_id": entity_type_id,
        "name": f"Test Entity {unique_id}",
    })
    assert create_response.status_code == 201
    entity_id = create_response.json()["id"]

    # Update
    new_name = f"Updated Entity {unique_id}"
    response = await admin_client.put(
        f"/api/v1/entities/{entity_id}",
        json={"name": new_name}
    )
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == new_name

    # Cleanup
    await admin_client.delete(f"/api/v1/entities/{entity_id}")
    await admin_client.delete(f"/api/v1/entity-types/{entity_type_id}")


@pytest.mark.asyncio
async def test_search_entities(admin_client: AsyncClient):
    """Test searching entities by name."""
    # Search in existing entities (municipalities)
    response = await admin_client.get("/api/v1/entities?search=Berlin&per_page=5")
    assert response.status_code == 200

    data = response.json()
    # Just check the response structure
    assert "items" in data
    assert "total" in data
