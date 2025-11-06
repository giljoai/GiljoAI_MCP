"""
Pytest fixtures for Handover 0073 API integration tests.

Provides:
- Test users with authentication
- HTTP client with auth headers
- Multi-tenant test setup
"""

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.app import create_app
from src.giljo_mcp.models import User
from tests.fixtures.auth_fixtures import UserFactory


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession) -> User:
    """Create primary test user."""
    return await UserFactory.create_developer(db_session, username="testuser", tenant_key="test_tenant_1")


@pytest_asyncio.fixture(scope="function")
async def test_user_2(db_session: AsyncSession) -> User:
    """Create secondary test user for multi-tenant tests."""
    return await UserFactory.create_developer(db_session, username="testuser2", tenant_key="test_tenant_2")


@pytest_asyncio.fixture(scope="function")
async def auth_headers(test_user: User) -> dict:
    """Generate auth headers for primary test user."""
    from src.giljo_mcp.auth.jwt_manager import JWTManager

    jwt_manager = JWTManager()
    token = jwt_manager.create_access_token({"sub": test_user.username, "tenant_key": test_user.tenant_key})

    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture(scope="function")
async def auth_headers_user_2(test_user_2: User) -> dict:
    """Generate auth headers for secondary test user."""
    from src.giljo_mcp.auth.jwt_manager import JWTManager

    jwt_manager = JWTManager()
    token = jwt_manager.create_access_token({"sub": test_user_2.username, "tenant_key": test_user_2.tenant_key})

    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture(scope="function")
async def client(db_manager) -> AsyncClient:
    """Create async HTTP client for API testing."""
    app = create_app()

    # Set database manager in app state
    app.state.api_state.db_manager = db_manager

    async with AsyncClient(app=app, base_url="http://testserver") as ac:
        yield ac
