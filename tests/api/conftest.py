"""
Pytest configuration for API endpoint tests.

Provides fixtures specific to API integration testing including:
- Async API client with authentication support
- Database session with proper isolation
- Test user management
- Authentication headers for protected endpoints
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient as HTTPXAsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import MagicMock
from passlib.hash import bcrypt


@pytest_asyncio.fixture(scope="function")
async def api_client(db_manager):
    """
    Create AsyncClient for API testing with proper dependency overrides and auth setup.

    This fixture:
    - Uses httpx.AsyncClient for async API testing
    - Mocks authentication dependencies for testing
    - Provides proper database session isolation
    - Sets up AuthManager in app state
    - Cleans up dependency overrides after tests

    Usage:
        async def test_endpoint(api_client: AsyncClient):
            response = await api_client.get("/api/v1/endpoint")
            assert response.status_code == 200
    """
    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_db_session
    from src.giljo_mcp.auth import AuthManager

    async def mock_get_db_session():
        """Provide test database session."""
        async with db_manager.get_session_async() as session:
            yield session

    # Override database session dependency
    app.dependency_overrides[get_db_session] = mock_get_db_session

    # Create mock config for AuthManager
    mock_config = MagicMock()
    mock_config.jwt.secret_key = "test_secret_key"
    mock_config.jwt.algorithm = "HS256"
    mock_config.jwt.expiration_minutes = 30

    # Set up auth manager in app state
    app.state.auth = AuthManager(mock_config, db=None)

    # Create async client with ASGI transport
    transport = ASGITransport(app=app)
    async with HTTPXAsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # Clear overrides after test
    app.dependency_overrides.clear()
    if hasattr(app.state, "auth"):
        del app.state.auth


@pytest_asyncio.fixture(scope="function")
async def auth_headers(db_manager, api_client) -> dict:
    """
    Create authentication headers for API tests.

    This fixture:
    - Creates a test user in the database
    - Generates a valid JWT token
    - Returns Authorization header dict for authenticated requests

    Usage:
        async def test_endpoint(api_client: AsyncClient, auth_headers: dict):
            response = await api_client.post(
                "/api/download/generate-token",
                headers=auth_headers,
                json={"content_type": "slash_commands"}
            )
            assert response.status_code == 201

    Returns:
        dict: {"Authorization": "Bearer <token>"}
    """
    from src.giljo_mcp.models import User
    from src.giljo_mcp.auth.jwt_manager import JWTManager

    # Create a test user if it doesn't exist
    async with db_manager.get_session_async() as session:
        # Check if test user exists
        stmt = select(User).where(User.username == "test_user")
        result = await session.execute(stmt)
        user = result.scalars().first()

        if not user:
            # Create test user with hashed password
            hashed_password = bcrypt.hash("test_password")

            user = User(
                username="test_user",
                email="test@example.com",
                hashed_password=hashed_password,
                tenant_key="test_tenant_key",
                is_admin=False,
            )
            session.add(user)
            await session.commit()

        # Generate token for the user
        token = JWTManager.create_access_token(
            user_id=user.id,
            username=user.username,
            role="user",
            tenant_key=user.tenant_key,
        )

        return {"Authorization": f"Bearer {token}"}
