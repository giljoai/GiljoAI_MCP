"""
Tests for User.org_id migration from OrgMembership.
"""

import pytest
from sqlalchemy import select, text

from src.giljo_mcp.models import Organization, OrgMembership, User


@pytest.mark.asyncio
async def test_user_org_id_relationship_works(db_session):
    """Test User.org_id relationship works correctly after migration.

    Post-migration test: Verifies that users created with org_id
    have proper relationship to organization.
    """
    # Create org (0424m: tenant_key required)
    tenant_key = "test_tenant_migration_123"
    org = Organization(
        name="Test Org",
        slug="test-org-migration-123",
        tenant_key=tenant_key,  # 0424m: Required NOT NULL
        is_active=True,
    )
    db_session.add(org)
    await db_session.flush()

    # Create user WITH org_id (required after migration)
    user = User(
        username="testuser_migration",
        email="test_migration@example.com",
        tenant_key=tenant_key,
        org_id=org.id,  # Now required
    )
    db_session.add(user)
    await db_session.flush()

    # Create membership (0424m: tenant_key required)
    membership = OrgMembership(
        org_id=org.id,
        user_id=user.id,
        role="owner",
        tenant_key=tenant_key,  # 0424m: Required NOT NULL
        is_active=True,
    )
    db_session.add(membership)
    await db_session.commit()

    # Reload user
    await db_session.refresh(user)

    # Assert org_id is set correctly
    assert user.org_id == org.id
    assert user.org_id is not None


@pytest.mark.asyncio
async def test_migration_does_not_overwrite_existing_org_id(db_session):
    """Test migration does not overwrite already-set org_id."""
    # Create first org (0424m: tenant_key required)
    tenant_key = "test_tenant_overwrite"
    first_org = Organization(
        name="First Org",
        slug="first-org-123",
        tenant_key=tenant_key,  # 0424m: Required NOT NULL
        is_active=True,
    )
    db_session.add(first_org)
    await db_session.flush()

    # Create another org (0424m: tenant_key required)
    other_org = Organization(
        name="Other Org",
        slug="other-org-456",
        tenant_key=tenant_key,  # 0424m: Required NOT NULL
        is_active=True,
    )
    db_session.add(other_org)
    await db_session.flush()

    # Create user WITH org_id already set
    user = User(
        username="existing",
        email="existing@example.com",
        tenant_key=tenant_key,
        org_id=first_org.id,  # Already set
    )
    db_session.add(user)
    await db_session.flush()

    # Create membership to different org (0424m: tenant_key required)
    membership = OrgMembership(
        org_id=other_org.id,
        user_id=user.id,
        role="member",
        tenant_key=tenant_key,  # 0424m: Required NOT NULL
        is_active=True,
    )
    db_session.add(membership)
    await db_session.commit()

    original_org_id = user.org_id

    # Run migration logic
    stmt = text("""
        UPDATE users
        SET org_id = om.org_id
        FROM org_memberships om
        WHERE users.id = om.user_id
        AND users.org_id IS NULL
    """)
    await db_session.execute(stmt)
    await db_session.commit()

    # Reload user
    await db_session.refresh(user)

    # Assert org_id was NOT changed
    assert user.org_id == original_org_id


@pytest.mark.asyncio
async def test_verify_no_null_org_ids_after_migration(db_session):
    """Test verification query finds no NULL org_ids."""
    # Run verification query
    stmt = select(User).where(User.org_id.is_(None))
    result = await db_session.execute(stmt)
    null_org_users = result.scalars().all()

    # Assert no users have NULL org_id
    assert len(null_org_users) == 0


@pytest.mark.asyncio
async def test_nullable_org_id_allows_creation_without_org(db_session):
    """Test User.org_id allows NULL (0424m - required for ondelete=SET NULL)."""
    # 0424m: org_id is nullable to support ondelete="SET NULL"
    # Users CAN be created without org_id (edge case for orphaned users)
    user = User(
        username="orphan",
        email="orphan@example.com",
        tenant_key="test_tenant",
        # No org_id - allowed after 0424m
    )
    db_session.add(user)
    await db_session.commit()  # Should NOT raise

    # User created successfully with NULL org_id
    assert user.org_id is None
