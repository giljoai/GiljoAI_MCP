"""
Test admin_user and admin_token fixtures in conftest.py

Verifies that:
- admin_user fixture creates valid admin user
- admin_token fixture creates valid JWT token
- Admin role is correctly set
- Multi-tenant isolation is maintained
"""

import pytest
from sqlalchemy import select

from src.giljo_mcp.models import User


@pytest.mark.asyncio
async def test_admin_user_fixture_creates_valid_user(admin_user, db_manager):
    """Verify admin_user fixture creates a valid admin user."""
    # Assert user object has expected attributes
    assert admin_user is not None
    assert admin_user.username is not None
    assert admin_user.username.startswith("admin_")
    assert admin_user.email is not None
    assert admin_user.email.endswith("@test.com")
    assert admin_user.tenant_key is not None
    assert admin_user.role == "admin"  # CRITICAL: Must be admin role
    assert admin_user.is_active is True

    # Verify user exists in database
    async with db_manager.get_session_async() as session:
        stmt = select(User).where(User.id == admin_user.id)
        result = await session.execute(stmt)
        db_user = result.scalar_one_or_none()

        assert db_user is not None
        assert db_user.username == admin_user.username
        assert db_user.role == "admin"
        assert db_user.is_active is True


@pytest.mark.asyncio
async def test_admin_token_fixture_creates_valid_jwt(admin_token, admin_user):
    """Verify admin_token fixture creates a valid JWT token."""
    from src.giljo_mcp.auth.jwt_manager import JWTManager

    # Assert token is a non-empty string
    assert admin_token is not None
    assert isinstance(admin_token, str)
    assert len(admin_token) > 0

    # Verify token can be verified and contains correct user info
    jwt_manager = JWTManager()
    payload = jwt_manager.verify_token(admin_token)

    assert payload is not None
    assert payload.get("username") == admin_user.username
    assert payload.get("role") == "admin"
    assert payload.get("tenant_key") == admin_user.tenant_key


@pytest.mark.asyncio
async def test_admin_user_has_hashed_password(admin_user):
    """Verify admin_user has properly hashed password."""
    from passlib.hash import bcrypt

    # Password should be hashed, not plaintext
    assert admin_user.password_hash is not None
    assert admin_user.password_hash != "admin_password"

    # Verify password hash is valid bcrypt hash
    assert bcrypt.verify("admin_password", admin_user.password_hash)


@pytest.mark.asyncio
async def test_admin_user_tenant_isolation(admin_user, db_manager):
    """Verify admin_user maintains multi-tenant isolation."""
    from src.giljo_mcp.tenant import TenantManager

    # Tenant key should be generated properly
    assert admin_user.tenant_key is not None
    assert len(admin_user.tenant_key) > 0

    # Create a second admin user - should have DIFFERENT tenant key
    from uuid import uuid4

    from passlib.hash import bcrypt

    unique_id = uuid4().hex[:8]
    tenant_key = TenantManager.generate_tenant_key(f"admin2_{unique_id}")

    async with db_manager.get_session_async() as session:
        user2 = User(
            username=f"admin2_{unique_id}",
            password_hash=bcrypt.hash("admin_password"),
            email=f"admin2_{unique_id}@test.com",
            tenant_key=tenant_key,
            role="admin",
            is_active=True,
        )
        session.add(user2)
        await session.commit()
        await session.refresh(user2)

        # Tenant keys should be different (multi-tenant isolation)
        assert user2.tenant_key != admin_user.tenant_key


@pytest.mark.asyncio
async def test_admin_token_can_authenticate_api_request(api_client, admin_token):
    """Verify admin_token can authenticate API requests."""
    # Use admin token in cookie header (matches auth_headers pattern)
    headers = {"Cookie": f"access_token={admin_token}"}

    # Try accessing an endpoint that requires authentication
    # Using /api/v1/settings as a test endpoint (admin-only in settings_api.py)
    response = await api_client.get("/api/v1/settings", headers=headers)

    # Should NOT get 401 Unauthorized (token is valid)
    assert response.status_code != 401
