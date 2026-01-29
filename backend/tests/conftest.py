"""Pytest configuration and fixtures."""

import os
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import AsyncClient

# Determine if we're running in CI mode (no external server)
CI_MODE = os.environ.get("CI", "false").lower() == "true"

# For integration tests, we test against the running API
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

# Test credentials - these should match a user in your test database
TEST_USER_EMAIL = os.environ.get("TEST_USER_EMAIL", "test@example.com")
TEST_USER_PASSWORD = os.environ.get("TEST_USER_PASSWORD", "testpassword123")


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test (requires running server)")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test (requires full stack)")


@pytest_asyncio.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient]:
    """Create test client for integration tests against running API.

    In CI mode, skips tests that require a running server.
    """
    if CI_MODE:
        pytest.skip("Skipping integration test in CI mode (no running server)")

    async with AsyncClient(base_url=API_BASE_URL, timeout=30.0) as ac:
        yield ac


@pytest_asyncio.fixture(scope="function")
async def auth_token(client: AsyncClient) -> str:
    """Get authentication token by logging in."""
    response = await client.post("/api/auth/login", json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD})
    if response.status_code != 200:
        pytest.skip(f"Could not authenticate test user: {response.status_code} - {response.text}")
    return response.json()["access_token"]


@pytest_asyncio.fixture(scope="function")
async def auth_headers(auth_token: str) -> dict[str, str]:
    """Get authentication headers."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest_asyncio.fixture(scope="function")
async def admin_client(auth_headers: dict[str, str]) -> AsyncGenerator[AsyncClient]:
    """Create authenticated test client for admin API calls.

    In CI mode, skips tests that require a running server.
    """
    if CI_MODE:
        pytest.skip("Skipping integration test in CI mode (no running server)")

    async with AsyncClient(base_url=API_BASE_URL, timeout=30.0, headers=auth_headers) as ac:
        yield ac


@pytest.fixture
def sample_entity_type_data():
    """Sample data for creating an entity type."""
    return {
        "name": "Test Entity Type",
        "name_plural": "Test Entity Types",
        "description": "A test entity type",
        "icon": "mdi-test",
        "color": "#FF0000",
        "is_primary": False,
        "supports_hierarchy": False,
    }


@pytest.fixture
def sample_entity_data():
    """Sample data for creating an entity."""
    return {
        "name": "Test Entity",
        "external_id": "TEST-001",
        "core_attributes": {"test_attr": "value"},
        "latitude": 50.0,
        "longitude": 7.0,
    }


@pytest_asyncio.fixture
async def session():
    """Create a mock async database session for unit tests."""
    mock_session = MagicMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.flush = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.refresh = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()

    yield mock_session
