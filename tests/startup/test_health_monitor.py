"""Tests for health monitor initialization module"""
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

from api.app import APIState


@pytest.mark.asyncio
async def test_init_health_monitor_starts_when_enabled():
    """Should start health monitor when enabled=true in config"""
    from api.startup.health_monitor import init_health_monitor

    state = APIState()
    state.db_manager = MagicMock()
    state.websocket_manager = MagicMock()
    state.config = MagicMock()
    state.config.config_path = Path("config.yaml")

    health_config_yaml = """
health_monitoring:
  enabled: true
  scan_interval_seconds: 300
  auto_fail_on_timeout: false
  notify_orchestrator: true
  timeouts:
    waiting_timeout: 2
    active_no_progress: 5
    heartbeat_timeout: 10
    orchestrator: 15
    implementer: 10
"""

    with patch('api.startup.health_monitor.open', mock_open(read_data=health_config_yaml)), \
         patch('api.startup.health_monitor.AgentHealthMonitor') as mock_health_monitor, \
         patch('api.startup.health_monitor.HealthCheckConfig'):

        mock_monitor_instance = MagicMock()
        mock_monitor_instance.start = AsyncMock()
        mock_health_monitor.return_value = mock_monitor_instance

        await init_health_monitor(state)

        # Verify monitor was created and started
        mock_health_monitor.assert_called_once()
        mock_monitor_instance.start.assert_awaited_once()
        assert state.health_monitor is not None


@pytest.mark.asyncio
async def test_init_health_monitor_skips_when_disabled():
    """Should skip health monitor when enabled=false in config"""
    from api.startup.health_monitor import init_health_monitor

    state = APIState()
    state.db_manager = MagicMock()
    state.websocket_manager = MagicMock()
    state.config = MagicMock()
    state.config.config_path = Path("config.yaml")

    health_config_yaml = """
health_monitoring:
  enabled: false
"""

    with patch('api.startup.health_monitor.open', mock_open(read_data=health_config_yaml)), \
         patch('api.startup.health_monitor.AgentHealthMonitor') as mock_health_monitor:

        await init_health_monitor(state)

        # Verify monitor was NOT created
        mock_health_monitor.assert_not_called()
        assert state.health_monitor is None


@pytest.mark.asyncio
async def test_init_health_monitor_builds_correct_config():
    """Should build HealthCheckConfig from YAML values"""
    from api.startup.health_monitor import init_health_monitor

    state = APIState()
    state.db_manager = MagicMock()
    state.websocket_manager = MagicMock()
    state.config = MagicMock()
    state.config.config_path = Path("config.yaml")

    health_config_yaml = """
health_monitoring:
  enabled: true
  scan_interval_seconds: 600
  auto_fail_on_timeout: true
  notify_orchestrator: false
  timeouts:
    waiting_timeout: 3
    active_no_progress: 7
    heartbeat_timeout: 12
    orchestrator: 20
    implementer: 15
    tester: 10
    analyzer: 8
    reviewer: 9
    documenter: 6
"""

    with patch('api.startup.health_monitor.open', mock_open(read_data=health_config_yaml)), \
         patch('api.startup.health_monitor.AgentHealthMonitor'), \
         patch('api.startup.health_monitor.HealthCheckConfig') as mock_config:

        await init_health_monitor(state)

        # Verify HealthCheckConfig was called with correct values
        mock_config.assert_called_once()
        call_kwargs = mock_config.call_args.kwargs

        assert call_kwargs['waiting_timeout_minutes'] == 3
        assert call_kwargs['active_no_progress_minutes'] == 7
        assert call_kwargs['heartbeat_timeout_minutes'] == 12
        assert call_kwargs['scan_interval_seconds'] == 600
        assert call_kwargs['auto_fail_on_timeout'] is True
        assert call_kwargs['notify_orchestrator'] is False
        assert call_kwargs['timeout_overrides']['orchestrator'] == 20
        assert call_kwargs['timeout_overrides']['implementer'] == 15


@pytest.mark.asyncio
async def test_init_health_monitor_uses_defaults_when_config_missing():
    """Should use default values when health_monitoring section missing"""
    from api.startup.health_monitor import init_health_monitor

    state = APIState()
    state.db_manager = MagicMock()
    state.websocket_manager = MagicMock()
    state.config = MagicMock()
    state.config.config_path = Path("config.yaml")

    minimal_config_yaml = """
server:
  host: localhost
"""

    with patch('api.startup.health_monitor.open', mock_open(read_data=minimal_config_yaml)), \
         patch('api.startup.health_monitor.AgentHealthMonitor') as mock_health_monitor, \
         patch('api.startup.health_monitor.HealthCheckConfig'):

        mock_monitor_instance = MagicMock()
        mock_monitor_instance.start = AsyncMock()
        mock_health_monitor.return_value = mock_monitor_instance

        await init_health_monitor(state)

        # Should start with defaults (enabled defaults to True)
        mock_health_monitor.assert_called_once()


@pytest.mark.asyncio
async def test_init_health_monitor_continues_on_error():
    """Should log warning and continue if health monitor fails to start"""
    from api.startup.health_monitor import init_health_monitor

    state = APIState()
    state.db_manager = MagicMock()
    state.websocket_manager = MagicMock()
    state.config = MagicMock()
    state.config.config_path = Path("config.yaml")

    with patch('api.startup.health_monitor.open', side_effect=FileNotFoundError), \
         patch('api.startup.health_monitor.logger') as mock_logger:

        # Should not raise, just log warning
        await init_health_monitor(state)

        # Verify warning was logged
        warning_calls = [call.args[0] for call in mock_logger.warning.call_args_list]
        assert any('Continuing without health monitoring' in msg for msg in warning_calls)


@pytest.mark.asyncio
async def test_init_health_monitor_passes_dependencies():
    """Should pass db_manager, ws_manager, and config to AgentHealthMonitor"""
    from api.startup.health_monitor import init_health_monitor

    state = APIState()
    state.db_manager = MagicMock()
    state.websocket_manager = MagicMock()
    state.config = MagicMock()
    state.config.config_path = Path("config.yaml")

    health_config_yaml = """
health_monitoring:
  enabled: true
"""

    with patch('api.startup.health_monitor.open', mock_open(read_data=health_config_yaml)), \
         patch('api.startup.health_monitor.AgentHealthMonitor') as mock_health_monitor, \
         patch('api.startup.health_monitor.HealthCheckConfig') as mock_config:

        mock_config_instance = MagicMock()
        mock_config.return_value = mock_config_instance

        mock_monitor_instance = MagicMock()
        mock_monitor_instance.start = AsyncMock()
        mock_health_monitor.return_value = mock_monitor_instance

        await init_health_monitor(state)

        # Verify AgentHealthMonitor received correct dependencies
        mock_health_monitor.assert_called_once_with(
            db_manager=state.db_manager,
            ws_manager=state.websocket_manager,
            config=mock_config_instance
        )
