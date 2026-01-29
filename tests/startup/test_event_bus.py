"""Tests for event bus initialization module"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.app import APIState


@pytest.mark.asyncio
async def test_init_event_bus_creates_event_bus():
    """Should create EventBus instance and set on state"""
    from api.startup.event_bus import init_event_bus

    state = APIState()
    state.websocket_manager = MagicMock()

    with patch('api.event_bus.EventBus') as mock_event_bus, \
         patch('api.websocket_event_listener.WebSocketEventListener') as mock_ws_listener:

        mock_event_bus_instance = MagicMock()
        mock_event_bus.return_value = mock_event_bus_instance

        # Need to mock the start() method as AsyncMock
        mock_listener_instance = MagicMock()
        mock_listener_instance.start = AsyncMock()
        mock_ws_listener.return_value = mock_listener_instance

        await init_event_bus(state)

        mock_event_bus.assert_called_once()
        assert state.event_bus is not None
        assert state.event_bus == mock_event_bus_instance


@pytest.mark.asyncio
async def test_init_event_bus_creates_websocket_listener():
    """Should create WebSocketEventListener with event_bus and websocket_manager"""
    from api.startup.event_bus import init_event_bus

    state = APIState()
    state.websocket_manager = MagicMock()

    with patch('api.event_bus.EventBus') as mock_event_bus, \
         patch('api.websocket_event_listener.WebSocketEventListener') as mock_ws_listener:

        mock_event_bus_instance = MagicMock()
        mock_event_bus.return_value = mock_event_bus_instance

        mock_listener_instance = MagicMock()
        mock_listener_instance.start = AsyncMock()
        mock_ws_listener.return_value = mock_listener_instance

        await init_event_bus(state)

        # Verify WebSocketEventListener was created with correct args
        mock_ws_listener.assert_called_once_with(
            mock_event_bus_instance,
            state.websocket_manager
        )


@pytest.mark.asyncio
async def test_init_event_bus_starts_websocket_listener():
    """Should call await ws_listener.start() to register handlers"""
    from api.startup.event_bus import init_event_bus

    state = APIState()
    state.websocket_manager = MagicMock()

    with patch('api.event_bus.EventBus'), \
         patch('api.websocket_event_listener.WebSocketEventListener') as mock_ws_listener:

        mock_listener_instance = MagicMock()
        mock_listener_instance.start = AsyncMock()
        mock_ws_listener.return_value = mock_listener_instance

        await init_event_bus(state)

        # Verify start() was awaited
        mock_listener_instance.start.assert_awaited_once()


@pytest.mark.asyncio
async def test_init_event_bus_logs_verbose_messages():
    """Should log verbose messages for debugging (Handover 0111)"""
    from api.startup.event_bus import init_event_bus

    state = APIState()
    state.websocket_manager = MagicMock()

    with patch('api.event_bus.EventBus') as mock_event_bus, \
         patch('api.websocket_event_listener.WebSocketEventListener') as mock_ws_listener, \
         patch('api.startup.event_bus.logger') as mock_logger:

        mock_event_bus_instance = MagicMock()
        mock_event_bus.return_value = mock_event_bus_instance

        mock_listener_instance = MagicMock()
        mock_listener_instance.start = AsyncMock()
        mock_ws_listener.return_value = mock_listener_instance

        await init_event_bus(state)

        # Verify verbose logging (Handover 0111 debugging)
        info_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any('STARTING EVENT BUS INITIALIZATION' in msg for msg in info_calls)
        assert any('EventBus imported successfully' in msg for msg in info_calls)
        assert any('WebSocketEventListener created' in msg for msg in info_calls)
        assert any('EVENT BUS INITIALIZATION COMPLETE' in msg for msg in info_calls)


@pytest.mark.asyncio
async def test_init_event_bus_raises_on_import_failure():
    """Should raise and log detailed error if EventBus import fails"""
    import sys
    from api.startup.event_bus import init_event_bus

    state = APIState()
    state.websocket_manager = MagicMock()

    # Temporarily remove api.event_bus from sys.modules to simulate import failure
    original_module = sys.modules.get('api.event_bus')
    if 'api.event_bus' in sys.modules:
        del sys.modules['api.event_bus']

    try:
        with patch.dict('sys.modules', {'api.event_bus': None}), \
             patch('api.startup.event_bus.logger') as mock_logger:

            with pytest.raises(ImportError):
                await init_event_bus(state)

            # Verify error logging
            error_calls = [call.args[0] for call in mock_logger.error.call_args_list]
            assert any('FAILED TO INITIALIZE EVENT BUS' in msg for msg in error_calls)
    finally:
        # Restore original module
        if original_module is not None:
            sys.modules['api.event_bus'] = original_module


@pytest.mark.asyncio
async def test_init_event_bus_raises_on_listener_start_failure():
    """Should raise if WebSocketEventListener.start() fails"""
    from api.startup.event_bus import init_event_bus

    state = APIState()
    state.websocket_manager = MagicMock()

    with patch('api.event_bus.EventBus'), \
         patch('api.websocket_event_listener.WebSocketEventListener') as mock_ws_listener:

        mock_listener_instance = MagicMock()
        mock_listener_instance.start = AsyncMock(side_effect=RuntimeError("Start failed"))
        mock_ws_listener.return_value = mock_listener_instance

        with pytest.raises(RuntimeError, match="Start failed"):
            await init_event_bus(state)
