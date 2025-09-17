"""
Mock servers and external service mocks for testing
"""

import asyncio
import json
from typing import Dict, Any, Optional, Callable
from unittest.mock import AsyncMock, MagicMock
import pytest


class MockAPIServer:
    """Mock API server for testing external API calls"""

    def __init__(self, port: int = 8999):
        self.port = port
        self.routes = {}
        self.server = None
        self.app = None

    def add_route(self, method: str, path: str, response_data: Dict[str, Any], status_code: int = 200):
        """Add a mock route"""
        self.routes[f"{method.upper()}:{path}"] = {
            "response": response_data,
            "status_code": status_code
        }

    async def start(self):
        """Start the mock server"""
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse
        import uvicorn

        self.app = FastAPI()

        @self.app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
        async def mock_handler(path: str, request):
            method = request.method
            route_key = f"{method}:/{path}"

            if route_key in self.routes:
                route_data = self.routes[route_key]
                return JSONResponse(
                    content=route_data["response"],
                    status_code=route_data["status_code"]
                )
            else:
                return JSONResponse(
                    content={"error": "Route not found"},
                    status_code=404
                )

        config = uvicorn.Config(self.app, host="127.0.0.1", port=self.port, log_level="error")
        self.server = uvicorn.Server(config)

        # Start server in background
        self.server_task = asyncio.create_task(self.server.serve())

    async def stop(self):
        """Stop the mock server"""
        if self.server:
            self.server.should_exit = True
            await self.server_task


class MockWebSocketServer:
    """Mock WebSocket server for testing"""

    def __init__(self, port: int = 8998):
        self.port = port
        self.server = None
        self.connections = set()
        self.message_handlers = []

    def add_message_handler(self, handler: Callable):
        """Add a message handler function"""
        self.message_handlers.append(handler)

    async def handle_connection(self, websocket, path):
        """Handle WebSocket connection"""
        self.connections.add(websocket)
        try:
            async for message in websocket:
                # Process message through handlers
                response = None
                for handler in self.message_handlers:
                    response = await handler(message) if asyncio.iscoroutinefunction(handler) else handler(message)
                    if response:
                        await websocket.send(response)
                        break
        except Exception:
            pass
        finally:
            self.connections.discard(websocket)

    async def start(self):
        """Start the WebSocket server"""
        import websockets

        self.server = await websockets.serve(
            self.handle_connection,
            "localhost",
            self.port
        )

    async def stop(self):
        """Stop the WebSocket server"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()

    async def broadcast(self, message: str):
        """Broadcast message to all connections"""
        if self.connections:
            await asyncio.gather(
                *[conn.send(message) for conn in self.connections],
                return_exceptions=True
            )


class MockDatabaseManager:
    """Mock database manager for testing without real database"""

    def __init__(self):
        self.data = {}
        self.is_connected = False

    async def create_tables_async(self):
        """Mock table creation"""
        self.data = {
            'projects': [],
            'agents': [],
            'messages': [],
            'tasks': []
        }

    async def get_session_async(self):
        """Mock session getter"""
        return MockAsyncSession(self.data)

    async def close_async(self):
        """Mock close"""
        self.is_connected = False


class MockAsyncSession:
    """Mock async session for database operations"""

    def __init__(self, data_store: Dict):
        self.data = data_store
        self.pending_adds = []
        self.committed = False

    def add(self, instance):
        """Mock add operation"""
        self.pending_adds.append(instance)

    async def commit(self):
        """Mock commit operation"""
        # Simulate committing pending adds
        for item in self.pending_adds:
            table_name = f"{type(item).__name__.lower()}s"
            if table_name in self.data:
                self.data[table_name].append(item)

        self.pending_adds.clear()
        self.committed = True

    async def rollback(self):
        """Mock rollback operation"""
        self.pending_adds.clear()

    async def execute(self, query):
        """Mock query execution"""
        # Return mock result
        return MockResult([])

    async def close(self):
        """Mock session close"""
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


class MockResult:
    """Mock query result"""

    def __init__(self, data):
        self.data = data

    def scalar(self):
        """Return scalar result"""
        return len(self.data) if self.data else 0

    def fetchall(self):
        """Return all results"""
        return self.data

    def fetchone(self):
        """Return first result"""
        return self.data[0] if self.data else None


@pytest.fixture(scope="function")
async def mock_api_server():
    """Fixture providing mock API server"""
    server = MockAPIServer()
    await server.start()
    yield server
    await server.stop()


@pytest.fixture(scope="function")
async def mock_websocket_server():
    """Fixture providing mock WebSocket server"""
    server = MockWebSocketServer()
    await server.start()
    yield server
    await server.stop()


@pytest.fixture(scope="function")
def mock_db_manager():
    """Fixture providing mock database manager"""
    return MockDatabaseManager()


class ExternalServiceMocks:
    """Collection of mocks for external services"""

    @staticmethod
    def mock_http_client():
        """Create mock HTTP client"""
        mock_client = AsyncMock()
        mock_client.get.return_value.status_code = 200
        mock_client.get.return_value.json.return_value = {"status": "ok"}
        mock_client.post.return_value.status_code = 201
        mock_client.post.return_value.json.return_value = {"id": "123", "status": "created"}
        return mock_client

    @staticmethod
    def mock_message_queue():
        """Create mock message queue"""
        mock_queue = MagicMock()
        mock_queue.send_message = AsyncMock(return_value=True)
        mock_queue.receive_message = AsyncMock(return_value={"id": "123", "content": "test"})
        mock_queue.acknowledge_message = AsyncMock(return_value=True)
        return mock_queue

    @staticmethod
    def mock_file_system():
        """Create mock file system operations"""
        mock_fs = MagicMock()
        mock_fs.read_file = AsyncMock(return_value="file content")
        mock_fs.write_file = AsyncMock(return_value=True)
        mock_fs.file_exists = MagicMock(return_value=True)
        mock_fs.create_directory = AsyncMock(return_value=True)
        return mock_fs