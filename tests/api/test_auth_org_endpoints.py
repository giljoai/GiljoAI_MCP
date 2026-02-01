"""
API tests for auth endpoints with organization integration (Handover 0424h).

Tests:
- POST /auth/create-first-admin accepts workspace_name parameter
- POST /auth/create-first-admin defaults workspace_name to "My Organization"
- GET /auth/me returns org_id, org_name, org_role fields
- GET /auth/me returns null org fields for users without org

Test Strategy (TDD):
1. Write tests that expect org integration (RED phase)
2. Update endpoints to pass tests (GREEN phase)
3. Verify all tests pass (REFACTOR phase)
"""

import pytest


@pytest.mark.asyncio
async def test_create_first_admin_accepts_workspace_name(api_client, db_manager):
    """
    Test that POST /auth/create-first-admin accepts workspace_name parameter.

    Expected behavior:
    - Accept workspace_name in request body
    - Create organization with provided workspace_name
    - User's org should match workspace_name

    NOTE: This test clears all users first to simulate fresh install.
    """
    # Arrange - Clear all users to simulate fresh install
    from src.giljo_mcp.models.auth import User
    from sqlalchemy import delete

    async with db_manager.get_session_async() as session:
        await session.execute(delete(User))
        await session.commit()

    request_body = {
        "username": "admin",
        "password": "SecureAdmin123!@#",
        "email": "admin@example.com",
        "full_name": "Administrator",
        "workspace_name": "Acme Corporation"
    }

    # Act
    response = await api_client.post("/api/auth/create-first-admin", json=request_body)

    # Assert
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

    data = response.json()
    assert data["username"] == "admin"
    assert data["role"] == "admin"
    assert data["tenant_key"].startswith("tk_")

    # Verify organization was created with correct name
    from sqlalchemy import select
    from src.giljo_mcp.models.organizations import Organization
    from src.giljo_mcp.models.auth import User

    async with db_manager.get_session_async() as session:
        # Get user
        user_stmt = select(User).where(User.username == "admin")
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one()

        # Verify user has org_id
        assert user.org_id is not None, "User should have org_id set"

        # Get organization
        org_stmt = select(Organization).where(Organization.id == user.org_id)
        org_result = await session.execute(org_stmt)
        org = org_result.scalar_one()

        # Verify organization name matches workspace_name
        assert org.name == "Acme Corporation", f"Expected 'Acme Corporation', got '{org.name}'"


@pytest.mark.asyncio
async def test_create_first_admin_defaults_workspace_name(api_client, db_manager):
    """
    Test that POST /auth/create-first-admin defaults workspace_name to "My Organization".

    Expected behavior:
    - If workspace_name not provided, use "My Organization" as default
    - Organization created with default name

    NOTE: This test clears all users first to simulate fresh install.
    """
    # Arrange - Clear all users to simulate fresh install
    from src.giljo_mcp.models.auth import User
    from sqlalchemy import delete

    async with db_manager.get_session_async() as session:
        await session.execute(delete(User))
        await session.commit()

    request_body = {
        "username": "admin",
        "password": "SecureAdmin123!@#",
        "email": "admin@example.com",
        "full_name": "Administrator"
        # workspace_name intentionally omitted
    }

    # Act
    response = await api_client.post("/api/auth/create-first-admin", json=request_body)

    # Assert
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

    data = response.json()
    assert data["username"] == "admin"

    # Verify organization was created with default name
    from sqlalchemy import select
    from src.giljo_mcp.models.organizations import Organization
    from src.giljo_mcp.models.auth import User

    async with db_manager.get_session_async() as session:
        # Get user
        user_stmt = select(User).where(User.username == "admin")
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one()

        # Get organization
        org_stmt = select(Organization).where(Organization.id == user.org_id)
        org_result = await session.execute(org_stmt)
        org = org_result.scalar_one()

        # Verify organization name is default
        assert org.name == "My Organization", f"Expected 'My Organization', got '{org.name}'"


@pytest.mark.asyncio
async def test_auth_me_returns_org_data(api_client, db_manager):
    """
    Test that GET /auth/me returns org_id, org_name, org_role for user with org.

    Expected behavior:
    - Return org_id field
    - Return org_name field
    - Return org_role field from membership

    NOTE: This test clears all users first to simulate fresh install.
    """
    # Arrange - Clear all users to simulate fresh install
    from src.giljo_mcp.models.auth import User
    from sqlalchemy import delete

    async with db_manager.get_session_async() as session:
        await session.execute(delete(User))
        await session.commit()

    # Create admin user with organization
    create_response = await api_client.post(
        "/api/auth/create-first-admin",
        json={
            "username": "admin",
            "password": "SecureAdmin123!@#",
            "email": "admin@example.com",
            "workspace_name": "Test Organization"
        }
    )
    assert create_response.status_code == 201

    # Token should be set in cookie from create-first-admin
    # Cookie is automatically included in subsequent requests by AsyncClient

    # Act
    response = await api_client.get("/api/auth/me")

    # Assert
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    data = response.json()
    assert "org_id" in data, "Response should include org_id field"
    assert "org_name" in data, "Response should include org_name field"
    assert "org_role" in data, "Response should include org_role field"

    assert data["org_id"] is not None, "User should have org_id"
    assert data["org_name"] == "Test Organization", f"Expected 'Test Organization', got '{data['org_name']}'"
    assert data["org_role"] == "owner", f"Expected 'owner', got '{data['org_role']}'"


@pytest.mark.asyncio
async def test_auth_me_without_org(api_client, db_manager):
    """
    Test that GET /auth/me returns null org fields for user without organization.

    Expected behavior:
    - Return org_id = null
    - Return org_name = null
    - Return org_role = null

    This test creates a user directly in the database without org association.
    """
    # Arrange - Create user without org (bypass normal registration flow)
    from src.giljo_mcp.models.auth import User
    from src.giljo_mcp.tenant import TenantManager
    from passlib.hash import bcrypt
    from datetime import datetime, timezone
    from uuid import uuid4

    tenant_key = TenantManager.generate_tenant_key("testuser")
    user_id = str(uuid4())

    async with db_manager.get_session_async() as session:
        # Create user WITHOUT org_id
        user = User(
            id=user_id,
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            password_hash=bcrypt.hash("TestPassword123!@#"),
            role="developer",
            tenant_key=tenant_key,
            org_id=None,  # Explicitly no org
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        session.add(user)
        await session.commit()

    # Generate token for login
    from src.giljo_mcp.auth.jwt_manager import JWTManager
    token = JWTManager.create_access_token(
        user_id=user_id,
        username="testuser",
        role="developer",
        tenant_key=tenant_key
    )

    # Set auth cookie
    api_client.cookies.set("access_token", token)

    # Act
    response = await api_client.get("/api/auth/me")

    # Assert
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    data = response.json()
    assert "org_id" in data, "Response should include org_id field"
    assert "org_name" in data, "Response should include org_name field"
    assert "org_role" in data, "Response should include org_role field"

    assert data["org_id"] is None, f"Expected null org_id, got {data['org_id']}"
    assert data["org_name"] is None, f"Expected null org_name, got {data['org_name']}"
    assert data["org_role"] is None, f"Expected null org_role, got {data['org_role']}"
