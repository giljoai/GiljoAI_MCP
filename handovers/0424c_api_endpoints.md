# Handover 0424c: Organization API Endpoints

**Date:** 2026-01-19
**From Agent:** Planning Session
**To Agent:** tdd-implementor / backend-integration-tester
**Priority:** HIGH
**Estimated Complexity:** 4-6 hours
**Status:** Ready for Implementation
**Parent:** 0424_org_hierarchy_overview.md
**Depends On:** 0424b (Service Layer)

---

## Summary

Create REST API endpoints for Organization management:
- Organization CRUD (create, read, update, delete)
- Membership management (invite, remove, change role)
- Permission middleware for role-based access

---

## TDD Discipline

Follow RED -> GREEN -> REFACTOR for all implementation.

```bash
# Create test file FIRST
touch tests/api/test_organizations_api.py

# Write failing tests
pytest tests/api/test_organizations_api.py -v
# MUST SEE: FAILED (RED)

# Implement endpoints
pytest tests/api/test_organizations_api.py -v
# MUST SEE: PASSED (GREEN)
```

---

## API Specification

### Organization Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/organizations` | Create organization | User |
| GET | `/api/organizations` | List user's organizations | User |
| GET | `/api/organizations/{org_id}` | Get organization | Member |
| PUT | `/api/organizations/{org_id}` | Update organization | Owner/Admin |
| DELETE | `/api/organizations/{org_id}` | Delete organization | Owner |

### Membership Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/organizations/{org_id}/members` | List members | Member |
| POST | `/api/organizations/{org_id}/members` | Invite member | Owner/Admin |
| PUT | `/api/organizations/{org_id}/members/{user_id}` | Change role | Owner/Admin |
| DELETE | `/api/organizations/{org_id}/members/{user_id}` | Remove member | Owner/Admin |
| POST | `/api/organizations/{org_id}/transfer` | Transfer ownership | Owner |

---

## Implementation Plan

### Step 1: Create Test File (tests/api/test_organizations_api.py)

