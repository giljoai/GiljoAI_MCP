"""
Async test utilities and helpers
"""

import asyncio
import functools
from typing import Any, Callable, Coroutine
import pytest


def async_test(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable:
    """Decorator to mark async functions as tests"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))
    return wrapper


class AsyncContextManager:
    """Helper for testing async context managers"""

    def __init__(self, manager):
        self.manager = manager
        self.entered = False
        self.exited = False

    async def __aenter__(self):
        self.entered = True
        self.result = await self.manager.__aenter__()
        return self.result

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.exited = True
        return await self.manager.__aexit__(exc_type, exc_val, exc_tb)


class AsyncMockManager:
    """Manager for async mocks and patches"""

    def __init__(self):
        self.patches = []
        self.mocks = []

    def add_mock(self, mock_obj):
        """Add a mock object to be cleaned up"""
        self.mocks.append(mock_obj)
        return mock_obj

    def add_patch(self, patch_obj):
        """Add a patch to be cleaned up"""
        self.patches.append(patch_obj)
        return patch_obj

    def cleanup(self):
        """Clean up all mocks and patches"""
        for patch in self.patches:
            try:
                patch.stop()
            except:
                pass

        for mock in self.mocks:
            try:
                mock.reset_mock()
            except:
                pass

        self.patches.clear()
        self.mocks.clear()


@pytest.fixture(scope="function")
def async_mock_manager():
    """Fixture providing async mock manager with automatic cleanup"""
    manager = AsyncMockManager()
    yield manager
    manager.cleanup()


class TimeoutHelper:
    """Helper for testing timeouts and timing"""

    @staticmethod
    async def wait_for_condition(
        condition_func: Callable[[], bool],
        timeout: float = 5.0,
        check_interval: float = 0.1
    ) -> bool:
        """Wait for a condition to become true"""
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            if condition_func():
                return True
            await asyncio.sleep(check_interval)

        return False

    @staticmethod
    async def wait_for_async_condition(
        condition_func: Callable[[], Coroutine[Any, Any, bool]],
        timeout: float = 5.0,
        check_interval: float = 0.1
    ) -> bool:
        """Wait for an async condition to become true"""
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            if await condition_func():
                return True
            await asyncio.sleep(check_interval)

        return False


class DatabaseTestHelper:
    """Helper for database testing operations"""

    @staticmethod
    async def count_records(session, model_class):
        """Count records in a table"""
        from sqlalchemy import select, func
        result = await session.execute(select(func.count()).select_from(model_class))
        return result.scalar()

    @staticmethod
    async def clear_table(session, model_class):
        """Clear all records from a table"""
        from sqlalchemy import delete
        await session.execute(delete(model_class))
        await session.commit()

    @staticmethod
    async def insert_test_data(session, model_class, data_list):
        """Insert multiple test records"""
        for data in data_list:
            if isinstance(data, dict):
                instance = model_class(**data)
            else:
                instance = data
            session.add(instance)
        await session.commit()


class WebSocketTestHelper:
    """Helper for WebSocket testing"""

    @staticmethod
    async def connect_and_test(uri: str, test_func: Callable):
        """Connect to WebSocket and run test function"""
        import websockets

        try:
            async with websockets.connect(uri) as websocket:
                return await test_func(websocket)
        except Exception as e:
            pytest.fail(f"WebSocket connection failed: {e}")

    @staticmethod
    async def send_and_receive(websocket, message: str, timeout: float = 5.0):
        """Send message and wait for response"""
        await websocket.send(message)
        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=timeout)
            return response
        except asyncio.TimeoutError:
            pytest.fail(f"No response received within {timeout} seconds")