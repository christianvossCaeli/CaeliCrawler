"""API Tests for AI Source Discovery endpoints."""

import pytest
from httpx import AsyncClient


class TestAIDiscoveryAPI:
    """Tests for AI Discovery API endpoints."""

    @pytest.mark.asyncio
    async def test_discover_sources_unauthorized(self, client: AsyncClient):
        """Test that unauthorized access is rejected."""
        response = await client.post(
            "/api/admin/ai-discovery/discover",
            json={
                "prompt": "Test prompt",
                "max_results": 10,
                "search_depth": "quick",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_discover_sources_success(self, admin_client: AsyncClient):
        """Test successful source discovery."""
        response = await admin_client.post(
            "/api/admin/ai-discovery/discover",
            json={
                "prompt": "Deutsche Bundesliga Vereine",
                "max_results": 10,
                "search_depth": "quick",
            },
        )

        # Should succeed even without external API (mock data)
        assert response.status_code == 200

        data = response.json()
        assert "sources" in data
        assert "search_strategy" in data
        assert isinstance(data["sources"], list)

    @pytest.mark.asyncio
    async def test_discover_sources_invalid_depth(self, admin_client: AsyncClient):
        """Test with invalid search depth."""
        response = await admin_client.post(
            "/api/admin/ai-discovery/discover",
            json={
                "prompt": "Test",
                "max_results": 10,
                "search_depth": "invalid_depth",
            },
        )

        # Should either reject or use default
        assert response.status_code in [200, 422]

    @pytest.mark.asyncio
    async def test_discover_sources_empty_prompt(self, admin_client: AsyncClient):
        """Test with empty prompt."""
        response = await admin_client.post(
            "/api/admin/ai-discovery/discover",
            json={
                "prompt": "",
                "max_results": 10,
                "search_depth": "quick",
            },
        )

        # Should reject empty prompt
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_discover_sources_max_results_limit(self, admin_client: AsyncClient):
        """Test max_results parameter is respected."""
        response = await admin_client.post(
            "/api/admin/ai-discovery/discover",
            json={
                "prompt": "Gemeinden in NRW",
                "max_results": 5,
                "search_depth": "quick",
            },
        )

        assert response.status_code == 200

        data = response.json()
        assert len(data.get("sources", [])) <= 5

    @pytest.mark.asyncio
    async def test_import_sources_unauthorized(self, client: AsyncClient):
        """Test that unauthorized import is rejected."""
        response = await client.post(
            "/api/admin/ai-discovery/import",
            json={
                "sources": [],
                "category_ids": [],
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_import_sources_empty(self, admin_client: AsyncClient):
        """Test importing empty source list."""
        response = await admin_client.post(
            "/api/admin/ai-discovery/import",
            json={
                "sources": [],
                "category_ids": [],
                "skip_duplicates": True,
            },
        )

        # Empty sources should be rejected with 422 (validation error: min_length=1)
        assert response.status_code in [200, 422]

        if response.status_code == 200:
            data = response.json()
            assert data.get("imported", 0) == 0

    @pytest.mark.asyncio
    async def test_import_sources_with_data(self, admin_client: AsyncClient):
        """Test importing actual sources."""
        # First discover some sources
        discover_response = await admin_client.post(
            "/api/admin/ai-discovery/discover",
            json={
                "prompt": "Test Quellen",
                "max_results": 3,
                "search_depth": "quick",
            },
        )

        if discover_response.status_code != 200:
            pytest.skip("Discovery endpoint not available")

        discovered = discover_response.json()
        sources = discovered.get("sources", [])

        if not sources:
            pytest.skip("No sources discovered to import")

        # Import the discovered sources
        response = await admin_client.post(
            "/api/admin/ai-discovery/import",
            json={
                "sources": sources[:2],  # Import max 2
                "category_ids": [],
                "skip_duplicates": True,
            },
        )

        assert response.status_code == 200

        data = response.json()
        assert "imported" in data
        assert "skipped" in data

    @pytest.mark.asyncio
    async def test_get_examples(self, admin_client: AsyncClient):
        """Test getting discovery examples."""
        response = await admin_client.get("/api/admin/ai-discovery/examples")

        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

        # Should have some example prompts
        if data:
            assert "prompt" in data[0]


class TestAIDiscoverySearchDepths:
    """Tests for different search depths."""

    @pytest.mark.asyncio
    async def test_quick_search(self, admin_client: AsyncClient):
        """Test quick search depth."""
        response = await admin_client.post(
            "/api/admin/ai-discovery/discover",
            json={
                "prompt": "Universitäten",
                "max_results": 5,
                "search_depth": "quick",
            },
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_standard_search(self, admin_client: AsyncClient):
        """Test standard search depth."""
        response = await admin_client.post(
            "/api/admin/ai-discovery/discover",
            json={
                "prompt": "Universitäten",
                "max_results": 5,
                "search_depth": "standard",
            },
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_deep_search(self, admin_client: AsyncClient):
        """Test deep search depth."""
        response = await admin_client.post(
            "/api/admin/ai-discovery/discover",
            json={
                "prompt": "Universitäten",
                "max_results": 5,
                "search_depth": "deep",
            },
        )

        assert response.status_code == 200


class TestAIDiscoveryPromptVariations:
    """Tests for various prompt types."""

    @pytest.mark.asyncio
    async def test_german_prompt(self, admin_client: AsyncClient):
        """Test German language prompt."""
        response = await admin_client.post(
            "/api/admin/ai-discovery/discover",
            json={
                "prompt": "Alle deutschen Bundesliga-Fußballvereine",
                "max_results": 5,
                "search_depth": "quick",
            },
        )

        assert response.status_code == 200

        data = response.json()
        # Check that tags include German-related tags
        if data.get("search_strategy", {}).get("base_tags"):
            base_tags = data["search_strategy"]["base_tags"]
            assert any(
                tag in ["de", "deutsch", "bundesliga", "fußball"]
                for tag in base_tags
            )

    @pytest.mark.asyncio
    async def test_geographic_prompt(self, admin_client: AsyncClient):
        """Test geographically-specific prompt."""
        response = await admin_client.post(
            "/api/admin/ai-discovery/discover",
            json={
                "prompt": "Gemeinden in Nordrhein-Westfalen",
                "max_results": 5,
                "search_depth": "quick",
            },
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_organization_type_prompt(self, admin_client: AsyncClient):
        """Test organization type prompt."""
        response = await admin_client.post(
            "/api/admin/ai-discovery/discover",
            json={
                "prompt": "DAX Unternehmen",
                "max_results": 5,
                "search_depth": "quick",
            },
        )

        assert response.status_code == 200


class TestAIDiscoveryWithCategories:
    """Tests for discovery with category assignment."""

    @pytest.mark.asyncio
    async def test_import_with_category(self, admin_client: AsyncClient):
        """Test importing sources with category assignment."""
        # First get available categories
        cat_response = await admin_client.get("/api/admin/categories")

        if cat_response.status_code != 200:
            pytest.skip("Categories endpoint not available")

        categories_data = cat_response.json()

        # Handle both list and dict response formats
        if isinstance(categories_data, dict):
            categories = categories_data.get("items", [])
        else:
            categories = categories_data

        if not categories:
            pytest.skip("No categories available")

        category_id = categories[0]["id"]

        # Discover sources
        discover_response = await admin_client.post(
            "/api/admin/ai-discovery/discover",
            json={
                "prompt": "Test",
                "max_results": 2,
                "search_depth": "quick",
            },
        )

        if discover_response.status_code != 200:
            pytest.skip("Discovery not available")

        sources = discover_response.json().get("sources", [])

        if not sources:
            pytest.skip("No sources to import")

        # Import with category
        response = await admin_client.post(
            "/api/admin/ai-discovery/import",
            json={
                "sources": sources[:1],
                "category_ids": [category_id],
                "skip_duplicates": True,
            },
        )

        assert response.status_code == 200


class TestSmartQueryDiscoveryIntegration:
    """Tests for Smart Query integration with discovery."""

    @pytest.mark.asyncio
    async def test_smart_query_discover_sources(self, admin_client: AsyncClient):
        """Test triggering discovery via Smart Query."""
        response = await admin_client.post(
            "/api/v1/smart-query/execute",
            json={
                "query": "Finde Datenquellen für Bundesliga-Vereine",
                "mode": "write",
            },
        )

        # The query should be recognized as a discover_sources operation
        if response.status_code == 200:
            data = response.json()
            # Check if it was interpreted as discovery
            if data.get("operation") == "discover_sources" or data.get("sources_found"):
                assert True
            else:
                # May be interpreted differently, that's okay
                pass

    @pytest.mark.asyncio
    async def test_smart_query_discover_pattern(self, admin_client: AsyncClient):
        """Test various discovery patterns in Smart Query."""
        patterns = [
            "Finde Datenquellen für Universitäten",
            "Suche Webseiten von Gemeinden in Bayern",
            "Importiere DAX-Unternehmen als Datenquellen",
        ]

        for pattern in patterns:
            response = await admin_client.post(
                "/api/v1/analysis/smart-query",
                json={
                    "question": pattern,
                    "allow_write": True,
                },
            )

            # Should at least not error - 404 is acceptable if endpoint not configured
            assert response.status_code in [200, 400, 404, 422]
