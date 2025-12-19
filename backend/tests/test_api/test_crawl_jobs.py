"""E2E Tests for Crawl Jobs API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_crawl_jobs(client: AsyncClient):
    """Test listing all crawl jobs."""
    response = await client.get("/api/admin/crawler/jobs")
    assert response.status_code == 200

    data = response.json()
    assert "items" in data or isinstance(data, list)


@pytest.mark.asyncio
async def test_get_crawler_status(client: AsyncClient):
    """Test getting crawler status."""
    response = await client.get("/api/admin/crawler/status")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, dict)


@pytest.mark.asyncio
async def test_get_crawler_stats(client: AsyncClient):
    """Test getting crawler statistics."""
    response = await client.get("/api/admin/crawler/stats")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, dict)


@pytest.mark.asyncio
async def test_get_running_jobs(client: AsyncClient):
    """Test getting currently running jobs."""
    response = await client.get("/api/admin/crawler/running")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, (list, dict))


@pytest.mark.asyncio
async def test_get_ai_tasks(client: AsyncClient):
    """Test getting AI processing tasks."""
    response = await client.get("/api/admin/crawler/ai-tasks")
    assert response.status_code == 200

    data = response.json()
    assert "items" in data or isinstance(data, list)


@pytest.mark.asyncio
async def test_get_running_ai_tasks(client: AsyncClient):
    """Test getting running AI tasks."""
    response = await client.get("/api/admin/crawler/ai-tasks/running")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_nonexistent_job(client: AsyncClient):
    """Test getting a non-existent job returns 404."""
    import uuid
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/api/admin/crawler/jobs/{fake_id}")
    assert response.status_code == 404
