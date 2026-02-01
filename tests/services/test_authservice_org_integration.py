"""
Tests for AuthService Organization Integration (Handover 0424g).

This test suite follows TDD discipline (Red → Green → Refactor):
1. Tests written FIRST (this file) - RED PHASE
2. All tests must FAIL initially
3. Implementation makes tests pass - GREEN PHASE
4. Refactor for quality - REFACTOR PHASE

Test Coverage (Handover 0424g):
- _create_default_organization returns org_id
- _create_first_admin_impl creates org FIRST, sets user.org_id
- _register_user_impl accepts org_id parameter
- create_user_in_org creates users within admin's organization
- Permission checks for create_user_in_org (owner/admin only)
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from passlib.hash import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.giljo_mcp.models.auth import User
from src.giljo_mcp.models.organizations import Organization, OrgMembership
from src.giljo_mcp.services.auth_service import AuthService
from src.giljo_mcp.exceptions import AuthorizationError, ValidationError


# Fixtures


@pytest_asyncio.fixture
async def auth_service(db_manager, db_session):
    """Create AuthService instance for testing with shared session"""
    return AuthService(
        db_manager=db_manager,
        websocket_manager=None,  # No WebSocket in tests
        session=db_session  # SHARED SESSION for test transaction isolation
    )


@pytest_asyncio.fixture
async def test_org(db_session):
    """Create test organization"""
    org = Organization(
        id="test-org-001",
        name="Test Organization",
        slug="test-organization",
        tenant_key="test_tenant_001",  # 0424m: Required NOT NULL
        is_active=True,
        settings={}
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest_asyncio.fixture
async def test_admin_user(db_session, test_org):
    """Create admin user with org_id set and owner membership"""
    password = "Admin1234!@#$"
    admin = User(
        id="test-admin-001",
        username="testadmin",
        email="admin@example.com",
        full_name="Test Admin",
        password_hash=bcrypt.hash(password),
        role="admin",
        tenant_key="test_tenant_001",
        org_id=test_org.id,  # Direct FK to organization
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(admin)
    await db_session.flush()

    # Create owner membership (0424m: tenant_key required)
    owner_membership = OrgMembership(
        org_id=test_org.id,
        user_id=admin.id,
        role="owner",
        tenant_key="test_tenant_001",  # 0424m: Required NOT NULL
        is_active=True
    )
    db_session.add(owner_membership)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin, password


@pytest_asyncio.fixture
async def test_member_user(db_session, test_org):
    """Create member user for permission tests"""
    password = "Member1234!@#$"
    member = User(
        id="test-member-001",
        username="testmember",
        email="member@example.com",
        full_name="Test Member",
        password_hash=bcrypt.hash(password),
        role="developer",
        tenant_key="test_tenant_002",
        org_id=test_org.id,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(member)
    await db_session.flush()

    # Create member membership (0424m: tenant_key required)
    member_membership = OrgMembership(
        org_id=test_org.id,
        user_id=member.id,
        role="member",
        tenant_key="test_tenant_001",  # 0424m: Required NOT NULL
        is_active=True
    )
    db_session.add(member_membership)
    await db_session.commit()
    await db_session.refresh(member)
    return member, password


# RED PHASE: Tests written first (expected to FAIL)


@pytest.mark.asyncio
async def test_create_default_organization_returns_org_id(auth_service, db_session):
    """
    Test that _create_default_organization returns org_id as string.

    Expected behavior (Handover 0424g):
    - Creates organization with custom name
    - Returns org.id as UUID string
    - Does NOT create membership (caller handles that)
    """
    # Call method with new signature
    org_id = await auth_service._create_default_organization(
        session=db_session,
        tenant_key="test_tenant_999",
        org_name="Custom Workspace"
    )

    # Verify returns UUID string
    assert isinstance(org_id, str)
    assert len(org_id) == 36  # UUID format

    # Verify organization created in database
    stmt = select(Organization).where(Organization.id == org_id)
    result = await db_session.execute(stmt)
    org = result.scalar_one_or_none()

    assert org is not None
    assert org.name == "Custom Workspace"
    assert org.is_active is True

    # Verify NO membership created (caller's responsibility)
    membership_stmt = select(OrgMembership).where(OrgMembership.org_id == org_id)
    membership_result = await db_session.execute(membership_stmt)
    membership = membership_result.scalar_one_or_none()

    assert membership is None  # No membership created by this method


@pytest.mark.asyncio
async def test_create_first_admin_sets_org_id(auth_service, db_session):
    """
    Test that _create_first_admin_impl creates org FIRST, then sets user.org_id.

    Expected behavior (Handover 0424g):
    - Creates organization FIRST
    - Creates user WITH org_id set
    - Creates owner membership
    - Organization created before user (org-first pattern)
    """
    # Clear all users to simulate fresh install (first admin check)
    await db_session.execute(User.__table__.delete())
    await db_session.commit()

    # Create first admin
    result = await auth_service._create_first_admin_impl(
        session=db_session,
        username="firstadmin",
        email="first@example.com",
        password="FirstAdmin1234!@#$",
        full_name="First Administrator"
    )

    # Verify user created with org_id set
    user_id = result["id"]
    stmt = select(User).where(User.id == user_id).options(selectinload(User.organization))
    user_result = await db_session.execute(stmt)
    user = user_result.scalar_one()

    assert user.org_id is not None
    assert len(user.org_id) == 36  # UUID format

    # Verify organization exists
    org_stmt = select(Organization).where(Organization.id == user.org_id)
    org_result = await db_session.execute(org_stmt)
    org = org_result.scalar_one()

    assert org is not None
    assert org.name == "My Organization"  # Default workspace name per implementation

    # Verify owner membership created
    membership_stmt = (
        select(OrgMembership)
        .where(OrgMembership.org_id == user.org_id)
        .where(OrgMembership.user_id == user.id)
    )
    membership_result = await db_session.execute(membership_stmt)
    membership = membership_result.scalar_one()

    assert membership.role == "owner"
    assert membership.is_active is True


@pytest.mark.asyncio
async def test_register_user_sets_org_id(auth_service, db_session, test_admin_user, test_org):
    """
    Test that _register_user_impl accepts org_id parameter and sets user.org_id.

    Expected behavior (Handover 0424g):
    - Accepts org_id and org_role parameters
    - Sets user.org_id if provided
    - Creates membership with specified role
    """
    admin, _ = test_admin_user

    # Register user with org_id
    result = await auth_service._register_user_impl(
        session=db_session,
        username="newuser",
        email="newuser@example.com",
        password="NewUser1234!@#$",
        role="developer",
        requesting_admin_id=admin.id,
        org_id=test_org.id,
        org_role="member"
    )

    # Verify user created with org_id set
    user_id = result["id"]
    stmt = select(User).where(User.id == user_id)
    user_result = await db_session.execute(stmt)
    user = user_result.scalar_one()

    assert user.org_id == test_org.id

    # Verify membership created with specified role
    membership_stmt = (
        select(OrgMembership)
        .where(OrgMembership.org_id == test_org.id)
        .where(OrgMembership.user_id == user.id)
    )
    membership_result = await db_session.execute(membership_stmt)
    membership = membership_result.scalar_one()

    assert membership.role == "member"
    assert membership.is_active is True


@pytest.mark.asyncio
async def test_create_user_in_org_by_admin(auth_service, db_session, test_admin_user, test_org):
    """
    Test that create_user_in_org creates users within admin's organization.

    Expected behavior (Handover 0424g):
    - Admin can create users in their organization
    - New user gets admin's org_id
    - Membership created with specified role
    """
    admin, _ = test_admin_user

    # Admin creates new user in their organization
    result = await auth_service.create_user_in_org(
        session=db_session,
        admin_user_id=admin.id,
        username="orguser",
        email="orguser@example.com",
        role="member",
        initial_password="OrgUser1234!@#$"
    )

    # Verify user created with admin's org_id
    assert result["username"] == "orguser"
    assert result["email"] == "orguser@example.com"

    user_id = result["id"]
    stmt = select(User).where(User.id == user_id)
    user_result = await db_session.execute(stmt)
    user = user_result.scalar_one()

    assert user.org_id == test_org.id  # Same org as admin

    # Verify membership created
    membership_stmt = (
        select(OrgMembership)
        .where(OrgMembership.org_id == test_org.id)
        .where(OrgMembership.user_id == user.id)
    )
    membership_result = await db_session.execute(membership_stmt)
    membership = membership_result.scalar_one()

    assert membership.role == "member"
    assert membership.is_active is True


@pytest.mark.asyncio
async def test_create_user_in_org_requires_admin_role(auth_service, db_session, test_member_user, test_org):
    """
    Test that create_user_in_org requires owner/admin membership role.

    Expected behavior (Handover 0424g):
    - Member users cannot create users
    - Raises PermissionDeniedError for non-admin roles
    """
    member, _ = test_member_user

    # Member tries to create user (should fail)
    with pytest.raises(AuthorizationError) as exc_info:
        await auth_service.create_user_in_org(
            session=db_session,
            admin_user_id=member.id,
            username="unauthorizeduser",
            email="unauthorized@example.com",
            role="member",
            initial_password="Unauthorized1234!@#$"
        )

    # Verify error message mentions permission requirement
    assert "owner" in str(exc_info.value).lower() or "admin" in str(exc_info.value).lower()

    # Verify no user created
    stmt = select(User).where(User.username == "unauthorizeduser")
    result = await db_session.execute(stmt)
    user = result.scalar_one_or_none()

    assert user is None
