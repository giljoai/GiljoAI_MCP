"""
Pytest configuration for API endpoint tests.

Provides fixtures specific to API integration testing including:
- Async API client with authentication support
- Database session with proper isolation
- Test user management
- Authentication headers for protected endpoints
- Automatic database cleanup between tests to prevent pollution
"""

from unittest.mock import MagicMock

import pytest_asyncio
from httpx import ASGITransport
from httpx import AsyncClient as HTTPXAsyncClient
from passlib.hash import bcrypt
from sqlalchemy import text


@pytest_asyncio.fixture(scope="function", autouse=True)
async def cleanup_api_test_data(db_manager):
    """
    Cleanup fixture that truncates all tables before each API test.

    This prevents test pollution where data from one test affects another.
    Runs automatically before each test in the api/ directory.

    Uses TRUNCATE CASCADE for fast cleanup while respecting FK constraints.
    """
    # Cleanup BEFORE test runs (ensures clean slate)
    async with db_manager.get_session_async() as session:
        try:
            # Get all table names from metadata
            from src.giljo_mcp.models import Base
            table_names = [table.name for table in Base.metadata.sorted_tables]

            if table_names:
                # Disable FK checks, truncate all, re-enable
                await session.execute(text("SET session_replication_role = 'replica'"))
                for table_name in table_names:
                    await session.execute(text(f"TRUNCATE TABLE {table_name} CASCADE"))
                await session.execute(text("SET session_replication_role = 'origin'"))
                await session.commit()
        except Exception:
            # If cleanup fails, rollback and continue - test isolation may be compromised
            await session.rollback()

    yield  # Test runs here

    # No post-test cleanup needed - next test will clean up before it runs


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
    - CRITICAL: Each test gets a fresh client to prevent cookie persistence
    - CRITICAL: Cleans up database tables after each test to prevent pollution

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
    mock_config.get = MagicMock(
        side_effect=lambda key, default=None: {
            "security.auth_enabled": True,
            "security.api_keys_required": False,
        }.get(key, default)
    )

    # Set up config in state (for endpoints that use state.config)
    state.config = mock_config
    app.state.config = mock_config

    # Set up auth manager in both app.state and module-level state used by middleware
    app.state.auth = AuthManager(mock_config, db=None)
    state.auth = app.state.auth

    # Create async client with ASGI transport
    # CRITICAL FIX: Use follow_redirects=True to prevent cookie persistence issues
    # Each test gets a completely isolated client instance
    transport = ASGITransport(app=app)
    async with HTTPXAsyncClient(
        transport=transport,
        base_url="http://test",
        cookies=None,  # Explicitly no cookies to start
        follow_redirects=True,
    ) as client:
        # Clear any cookies before yielding to test
        client.cookies.clear()
        yield client
        # Clear cookies after test completes to ensure no leakage
        client.cookies.clear()

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

    # Create a unique test user for each test run (prevents fixture collisions)
    from uuid import uuid4

    from src.giljo_mcp.auth.jwt_manager import JWTManager
    from src.giljo_mcp.models import User
    from src.giljo_mcp.models.organizations import Organization
    from src.giljo_mcp.tenant import TenantManager

    async with db_manager.get_session_async() as session:
        # Create test user with unique username to avoid conflicts
        unique_suffix = uuid4().hex[:8]
        username = f"test_user_{unique_suffix}"

        # Generate valid tenant key (tk_ + 32 chars)
        tenant_key = TenantManager.generate_tenant_key()

        # Create test user with password hash (models.User uses password_hash + role)
        password_hash = bcrypt.hash("test_password")

        # Create org first (0424m: org_id is NOT NULL, tenant_key required)
        org = Organization(
            name=f"Test Org {unique_suffix}",
            slug=f"test-org-{unique_suffix}",
            tenant_key=tenant_key,  # 0424m: Required NOT NULL
            is_active=True,
        )
        session.add(org)
        await session.flush()

        user = User(
            username=username,
            email=f"test_{unique_suffix}@example.com",
            password_hash=password_hash,
            tenant_key=tenant_key,
            role="developer",
            org_id=org.id,
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


@pytest_asyncio.fixture
async def admin_user(db_manager):
    """
    Admin user for testing admin-only endpoints.

    This fixture:
    - Creates a test admin user with unique credentials
    - Generates proper tenant key for multi-tenant isolation
    - Uses bcrypt password hashing
    - Sets role to "admin" for admin-only endpoint testing
    - Each test gets a unique admin user to prevent conflicts

    Usage:
        async def test_admin_endpoint(admin_user, admin_token):
            # Use admin_token for authenticated admin requests
            headers = {"Cookie": f"access_token={admin_token}"}
            response = await api_client.get("/api/v1/admin-endpoint", headers=headers)
            assert response.status_code == 200

    Returns:
        User: Admin user model instance with role="admin"
    """
    from uuid import uuid4

    from src.giljo_mcp.models import User
    from src.giljo_mcp.models.organizations import Organization
    from src.giljo_mcp.tenant import TenantManager

    unique_id = uuid4().hex[:8]
    # Generate valid tenant key (tk_ + 32 chars) - no seed parameter needed
    tenant_key = TenantManager.generate_tenant_key()

    async with db_manager.get_session_async() as session:
        # Create org first (0424m: org_id is NOT NULL, tenant_key required)
        org = Organization(
            name=f"Admin Org {unique_id}",
            slug=f"admin-org-{unique_id}",
            tenant_key=tenant_key,  # 0424m: Required NOT NULL
            is_active=True,
        )
        session.add(org)
        await session.flush()

        user = User(
            username=f"admin_{unique_id}",
            password_hash=bcrypt.hash("admin_password"),
            email=f"admin_{unique_id}@test.com",
            tenant_key=tenant_key,
            role="admin",  # ADMIN ROLE for admin-only endpoints
            is_active=True,
            org_id=org.id,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def admin_token(admin_user):
    """
    Admin JWT token for authenticated API requests.

    This fixture:
    - Generates a valid JWT token for the admin_user
    - Token includes admin role and tenant isolation
    - Can be used in Cookie header for API authentication
    - Follows same pattern as auth_headers fixture

    Usage:
        async def test_admin_endpoint(api_client, admin_token):
            headers = {"Cookie": f"access_token={admin_token}"}
            response = await api_client.get("/api/v1/settings", headers=headers)
            assert response.status_code == 200

    Returns:
        str: JWT access token for admin user
    """
    from src.giljo_mcp.auth.jwt_manager import JWTManager

    jwt_manager = JWTManager()
    return jwt_manager.create_access_token(
        user_id=admin_user.id,
        username=admin_user.username,
        role=admin_user.role,
        tenant_key=admin_user.tenant_key,
    )


@pytest_asyncio.fixture
async def test_user(db_manager):
    """
    Create test user for depth config tests.

    Returns the User object for assertions and token generation.
    """
    from uuid import uuid4

    from src.giljo_mcp.models import User
    from src.giljo_mcp.models.organizations import Organization
    from src.giljo_mcp.tenant import TenantManager

    unique_suffix = uuid4().hex[:8]
    # Generate valid tenant key (tk_ + 32 chars)
    tenant_key = TenantManager.generate_tenant_key()

    async with db_manager.get_session_async() as session:
        # Create org first (0424m: org_id is NOT NULL, tenant_key required)
        org = Organization(
            name=f"Test Org {unique_suffix}",
            slug=f"test-org-{unique_suffix}",
            tenant_key=tenant_key,  # 0424m: Required NOT NULL
            is_active=True,
        )
        session.add(org)
        await session.flush()

        user = User(
            username=f"test_user_{unique_suffix}",
            email=f"test_{unique_suffix}@example.com",
            password_hash=bcrypt.hash("test_password"),
            tenant_key=tenant_key,
            role="developer",
            is_active=True,
            org_id=org.id,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def auth_headers_tenant_a(db_manager):
    """
    Authentication headers for tenant A (multi-tenant isolation tests).
    """
    from uuid import uuid4

    from src.giljo_mcp.auth.jwt_manager import JWTManager
    from src.giljo_mcp.models import User
    from src.giljo_mcp.models.organizations import Organization
    from src.giljo_mcp.tenant import TenantManager

    unique_suffix = uuid4().hex[:8]
    # Generate valid tenant key (tk_ + 32 chars)
    tenant_key = TenantManager.generate_tenant_key()

    async with db_manager.get_session_async() as session:
        # Create org first (0424m: org_id is NOT NULL, tenant_key required)
        org = Organization(
            name=f"Tenant A Org {unique_suffix}",
            slug=f"tenant-a-org-{unique_suffix}",
            tenant_key=tenant_key,  # 0424m: Required NOT NULL
            is_active=True,
        )
        session.add(org)
        await session.flush()

        user = User(
            username=f"tenant_a_user_{unique_suffix}",
            email=f"tenant_a_{unique_suffix}@example.com",
            password_hash=bcrypt.hash("test_password"),
            tenant_key=tenant_key,
            role="developer",
            is_active=True,
            org_id=org.id,
        )
        session.add(user)
        await session.commit()

        token = JWTManager.create_access_token(
            user_id=user.id, username=user.username, role=user.role, tenant_key=user.tenant_key
        )

        return {"Cookie": f"access_token={token}"}


@pytest_asyncio.fixture
async def auth_headers_tenant_b(db_manager):
    """
    Authentication headers for tenant B (multi-tenant isolation tests).
    """
    from uuid import uuid4

    from src.giljo_mcp.auth.jwt_manager import JWTManager
    from src.giljo_mcp.models import User
    from src.giljo_mcp.models.organizations import Organization
    from src.giljo_mcp.tenant import TenantManager

    unique_suffix = uuid4().hex[:8]
    # Generate valid tenant key (tk_ + 32 chars)
    tenant_key = TenantManager.generate_tenant_key()

    async with db_manager.get_session_async() as session:
        # Create org first (0424m: org_id is NOT NULL, tenant_key required)
        org = Organization(
            name=f"Tenant B Org {unique_suffix}",
            slug=f"tenant-b-org-{unique_suffix}",
            tenant_key=tenant_key,  # 0424m: Required NOT NULL
            is_active=True,
        )
        session.add(org)
        await session.flush()

        user = User(
            username=f"tenant_b_user_{unique_suffix}",
            email=f"tenant_b_{unique_suffix}@example.com",
            password_hash=bcrypt.hash("test_password"),
            tenant_key=tenant_key,
            role="developer",
            is_active=True,
            org_id=org.id,
        )
        session.add(user)
        await session.commit()

        token = JWTManager.create_access_token(
            user_id=user.id, username=user.username, role=user.role, tenant_key=user.tenant_key
        )

        return {"Cookie": f"access_token={token}"}


@pytest_asyncio.fixture
async def websocket_listener():
    """
    Mock WebSocket listener for testing WebSocket event emission.

    NOTE: This is a simplified mock. Real WebSocket event testing should be done
    in integration tests. For unit tests, we assume WebSocket events are emitted
    (service layer tests verify emission, not actual broadcast).

    Provides get_events() method that always returns empty list (WebSocket events
    are integration-level concerns, not unit test concerns).
    """

    class MockWebSocketListener:
        def __init__(self):
            self.events = []

        async def get_events(self, event_type: str):
            """
            Return empty list for unit tests.

            WebSocket event testing requires full app setup and is better suited
            for integration tests where the WebSocket manager is properly initialized.
            """
            return []

    return MockWebSocketListener()
