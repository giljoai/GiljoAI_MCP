"""
Test suite for OrchestrationService WebSocket event emissions (Handover 0288 - TDD RED Phase).

Tests verify that OrchestrationService methods emit WebSocket events after database updates:
- acknowledge_job() emits agent:status_changed event
- complete_job() emits agent:status_changed event
- report_progress() emits progress event
- Multi-tenant isolation is preserved in WebSocket broadcasts

This is the RED phase - tests should FAIL because WebSocket emissions are not yet implemented.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call
from uuid import uuid4

from src.giljo_mcp.services.orchestration_service import OrchestrationService
from src.giljo_mcp.models.agents import MCPAgentJob
from src.giljo_mcp.models.projects import Project


@pytest.fixture
def mock_db_manager():
    """Mock database manager with async session support."""
    db_manager = MagicMock()
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)  # Don't suppress exceptions
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    db_manager.get_session_async = MagicMock(return_value=session)
    return db_manager, session


@pytest.fixture
def mock_tenant_manager():
    """Mock tenant manager."""
    tenant_manager = MagicMock()
    tenant_manager.get_current_tenant = MagicMock(return_value="tenant-test-123")
    return tenant_manager


@pytest.fixture
def orchestration_service(mock_db_manager, mock_tenant_manager):
    """Create OrchestrationService with mocked dependencies."""
    db_manager, _ = mock_db_manager
    service = OrchestrationService(
        db_manager=db_manager,
        tenant_manager=mock_tenant_manager
    )
    return service


@pytest.fixture
def mock_agent_job():
    """Create mock agent job in waiting status."""
    job = MCPAgentJob(
        job_id=str(uuid4()),
        tenant_key="tenant-test-123",
        project_id=str(uuid4()),
        agent_type="implementer",
        agent_name="impl-worker-1",
        mission="Test agent mission for WebSocket testing",
        status="waiting",
        created_at=datetime.now(timezone.utc),
        metadata={}
    )
    return job


@pytest.fixture
def mock_working_job():
    """Create mock agent job in working status."""
    job = MCPAgentJob(
        job_id=str(uuid4()),
        tenant_key="tenant-test-123",
        project_id=str(uuid4()),
        agent_type="implementer",
        agent_name="impl-worker-1",
        mission="Test agent mission for WebSocket testing",
        status="working",
        started_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        metadata={}
    )
    return job


@pytest.mark.asyncio
async def test_get_agent_mission_emits_mission_ack_and_status_changed_events(
    orchestration_service,
    mock_db_manager,
    mock_agent_job,
):
    """
    Verify get_agent_mission performs atomic job start semantics for CLI subagents.

    EXPECTED BEHAVIOR (Handover 0262 / 0332):
    1. First successful call for a waiting job sets mission_acknowledged_at and started_at
    2. Job status transitions waiting -> working
    3. After commit, it emits TWO WebSocket events via HTTP bridge:
       - job:mission_acknowledged (drives "Job Acknowledged" column)
       - agent:status_changed (waiting -> working, drives status chip)
    """
    db_manager, session = mock_db_manager
    job = mock_agent_job
    job.status = "waiting"
    job.started_at = None
    job.mission_acknowledged_at = None

    # Mock database query to return job
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=job)
    session.execute = AsyncMock(return_value=result)

    # Mock httpx client for HTTP bridge calls
    with patch("httpx.AsyncClient") as mock_httpx:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_httpx.return_value = mock_client

        # Action: First mission fetch (atomic start)
        response = await orchestration_service.get_agent_mission(
            agent_job_id=job.job_id,
            tenant_key="tenant-test-123",
        )

        # Verify response structure
        assert response["success"] is True
        assert response["agent_job_id"] == job.job_id
        assert response["status"] == "working"
        assert response["thin_client"] is True

        # Database fields should be updated
        assert job.mission_acknowledged_at is not None
        assert isinstance(job.mission_acknowledged_at, datetime)
        assert job.started_at is not None
        assert isinstance(job.started_at, datetime)
        assert job.status == "working"

        # Expect TWO bridge calls: job:mission_acknowledged and agent:status_changed
        assert mock_client.post.call_count == 2

        # Collect events by type
        events: dict[str, dict] = {}
        for call_args in mock_client.post.call_args_list:
            assert call_args[0][0] == "http://localhost:7272/api/v1/ws-bridge/emit"
            payload = call_args[1]["json"]
            event_type = payload["event_type"]
            events[event_type] = payload

        # job:mission_acknowledged event
        assert "job:mission_acknowledged" in events
        mission_payload = events["job:mission_acknowledged"]
        assert mission_payload["tenant_key"] == "tenant-test-123"
        mission_data = mission_payload["data"]
        assert mission_data["job_id"] == job.job_id
        assert mission_data["project_id"] == str(job.project_id)
        assert "mission_acknowledged_at" in mission_data

        # agent:status_changed event
        assert "agent:status_changed" in events
        status_payload = events["agent:status_changed"]
        assert status_payload["tenant_key"] == "tenant-test-123"
        status_data = status_payload["data"]
        assert status_data["job_id"] == job.job_id
        assert status_data["old_status"] == "waiting"
        assert status_data["status"] == "working"
        assert status_data["agent_type"] == job.agent_type
        assert status_data["agent_name"] == job.agent_name
        assert "started_at" in status_data


@pytest.mark.asyncio
async def test_get_agent_mission_is_idempotent_on_subsequent_calls(
    orchestration_service,
    mock_db_manager,
    mock_agent_job,
):
    """
    Verify get_agent_mission is idempotent after first mission fetch.

    EXPECTED BEHAVIOR:
    - First call: performs atomic start semantics and emits WebSocket events
    - Subsequent calls: return mission but DO NOT update timestamps or emit new events
    """
    db_manager, session = mock_db_manager
    job = mock_agent_job
    job.status = "waiting"
    job.started_at = None
    job.mission_acknowledged_at = None

    # Mock database query to always return the same job instance
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=job)
    session.execute = AsyncMock(return_value=result)

    with patch("httpx.AsyncClient") as mock_httpx:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_httpx.return_value = mock_client

        # First call - should perform atomic start
        first_response = await orchestration_service.get_agent_mission(
            agent_job_id=job.job_id,
            tenant_key="tenant-test-123",
        )
        assert first_response["success"] is True
        assert job.status == "working"
        assert job.mission_acknowledged_at is not None
        assert job.started_at is not None

        first_ack_time = job.mission_acknowledged_at
        first_started_at = job.started_at

        # Two events expected on first call
        assert mock_client.post.call_count == 2

        # Second call - should be a read-only re-fetch
        second_response = await orchestration_service.get_agent_mission(
            agent_job_id=job.job_id,
            tenant_key="tenant-test-123",
        )
        assert second_response["success"] is True
        assert second_response["agent_job_id"] == job.job_id
        assert second_response["status"] == "working"

        # mission_acknowledged_at and started_at must NOT change
        assert job.mission_acknowledged_at == first_ack_time
        assert job.started_at == first_started_at

        # No additional WebSocket bridge calls on second fetch
        assert mock_client.post.call_count == 2


@pytest.mark.asyncio
async def test_acknowledge_job_emits_websocket_event(orchestration_service, mock_db_manager, mock_agent_job):
    """
    Verify acknowledge_job emits agent:status_changed via WebSocket HTTP bridge.

    EXPECTED BEHAVIOR:
    1. acknowledge_job updates database (status: waiting -> working)
    2. After commit, it calls HTTP bridge to emit WebSocket event
    3. WebSocket event contains correct job_id, status, tenant_key
    """
    db_manager, session = mock_db_manager
    job = mock_agent_job

    # Mock database query to return job
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=job)
    session.execute = AsyncMock(return_value=result)

    # Mock httpx client for HTTP bridge calls
    with patch("httpx.AsyncClient") as mock_httpx:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_httpx.return_value = mock_client

        # Action: Call acknowledge_job
        response = await orchestration_service.acknowledge_job(
            job_id=job.job_id,
            agent_id="test-agent-id",
            tenant_key="tenant-test-123"
        )

        # Verify database update succeeded
        assert response["status"] == "success"
        assert job.status == "working"
        assert job.mission_acknowledged_at is not None  # Handover 0233: replaced acknowledged boolean

        # Assert: HTTP bridge was called with correct parameters
        mock_client.post.assert_called_once()

        call_args = mock_client.post.call_args
        assert call_args[0][0] == "http://localhost:7272/api/v1/ws-bridge/emit"

        payload = call_args[1]["json"]
        assert payload["event_type"] == "agent:status_changed"
        assert payload["tenant_key"] == "tenant-test-123"
        assert payload["data"]["job_id"] == job.job_id
        assert payload["data"]["old_status"] == "waiting"
        assert payload["data"]["status"] == "working"
        assert payload["data"]["agent_type"] == "implementer"


@pytest.mark.asyncio
async def test_complete_job_emits_websocket_event(orchestration_service, mock_db_manager, mock_working_job):
    """
    Verify complete_job emits agent:status_changed via WebSocket HTTP bridge.

    EXPECTED BEHAVIOR:
    1. complete_job updates database (status: working -> complete)
    2. After commit, it calls HTTP bridge to emit WebSocket event
    3. WebSocket event contains correct job_id, status transition
    """
    db_manager, session = mock_db_manager
    job = mock_working_job

    # Mock database query to return job
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=job)
    session.execute = AsyncMock(return_value=result)

    # Mock httpx client for HTTP bridge calls
    with patch("httpx.AsyncClient") as mock_httpx:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_httpx.return_value = mock_client

        # Action: Call complete_job
        response = await orchestration_service.complete_job(
            job_id=job.job_id,
            result={"output": "Task completed successfully", "files_modified": 3},
            tenant_key="tenant-test-123"
        )

        # Verify database update succeeded
        assert response["status"] == "success"
        assert job.status == "complete"
        assert job.completed_at is not None

        # Assert: HTTP bridge was called with correct parameters
        mock_client.post.assert_called_once()

        call_args = mock_client.post.call_args
        assert call_args[0][0] == "http://localhost:7272/api/v1/ws-bridge/emit"

        payload = call_args[1]["json"]
        assert payload["event_type"] == "agent:status_changed"
        assert payload["tenant_key"] == "tenant-test-123"
        assert payload["data"]["job_id"] == job.job_id
        assert payload["data"]["old_status"] == "working"
        assert payload["data"]["status"] == "complete"
        assert payload["data"]["agent_type"] == "implementer"


@pytest.mark.asyncio
async def test_report_progress_emits_websocket_event(orchestration_service, mock_db_manager, mock_working_job):
    """
    Verify report_progress emits progress WebSocket event via HTTP bridge.

    EXPECTED BEHAVIOR:
    1. report_progress stores progress message in message queue
    2. After storing, it emits a WebSocket progress event via HTTP bridge
    3. WebSocket event contains job_id and progress data
    """
    db_manager, session = mock_db_manager
    job = mock_working_job

    progress_data = {
        "percent": 50,
        "message": "Processing files",
        "current_step": "Code analysis",
        "total_steps": 5
    }

    # Mock database query to return job
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=job)
    session.execute = AsyncMock(return_value=result)

    # Mock message queue response
    with patch("giljo_mcp.agent_message_queue.AgentMessageQueue") as MockMessageQueue:
        mock_queue = AsyncMock()
        mock_queue.send_message = AsyncMock(return_value={"status": "success", "message_id": "msg-123"})
        MockMessageQueue.return_value = mock_queue

        # Mock httpx client for HTTP bridge calls
        with patch("httpx.AsyncClient") as mock_httpx:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.return_value = mock_client

            # Action: Call report_progress
            response = await orchestration_service.report_progress(
                job_id=job.job_id,
                progress=progress_data,
                tenant_key="tenant-test-123"
            )

            # Verify message queue was called
            assert response["status"] == "success"
            mock_queue.send_message.assert_called_once()

            # Assert: HTTP bridge was called with correct parameters
            mock_client.post.assert_called_once()

            call_args = mock_client.post.call_args
            assert call_args[0][0] == "http://localhost:7272/api/v1/ws-bridge/emit"

            payload = call_args[1]["json"]
            assert payload["event_type"] == "message:new"
            assert payload["tenant_key"] == "tenant-test-123"
            assert payload["data"]["job_id"] == job.job_id
            assert payload["data"]["progress"] == progress_data


@pytest.mark.asyncio
async def test_websocket_emission_respects_tenant_isolation(orchestration_service, mock_db_manager):
    """
    Verify WebSocket events only go to correct tenant (multi-tenant isolation).

    EXPECTED BEHAVIOR:
    1. Create jobs for two different tenants
    2. Acknowledge job for tenant A
    3. HTTP bridge should be called with ONLY tenant A's key
    4. Tenant B should NOT receive the event
    """
    db_manager, session = mock_db_manager

    # Create job for Tenant A
    tenant_a_key = "tenant-a-123"
    job_a = MCPAgentJob(
        job_id=str(uuid4()),
        tenant_key=tenant_a_key,
        project_id=str(uuid4()),
        agent_type="implementer",
        agent_name="impl-worker-a",
        mission="Tenant A mission",
        status="waiting",
        metadata={}
    )

    # Mock database query to return Tenant A's job
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=job_a)
    session.execute = AsyncMock(return_value=result)

    # Mock httpx client for HTTP bridge calls
    with patch("httpx.AsyncClient") as mock_httpx:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_httpx.return_value = mock_client

        # Action: Acknowledge Tenant A's job
        response = await orchestration_service.acknowledge_job(
            job_id=job_a.job_id,
            agent_id="test-agent-a",
            tenant_key=tenant_a_key
        )

        # Verify success
        assert response["status"] == "success"

        # Assert: HTTP bridge was called ONLY with Tenant A's key
        mock_client.post.assert_called_once()

        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["tenant_key"] == tenant_a_key
        assert payload["data"]["job_id"] == job_a.job_id

        # Verify no other tenant keys were used
        assert payload["tenant_key"] != "tenant-b-123"
        assert payload["tenant_key"] != "other-tenant"


@pytest.mark.asyncio
async def test_acknowledge_job_websocket_event_includes_agent_name(orchestration_service, mock_db_manager, mock_agent_job):
    """
    Verify WebSocket event includes agent_name for dashboard display.

    EXPECTED BEHAVIOR:
    - WebSocket event should include agent_name from job
    - Frontend needs this to display "impl-worker-1: working" in dashboard
    """
    db_manager, session = mock_db_manager
    job = mock_agent_job
    job.agent_name = "impl-worker-42"

    # Mock database query
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=job)
    session.execute = AsyncMock(return_value=result)

    # Mock httpx client for HTTP bridge calls
    with patch("httpx.AsyncClient") as mock_httpx:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_httpx.return_value = mock_client

        # Action: Call acknowledge_job
        await orchestration_service.acknowledge_job(
            job_id=job.job_id,
            agent_id="test-agent-id",
            tenant_key="tenant-test-123"
        )

        # Assert: WebSocket event includes agent_name
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["data"]["agent_type"] == "implementer"
        assert payload["data"]["agent_name"] == "impl-worker-42"


@pytest.mark.asyncio
async def test_complete_job_calculates_duration_for_websocket(orchestration_service, mock_db_manager, mock_working_job):
    """
    Verify complete_job calculates and includes job duration in WebSocket event.

    EXPECTED BEHAVIOR:
    - When job completes, calculate duration from started_at to completed_at
    - Include duration_seconds in WebSocket event for dashboard metrics
    """
    db_manager, session = mock_db_manager
    job = mock_working_job

    # Set started_at to 60 seconds ago
    from datetime import timedelta
    job.started_at = datetime.now(timezone.utc) - timedelta(seconds=60)

    # Mock database query
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=job)
    session.execute = AsyncMock(return_value=result)

    # Mock httpx client for HTTP bridge calls
    with patch("httpx.AsyncClient") as mock_httpx:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_httpx.return_value = mock_client

        # Action: Call complete_job
        await orchestration_service.complete_job(
            job_id=job.job_id,
            result={"output": "Done"},
            tenant_key="tenant-test-123"
        )

        # Assert: WebSocket event includes duration
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]

        assert payload["data"]["status"] == "complete"
        assert "duration_seconds" in payload["data"]
        # Duration should be approximately 60 seconds (allow some variance for test execution time)
        assert 59 <= payload["data"]["duration_seconds"] <= 61


@pytest.mark.asyncio
async def test_websocket_emission_failure_does_not_break_database_update(orchestration_service, mock_db_manager, mock_agent_job):
    """
    Verify that WebSocket emission failures don't prevent database updates.

    EXPECTED BEHAVIOR:
    1. Database update should succeed
    2. If HTTP bridge fails, log error but don't raise exception
    3. Method should still return success

    This ensures system resilience - WebSocket issues don't break core functionality.
    """
    db_manager, session = mock_db_manager
    job = mock_agent_job

    # Mock database query
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=job)
    session.execute = AsyncMock(return_value=result)

    # Mock httpx client to raise exception
    with patch("httpx.AsyncClient") as mock_httpx:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("HTTP bridge connection lost"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_httpx.return_value = mock_client

        # Action: Call acknowledge_job (should handle HTTP bridge error gracefully)
        response = await orchestration_service.acknowledge_job(
            job_id=job.job_id,
            agent_id="test-agent-id",
            tenant_key="tenant-test-123"
        )

        # Assert: Database update still succeeded despite HTTP bridge failure
        assert response["status"] == "success"
        assert job.status == "working"

        # Verify HTTP bridge was attempted
        mock_client.post.assert_called_once()
