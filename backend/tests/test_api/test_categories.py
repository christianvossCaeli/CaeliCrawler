"""E2E Tests for Categories API endpoints."""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_categories(admin_client: AsyncClient):
    """Test listing all categories."""
    response = await admin_client.get("/api/admin/categories")
    assert response.status_code == 200

    data = response.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_create_and_delete_category(admin_client: AsyncClient):
    """Test creating and deleting a category."""
    unique_id = str(uuid.uuid4())[:8]

    category_data = {
        "name": f"Test Category {unique_id}",
        "description": "A test category",
        "purpose": "Testing",
        "is_active": True,
    }

    # Create
    response = await admin_client.post("/api/admin/categories", json=category_data)
    assert response.status_code in [200, 201]

    category_id = response.json()["id"]

    try:
        # Get
        response = await admin_client.get(f"/api/admin/categories/{category_id}")
        assert response.status_code == 200
        assert response.json()["name"] == category_data["name"]

        # Get stats
        response = await admin_client.get(f"/api/admin/categories/{category_id}/stats")
        assert response.status_code == 200

        # Delete
        response = await admin_client.delete(f"/api/admin/categories/{category_id}")
        assert response.status_code in [200, 204]

        # Verify deleted
        response = await admin_client.get(f"/api/admin/categories/{category_id}")
        assert response.status_code == 404
    except Exception:
        # Cleanup on failure
        await admin_client.delete(f"/api/admin/categories/{category_id}")
        raise


@pytest.mark.asyncio
async def test_update_category(admin_client: AsyncClient):
    """Test updating a category."""
    unique_id = str(uuid.uuid4())[:8]

    category_data = {
        "name": f"Test Category {unique_id}",
        "description": "Original description",
        "purpose": "Testing",
    }

    # Create
    response = await admin_client.post("/api/admin/categories", json=category_data)
    assert response.status_code in [200, 201]
    category_id = response.json()["id"]

    try:
        # Update
        updated_data = {
            "name": f"Updated Category {unique_id}",
            "description": "Updated description",
        }
        response = await admin_client.put(f"/api/admin/categories/{category_id}", json=updated_data)
        assert response.status_code == 200
        assert response.json()["description"] == "Updated description"
    finally:
        # Cleanup
        await admin_client.delete(f"/api/admin/categories/{category_id}")


@pytest.mark.asyncio
async def test_get_nonexistent_category(admin_client: AsyncClient):
    """Test getting a non-existent category returns 404."""
    fake_id = str(uuid.uuid4())
    response = await admin_client.get(f"/api/admin/categories/{fake_id}")
    assert response.status_code == 404
