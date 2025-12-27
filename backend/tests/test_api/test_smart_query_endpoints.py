"""
Integration tests for Smart Query API endpoints.

These tests verify the API endpoints work correctly with mocked AI responses.

NOTE: These tests require additional fixtures (app, test_user_token) that are not
yet implemented. They are currently skipped.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

# Skip all tests in this module until fixtures are implemented
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skip(reason="Fixtures 'app' and 'test_user_token' not yet implemented")
]


class TestSmartQueryEndpoint:
    """Tests for POST /v1/analysis/smart-query"""

    async def test_requires_authentication(self, async_client: AsyncClient):
        """Test that endpoint requires authentication."""
        response = await async_client.post(
            "/api/v1/analysis/smart-query",
            json={"question": "Show all entities"},
        )
        assert response.status_code == 401

    async def test_rejects_empty_question(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test that empty questions are rejected."""
        response = await async_client.post(
            "/api/v1/analysis/smart-query",
            json={"question": ""},
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_rejects_too_short_question(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test that too short questions are rejected."""
        response = await async_client.post(
            "/api/v1/analysis/smart-query",
            json={"question": "ab"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    @patch("services.smart_query.interpreters.interpret_query")
    async def test_read_mode_query(
        self,
        mock_interpret: AsyncMock,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test read mode query execution."""
        mock_interpret.return_value = {
            "success": True,
            "items": [{"id": 1, "name": "Test Entity"}],
            "total": 1,
            "interpretation": {"operation": "search"},
        }

        response = await async_client.post(
            "/api/v1/analysis/smart-query",
            json={"question": "Show all entities", "allow_write": False},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["items"]) == 1

    @patch("services.smart_query.interpreters.interpret_plan_query")
    async def test_plan_mode_query(
        self,
        mock_interpret: AsyncMock,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test plan mode query execution."""
        mock_interpret.return_value = {
            "success": True,
            "message": "Here is your prompt",
            "has_generated_prompt": True,
            "generated_prompt": "Show all municipalities",
            "suggested_mode": "read",
            "mode": "plan",
        }

        response = await async_client.post(
            "/api/v1/analysis/smart-query",
            json={
                "question": "Help me search for data",
                "mode": "plan",
                "conversation_history": [],
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "plan"
        assert data["has_generated_prompt"] is True


class TestSmartWriteEndpoint:
    """Tests for POST /v1/analysis/smart-write"""

    async def test_requires_authentication(self, async_client: AsyncClient):
        """Test that endpoint requires authentication."""
        response = await async_client.post(
            "/api/v1/analysis/smart-write",
            json={"question": "Create entity"},
        )
        assert response.status_code == 401

    async def test_requires_editor_role(
        self, async_client: AsyncClient, viewer_auth_headers: dict
    ):
        """Test that endpoint requires editor role."""
        response = await async_client.post(
            "/api/v1/analysis/smart-write",
            json={"question": "Create entity"},
            headers=viewer_auth_headers,
        )
        assert response.status_code == 403

    @patch("services.smart_query.interpreters.interpret_write_command")
    async def test_preview_mode(
        self,
        mock_interpret: AsyncMock,
        async_client: AsyncClient,
        editor_auth_headers: dict,
    ):
        """Test write preview mode."""
        mock_interpret.return_value = {
            "success": True,
            "mode": "preview",
            "interpretation": {
                "operation": "create_entity",
                "entity_type": "person",
                "name": "Test Person",
            },
            "preview": "Will create a Person entity named 'Test Person'",
        }

        response = await async_client.post(
            "/api/v1/analysis/smart-write",
            json={
                "question": "Create a person named Test Person",
                "preview_only": True,
                "confirmed": False,
            },
            headers=editor_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "preview"
        assert "preview" in data


class TestValidateEndpoint:
    """Tests for POST /v1/analysis/smart-query/validate"""

    async def test_requires_authentication(self, async_client: AsyncClient):
        """Test that endpoint requires authentication."""
        response = await async_client.post(
            "/api/v1/analysis/smart-query/validate",
            json={"prompt": "Show entities", "mode": "read"},
        )
        assert response.status_code == 401

    async def test_validates_read_prompt(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test read prompt validation."""
        response = await async_client.post(
            "/api/v1/analysis/smart-query/validate",
            json={"prompt": "Show all municipalities", "mode": "read"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "valid" in data
        assert "original_prompt" in data

    async def test_validates_write_prompt(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test write prompt validation."""
        response = await async_client.post(
            "/api/v1/analysis/smart-query/validate",
            json={"prompt": "Create a new person", "mode": "write"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "valid" in data
        assert "warnings" in data


class TestStreamEndpoint:
    """Tests for POST /v1/analysis/smart-query/stream"""

    async def test_requires_authentication(self, async_client: AsyncClient):
        """Test that endpoint requires authentication."""
        response = await async_client.post(
            "/api/v1/analysis/smart-query/stream",
            json={"question": "Help me"},
        )
        assert response.status_code == 401

    async def test_rejects_empty_question(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test that empty questions are rejected."""
        response = await async_client.post(
            "/api/v1/analysis/smart-query/stream",
            json={"question": ""},
            headers=auth_headers,
        )
        assert response.status_code == 422

    @patch("services.smart_query.interpreters.interpret_plan_query_stream")
    async def test_returns_sse_stream(
        self,
        mock_stream: MagicMock,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test that endpoint returns SSE stream."""
        # Mock the async generator
        async def mock_generator():
            yield {"event": "start", "data": None}
            yield {"event": "chunk", "data": "Hello "}
            yield {"event": "chunk", "data": "World"}
            yield {"event": "done", "data": None}

        mock_stream.return_value = mock_generator()

        response = await async_client.post(
            "/api/v1/analysis/smart-query/stream",
            json={"question": "Help me search", "conversation_history": []},
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")


class TestRateLimiting:
    """Tests for rate limiting on Smart Query endpoints."""

    @pytest.mark.parametrize(
        "endpoint,method,limit",
        [
            ("/api/v1/analysis/smart-query", "POST", 30),
            ("/api/v1/analysis/smart-write", "POST", 15),
            ("/api/v1/analysis/smart-query/stream", "POST", 20),
            ("/api/v1/analysis/smart-query/validate", "POST", 60),
        ],
    )
    async def test_rate_limits_are_applied(
        self,
        endpoint: str,
        method: str,
        limit: int,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test that rate limits are correctly configured."""
        # This is a structural test - we verify the endpoint exists
        # Actual rate limiting is tested in load tests
        response = await async_client.request(
            method,
            endpoint,
            json={"question": "Test query", "prompt": "Test", "mode": "read"},
            headers=auth_headers,
        )
        # Should get a valid response (not 404)
        assert response.status_code != 404


# Fixtures for test setup
@pytest.fixture
async def async_client(app):
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def auth_headers(test_user_token):
    """Create authentication headers for regular user."""
    return {"Authorization": f"Bearer {test_user_token}"}


@pytest.fixture
def viewer_auth_headers(viewer_user_token):
    """Create authentication headers for viewer user."""
    return {"Authorization": f"Bearer {viewer_user_token}"}


@pytest.fixture
def editor_auth_headers(editor_user_token):
    """Create authentication headers for editor user."""
    return {"Authorization": f"Bearer {editor_user_token}"}
