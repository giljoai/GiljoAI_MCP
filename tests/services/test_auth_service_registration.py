"""
Tests for AuthService - User registration and first admin creation.

Split from test_auth_service.py. Contains:
- TestRegisterUser: User registration (admin + first admin flows)
- TestCreateFirstAdmin: First admin account creation

Handover 0731c: Updated for typed service returns (AuthResult, UserInfo).
"""

import pytest
from passlib.hash import bcrypt
from sqlalchemy import select

from src.giljo_mcp.exceptions import ValidationError
from src.giljo_mcp.models.auth import User
from src.giljo_mcp.schemas.service_responses import UserInfo


# Test Cases


class TestRegisterUser:
    """Tests for register_user method - returns UserInfo"""

    @pytest.mark.asyncio
    async def test_register_user_success(self, auth_service, auth_user_with_password, db_session):
        """Test registering new user returns UserInfo"""
        admin_user, _ = auth_user_with_password

        result = await auth_service.register_user(
            username="newuser",
            email="new@example.com",
            password="NewPassword123!",
            role="developer",
            requesting_admin_id=admin_user.id,
        )

        # Typed return: UserInfo with attribute access
        assert isinstance(result, UserInfo)
        assert result.username == "newuser"
        assert result.email == "new@example.com"
        assert result.role == "developer"
        assert result.tenant_key is not None  # Auto-generated per-user tenant

        # Verify password was hashed
        stmt = select(User).where(User.username == "newuser")
        result_db = await db_session.execute(stmt)
        new_user = result_db.scalar_one()
        assert new_user.password_hash != "NewPassword123!"
        assert bcrypt.verify("NewPassword123!", new_user.password_hash)

    @pytest.mark.asyncio
    async def test_register_user_duplicate_username(self, auth_service, auth_user_with_password):
        """Test registering user with existing username raises ValidationError"""
        admin_user, _ = auth_user_with_password

        with pytest.raises(ValidationError) as exc_info:
            await auth_service.register_user(
                username=admin_user.username,  # Duplicate
                email="different@example.com",
                password="Password123!",
                role="developer",
                requesting_admin_id=admin_user.id,
            )

        assert "already exists" in str(exc_info.value).lower()


class TestCreateFirstAdmin:
    """Tests for create_first_admin method - returns AuthResult"""

    @pytest.mark.asyncio
    async def test_create_first_admin_fails_when_users_exist(self, auth_service, auth_user_with_password):
        """Test creating first admin fails when users already exist"""

        with pytest.raises(ValidationError) as exc_info:
            await auth_service.create_first_admin(
                username="secondadmin",
                email="second@example.com",
                password="SecureAdmin123!@#",
                full_name="Second Admin",
            )

        assert "already exists" in str(exc_info.value).lower() or "Administrator account already exists" in str(
            exc_info.value
        )
