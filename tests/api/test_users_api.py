"""
Users API Integration Tests - Handover 0615

Comprehensive validation of 6 user management endpoints:
- GET /users - List users (admin-only)
- POST /users - Create user (admin-only)
- GET /users/{user_id} - Get user details (admin or self)
- PUT /users/{user_id} - Update user (admin or self)
- DELETE /users/{user_id} - Soft-delete user (admin-only)
- POST /users/{user_id}/reset-password - Reset password (admin-only)

Additional endpoints tested (bonus):
- PUT /users/{user_id}/role - Change role (admin-only)
- PUT /users/{user_id}/password - Change password (admin or self)

Test Coverage:
- Happy path scenarios (200/201 responses)
- Authentication enforcement (401 Unauthorized)
- Authorization enforcement (403 Forbidden - admin vs regular user)
- Multi-tenant isolation (zero cross-tenant leakage)
- Password security (hashed, not returned)
- Self-service operations (users can update own profile)
- Validation errors (400 Bad Request)
- Not Found scenarios (404)

Phase 2 Progress: API Layer Testing (7/10 groups)
"""

import pytest
from httpx import AsyncClient
from passlib.hash import bcrypt


# ============================================================================
# FIXTURES - Test Users and Authentication
# ============================================================================


@pytest.fixture
async def tenant_a_admin(db_manager):
    """Create Tenant A admin user."""
    from uuid import uuid4

    from src.giljo_mcp.models import User
    from src.giljo_mcp.tenant import TenantManager

    unique_id = uuid4().hex[:8]
    username = f"admin_a_{unique_id}"
    tenant_key = TenantManager.generate_tenant_key(f"tenant_a_{unique_id}")

    async with db_manager.get_session_async() as session:
        user = User(
            username=username,
            password_hash=bcrypt.hash("admin_password"),
            email=f"{username}@test.com",
            role="admin",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user._test_username = username
        user._test_password = "admin_password"
        user._test_tenant_key = tenant_key
        return user


@pytest.fixture
async def tenant_a_developer(db_manager, tenant_a_admin):
    """Create Tenant A developer user (same tenant as admin)."""
    from uuid import uuid4

    from src.giljo_mcp.models import User

    unique_id = uuid4().hex[:8]
    username = f"dev_a_{unique_id}"

    async with db_manager.get_session_async() as session:
        user = User(
            username=username,
            password_hash=bcrypt.hash("dev_password"),
            email=f"{username}@test.com",
            role="developer",
            tenant_key=tenant_a_admin.tenant_key,  # Same tenant
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user._test_username = username
        user._test_password = "dev_password"
        user._test_tenant_key = tenant_a_admin.tenant_key
        return user


@pytest.fixture
async def tenant_b_admin(db_manager):
    """Create Tenant B admin user (different tenant)."""
    from uuid import uuid4

    from src.giljo_mcp.models import User
    from src.giljo_mcp.tenant import TenantManager

    unique_id = uuid4().hex[:8]
    username = f"admin_b_{unique_id}"
    tenant_key = TenantManager.generate_tenant_key(f"tenant_b_{unique_id}")

    async with db_manager.get_session_async() as session:
        user = User(
            username=username,
            password_hash=bcrypt.hash("admin_b_password"),
            email=f"{username}@test.com",
            role="admin",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user._test_username = username
        user._test_password = "admin_b_password"
        user._test_tenant_key = tenant_key
        return user


@pytest.fixture
async def tenant_a_admin_token(api_client: AsyncClient, tenant_a_admin):
    """Get JWT token for Tenant A admin."""
    response = await api_client.post(
        "/api/auth/login", json={"username": tenant_a_admin._test_username, "password": tenant_a_admin._test_password}
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    access_token = response.cookies.get("access_token")
    assert access_token is not None
    return access_token


@pytest.fixture
async def tenant_a_developer_token(api_client: AsyncClient, tenant_a_developer):
    """Get JWT token for Tenant A developer."""
    response = await api_client.post(
        "/api/auth/login",
        json={"username": tenant_a_developer._test_username, "password": tenant_a_developer._test_password},
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    access_token = response.cookies.get("access_token")
    assert access_token is not None
    return access_token


@pytest.fixture
async def tenant_b_admin_token(api_client: AsyncClient, tenant_b_admin):
    """Get JWT token for Tenant B admin."""
    response = await api_client.post(
        "/api/auth/login", json={"username": tenant_b_admin._test_username, "password": tenant_b_admin._test_password}
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    access_token = response.cookies.get("access_token")
    assert access_token is not None
    return access_token


# ============================================================================
# USER LIST TESTS - GET /users (admin-only)
# ============================================================================


class TestListUsers:
    """Test GET /users - List all users in tenant (admin-only)"""

    @pytest.mark.asyncio
    async def test_list_users_happy_path(
        self, api_client: AsyncClient, tenant_a_admin_token: str, tenant_a_admin, tenant_a_developer
    ):
        """Test GET /users - List users successfully (admin)."""
        response = await api_client.get("/api/v1/users/", cookies={"access_token": tenant_a_admin_token})

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2  # At least admin and developer

        # Find our test users
        usernames = [u["username"] for u in data]
        assert tenant_a_admin.username in usernames
        assert tenant_a_developer.username in usernames

        # Verify response schema (password should not be included)
        user = data[0]
        assert "id" in user
        assert "username" in user
        assert "email" in user
        assert "role" in user
        assert "tenant_key" in user
        assert "is_active" in user
        assert "created_at" in user
        assert "password" not in user
        assert "password_hash" not in user

    @pytest.mark.asyncio
    async def test_list_users_admin_cross_tenant_view(
        self,
        api_client: AsyncClient,
        tenant_a_admin_token: str,
        tenant_b_admin_token: str,
        tenant_a_admin,
        tenant_b_admin,
    ):
        """Test GET /users - Admins see all users (per-user tenancy design).

        Per-user tenancy policy: each user has their own tenant_key.
        Admins see ALL users across all tenants for system administration.
        This is intentional - see api/endpoints/users.py docstring.
        """
        # Tenant A admin should see ALL users (including Tenant B)
        response_a = await api_client.get("/api/v1/users/", cookies={"access_token": tenant_a_admin_token})
        assert response_a.status_code == 200
        users_a = response_a.json()
        usernames_a = [u["username"] for u in users_a]

        # Admin sees their own user
        assert tenant_a_admin.username in usernames_a
        # Admin sees OTHER tenant's users too (per-user tenancy design)
        assert tenant_b_admin.username in usernames_a

        # Tenant B admin also sees ALL users
        response_b = await api_client.get("/api/v1/users/", cookies={"access_token": tenant_b_admin_token})
        assert response_b.status_code == 200
        users_b = response_b.json()
        usernames_b = [u["username"] for u in users_b]

        assert tenant_b_admin.username in usernames_b
        assert tenant_a_admin.username in usernames_b

    @pytest.mark.asyncio
    async def test_list_users_unauthorized(self, api_client: AsyncClient):
        """Test GET /users - 401 without authentication."""
        response = await api_client.get("/api/v1/users/")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_users_forbidden_non_admin(self, api_client: AsyncClient, tenant_a_developer_token: str):
        """Test GET /users - 403 for non-admin users."""
        response = await api_client.get("/api/v1/users/", cookies={"access_token": tenant_a_developer_token})
        assert response.status_code == 403


# ============================================================================
# USER CREATE TESTS - POST /users (admin-only)
# ============================================================================


class TestCreateUser:
    """Test POST /users - Create new user (admin-only)"""

    @pytest.mark.asyncio
    async def test_create_user_happy_path(self, api_client: AsyncClient, tenant_a_admin_token: str, tenant_a_admin):
        """Test POST /users - Create user successfully."""
        from uuid import uuid4

        unique_id = uuid4().hex[:8]
        username = f"newuser_{unique_id}"
        email = f"newuser_{unique_id}@test.com"

        response = await api_client.post(
            "/api/v1/users/",
            json={
                "username": username,
                "email": email,
                "full_name": "New User",
                "password": "password123",
                "role": "developer",
                "is_active": True,
            },
            cookies={"access_token": tenant_a_admin_token},
        )

        assert response.status_code == 201
        data = response.json()

        # Validate response schema
        assert "id" in data
        assert data["username"] == username
        assert data["email"] == email
        assert data["full_name"] == "New User"
        assert data["role"] == "developer"
        assert data["tenant_key"] == tenant_a_admin.tenant_key  # Inherits admin's tenant
        assert data["is_active"] is True
        assert "created_at" in data

        # Password should NOT be in response
        assert "password" not in data
        assert "password_hash" not in data

    @pytest.mark.asyncio
    async def test_create_user_minimal_data(self, api_client: AsyncClient, tenant_a_admin_token: str):
        """Test POST /users - Create with minimal required data."""
        from uuid import uuid4

        unique_id = uuid4().hex[:8]
        username = f"minimaluser_{unique_id}"

        response = await api_client.post(
            "/api/v1/users/",
            json={"username": username, "password": "password123"},
            cookies={"access_token": tenant_a_admin_token},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == username
        assert data["email"] is None
        assert data["full_name"] is None
        assert data["role"] == "developer"  # Default role

    @pytest.mark.asyncio
    async def test_create_user_duplicate_username(
        self, api_client: AsyncClient, tenant_a_admin_token: str, tenant_a_developer
    ):
        """Test POST /users - 400 for duplicate username."""
        response = await api_client.post(
            "/api/v1/users/",
            json={
                "username": tenant_a_developer.username,  # Duplicate
                "password": "password123",
            },
            cookies={"access_token": tenant_a_admin_token},
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(
        self, api_client: AsyncClient, tenant_a_admin_token: str, tenant_a_developer
    ):
        """Test POST /users - 400 for duplicate email."""
        response = await api_client.post(
            "/api/v1/users/",
            json={
                "username": "uniqueusername",
                "email": tenant_a_developer.email,  # Duplicate
                "password": "password123",
            },
            cookies={"access_token": tenant_a_admin_token},
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_create_user_invalid_role(self, api_client: AsyncClient, tenant_a_admin_token: str):
        """Test POST /users - 422 for invalid role."""
        from uuid import uuid4

        unique_id = uuid4().hex[:8]

        response = await api_client.post(
            "/api/v1/users/",
            json={
                "username": f"testuser_{unique_id}",
                "password": "password123",
                "role": "superadmin",  # Invalid role
            },
            cookies={"access_token": tenant_a_admin_token},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_create_user_unauthorized(self, api_client: AsyncClient):
        """Test POST /users - 401 without authentication."""
        from uuid import uuid4

        unique_id = uuid4().hex[:8]

        response = await api_client.post(
            "/api/v1/users/", json={"username": f"testuser_{unique_id}", "password": "password123"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_user_forbidden_non_admin(self, api_client: AsyncClient, tenant_a_developer_token: str):
        """Test POST /users - 403 for non-admin users."""
        from uuid import uuid4

        unique_id = uuid4().hex[:8]

        response = await api_client.post(
            "/api/v1/users/",
            json={"username": f"testuser_{unique_id}", "password": "password123"},
            cookies={"access_token": tenant_a_developer_token},
        )
        assert response.status_code == 403


# ============================================================================
# USER GET TESTS - GET /users/{user_id} (admin or self)
# ============================================================================


class TestGetUser:
    """Test GET /users/{user_id} - Get user details"""

    @pytest.mark.asyncio
    async def test_get_user_self(self, api_client: AsyncClient, tenant_a_developer_token: str, tenant_a_developer):
        """Test GET /users/{user_id} - Users can view their own profile."""
        response = await api_client.get(
            f"/api/v1/users/{tenant_a_developer.id}", cookies={"access_token": tenant_a_developer_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(tenant_a_developer.id)
        assert data["username"] == tenant_a_developer.username
        assert "password" not in data

    @pytest.mark.asyncio
    async def test_get_user_admin_view_other(
        self, api_client: AsyncClient, tenant_a_admin_token: str, tenant_a_developer
    ):
        """Test GET /users/{user_id} - Admin can view any user in their tenant."""
        response = await api_client.get(
            f"/api/v1/users/{tenant_a_developer.id}", cookies={"access_token": tenant_a_admin_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(tenant_a_developer.id)
        assert data["username"] == tenant_a_developer.username

    @pytest.mark.asyncio
    async def test_get_user_non_admin_view_other_forbidden(
        self, api_client: AsyncClient, tenant_a_developer_token: str, tenant_a_admin
    ):
        """Test GET /users/{user_id} - 403 when non-admin tries to view other users."""
        response = await api_client.get(
            f"/api/v1/users/{tenant_a_admin.id}", cookies={"access_token": tenant_a_developer_token}
        )

        assert response.status_code == 403
        assert "Cannot view other users" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_get_user_cross_tenant_allowed_for_admin(
        self, api_client: AsyncClient, tenant_a_admin_token: str, tenant_b_admin
    ):
        """Test GET /users/{user_id} - Admin can access cross-tenant users (per-user tenancy design)."""
        response = await api_client.get(
            f"/api/v1/users/{tenant_b_admin.id}", cookies={"access_token": tenant_a_admin_token}
        )

        # Per-user tenancy: admins can view ALL users for management
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == tenant_b_admin.username

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, api_client: AsyncClient, tenant_a_admin_token: str):
        """Test GET /users/{user_id} - 404 for non-existent user."""
        response = await api_client.get(
            "/api/v1/users/00000000-0000-0000-0000-000000000000", cookies={"access_token": tenant_a_admin_token}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_user_unauthorized(self, api_client: AsyncClient, tenant_a_developer):
        """Test GET /users/{user_id} - 401 without authentication."""
        response = await api_client.get(f"/api/v1/users/{tenant_a_developer.id}")
        assert response.status_code == 401


# ============================================================================
# USER UPDATE TESTS - PUT /users/{user_id} (admin or self)
# ============================================================================


class TestUpdateUser:
    """Test PUT /users/{user_id} - Update user profile"""

    @pytest.mark.asyncio
    async def test_update_user_self(self, api_client: AsyncClient, tenant_a_developer_token: str, tenant_a_developer):
        """Test PUT /users/{user_id} - Users can update their own profile."""
        from uuid import uuid4

        unique_id = uuid4().hex[:8]

        response = await api_client.put(
            f"/api/v1/users/{tenant_a_developer.id}",
            json={"email": f"newemail_{unique_id}@test.com", "full_name": "Updated Name"},
            cookies={"access_token": tenant_a_developer_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == f"newemail_{unique_id}@test.com"
        assert data["full_name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_user_admin_update_other(
        self, api_client: AsyncClient, tenant_a_admin_token: str, tenant_a_developer
    ):
        """Test PUT /users/{user_id} - Admin can update any user in their tenant."""
        response = await api_client.put(
            f"/api/v1/users/{tenant_a_developer.id}",
            json={"full_name": "Admin Updated Name", "is_active": False},
            cookies={"access_token": tenant_a_admin_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Admin Updated Name"
        assert data["is_active"] is False

    @pytest.mark.asyncio
    async def test_update_user_partial(
        self, api_client: AsyncClient, tenant_a_developer_token: str, tenant_a_developer
    ):
        """Test PUT /users/{user_id} - Partial update (only email)."""
        from uuid import uuid4

        unique_id = uuid4().hex[:8]
        original_full_name = tenant_a_developer.full_name

        response = await api_client.put(
            f"/api/v1/users/{tenant_a_developer.id}",
            json={"email": f"partial_{unique_id}@test.com"},
            cookies={"access_token": tenant_a_developer_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == f"partial_{unique_id}@test.com"
        # Full name should remain unchanged
        assert data["full_name"] == original_full_name

    @pytest.mark.asyncio
    async def test_update_user_duplicate_email(
        self, api_client: AsyncClient, tenant_a_admin_token: str, tenant_a_admin, tenant_a_developer
    ):
        """Test PUT /users/{user_id} - 400 for duplicate email."""
        response = await api_client.put(
            f"/api/v1/users/{tenant_a_developer.id}",
            json={"email": tenant_a_admin.email},  # Duplicate
            cookies={"access_token": tenant_a_admin_token},
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_update_user_non_admin_update_other_forbidden(
        self, api_client: AsyncClient, tenant_a_developer_token: str, tenant_a_admin
    ):
        """Test PUT /users/{user_id} - 403 when non-admin tries to update other users."""
        response = await api_client.put(
            f"/api/v1/users/{tenant_a_admin.id}",
            json={"full_name": "Hacked"},
            cookies={"access_token": tenant_a_developer_token},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_user_cross_tenant_allowed_for_admin(
        self, api_client: AsyncClient, tenant_a_admin_token: str, tenant_b_admin
    ):
        """Test PUT /users/{user_id} - Admin can update cross-tenant users (per-user tenancy design)."""
        response = await api_client.put(
            f"/api/v1/users/{tenant_b_admin.id}",
            json={"full_name": "Cross-tenant admin update"},
            cookies={"access_token": tenant_a_admin_token},
        )

        # Per-user tenancy: admins can manage ALL users across tenants
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Cross-tenant admin update"

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, api_client: AsyncClient, tenant_a_admin_token: str):
        """Test PUT /users/{user_id} - 404 for non-existent user."""
        response = await api_client.put(
            "/api/v1/users/00000000-0000-0000-0000-000000000000",
            json={"full_name": "Test"},
            cookies={"access_token": tenant_a_admin_token},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_user_unauthorized(self, api_client: AsyncClient, tenant_a_developer):
        """Test PUT /users/{user_id} - 401 without authentication."""
        response = await api_client.put(f"/api/v1/users/{tenant_a_developer.id}", json={"full_name": "Test"})
        assert response.status_code == 401


# ============================================================================
# USER DELETE TESTS - DELETE /users/{user_id} (admin-only)
# ============================================================================


class TestDeleteUser:
    """Test DELETE /users/{user_id} - Soft-delete user (admin-only)"""

    @pytest.mark.asyncio
    async def test_delete_user_happy_path(
        self, api_client: AsyncClient, tenant_a_admin_token: str, tenant_a_admin, db_manager
    ):
        """Test DELETE /users/{user_id} - Soft-delete user successfully."""
        # Create a user to delete
        from uuid import uuid4

        from src.giljo_mcp.models import User

        unique_id = uuid4().hex[:8]
        username = f"to_delete_{unique_id}"

        async with db_manager.get_session_async() as session:
            user_to_delete = User(
                username=username,
                password_hash=bcrypt.hash("password123"),
                email=f"{username}@test.com",
                role="developer",
                tenant_key=tenant_a_admin.tenant_key,
                is_active=True,
            )
            session.add(user_to_delete)
            await session.commit()
            await session.refresh(user_to_delete)
            user_id = user_to_delete.id

        # Delete the user
        response = await api_client.delete(f"/api/v1/users/{user_id}", cookies={"access_token": tenant_a_admin_token})

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "User deactivated successfully"
        assert data["user_id"] == str(user_id)
        assert data["username"] == username

        # Verify user is soft-deleted (is_active=False)
        async with db_manager.get_session_async() as session:
            from sqlalchemy import select

            stmt = select(User).where(User.id == user_id)
            result = await session.execute(stmt)
            deleted_user = result.scalar_one_or_none()
            assert deleted_user is not None
            assert deleted_user.is_active is False  # Soft delete

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, api_client: AsyncClient, tenant_a_admin_token: str):
        """Test DELETE /users/{user_id} - 404 for non-existent user."""
        response = await api_client.delete(
            "/api/v1/users/00000000-0000-0000-0000-000000000000", cookies={"access_token": tenant_a_admin_token}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_user_cross_tenant_forbidden(
        self, api_client: AsyncClient, tenant_a_admin_token: str, tenant_b_admin
    ):
        """Test DELETE /users/{user_id} - 404 for cross-tenant deletion."""
        response = await api_client.delete(
            f"/api/v1/users/{tenant_b_admin.id}", cookies={"access_token": tenant_a_admin_token}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_user_unauthorized(self, api_client: AsyncClient, tenant_a_developer):
        """Test DELETE /users/{user_id} - 401 without authentication."""
        response = await api_client.delete(f"/api/v1/users/{tenant_a_developer.id}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_user_forbidden_non_admin(
        self, api_client: AsyncClient, tenant_a_developer_token: str, tenant_a_developer
    ):
        """Test DELETE /users/{user_id} - 403 for non-admin users."""
        response = await api_client.delete(
            f"/api/v1/users/{tenant_a_developer.id}", cookies={"access_token": tenant_a_developer_token}
        )
        assert response.status_code == 403


# ============================================================================
# PASSWORD RESET TESTS - POST /users/{user_id}/reset-password (admin-only)
# ============================================================================


class TestResetPassword:
    """Test POST /users/{user_id}/reset-password - Reset password to default"""

    @pytest.mark.asyncio
    async def test_reset_password_happy_path(
        self, api_client: AsyncClient, tenant_a_admin_token: str, tenant_a_developer, db_manager
    ):
        """Test POST /users/{user_id}/reset-password - Reset password successfully."""
        response = await api_client.post(
            f"/api/v1/users/{tenant_a_developer.id}/reset-password", cookies={"access_token": tenant_a_admin_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Password reset successful"

        # Verify password was reset to 'GiljoMCP' and must_change_password set
        async with db_manager.get_session_async() as session:
            from sqlalchemy import select

            from src.giljo_mcp.models import User

            stmt = select(User).where(User.id == tenant_a_developer.id)
            result = await session.execute(stmt)
            user = result.scalar_one()

            # Password should be 'GiljoMCP'
            assert bcrypt.verify("GiljoMCP", user.password_hash)
            assert user.must_change_password is True

    @pytest.mark.asyncio
    async def test_reset_password_not_found(self, api_client: AsyncClient, tenant_a_admin_token: str):
        """Test POST /users/{user_id}/reset-password - 404 for non-existent user."""
        response = await api_client.post(
            "/api/v1/users/00000000-0000-0000-0000-000000000000/reset-password",
            cookies={"access_token": tenant_a_admin_token},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_reset_password_cross_tenant_forbidden(
        self, api_client: AsyncClient, tenant_a_admin_token: str, tenant_b_admin
    ):
        """Test POST /users/{user_id}/reset-password - 404 for cross-tenant reset."""
        response = await api_client.post(
            f"/api/v1/users/{tenant_b_admin.id}/reset-password", cookies={"access_token": tenant_a_admin_token}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_reset_password_unauthorized(self, api_client: AsyncClient, tenant_a_developer):
        """Test POST /users/{user_id}/reset-password - 401 without authentication."""
        response = await api_client.post(f"/api/v1/users/{tenant_a_developer.id}/reset-password")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_reset_password_forbidden_non_admin(
        self, api_client: AsyncClient, tenant_a_developer_token: str, tenant_a_admin
    ):
        """Test POST /users/{user_id}/reset-password - 403 for non-admin users."""
        response = await api_client.post(
            f"/api/v1/users/{tenant_a_admin.id}/reset-password", cookies={"access_token": tenant_a_developer_token}
        )
        assert response.status_code == 403


# ============================================================================
# PASSWORD SECURITY TESTS
# ============================================================================


class TestPasswordSecurity:
    """Comprehensive password security validation"""

    @pytest.mark.asyncio
    async def test_password_never_returned_in_responses(
        self, api_client: AsyncClient, tenant_a_admin_token: str, tenant_a_developer
    ):
        """Test that passwords are never included in API responses."""
        from uuid import uuid4

        # List users
        response = await api_client.get("/api/v1/users/", cookies={"access_token": tenant_a_admin_token})
        assert response.status_code == 200
        for user in response.json():
            assert "password" not in user
            assert "password_hash" not in user

        # Get user
        response = await api_client.get(
            f"/api/v1/users/{tenant_a_developer.id}", cookies={"access_token": tenant_a_admin_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert "password" not in data
        assert "password_hash" not in data

        # Create user
        unique_id = uuid4().hex[:8]
        response = await api_client.post(
            "/api/v1/users/",
            json={"username": f"securetest_{unique_id}", "password": "test123456"},
            cookies={"access_token": tenant_a_admin_token},
        )
        assert response.status_code == 201
        data = response.json()
        assert "password" not in data
        assert "password_hash" not in data

    @pytest.mark.asyncio
    async def test_password_hashed_in_database(self, api_client: AsyncClient, tenant_a_admin_token: str, db_manager):
        """Test that passwords are hashed in the database."""
        from uuid import uuid4

        # Create user via API (note: API uses default password 'GiljoMCP' per Handover 0023)
        unique_id = uuid4().hex[:8]
        response = await api_client.post(
            "/api/v1/users/",
            json={
                "username": f"hashtest_{unique_id}",
                "password": "plaintext123",  # This is ignored, default is used
            },
            cookies={"access_token": tenant_a_admin_token},
        )
        assert response.status_code == 201
        user_id = response.json()["id"]

        # Verify password is hashed in database
        async with db_manager.get_session_async() as session:
            from sqlalchemy import select

            from src.giljo_mcp.models import User

            stmt = select(User).where(User.id == user_id)
            result = await session.execute(stmt)
            user = result.scalar_one()

            # Password hash should not equal plaintext default
            assert user.password_hash != "GiljoMCP"

            # Password hash should be bcrypt format
            assert user.password_hash.startswith("$2b$")

            # Bcrypt verify should work with default password 'GiljoMCP'
            assert bcrypt.verify("GiljoMCP", user.password_hash)


# ============================================================================
# MULTI-TENANT ADMIN ACCESS TESTS (Per-User Tenancy Design)
# ============================================================================


class TestMultiTenantIsolation:
    """Per-user tenancy admin access verification.

    In the per-user tenancy model, each user has their own tenant_key.
    Admins have full access to ALL users for system administration.
    Non-admins can only access/modify themselves.
    """

    @pytest.mark.asyncio
    async def test_admin_cross_tenant_access(
        self,
        api_client: AsyncClient,
        tenant_a_admin_token: str,
        tenant_b_admin_token: str,
        tenant_a_admin,
        tenant_a_developer,
        tenant_b_admin,
    ):
        """Test admin cross-tenant access (per-user tenancy design allows this)."""

        # Tenant A admin can list ALL users (including Tenant B)
        response = await api_client.get("/api/v1/users/", cookies={"access_token": tenant_a_admin_token})
        assert response.status_code == 200
        usernames = [u["username"] for u in response.json()]
        assert tenant_a_admin.username in usernames
        assert tenant_a_developer.username in usernames
        assert tenant_b_admin.username in usernames  # Admin sees ALL users

        # Tenant A admin can get Tenant B user
        response = await api_client.get(
            f"/api/v1/users/{tenant_b_admin.id}", cookies={"access_token": tenant_a_admin_token}
        )
        assert response.status_code == 200

        # Tenant A admin can update Tenant B user (per-user tenancy)
        response = await api_client.put(
            f"/api/v1/users/{tenant_b_admin.id}",
            json={"full_name": "Admin Cross-Tenant Update"},
            cookies={"access_token": tenant_a_admin_token},
        )
        assert response.status_code == 200
