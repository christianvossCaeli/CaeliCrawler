"""Tests for Favorites API endpoints."""

import uuid
import pytest
from httpx import AsyncClient


async def create_test_entity_type(admin_client: AsyncClient) -> str:
    """Create a test entity type and return its ID."""
    unique_id = str(uuid.uuid4())[:8]
    response = await admin_client.post(
        "/api/v1/entity-types",
        json={
            "name": f"Fav Test Type {unique_id}",
            "name_plural": f"Fav Test Types {unique_id}",
            "icon": "mdi-star",
            "color": "#FFD700",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


async def create_test_entity(admin_client: AsyncClient, entity_type_id: str) -> str:
    """Create a test entity and return its ID."""
    unique_id = str(uuid.uuid4())[:8]
    response = await admin_client.post(
        "/api/v1/entities",
        json={
            "entity_type_id": entity_type_id,
            "name": f"Fav Test Entity {unique_id}",
            "external_id": f"FAV-TEST-{unique_id}",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.asyncio
async def test_list_favorites_empty(admin_client: AsyncClient):
    """Test listing favorites when empty or contains items."""
    response = await admin_client.get("/api/v1/favorites")
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data
    assert "pages" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_add_favorite(admin_client: AsyncClient):
    """Test adding an entity to favorites."""
    # Create test entity
    entity_type_id = await create_test_entity_type(admin_client)
    entity_id = await create_test_entity(admin_client, entity_type_id)

    try:
        # Add to favorites
        response = await admin_client.post(
            "/api/v1/favorites",
            json={"entity_id": entity_id},
        )
        assert response.status_code == 201

        data = response.json()
        assert data["entity_id"] == entity_id
        assert "id" in data
        assert "created_at" in data
        assert "entity" in data
        assert data["entity"]["id"] == entity_id

        favorite_id = data["id"]

        # Cleanup favorite
        await admin_client.delete(f"/api/v1/favorites/{favorite_id}")
    finally:
        # Cleanup entity and type
        await admin_client.delete(f"/api/v1/entities/{entity_id}")
        await admin_client.delete(f"/api/v1/entity-types/{entity_type_id}")


@pytest.mark.asyncio
async def test_add_favorite_duplicate_error(admin_client: AsyncClient):
    """Test that adding the same entity twice returns a conflict error."""
    # Create test entity
    entity_type_id = await create_test_entity_type(admin_client)
    entity_id = await create_test_entity(admin_client, entity_type_id)

    try:
        # Add to favorites
        response1 = await admin_client.post(
            "/api/v1/favorites",
            json={"entity_id": entity_id},
        )
        assert response1.status_code == 201
        favorite_id = response1.json()["id"]

        # Try to add again - should fail
        response2 = await admin_client.post(
            "/api/v1/favorites",
            json={"entity_id": entity_id},
        )
        assert response2.status_code == 409  # Conflict

        # Cleanup favorite
        await admin_client.delete(f"/api/v1/favorites/{favorite_id}")
    finally:
        # Cleanup entity and type
        await admin_client.delete(f"/api/v1/entities/{entity_id}")
        await admin_client.delete(f"/api/v1/entity-types/{entity_type_id}")


@pytest.mark.asyncio
async def test_add_favorite_entity_not_found(admin_client: AsyncClient):
    """Test that adding a non-existent entity returns 404."""
    fake_entity_id = str(uuid.uuid4())

    response = await admin_client.post(
        "/api/v1/favorites",
        json={"entity_id": fake_entity_id},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_check_favorite_true(admin_client: AsyncClient):
    """Test checking favorite status when entity is favorited."""
    # Create test entity
    entity_type_id = await create_test_entity_type(admin_client)
    entity_id = await create_test_entity(admin_client, entity_type_id)

    try:
        # Add to favorites
        add_response = await admin_client.post(
            "/api/v1/favorites",
            json={"entity_id": entity_id},
        )
        assert add_response.status_code == 201
        favorite_id = add_response.json()["id"]

        # Check favorite status
        response = await admin_client.get(f"/api/v1/favorites/check/{entity_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["entity_id"] == entity_id
        assert data["is_favorited"] is True
        assert data["favorite_id"] == favorite_id

        # Cleanup favorite
        await admin_client.delete(f"/api/v1/favorites/{favorite_id}")
    finally:
        # Cleanup entity and type
        await admin_client.delete(f"/api/v1/entities/{entity_id}")
        await admin_client.delete(f"/api/v1/entity-types/{entity_type_id}")


@pytest.mark.asyncio
async def test_check_favorite_false(admin_client: AsyncClient):
    """Test checking favorite status when entity is not favorited."""
    # Create test entity
    entity_type_id = await create_test_entity_type(admin_client)
    entity_id = await create_test_entity(admin_client, entity_type_id)

    try:
        # Check favorite status without adding
        response = await admin_client.get(f"/api/v1/favorites/check/{entity_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["entity_id"] == entity_id
        assert data["is_favorited"] is False
        assert data["favorite_id"] is None
    finally:
        # Cleanup entity and type
        await admin_client.delete(f"/api/v1/entities/{entity_id}")
        await admin_client.delete(f"/api/v1/entity-types/{entity_type_id}")


@pytest.mark.asyncio
async def test_remove_favorite(admin_client: AsyncClient):
    """Test removing a favorite by favorite ID."""
    # Create test entity
    entity_type_id = await create_test_entity_type(admin_client)
    entity_id = await create_test_entity(admin_client, entity_type_id)

    try:
        # Add to favorites
        add_response = await admin_client.post(
            "/api/v1/favorites",
            json={"entity_id": entity_id},
        )
        assert add_response.status_code == 201
        favorite_id = add_response.json()["id"]

        # Remove favorite
        remove_response = await admin_client.delete(f"/api/v1/favorites/{favorite_id}")
        assert remove_response.status_code == 200
        assert remove_response.json()["message"] == "Favorite removed successfully"

        # Verify it's removed
        check_response = await admin_client.get(f"/api/v1/favorites/check/{entity_id}")
        assert check_response.json()["is_favorited"] is False
    finally:
        # Cleanup entity and type
        await admin_client.delete(f"/api/v1/entities/{entity_id}")
        await admin_client.delete(f"/api/v1/entity-types/{entity_type_id}")


@pytest.mark.asyncio
async def test_remove_favorite_by_entity(admin_client: AsyncClient):
    """Test removing a favorite by entity ID."""
    # Create test entity
    entity_type_id = await create_test_entity_type(admin_client)
    entity_id = await create_test_entity(admin_client, entity_type_id)

    try:
        # Add to favorites
        add_response = await admin_client.post(
            "/api/v1/favorites",
            json={"entity_id": entity_id},
        )
        assert add_response.status_code == 201

        # Remove favorite by entity ID
        remove_response = await admin_client.delete(f"/api/v1/favorites/entity/{entity_id}")
        assert remove_response.status_code == 200
        assert remove_response.json()["message"] == "Favorite removed successfully"

        # Verify it's removed
        check_response = await admin_client.get(f"/api/v1/favorites/check/{entity_id}")
        assert check_response.json()["is_favorited"] is False
    finally:
        # Cleanup entity and type
        await admin_client.delete(f"/api/v1/entities/{entity_id}")
        await admin_client.delete(f"/api/v1/entity-types/{entity_type_id}")


@pytest.mark.asyncio
async def test_remove_favorite_not_found(admin_client: AsyncClient):
    """Test removing a non-existent favorite returns 404."""
    fake_favorite_id = str(uuid.uuid4())

    response = await admin_client.delete(f"/api/v1/favorites/{fake_favorite_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_favorites_with_filter(admin_client: AsyncClient):
    """Test listing favorites with entity type filter."""
    # Create test entity
    entity_type_id = await create_test_entity_type(admin_client)
    entity_id = await create_test_entity(admin_client, entity_type_id)

    # Get entity type slug
    type_response = await admin_client.get(f"/api/v1/entity-types/{entity_type_id}")
    entity_type_slug = type_response.json()["slug"]

    try:
        # Add to favorites
        add_response = await admin_client.post(
            "/api/v1/favorites",
            json={"entity_id": entity_id},
        )
        assert add_response.status_code == 201
        favorite_id = add_response.json()["id"]

        # List with filter
        response = await admin_client.get(
            f"/api/v1/favorites?entity_type_slug={entity_type_slug}"
        )
        assert response.status_code == 200

        data = response.json()
        assert "items" in data
        # Should contain our favorite
        entity_ids = [item["entity_id"] for item in data["items"]]
        assert entity_id in entity_ids

        # Cleanup favorite
        await admin_client.delete(f"/api/v1/favorites/{favorite_id}")
    finally:
        # Cleanup entity and type
        await admin_client.delete(f"/api/v1/entities/{entity_id}")
        await admin_client.delete(f"/api/v1/entity-types/{entity_type_id}")


@pytest.mark.asyncio
async def test_list_favorites_with_search(admin_client: AsyncClient):
    """Test listing favorites with search query."""
    # Create test entity with unique name
    entity_type_id = await create_test_entity_type(admin_client)
    unique_name = f"UniqueSearchTest{uuid.uuid4().hex[:8]}"

    create_response = await admin_client.post(
        "/api/v1/entities",
        json={
            "entity_type_id": entity_type_id,
            "name": unique_name,
        },
    )
    assert create_response.status_code == 201
    entity_id = create_response.json()["id"]

    try:
        # Add to favorites
        add_response = await admin_client.post(
            "/api/v1/favorites",
            json={"entity_id": entity_id},
        )
        assert add_response.status_code == 201
        favorite_id = add_response.json()["id"]

        # Search for the unique name
        response = await admin_client.get(
            f"/api/v1/favorites?search={unique_name[:10]}"
        )
        assert response.status_code == 200

        data = response.json()
        assert data["total"] >= 1
        entity_ids = [item["entity_id"] for item in data["items"]]
        assert entity_id in entity_ids

        # Cleanup favorite
        await admin_client.delete(f"/api/v1/favorites/{favorite_id}")
    finally:
        # Cleanup entity and type
        await admin_client.delete(f"/api/v1/entities/{entity_id}")
        await admin_client.delete(f"/api/v1/entity-types/{entity_type_id}")
