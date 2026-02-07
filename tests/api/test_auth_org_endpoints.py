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
    from sqlalchemy import delete

    from src.giljo_mcp.models.auth import User

    async with db_manager.get_session_async() as session:
        await session.execute(delete(User))
        await session.commit()

    request_body = {
        "username": "admin",
        "password": "SecureAdmin123!@#",
        "email": "admin@example.com",
        "full_name": "Administrator",
        "workspace_name": "Acme Corporation",
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

    from src.giljo_mcp.models.auth import User
    from src.giljo_mcp.models.organizations import Organization

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
    from sqlalchemy import delete

    from src.giljo_mcp.models.auth import User

    async with db_manager.get_session_async() as session:
        await session.execute(delete(User))
        await session.commit()

    request_body = {
        "username": "admin",
        "password": "SecureAdmin123!@#",
        "email": "admin@example.com",
        "full_name": "Administrator",
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

    from src.giljo_mcp.models.auth import User
    from src.giljo_mcp.models.organizations import Organization

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
    from sqlalchemy import delete

    from src.giljo_mcp.models.auth import User

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
            "workspace_name": "Test Organization",
        },
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
async def test_auth_me_returns_org_fields(api_client, db_manager):
    """
    Test that GET /auth/me always returns org fields (post-0424j).

    After 0424j migration:
    - All users MUST have org_id (NOT NULL)
    - org_name and org_role should always be present
    - No null org scenarios possible

    This test verifies the API returns org fields for authenticated user.
    """
    # Arrange - Clear all users to simulate fresh install
    from sqlalchemy import delete

    from src.giljo_mcp.models.auth import User

    async with db_manager.get_session_async() as session:
        await session.execute(delete(User))
        await session.commit()

    # Create admin user with organization
    create_response = await api_client.post(
        "/api/auth/create-first-admin",
        json={
            "username": "testuser",
            "password": "SecureAdmin123!@#",
            "email": "test@example.com",
            "workspace_name": "User Workspace",
        },
    )
    assert create_response.status_code == 201

    # Act
    response = await api_client.get("/api/auth/me")

    # Assert
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    data = response.json()
    assert "org_id" in data, "Response should include org_id field"
    assert "org_name" in data, "Response should include org_name field"
    assert "org_role" in data, "Response should include org_role field"

    # Post-0424j: All users MUST have org
    assert data["org_id"] is not None, "org_id should never be null after 0424j migration"
    assert data["org_name"] == "User Workspace", f"Expected 'User Workspace', got '{data['org_name']}'"
    assert data["org_role"] is not None, "org_role should never be null after 0424j migration"
