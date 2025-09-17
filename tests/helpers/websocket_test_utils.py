"""
WebSocket Testing Utilities
Helper functions and mocks for WebSocket integration testing
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

import websockets
from websockets.server import WebSocketServerProtocol


@dataclass
class MockMessage:
    """Mock WebSocket message for testing"""

    type: str
    content: dict
    timestamp: float = field(default_factory=time.time)
    client_id: Optional[str] = None

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(
            {"type": self.type, "content": self.content, "timestamp": self.timestamp, "client_id": self.client_id}
        )

    @classmethod
    def from_json(cls, json_str: str) -> "MockMessage":
        """Create from JSON string"""
        data = json.loads(json_str)
        return cls(**data)


class MockWebSocketServer:
    """Mock WebSocket server for testing"""

    def __init__(self, host: str = "localhost", port: int = 8001):
        self.host = host
        self.port = port
        self.clients: dict[str, WebSocketServerProtocol] = {}
        self.message_history: list[MockMessage] = []
        self.server = None
        self.broadcast_delay = 0  # Artificial delay for testing

    async def handler(self, websocket: WebSocketServerProtocol, path: str):
        """Handle WebSocket connections"""
        # Extract client ID from path
        client_id = path.strip("/").split("/")[-1] if path else "unknown"

        # Store client connection
        self.clients[client_id] = websocket

        try:
            # Send welcome message
            await websocket.send(json.dumps({"type": "welcome", "client_id": client_id, "timestamp": time.time()}))

            # Handle messages
            async for message in websocket:
                msg = MockMessage.from_json(message)
                msg.client_id = client_id
                self.message_history.append(msg)

                # Handle different message types
                if msg.type == "ping":
                    await websocket.send(json.dumps({"type": "pong", "timestamp": time.time()}))
                elif msg.type == "broadcast":
                    await self.broadcast(msg, exclude_sender=True)
                else:
                    # Echo back for testing
                    await websocket.send(message)

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            del self.clients[client_id]

    async def broadcast(self, message: MockMessage, exclude_sender: bool = False):
        """Broadcast message to all connected clients"""
        if self.broadcast_delay:
            await asyncio.sleep(self.broadcast_delay)

        tasks = []
        for client_id, ws in self.clients.items():
            if exclude_sender and client_id == message.client_id:
                continue
            tasks.append(ws.send(message.to_json()))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def start(self):
        """Start the mock server"""
        self.server = await websockets.serve(self.handler, self.host, self.port)

    async def stop(self):
        """Stop the mock server"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()


class ConnectionSimulator:
    """Simulate various network conditions"""

    def __init__(self):
        self.packet_loss_rate = 0.0
        self.latency_ms = 0
        self.jitter_ms = 0
        self.bandwidth_limit_kbps = None

    async def simulate_latency(self):
        """Add simulated network latency"""
        if self.latency_ms:
            base_delay = self.latency_ms / 1000.0
            if self.jitter_ms:
                import random

                jitter = random.uniform(-self.jitter_ms / 1000.0, self.jitter_ms / 1000.0)
                base_delay += jitter
            await asyncio.sleep(base_delay)

    def should_drop_packet(self) -> bool:
        """Determine if packet should be dropped"""
        if self.packet_loss_rate:
            import random

            return random.random() < self.packet_loss_rate
        return False

    async def throttle_bandwidth(self, data_size: int):
        """Simulate bandwidth limitations"""
        if self.bandwidth_limit_kbps:
            bytes_per_second = self.bandwidth_limit_kbps * 125  # kbps to bytes/sec
            delay = data_size / bytes_per_second
            await asyncio.sleep(delay)


class MessageValidator:
    """Validate WebSocket messages against schemas"""

    SCHEMAS = {
        "agent_status_update": {
            "required": ["type", "agent_id", "status", "timestamp"],
            "status_values": ["pending", "in_progress", "completed", "error"],
        },
        "new_message": {
            "required": ["type", "id", "from", "to", "content", "timestamp"],
        },
        "progress": {"required": ["type", "operation_id", "percentage", "timestamp"], "percentage_range": (0, 100)},
        "error": {
            "required": ["type", "error_code", "message", "timestamp"],
        },
    }

    @classmethod
    def validate(cls, message: dict, message_type: str) -> tuple[bool, str]:
        """Validate message against schema"""
        if message_type not in cls.SCHEMAS:
            return True, "No schema defined"

        schema = cls.SCHEMAS[message_type]

        # Check required fields
        if "required" in schema:
            for field in schema["required"]:
                if field not in message:
                    return False, f"Missing required field: {field}"

        # Check status values
        if "status_values" in schema and "status" in message:
            if message["status"] not in schema["status_values"]:
                return False, f"Invalid status: {message['status']}"

        # Check percentage range
        if "percentage_range" in schema and "percentage" in message:
            min_val, max_val = schema["percentage_range"]
            if not min_val <= message["percentage"] <= max_val:
                return False, f"Percentage out of range: {message['percentage']}"

        return True, "Valid"


