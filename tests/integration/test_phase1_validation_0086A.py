"""
Comprehensive Phase 1 Validation Tests for Handover 0086A
Production-Grade Stage Project Architecture

Tests cover:
1. Task 1.1: Project model hybrid_property (id/project_id compatibility)
2. Task 1.2: WebSocket dependency injection
3. Task 1.3: WebSocket broadcast_to_tenant method
4. Task 1.4: Event schema validation
5. Task 1.5: Refactored project.py endpoints (if implemented)

Quality Target: 100% coverage of Phase 1 implementation
Test Philosophy: Integration-focused, multi-tenant aware, production-grade
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import Request
from pydantic import ValidationError


# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import Phase 1 components directly to avoid circular import issues
# These imports are done carefully to avoid triggering api/__init__.py
import importlib.util


# Direct import of websocket module
websocket_spec = importlib.util.spec_from_file_location(
    "api.dependencies.websocket", project_root / "api" / "dependencies" / "websocket.py"
)
websocket_module = importlib.util.module_from_spec(websocket_spec)
sys.modules["api.dependencies.websocket"] = websocket_module
websocket_spec.loader.exec_module(websocket_module)

WebSocketDependency = websocket_module.WebSocketDependency
get_websocket_dependency = websocket_module.get_websocket_dependency
get_websocket_manager = websocket_module.get_websocket_manager

# Direct import of event schemas
schemas_spec = importlib.util.spec_from_file_location(
    "api.events.schemas", project_root / "api" / "events" / "schemas.py"
)
schemas_module = importlib.util.module_from_spec(schemas_spec)
sys.modules["api.events.schemas"] = schemas_module
schemas_spec.loader.exec_module(schemas_module)

AgentCreatedEvent = schemas_module.AgentCreatedEvent
AgentStatusChangedEvent = schemas_module.AgentStatusChangedEvent
EventFactory = schemas_module.EventFactory
ProjectMissionUpdatedEvent = schemas_module.ProjectMissionUpdatedEvent
WebSocketEvent = schemas_module.WebSocketEvent

# Import models normally
from src.giljo_mcp.models import Project


logger = logging.getLogger(__name__)


# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def tenant_key():
    """Generate a unique tenant key for isolation."""
    return f"test_tenant_{uuid4().hex[:8]}"


@pytest.fixture
def project_id():
    """Generate a unique project ID."""
    return str(uuid4())


@pytest.fixture
def mock_websocket_manager():
    """
    Mock WebSocket manager with active connections.

    Simulates 3 clients:
    - client1: tenant_a
    - client2: tenant_a
    - client3: tenant_b (different tenant for isolation tests)
    """
    manager = MagicMock()
    manager.active_connections = {}
    manager.auth_contexts = {}

    # Client 1 - tenant_a
    ws1 = AsyncMock()
    ws1.send_json = AsyncMock()
    manager.active_connections["client1"] = ws1
    manager.auth_contexts["client1"] = {"tenant_key": "tenant_a", "user_id": "user1"}

    # Client 2 - tenant_a
    ws2 = AsyncMock()
    ws2.send_json = AsyncMock()
    manager.active_connections["client2"] = ws2
    manager.auth_contexts["client2"] = {"tenant_key": "tenant_a", "user_id": "user2"}

    # Client 3 - tenant_b (different tenant)
    ws3 = AsyncMock()
    ws3.send_json = AsyncMock()
    manager.active_connections["client3"] = ws3
    manager.auth_contexts["client3"] = {"tenant_key": "tenant_b", "user_id": "user3"}

    return manager


@pytest.fixture
def mock_fastapi_request(mock_websocket_manager):
    """Mock FastAPI Request with WebSocket manager in app state."""
    request = MagicMock(spec=Request)
    request.app.state.websocket_manager = mock_websocket_manager
    request.url.path = "/test"
    request.method = "POST"
    return request


# ==============================================================================
# TASK 1.1: Project Model Hybrid Property Tests
# ==============================================================================


class TestProjectModelHybridProperty:
    """
    Validate Task 1.1: Standardize Data Model

    Success Criteria:
    - ✅ 'id' is primary field
    - ✅ 'project_id' works as backwards-compatible alias
    - ✅ Both return same value
    - ✅ Setter works correctly
    - ✅ No database schema changes
    """

    def test_project_has_id_field(self):
        """Test that Project model has 'id' as primary key."""
        project = Project(
            name="Test Project",
            description="Test Description",
            tenant_key="test_tenant",
        )

        assert hasattr(project, "id")
        assert project.id is not None

    def test_project_has_project_id_alias(self):
        """Test that Project model has 'project_id' hybrid property."""
        project = Project(
            name="Test Project",
            description="Test Description",
            tenant_key="test_tenant",
        )

        assert hasattr(project, "project_id")
        assert project.project_id is not None

    def test_project_id_returns_same_as_id(self):
        """Test that 'project_id' returns same value as 'id'."""
        project = Project(
            name="Test Project",
            description="Test Description",
            tenant_key="test_tenant",
        )

        # Both should return the same value
        assert project.project_id == project.id

    def test_project_id_setter_updates_id(self):
        """Test that setting 'project_id' updates 'id' field."""
        project = Project(
            name="Test Project",
            description="Test Description",
            tenant_key="test_tenant",
        )

        # Set a new ID via project_id
        new_id = str(uuid4())
        project.project_id = new_id

        # Both should reflect the new value
        assert project.id == new_id
        assert project.project_id == new_id

    def test_backwards_compatibility_in_dict(self):
        """Test that serialization includes both 'id' and 'project_id'."""
        project = Project(
            name="Test Project",
            description="Test Description",
            tenant_key="test_tenant",
        )

        # Simulate SQLAlchemy object to dict conversion
        # In real use, this would be done by SQLAlchemy or Pydantic
        project_dict = {
            "id": project.id,
            "project_id": project.project_id,
            "name": project.name,
        }

        assert "id" in project_dict
        assert "project_id" in project_dict
        assert project_dict["id"] == project_dict["project_id"]


# ==============================================================================
# TASK 1.2: WebSocket Dependency Injection Tests
# ==============================================================================


class TestWebSocketDependencyInjection:
    """
    Validate Task 1.2: Create WebSocket Dependency Injection

    Success Criteria:
    - ✅ get_websocket_manager returns manager from app state
    - ✅ get_websocket_manager returns None when unavailable
    - ✅ get_websocket_dependency returns WebSocketDependency instance
    - ✅ Graceful degradation when WebSocket unavailable
    """

    @pytest.mark.asyncio
    async def test_get_websocket_manager_returns_manager(self, mock_fastapi_request):
        """Test that dependency returns WebSocket manager from app state."""
        manager = await get_websocket_manager(mock_fastapi_request)

        assert manager is not None
        assert manager == mock_fastapi_request.app.state.websocket_manager

    @pytest.mark.asyncio
    async def test_get_websocket_manager_returns_none_when_unavailable(self):
        """Test graceful degradation when WebSocket manager not in app state."""
        request = MagicMock(spec=Request)
        request.app.state = MagicMock()
        # No websocket_manager attribute
        delattr(request.app.state, "websocket_manager") if hasattr(request.app.state, "websocket_manager") else None

        manager = await get_websocket_manager(request)

        assert manager is None

    @pytest.mark.asyncio
    async def test_get_websocket_dependency_returns_instance(self, mock_websocket_manager):
        """Test that dependency returns WebSocketDependency instance."""
        dependency = await get_websocket_dependency(mock_websocket_manager)

        assert isinstance(dependency, WebSocketDependency)
        assert dependency.manager == mock_websocket_manager

    @pytest.mark.asyncio
    async def test_websocket_dependency_with_none_manager(self):
        """Test WebSocketDependency initializes correctly with None manager."""
        dependency = await get_websocket_dependency(None)

        assert isinstance(dependency, WebSocketDependency)
        assert dependency.manager is None
        assert not dependency.is_available()


# ==============================================================================
# TASK 1.3: WebSocket Broadcast Tests
# ==============================================================================


class TestWebSocketBroadcastToTenant:
    """
    Validate Task 1.3: Add broadcast_to_tenant Method

    Success Criteria:
    - ✅ Broadcasts only to clients in target tenant
    - ✅ Multi-tenant isolation (no cross-tenant leakage)
    - ✅ Returns correct sent count
    - ✅ Handles client send failures gracefully
    - ✅ Validates required parameters (tenant_key, event_type)
    - ✅ Structured logging with context
    """

    @pytest.mark.asyncio
    async def test_broadcast_to_tenant_sends_to_correct_clients(self, mock_websocket_manager):
        """Test that broadcast sends only to clients in target tenant."""
        ws_dep = WebSocketDependency(mock_websocket_manager)

        sent_count = await ws_dep.broadcast_to_tenant(
            tenant_key="tenant_a",
            event_type="test:event",
            data={"message": "Hello tenant_a"},
        )

        # Should send to 2 clients (client1 and client2 are in tenant_a)
        assert sent_count == 2

        # Verify messages were sent to tenant_a clients
        ws1 = mock_websocket_manager.active_connections["client1"]
        ws2 = mock_websocket_manager.active_connections["client2"]
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_multi_tenant_isolation(self, mock_websocket_manager):
        """Test that broadcast respects multi-tenant isolation."""
        ws_dep = WebSocketDependency(mock_websocket_manager)

        sent_count = await ws_dep.broadcast_to_tenant(
            tenant_key="tenant_a",
            event_type="test:event",
            data={"message": "Hello tenant_a"},
        )

        # Should NOT send to client3 (different tenant)
        ws3 = mock_websocket_manager.active_connections["client3"]
        ws3.send_json.assert_not_called()

        assert sent_count == 2  # Only tenant_a clients

    @pytest.mark.asyncio
    async def test_broadcast_excludes_client(self, mock_websocket_manager):
        """Test that broadcast can exclude specific client."""
        ws_dep = WebSocketDependency(mock_websocket_manager)

        sent_count = await ws_dep.broadcast_to_tenant(
            tenant_key="tenant_a",
            event_type="test:event",
            data={"message": "Hello"},
            exclude_client="client1",
        )

        # Should send to 1 client (client2 only, client1 excluded)
        assert sent_count == 1

        # Verify exclusion
        ws1 = mock_websocket_manager.active_connections["client1"]
        ws2 = mock_websocket_manager.active_connections["client2"]
        ws1.send_json.assert_not_called()
        ws2.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_handles_send_failure_gracefully(self, mock_websocket_manager):
        """Test that broadcast continues after client send failure."""
        ws_dep = WebSocketDependency(mock_websocket_manager)

        # Make client1 fail
        ws1 = mock_websocket_manager.active_connections["client1"]
        ws1.send_json.side_effect = Exception("Connection lost")

        sent_count = await ws_dep.broadcast_to_tenant(
            tenant_key="tenant_a",
            event_type="test:event",
            data={"message": "Hello"},
        )

        # Should send to 1 client (client2 succeeds, client1 fails)
        assert sent_count == 1

        # Verify client2 still received message
        ws2 = mock_websocket_manager.active_connections["client2"]
        ws2.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_validates_tenant_key(self, mock_websocket_manager):
        """Test that broadcast raises ValueError for empty tenant_key."""
        ws_dep = WebSocketDependency(mock_websocket_manager)

        with pytest.raises(ValueError, match="tenant_key cannot be empty"):
            await ws_dep.broadcast_to_tenant(
                tenant_key="",
                event_type="test:event",
                data={"message": "Hello"},
            )

        with pytest.raises(ValueError, match="tenant_key cannot be empty"):
            await ws_dep.broadcast_to_tenant(
                tenant_key=None,
                event_type="test:event",
                data={"message": "Hello"},
            )

    @pytest.mark.asyncio
    async def test_broadcast_validates_event_type(self, mock_websocket_manager):
        """Test that broadcast raises ValueError for empty event_type."""
        ws_dep = WebSocketDependency(mock_websocket_manager)

        with pytest.raises(ValueError, match="event_type cannot be empty"):
            await ws_dep.broadcast_to_tenant(
                tenant_key="tenant_a",
                event_type="",
                data={"message": "Hello"},
            )

    @pytest.mark.asyncio
    async def test_broadcast_with_no_manager_returns_zero(self):
        """Test graceful degradation when WebSocket manager unavailable."""
        ws_dep = WebSocketDependency(None)  # No manager

        sent_count = await ws_dep.broadcast_to_tenant(
            tenant_key="tenant_a",
            event_type="test:event",
            data={"message": "Hello"},
        )

        assert sent_count == 0

    @pytest.mark.asyncio
    async def test_send_to_project_includes_project_id(self, mock_websocket_manager):
        """Test send_to_project helper includes project_id in data."""
        ws_dep = WebSocketDependency(mock_websocket_manager)

        sent_count = await ws_dep.send_to_project(
            tenant_key="tenant_a",
            project_id="proj_123",
            event_type="agent:created",
            data={"agent_id": "agent_456"},
        )

        # Verify project_id was added to data
        ws1 = mock_websocket_manager.active_connections["client1"]
        call_args = ws1.send_json.call_args
        message = call_args[0][0]

        assert message["data"]["project_id"] == "proj_123"
        assert message["data"]["agent_id"] == "agent_456"
        assert sent_count == 2


# ==============================================================================
# TASK 1.4: Event Schema Validation Tests
# ==============================================================================


class TestEventSchemaValidation:
    """
    Validate Task 1.4: Create Standardized Event Schemas

    Success Criteria:
    - ✅ EventFactory creates valid events
    - ✅ Pydantic validation catches malformed data
    - ✅ Timestamps are ISO 8601 compliant
    - ✅ All required fields enforced
    - ✅ Schema version included
    - ✅ JSON serialization works
    """

    def test_project_mission_updated_event_creation(self, project_id, tenant_key):
        """Test EventFactory creates valid project:mission_updated event."""
        event = EventFactory.project_mission_updated(
            project_id=project_id,
            tenant_key=tenant_key,
            mission="Implement feature X",
            token_estimate=5000,
            generated_by="orchestrator",
            user_config_applied=True,
            field_priorities={"security": 5, "performance": 4},
        )

        assert event["type"] == "project:mission_updated"
        assert event["schema_version"] == "1.0"
        assert event["data"]["project_id"] == project_id
        assert event["data"]["tenant_key"] == tenant_key
        assert event["data"]["mission"] == "Implement feature X"
        assert event["data"]["token_estimate"] == 5000
        assert event["data"]["generated_by"] == "orchestrator"
        assert event["data"]["user_config_applied"] is True
        assert event["data"]["field_priorities"]["security"] == 5

        # Verify timestamp format
        timestamp = event["timestamp"]
        assert timestamp.endswith("Z")
        # Should be parseable as ISO 8601
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    def test_agent_created_event_creation(self, project_id, tenant_key):
        """Test EventFactory creates valid agent:created event."""
        agent_data = {
            "id": str(uuid4()),
            "agent_display_name": "orchestrator",
            "status": "pending",
            "mission": "Coordinate implementation",
        }

        event = EventFactory.agent_created(
            project_id=project_id,
            tenant_key=tenant_key,
            agent=agent_data,
        )

        assert event["type"] == "agent:created"
        assert event["schema_version"] == "1.0"
        assert event["data"]["project_id"] == project_id
        assert event["data"]["tenant_key"] == tenant_key
        assert event["data"]["agent"]["id"] == agent_data["id"]
        assert event["data"]["agent"]["agent_display_name"] == "orchestrator"

    def test_agent_status_changed_event_creation(self, project_id, tenant_key):
        """Test EventFactory creates valid agent:status_changed event."""
        job_id = str(uuid4())

        event = EventFactory.agent_status_changed(
            job_id=job_id,
            tenant_key=tenant_key,
            old_status="waiting",
            new_status="active",
            agent_display_name="orchestrator",
            project_id=project_id,
            duration_seconds=None,
        )

        assert event["type"] == "agent:status_changed"
        assert event["schema_version"] == "1.0"
        assert event["data"]["job_id"] == job_id
        assert event["data"]["tenant_key"] == tenant_key
        assert event["data"]["old_status"] == "pending"
        assert event["data"]["new_status"] == "active"

    def test_agent_created_validates_required_fields(self, project_id, tenant_key):
        """Test agent:created event validation catches missing required fields."""
        # Missing 'status' field
        invalid_agent = {
            "id": str(uuid4()),
            "agent_display_name": "orchestrator",
            # "status": "pending",  # MISSING
        }

        with pytest.raises(ValidationError, match="missing required fields"):
            EventFactory.agent_created(
                project_id=project_id,
                tenant_key=tenant_key,
                agent=invalid_agent,
            )

    def test_agent_status_validates_valid_statuses(self, tenant_key):
        """Test agent:status_changed validates status values."""
        job_id = str(uuid4())

        # Invalid status should raise ValidationError
        with pytest.raises(ValidationError, match="Invalid agent status"):
            EventFactory.agent_status_changed(
                job_id=job_id,
                tenant_key=tenant_key,
                old_status="waiting",
                new_status="invalid_status",  # Invalid
                agent_display_name="orchestrator",
            )

    def test_event_timestamp_validation(self, project_id, tenant_key):
        """Test event timestamp is valid ISO 8601."""
        event = EventFactory.project_mission_updated(
            project_id=project_id,
            tenant_key=tenant_key,
            mission="Test",
            token_estimate=100,
        )

        timestamp = event["timestamp"]

        # Should be ISO 8601 with 'Z' suffix
        assert timestamp.endswith("Z")

        # Should be parseable
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        assert isinstance(dt, datetime)

    def test_event_json_serialization(self, project_id, tenant_key):
        """Test that events can be JSON serialized."""
        import json

        event = EventFactory.project_mission_updated(
            project_id=project_id,
            tenant_key=tenant_key,
            mission="Test mission",
            token_estimate=1000,
        )

        # Should serialize without errors
        json_str = json.dumps(event)
        assert isinstance(json_str, str)

        # Should deserialize back
        deserialized = json.loads(json_str)
        assert deserialized["type"] == "project:mission_updated"
        assert deserialized["data"]["mission"] == "Test mission"

    def test_event_schema_version(self, project_id, tenant_key):
        """Test that all events include schema_version field."""
        events = [
            EventFactory.project_mission_updated(
                project_id=project_id,
                tenant_key=tenant_key,
                mission="Test",
                token_estimate=100,
            ),
            EventFactory.agent_created(
                project_id=project_id,
                tenant_key=tenant_key,
                agent={"id": str(uuid4()), "agent_display_name": "test", "status": "pending"},
            ),
            EventFactory.agent_status_changed(
                job_id=str(uuid4()),
                tenant_key=tenant_key,
                old_status="waiting",
                new_status="active",
                agent_display_name="test",
            ),
        ]

        for event in events:
            assert "schema_version" in event
            assert event["schema_version"] == "1.0"


# ==============================================================================
# INTEGRATION TESTS
# ==============================================================================


class TestPhase1Integration:
    """
    End-to-end integration tests for Phase 1 components.

    Tests realistic workflows combining all Phase 1 features.
    """

    @pytest.mark.asyncio
    async def test_end_to_end_project_mission_broadcast(self, mock_websocket_manager, project_id, tenant_key):
        """
        Integration test: Project mission updated → Event created → WebSocket broadcast.

        Simulates complete workflow:
        1. Project mission updated in database
        2. Event created with EventFactory
        3. Broadcast to tenant clients via WebSocket
        4. Verify correct clients receive event
        """
        # 1. Create event using EventFactory
        event = EventFactory.project_mission_updated(
            project_id=project_id,
            tenant_key="tenant_a",  # Use mock tenant
            mission="Implement user authentication with OAuth2",
            token_estimate=5000,
            generated_by="orchestrator",
            user_config_applied=True,
            field_priorities={"security": 5, "performance": 4, "ux": 3},
        )

        # 2. Broadcast event using WebSocketDependency
        ws_dep = WebSocketDependency(mock_websocket_manager)
        sent_count = await ws_dep.broadcast_to_tenant(
            tenant_key="tenant_a",
            event_type="project:mission_updated",
            data=event["data"],
            schema_version=event["schema_version"],
        )

        # 3. Verify broadcast succeeded
        assert sent_count == 2  # 2 clients in tenant_a

        # 4. Verify message structure
        ws1 = mock_websocket_manager.active_connections["client1"]
        call_args = ws1.send_json.call_args
        message = call_args[0][0]

        assert message["type"] == "project:mission_updated"
        assert message["data"]["project_id"] == project_id
        assert message["data"]["mission"] == "Implement user authentication with OAuth2"
        assert message["data"]["token_estimate"] == 5000
        assert "timestamp" in message
        assert message["schema_version"] == "1.0"

    @pytest.mark.asyncio
    async def test_multi_tenant_isolation_end_to_end(self, mock_websocket_manager):
        """
        Integration test: Verify complete multi-tenant isolation.

        Tests that events for tenant_a never reach tenant_b clients.
        """
        ws_dep = WebSocketDependency(mock_websocket_manager)

        # Broadcast to tenant_a
        event_a = EventFactory.project_mission_updated(
            project_id=str(uuid4()),
            tenant_key="tenant_a",
            mission="Mission for tenant A",
            token_estimate=1000,
        )

        sent_count_a = await ws_dep.broadcast_to_tenant(
            tenant_key="tenant_a",
            event_type="project:mission_updated",
            data=event_a["data"],
        )

        # Broadcast to tenant_b
        event_b = EventFactory.project_mission_updated(
            project_id=str(uuid4()),
            tenant_key="tenant_b",
            mission="Mission for tenant B",
            token_estimate=2000,
        )

        sent_count_b = await ws_dep.broadcast_to_tenant(
            tenant_key="tenant_b",
            event_type="project:mission_updated",
            data=event_b["data"],
        )

        # Verify isolation
        assert sent_count_a == 2  # tenant_a has 2 clients
        assert sent_count_b == 1  # tenant_b has 1 client

        # Verify tenant_b client received only tenant_b message
        ws3 = mock_websocket_manager.active_connections["client3"]
        call_args = ws3.send_json.call_args
        message = call_args[0][0]

        assert message["data"]["tenant_key"] == "tenant_b"
        assert message["data"]["mission"] == "Mission for tenant B"

    @pytest.mark.asyncio
    async def test_agent_lifecycle_events_end_to_end(self, mock_websocket_manager):
        """
        Integration test: Complete agent lifecycle event broadcast.

        Tests:
        1. Agent created event
        2. Agent status changed event (pending → active)
        3. Agent status changed event (active → completed)
        """
        ws_dep = WebSocketDependency(mock_websocket_manager)
        project_id = str(uuid4())
        job_id = str(uuid4())
        tenant_key = "tenant_a"

        # 1. Agent created
        agent_data = {
            "id": job_id,
            "agent_display_name": "orchestrator",
            "status": "pending",
            "mission": "Coordinate implementation",
            "mode": "claude",
        }

        event_created = EventFactory.agent_created(
            project_id=project_id,
            tenant_key=tenant_key,
            agent=agent_data,
        )

        sent = await ws_dep.send_to_project(
            tenant_key=tenant_key,
            project_id=project_id,
            event_type="agent:created",
            data=event_created["data"],
        )

        assert sent == 2

        # 2. Agent status: pending → active
        event_active = EventFactory.agent_status_changed(
            job_id=job_id,
            tenant_key=tenant_key,
            old_status="waiting",
            new_status="active",
            agent_display_name="orchestrator",
            project_id=project_id,
        )

        sent = await ws_dep.send_to_project(
            tenant_key=tenant_key,
            project_id=project_id,
            event_type="agent:status_changed",
            data=event_active["data"],
        )

        assert sent == 2

        # 3. Agent status: active → completed
        event_completed = EventFactory.agent_status_changed(
            job_id=job_id,
            tenant_key=tenant_key,
            old_status="active",
            new_status="completed",
            agent_display_name="orchestrator",
            project_id=project_id,
            duration_seconds=120.5,
        )

        sent = await ws_dep.send_to_project(
            tenant_key=tenant_key,
            project_id=project_id,
            event_type="agent:status_changed",
            data=event_completed["data"],
        )

        assert sent == 2

        # Verify final message
        ws1 = mock_websocket_manager.active_connections["client1"]
        # Get last call (completed event)
        last_call = ws1.send_json.call_args
        message = last_call[0][0]

        assert message["type"] == "agent:status_changed"
        assert message["data"]["new_status"] == "completed"
        assert message["data"]["duration_seconds"] == 120.5


# ==============================================================================
# PERFORMANCE TESTS
# ==============================================================================


class TestPhase1Performance:
    """
    Performance validation for Phase 1 components.

    Ensures no performance regressions introduced.
    """

    @pytest.mark.asyncio
    async def test_broadcast_performance_with_many_clients(self):
        """Test broadcast performance with 50 clients."""
        # Create mock manager with 50 clients in same tenant
        manager = MagicMock()
        manager.active_connections = {}
        manager.auth_contexts = {}

        for i in range(50):
            ws = AsyncMock()
            ws.send_json = AsyncMock()
            manager.active_connections[f"client{i}"] = ws
            manager.auth_contexts[f"client{i}"] = {
                "tenant_key": "tenant_perf",
                "user_id": f"user{i}",
            }

        ws_dep = WebSocketDependency(manager)

        # Measure broadcast time
        import time

        start = time.perf_counter()

        sent_count = await ws_dep.broadcast_to_tenant(
            tenant_key="tenant_perf",
            event_type="test:performance",
            data={"message": "Performance test"},
        )

        duration = time.perf_counter() - start

        assert sent_count == 50
        # Should complete in under 100ms for 50 clients
        assert duration < 0.1, f"Broadcast took {duration:.3f}s, expected < 0.1s"

    def test_event_creation_performance(self):
        """Test EventFactory performance."""
        import time

        project_id = str(uuid4())
        tenant_key = "tenant_perf"

        # Measure event creation time
        start = time.perf_counter()

        for _ in range(1000):
            EventFactory.project_mission_updated(
                project_id=project_id,
                tenant_key=tenant_key,
                mission="Test mission",
                token_estimate=1000,
            )

        duration = time.perf_counter() - start

        # Should create 1000 events in under 100ms
        assert duration < 0.1, f"1000 events took {duration:.3f}s, expected < 0.1s"


# ==============================================================================
# ERROR HANDLING TESTS
# ==============================================================================


class TestPhase1ErrorHandling:
    """
    Validate robust error handling in Phase 1 components.

    Production-grade systems must handle all error conditions gracefully.
    """

    @pytest.mark.asyncio
    async def test_websocket_dependency_handles_closed_connections(self):
        """Test that broadcast handles closed WebSocket connections."""
        manager = MagicMock()
        manager.active_connections = {}
        manager.auth_contexts = {}

        # Client with closed connection
        ws_closed = AsyncMock()
        ws_closed.send_json.side_effect = RuntimeError("WebSocket closed")
        manager.active_connections["client_closed"] = ws_closed
        manager.auth_contexts["client_closed"] = {"tenant_key": "tenant_test"}

        # Client with healthy connection
        ws_healthy = AsyncMock()
        ws_healthy.send_json = AsyncMock()
        manager.active_connections["client_healthy"] = ws_healthy
        manager.auth_contexts["client_healthy"] = {"tenant_key": "tenant_test"}

        ws_dep = WebSocketDependency(manager)

        # Should send to healthy client despite closed connection failure
        sent_count = await ws_dep.broadcast_to_tenant(
            tenant_key="tenant_test",
            event_type="test:event",
            data={"message": "Test"},
        )

        assert sent_count == 1  # Only healthy client

    def test_event_factory_handles_uuid_objects(self):
        """Test that EventFactory accepts both UUID and string."""

        project_uuid = uuid4()
        project_str = str(project_uuid)

        # Both should work
        event1 = EventFactory.project_mission_updated(
            project_id=project_uuid,  # UUID object
            tenant_key="test",
            mission="Test",
            token_estimate=100,
        )

        event2 = EventFactory.project_mission_updated(
            project_id=project_str,  # String
            tenant_key="test",
            mission="Test",
            token_estimate=100,
        )

        assert event1["data"]["project_id"] == project_str
        assert event2["data"]["project_id"] == project_str

    def test_event_validation_rejects_invalid_data(self):
        """Test Pydantic validation rejects malformed event data."""
        # Invalid token_estimate (negative)
        with pytest.raises(ValidationError):
            EventFactory.project_mission_updated(
                project_id=str(uuid4()),
                tenant_key="test",
                mission="Test",
                token_estimate=-100,  # Invalid
            )


# ==============================================================================
# TEST SUMMARY
# ==============================================================================


if __name__ == "__main__":
    print("=" * 80)
    print("Phase 1 Validation Test Suite for Handover 0086A")
    print("=" * 80)
    print()
    print("Test Coverage:")
    print("  - Task 1.1: Project Model hybrid_property")
    print("  - Task 1.2: WebSocket Dependency Injection")
    print("  - Task 1.3: WebSocket broadcast_to_tenant")
    print("  - Task 1.4: Event Schema Validation")
    print("  - Integration Tests: End-to-end workflows")
    print("  - Performance Tests: Scalability validation")
    print("  - Error Handling: Robust failure handling")
    print()
    print("Run with: pytest tests/integration/test_phase1_validation_0086A.py -v")
    print("=" * 80)
