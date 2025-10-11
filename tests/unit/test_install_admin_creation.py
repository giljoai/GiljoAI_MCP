"""
Unit tests for default admin account creation in install.py

Following TDD principles - tests written BEFORE implementation.
Tests for unified authentication Phase 2 backend.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from passlib.hash import bcrypt

# Import the User model
from src.giljo_mcp.models import User, SetupState


class TestDefaultAdminCreation:
    """Test suite for default admin account creation during installation"""

    @pytest.mark.asyncio
    async def test_create_default_admin_account_creates_user(self, db_session):
        """Test that create_default_admin_account creates a user in the database"""
        # This test will fail until we implement the function
        from installer.core.database import DatabaseInstaller

        db_installer = DatabaseInstaller(settings={'pg_password': '4010'})

        # Call the function (doesn't exist yet - will fail)
        result = await db_installer.create_default_admin_account(db_session)

        assert result['success'] is True
        assert 'user' in result

        # Verify user was created
        user = result['user']
        assert user.username == 'admin'
        assert user.role == 'admin'
        assert user.tenant_key == 'default'
        assert user.is_active is True

    @pytest.mark.asyncio
    async def test_default_admin_password_is_hashed(self, db_session):
        """Test that default admin password is properly bcrypt hashed"""
        from installer.core.database import DatabaseInstaller

        db_installer = DatabaseInstaller(settings={'pg_password': '4010'})
        result = await db_installer.create_default_admin_account(db_session)

        user = result['user']

        # Password should NOT be stored in plaintext
        assert user.password_hash != 'admin'

        # Password should verify correctly
        assert bcrypt.verify('admin', user.password_hash)

        # Invalid password should not verify
        assert not bcrypt.verify('wrong_password', user.password_hash)

    @pytest.mark.asyncio
    async def test_default_admin_sets_setup_state(self, db_session):
        """Test that creating default admin sets default_password_active in setup state"""
        from installer.core.database import DatabaseInstaller

        db_installer = DatabaseInstaller(settings={'pg_password': '4010'})
        result = await db_installer.create_default_admin_account(db_session)

        # Check setup state was updated
        from sqlalchemy import select
        stmt = select(SetupState).where(SetupState.tenant_key == 'default')
        result_state = await db_session.execute(stmt)
        setup_state = result_state.scalar_one_or_none()

        assert setup_state is not None
        assert setup_state.meta_data.get('default_password_active') is True

    @pytest.mark.asyncio
    async def test_default_admin_idempotent(self, db_session):
        """Test that creating default admin is idempotent (doesn't create duplicates)"""
        from installer.core.database import DatabaseInstaller

        db_installer = DatabaseInstaller(settings={'pg_password': '4010'})

        # Create admin first time
        result1 = await db_installer.create_default_admin_account(db_session)
        assert result1['success'] is True

        # Try to create again - should not fail, should return existing user
        result2 = await db_installer.create_default_admin_account(db_session)
        assert result2['success'] is True

        # Should be same user
        assert result1['user'].id == result2['user'].id

        # Should only have ONE admin user
        from sqlalchemy import select, func
        stmt = select(func.count()).select_from(User).where(User.username == 'admin')
        count_result = await db_session.execute(stmt)
        count = count_result.scalar()
        assert count == 1

    @pytest.mark.asyncio
    async def test_default_admin_has_correct_attributes(self, db_session):
        """Test that default admin has all required attributes set correctly"""
        from installer.core.database import DatabaseInstaller

        db_installer = DatabaseInstaller(settings={'pg_password': '4010'})
        result = await db_installer.create_default_admin_account(db_session)

        user = result['user']

        # Check all attributes
        assert user.username == 'admin'
        assert user.email is None  # No email for default admin
        assert user.full_name is None  # No full name initially
        assert user.role == 'admin'
        assert user.tenant_key == 'default'
        assert user.is_active is True
        assert user.is_system_user is False  # Not a system user
        assert user.password_hash is not None
        assert user.created_at is not None

    @pytest.mark.asyncio
    async def test_default_admin_returns_credentials(self, db_session):
        """Test that function returns admin credentials for display"""
        from installer.core.database import DatabaseInstaller

        db_installer = DatabaseInstaller(settings={'pg_password': '4010'})
        result = await db_installer.create_default_admin_account(db_session)

        # Should return credentials for installer to display
        assert 'credentials' in result
        assert result['credentials']['username'] == 'admin'
        assert result['credentials']['password'] == 'admin'
        assert result['credentials']['message'] == 'Change this password on first login!'


class TestAdminCreationErrors:
    """Test error handling for admin account creation"""

    @pytest.mark.asyncio
    async def test_create_admin_handles_database_errors(self, db_session):
        """Test that database errors are handled gracefully"""
        from installer.core.database import DatabaseInstaller

        db_installer = DatabaseInstaller(settings={'pg_password': '4010'})

        # Mock database session to raise error
        with patch.object(db_session, 'add', side_effect=Exception('Database error')):
            result = await db_installer.create_default_admin_account(db_session)

            assert result['success'] is False
            assert 'error' in result
            assert 'Database error' in result['error']

    @pytest.mark.asyncio
    async def test_create_admin_handles_missing_setup_state(self, db_session):
        """Test that missing setup state is created if needed"""
        from installer.core.database import DatabaseInstaller

        db_installer = DatabaseInstaller(settings={'pg_password': '4010'})

        # Ensure no setup state exists
        from sqlalchemy import delete
        await db_session.execute(delete(SetupState).where(SetupState.tenant_key == 'default'))
        await db_session.commit()

        # Should create setup state
        result = await db_installer.create_default_admin_account(db_session)
        assert result['success'] is True

        # Verify setup state was created
        from sqlalchemy import select
        stmt = select(SetupState).where(SetupState.tenant_key == 'default')
        result_state = await db_session.execute(stmt)
        setup_state = result_state.scalar_one_or_none()

        assert setup_state is not None


class TestPasswordStrengthValidation:
    """Test password strength validation for password change endpoint"""

    def test_password_too_short(self):
        """Test that passwords under 12 characters are rejected"""
        from api.endpoints.auth import PasswordChangeRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            PasswordChangeRequest(
                current_password='admin',
                new_password='Short1!',  # Only 7 characters
                confirm_password='Short1!'
            )

        assert 'at least 12 characters' in str(exc_info.value)

    def test_password_missing_uppercase(self):
        """Test that passwords without uppercase are rejected"""
        from api.endpoints.auth import PasswordChangeRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            PasswordChangeRequest(
                current_password='admin',
                new_password='lowercase123!',  # No uppercase
                confirm_password='lowercase123!'
            )

        assert 'uppercase letter' in str(exc_info.value)

    def test_password_missing_lowercase(self):
        """Test that passwords without lowercase are rejected"""
        from api.endpoints.auth import PasswordChangeRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            PasswordChangeRequest(
                current_password='admin',
                new_password='UPPERCASE123!',  # No lowercase
                confirm_password='UPPERCASE123!'
            )

        assert 'lowercase letter' in str(exc_info.value)

    def test_password_missing_digit(self):
        """Test that passwords without digits are rejected"""
        from api.endpoints.auth import PasswordChangeRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            PasswordChangeRequest(
                current_password='admin',
                new_password='NoDigitsHere!',  # No digit
                confirm_password='NoDigitsHere!'
            )

        assert 'number' in str(exc_info.value) or 'digit' in str(exc_info.value)

    def test_password_missing_special_char(self):
        """Test that passwords without special characters are rejected"""
        from api.endpoints.auth import PasswordChangeRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            PasswordChangeRequest(
                current_password='admin',
                new_password='NoSpecialChar123',  # No special character
                confirm_password='NoSpecialChar123'
            )

        assert 'special character' in str(exc_info.value)

    def test_password_valid(self):
        """Test that valid password passes validation"""
        from api.endpoints.auth import PasswordChangeRequest

        # Should not raise error
        request = PasswordChangeRequest(
            current_password='admin',
            new_password='ValidPassword123!',
            confirm_password='ValidPassword123!'
        )

        assert request.new_password == 'ValidPassword123!'


# Fixtures for testing

@pytest.fixture
async def db_session():
    """Create a test database session"""
    from src.giljo_mcp.database import DatabaseManager

    db_manager = DatabaseManager.get_instance()

    async with db_manager.get_session_async() as session:
        yield session
        await session.rollback()  # Roll back test changes
