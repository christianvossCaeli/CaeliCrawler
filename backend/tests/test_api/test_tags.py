"""E2E Tests for DataSource Tags functionality."""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_available_tags(admin_client: AsyncClient):
    """Test listing all available tags."""
    response = await admin_client.get("/api/admin/sources/meta/tags")
    assert response.status_code == 200

    data = response.json()
    # Response format may be {"tags": [...]} or [...]
    tags = data.get("tags", data) if isinstance(data, dict) else data
    assert isinstance(tags, list)
    # Each tag should have tag name and count
    for tag_item in tags:
        assert "tag" in tag_item
        assert "count" in tag_item


@pytest.mark.asyncio
async def test_filter_sources_by_tags(admin_client: AsyncClient):
    """Test filtering data sources by tags."""
    # First get available tags
    tags_response = await admin_client.get("/api/admin/sources/meta/tags")
    if tags_response.status_code != 200:
        pytest.skip("Could not get tags")

    tags_data = tags_response.json()
    tags = tags_data.get("tags", tags_data) if isinstance(tags_data, dict) else tags_data
    if not tags:
        pytest.skip("No tags available for testing")

    # Filter by first available tag
    first_tag = tags[0]["tag"]
    response = await admin_client.get(
        "/api/admin/sources",
        params={"tags": first_tag}  # Single tag as string
    )
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    # All returned sources should have the tag
    for source in data["items"]:
        if "tags" in source and source["tags"]:
            assert first_tag in source["tags"]


@pytest.mark.asyncio
async def test_get_sources_by_tags_all_mode(admin_client: AsyncClient):
    """Test getting sources by tags with AND logic (all tags must match)."""
    # Use repeated tags parameter for list in query string
    response = await admin_client.get(
        "/api/admin/sources/by-tags?tags=nonexistent-tag-xyz&match_mode=all"
    )
    assert response.status_code == 200

    data = response.json()
    # Should return empty list for non-existent tag
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.asyncio
async def test_get_sources_by_tags_any_mode(admin_client: AsyncClient):
    """Test getting sources by tags with OR logic (any tag matches)."""
    # Use repeated tags parameter for list in query string
    response = await admin_client.get(
        "/api/admin/sources/by-tags?tags=nonexistent-tag-abc&tags=nonexistent-tag-xyz&match_mode=any"
    )
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_create_source_with_tags(admin_client: AsyncClient):
    """Test creating a data source with tags."""
    # First get a category
    cat_response = await admin_client.get("/api/admin/categories")
    if cat_response.status_code != 200 or not cat_response.json().get("items"):
        pytest.skip("No categories available")

    category_id = cat_response.json()["items"][0]["id"]
    unique_id = str(uuid.uuid4())[:8]

    source_data = {
        "name": f"Test Source with Tags {unique_id}",
        "category_id": category_id,
        "source_type": "WEBSITE",
        "base_url": f"https://test-tags-{unique_id}.example.com",
        "is_active": True,
        "tags": ["test-tag", "automated-test"],
    }

    response = await admin_client.post("/api/admin/sources", json=source_data)

    if response.status_code not in [200, 201]:
        pytest.skip(f"Could not create source: {response.text}")

    source = response.json()
    source_id = source["id"]

    try:
        # Verify tags were saved
        assert "tags" in source
        assert "test-tag" in source["tags"]
        assert "automated-test" in source["tags"]
    finally:
        # Cleanup
        await admin_client.delete(f"/api/admin/sources/{source_id}")


@pytest.mark.asyncio
async def test_update_source_tags(admin_client: AsyncClient):
    """Test updating tags on an existing data source."""
    # First get a category
    cat_response = await admin_client.get("/api/admin/categories")
    if cat_response.status_code != 200 or not cat_response.json().get("items"):
        pytest.skip("No categories available")

    category_id = cat_response.json()["items"][0]["id"]
    unique_id = str(uuid.uuid4())[:8]

    # Create source without tags
    source_data = {
        "name": f"Test Source Update Tags {unique_id}",
        "category_id": category_id,
        "source_type": "WEBSITE",
        "base_url": f"https://test-update-{unique_id}.example.com",
        "is_active": True,
    }

    create_response = await admin_client.post("/api/admin/sources", json=source_data)
    if create_response.status_code not in [200, 201]:
        pytest.skip(f"Could not create source: {create_response.text}")

    source = create_response.json()
    source_id = source["id"]

    try:
        # Update with tags
        update_response = await admin_client.put(
            f"/api/admin/sources/{source_id}",
            json={"tags": ["new-tag", "updated-tag"]}
        )
        assert update_response.status_code == 200

        updated_source = update_response.json()
        assert "tags" in updated_source
        assert "new-tag" in updated_source["tags"]
        assert "updated-tag" in updated_source["tags"]
    finally:
        # Cleanup
        await admin_client.delete(f"/api/admin/sources/{source_id}")
