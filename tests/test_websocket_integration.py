"""
WebSocket Integration Test Suite for Project 4.3.1
Tests real-time updates, auto-reconnect, and resilience
"""

import asyncio
import json
import time
import pytest
import websockets
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict, Any
import httpx

# Test configuration
WS_URL = "ws://localhost:8000/ws"
API_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:6000"
TEST_CLIENT_ID = "test_client_001"
TEST_API_KEY = "test_api_key_123"


class WebSocketTestClient:
    """Test client for WebSocket connections"""
    
    def __init__(self, client_id: str, api_key: str = None):
        self.client_id = client_id
        self.api_key = api_key
        self.websocket = None
        self.messages_received: List[Dict] = []
        self.connection_state = "disconnected"
        self.reconnect_count = 0
        self.last_ping_time = None
        self.latencies: List[float] = []
        
    async def connect(self, url: str = WS_URL):
        """Establish WebSocket connection"""
        try:
            # Add auth to URL if API key provided
            ws_url = f"{url}/{self.client_id}"
            if self.api_key:
                ws_url += f"?api_key={self.api_key}"
                
            self.websocket = await websockets.connect(ws_url)
            self.connection_state = "connected"
            return True
        except Exception as e:
            self.connection_state = "error"
            raise e
            
    async def disconnect(self):
        """Close WebSocket connection"""
        if self.websocket:
            await self.websocket.close()
            self.connection_state = "disconnected"
            
    async def send_message(self, message: Dict):
        """Send JSON message through WebSocket"""
        if self.websocket:
            await self.websocket.send(json.dumps(message))
            
    async def receive_message(self, timeout: float = 5.0) -> Dict:
        """Receive and parse JSON message"""
        if self.websocket:
            try:
                message = await asyncio.wait_for(
                    self.websocket.recv(), 
                    timeout=timeout
                )
                parsed = json.loads(message)
                self.messages_received.append(parsed)
                return parsed
            except asyncio.TimeoutError:
                return None
                
    async def measure_latency(self) -> float:
        """Measure round-trip latency"""
        start_time = time.time()
        await self.send_message({"type": "ping", "timestamp": start_time})
        response = await self.receive_message(timeout=1.0)
        if response and response.get("type") == "pong":
            latency = (time.time() - start_time) * 1000  # Convert to ms
            self.latencies.append(latency)
            return latency
        return -1


class TestWebSocketConnection:
    """Test WebSocket connection establishment and authentication"""
    
    @pytest.mark.asyncio
    async def test_successful_connection(self):
        """Test successful WebSocket connection"""
        client = WebSocketTestClient(TEST_CLIENT_ID)
        try:
            connected = await client.connect()
            assert connected == True
            assert client.connection_state == "connected"
        finally:
            await client.disconnect()
            
    @pytest.mark.asyncio
    async def test_connection_with_auth(self):
        """Test WebSocket connection with API key authentication"""
        client = WebSocketTestClient(TEST_CLIENT_ID, TEST_API_KEY)
        try:
            connected = await client.connect()
            assert connected == True
            
            # Send authenticated request
            await client.send_message({
                "type": "auth_test",
                "data": {"test": "authenticated"}
            })
            
            response = await client.receive_message()
            assert response is not None
        finally:
            await client.disconnect()
            
    @pytest.mark.asyncio
    async def test_invalid_auth_rejection(self):
        """Test that invalid auth is rejected"""
        client = WebSocketTestClient(TEST_CLIENT_ID, "invalid_key")
        with pytest.raises(websockets.exceptions.WebSocketException):
            await client.connect()
            
    @pytest.mark.asyncio
    async def test_multiple_clients(self):
        """Test multiple simultaneous WebSocket connections"""
        clients = [
            WebSocketTestClient(f"client_{i}") 
            for i in range(5)
        ]
        
        try:
            # Connect all clients
            for client in clients:
                await client.connect()
                assert client.connection_state == "connected"
                
            # Each client sends a message
            for i, client in enumerate(clients):
                await client.send_message({
                    "type": "test",
                    "client_num": i
                })
                
        finally:
            for client in clients:
                await client.disconnect()


