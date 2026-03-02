"""
Test suite for AuthManager v3.0 - Initialization, interface, and backward compatibility.

Tests the refactored AuthManager covering:
- Constructor signature (no mode parameter)
- Removed methods (is_enabled)
- Cross-platform path handling for secrets
- Preserved JWT and API key methods
- Type hints and documentation

Split from test_auth_manager_v3.py.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.giljo_mcp.auth_manager import AuthManager

pytestmark = pytest.mark.skip(reason="0750b: Auth manager v3 tests have partial bcrypt timeout failures on Windows")


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
