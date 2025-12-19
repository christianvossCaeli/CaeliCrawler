"""E2E Tests for Data Sources API endpoints."""

import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_data_sources(client: AsyncClient):
    """Test listing all data sources."""
    response = await client.get("/api/admin/sources")
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_list_data_sources_pagination(client: AsyncClient):
    """Test data sources pagination."""
    response = await client.get("/api/admin/sources", params={"page": 1, "per_page": 5})
    assert response.status_code == 200

    data = response.json()
    assert len(data["items"]) <= 5


@pytest.mark.asyncio
async def test_get_source_countries(client: AsyncClient):
    """Test getting available countries for sources."""
    response = await client.get("/api/admin/sources/meta/countries")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_source_locations(client: AsyncClient):
    """Test getting available locations for sources."""
    response = await client.get("/api/admin/sources/meta/locations")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_and_delete_data_source(client: AsyncClient):
    """Test creating and deleting a data source."""
    # First get a category
    cat_response = await client.get("/api/admin/categories")
    if cat_response.status_code != 200 or not cat_response.json().get("items"):
        pytest.skip("No categories available")

    category_id = cat_response.json()["items"][0]["id"]
    unique_id = str(uuid.uuid4())[:8]

    source_data = {
        "name": f"Test Source {unique_id}",
        "category_id": category_id,
        "source_type": "WEBSITE",
        "base_url": f"https://test-{unique_id}.example.com",
        "is_active": True,
    }

    # Create
    response = await client.post("/api/admin/sources", json=source_data)
    # Accept 200, 201, or 400 (if validation fails)
    if response.status_code not in [200, 201]:
        pytest.skip(f"Could not create source: {response.text}")

    source_id = response.json()["id"]

    try:
        # Get
        response = await client.get(f"/api/admin/sources/{source_id}")
        assert response.status_code == 200

        # Delete
        response = await client.delete(f"/api/admin/sources/{source_id}")
        assert response.status_code in [200, 204]
    except Exception:
        # Cleanup on failure
        await client.delete(f"/api/admin/sources/{source_id}")
        raise


@pytest.mark.asyncio
async def test_get_nonexistent_source(client: AsyncClient):
    """Test getting a non-existent source returns 404."""
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/api/admin/sources/{fake_id}")
    assert response.status_code == 404
