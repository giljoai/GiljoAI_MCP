"""
Mock WebSocket Server for Testing
Provides a standalone WebSocket server for isolated testing
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import websockets
from websockets.server import WebSocketServerProtocol


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Client:
    """Represents a connected WebSocket client"""

    id: str
    websocket: WebSocketServerProtocol
    connected_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    authenticated: bool = False
    api_key: Optional[str] = None
    messages_sent: int = 0
    messages_received: int = 0

    def is_alive(self, timeout: float = 60) -> bool:
        """Check if client is still alive based on heartbeat"""
        return (time.time() - self.last_heartbeat) < timeout


class MockWebSocketManager:
    """Manages WebSocket connections and message routing"""

    def __init__(self):
        self.clients: dict[str, Client] = {}
        self.message_queue: dict[str, list] = {}  # Offline message queue
        self.broadcast_history: list = []
        self.server = None
        self.running = False

        # Simulated data
        self.agents = {
            "agent_001": {"name": "ws_implementer", "status": "pending"},
            "agent_002": {"name": "frontend_implementer", "status": "pending"},
            "agent_003": {"name": "integration_tester", "status": "in_progress"},
        }

        self.operations = {}  # Track long-running operations

    async def handle_connection(self, websocket: WebSocketServerProtocol):
        """Handle new WebSocket connection"""
        try:
            # Parse client ID and auth from path/query
            path = websocket.path if hasattr(websocket, "path") else "/unknown"
            client_id, api_key = self._parse_connection_info(path)

            # Validate API key if provided
            if api_key and not self._validate_api_key(api_key):
                await websocket.send(
                    json.dumps({"type": "error", "error_code": "AUTH_FAILED", "message": "Invalid API key"})
                )
                await websocket.close(code=1008, reason="Invalid authentication")
                return

            # Create client instance
            client = Client(id=client_id, websocket=websocket, api_key=api_key, authenticated=bool(api_key))

            # Register client
            self.clients[client_id] = client
            logger.info(f"Client {client_id} connected")

            # Send welcome message
            await self._send_welcome(client)

            # Send any queued messages
            await self._deliver_queued_messages(client)

            # Start heartbeat task
            heartbeat_task = asyncio.create_task(self._heartbeat_loop(client))

            try:
                # Handle incoming messages
                async for message in websocket:
                    await self._handle_message(client, message)

            except websockets.exceptions.ConnectionClosed:
                logger.info(f"Client {client_id} disconnected")

        except Exception as e:
            logger.exception(f"Error handling connection: {e}")

        finally:
            # Clean up
            heartbeat_task.cancel()
            if client_id in self.clients:
                del self.clients[client_id]

    def _parse_connection_info(self, path: str) -> tuple[str, Optional[str]]:
        """Parse client ID and API key from connection path"""
        # Example: /ws/client_001?api_key=xxx
        parts = path.strip("/").split("/")
        client_id = parts[-1].split("?")[0] if parts else "unknown"

        # Extract API key from query params
        api_key = None
        if "?" in path:
            query = path.split("?")[1]
            for param in query.split("&"):
                if param.startswith("api_key="):
                    api_key = param.split("=")[1]
                    break

        return client_id, api_key

    def _validate_api_key(self, api_key: str) -> bool:
        """Validate API key (mock implementation)"""
        # Accept any key starting with "test_" for testing
        return api_key.startswith("test_") or api_key == "valid_key"

    async def _send_welcome(self, client: Client):
        """Send welcome message to new client"""
        welcome = {
            "type": "welcome",
            "client_id": client.id,
            "authenticated": client.authenticated,
            "timestamp": time.time(),
            "server_time": datetime.now().isoformat(),
        }
        await client.websocket.send(json.dumps(welcome))

    async def _deliver_queued_messages(self, client: Client):
        """Deliver any messages queued while client was offline"""
        if client.id in self.message_queue:
            messages = self.message_queue[client.id]
            logger.info(f"Delivering {len(messages)} queued messages to {client.id}")

            for msg in messages:
                await client.websocket.send(json.dumps(msg))

            # Clear queue after delivery
            del self.message_queue[client.id]

    async def _heartbeat_loop(self, client: Client):
        """Send periodic heartbeat to client"""
        try:
            while client.id in self.clients:
                await asyncio.sleep(30)  # 30-second interval

                ping_msg = {"type": "ping", "timestamp": time.time()}

                try:
                    await client.websocket.send(json.dumps(ping_msg))
                except:
                    # Connection likely closed
                    break

        except asyncio.CancelledError:
            pass

    async def _handle_message(self, client: Client, message: str):
        """Handle incoming message from client"""
        try:
            data = json.loads(message)
            msg_type = data.get("type")

            client.messages_received += 1

            # Handle different message types
            if msg_type == "ping":
                await self._handle_ping(client, data)
            elif msg_type == "pong":
                await self._handle_pong(client, data)
            elif msg_type == "broadcast":
                await self._handle_broadcast(client, data)
            elif msg_type == "agent_status_change":
                await self._handle_agent_status_change(client, data)
            elif msg_type == "start_operation":
                await self._handle_start_operation(client, data)
            elif msg_type == "message":
                await self._handle_message_relay(client, data)
            elif msg_type == "auth_test":
                await self._handle_auth_test(client, data)
            else:
                # Echo unknown messages back
                await client.websocket.send(message)

        except json.JSONDecodeError:
            logger.exception(f"Invalid JSON from {client.id}: {message}")
            await client.websocket.send(
                json.dumps({"type": "error", "error_code": "INVALID_JSON", "message": "Invalid JSON format"})
            )

    async def _handle_ping(self, client: Client, data: dict):
        """Handle ping message"""
        pong = {"type": "pong", "timestamp": time.time(), "echo": data.get("timestamp")}
        await client.websocket.send(json.dumps(pong))

    async def _handle_pong(self, client: Client, data: dict):
        """Handle pong message (heartbeat response)"""
        client.last_heartbeat = time.time()

    async def _handle_broadcast(self, client: Client, data: dict):
        """Handle broadcast message"""
        broadcast_msg = {
            "type": "broadcast",
            "from": client.id,
            "content": data.get("content"),
            "timestamp": time.time(),
        }

        self.broadcast_history.append(broadcast_msg)

        # Send to all connected clients except sender
        tasks = []
        for other_client in self.clients.values():
            if other_client.id != client.id:
                tasks.append(other_client.websocket.send(json.dumps(broadcast_msg)))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _handle_agent_status_change(self, client: Client, data: dict):
        """Handle agent status change and broadcast update"""
        agent_id = data.get("agent_id")
        new_status = data.get("new_status")
        old_status = data.get("old_status")

        # Update internal state
        if agent_id in self.agents:
            self.agents[agent_id]["status"] = new_status

        # Broadcast status change to all clients
        update_msg = {
            "type": "agent_status_update",
            "agent_id": agent_id,
            "old_status": old_status,
            "new_status": new_status,
            "timestamp": time.time(),
        }

        await self._broadcast_to_all(update_msg)

    async def _handle_start_operation(self, client: Client, data: dict):
        """Handle start of long-running operation"""
        operation_id = data.get("operation_id", f"op_{time.time()}")

        # Create operation tracker
        self.operations[operation_id] = {
            "id": operation_id,
            "client_id": client.id,
            "started_at": time.time(),
            "progress": 0,
        }

        # Start progress simulation
        asyncio.create_task(self._simulate_operation_progress(operation_id))

        # Send confirmation
        await client.websocket.send(
            json.dumps({"type": "operation_started", "operation_id": operation_id, "timestamp": time.time()})
        )

    async def _simulate_operation_progress(self, operation_id: str):
        """Simulate progress updates for an operation"""
        if operation_id not in self.operations:
            return

        operation = self.operations[operation_id]
        client_id = operation["client_id"]

        # Send progress updates
        for percentage in range(10, 101, 10):
            await asyncio.sleep(0.5)  # Simulate work

            if client_id not in self.clients:
                break

            progress_msg = {
                "type": "progress",
                "operation_id": operation_id,
                "percentage": percentage,
                "message": f"Processing... {percentage}%",
                "timestamp": time.time(),
            }

            client = self.clients.get(client_id)
            if client:
                try:
                    await client.websocket.send(json.dumps(progress_msg))
                except:
                    break

        # Clean up
        if operation_id in self.operations:
            del self.operations[operation_id]

    async def _handle_message_relay(self, client: Client, data: dict):
        """Relay message to specific client"""
        target_id = data.get("to")

        relay_msg = {"type": "message", "from": client.id, "content": data.get("content"), "timestamp": time.time()}

        if target_id in self.clients:
            # Client is online, deliver immediately
            target = self.clients[target_id]
            await target.websocket.send(json.dumps(relay_msg))
        else:
            # Client is offline, queue the message
            if target_id not in self.message_queue:
                self.message_queue[target_id] = []
            self.message_queue[target_id].append(relay_msg)

            # Notify sender that message was queued
            await client.websocket.send(
                json.dumps({"type": "message_queued", "target": target_id, "timestamp": time.time()})
            )

    async def _handle_auth_test(self, client: Client, data: dict):
        """Handle authentication test"""
        response = {
            "type": "auth_response",
            "authenticated": client.authenticated,
            "client_id": client.id,
            "data": data.get("data"),
            "timestamp": time.time(),
        }
        await client.websocket.send(json.dumps(response))

    async def _broadcast_to_all(self, message: dict):
        """Broadcast message to all connected clients"""
        tasks = []
        for client in self.clients.values():
            tasks.append(client.websocket.send(json.dumps(message)))
            client.messages_sent += 1

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Log any failures
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                client_id = list(self.clients.keys())[i]
                logger.error(f"Failed to send to {client_id}: {result}")

    async def simulate_disconnection(self, client_id: str):
        """Simulate client disconnection for testing"""
        if client_id in self.clients:
            client = self.clients[client_id]
            await client.websocket.close()

    def get_stats(self) -> dict[str, Any]:
        """Get server statistics"""
        return {
            "connected_clients": len(self.clients),
            "queued_messages": sum(len(q) for q in self.message_queue.values()),
            "active_operations": len(self.operations),
            "total_broadcasts": len(self.broadcast_history),
            "clients": {
                client_id: {
                    "connected_at": client.connected_at,
                    "authenticated": client.authenticated,
                    "messages_sent": client.messages_sent,
                    "messages_received": client.messages_received,
                    "is_alive": client.is_alive(),
                }
                for client_id, client in self.clients.items()
            },
        }


async def run_mock_server(host: str = "localhost", port: int = 8001):
    """Run the mock WebSocket server"""
    manager = MockWebSocketManager()

    logger.info(f"Starting mock WebSocket server on {host}:{port}")

    async with websockets.serve(
        manager.handle_connection, host, port, ping_interval=None, ping_timeout=None  # We handle our own heartbeat
    ):
        manager.running = True
        logger.info(f"Mock WebSocket server listening on ws://{host}:{port}")

        # Keep server running
        try:
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            logger.info("Shutting down mock server")
            manager.running = False


if __name__ == "__main__":
    # Run mock server for testing
    asyncio.run(run_mock_server())
