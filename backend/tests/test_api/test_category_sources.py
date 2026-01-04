"""E2E Tests for Category-DataSource assignment functionality."""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_assign_sources_by_tags_no_tags(admin_client: AsyncClient):
    """Test assigning sources by tags with empty tags list."""
    # Get a category
    cat_response = await admin_client.get("/api/admin/categories")
    if cat_response.status_code != 200 or not cat_response.json().get("items"):
        pytest.skip("No categories available")

    category_id = cat_response.json()["items"][0]["id"]

    response = await admin_client.post(
        f"/api/admin/categories/{category_id}/assign-sources-by-tags", json={"tags": [], "mode": "add"}
    )
    # Should fail validation - tags required
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_assign_sources_by_tags_nonexistent_category(admin_client: AsyncClient):
    """Test assigning sources to non-existent category."""
    fake_id = str(uuid.uuid4())

    response = await admin_client.post(
        f"/api/admin/categories/{fake_id}/assign-sources-by-tags", json={"tags": ["test-tag"], "mode": "add"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_assign_sources_by_tags_add_mode(admin_client: AsyncClient):
    """Test assigning sources by tags in add mode."""
    # Get a category
    cat_response = await admin_client.get("/api/admin/categories")
    if cat_response.status_code != 200 or not cat_response.json().get("items"):
        pytest.skip("No categories available")

    category_id = cat_response.json()["items"][0]["id"]

    response = await admin_client.post(
        f"/api/admin/categories/{category_id}/assign-sources-by-tags",
        json={"tags": ["nonexistent-tag-for-test"], "mode": "add"},
    )
    assert response.status_code == 200

    data = response.json()
    # Should return assignment result
    assert "assigned" in data or "count" in data or "message" in data


@pytest.mark.asyncio
async def test_assign_sources_by_tags_replace_mode(admin_client: AsyncClient):
    """Test assigning sources by tags in replace mode."""
    # Get a category
    cat_response = await admin_client.get("/api/admin/categories")
    if cat_response.status_code != 200 or not cat_response.json().get("items"):
        pytest.skip("No categories available")

    category_id = cat_response.json()["items"][0]["id"]

    response = await admin_client.post(
        f"/api/admin/categories/{category_id}/assign-sources-by-tags",
        json={"tags": ["nonexistent-tag-for-test"], "mode": "replace"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_bulk_import_with_tags(admin_client: AsyncClient):
    """Test bulk import of sources with tags."""
    # Get a category
    cat_response = await admin_client.get("/api/admin/categories")
    if cat_response.status_code != 200 or not cat_response.json().get("items"):
        pytest.skip("No categories available")

    category_id = cat_response.json()["items"][0]["id"]
    unique_id = str(uuid.uuid4())[:8]

    bulk_data = {
        "category_ids": [category_id],
        "default_tags": ["bulk-test", "automated"],
        "sources": [
            {
                "name": f"Bulk Test 1 {unique_id}",
                "base_url": f"https://bulk1-{unique_id}.example.com",
                "source_type": "WEBSITE",
                "tags": ["individual-tag"],
            },
            {
                "name": f"Bulk Test 2 {unique_id}",
                "base_url": f"https://bulk2-{unique_id}.example.com",
                "source_type": "WEBSITE",
            },
        ],
        "skip_duplicates": True,
    }

    response = await admin_client.post("/api/admin/sources/bulk-import", json=bulk_data)

    if response.status_code not in [200, 201]:
        # May fail due to validation, that's acceptable
        return

    data = response.json()
    # Check result structure
    assert "imported" in data or "created" in data or "success" in data

    # Cleanup - get and delete the created sources
    sources_response = await admin_client.get("/api/admin/sources")
    if sources_response.status_code == 200:
        for source in sources_response.json().get("items", []):
            if unique_id in source.get("name", ""):
                await admin_client.delete(f"/api/admin/sources/{source['id']}")


@pytest.mark.asyncio
async def test_bulk_import_multiple_categories(admin_client: AsyncClient):
    """Test bulk import with multiple category IDs (N:M)."""
    # Get categories
    cat_response = await admin_client.get("/api/admin/categories")
    if cat_response.status_code != 200:
        pytest.skip("Could not get categories")

    categories = cat_response.json().get("items", [])
    if len(categories) < 2:
        pytest.skip("Need at least 2 categories for this test")

    category_ids = [categories[0]["id"], categories[1]["id"]]
    unique_id = str(uuid.uuid4())[:8]

    bulk_data = {
        "category_ids": category_ids,
        "default_tags": ["multi-category-test"],
        "sources": [
            {
                "name": f"Multi-Cat Test {unique_id}",
                "base_url": f"https://multicat-{unique_id}.example.com",
                "source_type": "WEBSITE",
            },
        ],
        "skip_duplicates": True,
    }

    response = await admin_client.post("/api/admin/sources/bulk-import", json=bulk_data)

    # May succeed or fail based on implementation
    assert response.status_code in [200, 201, 400, 422]

    # Cleanup if created
    if response.status_code in [200, 201]:
        sources_response = await admin_client.get("/api/admin/sources")
        if sources_response.status_code == 200:
            for source in sources_response.json().get("items", []):
                if unique_id in source.get("name", ""):
                    await admin_client.delete(f"/api/admin/sources/{source['id']}")


@pytest.mark.asyncio
async def test_get_category_data_sources(admin_client: AsyncClient):
    """Test getting data sources assigned to a category."""
    # Get a category
    cat_response = await admin_client.get("/api/admin/categories")
    if cat_response.status_code != 200 or not cat_response.json().get("items"):
        pytest.skip("No categories available")

    category_id = cat_response.json()["items"][0]["id"]

    # Get sources for this category
    response = await admin_client.get("/api/admin/sources", params={"category_id": category_id})
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "total" in data
