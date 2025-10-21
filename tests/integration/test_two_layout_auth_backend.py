"""
Backend integration tests for Two-Layout Authentication Pattern.

Tests the simplified /api/auth/me endpoint that no longer checks setup mode.
The Two-Layout Pattern eliminates the need for setup mode complexity because:
- Auth routes are isolated in AuthLayout (no user loading during auth flow)
- App routes always require authentication and valid user data
- /api/auth/me simply returns current user or 401 Unauthorized

Related to: handovers/0024_HANDOVER_20251016_TWO_LAYOUT_AUTH_PATTERN.md
Phase 3: Simplify Backend
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from passlib.hash import bcrypt

from src.giljo_mcp.models import User, SetupState
from datetime import datetime, timezone


@pytest.mark.asyncio
async def test_auth_me_returns_user_when_authenticated(test_client: AsyncClient, authenticated_headers: dict, test_user: User):
    """
    Test /api/auth/me returns user data when authenticated.

    Two-Layout Pattern: Auth routes isolated, app routes always require valid user.
    No setup mode check - just return user data if authenticated.
    """
    response = await test_client.get("/api/auth/me", cookies=authenticated_headers)

    assert response.status_code == 200
    data = response.json()

    # Verify user profile data returned
    assert data["username"] == test_user.username
    assert data["role"] == test_user.role
    assert data["tenant_key"] == test_user.tenant_key
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data

    # CRITICAL: Verify NO setup mode response
    assert "setup_mode" not in data
    assert "requires_setup" not in data
    assert "message" not in data or "setup" not in data["message"].lower()


@pytest.mark.asyncio
async def test_auth_me_returns_401_when_not_authenticated(test_client: AsyncClient):
    """
    Test /api/auth/me returns 401 when not authenticated.

    Two-Layout Pattern: No setup mode complexity.
    If not authenticated, return 401 regardless of setup state.
    """
    response = await test_client.get("/api/auth/me")

    assert response.status_code == 401
    data = response.json()

    # Verify clean 401 response
    assert "detail" in data
    assert "Not authenticated" in data["detail"]

    # CRITICAL: Verify NO setup mode response even when unauthenticated
    assert "setup_mode" not in data
    assert "requires_setup" not in data


@pytest.mark.asyncio
async def test_auth_me_no_setup_mode_response_even_if_setup_active(test_client: AsyncClient, authenticated_headers: dict, test_user: User):
    """
    Test /api/auth/me does NOT return setup mode response even if setup mode is active.

    This is the CORE of Phase 3: Remove setup mode check from /api/auth/me.
    The endpoint should ignore setup mode state and just return user data.
    """
    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_db_session

    # Get database session to create setup state
    db_session_gen = app.dependency_overrides[get_db_session]
    async for session in db_session_gen():
        # Create SetupState (simulating setup mode)
        setup_state = SetupState(
            tenant_key=test_user.tenant_key,
            database_initialized=True,
            database_initialized_at=datetime.now(timezone.utc),  # Required when database_initialized=True
            first_admin_created=False,  # No admin created yet
            setup_version="3.0.0"
        )
        session.add(setup_state)
        await session.commit()
        break  # Exit after first iteration

    # Call /api/auth/me as authenticated user
    response = await test_client.get("/api/auth/me", cookies=authenticated_headers)

    assert response.status_code == 200
    data = response.json()

    # CRITICAL: Should return user data, NOT setup mode response
    assert data["username"] == test_user.username
    assert data["role"] == test_user.role

    # CRITICAL: Should NOT return setup mode fields
    assert "setup_mode" not in data
    assert "requires_setup" not in data


@pytest.mark.asyncio
async def test_auth_me_consistent_response_regardless_of_setup_state(test_client: AsyncClient, test_user: User):
    """
    Test /api/auth/me returns consistent response regardless of setup state.

    Verifies that the endpoint behavior is the same whether:
    - No SetupState exists
    - SetupState exists with first_admin_created=False
    - SetupState exists with first_admin_created=True
    """
    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_db_session

    # Test 1: No SetupState (fresh install)
    response1 = await test_client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "testpassword123"}
    )
    assert response1.status_code == 200
    cookies1 = response1.cookies

    me_response1 = await test_client.get("/api/auth/me", cookies=cookies1)
    assert me_response1.status_code == 200
    assert "username" in me_response1.json()
    assert "setup_mode" not in me_response1.json()

    # Test 2: SetupState with first_admin_created=False
    db_session_gen = app.dependency_overrides[get_db_session]
    async for session in db_session_gen():
        setup_state = SetupState(
            tenant_key=test_user.tenant_key,
            database_initialized=True,
            database_initialized_at=datetime.now(timezone.utc),  # Required
            first_admin_created=False,
            setup_version="3.0.0"
        )
        session.add(setup_state)
        await session.commit()
        break

    me_response2 = await test_client.get("/api/auth/me", cookies=cookies1)
    assert me_response2.status_code == 200
    assert "username" in me_response2.json()
    assert "setup_mode" not in me_response2.json()

    # Test 3: SetupState with first_admin_created=True
    db_session_gen = app.dependency_overrides[get_db_session]
    async for session in db_session_gen():
        # Update setup state
        from sqlalchemy import select
        stmt = select(SetupState).where(SetupState.tenant_key == test_user.tenant_key)
        result = await session.execute(stmt)
        setup_state = result.scalar_one_or_none()
        if setup_state:
            setup_state.first_admin_created = True
            await session.commit()
        break

    me_response3 = await test_client.get("/api/auth/me", cookies=cookies1)
    assert me_response3.status_code == 200
    assert "username" in me_response3.json()
    assert "setup_mode" not in me_response3.json()

    # All three responses should be identical (except timestamps)
    assert me_response1.json()["username"] == me_response2.json()["username"]
    assert me_response2.json()["username"] == me_response3.json()["username"]


@pytest.mark.asyncio
async def test_auth_me_with_api_key_authentication(test_client: AsyncClient, test_user: User):
    """
    Test /api/auth/me works with API key authentication.

    Verifies that API key authentication also returns user data without setup mode complexity.
    """
    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_db_session
    from src.giljo_mcp.api_key_utils import generate_api_key, hash_api_key, get_key_prefix
    from src.giljo_mcp.models import APIKey

    # Create API key
    api_key_plaintext = generate_api_key()
    key_hash = hash_api_key(api_key_plaintext)
    key_prefix = get_key_prefix(api_key_plaintext)

    db_session_gen = app.dependency_overrides[get_db_session]
    async for session in db_session_gen():
        api_key_record = APIKey(
            user_id=test_user.id,
            tenant_key=test_user.tenant_key,
            name="Test API Key",
            key_hash=key_hash,
            key_prefix=key_prefix,
            permissions=["*"],
            is_active=True
        )
        session.add(api_key_record)
        await session.commit()
        break

    # Use API key to access /me endpoint
    response = await test_client.get(
        "/api/auth/me",
        headers={"X-API-Key": api_key_plaintext}
    )

    assert response.status_code == 200
    data = response.json()

    # Verify user data returned
    assert data["username"] == test_user.username
    assert data["role"] == test_user.role

    # CRITICAL: No setup mode response
    assert "setup_mode" not in data
    assert "requires_setup" not in data


@pytest.mark.asyncio
async def test_auth_me_multi_tenant_isolation(test_client: AsyncClient, test_user: User):
    """
    Test /api/auth/me respects multi-tenant isolation.

    Verifies that users can only access their own tenant's data.
    """
    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_db_session

    # Create user in different tenant
    db_session_gen = app.dependency_overrides[get_db_session]
    async for session in db_session_gen():
        other_tenant_user = User(
            username="othertenant",
            password_hash=bcrypt.hash("password123"),
            email="other@example.com",
            role="developer",
            tenant_key="other_tenant",  # Different tenant
            is_active=True
        )
        session.add(other_tenant_user)
        await session.commit()
        await session.refresh(other_tenant_user)
        break

    # Login as test_user (default tenant)
    response = await test_client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "testpassword123"}
    )
    assert response.status_code == 200
    cookies = response.cookies

    # Get user profile
    me_response = await test_client.get("/api/auth/me", cookies=cookies)
    assert me_response.status_code == 200
    data = me_response.json()

    # Should return test_user (default tenant), not other_tenant_user
    assert data["username"] == "testuser"
    assert data["tenant_key"] == "default"
    assert data["tenant_key"] != "other_tenant"


# Fixtures (reuse from test_auth_endpoints.py but included for clarity)

@pytest_asyncio.fixture
async def test_client():
    """Create async HTTP client for testing auth endpoints."""
    from httpx import AsyncClient, ASGITransport
    from api.app import app
    from src.giljo_mcp.database import DatabaseManager
    from src.giljo_mcp.auth.dependencies import get_db_session
    from tests.helpers.test_db_helper import PostgreSQLTestHelper
    from sqlalchemy import text

    # Ensure test database exists
    await PostgreSQLTestHelper.ensure_test_database_exists()

    # Create test database manager
    db_url = PostgreSQLTestHelper.get_test_db_url()
    test_db_manager = DatabaseManager(db_url, is_async=True)

    # Create tables
    await PostgreSQLTestHelper.create_test_tables(test_db_manager)

    # Clean all test data
    async with test_db_manager.get_session_async() as session:
        await session.execute(text("TRUNCATE TABLE setup_state, api_keys, users RESTART IDENTITY CASCADE"))
        await session.commit()

    # Override get_db_session dependency
    async def override_get_db_session():
        async with test_db_manager.get_session_async() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    # Create async client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver:8000") as ac:
        yield ac

    # Cleanup
    app.dependency_overrides.clear()
    await test_db_manager.close_async()


@pytest_asyncio.fixture
async def test_user(test_client):
    """Create a test user."""
    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_db_session

    db_session_gen = app.dependency_overrides[get_db_session]
    async for session in db_session_gen():
        user = User(
            username="testuser",
            password_hash=bcrypt.hash("testpassword123"),
            email="test@example.com",
            role="developer",
            tenant_key="default",
            is_active=True
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def authenticated_headers(test_client: AsyncClient, test_user: User):
    """Get authenticated JWT cookie."""
    response = await test_client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "testpassword123"}
    )
    assert response.status_code == 200
    return response.cookies
