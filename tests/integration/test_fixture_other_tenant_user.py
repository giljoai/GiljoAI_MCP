"""Test for other_tenant_user fixture - TDD approach"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.giljo_mcp.models.auth import User


@pytest.mark.asyncio
async def test_other_tenant_user_fixture_exists(other_tenant_user: User, test_user: User):
    """Test that other_tenant_user fixture provides a user from different tenant"""
    # Test that fixture returns a User object
    assert isinstance(other_tenant_user, User)

    # Test that it has different tenant_key from test_user
    assert other_tenant_user.tenant_key != test_user.tenant_key

    # Test that both users have valid attributes
    assert other_tenant_user.id
    assert other_tenant_user.username
    assert other_tenant_user.email
    assert other_tenant_user.tenant_key

    # Test that user is active
    assert other_tenant_user.is_active is True


@pytest.mark.asyncio
async def test_other_tenant_user_has_api_token(other_tenant_user: User):
    """Test that other_tenant_user has an API token for authentication"""
    assert hasattr(other_tenant_user, 'api_token')
    assert other_tenant_user.api_token is not None
    assert len(other_tenant_user.api_token) > 0


@pytest.mark.asyncio
async def test_other_tenant_user_persisted_in_db(
    other_tenant_user: User,
    db_session: AsyncSession
):
    """Test that other_tenant_user is properly persisted in database"""
    from sqlalchemy import select

    # Query the user from database
    stmt = select(User).where(User.id == other_tenant_user.id)
    result = await db_session.execute(stmt)
    db_user = result.scalar_one_or_none()

    # Verify user exists in database
    assert db_user is not None
    assert db_user.id == other_tenant_user.id
    assert db_user.tenant_key == other_tenant_user.tenant_key