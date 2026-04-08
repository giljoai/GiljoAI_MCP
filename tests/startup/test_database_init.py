# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Tests for database initialization module"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.app import APIState


@pytest.mark.asyncio
async def test_init_database_sets_db_manager_on_state():
    """After init_database, state.db_manager should be set"""
    from api.startup.database import init_database

    state = APIState()

    with (
        patch("api.startup.database.get_config") as mock_get_config,
        patch("api.startup.database.DatabaseManager") as mock_db_manager,
        patch.dict(os.environ, {"DATABASE_URL": "postgresql://localhost/test"}),
    ):
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        mock_db_instance = MagicMock()
        mock_db_instance.create_tables_async = AsyncMock()
        mock_db_manager.return_value = mock_db_instance

        await init_database(state)

        assert state.db_manager is not None
        assert state.config is not None
        mock_db_instance.create_tables_async.assert_called_once()


@pytest.mark.asyncio
async def test_init_database_uses_env_url_first():
    """DATABASE_URL from environment should take precedence over config"""
    from api.startup.database import init_database

    state = APIState()
    env_url = "postgresql://envuser:envpass@envhost/envdb"

    with (
        patch("api.startup.database.get_config") as mock_get_config,
        patch("api.startup.database.DatabaseManager") as mock_db_manager,
        patch.dict(os.environ, {"DATABASE_URL": env_url}),
    ):
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        mock_db_instance = MagicMock()
        mock_db_instance.create_tables_async = AsyncMock()
        mock_db_manager.return_value = mock_db_instance

        await init_database(state)

        # Verify DatabaseManager was called with env URL
        mock_db_manager.assert_called_once_with(env_url, is_async=True)


@pytest.mark.asyncio
async def test_init_database_uses_config_url_when_no_env():
    """Should use config.database.get_connection_string() when no env var"""
    from api.startup.database import init_database

    state = APIState()
    config_url = "postgresql://configuser:configpass@confighost/configdb"

    with (
        patch("api.startup.database.get_config") as mock_get_config,
        patch("api.startup.database.DatabaseManager") as mock_db_manager,
        patch.dict(os.environ, {}, clear=True),
    ):
        mock_config = MagicMock()
        mock_config.database.get_connection_string.return_value = config_url
        mock_get_config.return_value = mock_config

        mock_db_instance = MagicMock()
        mock_db_instance.create_tables_async = AsyncMock()
        mock_db_manager.return_value = mock_db_instance

        await init_database(state)

        # Verify config method was called
        mock_config.database.get_connection_string.assert_called_once()
        mock_db_manager.assert_called_once_with(config_url, is_async=True)


@pytest.mark.asyncio
async def test_init_database_raises_on_missing_url():
    """Missing DATABASE_URL should raise ValueError"""
    from api.startup.database import init_database

    state = APIState()

    with patch("api.startup.database.get_config") as mock_get_config, patch.dict(os.environ, {}, clear=True):
        mock_config = MagicMock()
        mock_config.database = None  # No database config
        mock_get_config.return_value = mock_config

        with pytest.raises(ValueError, match="Database URL not configured"):
            await init_database(state)


@pytest.mark.asyncio
async def test_init_database_initializes_system_prompt_service():
    """System prompt service should be initialized after database"""
    from api.startup.database import init_database

    state = APIState()

    with (
        patch("api.startup.database.get_config") as mock_get_config,
        patch("api.startup.database.DatabaseManager") as mock_db_manager,
        patch("api.startup.database.SystemPromptService") as mock_prompt_service,
        patch.dict(os.environ, {"DATABASE_URL": "postgresql://localhost/test"}),
    ):
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        mock_db_instance = MagicMock()
        mock_db_instance.create_tables_async = AsyncMock()
        mock_db_manager.return_value = mock_db_instance

        await init_database(state)

        # Verify SystemPromptService was initialized with db_manager
        mock_prompt_service.assert_called_once_with(state.db_manager)
        assert state.system_prompt_service is not None


@pytest.mark.asyncio
async def test_init_database_logs_connection_info():
    """Should log database connection info (without credentials)"""
    from api.startup.database import init_database

    state = APIState()
    db_url = "postgresql://user:password@localhost:5432/testdb"

    with (
        patch("api.startup.database.get_config") as mock_get_config,
        patch("api.startup.database.DatabaseManager") as mock_db_manager,
        patch("api.startup.database.logger") as mock_logger,
        patch.dict(os.environ, {"DATABASE_URL": db_url}),
    ):
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        mock_db_instance = MagicMock()
        mock_db_instance.create_tables_async = AsyncMock()
        mock_db_manager.return_value = mock_db_instance

        await init_database(state)

        # Verify connection info was logged (without password)
        info_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any("localhost:5432/testdb" in msg for msg in info_calls)
