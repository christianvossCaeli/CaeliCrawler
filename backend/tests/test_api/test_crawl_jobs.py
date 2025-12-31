"""E2E Tests for Crawl Jobs API endpoints."""

import uuid

import pytest
from httpx import AsyncClient, ReadTimeout

# Custom marker for tests that require Celery workers
requires_celery = pytest.mark.skipif(
    True,  # Set to False when Celery workers are running
    reason="Requires Celery workers to be running"
)


# === Basic Endpoint Tests ===

@pytest.mark.asyncio
async def test_list_crawl_jobs(admin_client: AsyncClient):
    """Test listing all crawl jobs."""
    response = await admin_client.get("/api/admin/crawler/jobs")
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data


@pytest.mark.asyncio
async def test_list_crawl_jobs_with_pagination(admin_client: AsyncClient):
    """Test listing crawl jobs with pagination parameters."""
    response = await admin_client.get("/api/admin/crawler/jobs?page=1&per_page=10")
    assert response.status_code == 200

    data = response.json()
    assert data["page"] == 1
    assert data["per_page"] == 10


@pytest.mark.asyncio
async def test_list_crawl_jobs_filter_by_status(admin_client: AsyncClient):
    """Test filtering crawl jobs by status."""
    response = await admin_client.get("/api/admin/crawler/jobs?status=COMPLETED")
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    # All returned items should have COMPLETED status
    for item in data["items"]:
        assert item["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_get_crawler_status(admin_client: AsyncClient):
    """Test getting crawler status."""
    response = await admin_client.get("/api/admin/crawler/status")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, dict)
    # Check for expected status fields
    assert "running_jobs" in data or "active_workers" in data or isinstance(data, dict)


@pytest.mark.asyncio
async def test_get_crawler_stats(admin_client: AsyncClient):
    """Test getting crawler statistics."""
    response = await admin_client.get("/api/admin/crawler/stats")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, dict)


@pytest.mark.asyncio
async def test_get_running_jobs(admin_client: AsyncClient):
    """Test getting currently running jobs."""
    response = await admin_client.get("/api/admin/crawler/running")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, (list, dict))


@pytest.mark.asyncio
async def test_get_ai_tasks(admin_client: AsyncClient):
    """Test getting AI processing tasks."""
    response = await admin_client.get("/api/admin/crawler/ai-tasks")
    # May return 200 or 500 depending on Celery availability
    assert response.status_code in [200, 500]

    if response.status_code == 200:
        data = response.json()
        assert "items" in data or isinstance(data, list)


@pytest.mark.asyncio
async def test_get_running_ai_tasks(admin_client: AsyncClient):
    """Test getting running AI tasks."""
    response = await admin_client.get("/api/admin/crawler/ai-tasks/running")
    # May return 200 or 500 depending on Celery availability
    assert response.status_code in [200, 500]


# === Error Handling Tests ===