class LatencyTracker:
    """Track and analyze latency metrics"""

    def __init__(self):
        self.measurements: list[float] = []
        self.timestamps: list[float] = []

    def add_measurement(self, latency_ms: float):
        """Add a latency measurement"""
        self.measurements.append(latency_ms)
        self.timestamps.append(time.time())

    def get_average(self) -> float:
        """Get average latency"""
        if not self.measurements:
            return 0
        return sum(self.measurements) / len(self.measurements)

    def get_p95(self) -> float:
        """Get 95th percentile latency"""
        if not self.measurements:
            return 0
        sorted_measurements = sorted(self.measurements)
        index = int(len(sorted_measurements) * 0.95)
        return sorted_measurements[index]

    def get_max(self) -> float:
        """Get maximum latency"""
        return max(self.measurements) if self.measurements else 0

    def meets_sla(self, target_ms: float, percentile: float = 0.95) -> bool:
        """Check if latency meets SLA target"""
        if not self.measurements:
            return True
        sorted_measurements = sorted(self.measurements)
        index = int(len(sorted_measurements) * percentile)
        return sorted_measurements[index] <= target_ms


class ReconnectTracker:
    """Track reconnection attempts and patterns"""

    def __init__(self):
        self.attempts: list[dict] = []
        self.successful_reconnects = 0
        self.failed_reconnects = 0

    def record_attempt(self, attempt_number: int, wait_time: float, success: bool):
        """Record a reconnection attempt"""
        self.attempts.append(
            {"attempt": attempt_number, "wait_time": wait_time, "success": success, "timestamp": time.time()}
        )

        if success:
            self.successful_reconnects += 1
        else:
            self.failed_reconnects += 1

    def get_backoff_pattern(self) -> list[float]:
        """Get the backoff times used"""
        return [a["wait_time"] for a in self.attempts]

    def verify_exponential_backoff(self, base: float = 1.0, max_wait: float = 30.0) -> bool:
        """Verify exponential backoff was used correctly"""
        pattern = self.get_backoff_pattern()

        for i, wait_time in enumerate(pattern):
            expected = min(base * (2**i), max_wait)
            # Allow 10% tolerance
            if abs(wait_time - expected) > expected * 0.1:
                return False
        return True


async def wait_for_condition(
    condition_func: Callable[[], bool], timeout: float = 5.0, check_interval: float = 0.1
) -> bool:
    """Wait for a condition to become true"""
    start_time = time.time()

    while time.time() - start_time < timeout:
        if (
            await asyncio.coroutine(condition_func)()
            if asyncio.iscoroutinefunction(condition_func)
            else condition_func()
        ):
            return True
        await asyncio.sleep(check_interval)

    return False


def create_test_messages(count: int, message_type: str = "test") -> list[dict]:
    """Create test messages for load testing"""
    messages = []
    for i in range(count):
        messages.append(
            {
                "type": message_type,
                "id": f"msg_{i}",
                "content": f"Test message {i}",
                "timestamp": time.time() + i * 0.001,  # Slight offset
            }
        )
    return messages


class PerformanceMonitor:
    """Monitor WebSocket performance metrics"""

    def __init__(self):
        self.start_time = time.time()
        self.messages_sent = 0
        self.messages_received = 0
        self.bytes_sent = 0
        self.bytes_received = 0
        self.errors = 0

    def record_sent(self, message: str):
        """Record sent message"""
        self.messages_sent += 1
        self.bytes_sent += len(message.encode())

    def record_received(self, message: str):
        """Record received message"""
        self.messages_received += 1
        self.bytes_received += len(message.encode())

    def record_error(self):
        """Record error"""
        self.errors += 1

    def get_metrics(self) -> dict:
        """Get performance metrics"""
        elapsed = time.time() - self.start_time

        return {
            "duration_seconds": elapsed,
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "errors": self.errors,
            "send_rate": self.messages_sent / elapsed if elapsed > 0 else 0,
            "receive_rate": self.messages_received / elapsed if elapsed > 0 else 0,
            "error_rate": self.errors / self.messages_sent if self.messages_sent > 0 else 0,
        }


# Export all utilities
__all__ = [
    "ConnectionSimulator",
    "LatencyTracker",
    "MessageValidator",
    "MockMessage",
    "MockWebSocketServer",
    "PerformanceMonitor",
    "ReconnectTracker",
    "create_test_messages",
    "wait_for_condition",
]
