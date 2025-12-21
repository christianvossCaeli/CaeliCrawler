"""Tests for Smart Query API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_smart_query_read_mode(admin_client: AsyncClient):
    """Test smart query in read mode."""
    response = await admin_client.post(
        "/api/v1/analysis/smart-query",
        json={
            "question": "Zeige mir alle Gemeinden",
            "allow_write": False,
        },
    )
    assert response.status_code == 200

    data = response.json()
    # Should return either results or an interpretation
    assert "query_interpretation" in data or "results" in data or "message" in data


@pytest.mark.asyncio
async def test_smart_write_preview(admin_client: AsyncClient):
    """Test smart write in preview mode."""
    response = await admin_client.post(
        "/api/v1/analysis/smart-write",
        json={
            "question": "Erstelle eine Person Test User",
            "preview_only": True,
            "confirmed": False,
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["mode"] == "preview"
    # If AI is configured, should have interpretation
    if data.get("success"):
        assert "interpretation" in data
        assert "preview" in data


@pytest.mark.asyncio
async def test_smart_write_requires_confirmation(admin_client: AsyncClient):
    """Test that smart write requires confirmation."""
    response = await admin_client.post(
        "/api/v1/analysis/smart-write",
        json={
            "question": "Erstelle eine Person Test User",
            "preview_only": False,
            "confirmed": False,  # Not confirmed
        },
    )
    assert response.status_code == 200

    data = response.json()
    # Should fail without confirmation
    assert data["success"] is False or data["mode"] == "preview"


@pytest.mark.asyncio
async def test_smart_write_invalid_command(admin_client: AsyncClient):
    """Test smart write with invalid/non-write command."""
    response = await admin_client.post(
        "/api/v1/analysis/smart-write",
        json={
            "question": "Was ist das Wetter heute?",  # Not a write command
            "preview_only": True,
        },
    )
    assert response.status_code == 200

    data = response.json()
    # Should indicate no write operation detected
    if "success" in data:
        # Either fails or operation is 'none'
        interpretation = data.get("interpretation", {})
        if interpretation:
            assert interpretation.get("operation") in ["none", None] or not data["success"]


@pytest.mark.asyncio
async def test_smart_query_question_validation(admin_client: AsyncClient):
    """Test that question validation works."""
    # Too short
    response = await admin_client.post(
        "/api/v1/analysis/smart-query",
        json={
            "question": "ab",  # Less than 3 characters
            "allow_write": False,
        },
    )
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_smart_write_entity_type_creation_preview(admin_client: AsyncClient):
    """Test smart write preview for entity type creation."""
    response = await admin_client.post(
        "/api/v1/analysis/smart-write",
        json={
            "question": "Erstelle einen neuen Entity-Typ Solarpark fuer Solarprojekte",
            "preview_only": True,
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["mode"] == "preview"

    # If AI is configured and detects operation
    if data.get("success") and data.get("interpretation"):
        interpretation = data["interpretation"]
        # Could be create_entity_type or create_entity depending on AI interpretation
        assert interpretation.get("operation") in ["create_entity_type", "create_entity", "none"]
