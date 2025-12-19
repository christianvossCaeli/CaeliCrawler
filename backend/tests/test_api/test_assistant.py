"""E2E Tests for Assistant API endpoints."""

import pytest
from httpx import AsyncClient


# =============================================================================
# Chat Tests
# =============================================================================

@pytest.mark.asyncio
async def test_assistant_chat_basic(client: AsyncClient):
    """Test basic assistant chat."""
    response = await client.post(
        "/api/v1/assistant/chat",
        json={
            "message": "Hallo",
            "context": {"current_route": "/", "view_mode": "dashboard"},
            "mode": "read",
            "language": "de"
        }
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "response" in data


@pytest.mark.asyncio
async def test_assistant_chat_query(client: AsyncClient):
    """Test assistant chat with a query."""
    response = await client.post(
        "/api/v1/assistant/chat",
        json={
            "message": "Wie viele Gemeinden gibt es?",
            "context": {"current_route": "/entities/municipality", "view_mode": "list"},
            "mode": "read",
            "language": "de"
        }
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_assistant_chat_help(client: AsyncClient):
    """Test assistant help command."""
    response = await client.post(
        "/api/v1/assistant/chat",
        json={
            "message": "/help",
            "context": {"current_route": "/"},
            "mode": "read",
            "language": "de"
        }
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_assistant_chat_search(client: AsyncClient):
    """Test assistant search command."""
    response = await client.post(
        "/api/v1/assistant/chat",
        json={
            "message": "/search München",
            "context": {"current_route": "/"},
            "mode": "read",
            "language": "de"
        }
    )
    assert response.status_code == 200


# =============================================================================
# Commands Tests
# =============================================================================

@pytest.mark.asyncio
async def test_assistant_get_commands(client: AsyncClient):
    """Test getting available commands."""
    response = await client.get("/api/v1/assistant/commands")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, (list, dict))


# =============================================================================
# Reminders Tests
# =============================================================================

@pytest.mark.asyncio
async def test_assistant_list_reminders(client: AsyncClient):
    """Test listing reminders (requires auth)."""
    response = await client.get("/api/v1/assistant/reminders")
    # 401 indicates auth required, 200 is success
    assert response.status_code in [200, 401]


@pytest.mark.asyncio
async def test_assistant_get_due_reminders(client: AsyncClient):
    """Test getting due reminders (requires auth)."""
    response = await client.get("/api/v1/assistant/reminders/due")
    # 401 indicates auth required, 200 is success
    assert response.status_code in [200, 401]


# =============================================================================
# Insights Tests
# =============================================================================

@pytest.mark.asyncio
async def test_assistant_get_insights(client: AsyncClient):
    """Test getting assistant insights."""
    response = await client.get("/api/v1/assistant/insights")
    # 422 indicates missing parameters, 200 is success
    assert response.status_code in [200, 422]


# =============================================================================
# Actions Tests
# =============================================================================

@pytest.mark.asyncio
async def test_assistant_execute_action(client: AsyncClient):
    """Test executing an assistant action (requires auth)."""
    response = await client.post(
        "/api/v1/assistant/execute-action",
        json={
            "action": "search",
            "parameters": {"query": "test"},
            "context": {"current_route": "/"}
        }
    )
    # Accept various responses including 401 (auth required)
    assert response.status_code in [200, 400, 401, 422]


# =============================================================================
# Entity Context Tests
# =============================================================================

@pytest.mark.asyncio
async def test_assistant_with_entity_context(client: AsyncClient):
    """Test assistant with entity context."""
    # Get a municipality
    response = await client.get("/api/v1/entities", params={"per_page": 1})
    if response.status_code != 200 or not response.json().get("items"):
        pytest.skip("No entities available")

    entity = response.json()["items"][0]

    response = await client.post(
        "/api/v1/assistant/chat",
        json={
            "message": "Erzähl mir mehr über diese Gemeinde",
            "context": {
                "current_route": f"/entities/{entity['id']}",
                "current_entity_id": entity["id"],
                "current_entity_type": entity.get("entity_type_slug", "municipality"),
                "current_entity_name": entity["name"],
                "view_mode": "detail"
            },
            "mode": "read",
            "language": "de"
        }
    )
    assert response.status_code == 200


# =============================================================================
# Batch Action Tests
# =============================================================================

@pytest.mark.asyncio
async def test_assistant_batch_action(client: AsyncClient):
    """Test batch action endpoint (requires auth)."""
    response = await client.post(
        "/api/v1/assistant/batch-action",
        json={
            "action": "tag",
            "entity_ids": [],
            "parameters": {"tag": "test"}
        }
    )
    # Accept various responses including 401 (auth required)
    assert response.status_code in [200, 400, 401, 422]


# =============================================================================
# Error Handling Tests
# =============================================================================

@pytest.mark.asyncio
async def test_assistant_empty_message(client: AsyncClient):
    """Test assistant with empty message."""
    response = await client.post(
        "/api/v1/assistant/chat",
        json={
            "message": "",
            "context": {"current_route": "/"},
            "mode": "read",
            "language": "de"
        }
    )
    # Should handle gracefully
    assert response.status_code in [200, 400, 422]


@pytest.mark.asyncio
async def test_assistant_missing_context(client: AsyncClient):
    """Test assistant with missing context."""
    response = await client.post(
        "/api/v1/assistant/chat",
        json={
            "message": "test",
            "mode": "read",
            "language": "de"
        }
    )
    # Should handle gracefully
    assert response.status_code in [200, 422]
