"""
Integration tests for Agent Job WebSocket Event Broadcasting (Handover 0019).

Tests real-time WebSocket event delivery for agent job lifecycle:
- Job creation events
- Job status updates (acknowledged, completed, failed)
- Job messages
- Children spawned events
- Multi-tenant isolation

These tests verify that WebSocket broadcasts work correctly when integrated
with the agent_management API endpoints.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

import pytest
from httpx import AsyncClient


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.app import create_app, state
from src.giljo_mcp.models import Product, User
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from tests.helpers.test_db_helper import PostgreSQLTestHelper
from tests.helpers.websocket_test_utils import PerformanceMonitor


class WebSocketEventCollector:
    """Collects WebSocket events for testing."""

    def __init__(self):
        self.events: List[dict] = []
        self.event_types: List[str] = []
        self.lock = asyncio.Lock()

    async def add_event(self, event: dict):
        """Add an event to the collection."""
        async with self.lock:
            self.events.append(event)
            self.event_types.append(event.get("type", "unknown"))

    def add_event_sync(self, event: dict):
        """Add an event synchronously (for mocking)."""
        self.events.append(event)
        self.event_types.append(event.get("type", "unknown"))

    async def wait_for_event(self, event_type: str, timeout: float = 5.0) -> Optional[dict]:
        """Wait for a specific event type."""
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            async with self.lock:
                for event in self.events:
                    if event.get("type") == event_type:
                        return event
            await asyncio.sleep(0.1)

        return None

    async def get_events_by_type(self, event_type: str) -> List[dict]:
        """Get all events of a specific type."""
        async with self.lock:
            return [e for e in self.events if e.get("type") == event_type]

    async def clear(self):
        """Clear all collected events."""
        async with self.lock:
            self.events.clear()
            self.event_types.clear()


@pytest.fixture
async def test_app():
    """Create test application."""
    app = create_app()
    return app


@pytest.fixture
async def async_client(test_app):
    """Create async HTTP client."""
    from httpx import ASGITransport

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        yield client


@pytest.fixture
async def test_db():
    """Setup test database."""
    from src.giljo_mcp.database import DatabaseManager

    db_url = PostgreSQLTestHelper.get_test_db_url(async_driver=True)
    db_manager = DatabaseManager(db_url, is_async=True)
    await db_manager.create_tables_async()

    yield db_manager

    await db_manager.close_async()


@pytest.fixture
async def test_tenant_key():
    """Generate test tenant key."""
    return f"test-tenant-{uuid4()}"


@pytest.fixture
async def test_product(test_db, test_tenant_key):
    """Create test product."""
    async with test_db.get_session_async() as session:
        product = Product(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            name="Test Product",
            description="Test product for WebSocket event testing",
        )
        session.add(product)
        await session.commit()
        await session.refresh(product)
        return product


@pytest.fixture
async def test_user(test_db, test_tenant_key):
    """Create test user."""
    async with test_db.get_session_async() as session:
        user = User(
            id=str(uuid4()), tenant_key=test_tenant_key, username="test_user", email="test@example.com", is_active=True
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture
async def auth_headers(test_user, test_tenant_key):
    """Create authentication headers."""
    # Mock JWT token for testing
    return {"Authorization": f"Bearer test-token-{test_user.id}", "X-Tenant-Key": test_tenant_key}


class TestAgentJobWebSocketEvents:
    """Test agent job WebSocket event broadcasting."""

    @pytest.mark.asyncio
    async def test_job_created_event(self, async_client, auth_headers, test_tenant_key):
        """Test that job creation broadcasts agent_job:created event."""
        collector = WebSocketEventCollector()

        # Mock WebSocket connection
        from unittest.mock import AsyncMock

        async def mock_send(msg):
            collector.add_event_sync(msg)

        mock_websocket = AsyncMock()
        mock_websocket.send_json = AsyncMock(side_effect=mock_send)

        # Inject mock WebSocket manager
        if state.websocket_manager:
            original_manager = state.websocket_manager
            state.websocket_manager.active_connections["test_client"] = mock_websocket
            state.websocket_manager.auth_contexts["test_client"] = {"tenant_key": test_tenant_key}

        try:
            # Create agent job via API
            response = await async_client.post(
                "/api/agent/agent-jobs",
                headers=auth_headers,
                json={
                    "agent_display_name": "orchestrator",
                    "mission": "Coordinate implementation of feature X with comprehensive testing",
                    "spawned_by": None,
                    "context_chunks": [],
                },
            )

            assert response.status_code == 201
            job_data = response.json()
            job_id = job_data["job_id"]

            # Wait for WebSocket event
            event = await collector.wait_for_event("agent_job:created", timeout=2.0)

            assert event is not None, "Did not receive agent_job:created event"
            assert event["type"] == "agent_job:created"
            assert event["data"]["job_id"] == job_id
            assert event["data"]["agent_display_name"] == "orchestrator"
            assert (
                event["data"]["mission_preview"]
                == "Coordinate implementation of feature X with comprehensive testing"[:100]
            )
            assert "timestamp" in event
            assert "created_at" in event["data"]

        finally:
            # Cleanup
            if state.websocket_manager:
                state.websocket_manager.disconnect("test_client")

    @pytest.mark.asyncio
    async def test_job_acknowledged_event(self, async_client, auth_headers, test_tenant_key, test_db):
        """Test that job acknowledgment broadcasts agent_job:acknowledged event."""
        collector = WebSocketEventCollector()

        # Create a pending job first
        async with test_db.get_session_async() as session:
            job = AgentExecution(
                tenant_key=test_tenant_key,
                job_id=str(uuid4()),
                agent_display_name="analyzer",
                mission="Analyze codebase structure",
                status="waiting",
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)
            job_id = job.job_id

        # Mock WebSocket
        from unittest.mock import AsyncMock

        async def mock_send(msg):
            collector.add_event_sync(msg)

        mock_websocket = AsyncMock()
        mock_websocket.send_json = AsyncMock(side_effect=mock_send)

        if state.websocket_manager:
            state.websocket_manager.active_connections["test_client"] = mock_websocket
            state.websocket_manager.auth_contexts["test_client"] = {"tenant_key": test_tenant_key}

        try:
            # Acknowledge job via API
            response = await async_client.post(f"/api/agent/agent-jobs/{job_id}/acknowledge", headers=auth_headers)

            assert response.status_code == 200

            # Wait for WebSocket event
            event = await collector.wait_for_event("agent:status_changed", timeout=2.0)

            assert event is not None, "Did not receive agent:status_changed event"
            assert event["type"] == "agent:status_changed"
            assert event["data"]["job_id"] == job_id
            assert event["data"]["old_status"] == "pending"
            assert event["data"]["status"] == "active"
            assert "timestamp" in event

        finally:
            if state.websocket_manager:
                state.websocket_manager.disconnect("test_client")

    @pytest.mark.asyncio
    async def test_job_completed_event(self, async_client, auth_headers, test_tenant_key, test_db):
        """Test that job completion broadcasts agent_job:completed event with duration."""
        collector = WebSocketEventCollector()

        # Create an active job
        async with test_db.get_session_async() as session:
            job = AgentExecution(
                tenant_key=test_tenant_key,
                job_id=str(uuid4()),
                agent_display_name="implementer",
                mission="Implement authentication module",
                status="active",
                started_at=datetime.utcnow(),
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)
            job_id = job.job_id

        # Mock WebSocket
        from unittest.mock import AsyncMock

        async def mock_send(msg):
            collector.add_event_sync(msg)

        mock_websocket = AsyncMock()
        mock_websocket.send_json = AsyncMock(side_effect=mock_send)

        if state.websocket_manager:
            state.websocket_manager.active_connections["test_client"] = mock_websocket
            state.websocket_manager.auth_contexts["test_client"] = {"tenant_key": test_tenant_key}

        try:
            # Complete job via API
            response = await async_client.put(
                f"/api/agent/agent-jobs/{job_id}/status", headers=auth_headers, json={"status": "completed"}
            )

            assert response.status_code == 200

            # Wait for WebSocket event
            event = await collector.wait_for_event("agent:status_changed", timeout=2.0)

            assert event is not None, "Did not receive agent:status_changed event"
            assert event["type"] == "agent:status_changed"
            assert event["data"]["job_id"] == job_id
            assert event["data"]["old_status"] == "active"
            assert event["data"]["status"] == "completed"
            assert "duration_seconds" in event["data"]
            assert event["data"]["duration_seconds"] >= 0
            assert "timestamp" in event

        finally:
            if state.websocket_manager:
                state.websocket_manager.disconnect("test_client")

    @pytest.mark.asyncio
    async def test_job_failed_event(self, async_client, auth_headers, test_tenant_key, test_db):
        """Test that job failure broadcasts agent_job:failed event."""
        collector = WebSocketEventCollector()

        # Create an active job
        async with test_db.get_session_async() as session:
            job = AgentExecution(
                tenant_key=test_tenant_key,
                job_id=str(uuid4()),
                agent_display_name="tester",
                mission="Run integration tests",
                status="active",
                started_at=datetime.utcnow(),
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)
            job_id = job.job_id

        # Mock WebSocket
        from unittest.mock import AsyncMock

        async def mock_send(msg):
            collector.add_event_sync(msg)

        mock_websocket = AsyncMock()
        mock_websocket.send_json = AsyncMock(side_effect=mock_send)

        if state.websocket_manager:
            state.websocket_manager.active_connections["test_client"] = mock_websocket
            state.websocket_manager.auth_contexts["test_client"] = {"tenant_key": test_tenant_key}

        try:
            # Fail job via API
            response = await async_client.put(
                f"/api/agent/agent-jobs/{job_id}/status", headers=auth_headers, json={"status": "failed"}
            )

            assert response.status_code == 200

            # Wait for WebSocket event
            event = await collector.wait_for_event("agent:status_changed", timeout=2.0)

            assert event is not None, "Did not receive agent:status_changed event"
            assert event["type"] == "agent:status_changed"
            assert event["data"]["job_id"] == job_id
            assert event["data"]["status"] == "failed"
            assert "duration_seconds" in event["data"]

        finally:
            if state.websocket_manager:
                state.websocket_manager.disconnect("test_client")

    @pytest.mark.asyncio
    async def test_job_message_event(self, async_client, auth_headers, test_tenant_key, test_db):
        """Test that adding a message broadcasts agent_job:message event."""
        collector = WebSocketEventCollector()

        # Create a job
        async with test_db.get_session_async() as session:
            job = AgentExecution(
                tenant_key=test_tenant_key,
                job_id=str(uuid4()),
                agent_display_name="orchestrator",
                mission="Coordinate implementation",
                status="active",
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)
            job_id = job.job_id

        # Mock WebSocket
        from unittest.mock import AsyncMock

        async def mock_send(msg):
            collector.add_event_sync(msg)

        mock_websocket = AsyncMock()
        mock_websocket.send_json = AsyncMock(side_effect=mock_send)

        if state.websocket_manager:
            state.websocket_manager.active_connections["test_client"] = mock_websocket
            state.websocket_manager.auth_contexts["test_client"] = {"tenant_key": test_tenant_key}

        try:
            # Add message via API
            message_content = "Implementation complete, running tests now"
            response = await async_client.post(
                f"/api/agent/agent-jobs/{job_id}/messages",
                headers=auth_headers,
                json={"message": {"type": "status", "content": message_content, "from_agent": "orchestrator"}},
            )

            assert response.status_code == 200

            # Wait for WebSocket event
            event = await collector.wait_for_event("message:new", timeout=2.0)

            assert event is not None, "Did not receive message:new event"
            assert event["type"] == "message:new"
            assert event["data"]["job_id"] == job_id
            assert event["data"]["from_agent"] == "orchestrator"
            assert event["data"]["message_type"] == "status"
            assert event["data"]["message"] == message_content
            assert "message_id" in event["data"]
            assert "timestamp" in event

        finally:
            if state.websocket_manager:
                state.websocket_manager.disconnect("test_client")


class TestMultiTenantIsolation:
    """Test multi-tenant isolation in WebSocket broadcasts."""

    @pytest.mark.asyncio
    async def test_events_isolated_by_tenant(self, async_client, test_db):
        """Test that events are only broadcast to clients in the same tenant."""
        tenant_a = f"tenant-a-{uuid4()}"
        tenant_b = f"tenant-b-{uuid4()}"

        collector_a = WebSocketEventCollector()
        collector_b = WebSocketEventCollector()

        # Mock WebSockets for two different tenants
        from unittest.mock import AsyncMock

        async def mock_send_a(msg):
            collector_a.add_event_sync(msg)

        async def mock_send_b(msg):
            collector_b.add_event_sync(msg)

        mock_ws_a = AsyncMock()
        mock_ws_a.send_json = AsyncMock(side_effect=mock_send_a)

        mock_ws_b = AsyncMock()
        mock_ws_b.send_json = AsyncMock(side_effect=mock_send_b)

        if state.websocket_manager:
            state.websocket_manager.active_connections["client_a"] = mock_ws_a
            state.websocket_manager.auth_contexts["client_a"] = {"tenant_key": tenant_a}

            state.websocket_manager.active_connections["client_b"] = mock_ws_b
            state.websocket_manager.auth_contexts["client_b"] = {"tenant_key": tenant_b}

        try:
            # Create job in tenant A
            async with test_db.get_session_async() as session:
                job_a = AgentExecution(
                    tenant_key=tenant_a,
                    job_id=str(uuid4()),
                    agent_display_name="orchestrator",
                    mission="Tenant A mission",
                    status="waiting",
                )
                session.add(job_a)
                await session.commit()

            # Broadcast job created event
            if state.websocket_manager:
                await state.websocket_manager.broadcast_job_created(
                    job_id=job_a.job_id,
                    agent_display_name=job_a.agent_display_name,
                    tenant_key=tenant_a,
                    mission_preview=job_a.mission[:100],
                )

            # Wait a bit for async operations
            await asyncio.sleep(0.5)

            # Verify tenant A received the event
            events_a = await collector_a.get_events_by_type("agent_job:created")
            assert len(events_a) == 1, "Tenant A should receive the event"
            assert events_a[0]["data"]["job_id"] == job_a.job_id

            # Verify tenant B did NOT receive the event
            events_b = await collector_b.get_events_by_type("agent_job:created")
            assert len(events_b) == 0, "Tenant B should NOT receive tenant A's events"

        finally:
            if state.websocket_manager:
                state.websocket_manager.disconnect("client_a")
                state.websocket_manager.disconnect("client_b")

    @pytest.mark.asyncio
    async def test_status_updates_isolated_by_tenant(self, test_db):
        """Test that status updates respect tenant boundaries."""
        tenant_a = f"tenant-a-{uuid4()}"
        tenant_b = f"tenant-b-{uuid4()}"

        collector_a = WebSocketEventCollector()
        collector_b = WebSocketEventCollector()

        # Mock WebSockets
        from unittest.mock import AsyncMock

        async def mock_send_a(msg):
            collector_a.add_event_sync(msg)

        async def mock_send_b(msg):
            collector_b.add_event_sync(msg)

        mock_ws_a = AsyncMock()
        mock_ws_a.send_json = AsyncMock(side_effect=mock_send_a)

        mock_ws_b = AsyncMock()
        mock_ws_b.send_json = AsyncMock(side_effect=mock_send_b)

        if state.websocket_manager:
            state.websocket_manager.active_connections["client_a"] = mock_ws_a
            state.websocket_manager.auth_contexts["client_a"] = {"tenant_key": tenant_a}

            state.websocket_manager.active_connections["client_b"] = mock_ws_b
            state.websocket_manager.auth_contexts["client_b"] = {"tenant_key": tenant_b}

        try:
            # Broadcast status update to tenant A
            if state.websocket_manager:
                await state.websocket_manager.broadcast_job_status_update(
                    job_id=str(uuid4()),
                    agent_display_name="analyzer",
                    tenant_key=tenant_a,
                    old_status="waiting",
                    new_status="active",
                )

            await asyncio.sleep(0.5)

            # Verify isolation
            events_a = await collector_a.get_events_by_type("agent:status_changed")
            assert len(events_a) == 1, "Tenant A should receive the event"

            events_b = await collector_b.get_events_by_type("agent:status_changed")
            assert len(events_b) == 0, "Tenant B should NOT receive the event"

        finally:
            if state.websocket_manager:
                state.websocket_manager.disconnect("client_a")
                state.websocket_manager.disconnect("client_b")


class TestWebSocketPerformance:
    """Test WebSocket broadcast performance."""

    @pytest.mark.asyncio
    async def test_broadcast_performance_100_clients(self, test_db):
        """Test broadcast performance with 100 concurrent clients."""
        tenant_key = f"perf-tenant-{uuid4()}"
        monitor = PerformanceMonitor()

        # Mock 100 clients
        from unittest.mock import AsyncMock

        collectors = []

        if state.websocket_manager:
            for i in range(100):
                collector = WebSocketEventCollector()
                collectors.append(collector)

                # Create closure for each collector
                def make_mock_send(c):
                    async def mock_send(msg):
                        c.add_event_sync(msg)

                    return mock_send

                mock_ws = AsyncMock()
                mock_ws.send_json = AsyncMock(side_effect=make_mock_send(collector))

                state.websocket_manager.active_connections[f"client_{i}"] = mock_ws
                state.websocket_manager.auth_contexts[f"client_{i}"] = {"tenant_key": tenant_key}

        try:
            import time

            start_time = time.time()

            # Broadcast 10 events
            if state.websocket_manager:
                for i in range(10):
                    await state.websocket_manager.broadcast_job_created(
                        job_id=str(uuid4()),
                        agent_display_name="orchestrator",
                        tenant_key=tenant_key,
                        mission_preview=f"Mission {i}",
                    )

            end_time = time.time()
            duration = end_time - start_time

            # All clients should receive all events
            await asyncio.sleep(1.0)  # Wait for async broadcasts

            for i, collector in enumerate(collectors):
                events = await collector.get_events_by_type("agent_job:created")
                assert len(events) == 10, f"Client {i} should receive all 10 events"

            # Performance check: 10 broadcasts to 100 clients should complete in under 1 second
            assert duration < 1.0, f"Broadcast took too long: {duration}s"

        finally:
            if state.websocket_manager:
                for i in range(100):
                    state.websocket_manager.disconnect(f"client_{i}")


class TestErrorHandling:
    """Test error handling in WebSocket broadcasts."""

    @pytest.mark.asyncio
    async def test_broadcast_continues_on_client_error(self, test_db):
        """Test that broadcast continues if one client raises an error."""
        tenant_key = f"error-tenant-{uuid4()}"

        collector_good = WebSocketEventCollector()

        # Mock WebSockets - one that errors, one that works
        from unittest.mock import AsyncMock

        mock_ws_error = AsyncMock()
        mock_ws_error.send_json = AsyncMock(side_effect=Exception("Connection closed"))

        async def mock_send_good(msg):
            collector_good.add_event_sync(msg)

        mock_ws_good = AsyncMock()
        mock_ws_good.send_json = AsyncMock(side_effect=mock_send_good)

        if state.websocket_manager:
            state.websocket_manager.active_connections["error_client"] = mock_ws_error
            state.websocket_manager.auth_contexts["error_client"] = {"tenant_key": tenant_key}

            state.websocket_manager.active_connections["good_client"] = mock_ws_good
            state.websocket_manager.auth_contexts["good_client"] = {"tenant_key": tenant_key}

        try:
            # Broadcast event
            if state.websocket_manager:
                await state.websocket_manager.broadcast_job_created(
                    job_id=str(uuid4()),
                    agent_display_name="orchestrator",
                    tenant_key=tenant_key,
                    mission_preview="Test mission",
                )

            await asyncio.sleep(0.5)

            # Good client should still receive the event
            events = await collector_good.get_events_by_type("agent_job:created")
            assert len(events) == 1, "Good client should receive event despite error client"

            # Error client should be disconnected
            assert "error_client" not in state.websocket_manager.active_connections

        finally:
            if state.websocket_manager:
                state.websocket_manager.disconnect("good_client")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
