"""Tests for validation initialization module"""
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from api.app import APIState


@pytest.mark.asyncio
async def test_init_validation_loads_version_from_config():
    """Should load version from config.yaml installation section"""
    from api.startup.validation import init_validation

    state = APIState()
    state.db_manager = MagicMock()

    config_yaml = """
installation:
  version: "3.1.5"
"""

    with patch('api.startup.validation.open', mock_open(read_data=config_yaml)), \
         patch('api.startup.validation.Path.exists', return_value=True), \
         patch('api.startup.validation.SetupStateManager') as mock_state_manager:

        mock_manager_instance = MagicMock()
        mock_manager_instance.requires_migration.return_value = False
        mock_manager_instance.validate_state.return_value = (True, [])
        mock_state_manager.get_instance.return_value = mock_manager_instance

        await init_validation(state)

        # Verify SetupStateManager was initialized with correct version
        mock_state_manager.get_instance.assert_called_once_with(
            tenant_key="default",
            current_version="3.1.5",
            required_db_version="18"
        )


@pytest.mark.asyncio
async def test_init_validation_uses_default_version_when_missing():
    """Should use default version "2.0.0" when not in config"""
    from api.startup.validation import init_validation

    state = APIState()
    state.db_manager = MagicMock()

    minimal_config_yaml = """
server:
  host: localhost
"""

    with patch('api.startup.validation.open', mock_open(read_data=minimal_config_yaml)), \
         patch('api.startup.validation.Path.exists', return_value=True), \
         patch('api.startup.validation.SetupStateManager') as mock_state_manager:

        mock_manager_instance = MagicMock()
        mock_manager_instance.requires_migration.return_value = False
        mock_manager_instance.validate_state.return_value = (True, [])
        mock_state_manager.get_instance.return_value = mock_manager_instance

        await init_validation(state)

        # Should use default version
        mock_state_manager.get_instance.assert_called_once_with(
            tenant_key="default",
            current_version="2.0.0",
            required_db_version="18"
        )


@pytest.mark.asyncio
async def test_init_validation_checks_migration_required():
    """Should check if migration is required via requires_migration()"""
    from api.startup.validation import init_validation

    state = APIState()
    state.db_manager = MagicMock()

    config_yaml = """
installation:
  version: "3.2.0"
"""

    with patch('api.startup.validation.open', mock_open(read_data=config_yaml)), \
         patch('api.startup.validation.Path.exists', return_value=True), \
         patch('api.startup.validation.SetupStateManager') as mock_state_manager:

        mock_manager_instance = MagicMock()
        mock_manager_instance.requires_migration.return_value = False
        mock_manager_instance.validate_state.return_value = (True, [])
        mock_state_manager.get_instance.return_value = mock_manager_instance

        await init_validation(state)

        # Verify migration check was called
        mock_manager_instance.requires_migration.assert_called_once()


@pytest.mark.asyncio
async def test_init_validation_warns_on_migration_required():
    """Should log warnings when migration is required"""
    from api.startup.validation import init_validation

    state = APIState()
    state.db_manager = MagicMock()

    config_yaml = """
installation:
  version: "3.2.0"
"""

    with patch('api.startup.validation.open', mock_open(read_data=config_yaml)), \
         patch('api.startup.validation.Path.exists', return_value=True), \
         patch('api.startup.validation.SetupStateManager') as mock_state_manager, \
         patch('api.startup.validation.logger') as mock_logger:

        mock_manager_instance = MagicMock()
        mock_manager_instance.requires_migration.return_value = True
        mock_manager_instance.get_state.return_value = {"setup_version": "3.0.0"}
        mock_manager_instance.validate_state.return_value = (True, [])
        mock_state_manager.get_instance.return_value = mock_manager_instance

        await init_validation(state)

        # Verify warnings were logged
        warning_calls = [call.args[0] for call in mock_logger.warning.call_args_list]
        assert any('Setup state version mismatch detected' in msg for msg in warning_calls)
        assert any('Run POST /api/setup/migrate' in msg for msg in warning_calls)


