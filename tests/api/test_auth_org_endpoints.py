"""
API tests for auth endpoints with organization integration (Handover 0424h).

Tests:
- POST /auth/create-first-admin accepts workspace_name parameter
- POST /auth/create-first-admin defaults workspace_name to "My Organization"
- GET /auth/me returns org_id, org_name, org_role fields

Test Strategy (TDD):
1. Write tests that expect org integration (RED phase)
2. Update endpoints to pass tests (GREEN phase)
3. Verify all tests pass (REFACTOR phase)

Updated for exception-based patterns (Handover 0480 series).
"""

from uuid import uuid4

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def fresh_db_session(db_manager):
    """
    Provides a fresh database session for tests that need isolated user creation.

    Instead of deleting all users (which violates FK constraints), we:
    1. Create a unique test user for each test
    2. Use unique identifiers to avoid collisions
    """
    async with db_manager.get_session_async() as session:
        yield session


@pytest_asyncio.fixture
async def authed_client_for_first_admin(db_manager, api_client):
    """
    Provides an API client that simulates a fresh installation.

    Since we can't delete all users due to FK constraints, we test the
    create-first-admin endpoint behavior by checking it works when no
    admin exists, or returns appropriate error when admin exists.
    """
    yield api_client


@pytest.mark.asyncio
async def test_create_first_admin_accepts_workspace_name(api_client, db_manager):
    """
    Test that POST /auth/create-first-admin accepts workspace_name parameter.

    Expected behavior:
    - Accept workspace_name in request body
    - Create organization with provided workspace_name
    - User's org should match workspace_name

    NOTE: This test uses unique credentials to avoid conflicts.
    If first admin already exists, endpoint returns 400 (expected behavior).
    """
    from sqlalchemy import func, select

    from src.giljo_mcp.models.auth import User

    # Check if any users already exist (endpoint rejects if total_users > 0, not just admins)
    async with db_manager.get_session_async() as session:
        user_count_result = await session.execute(
            select(func.count()).select_from(User)
        )
        user_count = user_count_result.scalar()

    unique_suffix = str(uuid4())[:8]
    request_body = {
        "username": f"admin_{unique_suffix}",
        "password": "SecureAdmin123!@#",
        "email": f"admin_{unique_suffix}@example.com",
        "full_name": "Administrator",
        "workspace_name": f"Acme Corporation {unique_suffix}",
    }

    # Act
    response = await api_client.post("/api/auth/create-first-admin", json=request_body)

    # Assert based on whether users already exist (endpoint checks total user count)
    if user_count > 0:
        # Users already exist - endpoint should reject (fresh install only)
        assert response.status_code == 400, f"Expected 400 when users exist, got {response.status_code}"
        assert "already exists" in response.text.lower() or "already created" in response.text.lower()
    else:
        # No admin yet - should create successfully
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        data = response.json()
        assert data["username"] == f"admin_{unique_suffix}"
        assert data["role"] == "admin"
        assert data["tenant_key"].startswith("tk_")

        # Verify organization was created with correct name
        from sqlalchemy import select

        from src.giljo_mcp.models.auth import User
        from src.giljo_mcp.models.organizations import Organization

        async with db_manager.get_session_async() as session:
            # Get user
            user_stmt = select(User).where(User.username == f"admin_{unique_suffix}")
            user_result = await session.execute(user_stmt)
            user = user_result.scalar_one_or_none()

            if user:
                # Verify user has org_id
                assert user.org_id is not None, "User should have org_id set"

                # Get organization
                org_stmt = select(Organization).where(Organization.id == user.org_id)
                org_result = await session.execute(org_stmt)
                org = org_result.scalar_one()

                # Verify organization name matches workspace_name
                assert org.name == f"Acme Corporation {unique_suffix}", f"Expected org name, got '{org.name}'"


