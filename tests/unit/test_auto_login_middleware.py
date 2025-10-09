"""
Unit tests for auto-login middleware.

Tests the automatic authentication of localhost clients (127.0.0.1, ::1)
versus requiring authentication for network clients.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from src.giljo_mcp.auth.auto_login import AutoLoginMiddleware, LOCALHOST_IPS


@pytest.mark.asyncio
async def test_auto_login_localhost_ipv4(db_session):
    """Test auto-login for 127.0.0.1."""
    # Arrange: Mock request from 127.0.0.1
    request = Mock()
    request.client = Mock()
    request.client.host = "127.0.0.1"
    request.state = Mock()

    middleware = AutoLoginMiddleware(db_session)

    # Act: Process request
    authenticated = await middleware.authenticate_request(request)

    # Assert: Auto-authenticated as localhost user
    assert authenticated is True
    assert hasattr(request.state, "user")
    assert request.state.user.username == "localhost"
    assert request.state.user.is_system_user is True
    assert request.state.is_auto_login is True
    assert request.state.authenticated is True


@pytest.mark.asyncio
async def test_auto_login_localhost_ipv6(db_session):
    """Test auto-login for ::1 (IPv6 localhost)."""
    # Arrange: Mock request from ::1
    request = Mock()
    request.client = Mock()
    request.client.host = "::1"
    request.state = Mock()

    middleware = AutoLoginMiddleware(db_session)

    # Act: Process request
    authenticated = await middleware.authenticate_request(request)

    # Assert: Auto-authenticated as localhost user
    assert authenticated is True
    assert hasattr(request.state, "user")
    assert request.state.user.username == "localhost"
    assert request.state.user.is_system_user is True
    assert request.state.is_auto_login is True


@pytest.mark.asyncio
async def test_no_auto_login_network_client(db_session):
    """Test network client not auto-logged in."""

    # Arrange: Mock request from 192.168.1.100
    # Use a simple object instead of Mock to avoid auto-attribute creation
    class MockState:
        pass

    class MockClient:
        host = "192.168.1.100"

    class MockRequest:
        client = MockClient()
        state = MockState()

    request = MockRequest()
    middleware = AutoLoginMiddleware(db_session)

    # Act: Process request
    authenticated = await middleware.authenticate_request(request)

    # Assert: NOT auto-authenticated (returns False)
    assert authenticated is False
    assert not hasattr(request.state, "user")
    assert not hasattr(request.state, "is_auto_login")


@pytest.mark.asyncio
async def test_no_auto_login_public_ip(db_session):
    """Test public IP not auto-logged in."""

    # Arrange: Mock request from public IP
    class MockState:
        pass

    class MockClient:
        host = "203.0.113.45"  # Example public IP

    class MockRequest:
        client = MockClient()
        state = MockState()

    request = MockRequest()
    middleware = AutoLoginMiddleware(db_session)

    # Act: Process request
    authenticated = await middleware.authenticate_request(request)

    # Assert: NOT auto-authenticated
    assert authenticated is False
    assert not hasattr(request.state, "user")


@pytest.mark.asyncio
async def test_localhost_ips_constant():
    """Test LOCALHOST_IPS constant contains expected values."""
    # Assert: Contains both IPv4 and IPv6 localhost
    assert "127.0.0.1" in LOCALHOST_IPS
    assert "::1" in LOCALHOST_IPS
    assert len(LOCALHOST_IPS) == 2


@pytest.mark.asyncio
async def test_auto_login_creates_localhost_user_if_missing(db_session):
    """Test auto-login creates localhost user if not exists."""
    # Arrange: Clean database (no localhost user)
    # Mock request from localhost
    request = Mock()
    request.client = Mock()
    request.client.host = "127.0.0.1"
    request.state = Mock()

    middleware = AutoLoginMiddleware(db_session)

    # Act: Process request
    authenticated = await middleware.authenticate_request(request)

    # Assert: User created and authenticated
    assert authenticated is True
    assert request.state.user.username == "localhost"

    # Verify user was created in database
    from src.giljo_mcp.auth.localhost_user import get_localhost_user

    user = await get_localhost_user(db_session)
    assert user is not None
    assert user.username == "localhost"


@pytest.mark.asyncio
async def test_auto_login_idempotent_multiple_requests(db_session):
    """Test multiple localhost requests use same user."""
    # Arrange: Two requests from localhost
    request1 = Mock()
    request1.client = Mock()
    request1.client.host = "127.0.0.1"
    request1.state = Mock()

    request2 = Mock()
    request2.client = Mock()
    request2.client.host = "127.0.0.1"
    request2.state = Mock()

    middleware = AutoLoginMiddleware(db_session)

    # Act: Process both requests
    auth1 = await middleware.authenticate_request(request1)
    auth2 = await middleware.authenticate_request(request2)

    # Assert: Both authenticated with same user
    assert auth1 is True
    assert auth2 is True
    assert request1.state.user.id == request2.state.user.id
    assert request1.state.user.username == "localhost"
    assert request2.state.user.username == "localhost"


@pytest.mark.asyncio
async def test_auto_login_sets_all_required_state(db_session):
    """Test auto-login sets all required state attributes."""
    # Arrange: Mock request from localhost
    request = Mock()
    request.client = Mock()
    request.client.host = "127.0.0.1"
    request.state = Mock()

    middleware = AutoLoginMiddleware(db_session)

    # Act: Process request
    await middleware.authenticate_request(request)

    # Assert: All required state attributes set
    assert hasattr(request.state, "user")
    assert hasattr(request.state, "is_auto_login")
    assert hasattr(request.state, "authenticated")
    assert request.state.user is not None
    assert request.state.is_auto_login is True
    assert request.state.authenticated is True