```python
"""Tests for Organization API endpoints."""
import pytest
from httpx import AsyncClient


class TestOrganizationCRUD:
    """Tests for organization CRUD endpoints."""

    @pytest.mark.asyncio
    async def test_create_organization(self, client: AsyncClient, auth_headers):
        """Test POST /api/organizations creates org with user as owner."""
        response = await client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Test Company", "slug": "test-company"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Company"
        assert data["slug"] == "test-company"
        assert len(data["members"]) == 1
        assert data["members"][0]["role"] == "owner"

    @pytest.mark.asyncio
    async def test_create_organization_auto_slug(self, client: AsyncClient, auth_headers):
        """Test slug auto-generated from name."""
        response = await client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "My Awesome Company!"}
        )

        assert response.status_code == 201
        assert response.json()["slug"] == "my-awesome-company"

    @pytest.mark.asyncio
    async def test_create_organization_duplicate_slug(
        self,
        client: AsyncClient,
        auth_headers
    ):
        """Test duplicate slug returns 409."""
        await client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "First", "slug": "dup-slug"}
        )

        response = await client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Second", "slug": "dup-slug"}
        )

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_list_user_organizations(self, client: AsyncClient, auth_headers):
        """Test GET /api/organizations returns user's orgs."""
        # Create two orgs
        await client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Org 1", "slug": "list-org-1"}
        )
        await client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Org 2", "slug": "list-org-2"}
        )

        response = await client.get("/api/organizations", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

    @pytest.mark.asyncio
    async def test_get_organization(self, client: AsyncClient, auth_headers):
        """Test GET /api/organizations/{org_id} returns org details."""
        create_response = await client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Get Test", "slug": "get-test-org"}
        )
        org_id = create_response.json()["id"]

        response = await client.get(
            f"/api/organizations/{org_id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Get Test"

    @pytest.mark.asyncio
    async def test_get_organization_not_member(
        self,
        client: AsyncClient,
        auth_headers,
        other_user_headers
    ):
        """Test non-member cannot access org."""
        create_response = await client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Private Org", "slug": "private-org"}
        )
        org_id = create_response.json()["id"]

        response = await client.get(
            f"/api/organizations/{org_id}",
            headers=other_user_headers
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_organization(self, client: AsyncClient, auth_headers):
        """Test PUT /api/organizations/{org_id} updates org."""
        create_response = await client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Update Test", "slug": "update-test"}
        )
        org_id = create_response.json()["id"]

        response = await client.put(
            f"/api/organizations/{org_id}",
            headers=auth_headers,
            json={"name": "Updated Name"}
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_delete_organization(self, client: AsyncClient, auth_headers):
        """Test DELETE /api/organizations/{org_id} soft deletes org."""
        create_response = await client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Delete Test", "slug": "delete-test"}
        )
        org_id = create_response.json()["id"]

        response = await client.delete(
            f"/api/organizations/{org_id}",
            headers=auth_headers
        )

        assert response.status_code == 200

        # Verify org no longer accessible
        get_response = await client.get(
            f"/api/organizations/{org_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404


class TestMembershipManagement:
    """Tests for membership management endpoints."""

    @pytest.mark.asyncio
    async def test_list_members(self, client: AsyncClient, auth_headers):
        """Test GET /api/organizations/{org_id}/members lists members."""
        create_response = await client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Members Test", "slug": "members-test"}
        )
        org_id = create_response.json()["id"]

        response = await client.get(
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
        client: AsyncClient,
        auth_headers,
        other_user_id
    ):
        """Test POST /api/organizations/{org_id}/members invites user."""
        create_response = await client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Invite Test", "slug": "invite-test"}
        )
        org_id = create_response.json()["id"]

        response = await client.post(
            f"/api/organizations/{org_id}/members",
            headers=auth_headers,
            json={"user_id": other_user_id, "role": "member"}
        )

        assert response.status_code == 201
        assert response.json()["role"] == "member"

    @pytest.mark.asyncio
    async def test_invite_member_not_admin(
        self,
        client: AsyncClient,
        auth_headers,
        member_user_headers,
        third_user_id
    ):
        """Test member cannot invite other members."""
        create_response = await client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Perm Test", "slug": "perm-test"}
        )
        org_id = create_response.json()["id"]

        # Add member_user as member
        # ... setup code ...

        response = await client.post(
            f"/api/organizations/{org_id}/members",
            headers=member_user_headers,
            json={"user_id": third_user_id, "role": "viewer"}
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_change_member_role(
        self,
        client: AsyncClient,
        auth_headers,
        other_user_id
    ):
        """Test PUT /api/organizations/{org_id}/members/{user_id} changes role."""
        create_response = await client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Role Test", "slug": "role-test"}
        )
        org_id = create_response.json()["id"]

        # Invite member
        await client.post(
            f"/api/organizations/{org_id}/members",
            headers=auth_headers,
            json={"user_id": other_user_id, "role": "member"}
        )

        # Change to admin
        response = await client.put(
            f"/api/organizations/{org_id}/members/{other_user_id}",
            headers=auth_headers,
            json={"role": "admin"}
        )

        assert response.status_code == 200
        assert response.json()["role"] == "admin"

    @pytest.mark.asyncio
    async def test_remove_member(
        self,
        client: AsyncClient,
        auth_headers,
        other_user_id
    ):
        """Test DELETE /api/organizations/{org_id}/members/{user_id} removes member."""
        create_response = await client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Remove Test", "slug": "remove-test"}
        )
        org_id = create_response.json()["id"]

        # Invite member
        await client.post(
            f"/api/organizations/{org_id}/members",
            headers=auth_headers,
            json={"user_id": other_user_id, "role": "member"}
        )

        # Remove member
        response = await client.delete(
            f"/api/organizations/{org_id}/members/{other_user_id}",
            headers=auth_headers
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_cannot_remove_owner(self, client: AsyncClient, auth_headers, test_user_id):
        """Test owner cannot be removed."""
        create_response = await client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Owner Test", "slug": "owner-test"}
        )
        org_id = create_response.json()["id"]

        response = await client.delete(
            f"/api/organizations/{org_id}/members/{test_user_id}",
            headers=auth_headers
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_transfer_ownership(
        self,
        client: AsyncClient,
        auth_headers,
        other_user_id
    ):
        """Test POST /api/organizations/{org_id}/transfer transfers ownership."""
        create_response = await client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Transfer Test", "slug": "transfer-test"}
        )
        org_id = create_response.json()["id"]

        # Invite member
        await client.post(
            f"/api/organizations/{org_id}/members",
            headers=auth_headers,
            json={"user_id": other_user_id, "role": "admin"}
        )

        # Transfer ownership
        response = await client.post(
            f"/api/organizations/{org_id}/transfer",
            headers=auth_headers,
            json={"new_owner_id": other_user_id}
        )

        assert response.status_code == 200
```

### Step 2: Create Pydantic Schemas (api/endpoints/organizations/models.py)

