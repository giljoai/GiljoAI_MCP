"""
Tests for Organization API endpoints - Handover 0424c.

Comprehensive validation of organization CRUD and membership management:
- Organization CRUD endpoints
- Membership management endpoints
- Permission enforcement (owner, admin, member, viewer roles)
- Multi-tenant isolation
- Response schema validation

TDD Methodology: This test file is written FIRST (RED phase).
Endpoints are implemented after to make tests pass (GREEN phase).
"""

import pytest
from httpx import AsyncClient
from uuid import uuid4

from src.giljo_mcp.auth.jwt_manager import JWTManager
from src.giljo_mcp.models.auth import User
from src.giljo_mcp.tenant import TenantManager
from passlib.hash import bcrypt


# ============================================================================
# FIXTURES - Additional users for org testing
# ============================================================================

@pytest.fixture
async def other_user_data(db_manager) -> dict:
    """Create a second user for tests, return both ID and headers."""
    from uuid import uuid4
    from src.giljo_mcp.models.organizations import Organization

    unique_suffix = uuid4().hex[:8]
    tenant_key = TenantManager.generate_tenant_key()

    async with db_manager.get_session_async() as session:
        # Create org first (0424m: org_id is NOT NULL, tenant_key required)
        org = Organization(
            name=f"Other User Org {unique_suffix}",
            slug=f"other-user-org-{unique_suffix}",
            tenant_key=tenant_key,  # 0424m: Required NOT NULL
            is_active=True
        )
        session.add(org)
        await session.flush()

        user = User(
            username=f"other_user_{unique_suffix}",
            email=f"other_{unique_suffix}@example.com",
            password_hash=bcrypt.hash("test_password"),
            tenant_key=tenant_key,
            role="developer",
            is_active=True,
            org_id=org.id  # Required after 0424j
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        token = JWTManager.create_access_token(
            user_id=user.id,
            username=user.username,
            role=user.role,
            tenant_key=user.tenant_key
        )

        return {
            "id": user.id,
            "headers": {"Cookie": f"access_token={token}"}
        }


@pytest.fixture
async def other_user_id(other_user_data) -> str:
    """Get second user's ID."""
    return other_user_data["id"]


@pytest.fixture
async def other_user_headers(other_user_data) -> dict:
    """Auth headers for the second user."""
    return other_user_data["headers"]


@pytest.fixture
async def test_user_id(db_manager, auth_headers) -> str:
    """Get user ID from auth_headers fixture (for owner tests)."""
    # Extract token from Cookie header
    cookie = auth_headers["Cookie"]
    token = cookie.replace("access_token=", "")

    # Decode token to get user_id (no verification needed in tests)
    payload = JWTManager.decode_token_no_verify(token)
    return payload["sub"]  # JWT uses "sub" for subject (user_id)


@pytest.fixture
async def third_user_id(db_manager) -> str:
    """Create a third user for complex permission tests."""
    from uuid import uuid4
    from src.giljo_mcp.models.organizations import Organization

    unique_suffix = uuid4().hex[:8]
    tenant_key = TenantManager.generate_tenant_key()

    async with db_manager.get_session_async() as session:
        # Create org first (0424m: org_id is NOT NULL, tenant_key required)
        org = Organization(
            name=f"Third User Org {unique_suffix}",
            slug=f"third-user-org-{unique_suffix}",
            tenant_key=tenant_key,  # 0424m: Required NOT NULL
            is_active=True
        )
        session.add(org)
        await session.flush()

        user = User(
            username=f"third_user_{unique_suffix}",
            email=f"third_{unique_suffix}@example.com",
            password_hash=bcrypt.hash("test_password"),
            tenant_key=tenant_key,
            role="developer",
            is_active=True,
            org_id=org.id  # Required after 0424j
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user.id


@pytest.fixture
async def member_user_headers(db_manager) -> dict:
    """Auth headers for a member-role user (for permission tests)."""
    from uuid import uuid4
    from src.giljo_mcp.models.organizations import Organization

    unique_suffix = uuid4().hex[:8]
    tenant_key = TenantManager.generate_tenant_key()

    async with db_manager.get_session_async() as session:
        # Create org first (0424m: org_id is NOT NULL, tenant_key required)
        org = Organization(
            name=f"Member User Org {unique_suffix}",
            slug=f"member-user-org-{unique_suffix}",
            tenant_key=tenant_key,  # 0424m: Required NOT NULL
            is_active=True
        )
        session.add(org)
        await session.flush()

        user = User(
            username=f"member_user_{unique_suffix}",
            email=f"member_{unique_suffix}@example.com",
            password_hash=bcrypt.hash("test_password"),
            tenant_key=tenant_key,
            role="developer",
            is_active=True,
            org_id=org.id  # Required after 0424j
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        token = JWTManager.create_access_token(
            user_id=user.id,
            username=user.username,
            role=user.role,
            tenant_key=user.tenant_key
        )

        return {"Cookie": f"access_token={token}"}


# ============================================================================
# Organization CRUD Tests
# ============================================================================

class TestOrganizationCRUD:
    """Tests for organization CRUD endpoints."""

    @pytest.mark.asyncio
    async def test_create_organization(self, api_client: AsyncClient, auth_headers):
        """Test POST /api/organizations creates org with user as owner."""
        unique_slug = f"test-company-{uuid4().hex[:8]}"
        response = await api_client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Test Company", "slug": unique_slug}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Company"
        assert data["slug"] == unique_slug
        assert data["is_active"] is True
        assert len(data["members"]) == 1
        assert data["members"][0]["role"] == "owner"

    @pytest.mark.asyncio
    async def test_create_organization_auto_slug(self, api_client: AsyncClient, auth_headers):
        """Test slug auto-generated from name."""
        unique_name = f"My Awesome Company {uuid4().hex[:6]}"
        response = await api_client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": unique_name}
        )

        assert response.status_code == 201
        # Verify slug was generated (contains "my-awesome-company" prefix)
        assert response.json()["slug"].startswith("my-awesome-company")

    @pytest.mark.asyncio
    async def test_create_organization_duplicate_slug(
        self,
        api_client: AsyncClient,
        auth_headers
    ):
        """Test duplicate slug returns 409."""
        dup_slug = f"dup-slug-{uuid4().hex[:8]}"
        await api_client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "First", "slug": dup_slug}
        )

        response = await api_client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Second", "slug": dup_slug}
        )

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_list_user_organizations(self, api_client: AsyncClient, auth_headers):
        """Test GET /api/organizations returns user's orgs."""
        # Create two orgs
        prefix = uuid4().hex[:8]
        await api_client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Org 1", "slug": f"list-org-1-{prefix}"}
        )
        await api_client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Org 2", "slug": f"list-org-2-{prefix}"}
        )

        response = await api_client.get("/api/organizations", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

    @pytest.mark.asyncio
    async def test_get_organization(self, api_client: AsyncClient, auth_headers):
        """Test GET /api/organizations/{org_id} returns org details."""
        create_response = await api_client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Get Test", "slug": f"get-test-org-{uuid4().hex[:8]}"}
        )
        org_id = create_response.json()["id"]

        response = await api_client.get(
            f"/api/organizations/{org_id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Get Test"

    @pytest.mark.asyncio
    async def test_get_organization_not_member(
        self,
        api_client: AsyncClient,
        auth_headers,
        other_user_headers
    ):
        """Test non-member cannot access org."""
        create_response = await api_client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Private Org", "slug": f"private-org-{uuid4().hex[:8]}"}
        )
        org_id = create_response.json()["id"]

        response = await api_client.get(
            f"/api/organizations/{org_id}",
            headers=other_user_headers
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_organization(self, api_client: AsyncClient, auth_headers):
        """Test PUT /api/organizations/{org_id} updates org."""
        create_response = await api_client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Update Test", "slug": f"update-test-{uuid4().hex[:8]}"}
        )
        org_id = create_response.json()["id"]

        response = await api_client.put(
            f"/api/organizations/{org_id}",
            headers=auth_headers,
            json={"name": "Updated Name"}
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_delete_organization(self, api_client: AsyncClient, auth_headers):
        """Test DELETE /api/organizations/{org_id} soft deletes org."""
        create_response = await api_client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Delete Test", "slug": f"delete-test-{uuid4().hex[:8]}"}
        )
        org_id = create_response.json()["id"]

        response = await api_client.delete(
            f"/api/organizations/{org_id}",
            headers=auth_headers
        )

        assert response.status_code == 200

        # Verify org no longer accessible
        get_response = await api_client.get(
            f"/api/organizations/{org_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404


# ============================================================================
# Membership Management Tests
# ============================================================================

class TestMembershipManagement:
    """Tests for membership management endpoints."""

    @pytest.mark.asyncio
    async def test_list_members(self, api_client: AsyncClient, auth_headers):
        """Test GET /api/organizations/{org_id}/members lists members."""
        create_response = await api_client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Members Test", "slug": f"members-test-{uuid4().hex[:8]}"}
        )
        org_id = create_response.json()["id"]

        response = await api_client.get(
            f"/api/organizations/{org_id}/members",
            headers=auth_headers
        )

        assert response.status_code == 200
        members = response.json()
        assert len(members) == 1
        assert members[0]["role"] == "owner"

    @pytest.mark.asyncio
    async def test_invite_member(
        self,
        api_client: AsyncClient,
        auth_headers,
        other_user_id
    ):
        """Test POST /api/organizations/{org_id}/members invites user."""
        create_response = await api_client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Invite Test", "slug": f"invite-test-{uuid4().hex[:8]}"}
        )
        org_id = create_response.json()["id"]

        response = await api_client.post(
            f"/api/organizations/{org_id}/members",
            headers=auth_headers,
            json={"user_id": other_user_id, "role": "member"}
        )

        assert response.status_code == 201
        assert response.json()["role"] == "member"

    @pytest.mark.asyncio
    async def test_change_member_role(
        self,
        api_client: AsyncClient,
        auth_headers,
        other_user_id
    ):
        """Test PUT /api/organizations/{org_id}/members/{user_id} changes role."""
        create_response = await api_client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Role Test", "slug": f"role-test-{uuid4().hex[:8]}"}
        )
        org_id = create_response.json()["id"]

        # Invite member
        await api_client.post(
            f"/api/organizations/{org_id}/members",
            headers=auth_headers,
            json={"user_id": other_user_id, "role": "member"}
        )

        # Change to admin
        response = await api_client.put(
            f"/api/organizations/{org_id}/members/{other_user_id}",
            headers=auth_headers,
            json={"role": "admin"}
        )

        assert response.status_code == 200
        assert response.json()["role"] == "admin"

    @pytest.mark.asyncio
    async def test_remove_member(
        self,
        api_client: AsyncClient,
        auth_headers,
        other_user_id
    ):
        """Test DELETE /api/organizations/{org_id}/members/{user_id} removes member."""
        create_response = await api_client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Remove Test", "slug": f"remove-test-{uuid4().hex[:8]}"}
        )
        org_id = create_response.json()["id"]

        # Invite member
        await api_client.post(
            f"/api/organizations/{org_id}/members",
            headers=auth_headers,
            json={"user_id": other_user_id, "role": "member"}
        )

        # Remove member
        response = await api_client.delete(
            f"/api/organizations/{org_id}/members/{other_user_id}",
            headers=auth_headers
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_cannot_remove_owner(
        self,
        api_client: AsyncClient,
        auth_headers,
        test_user_id
    ):
        """Test owner cannot be removed."""
        create_response = await api_client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Owner Test", "slug": f"owner-test-{uuid4().hex[:8]}"}
        )
        org_id = create_response.json()["id"]

        response = await api_client.delete(
            f"/api/organizations/{org_id}/members/{test_user_id}",
            headers=auth_headers
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_transfer_ownership(
        self,
        api_client: AsyncClient,
        auth_headers,
        other_user_id
    ):
        """Test POST /api/organizations/{org_id}/transfer transfers ownership."""
        create_response = await api_client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Transfer Test", "slug": f"transfer-test-{uuid4().hex[:8]}"}
        )
        org_id = create_response.json()["id"]

        # Invite member first
        await api_client.post(
            f"/api/organizations/{org_id}/members",
            headers=auth_headers,
            json={"user_id": other_user_id, "role": "admin"}
        )

        # Transfer ownership
        response = await api_client.post(
            f"/api/organizations/{org_id}/transfer",
            headers=auth_headers,
            json={"new_owner_id": other_user_id}
        )

        assert response.status_code == 200


