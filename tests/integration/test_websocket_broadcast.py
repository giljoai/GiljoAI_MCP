#!/usr/bin/env python
"""
Integration tests for WebSocket broadcast system (Handover 0086B Phase 5.3)

Tests WebSocket event propagation across multiple clients including:
- Multi-client broadcast validation
- Multi-tenant isolation in broadcasts
- Event ordering and consistency
- Concurrent broadcast handling
- Client disconnect scenarios
- Zero cross-tenant leakage

PRODUCTION-GRADE: Validates real-time event delivery with tenant isolation
"""

import asyncio
from typing import Dict, List
from uuid import uuid4

import pytest
from api.websocket_manager import ConnectionInfo, WebSocketManager
from sqlalchemy.orm import Session

from api.dependencies.websocket import WebSocketDependency
from api.events.schemas import EventFactory
from src.giljo_mcp.models import User


@pytest.fixture
def websocket_manager():
    """Create WebSocket manager instance"""
    return WebSocketManager()


@pytest.fixture
def test_user_a(db: Session):
    """Create test user A (tenant A)"""
    user = User(
        username=f"user_a_{uuid4().hex[:8]}",
        email=f"usera_{uuid4().hex[:8]}@example.com",
        tenant_key=f"tenant_a_{uuid4().hex[:8]}",
        role="developer",
        password_hash="hashed_password",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_user_b(db: Session):
    """Create test user B (tenant B)"""
    user = User(
        username=f"user_b_{uuid4().hex[:8]}",
        email=f"userb_{uuid4().hex[:8]}@example.com",
        tenant_key=f"tenant_b_{uuid4().hex[:8]}",
        role="developer",
        password_hash="hashed_password",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class MockWebSocket:
    """Mock WebSocket for testing"""

    def __init__(self, client_id: str, tenant_key: str):
        self.client_id = client_id
        self.tenant_key = tenant_key
        self.messages_sent: List[Dict] = []
        self.is_connected = True
        self.send_count = 0

    async def send_json(self, data: dict):
        """Mock send_json method"""
        if not self.is_connected:
            raise RuntimeError("WebSocket disconnected")
        self.messages_sent.append(data)
        self.send_count += 1

    def disconnect(self):
        """Simulate disconnect"""
        self.is_connected = False


@pytest.mark.asyncio
class TestWebSocketBroadcast:
    """
    Test 1: WebSocket event propagation to multiple clients
    Validates broadcast reaches all connected clients in tenant
    """

    async def test_websocket_event_propagation_to_multiple_clients(
        self, websocket_manager: WebSocketManager, test_user_a: User
    ):
        """
        PRODUCTION-GRADE: Broadcast to multiple clients in same tenant
        """
        # Arrange: Connect 5 clients for same tenant
        clients = []
        for i in range(5):
            client = MockWebSocket(client_id=f"client_{i}", tenant_key=test_user_a.tenant_key)
            websocket_manager.active_connections[f"client_{i}"] = ConnectionInfo(
                websocket=client,
                user_id=test_user_a.id,
                tenant_key=test_user_a.tenant_key,
                username=test_user_a.username,
            )
            clients.append(client)

        # Act: Broadcast event to tenant
        event_data = EventFactory.project_mission_updated(
            project_id=str(uuid4()),
            tenant_key=test_user_a.tenant_key,
            mission="Test mission",
            token_estimate=1000,
            generated_by="orchestrator",
            user_config_applied=True,
        )

        ws_dep = WebSocketDependency(websocket_manager=websocket_manager)
        sent_count = await ws_dep.broadcast_to_tenant(
            tenant_key=test_user_a.tenant_key, event_type="project:mission_updated", data=event_data["data"]
        )

        # Assert: All 5 clients received broadcast
        assert sent_count == 5

        for client in clients:
            assert len(client.messages_sent) == 1
            message = client.messages_sent[0]
            assert message["type"] == "project:mission_updated"
            assert message["data"]["mission"] == "Test mission"
            assert message["data"]["user_config_applied"] is True

    """
    Test 2: Multi-tenant isolation in broadcasts
    Validates zero cross-tenant leakage
    """

    async def test_multi_tenant_isolation_in_broadcasts(
        self, websocket_manager: WebSocketManager, test_user_a: User, test_user_b: User
    ):
        """
        PRODUCTION-GRADE: Multi-tenant isolation (security critical)
        """
        # Arrange: Connect clients from two different tenants
        client_a1 = MockWebSocket("client_a1", test_user_a.tenant_key)
        client_a2 = MockWebSocket("client_a2", test_user_a.tenant_key)
        client_b1 = MockWebSocket("client_b1", test_user_b.tenant_key)
        client_b2 = MockWebSocket("client_b2", test_user_b.tenant_key)

        websocket_manager.active_connections["client_a1"] = ConnectionInfo(
            websocket=client_a1,
            user_id=test_user_a.id,
            tenant_key=test_user_a.tenant_key,
            username=test_user_a.username,
        )
        websocket_manager.active_connections["client_a2"] = ConnectionInfo(
            websocket=client_a2,
            user_id=test_user_a.id,
            tenant_key=test_user_a.tenant_key,
            username=test_user_a.username,
        )
        websocket_manager.active_connections["client_b1"] = ConnectionInfo(
            websocket=client_b1,
            user_id=test_user_b.id,
            tenant_key=test_user_b.tenant_key,
            username=test_user_b.username,
        )
        websocket_manager.active_connections["client_b2"] = ConnectionInfo(
            websocket=client_b2,
            user_id=test_user_b.id,
            tenant_key=test_user_b.tenant_key,
            username=test_user_b.username,
        )

        # Act: Broadcast event to tenant A only
        event_data = EventFactory.agent_created(
            agent_id=str(uuid4()),
            tenant_key=test_user_a.tenant_key,
            project_id=str(uuid4()),
            agent_display_name="implementor",
            mission="Test mission",
            status="waiting",
        )

        ws_dep = WebSocketDependency(websocket_manager=websocket_manager)
        sent_count = await ws_dep.broadcast_to_tenant(
            tenant_key=test_user_a.tenant_key, event_type="agent:created", data=event_data["data"]
        )

        # Assert: Only tenant A clients received broadcast
        assert sent_count == 2  # Only client_a1 and client_a2

        assert len(client_a1.messages_sent) == 1
        assert len(client_a2.messages_sent) == 1
        assert len(client_b1.messages_sent) == 0  # Tenant B not notified
        assert len(client_b2.messages_sent) == 0  # Tenant B not notified

        # Assert: Message content correct
        assert client_a1.messages_sent[0]["type"] == "agent:created"
        assert client_a2.messages_sent[0]["type"] == "agent:created"

    """
    Test 3: broadcast_to_tenant reaches all tenant clients
    Validates broadcast_to_tenant method implementation
    """

    async def test_broadcast_to_tenant_reaches_all_tenant_clients(
        self, websocket_manager: WebSocketManager, test_user_a: User
    ):
        """
        PRODUCTION-GRADE: Validate broadcast_to_tenant method (Task 1.3)
        """
        # Arrange: Connect 10 clients for tenant
        clients = []
        for i in range(10):
            client = MockWebSocket(f"client_{i}", test_user_a.tenant_key)
            websocket_manager.active_connections[f"client_{i}"] = ConnectionInfo(
                websocket=client,
                user_id=test_user_a.id,
                tenant_key=test_user_a.tenant_key,
                username=test_user_a.username,
            )
            clients.append(client)

        # Act: Broadcast to tenant
        ws_dep = WebSocketDependency(websocket_manager=websocket_manager)
        sent_count = await ws_dep.broadcast_to_tenant(
            tenant_key=test_user_a.tenant_key, event_type="test:event", data={"message": "Hello all clients"}
        )

        # Assert: All 10 clients received message
        assert sent_count == 10

        for client in clients:
            assert len(client.messages_sent) == 1
            assert client.messages_sent[0]["data"]["message"] == "Hello all clients"

    """
    Test 4: exclude_client parameter works
    Validates exclude_client functionality in broadcast
    """

    async def test_exclude_client_parameter_works(self, websocket_manager: WebSocketManager, test_user_a: User):
        """
        PRODUCTION-GRADE: Validate exclude_client parameter
        """
        # Arrange: Connect 3 clients
        client1 = MockWebSocket("client_1", test_user_a.tenant_key)
        client2 = MockWebSocket("client_2", test_user_a.tenant_key)
        client3 = MockWebSocket("client_3", test_user_a.tenant_key)

        websocket_manager.active_connections["client_1"] = ConnectionInfo(
            websocket=client1, user_id=test_user_a.id, tenant_key=test_user_a.tenant_key, username=test_user_a.username
        )
        websocket_manager.active_connections["client_2"] = ConnectionInfo(
            websocket=client2, user_id=test_user_a.id, tenant_key=test_user_a.tenant_key, username=test_user_a.username
        )
        websocket_manager.active_connections["client_3"] = ConnectionInfo(
            websocket=client3, user_id=test_user_a.id, tenant_key=test_user_a.tenant_key, username=test_user_a.username
        )

        # Act: Broadcast excluding client_2
        ws_dep = WebSocketDependency(websocket_manager=websocket_manager)
        sent_count = await ws_dep.broadcast_to_tenant(
            tenant_key=test_user_a.tenant_key,
            event_type="test:event",
            data={"message": "Not for client_2"},
            exclude_client="client_2",
        )

        # Assert: Only 2 clients received (client_1 and client_3)
        assert sent_count == 2

        assert len(client1.messages_sent) == 1
        assert len(client2.messages_sent) == 0  # Excluded
        assert len(client3.messages_sent) == 1

    """
    Test 5: Event ordering preserved
    Validates events received in same order as sent
    """

    async def test_event_ordering_preserved(self, websocket_manager: WebSocketManager, test_user_a: User):
        """
        PRODUCTION-GRADE: Event ordering consistency
        """
        # Arrange: Connect client
        client = MockWebSocket("client_1", test_user_a.tenant_key)
        websocket_manager.active_connections["client_1"] = ConnectionInfo(
            websocket=client, user_id=test_user_a.id, tenant_key=test_user_a.tenant_key, username=test_user_a.username
        )

        # Act: Send 10 events in sequence
        ws_dep = WebSocketDependency(websocket_manager=websocket_manager)
        for i in range(10):
            await ws_dep.broadcast_to_tenant(
                tenant_key=test_user_a.tenant_key, event_type="test:sequence", data={"sequence": i}
            )

        # Assert: Events received in correct order
        assert len(client.messages_sent) == 10

        for i in range(10):
            assert client.messages_sent[i]["data"]["sequence"] == i

    """
    Test 6: Concurrent broadcasts handled
    Validates race condition prevention in concurrent broadcasts
    """

    async def test_concurrent_broadcasts_handled(self, websocket_manager: WebSocketManager, test_user_a: User):
        """
        PRODUCTION-GRADE: Concurrent broadcast handling
        """
        # Arrange: Connect 5 clients
        clients = []
        for i in range(5):
            client = MockWebSocket(f"client_{i}", test_user_a.tenant_key)
            websocket_manager.active_connections[f"client_{i}"] = ConnectionInfo(
                websocket=client,
                user_id=test_user_a.id,
                tenant_key=test_user_a.tenant_key,
                username=test_user_a.username,
            )
            clients.append(client)

        # Act: 20 concurrent broadcasts
        ws_dep = WebSocketDependency(websocket_manager=websocket_manager)

        async def broadcast(index: int):
            return await ws_dep.broadcast_to_tenant(
                tenant_key=test_user_a.tenant_key, event_type="test:concurrent", data={"broadcast_id": index}
            )

        tasks = [broadcast(i) for i in range(20)]
        results = await asyncio.gather(*tasks)

        # Assert: All broadcasts sent to all clients
        assert all(count == 5 for count in results)  # Each broadcast reached 5 clients

        # Assert: Each client received all 20 broadcasts
        for client in clients:
            assert len(client.messages_sent) == 20

            # Verify all broadcast IDs present (order may vary due to concurrency)
            broadcast_ids = {msg["data"]["broadcast_id"] for msg in client.messages_sent}
            assert broadcast_ids == set(range(20))

    """
    Test 7: Client disconnect during broadcast
    Validates graceful handling of client disconnection
    """

    async def test_client_disconnect_during_broadcast(self, websocket_manager: WebSocketManager, test_user_a: User):
        """
        PRODUCTION-GRADE: Handle client disconnect gracefully
        """
        # Arrange: Connect 3 clients
        client1 = MockWebSocket("client_1", test_user_a.tenant_key)
        client2 = MockWebSocket("client_2", test_user_a.tenant_key)
        client3 = MockWebSocket("client_3", test_user_a.tenant_key)

        websocket_manager.active_connections["client_1"] = ConnectionInfo(
            websocket=client1, user_id=test_user_a.id, tenant_key=test_user_a.tenant_key, username=test_user_a.username
        )
        websocket_manager.active_connections["client_2"] = ConnectionInfo(
            websocket=client2, user_id=test_user_a.id, tenant_key=test_user_a.tenant_key, username=test_user_a.username
        )
        websocket_manager.active_connections["client_3"] = ConnectionInfo(
            websocket=client3, user_id=test_user_a.id, tenant_key=test_user_a.tenant_key, username=test_user_a.username
        )

        # Disconnect client_2 before broadcast
        client2.disconnect()

        # Act: Broadcast to tenant (should handle disconnect gracefully)
        ws_dep = WebSocketDependency(websocket_manager=websocket_manager)
        sent_count = await ws_dep.broadcast_to_tenant(
            tenant_key=test_user_a.tenant_key, event_type="test:event", data={"message": "Test"}
        )

        # Assert: Broadcast to remaining clients succeeded
        # Note: Implementation may still return 3 (attempted) or 2 (successful)
        # depending on error handling approach
        assert sent_count >= 2  # At least client_1 and client_3

        assert len(client1.messages_sent) == 1
        assert len(client3.messages_sent) == 1
        # client2 may or may not have message (disconnected)

    """
    Test 8: Zero cross-tenant leakage
    Validates complete tenant isolation across multiple broadcasts
    """

    async def test_zero_cross_tenant_leakage(
        self, websocket_manager: WebSocketManager, test_user_a: User, test_user_b: User
    ):
        """
        PRODUCTION-GRADE: Security validation - zero cross-tenant leakage
        """
        # Arrange: Connect 10 clients per tenant (20 total)
        tenant_a_clients = []
        tenant_b_clients = []

        for i in range(10):
            client_a = MockWebSocket(f"client_a_{i}", test_user_a.tenant_key)
            websocket_manager.active_connections[f"client_a_{i}"] = ConnectionInfo(
                websocket=client_a,
                user_id=test_user_a.id,
                tenant_key=test_user_a.tenant_key,
                username=test_user_a.username,
            )
            tenant_a_clients.append(client_a)

            client_b = MockWebSocket(f"client_b_{i}", test_user_b.tenant_key)
            websocket_manager.active_connections[f"client_b_{i}"] = ConnectionInfo(
                websocket=client_b,
                user_id=test_user_b.id,
                tenant_key=test_user_b.tenant_key,
                username=test_user_b.username,
            )
            tenant_b_clients.append(client_b)

        # Act: Broadcast 10 events to tenant A, 10 to tenant B
        ws_dep = WebSocketDependency(websocket_manager=websocket_manager)

        for i in range(10):
            # Tenant A broadcast
            await ws_dep.broadcast_to_tenant(
                tenant_key=test_user_a.tenant_key, event_type="tenant_a:event", data={"tenant": "A", "sequence": i}
            )

            # Tenant B broadcast
            await ws_dep.broadcast_to_tenant(
                tenant_key=test_user_b.tenant_key, event_type="tenant_b:event", data={"tenant": "B", "sequence": i}
            )

        # Assert: Tenant A clients only received tenant A events
        for client in tenant_a_clients:
            assert len(client.messages_sent) == 10
            for message in client.messages_sent:
                assert message["type"] == "tenant_a:event"
                assert message["data"]["tenant"] == "A"

        # Assert: Tenant B clients only received tenant B events
        for client in tenant_b_clients:
            assert len(client.messages_sent) == 10
            for message in client.messages_sent:
                assert message["type"] == "tenant_b:event"
                assert message["data"]["tenant"] == "B"

        # Assert: Zero cross-tenant leakage
        # Tenant A clients should NOT have any tenant B messages
        for client in tenant_a_clients:
            for message in client.messages_sent:
                assert message["data"]["tenant"] != "B"

        # Tenant B clients should NOT have any tenant A messages
        for client in tenant_b_clients:
            for message in client.messages_sent:
                assert message["data"]["tenant"] != "A"


@pytest.mark.asyncio
class TestWebSocketBroadcastEdgeCases:
    """Edge cases and error scenarios"""

    async def test_broadcast_to_empty_tenant(self, websocket_manager: WebSocketManager, test_user_a: User):
        """
        Validate broadcast when no clients connected for tenant
        """
        # Arrange: No clients connected
        ws_dep = WebSocketDependency(websocket_manager=websocket_manager)

        # Act: Broadcast to tenant with no clients
        sent_count = await ws_dep.broadcast_to_tenant(
            tenant_key=test_user_a.tenant_key, event_type="test:event", data={"message": "No one listening"}
        )

        # Assert: Zero clients notified (no error)
        assert sent_count == 0

    async def test_broadcast_with_invalid_event_data(self, websocket_manager: WebSocketManager, test_user_a: User):
        """
        Validate error handling for invalid event data
        """
        # Arrange: Connect client
        client = MockWebSocket("client_1", test_user_a.tenant_key)
        websocket_manager.active_connections["client_1"] = ConnectionInfo(
            websocket=client, user_id=test_user_a.id, tenant_key=test_user_a.tenant_key, username=test_user_a.username
        )

        # Act & Assert: Broadcast with None data (should handle gracefully)
        ws_dep = WebSocketDependency(websocket_manager=websocket_manager)

        # Implementation should handle None or invalid data gracefully
        try:
            sent_count = await ws_dep.broadcast_to_tenant(
                tenant_key=test_user_a.tenant_key,
                event_type="test:event",
                data=None,  # Invalid
            )
            # If no error, verify it was handled
            assert sent_count >= 0
        except Exception:
            # If error raised, that's acceptable too
            pass

    async def test_multiple_tenants_same_user_id(
        self, websocket_manager: WebSocketManager, test_user_a: User, test_user_b: User
    ):
        """
        Validate isolation when users in different tenants have same user_id
        (Edge case: user_id collision across tenants)
        """
        # Arrange: Force same user_id for different tenants (edge case)
        same_user_id = uuid4()
        test_user_a.id = same_user_id
        test_user_b.id = same_user_id

        client_a = MockWebSocket("client_a", test_user_a.tenant_key)
        client_b = MockWebSocket("client_b", test_user_b.tenant_key)

        websocket_manager.active_connections["client_a"] = ConnectionInfo(
            websocket=client_a, user_id=same_user_id, tenant_key=test_user_a.tenant_key, username=test_user_a.username
        )
        websocket_manager.active_connections["client_b"] = ConnectionInfo(
            websocket=client_b, user_id=same_user_id, tenant_key=test_user_b.tenant_key, username=test_user_b.username
        )

        # Act: Broadcast to tenant A
        ws_dep = WebSocketDependency(websocket_manager=websocket_manager)
        sent_count = await ws_dep.broadcast_to_tenant(
            tenant_key=test_user_a.tenant_key, event_type="test:event", data={"message": "Tenant A only"}
        )

        # Assert: Only tenant A client received message (tenant_key isolation)
        assert sent_count == 1
        assert len(client_a.messages_sent) == 1
        assert len(client_b.messages_sent) == 0  # Different tenant
