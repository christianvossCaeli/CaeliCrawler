"""Tests for Entity Types API endpoints."""

import uuid
import pytest
from httpx import AsyncClient


def make_unique_entity_type_data():
    """Generate unique entity type data to avoid conflicts."""
    unique_id = str(uuid.uuid4())[:8]
    return {
        "name": f"Test Entity Type {unique_id}",
        "name_plural": f"Test Entity Types {unique_id}",
        "description": "A test entity type",
        "icon": "mdi-test",
        "color": "#FF0000",
        "is_primary": False,
        "supports_hierarchy": False,
    }


@pytest.mark.asyncio
async def test_list_entity_types(client: AsyncClient):
    """Test listing entity types."""
    response = await client.get("/api/v1/entity-types")
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_create_entity_type(admin_client: AsyncClient):
    """Test creating a new entity type."""
    entity_type_data = make_unique_entity_type_data()
    response = await admin_client.post(
        "/api/v1/entity-types",
        json=entity_type_data,
    )
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == entity_type_data["name"]
    assert "id" in data
    assert "slug" in data

    # Cleanup
    await admin_client.delete(f"/api/v1/entity-types/{data['id']}")


@pytest.mark.asyncio
async def test_create_duplicate_entity_type(admin_client: AsyncClient):
    """Test that creating duplicate entity type fails."""
    entity_type_data = make_unique_entity_type_data()

    # Create first
    response1 = await admin_client.post(
        "/api/v1/entity-types",
        json=entity_type_data,
    )
    assert response1.status_code == 201
    entity_type_id = response1.json()["id"]

    # Try to create duplicate
    response2 = await admin_client.post(
        "/api/v1/entity-types",
        json=entity_type_data,
    )
    assert response2.status_code == 409  # Conflict

    # Cleanup
    await admin_client.delete(f"/api/v1/entity-types/{entity_type_id}")


@pytest.mark.asyncio
async def test_get_entity_type_by_id(admin_client: AsyncClient):
    """Test getting entity type by ID."""
    entity_type_data = make_unique_entity_type_data()

    # Create first
    create_response = await admin_client.post(
        "/api/v1/entity-types",
        json=entity_type_data,
    )
    assert create_response.status_code == 201
    entity_type_id = create_response.json()["id"]

    # Get by ID
    response = await admin_client.get(f"/api/v1/entity-types/{entity_type_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == entity_type_data["name"]

    # Cleanup
    await admin_client.delete(f"/api/v1/entity-types/{entity_type_id}")


@pytest.mark.asyncio
async def test_update_entity_type(admin_client: AsyncClient):
    """Test updating an entity type."""
    entity_type_data = make_unique_entity_type_data()

    # Create first
    create_response = await admin_client.post(
        "/api/v1/entity-types",
        json=entity_type_data,
    )
    assert create_response.status_code == 201
    entity_type_id = create_response.json()["id"]

    # Update
    update_data = {"description": "Updated description"}
    response = await admin_client.put(
        f"/api/v1/entity-types/{entity_type_id}",
        json=update_data,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["description"] == "Updated description"

    # Cleanup
    await admin_client.delete(f"/api/v1/entity-types/{entity_type_id}")


@pytest.mark.asyncio
async def test_delete_entity_type(admin_client: AsyncClient):
    """Test deleting an entity type."""
    entity_type_data = make_unique_entity_type_data()

    # Create first
    create_response = await admin_client.post(
        "/api/v1/entity-types",
        json=entity_type_data,
    )
    assert create_response.status_code == 201
    entity_type_id = create_response.json()["id"]

    # Delete
    response = await admin_client.delete(f"/api/v1/entity-types/{entity_type_id}")
    assert response.status_code == 200

    # Verify deleted
    get_response = await admin_client.get(f"/api/v1/entity-types/{entity_type_id}")
    assert get_response.status_code == 404
