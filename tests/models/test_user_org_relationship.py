"""
Tests for User.org_id direct relationship to Organization.
Handover 0424f (schema) + 0424j (NOT NULL constraint)

These tests verify:
- User model has org_id column
- org_id is NOT NULL (0424j migration complete)
- User.organization relationship loads Organization
- Users MUST have org_id (NOT NULL enforced)
- Organization.users backref returns users
- org_id FK constraint enforces referential integrity
"""

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from src.giljo_mcp.models.auth import User
from src.giljo_mcp.models.base import generate_uuid
from src.giljo_mcp.models.organizations import Organization


@pytest_asyncio.fixture(scope="function")
async def test_org(db_session, test_tenant_key):
    """Create a test organization for relationship tests."""
    org = Organization(
        name="Test Organization",
        slug=f"test-org-{generate_uuid()[:8]}",  # Unique slug
        tenant_key=test_tenant_key,  # 0424m: Required NOT NULL
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest.mark.asyncio
async def test_user_org_id_column_exists(db_session):
    """Test User model has org_id column."""
    from sqlalchemy import inspect

    inspector = inspect(User)
    column_names = [c.name for c in inspector.columns]

    assert "org_id" in column_names, "User model should have org_id column"


@pytest.mark.asyncio
async def test_user_org_id_nullable(db_session):
    """Test User.org_id is nullable (0424m - required for ondelete=SET NULL)."""
    from sqlalchemy import inspect

    inspector = inspect(User)
    org_id_col = [c for c in inspector.columns if c.name == "org_id"][0]

    # 0424m: Changed to nullable=True to support ondelete="SET NULL"
    assert org_id_col.nullable is True, "org_id should be nullable after 0424m (ondelete=SET NULL)"


@pytest.mark.asyncio
async def test_user_organization_relationship(db_session, test_org, test_tenant_key):
    """Test User.organization relationship loads Organization."""
    # Create user with org_id
    user = User(
        id=generate_uuid(),
        username=f"testuser_{generate_uuid()[:8]}",
        email=f"test_{generate_uuid()[:8]}@example.com",
        password_hash="hashed_password",
        tenant_key=test_tenant_key,
        role="developer",
        org_id=test_org.id,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    # Load user with organization relationship
    stmt = select(User).options(selectinload(User.organization)).where(User.id == user.id)
    result = await db_session.execute(stmt)
    loaded_user = result.scalar_one()

    # Assert relationship works
    assert loaded_user.organization is not None, "User.organization should load Organization"
    assert loaded_user.organization.id == test_org.id, "Relationship should return correct org"
    assert loaded_user.organization.name == test_org.name, "Organization data should be accessible"


@pytest.mark.asyncio
async def test_user_allows_null_org_id(db_session, test_tenant_key):
    """Test User can be created without org_id (0424m - nullable for ondelete=SET NULL)."""
    # 0424m: org_id is nullable to support ondelete="SET NULL"
    user = User(
        id=generate_uuid(),
        username=f"orphan_user_{generate_uuid()[:8]}",
        email=f"orphan_{generate_uuid()[:8]}@example.com",
        password_hash="hashed_password",
        tenant_key=test_tenant_key,
        role="developer",
        is_active=True,
        # No org_id - allowed after 0424m
    )
    db_session.add(user)
    await db_session.commit()  # Should NOT raise

    # User created successfully with NULL org_id
    assert user.org_id is None


@pytest.mark.asyncio
async def test_organization_users_backref(db_session, test_org, test_tenant_key):
    """Test Organization.users backref returns users."""
    # Create 3 users with org_id
    for i in range(3):
        user = User(
            id=generate_uuid(),
            username=f"user{i}_{generate_uuid()[:8]}",
            email=f"user{i}_{generate_uuid()[:8]}@example.com",
            password_hash="hashed_password",
            tenant_key=test_tenant_key,
            role="developer",
            org_id=test_org.id,
            is_active=True,
        )
        db_session.add(user)
    await db_session.commit()

    # Load org with users backref
    stmt = select(Organization).options(selectinload(Organization.users)).where(Organization.id == test_org.id)
    result = await db_session.execute(stmt)
    loaded_org = result.scalar_one()

    # Assert backref works
    assert len(loaded_org.users) == 3, "Organization.users should return all users"
    assert all(u.org_id == test_org.id for u in loaded_org.users), "All users should belong to org"


@pytest.mark.asyncio
async def test_user_org_id_fk_constraint(db_session, test_tenant_key):
    """Test org_id FK constraint enforces referential integrity."""
    # Try to create user with invalid org_id
    user = User(
        id=generate_uuid(),
        username=f"baduser_{generate_uuid()[:8]}",
        email=f"bad_{generate_uuid()[:8]}@example.com",
        password_hash="hashed_password",
        tenant_key=test_tenant_key,
        role="developer",
        org_id="00000000-0000-0000-0000-000000000000",  # Non-existent org
        is_active=True,
    )
    db_session.add(user)

    with pytest.raises(IntegrityError, match="violates foreign key constraint"):
        await db_session.commit()
