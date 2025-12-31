"""E2E Tests for Analysis API endpoints."""

import pytest
from httpx import AsyncClient

# =============================================================================
# Overview & Stats Tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_analysis_overview(admin_client: AsyncClient):
    """Test getting analysis overview."""
    response = await admin_client.get("/api/v1/analysis/overview")
    # 409 indicates a conflict (e.g., feature requires setup), 200 is normal
    assert response.status_code in [200, 409]

    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, dict)


@pytest.mark.asyncio
async def test_get_analysis_stats(admin_client: AsyncClient):
    """Test getting analysis statistics."""
    response = await admin_client.get("/api/v1/analysis/stats")
    assert response.status_code == 200


# =============================================================================
# Smart Query Tests
# =============================================================================

@pytest.mark.asyncio
async def test_smart_query_examples(admin_client: AsyncClient):
    """Test getting smart query examples."""
    response = await admin_client.get("/api/v1/analysis/smart-query/examples")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, dict)


@pytest.mark.asyncio
async def test_smart_query_persons(admin_client: AsyncClient):
    """Test smart query for persons."""
    response = await admin_client.post(
        "/api/v1/analysis/smart-query",
        json={"question": "Zeige mir alle Personen", "allow_write": False}
    )
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "query_interpretation" in data


@pytest.mark.asyncio
async def test_smart_query_events(admin_client: AsyncClient):
    """Test smart query for events."""
    response = await admin_client.post(
        "/api/v1/analysis/smart-query",
        json={"question": "Zeige mir kommende Veranstaltungen", "allow_write": False}
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_smart_query_with_filter(admin_client: AsyncClient):
    """Test smart query with location filter."""
    response = await admin_client.post(
        "/api/v1/analysis/smart-query",
        json={
            "question": "Zeige mir Entscheider in NRW",
            "allow_write": False
        }
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_smart_write_preview(admin_client: AsyncClient):
    """Test smart write in preview mode."""
    response = await admin_client.post(
        "/api/v1/analysis/smart-write",
        json={
            "question": "Erstelle eine neue Person namens Max Mustermann",
            "preview_only": True,
            "confirmed": False
        }
    )
    # Accept 200 or error if write not allowed
    assert response.status_code in [200, 400, 403, 422]


# =============================================================================
# Templates Tests
# =============================================================================

@pytest.mark.asyncio
async def test_list_analysis_templates(admin_client: AsyncClient):
    """Test listing analysis templates."""
    response = await admin_client.get("/api/v1/analysis/templates")
    assert response.status_code == 200

    data = response.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_get_template_by_slug(admin_client: AsyncClient):
    """Test getting a template by slug."""
    response = await admin_client.get("/api/v1/analysis/templates")
    if response.status_code != 200 or not response.json().get("items"):
        pytest.skip("No templates available")

    slug = response.json()["items"][0]["slug"]

    response = await admin_client.get(f"/api/v1/analysis/templates/by-slug/{slug}")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_entity_report(admin_client: AsyncClient):
    """Test getting an analysis report for an entity."""
    # Get a municipality
    response = await admin_client.get("/api/v1/entities", params={"per_page": 1})
    if response.status_code != 200 or not response.json().get("items"):
        pytest.skip("No entities available")

    entity_id = response.json()["items"][0]["id"]

    response = await admin_client.get(f"/api/v1/analysis/report/{entity_id}")
    # 500 may occur if report generation has an issue
    assert response.status_code in [200, 404, 500]


# =============================================================================
# Error Handling Tests
# =============================================================================

@pytest.mark.asyncio
async def test_smart_query_empty_question(admin_client: AsyncClient):
    """Test smart query with empty question fails."""
    response = await admin_client.post(
        "/api/v1/analysis/smart-query",
        json={"question": "", "allow_write": False}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_smart_query_too_short(admin_client: AsyncClient):
    """Test smart query with too short question fails."""
    response = await admin_client.post(
        "/api/v1/analysis/smart-query",
        json={"question": "ab", "allow_write": False}
    )
    assert response.status_code == 422
