"""
Tests for blocked->working status transition in report_progress().

When an agent calls report_progress() while in "blocked" status, the execution
should transition to "working" and broadcast a status change event. This mirrors
the silent->working auto-recovery pattern used elsewhere in the orchestration service.

Covers:
- Blocked -> working transition with block_reason cleared
- WebSocket broadcast on blocked -> working transition
- No status change when already "working"
- No status change when "waiting"
- No status change when "silent" (handled by auto_clear_silent, not report_progress)
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.giljo_mcp.services.orchestration_service import OrchestrationService


def _make_mock_execution(
    *,
    agent_id="agent-001",
    job_id="job-001",
    tenant_key="test-tenant",
    status="working",
    block_reason=None,
    agent_display_name="Test Agent",
):
    """Create a mock AgentExecution with the given status."""
    execution = Mock()
    execution.agent_id = agent_id
    execution.job_id = job_id
    execution.tenant_key = tenant_key
    execution.status = status
    execution.block_reason = block_reason
    execution.last_progress_at = None
    execution.progress = 0
    execution.current_task = None
    execution.started_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    execution.agent_display_name = agent_display_name
    return execution


def _make_mock_job(*, job_id="job-001", project_id="proj-001", tenant_key="test-tenant"):
    """Create a mock AgentJob."""
    job = Mock()
    job.job_id = job_id
    job.project_id = project_id
    job.tenant_key = tenant_key
    job.job_metadata = {}
    return job


def _build_service(db_manager, mock_tenant_manager, mock_ws=None):
    """Build OrchestrationService with mocked dependencies."""
    return OrchestrationService(
        db_manager=db_manager,
        tenant_manager=mock_tenant_manager,
        websocket_manager=mock_ws,
    )


def _setup_session_mocks(session, execution, job):
    """Configure session.execute to return execution and job for the two queries."""
    exec_result = Mock()
    exec_result.scalar_one_or_none = Mock(return_value=execution)
    job_result = Mock()
    job_result.scalar_one_or_none = Mock(return_value=job)
    session.execute = AsyncMock(side_effect=[exec_result, job_result])


@pytest.mark.asyncio
async def test_report_progress_transitions_blocked_to_working(mock_db_manager, mock_tenant_manager):
    """When execution status is 'blocked', report_progress sets it to 'working' and clears block_reason."""
    db_manager, session = mock_db_manager
    mock_ws = Mock()
    mock_ws.broadcast_event_to_tenant = AsyncMock()

    execution = _make_mock_execution(status="blocked", block_reason="Waiting for user input")
    job = _make_mock_job()
    _setup_session_mocks(session, execution, job)

    service = _build_service(db_manager, mock_tenant_manager, mock_ws)

    with patch.object(service, "_fetch_and_broadcast_progress", new_callable=AsyncMock):
        result = await service.report_progress(
            job_id="job-001",
            tenant_key="test-tenant",
            progress={"percent": 50, "message": "Working on task"},
        )

    assert result.status == "success"
    assert execution.status == "working"
    assert execution.block_reason is None


@pytest.mark.asyncio
async def test_report_progress_broadcasts_status_change_on_blocked_to_working(
    mock_db_manager, mock_tenant_manager
):
    """When transitioning blocked->working, broadcast agent:status_changed event."""
    db_manager, session = mock_db_manager
    mock_ws = Mock()
    mock_ws.broadcast_event_to_tenant = AsyncMock()

    execution = _make_mock_execution(status="blocked", block_reason="Need clarification")
    job = _make_mock_job()
    _setup_session_mocks(session, execution, job)

    service = _build_service(db_manager, mock_tenant_manager, mock_ws)

    with patch.object(service, "_fetch_and_broadcast_progress", new_callable=AsyncMock):
        await service.report_progress(
            job_id="job-001",
            tenant_key="test-tenant",
            progress={"percent": 25, "message": "Resumed work"},
        )

    # Verify WebSocket broadcast was called
    mock_ws.broadcast_event_to_tenant.assert_called_once()
    call_kwargs = mock_ws.broadcast_event_to_tenant.call_args
    assert call_kwargs.kwargs["tenant_key"] == "test-tenant"
    event = call_kwargs.kwargs["event"]
    assert event["type"] == "agent:status_changed"
    assert event["data"]["old_status"] == "blocked"
    assert event["data"]["new_status"] == "working"
    assert event["data"]["agent_display_name"] == "Test Agent"


@pytest.mark.asyncio
async def test_report_progress_does_not_change_working_status(mock_db_manager, mock_tenant_manager):
    """When execution is already 'working', report_progress does not change status."""
    db_manager, session = mock_db_manager
    mock_ws = Mock()
    mock_ws.broadcast_event_to_tenant = AsyncMock()

    execution = _make_mock_execution(status="working")
    job = _make_mock_job()
    _setup_session_mocks(session, execution, job)

    service = _build_service(db_manager, mock_tenant_manager, mock_ws)

    with patch.object(service, "_fetch_and_broadcast_progress", new_callable=AsyncMock):
        result = await service.report_progress(
            job_id="job-001",
            tenant_key="test-tenant",
            progress={"percent": 50, "message": "In progress"},
        )

    assert result.status == "success"
    assert execution.status == "working"
    # No WebSocket broadcast for status change (status did not change)
    mock_ws.broadcast_event_to_tenant.assert_not_called()


@pytest.mark.asyncio
async def test_report_progress_does_not_change_waiting_status(mock_db_manager, mock_tenant_manager):
    """When execution is 'waiting', report_progress does not change status."""
    db_manager, session = mock_db_manager
    mock_ws = Mock()
    mock_ws.broadcast_event_to_tenant = AsyncMock()

    execution = _make_mock_execution(status="waiting")
    job = _make_mock_job()
    _setup_session_mocks(session, execution, job)

    service = _build_service(db_manager, mock_tenant_manager, mock_ws)

    with patch.object(service, "_fetch_and_broadcast_progress", new_callable=AsyncMock):
        result = await service.report_progress(
            job_id="job-001",
            tenant_key="test-tenant",
            progress={"percent": 10, "message": "Starting"},
        )

    assert result.status == "success"
    assert execution.status == "waiting"
    mock_ws.broadcast_event_to_tenant.assert_not_called()


@pytest.mark.asyncio
async def test_report_progress_does_not_change_silent_status(mock_db_manager, mock_tenant_manager):
    """When execution is 'silent', report_progress does not change status (auto_clear_silent handles that)."""
    db_manager, session = mock_db_manager
    mock_ws = Mock()
    mock_ws.broadcast_event_to_tenant = AsyncMock()

    execution = _make_mock_execution(status="silent")
    job = _make_mock_job()
    _setup_session_mocks(session, execution, job)

    service = _build_service(db_manager, mock_tenant_manager, mock_ws)

    with patch.object(service, "_fetch_and_broadcast_progress", new_callable=AsyncMock):
        result = await service.report_progress(
            job_id="job-001",
            tenant_key="test-tenant",
            progress={"percent": 30, "message": "Working silently"},
        )

    assert result.status == "success"
    assert execution.status == "silent"
    mock_ws.broadcast_event_to_tenant.assert_not_called()
