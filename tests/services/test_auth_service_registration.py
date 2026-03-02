"""
Tests for AuthService - User registration and first admin creation.

Split from test_auth_service.py. Contains:
- TestRegisterUser: User registration (admin + first admin flows)
- TestCreateFirstAdmin: First admin account creation

Handover 0731c: Updated for typed service returns (AuthResult, UserInfo).
"""

from datetime import datetime, timezone

import pytest
from passlib.hash import bcrypt
from sqlalchemy import select

from src.giljo_mcp.exceptions import ValidationError
from src.giljo_mcp.models.auth import User
from src.giljo_mcp.models.config import SetupState
from src.giljo_mcp.schemas.service_responses import (
    AuthResult,
    UserInfo,
)


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
    async def test_create_first_admin_success(self, auth_service, db_session):
        """Test creating first admin account returns AuthResult"""
        # Verify no users exist - skip if users already exist from other tests
        stmt = select(User)
        result = await db_session.execute(stmt)
        existing_users = len(result.scalars().all())
        if existing_users > 0:
            pytest.skip(f"Test requires empty database (found {existing_users} users from previous tests)")

        result = await auth_service.create_first_admin(
            username="admin", email="admin@example.com", password="SecureAdmin123!@#", full_name="System Administrator"
        )

        # Typed return: AuthResult with attribute access
        assert isinstance(result, AuthResult)
        assert result.username == "admin"
        assert result.role == "admin"
        assert result.is_active is True
        assert result.token.startswith("eyJ")  # JWT for immediate login

        # Verify SetupState was updated
        stmt_setup = select(SetupState)
        result_setup = await db_session.execute(stmt_setup)
        setup_state = result_setup.scalar_one_or_none()
        assert setup_state is not None
        assert setup_state.first_admin_created is True

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

    @pytest.mark.asyncio
    async def test_create_first_admin_weak_password(self, auth_service, db_session):
        """Test creating first admin with weak password raises ValidationError"""
        # Skip if users already exist (test requires empty database)
        stmt = select(User)
        result = await db_session.execute(stmt)
        existing_users = len(result.scalars().all())
        if existing_users > 0:
            pytest.skip(f"Test requires empty database (found {existing_users} users from previous tests)")

        with pytest.raises(ValidationError) as exc_info:
            await auth_service.create_first_admin(
                username="admin",
                email="admin@example.com",
                password="weak",  # Too short, no complexity
                full_name="Admin",
            )

        assert "password" in str(exc_info.value).lower()