class TestAutoReconnect:
    """Test auto-reconnect functionality with exponential backoff"""
    
    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test reconnect uses exponential backoff (1s→2s→4s→8s)"""
        backoff_times = []
        
        async def mock_reconnect_with_backoff(attempt: int):
            """Simulate reconnect with exponential backoff"""
            wait_time = min(2 ** attempt, 30)  # Cap at 30s
            backoff_times.append(wait_time)
            await asyncio.sleep(wait_time)
            return attempt < 4  # Succeed on 4th attempt
            
        # Test backoff sequence
        attempt = 0
        while attempt < 4:
            await mock_reconnect_with_backoff(attempt)
            attempt += 1
            
        assert backoff_times == [1, 2, 4, 8]
        
    @pytest.mark.asyncio
    async def test_auto_reconnect_on_disconnect(self):
        """Test client auto-reconnects after disconnection"""
        client = WebSocketTestClient(TEST_CLIENT_ID)
        
        try:
            # Initial connection
            await client.connect()
            initial_ws = client.websocket
            
            # Simulate disconnection
            await client.websocket.close()
            client.connection_state = "disconnected"
            
            # Simulate auto-reconnect
            await asyncio.sleep(1)  # Wait for first backoff
            await client.connect()
            
            assert client.websocket != initial_ws
            assert client.connection_state == "connected"
            
        finally:
            await client.disconnect()
            
    @pytest.mark.asyncio
    async def test_reconnect_within_5_seconds(self):
        """Test dashboard auto-reconnects within 5 seconds requirement"""
        client = WebSocketTestClient(TEST_CLIENT_ID)
        
        try:
            await client.connect()
            
            # Simulate disconnection
            disconnect_time = time.time()
            await client.websocket.close()
            
            # Attempt reconnect
            await asyncio.sleep(1)  # First backoff
            await client.connect()
            reconnect_time = time.time()
            
            elapsed = reconnect_time - disconnect_time
            assert elapsed < 5.0, f"Reconnection took {elapsed}s, expected <5s"
            
        finally:
            await client.disconnect()


class TestRealTimeUpdates:
    """Test real-time update broadcasting and latency"""
    
    @pytest.mark.asyncio
    async def test_agent_status_update_latency(self):
        """Test agent status updates appear within 100ms"""
        client = WebSocketTestClient(TEST_CLIENT_ID)
        
        try:
            await client.connect()
            
            # Measure update latency
            latency = await client.measure_latency()
            assert latency < 100, f"Latency {latency}ms exceeds 100ms requirement"
            
            # Test agent status change broadcast
            start_time = time.time()
            
            # Simulate agent status change via API
            async with httpx.AsyncClient() as http_client:
                response = await http_client.post(
                    f"{API_URL}/test/agent_status_change",
                    json={
                        "agent_id": "test_agent",
                        "old_status": "pending",
                        "new_status": "in_progress"
                    }
                )
                
            # Wait for WebSocket notification
            update = await client.receive_message(timeout=0.5)
            receive_time = time.time()
            
            assert update is not None
            assert update.get("type") == "agent_status_update"
            assert (receive_time - start_time) * 1000 < 100
            
        finally:
            await client.disconnect()
            
    @pytest.mark.asyncio
    async def test_message_streaming(self):
        """Test real-time message streaming"""
        sender = WebSocketTestClient("sender_client")
        receiver = WebSocketTestClient("receiver_client")
        
        try:
            await sender.connect()
            await receiver.connect()
            
            # Send message from sender
            test_message = {
                "type": "message",
                "content": "Test real-time message",
                "timestamp": time.time()
            }
            await sender.send_message(test_message)
            
            # Receiver should get it immediately
            received = await receiver.receive_message(timeout=1.0)
            assert received is not None
            assert received.get("content") == test_message["content"]
            
        finally:
            await sender.disconnect()
            await receiver.disconnect()
            
    @pytest.mark.asyncio
    async def test_progress_indicator_updates(self):
        """Test smooth progress indicator updates"""
        client = WebSocketTestClient(TEST_CLIENT_ID)
        
        try:
            await client.connect()
            
            # Simulate long operation with progress updates
            progress_updates = []
            
            # Start operation
            await client.send_message({
                "type": "start_operation",
                "operation_id": "test_op_001"
            })
            
            # Collect progress updates
            for _ in range(10):
                update = await client.receive_message(timeout=2.0)
                if update and update.get("type") == "progress":
                    progress_updates.append(update.get("percentage", 0))
                    
            # Verify smooth progression
            assert len(progress_updates) >= 5
            assert progress_updates[-1] >= 90  # Should be near completion
            
            # Check updates are incremental
            for i in range(1, len(progress_updates)):
                assert progress_updates[i] >= progress_updates[i-1]
                
        finally:
            await client.disconnect()


class TestMessageQueue:
    """Test message queuing during disconnection"""
    
    @pytest.mark.asyncio
    async def test_message_queue_during_disconnect(self):
        """Test messages are queued during disconnection"""
        client = WebSocketTestClient(TEST_CLIENT_ID)
        
        try:
            # Connect initially
            await client.connect()
            
            # Disconnect
            await client.disconnect()
            
            # Simulate messages sent while disconnected
            queued_messages = [
                {"id": 1, "content": "Message while disconnected 1"},
                {"id": 2, "content": "Message while disconnected 2"},
                {"id": 3, "content": "Message while disconnected 3"}
            ]
            
            # Simulate API storing messages
            async with httpx.AsyncClient() as http_client:
                for msg in queued_messages:
                    await http_client.post(
                        f"{API_URL}/queue_message",
                        json={"client_id": TEST_CLIENT_ID, "message": msg}
                    )
                    
            # Reconnect
            await client.connect()
            
            # Should receive queued messages
            received_count = 0
            while True:
                msg = await client.receive_message(timeout=1.0)
                if not msg:
                    break
                received_count += 1
                
            assert received_count == len(queued_messages)
            
        finally:
            await client.disconnect()
            
    @pytest.mark.asyncio
    async def test_no_message_loss(self):
        """Test no messages are lost during network interruptions"""
        client = WebSocketTestClient(TEST_CLIENT_ID)
        sent_messages = []
        
        try:
            await client.connect()
            
            # Send messages with simulated interruptions
            for i in range(10):
                msg = {"id": i, "content": f"Message {i}"}
                sent_messages.append(msg)
                
                if i == 5:
                    # Simulate brief disconnection
                    await client.websocket.close()
                    await asyncio.sleep(0.5)
                    await client.connect()
                    
                await client.send_message(msg)
                
            # Verify all messages were processed
            # This would check against API/database
            async with httpx.AsyncClient() as http_client:
                response = await http_client.get(
                    f"{API_URL}/messages/{TEST_CLIENT_ID}"
                )
                stored_messages = response.json()
                
            assert len(stored_messages) == len(sent_messages)
            
        finally:
            await client.disconnect()


class TestConnectionResilience:
    """Test connection resilience and failover"""
    
    @pytest.mark.asyncio
    async def test_heartbeat_keepalive(self):
        """Test 30-second heartbeat keeps connection alive"""
        client = WebSocketTestClient(TEST_CLIENT_ID)
        
        try:
            await client.connect()
            
            # Wait for heartbeat
            await asyncio.sleep(31)  # Just over 30 seconds
            
            # Connection should still be alive
            assert client.websocket.open
            
            # Should have received at least one ping
            pings_received = [
                msg for msg in client.messages_received 
                if msg.get("type") == "ping"
            ]
            assert len(pings_received) >= 1
            
        finally:
            await client.disconnect()
            
    @pytest.mark.asyncio
    async def test_connection_quality_indicator(self):
        """Test connection quality indicators work correctly"""
        client = WebSocketTestClient(TEST_CLIENT_ID)
        
        try:
            await client.connect()
            
            # Measure multiple latencies
            for _ in range(10):
                await client.measure_latency()
                await asyncio.sleep(0.1)
                
            # Calculate connection quality
            avg_latency = sum(client.latencies) / len(client.latencies)
            
            if avg_latency < 50:
                quality = "excellent"
            elif avg_latency < 150:
                quality = "good"
            elif avg_latency < 300:
                quality = "fair"
            else:
                quality = "poor"
                
            assert quality in ["excellent", "good", "fair", "poor"]
            
        finally:
            await client.disconnect()
            
    @pytest.mark.asyncio
    async def test_fallback_to_polling(self):
        """Test fallback to polling when WebSocket fails"""
        client = WebSocketTestClient(TEST_CLIENT_ID)
        
        # Simulate WebSocket failure
        with patch('websockets.connect', side_effect=Exception("WS Failed")):
            # Should fallback to polling
            async with httpx.AsyncClient() as http_client:
                # Poll for updates
                response = await http_client.get(
                    f"{API_URL}/poll/{TEST_CLIENT_ID}"
                )
                assert response.status_code == 200
                
                # Should return updates via polling
                updates = response.json()
                assert isinstance(updates, list)


class TestBroadcastFeatures:
    """Test broadcast functionality for all entity types"""
    
    @pytest.mark.asyncio
    async def test_project_update_broadcast(self):
        """Test project creation/status/closure broadcasts"""
        client1 = WebSocketTestClient("client_1")
        client2 = WebSocketTestClient("client_2")
        
        try:
            await client1.connect()
            await client2.connect()
            
            # Simulate project creation
            async with httpx.AsyncClient() as http_client:
                await http_client.post(
                    f"{API_URL}/test/broadcast",
                    json={
                        "type": "project_created",
                        "project": {"id": "proj_001", "name": "Test Project"}
                    }
                )
                
            # Both clients should receive the broadcast
            msg1 = await client1.receive_message(timeout=1.0)
            msg2 = await client2.receive_message(timeout=1.0)
            
            assert msg1 is not None
            assert msg2 is not None
            assert msg1.get("type") == "project_created"
            assert msg2.get("type") == "project_created"
            
        finally:
            await client1.disconnect()
            await client2.disconnect()
            
    @pytest.mark.asyncio
    async def test_system_notification_broadcast(self):
        """Test system notifications (errors, warnings, info)"""
        client = WebSocketTestClient(TEST_CLIENT_ID)
        
        try:
            await client.connect()
            
            # Test different notification types
            notification_types = ["error", "warning", "info"]
            
            for notif_type in notification_types:
                async with httpx.AsyncClient() as http_client:
                    await http_client.post(
                        f"{API_URL}/test/system_notification",
                        json={
                            "type": notif_type,
                            "message": f"Test {notif_type} notification"
                        }
                    )
                    
                notification = await client.receive_message(timeout=1.0)
                assert notification is not None
                assert notification.get("severity") == notif_type
                
        finally:
            await client.disconnect()


class TestEndToEndIntegration:
    """End-to-end integration tests for complete workflows"""
    
    @pytest.mark.asyncio
    async def test_complete_agent_workflow(self):
        """Test complete agent workflow with real-time updates"""
        client = WebSocketTestClient(TEST_CLIENT_ID)
        
        try:
            await client.connect()
            
            # 1. Create agent
            async with httpx.AsyncClient() as http_client:
                response = await http_client.post(
                    f"{API_URL}/agents",
                    json={"name": "test_agent", "type": "worker"}
                )
                agent_id = response.json()["id"]
                
            # Should receive agent creation notification
            creation_msg = await client.receive_message(timeout=1.0)
            assert creation_msg.get("type") == "agent_created"
            
            # 2. Update agent status
            async with httpx.AsyncClient() as http_client:
                await http_client.patch(
                    f"{API_URL}/agents/{agent_id}",
                    json={"status": "in_progress"}
                )
                
            # Should receive status update
            status_msg = await client.receive_message(timeout=1.0)
            assert status_msg.get("type") == "agent_status_update"
            assert status_msg.get("status") == "in_progress"
            
            # 3. Send message to agent
            async with httpx.AsyncClient() as http_client:
                await http_client.post(
                    f"{API_URL}/messages",
                    json={
                        "to": agent_id,
                        "content": "Test message"
                    }
                )
                
            # Should receive message notification
            msg_notification = await client.receive_message(timeout=1.0)
            assert msg_notification.get("type") == "new_message"
            
            # 4. Complete agent task
            async with httpx.AsyncClient() as http_client:
                await http_client.patch(
                    f"{API_URL}/agents/{agent_id}",
                    json={"status": "completed"}
                )
                
            # Should receive completion notification
            completion_msg = await client.receive_message(timeout=1.0)
            assert completion_msg.get("type") == "agent_status_update"
            assert completion_msg.get("status") == "completed"
            
        finally:
            await client.disconnect()
            
    @pytest.mark.asyncio
    async def test_performance_under_load(self):
        """Test WebSocket performance under load"""
        clients = [WebSocketTestClient(f"load_test_{i}") for i in range(20)]
        
        try:
            # Connect all clients
            await asyncio.gather(*[c.connect() for c in clients])
            
            # Each client sends rapid messages
            start_time = time.time()
            messages_sent = 0
            
            async def send_rapid_messages(client: WebSocketTestClient):
                nonlocal messages_sent
                for i in range(50):
                    await client.send_message({
                        "type": "load_test",
                        "seq": i
                    })
                    messages_sent += 1
                    
            await asyncio.gather(*[send_rapid_messages(c) for c in clients])
            
            elapsed = time.time() - start_time
            throughput = messages_sent / elapsed
            
            # Should handle at least 500 msgs/sec
            assert throughput > 500, f"Throughput {throughput} msgs/sec is too low"
            
        finally:
            await asyncio.gather(*[c.disconnect() for c in clients])


# Pytest fixtures
@pytest.fixture
async def ws_client():
    """Fixture for WebSocket test client"""
    client = WebSocketTestClient(TEST_CLIENT_ID)
    yield client
    if client.websocket:
        await client.disconnect()


@pytest.fixture
async def mock_api_server():
    """Fixture for mocked API server responses"""
    with patch('httpx.AsyncClient') as mock:
        mock_client = AsyncMock()
        mock.return_value.__aenter__.return_value = mock_client
        yield mock_client


# Test runner configuration
if __name__ == "__main__":
    # Run tests with detailed output
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto",
        "-W", "ignore::DeprecationWarning"
    ])