```python
"""Pydantic schemas for Organization endpoints."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class OrganizationCreate(BaseModel):
    """Schema for creating organization."""
    name: str = Field(..., min_length=1, max_length=255)
    slug: Optional[str] = Field(None, max_length=100)
    settings: Optional[dict] = Field(default_factory=dict)


class OrganizationUpdate(BaseModel):
    """Schema for updating organization."""
    name: Optional[str] = Field(None, max_length=255)
    settings: Optional[dict] = None


class MemberResponse(BaseModel):
    """Schema for membership in response."""
    id: str
    user_id: str
    role: str
    joined_at: datetime
    invited_by: Optional[str] = None

    class Config:
        from_attributes = True


class OrganizationResponse(BaseModel):
    """Schema for organization response."""
    id: str
    name: str
    slug: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    settings: dict
    members: List[MemberResponse] = []

    class Config:
        from_attributes = True


class MemberInvite(BaseModel):
    """Schema for inviting member."""
    user_id: str
    role: str = Field(..., pattern="^(admin|member|viewer)$")


class MemberRoleUpdate(BaseModel):
    """Schema for updating member role."""
    role: str = Field(..., pattern="^(admin|member|viewer)$")


class OwnershipTransfer(BaseModel):
    """Schema for transferring ownership."""
    new_owner_id: str
```

### Step 3: Create Organization Endpoints (api/endpoints/organizations/crud.py)

```python
"""Organization CRUD endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth_utils import get_current_active_user
from api.dependencies import get_db_session
from src.giljo_mcp.models.auth import User
from src.giljo_mcp.services.org_service import OrgService

from .models import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
)

router = APIRouter(prefix="/api/organizations", tags=["organizations"])


def get_org_service(
    db: AsyncSession = Depends(get_db_session)
) -> OrgService:
    return OrgService(db)


@router.post("/", response_model=OrganizationResponse, status_code=201)
async def create_organization(
    org_data: OrganizationCreate,
    current_user: User = Depends(get_current_active_user),
    org_service: OrgService = Depends(get_org_service)
):
    """Create new organization with current user as owner."""
    result = await org_service.create_organization(
        name=org_data.name,
        slug=org_data.slug,
        owner_id=current_user.id,
        settings=org_data.settings
    )

    if not result["success"]:
        if "already exists" in result["error"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=result["error"]
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    return result["data"]


@router.get("/", response_model=list[OrganizationResponse])
async def list_organizations(
    current_user: User = Depends(get_current_active_user),
    org_service: OrgService = Depends(get_org_service)
):
    """List all organizations for current user."""
    result = await org_service.get_user_organizations(current_user.id)

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["error"]
        )

    return result["data"]


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: str,
    current_user: User = Depends(get_current_active_user),
    org_service: OrgService = Depends(get_org_service)
):
    """Get organization by ID."""
    # Check membership
    if not await org_service.can_view_org(org_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization"
        )

    result = await org_service.get_organization(org_id)

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    return result["data"]


@router.put("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: str,
    org_data: OrganizationUpdate,
    current_user: User = Depends(get_current_active_user),
    org_service: OrgService = Depends(get_org_service)
):
    """Update organization (owner or admin only)."""
    if not await org_service.can_edit_org(org_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owner or admin can update organization"
        )

    result = await org_service.update_organization(
        org_id=org_id,
        name=org_data.name,
        settings=org_data.settings
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    return result["data"]


@router.delete("/{org_id}")
async def delete_organization(
    org_id: str,
    current_user: User = Depends(get_current_active_user),
    org_service: OrgService = Depends(get_org_service)
):
    """Delete organization (owner only)."""
    if not await org_service.can_delete_org(org_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owner can delete organization"
        )

    result = await org_service.delete_organization(org_id)

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    return {"message": "Organization deleted"}
```

### Step 4: Create Membership Endpoints (api/endpoints/organizations/members.py)