@pytest.mark.asyncio
async def test_init_validation_validates_state():
    """Should call validate_state() to check setup state"""
    from api.startup.validation import init_validation

    state = APIState()
    state.db_manager = MagicMock()

    config_yaml = """
installation:
  version: "3.2.0"
"""

    with patch('api.startup.validation.open', mock_open(read_data=config_yaml)), \
         patch('api.startup.validation.Path.exists', return_value=True), \
         patch('api.startup.validation.SetupStateManager') as mock_state_manager:

        mock_manager_instance = MagicMock()
        mock_manager_instance.requires_migration.return_value = False
        mock_manager_instance.validate_state.return_value = (True, [])
        mock_state_manager.get_instance.return_value = mock_manager_instance

        await init_validation(state)

        # Verify validation was called
        mock_manager_instance.validate_state.assert_called_once()


@pytest.mark.asyncio
async def test_init_validation_warns_on_validation_failures():
    """Should log warnings when validation fails"""
    from api.startup.validation import init_validation

    state = APIState()
    state.db_manager = MagicMock()

    config_yaml = """
installation:
  version: "3.2.0"
"""

    failures = [
        "Database connection check failed",
        "Config file permissions incorrect"
    ]

    with patch('api.startup.validation.open', mock_open(read_data=config_yaml)), \
         patch('api.startup.validation.Path.exists', return_value=True), \
         patch('api.startup.validation.SetupStateManager') as mock_state_manager, \
         patch('api.startup.validation.logger') as mock_logger:

        mock_manager_instance = MagicMock()
        mock_manager_instance.requires_migration.return_value = False
        mock_manager_instance.validate_state.return_value = (False, failures)
        mock_state_manager.get_instance.return_value = mock_manager_instance

        await init_validation(state)

        # Verify validation failures were logged
        warning_calls = [call.args[0] for call in mock_logger.warning.call_args_list]
        assert any('Setup validation failures detected' in msg for msg in warning_calls)
        assert any('Database connection check failed' in msg for msg in warning_calls)


@pytest.mark.asyncio
async def test_init_validation_logs_success_on_valid_state():
    """Should log success message when validation passes"""
    from api.startup.validation import init_validation

    state = APIState()
    state.db_manager = MagicMock()

    config_yaml = """
installation:
  version: "3.2.0"
"""

    with patch('api.startup.validation.open', mock_open(read_data=config_yaml)), \
         patch('api.startup.validation.Path.exists', return_value=True), \
         patch('api.startup.validation.SetupStateManager') as mock_state_manager, \
         patch('api.startup.validation.logger') as mock_logger:

        mock_manager_instance = MagicMock()
        mock_manager_instance.requires_migration.return_value = False
        mock_manager_instance.validate_state.return_value = (True, [])
        mock_state_manager.get_instance.return_value = mock_manager_instance

        await init_validation(state)

        # Verify success messages were logged
        info_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any('Setup state version is current' in msg for msg in info_calls)
        assert any('Setup state validation passed' in msg for msg in info_calls)


@pytest.mark.asyncio
async def test_init_validation_continues_on_error():
    """Should not crash app on validation error, just log warning"""
    from api.startup.validation import init_validation

    state = APIState()
    state.db_manager = MagicMock()

    with patch('api.startup.validation.Path.exists', return_value=False), \
         patch('api.startup.validation.logger') as mock_logger:

        # Should not raise exception
        await init_validation(state)

        # Verify warning was logged
        warning_calls = [call.args[0] for call in mock_logger.warning.call_args_list]
        assert any('Continuing startup despite setup check failure' in msg for msg in warning_calls)


@pytest.mark.asyncio
async def test_init_validation_skips_when_no_db_manager():
    """Should skip validation when state.db_manager is None"""
    from api.startup.validation import init_validation

    state = APIState()
    state.db_manager = None

    with patch('api.startup.validation.SetupStateManager') as mock_state_manager:
        await init_validation(state)

        # Should not call SetupStateManager when db_manager is None
        mock_state_manager.get_instance.assert_not_called()
