"""Tests for shutdown module"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.app import APIState


@pytest.mark.asyncio
async def test_shutdown_cancels_heartbeat_task():
    """Should cancel heartbeat task if present"""
    from api.startup.shutdown import shutdown

    state = APIState()

    # Create a proper async task that can be cancelled
    async def mock_task():
        while True:
            await asyncio.sleep(1)

    state.heartbeat_task = asyncio.create_task(mock_task())

    await shutdown(state)

    # Verify task was cancelled
    assert state.heartbeat_task.cancelled()


@pytest.mark.asyncio
async def test_shutdown_cancels_cleanup_task():
    """Should cancel cleanup task if present"""
    from api.startup.shutdown import shutdown

    state = APIState()

    # Create a proper async task that can be cancelled
    async def mock_task():
        while True:
            await asyncio.sleep(1)

    state.cleanup_task = asyncio.create_task(mock_task())

    await shutdown(state)

    # Verify task was cancelled
    assert state.cleanup_task.cancelled()


@pytest.mark.asyncio
async def test_shutdown_cancels_metrics_sync_task():
    """Should cancel metrics sync task if present"""
    from api.startup.shutdown import shutdown

    state = APIState()

    # Create a proper async task that can be cancelled
    async def mock_task():
        while True:
            await asyncio.sleep(1)

    state.metrics_sync_task = asyncio.create_task(mock_task())

    await shutdown(state)

    # Verify task was cancelled
    assert state.metrics_sync_task.cancelled()


@pytest.mark.asyncio
async def test_shutdown_handles_missing_tasks():
    """Should handle gracefully when tasks are None"""
    from api.startup.shutdown import shutdown

    state = APIState()
    state.heartbeat_task = None
    state.cleanup_task = None
    state.metrics_sync_task = None
    state.health_monitor = None
    state.db_manager = None
    state.connections = {}

    # Should not raise any errors
    await shutdown(state)


@pytest.mark.asyncio
async def test_shutdown_stops_health_monitor():
    """Should call health_monitor.stop() if monitor exists"""
    from api.startup.shutdown import shutdown

    state = APIState()
    state.health_monitor = MagicMock()
    state.health_monitor.stop = AsyncMock()
    state.connections = {}

    await shutdown(state)

    # Verify stop was called
    state.health_monitor.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_shutdown_closes_websocket_connections():
    """Should close all WebSocket connections in state.connections"""
    from api.startup.shutdown import shutdown

    state = APIState()

    # Create mock WebSocket connections
    mock_ws1 = MagicMock()
    mock_ws1.close = AsyncMock()
    mock_ws2 = MagicMock()
    mock_ws2.close = AsyncMock()

    state.connections = {"client1": mock_ws1, "client2": mock_ws2}

    await shutdown(state)

    # Verify both connections were closed
    mock_ws1.close.assert_awaited_once()
    mock_ws2.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_shutdown_closes_database_connection():
    """Should call db_manager.close_async() if db_manager exists"""
    from api.startup.shutdown import shutdown

    state = APIState()
    state.db_manager = MagicMock()
    state.db_manager.close_async = AsyncMock()
    state.connections = {}

    await shutdown(state)

    # Verify database connection was closed
    state.db_manager.close_async.assert_awaited_once()


@pytest.mark.asyncio
async def test_shutdown_continues_on_task_cancel_error():
    """Should handle CancelledError gracefully when awaiting cancelled tasks"""
    from api.startup.shutdown import shutdown

    state = APIState()

    # Create a proper async task that can be cancelled
    async def mock_task():
        while True:
            await asyncio.sleep(1)

    state.heartbeat_task = asyncio.create_task(mock_task())
    state.connections = {}

    # Should not propagate CancelledError
    await shutdown(state)

    # Test passes if no exception raised - task should be cancelled
    assert state.heartbeat_task.cancelled()


@pytest.mark.asyncio
async def test_shutdown_continues_on_error():
    """Should log errors but continue shutdown process"""
    from api.startup.shutdown import shutdown

    state = APIState()
    state.health_monitor = MagicMock()
    state.health_monitor.stop = AsyncMock(side_effect=RuntimeError("Stop failed"))
    state.connections = {}
    state.db_manager = MagicMock()
    state.db_manager.close_async = AsyncMock()

    with patch("api.startup.shutdown.logger") as mock_logger:
        # Should not raise, just log error
        await shutdown(state)

        # Verify error was logged via logger.exception (used by _run_with_timeout)
        exc_calls = [call.args[0] for call in mock_logger.exception.call_args_list]
        assert any("Error in shutdown step" in msg for msg in exc_calls)

        # Database should still close despite health monitor error
        state.db_manager.close_async.assert_awaited_once()


@pytest.mark.asyncio
async def test_shutdown_logs_progress():
    """Should log shutdown progress messages"""
    from api.startup.shutdown import shutdown

    state = APIState()

    # Create a proper async task mock that can be cancelled and awaited
    async def mock_task():
        while True:
            await asyncio.sleep(1)

    # Start the task so it's a real asyncio.Task
    state.heartbeat_task = asyncio.create_task(mock_task())
    state.cleanup_task = None
    state.metrics_sync_task = None
    state.health_monitor = None
    state.connections = {}
    state.db_manager = MagicMock()
    state.db_manager.close_async = AsyncMock()
    state.websocket_broker = None  # Avoid WebSocket broker shutdown logs

    with patch("api.startup.shutdown.logger") as mock_logger:
        await shutdown(state)

        # Verify shutdown messages were logged (progress steps use print(), not logger)
        info_calls = [call.args[0] for call in mock_logger.info.call_args_list]

        # Check for the actual logger.info messages from shutdown.py
        assert any("Shutting down GiljoAI MCP API" in msg for msg in info_calls)
        assert any("API shutdown complete" in msg for msg in info_calls)


@pytest.mark.asyncio
async def test_shutdown_all_tasks_in_order():
    """Should perform shutdown steps in correct order"""
    from api.startup.shutdown import shutdown

    state = APIState()
    execution_order = []

    # Create a proper async task
    async def mock_task():
        while True:
            await asyncio.sleep(1)

    # Track when task is cancelled
    original_task = asyncio.create_task(mock_task())

    # Wrap cancel to track execution
    original_cancel = original_task.cancel

    def tracked_cancel():
        execution_order.append("cancel_heartbeat")
        return original_cancel()

    original_task.cancel = tracked_cancel
    state.heartbeat_task = original_task

    state.health_monitor = MagicMock()
    state.health_monitor.stop = AsyncMock(side_effect=lambda: execution_order.append("stop_health_monitor"))

    mock_ws = MagicMock()
    mock_ws.close = AsyncMock(side_effect=lambda: execution_order.append("close_websocket"))
    state.connections = {"client1": mock_ws}

    state.db_manager = MagicMock()
    state.db_manager.close_async = AsyncMock(side_effect=lambda: execution_order.append("close_database"))

    await shutdown(state)

    # Verify order: tasks cancelled → health monitor stopped → websockets closed → database closed
    assert execution_order.index("cancel_heartbeat") < execution_order.index("stop_health_monitor")
    assert execution_order.index("stop_health_monitor") < execution_order.index("close_websocket")
    assert execution_order.index("close_websocket") < execution_order.index("close_database")
