"""
Smoke test fixtures with authentication support.

This module provides fixtures for smoke tests that properly initialize
the authentication middleware and provide authenticated clients.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest_asyncio
from httpx import ASGITransport

# Shared CSRF token for smoke test fixtures (double-submit cookie pattern)
_TEST_CSRF_TOKEN = secrets.token_urlsafe(32)
from httpx import AsyncClient as HTTPXAsyncClient
from sqlalchemy import select


@pytest_asyncio.fixture
async def api_client(db_manager):
    """
    Create AsyncClient for smoke tests with proper AuthManager setup.

    This fixture:
    - Uses httpx.AsyncClient for async API testing
    - Sets up AuthManager in app state (required by middleware)
    - Provides proper database session isolation
    - Cleans up dependency overrides after tests
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

    # Ensure global state has db_manager and tenant_manager
    state.db_manager = db_manager
    app.state.db_manager = db_manager
    if state.tenant_manager is None:
        state.tenant_manager = TenantManager()

    # Register smoke test tenant keys (bypasses format validation via public API)
    TenantManager.register_test_tenant("smoke-tenant")
    TenantManager.register_test_tenant("tenant-a")
    TenantManager.register_test_tenant("tenant-b")

    # Create mock config for AuthManager
    mock_config = MagicMock()
    mock_config.jwt.secret_key = "test_secret_key"
    mock_config.jwt.algorithm = "HS256"
    mock_config.jwt.expiration_minutes = 30

    # Set up auth manager in both app.state and module-level state used by middleware
    # This is CRITICAL - without this, auth_manager will be None and tests will fail
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


@pytest_asyncio.fixture
async def authenticated_client(api_client, db_manager):
    """
    Create API client with authentication configured.

    This fixture:
    - Creates or retrieves a test user from the database
    - Generates a valid JWT token for the user
    - Sets up default headers with the JWT token
    - Returns AsyncClient ready for authenticated requests

    Usage:
        @pytest.mark.asyncio
        async def test_something(authenticated_client):
            client, user = authenticated_client
            response = await client.post("/api/v1/products/", json={...})
            assert response.status_code == 200
    """
    from src.giljo_mcp.auth.jwt_manager import JWTManager
    from src.giljo_mcp.models import User

    # Check if user already exists (to avoid duplicate key errors)
    async with db_manager.get_session_async() as session:
        stmt = select(User).where(User.username == "smoke_test_user")
        result = await session.execute(stmt)
        test_user = result.scalar_one_or_none()

        if not test_user:
            # Create test user
            test_user = User(
                id=str(uuid4()),
                username="smoke_test_user",
                email="smoke@example.com",
                tenant_key="smoke-tenant",
                is_active=True,
                role="admin",  # Admin role for full access in smoke tests
                created_at=datetime.now(timezone.utc),
                password_hash="hashed_password",
            )
            session.add(test_user)
            await session.commit()
            await session.refresh(test_user)
        else:
            # Update existing user role to admin
            test_user.role = "admin"
            await session.commit()
            await session.refresh(test_user)

    # Generate JWT token for the user using the auth manager's JWT manager
    token = JWTManager.create_access_token(
        user_id=test_user.id,
        username=test_user.username,
        role=test_user.role,
        tenant_key=test_user.tenant_key,
    )

    # Set default headers with JWT token in Cookie (matches production auth flow)
    api_client.cookies.set("access_token", token)
    # Add CSRF token for double-submit cookie pattern (0765f)
    api_client.cookies.set("csrf_token", _TEST_CSRF_TOKEN)
    api_client.headers["X-CSRF-Token"] = _TEST_CSRF_TOKEN

    yield api_client, test_user

    # Cleanup cookies
    api_client.cookies.clear()


@pytest_asyncio.fixture
async def smoke_test_tenant_key():
    """Provide consistent tenant key for smoke tests."""
    return "smoke-tenant"
