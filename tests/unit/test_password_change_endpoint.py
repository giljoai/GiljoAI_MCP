"""
Unit tests for password change endpoint (Phase 2 unified auth)

Tests password change flow from default admin/admin to secure password.
Following TDD principles - tests written BEFORE implementation.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.hash import bcrypt

from src.giljo_mcp.models import User, SetupState


class TestPasswordChangeEndpoint:
    """Test suite for /auth/change-password endpoint"""

    @pytest.fixture
    async def db_session(self):
        """Create test database session"""
        from src.giljo_mcp.database import DatabaseManager

        db_manager = DatabaseManager.get_instance()
        async with db_manager.get_session_async() as session:
            yield session
            await session.rollback()

    @pytest.fixture
    async def default_admin_user(self, db_session):
        """Create default admin user with admin/admin credentials"""
        user = User(
            username='admin',
            password_hash=bcrypt.hash('admin'),
            role='admin',
            tenant_key='default',
            is_active=True
        )
        db_session.add(user)

        # Create setup state with default_password_active
        setup_state = SetupState(
            tenant_key='default',
            database_initialized=False,
            meta_data={'default_password_active': True}
        )
        db_session.add(setup_state)

        await db_session.commit()
        await db_session.refresh(user)
        return user

    @pytest.mark.asyncio
    async def test_change_password_with_valid_data(self, db_session, default_admin_user):
        """Test password change with valid data"""
        from api.endpoints.auth import change_password, PasswordChangeRequest

        request = PasswordChangeRequest(
            current_password='admin',
            new_password='NewSecurePassword123!',
            confirm_password='NewSecurePassword123!'
        )

        # Mock current user
        with patch('api.endpoints.auth.get_current_active_user', return_value=default_admin_user):
            response = await change_password(request, db=db_session)

        # Should succeed
        assert 'token' in response
        assert 'message' in response

        # Password should be updated
        from sqlalchemy import select
        stmt = select(User).where(User.username == 'admin')
        result = await db_session.execute(stmt)
        user = result.scalar_one()

        # Old password should NOT work
        assert not bcrypt.verify('admin', user.password_hash)

        # New password should work
        assert bcrypt.verify('NewSecurePassword123!', user.password_hash)

    @pytest.mark.asyncio
    async def test_change_password_sets_default_password_inactive(
        self, db_session, default_admin_user
    ):
        """Test that password change sets default_password_active to False"""
        from api.endpoints.auth import change_password, PasswordChangeRequest

        request = PasswordChangeRequest(
            current_password='admin',
            new_password='NewSecurePassword123!',
            confirm_password='NewSecurePassword123!'
        )

        with patch('api.endpoints.auth.get_current_active_user', return_value=default_admin_user):
            await change_password(request, db=db_session)

        # Check setup state
        from sqlalchemy import select
        stmt = select(SetupState).where(SetupState.tenant_key == 'default')
        result = await db_session.execute(stmt)
        setup_state = result.scalar_one()

        assert setup_state.meta_data.get('default_password_active') is False

    @pytest.mark.asyncio
    async def test_change_password_returns_jwt_token(self, db_session, default_admin_user):
        """Test that password change returns JWT token for immediate login"""
        from api.endpoints.auth import change_password, PasswordChangeRequest

        request = PasswordChangeRequest(
            current_password='admin',
            new_password='NewSecurePassword123!',
            confirm_password='NewSecurePassword123!'
        )

        with patch('api.endpoints.auth.get_current_active_user', return_value=default_admin_user):
            response = await change_password(request, db=db_session)

        # Should return a token
        assert 'token' in response
        assert isinstance(response['token'], str)
        assert len(response['token']) > 0

        # Token should be valid
        from src.giljo_mcp.auth.jwt_manager import JWTManager
        payload = JWTManager.verify_token(response['token'])
        assert payload is not None
        assert payload['username'] == 'admin'

    @pytest.mark.asyncio
    async def test_change_password_with_wrong_current_password(
        self, db_session, default_admin_user
    ):
        """Test that wrong current password is rejected"""
        from api.endpoints.auth import change_password, PasswordChangeRequest

        request = PasswordChangeRequest(
            current_password='wrong_password',  # Incorrect
            new_password='NewSecurePassword123!',
            confirm_password='NewSecurePassword123!'
        )

        with patch('api.endpoints.auth.get_current_active_user', return_value=default_admin_user):
            with pytest.raises(HTTPException) as exc_info:
                await change_password(request, db=db_session)

            assert exc_info.value.status_code == 401
            assert 'current password' in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_change_password_with_mismatched_passwords(
        self, db_session, default_admin_user
    ):
        """Test that mismatched new passwords are rejected"""
        from api.endpoints.auth import change_password, PasswordChangeRequest
        from pydantic import ValidationError

        # Should raise validation error during request creation
        with pytest.raises(ValidationError) as exc_info:
            request = PasswordChangeRequest(
                current_password='admin',
                new_password='NewSecurePassword123!',
                confirm_password='DifferentPassword123!'  # Doesn't match
            )

        assert 'passwords must match' in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_change_password_weak_password_rejected(
        self, db_session, default_admin_user
    ):
        """Test that weak passwords are rejected by validation"""
        from api.endpoints.auth import PasswordChangeRequest
        from pydantic import ValidationError

        # Too short
        with pytest.raises(ValidationError):
            PasswordChangeRequest(
                current_password='admin',
                new_password='Short1!',  # Only 7 chars
                confirm_password='Short1!'
            )

        # Missing uppercase
        with pytest.raises(ValidationError):
            PasswordChangeRequest(
                current_password='admin',
                new_password='lowercase123!',
                confirm_password='lowercase123!'
            )

        # Missing digit
        with pytest.raises(ValidationError):
            PasswordChangeRequest(
                current_password='admin',
                new_password='NoDigitsHere!',
                confirm_password='NoDigitsHere!'
            )

        # Missing special char
        with pytest.raises(ValidationError):
            PasswordChangeRequest(
                current_password='admin',
                new_password='NoSpecialChar123',
                confirm_password='NoSpecialChar123'
            )


class TestLoginWithDefaultPassword:
    """Test login endpoint behavior with default password active"""

    @pytest.fixture
    async def db_session(self):
        """Create test database session"""
        from src.giljo_mcp.database import DatabaseManager

        db_manager = DatabaseManager.get_instance()
        async with db_manager.get_session_async() as session:
            yield session
            await session.rollback()

    @pytest.fixture
    async def default_admin_user(self, db_session):
        """Create default admin user"""
        user = User(
            username='admin',
            password_hash=bcrypt.hash('admin'),
            role='admin',
            tenant_key='default',
            is_active=True
        )
        db_session.add(user)

        # Setup state with default password active
        setup_state = SetupState(
            tenant_key='default',
            database_initialized=False,
            meta_data={'default_password_active': True}
        )
        db_session.add(setup_state)

        await db_session.commit()
        await db_session.refresh(user)
        return user

    @pytest.mark.asyncio
    async def test_login_with_default_password_active_blocked(
        self, db_session, default_admin_user
    ):
        """Test that login is blocked when default password is still active"""
        from api.endpoints.auth import login, LoginRequest
        from fastapi import Response

        request = LoginRequest(username='admin', password='admin')
        response = Mock(spec=Response)

        with pytest.raises(HTTPException) as exc_info:
            await login(request, response=response, db=db_session)

        # Should return 403 Forbidden
        assert exc_info.value.status_code == 403

        # Error should indicate password change required
        detail = exc_info.value.detail
        assert 'must_change_password' in str(detail).lower() or 'change' in str(detail).lower()

    @pytest.mark.asyncio
    async def test_login_after_password_changed_succeeds(self, db_session):
        """Test that login works after password has been changed"""
        from api.endpoints.auth import login, LoginRequest
        from fastapi import Response

        # Create user with changed password
        user = User(
            username='admin',
            password_hash=bcrypt.hash('NewSecurePassword123!'),
            role='admin',
            tenant_key='default',
            is_active=True
        )
        db_session.add(user)

        # Setup state with default password inactive
        setup_state = SetupState(
            tenant_key='default',
            database_initialized=True,
            meta_data={'default_password_active': False}
        )
        db_session.add(setup_state)

        await db_session.commit()

        # Login should succeed
        request = LoginRequest(username='admin', password='NewSecurePassword123!')
        response = Mock(spec=Response)

        result = await login(request, response=response, db=db_session)

        assert result.message == 'Login successful'
        assert result.username == 'admin'
        assert result.role == 'admin'


class TestPasswordChangeValidation:
    """Test password validation rules"""

    def test_password_min_length_8(self):
        """Test minimum password length of 8 characters"""
        from api.endpoints.auth import PasswordChangeRequest
        from pydantic import ValidationError

        # 7 characters - should fail
        with pytest.raises(ValidationError) as exc_info:
            PasswordChangeRequest(
                current_password='admin',
                new_password='Short1!',  # 7 chars
                confirm_password='Short1!'
            )
        assert '8' in str(exc_info.value)

        # 8 characters - should pass
        request = PasswordChangeRequest(
            current_password='admin',
            new_password='Valid1!a',  # 8 chars
            confirm_password='Valid1!a'
        )
        assert request.new_password == 'Valid1!a'

    def test_password_requires_all_character_types(self):
        """Test that password requires uppercase, lowercase, digit, and special char"""
        from api.endpoints.auth import PasswordChangeRequest
        from pydantic import ValidationError

        # Valid password with all types
        request = PasswordChangeRequest(
            current_password='admin',
            new_password='MySecurePass123!',
            confirm_password='MySecurePass123!'
        )
        assert request.new_password == 'MySecurePass123!'

    def test_password_validation_edge_cases(self):
        """Test edge cases in password validation"""
        from api.endpoints.auth import PasswordChangeRequest

        # Exactly 8 characters with all requirements
        request = PasswordChangeRequest(
            current_password='admin',
            new_password='aA1!aA1!',  # Exactly 8
            confirm_password='aA1!aA1!'
        )
        assert len(request.new_password) == 8

        # Longer passwords should also work
        request = PasswordChangeRequest(
            current_password='admin',
            new_password='ThisIsAVeryLongAndSecurePassword123!',
            confirm_password='ThisIsAVeryLongAndSecurePassword123!'
        )
        assert len(request.new_password) > 8
