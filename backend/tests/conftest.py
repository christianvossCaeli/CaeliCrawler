"""Pytest configuration and fixtures."""

import asyncio
import os
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient

# For integration tests, we test against the running API
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for session scope."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create test client for integration tests against running API."""
    async with AsyncClient(base_url=API_BASE_URL, timeout=30.0) as ac:
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