# ============================================================================
# Permission Tests
# ============================================================================

class TestPermissions:
    """Tests for role-based permission enforcement."""

    @pytest.mark.asyncio
    async def test_member_cannot_update_org(
        self,
        api_client: AsyncClient,
        auth_headers,
        other_user_headers,
        other_user_id
    ):
        """Test member role cannot update organization."""
        # Create org
        create_response = await api_client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Perm Test", "slug": f"perm-test-{uuid4().hex[:8]}"}
        )
        org_id = create_response.json()["id"]

        # Invite other user as member
        await api_client.post(
            f"/api/organizations/{org_id}/members",
            headers=auth_headers,
            json={"user_id": other_user_id, "role": "member"}
        )

        # Try to update org as member
        response = await api_client.put(
            f"/api/organizations/{org_id}",
            headers=other_user_headers,
            json={"name": "Hacked Name"}
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_can_invite_members(
        self,
        api_client: AsyncClient,
        auth_headers,
        other_user_headers,
        other_user_id,
        third_user_id
    ):
        """Test admin role can invite new members."""
        # Create org
        create_response = await api_client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Admin Invite Test", "slug": f"admin-invite-test-{uuid4().hex[:8]}"}
        )
        org_id = create_response.json()["id"]

        # Make other_user an admin
        await api_client.post(
            f"/api/organizations/{org_id}/members",
            headers=auth_headers,
            json={"user_id": other_user_id, "role": "admin"}
        )

        # Other user (admin) invites third user
        response = await api_client.post(
            f"/api/organizations/{org_id}/members",
            headers=other_user_headers,
            json={"user_id": third_user_id, "role": "viewer"}
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_only_owner_can_delete_org(
        self,
        api_client: AsyncClient,
        auth_headers,
        other_user_headers,
        other_user_id
    ):
        """Test only owner can delete organization."""
        # Create org
        create_response = await api_client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Delete Perm Test", "slug": f"delete-perm-test-{uuid4().hex[:8]}"}
        )
        org_id = create_response.json()["id"]

        # Make other_user an admin (not owner)
        await api_client.post(
            f"/api/organizations/{org_id}/members",
            headers=auth_headers,
            json={"user_id": other_user_id, "role": "admin"}
        )

        # Try to delete as admin (not owner)
        response = await api_client.delete(
            f"/api/organizations/{org_id}",
            headers=other_user_headers
        )

        assert response.status_code == 403
