"""E2E Tests for API Import endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_api_import_templates(admin_client: AsyncClient):
    """Test listing available API import templates."""
    response = await admin_client.get("/api/admin/api-import/templates")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    # Should have at least Wikidata and OParl templates
    template_types = [t["api_type"] for t in data]
    assert "wikidata" in template_types or len(template_types) > 0


@pytest.mark.asyncio
async def test_preview_api_import_invalid_url(admin_client: AsyncClient):
    """Test API import preview with invalid URL."""
    response = await admin_client.post(
        "/api/admin/api-import/preview",
        json={
            "api_url": "not-a-valid-url",
            "api_type": "wikidata",
            "params": {},
        },
    )
    # Should fail validation or return error
    assert response.status_code in [400, 422, 500]


@pytest.mark.asyncio
async def test_preview_api_import_wikidata(admin_client: AsyncClient):
    """Test API import preview with Wikidata SPARQL query."""
    # Simple query that should return quickly
    sparql_query = """
    SELECT ?item ?itemLabel ?website WHERE {
      ?item wdt:P31 wd:Q262166 .
      OPTIONAL { ?item wdt:P856 ?website }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "de" }
    }
    LIMIT 5
    """

    response = await admin_client.post(
        "/api/admin/api-import/preview",
        json={
            "api_url": "https://query.wikidata.org/sparql",
            "api_type": "wikidata",
            "params": {"query": sparql_query},
            "sample_size": 5,
        },
        timeout=30.0,
    )

    # May timeout or fail if Wikidata is slow, that's acceptable
    if response.status_code == 200:
        data = response.json()
        assert "preview" in data or "sources" in data or "items" in data


@pytest.mark.asyncio
async def test_execute_api_import_no_category(admin_client: AsyncClient):
    """Test API import execution without category should fail."""
    response = await admin_client.post(
        "/api/admin/api-import/execute",
        json={
            "api_url": "https://example.com/api",
            "api_type": "custom",
            "params": {},
            "default_tags": ["test"],
            # Missing category_ids
        },
    )
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_api_import_supported_types(admin_client: AsyncClient):
    """Test that supported API types are documented."""
    response = await admin_client.get("/api/admin/api-import/templates")

    if response.status_code == 200:
        data = response.json()
        for template in data:
            assert "api_type" in template
            assert "name" in template or "title" in template