```python
"""Organization membership endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth_utils import get_current_active_user
from api.dependencies import get_db_session
from src.giljo_mcp.models.auth import User
from src.giljo_mcp.services.org_service import OrgService

from .models import MemberInvite, MemberRoleUpdate, MemberResponse, OwnershipTransfer

router = APIRouter(
    prefix="/api/organizations/{org_id}/members",
    tags=["organization-members"]
)


def get_org_service(
    db: AsyncSession = Depends(get_db_session)
) -> OrgService:
    return OrgService(db)


@router.get("/", response_model=list[MemberResponse])
async def list_members(
    org_id: str,
    current_user: User = Depends(get_current_active_user),
    org_service: OrgService = Depends(get_org_service)
):
    """List all members of organization."""
    if not await org_service.can_view_org(org_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization"
        )

    result = await org_service.list_members(org_id)

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["error"]
        )

    return result["data"]


@router.post("/", response_model=MemberResponse, status_code=201)
async def invite_member(
    org_id: str,
    invite_data: MemberInvite,
    current_user: User = Depends(get_current_active_user),
    org_service: OrgService = Depends(get_org_service)
):
    """Invite user to organization (owner or admin only)."""
    if not await org_service.can_manage_members(org_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owner or admin can invite members"
        )

    result = await org_service.invite_member(
        org_id=org_id,
        user_id=invite_data.user_id,
        role=invite_data.role,
        invited_by=current_user.id
    )

    if not result["success"]:
        if "already" in result["error"].lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=result["error"]
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    return result["data"]


@router.put("/{user_id}", response_model=MemberResponse)
async def change_member_role(
    org_id: str,
    user_id: str,
    role_data: MemberRoleUpdate,
    current_user: User = Depends(get_current_active_user),
    org_service: OrgService = Depends(get_org_service)
):
    """Change member's role (owner or admin only)."""
    if not await org_service.can_manage_members(org_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owner or admin can change member roles"
        )

    result = await org_service.change_member_role(
        org_id=org_id,
        user_id=user_id,
        new_role=role_data.role
    )

    if not result["success"]:
        if "owner" in result["error"].lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    return result["data"]


@router.delete("/{user_id}")
async def remove_member(
    org_id: str,
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    org_service: OrgService = Depends(get_org_service)
):
    """Remove member from organization (owner or admin only)."""
    if not await org_service.can_manage_members(org_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owner or admin can remove members"
        )

    result = await org_service.remove_member(org_id=org_id, user_id=user_id)

    if not result["success"]:
        if "owner" in result["error"].lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    return {"message": "Member removed"}


# Transfer endpoint at org level
transfer_router = APIRouter(
    prefix="/api/organizations/{org_id}",
    tags=["organization-transfer"]
)


@transfer_router.post("/transfer")
async def transfer_ownership(
    org_id: str,
    transfer_data: OwnershipTransfer,
    current_user: User = Depends(get_current_active_user),
    org_service: OrgService = Depends(get_org_service)
):
    """Transfer organization ownership (owner only)."""
    if not await org_service.can_delete_org(org_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owner can transfer ownership"
        )

    result = await org_service.transfer_ownership(
        org_id=org_id,
        current_owner_id=current_user.id,
        new_owner_id=transfer_data.new_owner_id
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    return {"message": "Ownership transferred"}
```

### Step 5: Register Routes in app.py

```python
# Add to api/app.py

from api.endpoints.organizations.crud import router as org_router
from api.endpoints.organizations.members import router as members_router
from api.endpoints.organizations.members import transfer_router

app.include_router(org_router)
app.include_router(members_router)
app.include_router(transfer_router)
```

---

## Files to Create/Modify

### NEW Files:
```
□ api/endpoints/organizations/__init__.py (empty)
□ api/endpoints/organizations/models.py (~80 lines)
□ api/endpoints/organizations/crud.py (~130 lines)
□ api/endpoints/organizations/members.py (~150 lines)
□ tests/api/test_organizations_api.py (~300 lines)
```

### MODIFIED Files:
```
□ api/app.py (3 lines - import and include routers)
```

---

## Expected Test Results

```bash
# API tests
pytest tests/api/test_organizations_api.py -v
# Expected: 15+ tests passed (GREEN)

# Full suite (no regressions)
pytest tests/ -v
# Expected: All existing tests pass
```

---

## Verification Checklist

- [ ] Organization CRUD endpoints work
- [ ] Membership management endpoints work
- [ ] Permission checks enforced (owner, admin, member, viewer)
- [ ] Proper HTTP status codes returned
- [ ] Error messages are informative
- [ ] Pydantic validation works
- [ ] All tests pass
- [ ] No regressions in existing endpoints

---

## API Response Examples

### Create Organization
```json
// POST /api/organizations
// Request:
{"name": "Acme Corp", "slug": "acme-corp"}

// Response 201:
{
  "id": "uuid-here",
  "name": "Acme Corp",
  "slug": "acme-corp",
  "is_active": true,
  "created_at": "2026-01-19T10:00:00Z",
  "members": [
    {"id": "...", "user_id": "owner-id", "role": "owner"}
  ]
}
```

### Invite Member
```json
// POST /api/organizations/{org_id}/members
// Request:
{"user_id": "user-uuid", "role": "admin"}

// Response 201:
{
  "id": "membership-uuid",
  "user_id": "user-uuid",
  "role": "admin",
  "joined_at": "2026-01-19T10:00:00Z",
  "invited_by": "owner-uuid"
}
```

---

## Dependencies

- **Depends on:** 0424b (Service Layer)
- **Blocks:** 0424d (Frontend needs API)

---

## Notes for Implementing Agent

1. **Test first** - Write test_organizations_api.py before endpoints
2. **Follow endpoint pattern** - Match existing endpoints (products, projects)
3. **Permission middleware** - Use service permission checks
4. **Proper status codes** - 201 create, 200 success, 4xx errors
5. **Structured logging** - Log all operations

---

## Success Criteria

- [ ] All 15+ API tests pass
- [ ] Organization CRUD works end-to-end
- [ ] Membership management works end-to-end
- [ ] Permission levels enforced correctly
- [ ] Manual testing via curl/Postman works
- [ ] No regressions in other endpoints
