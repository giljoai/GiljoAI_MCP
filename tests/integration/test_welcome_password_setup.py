"""
Integration tests for Welcome Password Setup flow.

Tests the existing /api/auth/change-password endpoint to verify it works
correctly for the initial password setup during first-launch experience.

This is part of HANDOVER 0013 - Setup Flow Authentication Redesign.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from uuid import uuid4
from httpx import AsyncClient
from passlib.hash import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import SetupState, User


# Test Fixtures

@pytest.fixture
async def test_app():
    """Create FastAPI test app"""
    from api.app import app
    return app


@pytest_asyncio.fixture
async def client(test_app):
    """Create async test client for FastAPI"""
    async with AsyncClient(app=test_app, base_url="http://testserver") as test_client:
        yield test_client


@pytest_asyncio.fixture
async def admin_user(db_session):
    """Create admin user with default password (for password change tests)"""
    user = User(
        id=str(uuid4()),
        username="admin",
        password_hash=bcrypt.hash("admin"),
        role="admin",
        tenant_key="default",
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(user)

    # Create setup state with default_password_active
    setup_state = SetupState(
        id=str(uuid4()),
        tenant_key="default",
        database_initialized=True,
        default_password_active=True,
        setup_version="3.0.0"
    )
    db_session.add(setup_state)

    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def tenant_key():
    """Provide default tenant key for tests"""
    return "default"


# Test Suite

class TestWelcomePasswordSetup:
    """Test suite for welcome password setup using /api/auth/change-password endpoint."""

    @pytest.mark.asyncio
    async def test_change_password_success_initial_setup(
        self, client: AsyncClient, db_session: AsyncSession, admin_user: User, tenant_key: str
    ):
        """
        Test successful password change from default admin/admin.

        This is the PRIMARY use case for the welcome setup flow:
        - User provides current_password: 'admin' (default)
        - User provides new_password: <their choice>
        - Endpoint updates password
        - Endpoint sets default_password_active: false
        - Endpoint returns JWT token for immediate login
        """
        # Verify admin user exists with default password
        assert admin_user.username == "admin"

        # Verify setup state shows default password is active
        stmt = select(SetupState).where(SetupState.tenant_key == tenant_key)
        result = await db_session.execute(stmt)
        setup_state = result.scalar_one()
        assert setup_state.default_password_active is True

        # Make password change request (matching frontend format)
        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "admin",
                "new_password": "NewSecurePass123!",
                "confirm_password": "NewSecurePass123!",
            }
        )

        # Verify success response
        assert response.status_code == 200
        data = response.json()

        # Verify response format matches frontend expectations
        assert data["success"] is True
        assert data["message"] == "Password changed successfully"
        assert "token" in data
        assert "user" in data
        assert data["user"]["username"] == "admin"
        assert data["user"]["role"] == "admin"
        assert data["user"]["tenant_key"] == tenant_key

        # Verify JWT token is valid (non-empty string)
        assert isinstance(data["token"], str)
        assert len(data["token"]) > 0

        # Verify database updates
        await db_session.refresh(admin_user)

        # Password should be changed (hash should be different)
        assert bcrypt.verify("NewSecurePass123!", admin_user.password_hash)
        assert not bcrypt.verify("admin", admin_user.password_hash)

        # SetupState should reflect password change
        await db_session.refresh(setup_state)
        assert setup_state.default_password_active is False
        assert setup_state.password_changed_at is not None

    @pytest.mark.asyncio
    async def test_change_password_validation_passwords_mismatch(
        self, client: AsyncClient, admin_user: User
    ):
        """Test validation failure when new_password and confirm_password don't match."""
        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "admin",
                "new_password": "NewSecurePass123!",
                "confirm_password": "DifferentPass456!",  # Mismatch
            }
        )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "not match" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_change_password_validation_password_too_short(
        self, client: AsyncClient, admin_user: User
    ):
        """Test validation failure when password is too short (<8 chars)."""
        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "admin",
                "new_password": "Short1!",  # Only 7 characters
                "confirm_password": "Short1!",
            }
        )

        # Should fail validation (Pydantic or custom validation)
        assert response.status_code in [400, 422]
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_change_password_validation_missing_complexity(
        self, client: AsyncClient, admin_user: User
    ):
        """Test validation failure when password lacks complexity requirements."""
        # Test password without uppercase
        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "admin",
                "new_password": "lowercase123!",  # No uppercase
                "confirm_password": "lowercase123!",
            }
        )
        assert response.status_code in [400, 422]
        data = response.json()
        assert "detail" in data
        assert "uppercase" in str(data["detail"]).lower()

        # Test password without lowercase
        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "admin",
                "new_password": "UPPERCASE123!",  # No lowercase
                "confirm_password": "UPPERCASE123!",
            }
        )
        assert response.status_code in [400, 422]

        # Test password without digit
        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "admin",
                "new_password": "NoDigitsHere!",  # No digits
                "confirm_password": "NoDigitsHere!",
            }
        )
        assert response.status_code in [400, 422]

        # Test password without special character
        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "admin",
                "new_password": "NoSpecial123",  # No special chars
                "confirm_password": "NoSpecial123",
            }
        )
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_change_password_incorrect_current_password(
        self, client: AsyncClient, admin_user: User
    ):
        """Test authentication failure when current_password is incorrect."""
        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "wrongpassword",  # Incorrect
                "new_password": "NewSecurePass123!",
                "confirm_password": "NewSecurePass123!",
            }
        )

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "incorrect" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_change_password_admin_user_not_found(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test error handling when admin user doesn't exist in database."""
        # Delete admin user to simulate missing user scenario
        stmt = select(User).where(User.username == "admin")
        result = await db_session.execute(stmt)
        admin = result.scalar_one_or_none()

        if admin:
            await db_session.delete(admin)
            await db_session.commit()

        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "admin",
                "new_password": "NewSecurePass123!",
                "confirm_password": "NewSecurePass123!",
            }
        )

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_change_password_creates_setup_state_if_missing(
        self, client: AsyncClient, db_session: AsyncSession, admin_user: User, tenant_key: str
    ):
        """
        Test that endpoint creates SetupState if it doesn't exist.

        This handles edge cases where setup_state table entry is missing.
        """
        # Delete setup state to simulate missing entry
        stmt = select(SetupState).where(SetupState.tenant_key == tenant_key)
        result = await db_session.execute(stmt)
        setup_state = result.scalar_one_or_none()

        if setup_state:
            await db_session.delete(setup_state)
            await db_session.commit()

        # Make password change request
        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "admin",
                "new_password": "NewSecurePass123!",
                "confirm_password": "NewSecurePass123!",
            }
        )

        # Should succeed and create setup_state
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify SetupState was created
        stmt = select(SetupState).where(SetupState.tenant_key == tenant_key)
        result = await db_session.execute(stmt)
        new_setup_state = result.scalar_one_or_none()

        assert new_setup_state is not None
        assert new_setup_state.default_password_active is False
        assert new_setup_state.password_changed_at is not None
        assert new_setup_state.database_initialized is True
        assert new_setup_state.setup_version == "3.0.0"

    @pytest.mark.asyncio
    async def test_change_password_jwt_token_valid_for_immediate_login(
        self, client: AsyncClient, admin_user: User, tenant_key: str
    ):
        """
        Test that returned JWT token can be used immediately for authentication.

        This is critical for UX - user should be auto-logged in after password setup.
        """
        # Change password
        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "admin",
                "new_password": "NewSecurePass123!",
                "confirm_password": "NewSecurePass123!",
            }
        )

        assert response.status_code == 200
        data = response.json()
        token = data["token"]

        # Verify token works by calling /api/auth/me
        me_response = await client.get(
            "/api/auth/me",
            cookies={"access_token": token}
        )

        assert me_response.status_code == 200
        user_data = me_response.json()
        assert user_data["username"] == "admin"
        assert user_data["role"] == "admin"
        assert user_data["tenant_key"] == tenant_key

    @pytest.mark.asyncio
    async def test_change_password_idempotent_after_change(
        self, client: AsyncClient, admin_user: User, tenant_key: str
    ):
        """
        Test that password can be changed multiple times (not restricted to first change).

        User should be able to change password again using the new password.
        """
        # First password change
        response1 = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "admin",
                "new_password": "FirstPassword123!",
                "confirm_password": "FirstPassword123!",
            }
        )
        assert response1.status_code == 200

        # Second password change (using first new password)
        response2 = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "FirstPassword123!",
                "new_password": "SecondPassword456!",
                "confirm_password": "SecondPassword456!",
            }
        )

        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["success"] is True

        # Verify new password works
        login_response = await client.post(
            "/api/auth/login",
            json={
                "username": "admin",
                "password": "SecondPassword456!",
            }
        )
        assert login_response.status_code == 200

    @pytest.mark.asyncio
    async def test_change_password_request_format_matches_frontend(
        self, client: AsyncClient, admin_user: User
    ):
        """
        Test that endpoint accepts exact request format sent by frontend.

        Frontend sends:
        {
            "current_password": "admin",
            "new_password": "<user choice>",
            "confirm_password": "<user choice>"
        }
        """
        # This is the EXACT format from WelcomePasswordStep.vue
        frontend_request = {
            "current_password": "admin",
            "new_password": "UserChoice123!",
            "confirm_password": "UserChoice123!",
        }

        response = await client.post(
            "/api/auth/change-password",
            json=frontend_request
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response has ALL expected fields
        required_fields = ["success", "message", "token", "user"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Verify user object structure
        user_fields = ["id", "username", "role", "tenant_key"]
        for field in user_fields:
            assert field in data["user"], f"Missing user field: {field}"

    @pytest.mark.asyncio
    async def test_change_password_missing_required_fields(
        self, client: AsyncClient, admin_user: User
    ):
        """Test validation when required fields are missing."""
        # Missing current_password
        response = await client.post(
            "/api/auth/change-password",
            json={
                "new_password": "NewPass123!",
                "confirm_password": "NewPass123!",
            }
        )
        assert response.status_code == 422  # Pydantic validation error

        # Missing new_password
        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "admin",
                "confirm_password": "NewPass123!",
            }
        )
        assert response.status_code == 422

        # Missing confirm_password
        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "admin",
                "new_password": "NewPass123!",
            }
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_change_password_performance(
        self, client: AsyncClient, admin_user: User
    ):
        """Test that password change completes within reasonable time (<1 second)."""
        import time

        start_time = time.time()

        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "admin",
                "new_password": "PerformanceTest123!",
                "confirm_password": "PerformanceTest123!",
            }
        )

        elapsed_time = time.time() - start_time

        assert response.status_code == 200
        assert elapsed_time < 1.0, f"Password change took {elapsed_time:.2f}s (should be <1s)"
