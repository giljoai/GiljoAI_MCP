"""Tests for Organization and OrgMembership models.

Handover 0424a: RED -> GREEN -> REFACTOR cycle for organization hierarchy.

These tests verify:
- Organization creation with required fields
- Slug uniqueness constraint
- OrgMembership user-org-role junction
- Role validation constraint
- Relationship navigation
- User uniqueness per org constraint
"""

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.giljo_mcp.models.auth import User
from src.giljo_mcp.models.base import generate_uuid


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session, test_tenant_key):
    """Create a test user for organization membership tests."""
    from src.giljo_mcp.models.organizations import Organization

    # Create org first (0424m: tenant_key required)
    org = Organization(
        name=f"Test Org {generate_uuid()[:8]}",
        slug=f"test-org-{generate_uuid()[:8]}",
        tenant_key=test_tenant_key,
        is_active=True,
    )
    db_session.add(org)
    await db_session.flush()

    user = User(
        id=generate_uuid(),
        tenant_key=test_tenant_key,
        username=f"test_user_{generate_uuid()[:8]}",
        email=f"test_{generate_uuid()[:8]}@example.com",
        password_hash="hashed_password",
        role="developer",
        is_active=True,
        org_id=org.id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_organization_creation(db_session, test_tenant_key):
    """Test Organization can be created with required fields."""
    from src.giljo_mcp.models.organizations import Organization

    org = Organization(name="Test Organization", slug="test-org", tenant_key=test_tenant_key)
    db_session.add(org)
    await db_session.commit()

    assert org.id is not None
    assert org.name == "Test Organization"
    assert org.slug == "test-org"
    assert org.is_active is True  # Default


@pytest.mark.asyncio
async def test_organization_slug_unique(db_session, test_tenant_key):
    """Test Organization slug must be unique."""
    from src.giljo_mcp.models.organizations import Organization

    org1 = Organization(name="Org 1", slug="same-slug", tenant_key=test_tenant_key)
    org2 = Organization(name="Org 2", slug="same-slug", tenant_key=test_tenant_key)

    db_session.add(org1)
    await db_session.commit()

    db_session.add(org2)
    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_org_membership_creation(db_session, test_user, test_tenant_key):
    """Test OrgMembership links user to organization with role."""
    from src.giljo_mcp.models.organizations import Organization, OrgMembership

    org = Organization(name="Test Org", slug="test-membership", tenant_key=test_tenant_key)
    db_session.add(org)
    await db_session.commit()

    membership = OrgMembership(org_id=org.id, user_id=test_user.id, role="owner", tenant_key=test_tenant_key)
    db_session.add(membership)
    await db_session.commit()

    assert membership.id is not None
    assert membership.org_id == org.id
    assert membership.user_id == test_user.id
    assert membership.role == "owner"
    assert membership.is_active is True


@pytest.mark.asyncio
async def test_org_membership_role_constraint(db_session, test_user, test_tenant_key):
    """Test OrgMembership role must be valid."""
    from src.giljo_mcp.models.organizations import Organization, OrgMembership

    org = Organization(name="Test Org", slug="test-role", tenant_key=test_tenant_key)
    db_session.add(org)
    await db_session.commit()

    membership = OrgMembership(
        org_id=org.id,
        user_id=test_user.id,
        role="invalid_role",  # Not in allowed roles
        tenant_key=test_tenant_key,
    )
    db_session.add(membership)

    with pytest.raises(IntegrityError):  # CheckConstraint violation
        await db_session.commit()


@pytest.mark.asyncio
async def test_org_members_relationship(db_session, test_user, test_tenant_key):
    """Test Organization.members relationship returns memberships."""
    from sqlalchemy.orm import selectinload

    from src.giljo_mcp.models.organizations import Organization, OrgMembership

    org = Organization(name="Test Org", slug="test-rel", tenant_key=test_tenant_key)
    db_session.add(org)
    await db_session.commit()

    membership = OrgMembership(org_id=org.id, user_id=test_user.id, role="admin", tenant_key=test_tenant_key)
    db_session.add(membership)
    await db_session.commit()

    # Use selectinload to eagerly load the relationship in async context
    stmt = select(Organization).where(Organization.id == org.id).options(selectinload(Organization.members))
    result = await db_session.execute(stmt)
    org_with_members = result.scalar_one()

    assert len(org_with_members.members) == 1
    assert org_with_members.members[0].role == "admin"


@pytest.mark.asyncio
async def test_user_unique_per_org(db_session, test_user, test_tenant_key):
    """Test user can only have one membership per org."""
    from src.giljo_mcp.models.organizations import Organization, OrgMembership

    org = Organization(name="Test Org", slug="test-unique", tenant_key=test_tenant_key)
    db_session.add(org)
    await db_session.commit()

    membership1 = OrgMembership(org_id=org.id, user_id=test_user.id, role="owner", tenant_key=test_tenant_key)
    db_session.add(membership1)
    await db_session.commit()

    membership2 = OrgMembership(
        org_id=org.id,
        user_id=test_user.id,
        role="admin",  # Same user, same org, different role
        tenant_key=test_tenant_key,
    )
    db_session.add(membership2)

    with pytest.raises(IntegrityError):  # UniqueConstraint violation
        await db_session.commit()
