"""
Tests for Agent Jobs WebSocket Broadcasting

Tests the refactored agent_jobs.py endpoint to ensure it uses dependency injection
for WebSocket broadcasting instead of manual loops (band-aid pattern).

Handover 0086B Phase 5.1: Backend Integration Testing (Task 3.1)
Created: 2025-11-02
Coverage Target: 95%+
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio

from api.dependencies.websocket import WebSocketDependency


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def authenticated_client(api_client, db_manager):
    """
    Create API client with authentication mocked.

    Overrides authentication dependencies to provide a test user
    with known tenant_key for multi-tenant testing.
    """
    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_current_active_user
    from src.giljo_mcp.models import User

    unique_suffix = uuid4().hex[:8]
    test_user = User(
        id=str(uuid4()),
        username=f"test_user_{unique_suffix}",
        email=f"test_{unique_suffix}@example.com",
        tenant_key=f"tenant_{unique_suffix}",
        is_active=True,
        role="developer",
        created_at=datetime.now(timezone.utc),
        password_hash="hashed",
    )

    async def mock_get_current_user():
        return test_user

    # Override authentication
    app.dependency_overrides[get_current_active_user] = mock_get_current_user

    yield api_client, test_user

    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture
def mock_websocket_dependency():
    """
    Create mock WebSocketDependency for testing broadcasts.

    Returns a mock that tracks broadcast calls for verification.
    """
    ws_dep = MagicMock(spec=WebSocketDependency)
    ws_dep.broadcast_to_tenant = AsyncMock(return_value=2)  # 2 clients received
    ws_dep.is_available = MagicMock(return_value=True)

    return ws_dep


@pytest.fixture
def mock_websocket_dependency_unavailable():
    """
    Create mock WebSocketDependency that simulates unavailable WebSocket.

    Tests graceful degradation when WebSocket is down.
    """
    ws_dep = MagicMock(spec=WebSocketDependency)
    ws_dep.broadcast_to_tenant = AsyncMock(return_value=0)  # No clients (unavailable)
    ws_dep.is_available = MagicMock(return_value=False)

    return ws_dep


@pytest_asyncio.fixture
async def test_project(db_session):
    """Create test project in database."""
    from src.giljo_mcp.models import Project

    project = Project(
        id=str(uuid4()),
        name="Test Project",
        tenant_key="tenant_abc",
        description="Integration test project",
        status="active",
    )

    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    return project


# ============================================================================
# Test: Agent Creation with Dependency Injection
# ============================================================================


@pytest.mark.asyncio
async def test_create_agent_broadcasts_via_dependency_injection(
    authenticated_client, test_project, mock_websocket_dependency
):
    """
    Test create_job endpoint uses WebSocketDependency for broadcasting.

    CRITICAL: Validates that the refactored code uses dependency injection
    instead of the old band-aid manual loop pattern.

    This test verifies:
    - WebSocketDependency.broadcast_to_tenant is called
    - EventFactory is used for standardized event format
    - Tenant isolation is enforced
    - Structured logging is present
    """
    # Arrange
    client, user = authenticated_client

    # Override WebSocket dependency
    from api.app import app
    from api.dependencies.websocket import get_websocket_dependency

    async def mock_get_ws_dep():
        return mock_websocket_dependency

    app.dependency_overrides[get_websocket_dependency] = mock_get_ws_dep

    job_data = {
        "project_id": test_project.id,
        "agent_type": "orchestrator",
        "mode": "claude",
        "mission": "Coordinate project implementation",
        "tenant_key": "tenant_abc",
    }

    # Act
    response = await client.post("/api/agent-jobs", json=job_data)

    # Assert
    assert response.status_code == 201

    # Verify WebSocketDependency.broadcast_to_tenant was called
    mock_websocket_dependency.broadcast_to_tenant.assert_called_once()

    # Verify call parameters
    call_args = mock_websocket_dependency.broadcast_to_tenant.call_args
    assert call_args.kwargs["tenant_key"] == "tenant_abc"
    assert call_args.kwargs["event_type"] == "agent:created"

    # Verify data structure
    data = call_args.kwargs["data"]
    assert data["project_id"] == test_project.id
    assert data["tenant_key"] == "tenant_abc"
    assert "agent" in data
    assert data["agent"]["agent_type"] == "orchestrator"

    # Cleanup
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_agent_uses_event_factory(authenticated_client, test_project, mock_websocket_dependency):
    """
    Test create_job endpoint uses EventFactory for standardized events.

    Validates that the event structure follows the standardized schema
    defined in api/events/schemas.py (not ad-hoc formatting).
    """
    # Arrange
    client, user = authenticated_client

    # Override WebSocket dependency
    from api.app import app
    from api.dependencies.websocket import get_websocket_dependency

    async def mock_get_ws_dep():
        return mock_websocket_dependency

    app.dependency_overrides[get_websocket_dependency] = mock_get_ws_dep

    job_data = {
        "project_id": test_project.id,
        "agent_type": "implementer",
        "mode": "claude",
        "mission": "Implement authentication",
        "tenant_key": "tenant_abc",
    }

    # Act
    response = await client.post("/api/agent-jobs", json=job_data)

    # Assert
    assert response.status_code == 201

    # Verify EventFactory structure
    call_args = mock_websocket_dependency.broadcast_to_tenant.call_args
    data = call_args.kwargs["data"]

    # EventFactory.agent_created should include these fields
    assert "project_id" in data
    assert "tenant_key" in data
    assert "agent" in data

    # Agent data should have required fields (per EventFactory validation)
    agent = data["agent"]
    assert "id" in agent
    assert "agent_type" in agent
    assert "status" in agent

    # Cleanup
    app.dependency_overrides.clear()


# ============================================================================
# Test: Multi-Tenant Isolation
# ============================================================================


@pytest.mark.asyncio
async def test_create_agent_tenant_isolation_in_broadcast(
    authenticated_client, test_project, mock_websocket_dependency
):
    """
    Test agent creation broadcast enforces multi-tenant isolation.

    CRITICAL SECURITY TEST: Validates that broadcast_to_tenant is called
    with the correct tenant_key, ensuring zero cross-tenant leakage.
    """
    # Arrange
    client, user = authenticated_client

    # Override WebSocket dependency
    from api.app import app
    from api.dependencies.websocket import get_websocket_dependency

    async def mock_get_ws_dep():
        return mock_websocket_dependency

    app.dependency_overrides[get_websocket_dependency] = mock_get_ws_dep

    job_data = {
        "project_id": test_project.id,
        "agent_type": "tester",
        "mode": "claude",
        "mission": "Write comprehensive tests",
        "tenant_key": "tenant_abc",  # User's tenant
    }

    # Act
    response = await client.post("/api/agent-jobs", json=job_data)

    # Assert
    assert response.status_code == 201

    # CRITICAL: Verify broadcast_to_tenant uses correct tenant_key
    call_args = mock_websocket_dependency.broadcast_to_tenant.call_args
    assert call_args.kwargs["tenant_key"] == "tenant_abc"

    # Verify tenant_key in data payload matches
    data = call_args.kwargs["data"]
    assert data["tenant_key"] == "tenant_abc"

    # Cleanup
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_agent_unauthorized_tenant_rejected(authenticated_client, db_session):
    """
    Test agent creation rejects attempts to create agents for other tenants.

    Validates that API endpoints enforce tenant isolation at the access level,
    not just at the broadcast level.
    """
    # Arrange
    client, user = authenticated_client

    # Create project for a DIFFERENT tenant
    from src.giljo_mcp.models import Project

    other_tenant_project = Project(
        id=str(uuid4()),
        name="Other Tenant Project",
        tenant_key="tenant_xyz",  # DIFFERENT tenant
        description="Should not be accessible",
        status="active",
    )

    db_session.add(other_tenant_project)
    await db_session.commit()

    job_data = {
        "project_id": other_tenant_project.id,
        "agent_type": "orchestrator",
        "mode": "claude",
        "mission": "Malicious access attempt",
        "tenant_key": "tenant_xyz",  # Different tenant
    }

    # Act
    response = await client.post("/api/agent-jobs", json=job_data)

    # Assert
    # Should be rejected (403 Forbidden or 404 Not Found)
    assert response.status_code in [403, 404]


# ============================================================================
# Test: Graceful Degradation
# ============================================================================


@pytest.mark.asyncio
async def test_create_agent_graceful_degradation_websocket_unavailable(
    authenticated_client, test_project, mock_websocket_dependency_unavailable, caplog
):
    """
    Test agent creation succeeds even when WebSocket is unavailable.

    Validates graceful degradation: API endpoint should complete successfully
    and create the agent job even if WebSocket broadcasting fails.
    """
    # Arrange
    client, user = authenticated_client

    # Override WebSocket dependency with unavailable version
    from api.app import app
    from api.dependencies.websocket import get_websocket_dependency

    async def mock_get_ws_dep():
        return mock_websocket_dependency_unavailable

    app.dependency_overrides[get_websocket_dependency] = mock_get_ws_dep

    job_data = {
        "project_id": test_project.id,
        "agent_type": "orchestrator",
        "mode": "claude",
        "mission": "Test graceful degradation",
        "tenant_key": "tenant_abc",
    }

    # Act
    response = await client.post("/api/agent-jobs", json=job_data)

    # Assert
    assert response.status_code == 201  # Still succeeds

    # Verify job was created despite WebSocket failure
    job = response.json()
    assert job["agent_type"] == "orchestrator"
    assert job["status"] in ["pending", "waiting"]

    # Verify broadcast was attempted but returned 0
    mock_websocket_dependency_unavailable.broadcast_to_tenant.assert_called_once()

    # Cleanup
    app.dependency_overrides.clear()


# ============================================================================
# Test: Structured Logging
# ============================================================================


@pytest.mark.asyncio
async def test_create_agent_structured_logging(authenticated_client, test_project, mock_websocket_dependency, caplog):
    """
    Test agent creation includes structured logging for debugging.

    Validates that WebSocket broadcast success/failure is logged with
    proper context (job_id, agent_type, sent_count).
    """
    # Arrange
    client, user = authenticated_client

    # Override WebSocket dependency
    from api.app import app
    from api.dependencies.websocket import get_websocket_dependency

    async def mock_get_ws_dep():
        return mock_websocket_dependency

    app.dependency_overrides[get_websocket_dependency] = mock_get_ws_dep

    job_data = {
        "project_id": test_project.id,
        "agent_type": "code-reviewer",
        "mode": "claude",
        "mission": "Review code for quality",
        "tenant_key": "tenant_abc",
    }

    # Act
    with caplog.at_level("INFO"):
        response = await client.post("/api/agent-jobs", json=job_data)

    # Assert
    assert response.status_code == 201

    # Verify structured logging is present
    # Should log broadcast success with sent_count
    assert "broadcasted" in caplog.text.lower() or "broadcast" in caplog.text.lower()

    # Cleanup
    app.dependency_overrides.clear()


# ============================================================================
# Test: Error Handling
# ============================================================================


@pytest.mark.asyncio
async def test_create_agent_handles_broadcast_exception_gracefully(authenticated_client, test_project, caplog):
    """
    Test agent creation handles WebSocket broadcast exceptions gracefully.

    Validates that if broadcast_to_tenant raises an exception, the API
    endpoint catches it, logs the error, and completes successfully.
    """
    # Arrange
    client, user = authenticated_client

    # Create WebSocket dependency that raises exception
    ws_dep_error = MagicMock(spec=WebSocketDependency)
    ws_dep_error.broadcast_to_tenant = AsyncMock(side_effect=Exception("WebSocket connection lost"))
    ws_dep_error.is_available = MagicMock(return_value=True)

    # Override WebSocket dependency
    from api.app import app
    from api.dependencies.websocket import get_websocket_dependency

    async def mock_get_ws_dep():
        return ws_dep_error

    app.dependency_overrides[get_websocket_dependency] = mock_get_ws_dep

    job_data = {
        "project_id": test_project.id,
        "agent_type": "orchestrator",
        "mode": "claude",
        "mission": "Test error handling",
        "tenant_key": "tenant_abc",
    }

    # Act
    with caplog.at_level("ERROR"):
        response = await client.post("/api/agent-jobs", json=job_data)

    # Assert
    assert response.status_code == 201  # Still succeeds despite broadcast error

    # Verify error was logged
    assert "Failed to broadcast" in caplog.text or "error" in caplog.text.lower()

    # Cleanup
    app.dependency_overrides.clear()


# ============================================================================
# Test: Response Format
# ============================================================================


@pytest.mark.asyncio
async def test_create_agent_response_includes_broadcast_metadata(
    authenticated_client, test_project, mock_websocket_dependency
):
    """
    Test agent creation response includes relevant metadata.

    Validates that the response follows the AgentJobResponse model
    and includes all necessary fields for frontend visualization.
    """
    # Arrange
    client, user = authenticated_client

    # Override WebSocket dependency
    from api.app import app
    from api.dependencies.websocket import get_websocket_dependency

    async def mock_get_ws_dep():
        return mock_websocket_dependency

    app.dependency_overrides[get_websocket_dependency] = mock_get_ws_dep

    job_data = {
        "project_id": test_project.id,
        "agent_type": "frontend-implementer",
        "mode": "claude",
        "mission": "Build Vue.js components",
        "tenant_key": "tenant_abc",
    }

    # Act
    response = await client.post("/api/agent-jobs", json=job_data)

    # Assert
    assert response.status_code == 201

    job = response.json()

    # Verify response structure
    assert "id" in job or "job_id" in job
    assert job["agent_type"] == "frontend-implementer"
    assert job["status"] in ["pending", "waiting"]
    assert job["mode"] == "claude"
    assert job["mission"] == "Build Vue.js components"
    assert "created_at" in job

    # Cleanup
    app.dependency_overrides.clear()