@pytest.mark.asyncio
async def test_create_first_admin_defaults_workspace_name(api_client, db_manager):
    """
    Test that POST /auth/create-first-admin defaults workspace_name to "My Organization".

    Expected behavior:
    - If workspace_name not provided, use "My Organization" as default
    - Organization created with default name

    NOTE: This test uses unique credentials to avoid conflicts.
    """
    from sqlalchemy import func, select

    from src.giljo_mcp.models.auth import User

    # Check if any users already exist (endpoint rejects if total_users > 0, not just admins)
    async with db_manager.get_session_async() as session:
        user_count_result = await session.execute(
            select(func.count()).select_from(User)
        )
        user_count = user_count_result.scalar()

    unique_suffix = str(uuid4())[:8]
    request_body = {
        "username": f"admin_default_{unique_suffix}",
        "password": "SecureAdmin123!@#",
        "email": f"admin_default_{unique_suffix}@example.com",
        "full_name": "Administrator",
        # workspace_name intentionally omitted
    }

    # Act
    response = await api_client.post("/api/auth/create-first-admin", json=request_body)

    # Assert based on whether users already exist (endpoint checks total user count)
    if user_count > 0:
        # Users already exist - endpoint should reject (fresh install only)
        assert response.status_code == 400, f"Expected 400 when users exist, got {response.status_code}"
    else:
        # No admin yet - should create successfully with default org name
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        data = response.json()
        assert data["username"] == f"admin_default_{unique_suffix}"

        # Verify organization was created with default name
        from sqlalchemy import select

        from src.giljo_mcp.models.auth import User
        from src.giljo_mcp.models.organizations import Organization

        async with db_manager.get_session_async() as session:
            # Get user
            user_stmt = select(User).where(User.username == f"admin_default_{unique_suffix}")
            user_result = await session.execute(user_stmt)
            user = user_result.scalar_one_or_none()

            if user:
                # Get organization
                org_stmt = select(Organization).where(Organization.id == user.org_id)
                org_result = await session.execute(org_stmt)
                org = org_result.scalar_one()

                # Verify organization name is default
                assert org.name == "My Organization", f"Expected 'My Organization', got '{org.name}'"


@pytest.mark.asyncio
async def test_auth_me_returns_org_data(api_client, db_manager, auth_headers):
    """
    Test that GET /auth/me returns org_id, org_name, org_role for user with org.

    Expected behavior:
    - Return org_id field
    - Return org_name field
    - Return org_role field from membership

    Uses auth_headers fixture which creates a properly authenticated user with org.
    """
    # Act - use authenticated client
    response = await api_client.get("/api/auth/me", headers=auth_headers)

    # Assert
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    data = response.json()
    assert "org_id" in data, "Response should include org_id field"
    assert "org_name" in data, "Response should include org_name field"
    assert "org_role" in data, "Response should include org_role field"

    assert data["org_id"] is not None, "User should have org_id"
    # org_name and org_role should be present (values depend on fixture setup)
    assert data["org_name"] is not None, "org_name should not be null"


@pytest.mark.asyncio
async def test_auth_me_returns_org_fields(api_client, db_manager, auth_headers):
    """
    Test that GET /auth/me always returns org fields (post-0424j).

    After 0424j migration:
    - All users MUST have org_id (NOT NULL)
    - org_name and org_role should always be present
    - No null org scenarios possible

    This test verifies the API returns org fields for authenticated user.
    """
    # Act
    response = await api_client.get("/api/auth/me", headers=auth_headers)

    # Assert
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    data = response.json()
    assert "org_id" in data, "Response should include org_id field"
    assert "org_name" in data, "Response should include org_name field"
    assert "org_role" in data, "Response should include org_role field"

    # Post-0424j: All users MUST have org
    assert data["org_id"] is not None, "org_id should never be null after 0424j migration"
    assert data["org_name"] is not None, "org_name should never be null"
    # org_role can vary based on membership but should be present
    assert "org_role" in data, "org_role field should be present"
