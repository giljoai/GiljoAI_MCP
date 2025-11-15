"""
Pytest configuration for API endpoint tests.

Provides fixtures specific to API integration testing including:
- Async API client with authentication support
- Database session with proper isolation
- Test user management
- Authentication headers for protected endpoints
"""

from unittest.mock import MagicMock

import pytest_asyncio
from httpx import ASGITransport
from httpx import AsyncClient as HTTPXAsyncClient
from passlib.hash import bcrypt
from sqlalchemy import select


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
    from api.app import app, state
    from src.giljo_mcp.auth import AuthManager
    from src.giljo_mcp.auth.dependencies import get_db_session
    from src.giljo_mcp.tenant import TenantManager

    async def mock_get_db_session():
        """Provide test database session."""
        async with db_manager.get_session_async() as session:
            yield session

    # Override database session dependency
    app.dependency_overrides[get_db_session] = mock_get_db_session

    # Ensure global state has db_manager and tenant_manager for services like TemplateService
    state.db_manager = db_manager
    app.state.db_manager = db_manager
    if state.tenant_manager is None:
        state.tenant_manager = TenantManager()

    # Set up tool_accessor for message endpoints
    from src.giljo_mcp.tools.tool_accessor import ToolAccessor
    state.tool_accessor = ToolAccessor(db_manager=db_manager, tenant_manager=state.tenant_manager)
    app.state.tool_accessor = state.tool_accessor

    # Create mock config for AuthManager and state.config
    mock_config = MagicMock()
    mock_config.jwt.secret_key = "test_secret_key"
    mock_config.jwt.algorithm = "HS256"
    mock_config.jwt.expiration_minutes = 30
    mock_config.get = MagicMock(side_effect=lambda key, default=None: {
        "security.auth_enabled": True,
        "security.api_keys_required": False,
    }.get(key, default))

    # Set up config in state (for endpoints that use state.config)
    state.config = mock_config
    app.state.config = mock_config

    # Set up auth manager in both app.state and module-level state used by middleware
    app.state.auth = AuthManager(mock_config, db=None)
    state.auth = app.state.auth

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
    import os

    from src.giljo_mcp.auth.jwt_manager import JWTManager
    from src.giljo_mcp.models import User

    # Create a unique test user for each test run (prevents fixture collisions)
    from uuid import uuid4

    async with db_manager.get_session_async() as session:
        # Create test user with unique username to avoid conflicts
        unique_suffix = uuid4().hex[:8]
        username = f"test_user_{unique_suffix}"

        # Create test user with password hash (models.User uses password_hash + role)
        password_hash = bcrypt.hash("test_password")

        user = User(
            username=username,
            email=f"test_{unique_suffix}@example.com",
            password_hash=password_hash,
            tenant_key=f"test_tenant_{unique_suffix}",
            role="developer",
        )
        session.add(user)
        await session.commit()

        # Ensure JWT secret available for test token creation
        os.environ.setdefault("JWT_SECRET", "test_secret_key")

        # Generate token for the user
        token = JWTManager.create_access_token(
            user_id=user.id,
            username=user.username,
            role="developer",
            tenant_key=user.tenant_key,
        )

        # Use Cookie header because dependencies expect JWT in cookie 'access_token'
        return {"Cookie": f"access_token={token}"}
