"""
Handover 0379e: SaaS Broker (Pub/Sub) + Loopback Elimination

These tests enforce that OrchestrationService emits WebSocket events via the
in-process WebSocketManager (no HTTP loopback to /api/v1/ws-bridge/emit).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.giljo_mcp.services.orchestration_service import OrchestrationService


pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_db_manager():
    db_manager = MagicMock()
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    db_manager.get_session_async = MagicMock(return_value=session)
    return db_manager, session


@pytest.fixture
def mock_tenant_manager():
    tenant_manager = MagicMock()
    tenant_manager.get_current_tenant = MagicMock(return_value="tenant-test-123")
    return tenant_manager


@pytest.fixture
def mock_websocket_manager():
    return AsyncMock()


@pytest.fixture
def orchestration_service(mock_db_manager, mock_tenant_manager, mock_websocket_manager):
    db_manager, _ = mock_db_manager
    return OrchestrationService(
        db_manager=db_manager,
        tenant_manager=mock_tenant_manager,
        websocket_manager=mock_websocket_manager,
    )


def _scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=value)
    return result


def _rows_result(rows):
    result = MagicMock()
    result.all = MagicMock(return_value=rows)
    return result


async def test_get_agent_mission_emits_ack_and_status_changed(
    orchestration_service,
    mock_db_manager,
    mock_websocket_manager,
):
    db_manager, session = mock_db_manager
    tenant_key = "tenant-test-123"
    project_id = str(uuid4())
    job_id = str(uuid4())
    agent_id = str(uuid4())

    job = SimpleNamespace(job_id=job_id, tenant_key=tenant_key, project_id=project_id, mission="Do work", created_at=datetime.now(timezone.utc))
    execution = SimpleNamespace(
        agent_id=agent_id,
        job_id=job_id,
        tenant_key=tenant_key,
        agent_display_name="implementer",
        agent_name="impl-worker-1",
        spawned_by=None,
        status="waiting",
        mission_acknowledged_at=None,
        started_at=None,
    )
    project = SimpleNamespace(
        id=project_id,
        tenant_key=tenant_key,
        implementation_launched_at=datetime.now(timezone.utc),
    )

    session.execute.side_effect = [
        _scalar_result(job),
        _scalar_result(execution),
        _scalar_result(project),
        _rows_result([(execution, job)]),
    ]

    response = await orchestration_service.get_agent_mission(job_id=job_id, tenant_key=tenant_key)

    # No success wrapper after 0730b refactor
    assert execution.mission_acknowledged_at is not None
    assert execution.status == "working"
    assert execution.started_at is not None

    event_types = [c.kwargs["event_type"] for c in mock_websocket_manager.broadcast_to_tenant.await_args_list]
    assert "job:mission_acknowledged" in event_types
    assert "agent:status_changed" in event_types


async def test_get_agent_mission_is_idempotent_and_does_not_re_emit(
    orchestration_service,
    mock_db_manager,
    mock_websocket_manager,
):
    db_manager, session = mock_db_manager
    tenant_key = "tenant-test-123"
    project_id = str(uuid4())
    job_id = str(uuid4())
    agent_id = str(uuid4())

    job = SimpleNamespace(job_id=job_id, tenant_key=tenant_key, project_id=project_id, mission="Do work", created_at=datetime.now(timezone.utc))
    execution = SimpleNamespace(
        agent_id=agent_id,
        job_id=job_id,
        tenant_key=tenant_key,
        agent_display_name="implementer",
        agent_name="impl-worker-1",
        spawned_by=None,
        status="working",
        mission_acknowledged_at=datetime.now(timezone.utc),
        started_at=datetime.now(timezone.utc),
    )
    project = SimpleNamespace(
        id=project_id,
        tenant_key=tenant_key,
        implementation_launched_at=datetime.now(timezone.utc),
    )

    session.execute.side_effect = [
        _scalar_result(job),
        _scalar_result(execution),
        _scalar_result(project),
        _rows_result([(execution, job)]),
    ]

    response = await orchestration_service.get_agent_mission(job_id=job_id, tenant_key=tenant_key)

    # No success wrapper after 0730b refactor
    mock_websocket_manager.broadcast_to_tenant.assert_not_awaited()


async def test_acknowledge_job_emits_status_changed(
    orchestration_service,
    mock_db_manager,
    mock_websocket_manager,
):
    db_manager, session = mock_db_manager
    tenant_key = "tenant-test-123"
    job_id = str(uuid4())
    project_id = str(uuid4())

    execution = SimpleNamespace(
        agent_id=str(uuid4()),
        job_id=job_id,
        tenant_key=tenant_key,
        agent_display_name="implementer",
        agent_name="impl-worker-42",
        status="waiting",
        started_at=None,
        mission_acknowledged_at=None,
    )
    job = SimpleNamespace(job_id=job_id, tenant_key=tenant_key, project_id=project_id, mission="Do work")
    project = SimpleNamespace(
        id=project_id,
        tenant_key=tenant_key,
        implementation_launched_at=datetime.now(timezone.utc),
    )

    session.execute.side_effect = [
        _scalar_result(execution),
        _scalar_result(job),
        _scalar_result(project),
    ]

    result = await orchestration_service.acknowledge_job(job_id=job_id, agent_id="ignored", tenant_key=tenant_key)

    # Handover 0731c: Returns AcknowledgeJobResult typed model
    assert result.job
    assert result.next_instructions
    assert execution.status == "working"
    mock_websocket_manager.broadcast_to_tenant.assert_awaited()

    last_call = mock_websocket_manager.broadcast_to_tenant.await_args_list[-1].kwargs
    assert last_call["tenant_key"] == tenant_key
    assert last_call["event_type"] == "agent:status_changed"
    assert last_call["data"]["agent_name"] == "impl-worker-42"


async def test_complete_job_emits_status_changed_with_duration_seconds(
    orchestration_service,
    mock_db_manager,
    mock_websocket_manager,
):
    db_manager, session = mock_db_manager
    tenant_key = "tenant-test-123"
    job_id = str(uuid4())

    started_at = datetime.now(timezone.utc) - timedelta(seconds=60)
    execution = SimpleNamespace(
        agent_id=str(uuid4()),
        job_id=job_id,
        tenant_key=tenant_key,
        agent_display_name="implementer",
        agent_name="impl-worker-1",
        status="working",
        started_at=started_at,
        completed_at=None,
        progress=0,
    )
    job = SimpleNamespace(
        job_id=job_id, tenant_key=tenant_key, project_id=str(uuid4()), status="active", completed_at=None
    )

    # complete_job makes 5 execute calls: execution, job, unread messages, todo items, other active executions
    # unread messages, todo items, and other active use .scalars().all() not .scalar_one_or_none()
    unread_result = MagicMock()
    unread_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))

    todo_result = MagicMock()
    todo_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))

    other_active_result = MagicMock()
    other_active_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))

    session.execute.side_effect = [
        _scalar_result(execution),
        _scalar_result(job),
        unread_result,  # unread messages (empty list)
        todo_result,  # todo items (empty list)
        other_active_result,  # other active executions (empty list)
    ]

    result = await orchestration_service.complete_job(job_id=job_id, result={"ok": True}, tenant_key=tenant_key)

    # Handover 0731c: Returns CompleteJobResult typed model
    assert result.status == "success"
    assert execution.status == "complete"

    last_call = mock_websocket_manager.broadcast_to_tenant.await_args_list[-1].kwargs
    assert last_call["event_type"] == "agent:status_changed"
    assert last_call["data"]["status"] == "complete"
    assert 59 <= last_call["data"]["duration_seconds"] <= 61


async def test_report_progress_fallback_emits_message_new_event(
    orchestration_service,
    mock_db_manager,
    mock_websocket_manager,
    monkeypatch,
):
    db_manager, session = mock_db_manager
    tenant_key = "tenant-test-123"
    job_id = str(uuid4())

    execution = SimpleNamespace(
        agent_id=str(uuid4()),
        job_id=job_id,
        tenant_key=tenant_key,
        agent_display_name="implementer",
        agent_name="impl-worker-1",
        status="working",
        started_at=datetime.now(timezone.utc),
        mission_acknowledged_at=datetime.now(timezone.utc),
    )
    job = SimpleNamespace(
        job_id=job_id,
        tenant_key=tenant_key,
        project_id=str(uuid4()),
        job_metadata={},  # Required for websocket broadcast
    )

    # report_progress uses 2 session contexts with 3 total execute calls:
    # Session 1: execution, job (both scalar_one_or_none)
    # Session 2: todo_items (scalars().all())
    todo_items_result = MagicMock()
    todo_items_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))

    session.execute.side_effect = [
        _scalar_result(execution),
        _scalar_result(job),
        todo_items_result,  # todo_items query (empty list)
    ]

    # Force fallback path by ensuring MessageService is unavailable
    orchestration_service._message_service = None

    result = await orchestration_service.report_progress(
        job_id=job_id,
        progress={"percent": 50, "message": "Half done"},
        tenant_key=tenant_key,
    )

    # Handover 0731c: Returns ProgressResult typed model
    assert result.status == "success"
    mock_websocket_manager.broadcast_to_tenant.assert_awaited()

    # report_progress emits job:progress_update event (not message:new)
    last_call = mock_websocket_manager.broadcast_to_tenant.await_args_list[-1].kwargs
    assert last_call["tenant_key"] == tenant_key
    assert last_call["event_type"] == "job:progress_update"


async def test_websocket_failures_do_not_break_orchestration_calls(
    orchestration_service,
    mock_db_manager,
    mock_websocket_manager,
):
    db_manager, session = mock_db_manager
    tenant_key = "tenant-test-123"
    job_id = str(uuid4())
    project_id = str(uuid4())

    execution = SimpleNamespace(
        agent_id=str(uuid4()),
        job_id=job_id,
        tenant_key=tenant_key,
        agent_display_name="implementer",
        agent_name="impl-worker-42",
        status="waiting",
        started_at=None,
        mission_acknowledged_at=None,
    )
    job = SimpleNamespace(job_id=job_id, tenant_key=tenant_key, project_id=project_id, mission="Do work")
    project = SimpleNamespace(
        id=project_id,
        tenant_key=tenant_key,
        implementation_launched_at=datetime.now(timezone.utc),
    )

    session.execute.side_effect = [
        _scalar_result(execution),
        _scalar_result(job),
        _scalar_result(project),
    ]

    mock_websocket_manager.broadcast_to_tenant.side_effect = Exception("WebSocket down")

    result = await orchestration_service.acknowledge_job(job_id=job_id, agent_id="ignored", tenant_key=tenant_key)

    # Handover 0731c: Returns AcknowledgeJobResult typed model
    assert result.job
    assert result.next_instructions
    assert execution.status == "working"
