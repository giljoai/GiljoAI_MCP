"""
WebSocket Load Testing Scenarios for GiljoAI MCP

Tests WebSocket connection scaling and message throughput.

Usage:
    # Run WebSocket stress test
    locust -f tests/load/scenarios/websocket_load.py --host=http://localhost:7272 \
           --headless -u 50 -r 10 -t 5m
"""

import json
import logging
import time

import websocket
from locust import User, between, events, task
from locust.exception import LocustError


logger = logging.getLogger(__name__)


class WebSocketClient:
    """
    WebSocket client for load testing.

    Manages WebSocket connection lifecycle and tracks metrics.
    """

    def __init__(self, host, tenant_key):
        self.host = host
        self.tenant_key = tenant_key
        self.ws = None
        self.connected = False

    def connect(self):
        """Establish WebSocket connection."""
        # Convert HTTP URL to WebSocket URL
        ws_url = self.host.replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{ws_url}/ws"

        start_time = time.time()
        try:
            self.ws = websocket.create_connection(ws_url, timeout=10)
            self.connected = True

            # Authenticate
            auth_message = {"type": "auth", "tenant_key": self.tenant_key}
            self.ws.send(json.dumps(auth_message))

            # Wait for auth response
            response = self.ws.recv()

            total_time = int((time.time() - start_time) * 1000)
            events.request.fire(
                request_type="WSS",
                name="connect",
                response_time=total_time,
                response_length=len(response),
                exception=None,
                context={},
            )

            logger.info(f"WebSocket connected in {total_time}ms")

        except Exception as e:
            total_time = int((time.time() - start_time) * 1000)
            events.request.fire(
                request_type="WSS", name="connect", response_time=total_time, response_length=0, exception=e, context={}
            )
            logger.error(f"WebSocket connection failed: {e}")
            raise

    def send_message(self, message: dict):
        """Send message via WebSocket and wait for response."""
        if not self.connected:
            raise LocustError("WebSocket not connected")

        start_time = time.time()
        try:
            self.ws.send(json.dumps(message))

            # Wait for response with timeout
            self.ws.settimeout(5.0)
            response = self.ws.recv()

            total_time = int((time.time() - start_time) * 1000)
            events.request.fire(
                request_type="WSS",
                name="send_message",
                response_time=total_time,
                response_length=len(response),
                exception=None,
                context={},
            )

            return json.loads(response)

        except websocket.WebSocketTimeoutException:
            total_time = int((time.time() - start_time) * 1000)
            events.request.fire(
                request_type="WSS",
                name="send_message",
                response_time=total_time,
                response_length=0,
                exception=LocustError("WebSocket timeout"),
                context={},
            )
            logger.error("WebSocket message timeout")
            return None

        except Exception as e:
            total_time = int((time.time() - start_time) * 1000)
            events.request.fire(
                request_type="WSS",
                name="send_message",
                response_time=total_time,
                response_length=0,
                exception=e,
                context={},
            )
            logger.error(f"WebSocket send failed: {e}")
            raise

    def subscribe(self, channel: str):
        """Subscribe to a channel."""
        message = {"type": "subscribe", "channel": channel}
        return self.send_message(message)

    def unsubscribe(self, channel: str):
        """Unsubscribe from a channel."""
        message = {"type": "unsubscribe", "channel": channel}
        return self.send_message(message)

    def ping(self):
        """Send ping to keep connection alive."""
        message = {"type": "ping"}
        return self.send_message(message)

    def disconnect(self):
        """Close WebSocket connection."""
        if self.ws:
            try:
                self.ws.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")
            finally:
                self.connected = False


