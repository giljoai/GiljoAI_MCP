"""
Tests for User.org_id migration from OrgMembership.
"""
import pytest
from sqlalchemy import select, text

from src.giljo_mcp.models import User, Organization, OrgMembership


@pytest.mark.asyncio
async def test_user_org_id_relationship_works(db_session):
    """Test User.org_id relationship works correctly after migration.

    Post-migration test: Verifies that users created with org_id
    have proper relationship to organization.
    """
    # Create org
    org = Organization(
        name="Test Org",
        slug="test-org-migration-123",
        is_active=True
    )
    db_session.add(org)
    await db_session.flush()

    # Create user WITH org_id (required after migration)
    user = User(
        username="testuser_migration",
        email="test_migration@example.com",
        tenant_key="test_tenant",
        org_id=org.id  # Now required
    )
    db_session.add(user)
    await db_session.flush()

    # Create membership
    membership = OrgMembership(
        org_id=org.id,
        user_id=user.id,
        role="owner",
        is_active=True
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
    # Create first org
    first_org = Organization(
        name="First Org",
        slug="first-org-123",
        is_active=True
    )
    db_session.add(first_org)
    await db_session.flush()

    # Create another org
    other_org = Organization(
        name="Other Org",
        slug="other-org-456",
        is_active=True
    )
    db_session.add(other_org)
    await db_session.flush()

    # Create user WITH org_id already set
    user = User(
        username="existing",
        email="existing@example.com",
        tenant_key="test_tenant",
        org_id=first_org.id  # Already set
    )
    db_session.add(user)
    await db_session.flush()

    # Create membership to different org
    membership = OrgMembership(
        org_id=other_org.id,
        user_id=user.id,
        role="member",
        is_active=True
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
async def test_not_null_constraint_enforced(db_session):
    """Test User.org_id NOT NULL constraint prevents creation without org."""
    from sqlalchemy.exc import IntegrityError

    # Try to create user without org_id
    user = User(
        username="orphan",
        email="orphan@example.com",
        tenant_key="test_tenant"
        # No org_id
    )
    db_session.add(user)

    with pytest.raises(IntegrityError, match="null value"):
        await db_session.commit()
