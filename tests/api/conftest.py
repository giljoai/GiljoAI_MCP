"""
Pytest configuration for API endpoint tests.

Provides fixtures specific to API integration testing including:
- Async API client with authentication support
- Database session with proper isolation
- Test user management
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient as HTTPXAsyncClient


@pytest_asyncio.fixture(scope="function")
async def api_client(db_manager):
    """
    Create AsyncClient for API testing with proper dependency overrides.

    This fixture:
    - Uses httpx.AsyncClient for async API testing
    - Mocks authentication dependencies for testing
    - Provides proper database session isolation
    - Cleans up dependency overrides after tests

    Usage:
        async def test_endpoint(api_client: AsyncClient):
            response = await api_client.get("/api/v1/endpoint")
            assert response.status_code == 200
    """
    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_db_session

    async def mock_get_db_session():
        """Provide test database session."""
        async with db_manager.get_session_async() as session:
            yield session

    # Override database session dependency
    app.dependency_overrides[get_db_session] = mock_get_db_session

    # Create async client
    async with HTTPXAsyncClient(app=app, base_url="http://test") as client:
        yield client

    # Clear overrides after test
    app.dependency_overrides.clear()
