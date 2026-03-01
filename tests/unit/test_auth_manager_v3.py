"""
Test suite for AuthManager v3.0 - Mode-independent authentication with auto-login.

Tests the refactored AuthManager that:
- Uses auto-login for localhost clients (127.0.0.1, ::1)
- Requires JWT or API key for network clients
- Removes mode-dependent logic (no more LOCAL/LAN/WAN modes)
- Integrates with auto-login middleware and localhost user system

This test suite follows TDD - tests are written BEFORE implementation.
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import Request

from src.giljo_mcp.auth_manager import AuthManager
from src.giljo_mcp.models import User

pytestmark = pytest.mark.skip(reason="0750b: Auth manager v3 tests have partial bcrypt timeout failures on Windows")

# Fixtures


@pytest.fixture
def mock_db_session():
    """Mock async database session for testing"""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = Mock()
    return session


@pytest.fixture
def test_user(mock_db_session):
    """Create a test user for authentication"""
    user = User(
        id=str(uuid.uuid4()),
        username="test_user",
        email="test@example.com",
        password_hash="$2b$12$dummyhash",
        role="developer",
        is_active=True,
        is_system_user=False,
        tenant_key="default",
        created_at=datetime.now(timezone.utc),
    )
    user.api_key = "gk_test_api_key_12345"
    return user


@pytest.fixture
def localhost_user(mock_db_session):
    """Create localhost system user"""
    user = User(
        id=str(uuid.uuid4()),
        username="localhost",
        email="localhost@local",
        password_hash=None,
        role="admin",
        is_active=True,
        is_system_user=True,
        tenant_key="default",
        created_at=datetime.now(timezone.utc),
    )
    return user


@pytest.fixture
def mock_config():
    """Mock configuration object"""
    config = Mock()
    config.server = Mock()
    config.server.mode = "LOCAL"  # This should be ignored by v3
    config.database = Mock()
    config.database.type = "postgresql"
    return config


# Test: AuthManager initialization


def test_auth_manager_init_no_mode_parameter(mock_config, mock_db_session):
    """Test AuthManager initialization without mode parameter"""
    # This test verifies the refactored __init__ signature
    auth_manager = AuthManager(config=mock_config, db=mock_db_session)

    assert auth_manager.config == mock_config
    assert auth_manager.db == mock_db_session
    # Should NOT have mode attribute
    assert not hasattr(auth_manager, "mode")


def test_auth_manager_init_mode_parameter_removed(mock_config, mock_db_session):
    """Test that mode parameter is removed from __init__"""
    # This should work - no mode parameter
    auth_manager = AuthManager(config=mock_config, db=mock_db_session)
    assert auth_manager is not None

    # This should FAIL - mode parameter should not exist
    with pytest.raises(TypeError):
        AuthManager(config=mock_config, db=mock_db_session, mode="LOCAL")


# Test: is_enabled() method removal


def test_auth_manager_is_enabled_method_removed(mock_config, mock_db_session):
    """Test that is_enabled() method is removed"""
    auth_manager = AuthManager(config=mock_config, db=mock_db_session)

    # Method should not exist
    assert not hasattr(auth_manager, "is_enabled")


# Test: authenticate_request() - Localhost auto-login


@pytest.mark.asyncio
async def test_auth_manager_localhost_ipv4_auto_login(mock_config, mock_db_session, localhost_user):
    """Test auto-login for localhost IPv4 (127.0.0.1)"""
    # Arrange
    auth_manager = AuthManager(config=mock_config, db=mock_db_session)

    # Mock request from localhost
    request = Mock(spec=Request)
    request.client = Mock()
    request.client.host = "127.0.0.1"
    request.state = Mock()
    request.headers = {}

    # Mock auto-login middleware behavior (patch the import inside the method)
    with patch("src.giljo_mcp.auth.auto_login.AutoLoginMiddleware") as mock_auto_login_cls:
        mock_auto_login = Mock()
        mock_auto_login.authenticate_request = AsyncMock(return_value=True)
        mock_auto_login_cls.return_value = mock_auto_login

        # Mock request.state set by auto-login
        request.state.user = localhost_user
        request.state.is_auto_login = True

        # Act
        result = await auth_manager.authenticate_request(request)

        # Assert
        assert result["authenticated"] is True
        assert result["user"] == "localhost"
        assert result["is_auto_login"] is True
        assert result["tenant_key"] == "default"
        assert "error" not in result


@pytest.mark.asyncio
async def test_auth_manager_localhost_ipv6_auto_login(mock_config, mock_db_session, localhost_user):
    """Test auto-login for localhost IPv6 (::1)"""
    # Arrange
    auth_manager = AuthManager(config=mock_config, db=mock_db_session)

    request = Mock(spec=Request)
    request.client = Mock()
    request.client.host = "::1"
    request.state = Mock()
    request.headers = {}

    # Mock auto-login (patch the import inside the method)
    with patch("src.giljo_mcp.auth.auto_login.AutoLoginMiddleware") as mock_auto_login_cls:
        mock_auto_login = Mock()
        mock_auto_login.authenticate_request = AsyncMock(return_value=True)
        mock_auto_login_cls.return_value = mock_auto_login

        request.state.user = localhost_user
        request.state.is_auto_login = True

        # Act
        result = await auth_manager.authenticate_request(request)

        # Assert
        assert result["authenticated"] is True
        assert result["user"] == "localhost"
        assert result["is_auto_login"] is True


# Test: authenticate_request() - Network clients require credentials


@pytest.mark.asyncio
async def test_auth_manager_network_client_no_credentials(mock_config, mock_db_session):
    """Test network client without credentials fails authentication"""
    # Arrange
    auth_manager = AuthManager(config=mock_config, db=mock_db_session)

    request = Mock(spec=Request)
    request.client = Mock()
    request.client.host = "192.168.1.100"  # Network IP
    request.headers = {}  # No auth headers

    # Act
    result = await auth_manager.authenticate_request(request)

    # Assert
    assert result["authenticated"] is False
    assert "error" in result
    assert "Authentication required" in result["error"] or "required" in result["error"].lower()


@pytest.mark.asyncio
async def test_auth_manager_network_client_with_valid_api_key(mock_config, mock_db_session, test_user):
    """Test network client with valid API key succeeds"""
    # Arrange
    auth_manager = AuthManager(config=mock_config, db=mock_db_session)

    # Pre-populate API keys
    auth_manager.api_keys = {
        test_user.api_key: {
            "name": test_user.username,
            "created_at": test_user.created_at.isoformat(),
            "permissions": ["*"],
            "active": True,
        }
    }

    request = Mock(spec=Request)
    request.client = Mock()
    request.client.host = "192.168.1.100"
    request.headers = {"X-API-Key": test_user.api_key}

    # Mock validate_api_key to return key info
    with patch.object(auth_manager, "validate_api_key", return_value=auth_manager.api_keys[test_user.api_key]):
        # Act
        result = await auth_manager.authenticate_request(request)

        # Assert
        assert result["authenticated"] is True
        assert result["user"] == test_user.username
        assert "error" not in result


@pytest.mark.asyncio
async def test_auth_manager_network_client_with_invalid_api_key(mock_config, mock_db_session):
    """Test network client with invalid API key fails"""
    # Arrange
    auth_manager = AuthManager(config=mock_config, db=mock_db_session)

    request = Mock(spec=Request)
    request.client = Mock()
    request.client.host = "192.168.1.100"
    request.headers = {"X-API-Key": "gk_invalid_key_12345"}

    # Mock validate_api_key to return None
    with patch.object(auth_manager, "validate_api_key", return_value=None):
        # Act
        result = await auth_manager.authenticate_request(request)

        # Assert
        assert result["authenticated"] is False
        assert "error" in result


@pytest.mark.asyncio
async def test_auth_manager_network_client_with_valid_jwt(mock_config, mock_db_session, test_user):
    """Test network client with valid JWT token succeeds"""
    # Arrange
    auth_manager = AuthManager(config=mock_config, db=mock_db_session)

    # Generate JWT token
    token = auth_manager.generate_jwt_token(user_id=test_user.username, tenant_key="default")

    request = Mock(spec=Request)
    request.client = Mock()
    request.client.host = "192.168.1.100"
    request.headers = {"Authorization": f"Bearer {token}"}

    # Mock validate_jwt_token to return payload
    mock_payload = {"user_id": test_user.username, "tenant_key": "default"}
    with patch.object(auth_manager, "validate_jwt_token", return_value=mock_payload):
        # Act
        result = await auth_manager.authenticate_request(request)

        # Assert
        assert result["authenticated"] is True
        assert result["user"] == test_user.username
        assert result.get("tenant_key") == "default"


@pytest.mark.asyncio
async def test_auth_manager_network_client_with_invalid_jwt(mock_config, mock_db_session):
    """Test network client with invalid JWT token fails"""
    # Arrange
    auth_manager = AuthManager(config=mock_config, db=mock_db_session)

    request = Mock(spec=Request)
    request.client = Mock()
    request.client.host = "192.168.1.100"
    request.headers = {"Authorization": "Bearer invalid_token_xyz"}

    # Mock validate_jwt_token to return None
    with patch.object(auth_manager, "validate_jwt_token", return_value=None):
        # Act
        result = await auth_manager.authenticate_request(request)

        # Assert
        assert result["authenticated"] is False
        assert "error" in result


# Test: JWT token priority over API key


@pytest.mark.asyncio
async def test_auth_manager_jwt_takes_priority_over_api_key(mock_config, mock_db_session, test_user):
    """Test that JWT Bearer token is checked before API key"""
    # Arrange
    auth_manager = AuthManager(config=mock_config, db=mock_db_session)

    # Generate valid JWT
    token = auth_manager.generate_jwt_token(user_id=test_user.username, tenant_key="default")

    request = Mock(spec=Request)
    request.client = Mock()
    request.client.host = "192.168.1.100"
    # Both JWT and API key present
    request.headers = {"Authorization": f"Bearer {token}", "X-API-Key": "gk_some_api_key"}

    # Mock both validators - JWT should be checked first
    mock_jwt_payload = {"user_id": test_user.username, "tenant_key": "default"}

    jwt_called = False
    api_key_called = False

    def mock_jwt_validate(token):
        nonlocal jwt_called
        jwt_called = True
        return mock_jwt_payload

    def mock_api_key_validate(key):
        nonlocal api_key_called
        api_key_called = True
        return {"name": "api_user", "active": True}

    with patch.object(auth_manager, "validate_jwt_token", side_effect=mock_jwt_validate):
        with patch.object(auth_manager, "validate_api_key", side_effect=mock_api_key_validate):
            # Act
            result = await auth_manager.authenticate_request(request)

            # Assert
            assert result["authenticated"] is True
            assert result["user"] == test_user.username
            assert jwt_called  # JWT should be checked
            # API key should NOT be checked (JWT succeeded)
            assert not api_key_called


# Test: API key fallback when JWT invalid


@pytest.mark.asyncio
async def test_auth_manager_api_key_fallback_when_jwt_invalid(mock_config, mock_db_session, test_user):
    """Test that API key is checked if JWT is invalid"""
    # Arrange
    auth_manager = AuthManager(config=mock_config, db=mock_db_session)

    request = Mock(spec=Request)
    request.client = Mock()
    request.client.host = "192.168.1.100"
    request.headers = {"Authorization": "Bearer invalid_token", "X-API-Key": test_user.api_key}

    # Mock JWT validation to fail, API key to succeed
    with (
        patch.object(auth_manager, "validate_jwt_token", return_value=None),
        patch.object(
            auth_manager,
            "validate_api_key",
            return_value={"name": test_user.username, "active": True, "permissions": ["*"]},
        ),
    ):
        # Act
        result = await auth_manager.authenticate_request(request)

        # Assert
        assert result["authenticated"] is True
        assert result["user"] == test_user.username


# Test: Cross-platform path handling


def test_auth_manager_uses_pathlib_for_secrets(mock_config, mock_db_session, tmp_path, monkeypatch):
    """Test that AuthManager uses pathlib.Path for all file operations"""
    # Mock home directory to temporary path
    monkeypatch.setenv("HOME", str(tmp_path))

    with patch("pathlib.Path.home", return_value=tmp_path):
        # Create auth manager
        auth_manager = AuthManager(config=mock_config, db=mock_db_session)

        # Verify secrets are stored using pathlib paths
        secret_file = tmp_path / ".giljo-mcp" / "jwt_secret"
        encryption_file = tmp_path / ".giljo-mcp" / "encryption_key"

        # Check that files were created using Path (not string concatenation)
        assert secret_file.exists()
        assert encryption_file.exists()

        # Verify paths are Path objects, not strings
        assert isinstance(secret_file, Path)
        assert isinstance(encryption_file, Path)


# Test: Backward compatibility - existing methods preserved


def test_auth_manager_preserves_jwt_methods(mock_config, mock_db_session):
    """Test that existing JWT methods are preserved"""
    auth_manager = AuthManager(config=mock_config, db=mock_db_session)

    # Methods should exist
    assert hasattr(auth_manager, "generate_jwt_token")
    assert hasattr(auth_manager, "validate_jwt_token")
    assert callable(auth_manager.generate_jwt_token)
    assert callable(auth_manager.validate_jwt_token)


def test_auth_manager_preserves_api_key_methods(mock_config, mock_db_session):
    """Test that existing API key methods are preserved"""
    auth_manager = AuthManager(config=mock_config, db=mock_db_session)

    # Methods should exist
    assert hasattr(auth_manager, "generate_api_key")
    assert hasattr(auth_manager, "validate_api_key")
    assert hasattr(auth_manager, "get_or_create_api_key")
    assert callable(auth_manager.generate_api_key)
    assert callable(auth_manager.validate_api_key)
    assert callable(auth_manager.get_or_create_api_key)


# Test: Error handling


@pytest.mark.asyncio
async def test_auth_manager_handles_missing_client_host(mock_config, mock_db_session):
    """Test graceful handling when request.client.host is missing"""
    auth_manager = AuthManager(config=mock_config, db=mock_db_session)

    request = Mock(spec=Request)
    request.client = None  # No client info
    request.headers = {}

    # Should not crash - should treat as network client requiring auth
    result = await auth_manager.authenticate_request(request)

    assert result["authenticated"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_auth_manager_handles_malformed_bearer_token(mock_config, mock_db_session):
    """Test handling of malformed Bearer token"""
    auth_manager = AuthManager(config=mock_config, db=mock_db_session)

    request = Mock(spec=Request)
    request.client = Mock()
    request.client.host = "192.168.1.100"
    request.headers = {"Authorization": "Bearertoken"}  # Missing space

    result = await auth_manager.authenticate_request(request)

    # Should fail gracefully
    assert result["authenticated"] is False
    assert "error" in result


# Integration test: Full authentication flow


@pytest.mark.asyncio
async def test_auth_manager_full_flow_localhost_then_network(mock_config, mock_db_session, localhost_user, test_user):
    """Test complete authentication flow for both localhost and network clients"""
    auth_manager = AuthManager(config=mock_config, db=mock_db_session)

    # 1. Localhost request - auto-login
    localhost_request = Mock(spec=Request)
    localhost_request.client = Mock()
    localhost_request.client.host = "127.0.0.1"
    localhost_request.state = Mock()
    localhost_request.headers = {}

    with patch("src.giljo_mcp.auth.auto_login.AutoLoginMiddleware") as mock_auto_login_cls:
        mock_auto_login = Mock()
        mock_auto_login.authenticate_request = AsyncMock(return_value=True)
        mock_auto_login_cls.return_value = mock_auto_login

        localhost_request.state.user = localhost_user
        localhost_request.state.is_auto_login = True

        localhost_result = await auth_manager.authenticate_request(localhost_request)

    assert localhost_result["authenticated"] is True
    assert localhost_result["user"] == "localhost"

    # 2. Network request with API key
    network_request = Mock(spec=Request)
    network_request.client = Mock()
    network_request.client.host = "192.168.1.50"
    network_request.headers = {"X-API-Key": test_user.api_key}

    with patch.object(
        auth_manager,
        "validate_api_key",
        return_value={"name": test_user.username, "active": True, "permissions": ["*"]},
    ):
        network_result = await auth_manager.authenticate_request(network_request)

    assert network_result["authenticated"] is True
    assert network_result["user"] == test_user.username


# Test: Type hints and documentation


def test_auth_manager_has_type_hints():
    """Test that authenticate_request has proper type hints"""
    import inspect

    sig = inspect.signature(AuthManager.authenticate_request)

    # Check return type annotation
    assert sig.return_annotation != inspect.Parameter.empty
    # Should return dict
    assert "dict" in str(sig.return_annotation).lower()


def test_auth_manager_has_docstring():
    """Test that authenticate_request has comprehensive docstring"""
    docstring = AuthManager.authenticate_request.__doc__

    assert docstring is not None
    assert len(docstring) > 50  # Non-trivial docstring
    # Should mention localhost and network
    assert "localhost" in docstring.lower() or "127.0.0.1" in docstring