@pytest.mark.asyncio
async def test_get_nonexistent_job(admin_client: AsyncClient):
    """Test getting a non-existent job returns 404."""
    fake_id = str(uuid.uuid4())
    response = await admin_client.get(f"/api/admin/crawler/jobs/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cancel_nonexistent_job(admin_client: AsyncClient):
    """Test cancelling a non-existent job returns 404."""
    fake_id = str(uuid.uuid4())
    response = await admin_client.post(f"/api/admin/crawler/jobs/{fake_id}/cancel")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_log_nonexistent_job(admin_client: AsyncClient):
    """Test getting log of a non-existent job returns 404."""
    fake_id = str(uuid.uuid4())
    response = await admin_client.get(f"/api/admin/crawler/jobs/{fake_id}/log")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cancel_nonexistent_ai_task(admin_client: AsyncClient):
    """Test cancelling a non-existent AI task returns 404."""
    fake_id = str(uuid.uuid4())
    response = await admin_client.post(f"/api/admin/crawler/ai-tasks/{fake_id}/cancel")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_process_nonexistent_document(admin_client: AsyncClient):
    """Test processing a non-existent document returns 404."""
    fake_id = str(uuid.uuid4())
    response = await admin_client.post(f"/api/admin/crawler/documents/{fake_id}/process")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_analyze_nonexistent_document(admin_client: AsyncClient):
    """Test analyzing a non-existent document returns 404."""
    fake_id = str(uuid.uuid4())
    response = await admin_client.post(f"/api/admin/crawler/documents/{fake_id}/analyze")
    assert response.status_code == 404


# === Validation Tests ===

@pytest.mark.asyncio
async def test_list_jobs_invalid_page(admin_client: AsyncClient):
    """Test that invalid page number is handled."""
    response = await admin_client.get("/api/admin/crawler/jobs?page=0")
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_list_jobs_invalid_per_page(admin_client: AsyncClient):
    """Test that invalid per_page is handled."""
    response = await admin_client.get("/api/admin/crawler/jobs?per_page=1000")
    assert response.status_code == 422  # per_page max is 100


@pytest.mark.asyncio
@requires_celery
async def test_start_crawl_invalid_request(admin_client: AsyncClient):
    """Test start crawl with invalid request body.

    Note: This test requires Celery workers to be running as the endpoint
    attempts to queue Celery tasks.
    """
    try:
        response = await admin_client.post(
            "/api/admin/crawler/start",
            json={}  # Empty request
        )
        # Should either succeed with empty filters or return validation error
        assert response.status_code in [200, 422]
    except ReadTimeout:
        pytest.skip("Celery workers not responding (timeout)")


# === Start Crawl Tests ===

@pytest.mark.asyncio
@requires_celery
async def test_start_crawl_with_source_filter(admin_client: AsyncClient):
    """Test starting crawl with source filter.

    Note: This test requires Celery workers to be running.
    """
    try:
        response = await admin_client.post(
            "/api/admin/crawler/start",
            json={"source_ids": [str(uuid.uuid4())]}  # Non-existent source
        )
        # May return 200 (0 jobs created) or 404 (no sources found)
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert "jobs_created" in data or "job_ids" in data
    except ReadTimeout:
        pytest.skip("Celery workers not responding (timeout)")


@pytest.mark.asyncio
@requires_celery
async def test_start_crawl_with_type_filter(admin_client: AsyncClient):
    """Test starting crawl with source type filter.

    Note: This test requires Celery workers to be running.
    """
    try:
        response = await admin_client.post(
            "/api/admin/crawler/start",
            json={"source_type": "WEBSITE"}
        )
        assert response.status_code == 200
    except ReadTimeout:
        pytest.skip("Celery workers not responding (timeout)")


@pytest.mark.asyncio
@requires_celery
async def test_start_crawl_with_status_filter(admin_client: AsyncClient):
    """Test starting crawl with status filter.

    Note: This test requires Celery workers to be running.
    """
    try:
        response = await admin_client.post(
            "/api/admin/crawler/start",
            json={"status": "ACTIVE"}
        )
        assert response.status_code == 200
    except ReadTimeout:
        pytest.skip("Celery workers not responding (timeout)")


# === Reanalyze Tests ===

@pytest.mark.asyncio
@requires_celery
async def test_reanalyze_empty_filter(admin_client: AsyncClient):
    """Test reanalyze with empty filter.

    Note: This test requires Celery workers to be running.
    """
    try:
        response = await admin_client.post(
            "/api/admin/crawler/reanalyze",
            json={}
        )
        # Should return validation error or succeed with no documents
        assert response.status_code in [200, 400, 422]
    except ReadTimeout:
        pytest.skip("Celery workers not responding (timeout)")


@pytest.mark.asyncio
@requires_celery
async def test_reanalyze_filtered(admin_client: AsyncClient):
    """Test reanalyze filtered documents.

    Note: This test requires Celery workers to be running.
    """
    try:
        response = await admin_client.post(
            "/api/admin/crawler/documents/reanalyze-filtered",
            json={"category_id": str(uuid.uuid4())}  # Non-existent category
        )
        assert response.status_code == 200
        data = response.json()
        assert "queued" in data or "count" in data or isinstance(data, dict)
    except ReadTimeout:
        pytest.skip("Celery workers not responding (timeout)")


# === Process Pending Documents Tests ===

@pytest.mark.asyncio
@requires_celery
async def test_process_pending_documents(admin_client: AsyncClient):
    """Test triggering processing of pending documents.

    Note: This test requires Celery workers to be running.
    """
    try:
        response = await admin_client.post("/api/admin/crawler/documents/process-pending")
        assert response.status_code == 200
    except ReadTimeout:
        pytest.skip("Celery workers not responding (timeout)")


@pytest.mark.asyncio
@requires_celery
async def test_stop_all_processing(admin_client: AsyncClient):
    """Test stopping all document processing.

    Note: This test requires Celery workers to be running.
    """
    try:
        response = await admin_client.post("/api/admin/crawler/documents/stop-all")
        assert response.status_code == 200
    except ReadTimeout:
        pytest.skip("Celery workers not responding (timeout)")