class WebSocketUser(User):
    """
    WebSocket load testing user.

    Simulates user maintaining WebSocket connection and receiving updates.
    """

    abstract = True
    wait_time = between(1, 3)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ws_client = None
        # In a real scenario, get tenant_key from authentication
        self.tenant_key = "test_tenant_key"

    def on_start(self):
        """Establish WebSocket connection on user start."""
        try:
            self.ws_client = WebSocketClient(self.host, self.tenant_key)
            self.ws_client.connect()
            logger.info("User started with WebSocket connection")
        except Exception as e:
            logger.error(f"Failed to start user: {e}")
            raise

    def on_stop(self):
        """Close WebSocket connection on user stop."""
        if self.ws_client:
            try:
                self.ws_client.disconnect()
                logger.info("User stopped, WebSocket closed")
            except Exception as e:
                logger.error(f"Error stopping user: {e}")

    @task(5)
    def receive_updates(self):
        """Simulate receiving real-time updates."""
        if self.ws_client and self.ws_client.connected:
            try:
                # Subscribe to project updates channel
                self.ws_client.subscribe("project_updates")
            except Exception as e:
                logger.error(f"Failed to subscribe: {e}")

    @task(3)
    def ping_pong(self):
        """Ping/pong to keep connection alive."""
        if self.ws_client and self.ws_client.connected:
            try:
                self.ws_client.ping()
            except Exception as e:
                logger.error(f"Ping failed: {e}")

    @task(2)
    def subscribe_agent_updates(self):
        """Subscribe to agent job updates."""
        if self.ws_client and self.ws_client.connected:
            try:
                self.ws_client.subscribe("agent_updates")
            except Exception as e:
                logger.error(f"Failed to subscribe to agent updates: {e}")

    @task(1)
    def unsubscribe_channel(self):
        """Unsubscribe from a channel."""
        if self.ws_client and self.ws_client.connected:
            try:
                # Unsubscribe from a random channel
                channel = ["project_updates", "agent_updates"][time.time_ns() % 2]
                self.ws_client.unsubscribe(channel)
            except Exception as e:
                logger.error(f"Failed to unsubscribe: {e}")


class NormalWebSocketUser(WebSocketUser):
    """
    Normal WebSocket user - typical usage patterns.

    Maintains connection, periodic pings, occasional subscriptions.
    """

    wait_time = between(2, 5)


class StressWebSocketUser(WebSocketUser):
    """
    Aggressive WebSocket user for stress testing.

    Rapid message sending to test throughput and connection stability.
    """

    wait_time = between(0.5, 1)

    @task(10)
    def rapid_messages(self):
        """Send rapid messages to stress test."""
        if self.ws_client and self.ws_client.connected:
            try:
                # Send burst of messages
                for _ in range(10):
                    self.ws_client.ping()
                    time.sleep(0.1)
            except Exception as e:
                logger.error(f"Rapid messages failed: {e}")

    @task(5)
    def rapid_subscribe_unsubscribe(self):
        """Rapidly subscribe and unsubscribe to stress channel management."""
        if self.ws_client and self.ws_client.connected:
            try:
                channels = ["project_updates", "agent_updates", "system_alerts"]
                for channel in channels:
                    self.ws_client.subscribe(channel)
                    time.sleep(0.2)
                    self.ws_client.unsubscribe(channel)
                    time.sleep(0.2)
            except Exception as e:
                logger.error(f"Rapid subscribe/unsubscribe failed: {e}")


class LongLivedWebSocketUser(WebSocketUser):
    """
    Long-lived WebSocket connection for soak testing.

    Maintains connection with minimal activity to test connection stability
    and detect memory leaks.
    """

    wait_time = between(10, 30)  # Long wait times

    @task(10)
    def keep_alive_ping(self):
        """Send occasional pings to keep connection alive."""
        if self.ws_client and self.ws_client.connected:
            try:
                self.ws_client.ping()
            except Exception as e:
                logger.error(f"Keep-alive ping failed: {e}")

    @task(1)
    def subscribe_once(self):
        """Subscribe to channels once and maintain subscription."""
        if self.ws_client and self.ws_client.connected:
            try:
                self.ws_client.subscribe("project_updates")
                self.ws_client.subscribe("agent_updates")
            except Exception as e:
                logger.error(f"Subscription failed: {e}")


# Default user for general WebSocket testing
class DefaultWebSocketUser(NormalWebSocketUser):
    """Default WebSocket user for load testing."""
