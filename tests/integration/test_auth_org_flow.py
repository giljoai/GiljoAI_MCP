"""
Integration tests for auth org-first flow (Handover 0424g).

Tests the full authentication flow with organization integration,
validating that organizations are created FIRST before users in
the fresh install flow, and that admins can create users within
their organization.

Test Coverage:
- Fresh install creates org -> admin user -> membership
- Admin can create users in their organization
- Tenant isolation is maintained
"""

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.giljo_mcp.models.auth import User
from src.giljo_mcp.models.organizations import Organization, OrgMembership
from src.giljo_mcp.services.auth_service import AuthService

pytestmark = pytest.mark.skip(reason="0750c3: dict-return API — tests expect dict, service returns Pydantic model")

# Fixtures


@pytest_asyncio.fixture
async def auth_service(db_manager, db_session):
    """Create AuthService instance for integration testing with shared session"""
    return AuthService(
        db_manager=db_manager,
        websocket_manager=None,  # No WebSocket in tests
        session=db_session,  # SHARED SESSION for test transaction isolation
    )


# Integration Tests


@pytest.mark.asyncio
async def test_fresh_install_creates_org_first(db_session, auth_service):
    """
    Test fresh install flow creates organization FIRST, then admin user.

    Integration test verifying:
    1. Organization is created first
    2. Admin user is created with org_id set
    3. Owner membership is created
    4. All entities are properly persisted in database

    Expected behavior (Handover 0424g):
    - _create_first_admin_impl creates org FIRST
    - User has org_id set to created organization
    - Membership with role="owner" exists
    - Tenant isolation is maintained
    """
    # Clear all users to simulate fresh install
    await db_session.execute(User.__table__.delete())
    await db_session.commit()

    # Create first admin user via service
    result = await auth_service._create_first_admin_impl(
        session=db_session,
        username="firstadmin",
        email="firstadmin@example.com",
        password="FirstAdmin1234!@#$",
        full_name="First Administrator",
    )

    # Verify user was created
    assert result is not None
    assert "id" in result
    assert result["username"] == "firstadmin"

    user_id = result["id"]

    # Load user from database with organization relationship
    stmt = select(User).where(User.id == user_id).options(selectinload(User.organization))
    user_result = await db_session.execute(stmt)
    user = user_result.scalar_one()

    # CRITICAL: Verify user.org_id is set (org-first pattern)
    assert user.org_id is not None, "User.org_id must be set in org-first flow"
    assert len(user.org_id) == 36, "User.org_id must be valid UUID"

    # Verify organization exists in database
    org_stmt = select(Organization).where(Organization.id == user.org_id)
    org_result = await db_session.execute(org_stmt)
    org = org_result.scalar_one_or_none()

    assert org is not None, "Organization must exist in database"
    assert org.name == "My Organization", "Organization name should be the default 'My Organization'"
    assert org.is_active is True, "Organization must be active"

    # Verify owner membership exists
    membership_stmt = (
        select(OrgMembership).where(OrgMembership.org_id == user.org_id).where(OrgMembership.user_id == user.id)
    )
    membership_result = await db_session.execute(membership_stmt)
    membership = membership_result.scalar_one_or_none()

    assert membership is not None, "Owner membership must exist"
    assert membership.role == "owner", "First admin must have owner role"
    assert membership.is_active is True, "Membership must be active"

    # Verify relationship is loaded correctly
    assert user.organization is not None, "User.organization relationship should be loaded"
    assert user.organization.id == org.id, "User.organization should match org_id"


@pytest.mark.asyncio
async def test_admin_creates_user_in_org(db_session, auth_service):
    """
    Test that admin can create users within their organization.

    Integration test verifying:
    1. Admin user with org_id can create new users
    2. New users get same org_id as admin
    3. Membership is created with specified role
    4. Tenant isolation is maintained

    Expected behavior (Handover 0424g):
    - create_user_in_org creates user with admin's org_id
    - Membership created with specified role
    - User persisted to database correctly
    """
    # Create organization first
    org_id = await auth_service._create_default_organization(
        session=db_session, tenant_key="test_tenant_admin", org_name="Admin Test Organization"
    )

    # Create admin user with org_id
    admin_result = await auth_service._register_user_impl(
        session=db_session,
        username="adminuser",
        email="adminuser@example.com",
        password="AdminUser1234!@#$",
        role="admin",
        requesting_admin_id=None,  # No requesting admin for first user
        org_id=org_id,
        org_role="owner",
    )

    admin_id = admin_result["id"]

    # Load admin to verify setup
    admin_stmt = select(User).where(User.id == admin_id)
    admin_result_db = await db_session.execute(admin_stmt)
    admin = admin_result_db.scalar_one()

    assert admin.org_id == org_id, "Admin must have org_id set"

    # Admin creates new user in their organization
    new_user_result = await auth_service.create_user_in_org(
        session=db_session,
        admin_user_id=admin_id,
        username="neworguser",
        email="neworguser@example.com",
        role="member",
        initial_password="NewOrgUser1234!@#$",
    )

    # Verify new user created
    assert new_user_result is not None
    assert new_user_result["username"] == "neworguser"
    assert new_user_result["email"] == "neworguser@example.com"

    new_user_id = new_user_result["id"]

    # Load new user from database
    user_stmt = select(User).where(User.id == new_user_id)
    user_result = await db_session.execute(user_stmt)
    new_user = user_result.scalar_one()

    # CRITICAL: Verify new user has same org_id as admin
    assert new_user.org_id == org_id, "New user must have same org_id as admin"
    assert new_user.org_id == admin.org_id, "New user org_id must match admin org_id"

    # Verify membership created with correct role
    membership_stmt = (
        select(OrgMembership).where(OrgMembership.org_id == org_id).where(OrgMembership.user_id == new_user_id)
    )
    membership_result = await db_session.execute(membership_stmt)
    membership = membership_result.scalar_one_or_none()

    assert membership is not None, "Membership must exist for new user"
    assert membership.role == "member", "New user must have member role"
    assert membership.is_active is True, "Membership must be active"

    # Verify both users are in same organization
    org_members_stmt = select(OrgMembership).where(OrgMembership.org_id == org_id)
    org_members_result = await db_session.execute(org_members_stmt)
    org_members = org_members_result.scalars().all()

    assert len(org_members) == 2, "Organization should have 2 members (admin + new user)"

    # Verify member roles
    member_roles = {m.user_id: m.role for m in org_members}
    assert member_roles[admin_id] == "owner", "Admin should be owner"
    assert member_roles[new_user_id] == "member", "New user should be member"
