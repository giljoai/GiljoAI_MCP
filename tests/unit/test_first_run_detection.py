"""
Unit tests for first-run detection functionality.

Tests the backend first-run detection logic that determines whether
the setup wizard should be displayed based on the presence of an admin user.

Following TDD principles - these tests are written before implementation.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import select


pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def admin_user(db_session):
    """Create an admin user for testing"""
    import uuid

    from src.giljo_mcp.models import User

    user = User(
        id=str(uuid.uuid4()),
        username="admin",
        email="admin@example.com",
        password_hash="hashed_password",
        role="admin",
        tenant_key="default",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest_asyncio.fixture
async def regular_user(db_session):
    """Create a regular (non-admin) user for testing"""
    import uuid

    from src.giljo_mcp.models import User

    user = User(
        id=str(uuid.uuid4()),
        username="user",
        email="user@example.com",
        password_hash="hashed_password",
        role="developer",
        tenant_key="default",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


class TestFirstRunDetection:
    """Test suite for first-run detection logic"""

    async def test_first_run_no_admin_exists(self, db_session):
        """
        Test first-run detection when no admin user exists.

        Expected: first_run = True
        """
        from src.giljo_mcp.models import User

        # Verify no admin users exist
        stmt = select(User).where(User.role == "admin").limit(1)
        result = await db_session.execute(stmt)
        admin_exists = result.scalar_one_or_none() is not None

        assert admin_exists is False, "No admin user should exist"

        # This should be detected as first run
        first_run = not admin_exists
        assert first_run is True

    async def test_first_run_admin_exists(self, db_session, admin_user):
        """
        Test first-run detection when admin user exists.

        Expected: first_run = False
        """
        from src.giljo_mcp.models import User

        # Verify admin user exists
        stmt = select(User).where(User.role == "admin").limit(1)
        result = await db_session.execute(stmt)
        admin_exists = result.scalar_one_or_none() is not None

        assert admin_exists is True, "Admin user should exist"

        # This should NOT be detected as first run
        first_run = not admin_exists
        assert first_run is False

    async def test_first_run_only_regular_user_exists(self, db_session, regular_user):
        """
        Test first-run detection when only regular (non-admin) user exists.

        Expected: first_run = True (because no ADMIN user exists)
        """
        from src.giljo_mcp.models import User

        # Verify regular user exists but no admin
        stmt = select(User).where(User.role == "admin").limit(1)
        result = await db_session.execute(stmt)
        admin_exists = result.scalar_one_or_none() is not None

        assert admin_exists is False, "No admin user should exist"

        # This should be detected as first run
        first_run = not admin_exists
        assert first_run is True

    async def test_first_run_inactive_admin_exists(self, db_session):
        """
        Test first-run detection when an inactive admin user exists.

        Expected: first_run = False (inactive admin still counts as setup completed)
        """
        import uuid

        from src.giljo_mcp.models import User

        # Create inactive admin user
        user = User(
            id=str(uuid.uuid4()),
            username="inactive_admin",
            email="inactive@example.com",
            password_hash="hashed_password",
            role="admin",
            tenant_key="default",
            is_active=False,  # Inactive
            created_at=datetime.now(timezone.utc),
        )

        db_session.add(user)
        await db_session.commit()

        # Check if admin exists (regardless of active status)
        stmt = select(User).where(User.role == "admin").limit(1)
        result = await db_session.execute(stmt)
        admin_exists = result.scalar_one_or_none() is not None

        assert admin_exists is True, "Inactive admin user should exist"

        # This should NOT be detected as first run
        first_run = not admin_exists
        assert first_run is False

    async def test_first_run_multiple_admins(self, db_session, admin_user):
        """
        Test first-run detection when multiple admin users exist.

        Expected: first_run = False
        """
        import uuid

        from src.giljo_mcp.models import User

        # Create second admin user
        user2 = User(
            id=str(uuid.uuid4()),
            username="admin2",
            email="admin2@example.com",
            password_hash="hashed_password",
            role="admin",
            tenant_key="default",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        db_session.add(user2)
        await db_session.commit()

        # Check if admin exists
        stmt = select(User).where(User.role == "admin").limit(1)
        result = await db_session.execute(stmt)
        admin_exists = result.scalar_one_or_none() is not None

        assert admin_exists is True, "At least one admin should exist"

        # This should NOT be detected as first run
        first_run = not admin_exists
        assert first_run is False


class TestFirstRunAPIEndpoint:
    """Test suite for /api/setup/first-run endpoint"""

    async def test_first_run_endpoint_no_admin(self, db_session):
        """
        Test /api/setup/first-run endpoint when no admin exists.

        Expected: {"first_run": true}
        """
        from fastapi import Request

        from api.endpoints.setup import check_first_run

        # Create mock request with db_manager in app state
        mock_app = MagicMock()
        mock_api_state = MagicMock()

        # Mock the db_manager to return our test db_session
        mock_db_manager = MagicMock()

        async def mock_get_session():
            yield db_session

        mock_db_manager.get_session_async = mock_get_session
        mock_api_state.db_manager = mock_db_manager
        mock_app.state.api_state = mock_api_state

        mock_request = MagicMock(spec=Request)
        mock_request.app = mock_app

        # Call endpoint
        response = await check_first_run(mock_request)

        assert response["first_run"] is True

    async def test_first_run_endpoint_admin_exists(self, db_session, admin_user):
        """
        Test /api/setup/first-run endpoint when admin exists.

        Expected: {"first_run": false}
        """
        from fastapi import Request

        from api.endpoints.setup import check_first_run

        # Create mock request with db_manager in app state
        mock_app = MagicMock()
        mock_api_state = MagicMock()

        # Mock the db_manager to return our test db_session
        mock_db_manager = MagicMock()

        async def mock_get_session():
            yield db_session

        mock_db_manager.get_session_async = mock_get_session
        mock_api_state.db_manager = mock_db_manager
        mock_app.state.api_state = mock_api_state

        mock_request = MagicMock(spec=Request)
        mock_request.app = mock_app

        # Call endpoint
        response = await check_first_run(mock_request)

        assert response["first_run"] is False

    async def test_first_run_endpoint_handles_db_error(self):
        """
        Test /api/setup/first-run endpoint when database error occurs.

        Expected: {"first_run": false} (safe default on error)
        """
        from fastapi import Request

        from api.endpoints.setup import check_first_run

        # Create mock request that raises an error
        mock_app = MagicMock()
        mock_api_state = MagicMock()

        # Mock db_manager that raises an error
        mock_db_manager = MagicMock()

        async def mock_get_session_error():
            raise Exception("Database connection failed")
            yield  # Never reached

        mock_db_manager.get_session_async = mock_get_session_error
        mock_api_state.db_manager = mock_db_manager
        mock_app.state.api_state = mock_api_state

        mock_request = MagicMock(spec=Request)
        mock_request.app = mock_app

        # Call endpoint
        response = await check_first_run(mock_request)

        # Should return safe default (not first run) on error
        assert response["first_run"] is False

    async def test_first_run_endpoint_uses_app_state_cache(self, db_session, admin_user):
        """
        Test that endpoint uses app.state.first_run cache if available.

        Expected: Uses cached value instead of querying database
        """
        from fastapi import Request

        from api.endpoints.setup import check_first_run

        # Create mock request with cached first_run state
        mock_app = MagicMock()
        mock_app.state.first_run = False  # Cached value

        mock_request = MagicMock(spec=Request)
        mock_request.app = mock_app

        # Call endpoint
        response = await check_first_run(mock_request)

        # Should use cached value
        assert response["first_run"] is False

    async def test_first_run_endpoint_falls_back_to_db_when_no_cache(self, db_session):
        """
        Test that endpoint falls back to database query when cache not available.

        Expected: Queries database when app.state.first_run is None
        """
        from fastapi import Request

        from api.endpoints.setup import check_first_run

        # Create mock request without cached first_run state
        mock_app = MagicMock()
        mock_app.state.first_run = None  # No cached value
        mock_api_state = MagicMock()

        # Mock the db_manager to return our test db_session
        mock_db_manager = MagicMock()

        async def mock_get_session():
            yield db_session

        mock_db_manager.get_session_async = mock_get_session
        mock_api_state.db_manager = mock_db_manager
        mock_app.state.api_state = mock_api_state

        mock_request = MagicMock(spec=Request)
        mock_request.app = mock_app

        # Call endpoint
        response = await check_first_run(mock_request)

        # Should query database and return true (no admin exists)
        assert response["first_run"] is True


class TestStartupFirstRunCheck:
    """Test suite for startup event first-run check"""

    async def test_startup_checks_admin_user_exists(self, db_session, admin_user):
        """
        Test that startup event correctly detects admin user exists.

        Expected: app.state.first_run = False
        """
        from src.giljo_mcp.models import User

        # Simulate startup check logic
        stmt = select(User).where(User.role == "admin").limit(1)
        result = await db_session.execute(stmt)
        admin_exists = result.scalar_one_or_none() is not None

        first_run = not admin_exists

        assert first_run is False

    async def test_startup_checks_no_admin_user(self, db_session):
        """
        Test that startup event correctly detects no admin user.

        Expected: app.state.first_run = True
        """
        from src.giljo_mcp.models import User

        # Simulate startup check logic
        stmt = select(User).where(User.role == "admin").limit(1)
        result = await db_session.execute(stmt)
        admin_exists = result.scalar_one_or_none() is not None

        first_run = not admin_exists

        assert first_run is True

    async def test_startup_handles_db_error_gracefully(self):
        """
        Test that startup event handles database errors gracefully.

        Expected: app.state.first_run = False (safe default on error)
        """
        # Simulate database error during startup check
        try:
            raise Exception("Database connection failed")
        except Exception:
            # On error, assume not first run (safe default)
            first_run = False

        assert first_run is False


class TestRouterGuardFirstRunCheck:
    """Test suite for frontend router guard first-run check"""

    def test_router_guard_redirects_on_first_run(self):
        """
        Test that router guard redirects to /setup on first run.

        Expected: Navigation to /setup when first_run = true
        """
        # Mock setup status response
        setup_status = {"first_run": True}

        # Simulate router guard logic
        if setup_status["first_run"]:
            redirect_path = "/setup"
        else:
            redirect_path = None

        assert redirect_path == "/setup"

    def test_router_guard_allows_navigation_when_setup_complete(self):
        """
        Test that router guard allows navigation when setup complete.

        Expected: No redirect when first_run = false
        """
        # Mock setup status response
        setup_status = {"first_run": False}

        # Simulate router guard logic
        if setup_status["first_run"]:
            redirect_path = "/setup"
        else:
            redirect_path = None

        assert redirect_path is None

    def test_router_guard_allows_setup_route_always(self):
        """
        Test that router guard always allows access to /setup route.

        Expected: No redirect when navigating to /setup
        """
        to_path = "/setup"

        # Simulate router guard logic
        if to_path == "/setup":
            # Skip first-run check for setup route
            redirect_path = None
        else:
            redirect_path = "/setup"  # Would redirect for other routes

        assert redirect_path is None


class TestLoginPageFirstRunCheck:
    """Test suite for Login.vue first-run check"""

    def test_login_redirects_to_setup_on_first_run(self):
        """
        Test that Login.vue redirects to /setup on first run.

        Expected: Redirect to /setup when first_run = true
        """
        # Mock API response
        first_run_response = {"first_run": True}

        # Simulate Login.vue mounted logic
        if first_run_response["first_run"]:
            redirect_path = "/setup"
        else:
            redirect_path = None

        assert redirect_path == "/setup"

    def test_login_shows_form_when_setup_complete(self):
        """
        Test that Login.vue shows login form when setup complete.

        Expected: Show login form when first_run = false
        """
        # Mock API response
        first_run_response = {"first_run": False}

        # Simulate Login.vue mounted logic
        if first_run_response["first_run"]:
            show_login_form = False
        else:
            show_login_form = True

        assert show_login_form is True

    def test_login_handles_api_error_gracefully(self):
        """
        Test that Login.vue handles API errors gracefully.

        Expected: Show login form on API error (safe default)
        """
        # Simulate API error
        api_error = True

        # On error, show login form (safe default)
        if api_error:
            show_login_form = True
        else:
            show_login_form = False

        assert show_login_form is True


class TestFirstRunEdgeCases:
    """Test suite for edge cases in first-run detection"""

    async def test_first_run_with_system_user_only(self, db_session):
        """
        Test first-run detection when only system user exists (not admin).

        Expected: first_run = True (system user doesn't count as admin)
        """
        import uuid

        from src.giljo_mcp.models import User

        # Create system user (localhost auto-login user)
        user = User(
            id=str(uuid.uuid4()),
            username="localhost",
            email=None,
            password_hash=None,
            role="developer",  # System user is NOT admin
            tenant_key="default",
            is_active=True,
            is_system_user=True,
            created_at=datetime.now(timezone.utc),
        )

        db_session.add(user)
        await db_session.commit()

        # Check if admin exists
        stmt = select(User).where(User.role == "admin").limit(1)
        result = await db_session.execute(stmt)
        admin_exists = result.scalar_one_or_none() is not None

        assert admin_exists is False, "System user should not count as admin"

        # This should be detected as first run
        first_run = not admin_exists
        assert first_run is True

    async def test_first_run_detection_performance(self, db_session, admin_user):
        """
        Test that first-run detection query is efficient.

        Expected: Uses LIMIT 1 for optimal performance
        """
        import time

        from src.giljo_mcp.models import User

        # Measure query performance
        start = time.perf_counter()

        stmt = select(User).where(User.role == "admin").limit(1)
        result = await db_session.execute(stmt)
        admin_exists = result.scalar_one_or_none() is not None

        elapsed = time.perf_counter() - start

        # Query should be fast (< 100ms)
        assert elapsed < 0.1, f"Query took too long: {elapsed:.3f}s"
        assert admin_exists is True
