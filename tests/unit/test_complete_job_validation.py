from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from src.giljo_mcp.models import AgentExecution, AgentJob, AgentTodoItem, Message
from src.giljo_mcp.services import orchestration_service
from src.giljo_mcp.services.orchestration_service import OrchestrationService


def _scalar_result(value):
    result = Mock()
    result.scalar_one_or_none = Mock(return_value=value)
    return result


def _scalars_result(values):
    result = Mock()
    result.scalars = Mock(return_value=Mock(all=Mock(return_value=values)))
    return result


@pytest.mark.asyncio
async def test_complete_job_rejects_with_unread_messages(mock_db_manager):
    db_manager, session = mock_db_manager
    tenant_manager = Mock()
    tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

    execution = Mock(spec=AgentExecution)
    execution.job_id = "job-123"
    execution.status = "working"
    execution.agent_id = "agent-456"
    execution.agent_display_name = "implementer"
    execution.agent_name = "implementer"

    job = Mock(spec=AgentJob)
    job.job_id = "job-123"
    job.project_id = "project-1"
    job.status = "active"
    job.completed_at = None

    msg1 = Mock(spec=Message)
    msg1.id = "msg-1"
    msg1.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)

    msg2 = Mock(spec=Message)
    msg2.id = "msg-2"
    msg2.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)

    session.execute.side_effect = [
        _scalar_result(execution),
        _scalar_result(job),
        _scalars_result([msg1, msg2]),
        _scalars_result([]),
    ]

    service = OrchestrationService(db_manager, tenant_manager)

    result = await service.complete_job(
        job_id="job-123",
        result={"summary": "done"},
    )

    assert result["status"] == "error"
    assert result["error"] == "COMPLETION_BLOCKED"
    assert any("unread messages" in reason.lower() for reason in result["reasons"])
    assert "msg-1" in " ".join(result["reasons"])
    session.commit.assert_not_awaited()
    assert execution.status == "working"


@pytest.mark.asyncio
async def test_complete_job_rejects_with_incomplete_todos(mock_db_manager):
    db_manager, session = mock_db_manager
    tenant_manager = Mock()
    tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

    execution = Mock(spec=AgentExecution)
    execution.job_id = "job-123"
    execution.status = "working"
    execution.agent_id = "agent-456"
    execution.agent_display_name = "implementer"
    execution.agent_name = "implementer"

    job = Mock(spec=AgentJob)
    job.job_id = "job-123"
    job.project_id = "project-1"
    job.status = "active"
    job.completed_at = None

    todo = Mock(spec=AgentTodoItem)
    todo.content = "Finish validation"
    todo.status = "pending"

    session.execute.side_effect = [
        _scalar_result(execution),
        _scalar_result(job),
        _scalars_result([]),
        _scalars_result([todo]),
    ]

    service = OrchestrationService(db_manager, tenant_manager)

    result = await service.complete_job(
        job_id="job-123",
        result={"summary": "done"},
    )

    assert result["status"] == "error"
    assert result["error"] == "COMPLETION_BLOCKED"
    assert any("todo items" in reason.lower() for reason in result["reasons"])
    assert "Finish validation" in " ".join(result["reasons"])
    session.commit.assert_not_awaited()
    assert execution.status == "working"


@pytest.mark.asyncio
async def test_complete_job_succeeds_when_all_complete(mock_db_manager):
    db_manager, session = mock_db_manager
    tenant_manager = Mock()
    tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

    execution = Mock(spec=AgentExecution)
    execution.job_id = "job-123"
    execution.status = "working"
    execution.agent_id = "agent-456"
    execution.agent_display_name = "implementer"
    execution.agent_name = "implementer"
    execution.completed_at = None
    execution.started_at = None

    job = Mock(spec=AgentJob)
    job.job_id = "job-123"
    job.project_id = "project-1"
    job.status = "active"
    job.completed_at = None

    session.execute.side_effect = [
        _scalar_result(execution),
        _scalar_result(job),
        _scalars_result([]),
        _scalars_result([]),
        _scalar_result(None),
    ]

    service = OrchestrationService(db_manager, tenant_manager)

    result = await service.complete_job(
        job_id="job-123",
        result={"summary": "done"},
    )

    assert result["status"] == "success"
    assert execution.status == "complete"
    assert job.status == "completed"
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_complete_job_ignores_messages_after_attempt(mock_db_manager, monkeypatch):
    db_manager, session = mock_db_manager
    tenant_manager = Mock()
    tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

    fixed_now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now

    monkeypatch.setattr(orchestration_service, "datetime", FixedDateTime)

    execution = Mock(spec=AgentExecution)
    execution.job_id = "job-123"
    execution.status = "working"
    execution.agent_id = "agent-456"
    execution.agent_display_name = "implementer"
    execution.agent_name = "implementer"
    execution.completed_at = None
    execution.started_at = None

    job = Mock(spec=AgentJob)
    job.job_id = "job-123"
    job.project_id = "project-1"
    job.status = "active"
    job.completed_at = None

    msg = Mock(spec=Message)
    msg.id = "msg-future"
    msg.created_at = fixed_now + timedelta(seconds=5)

    session.execute.side_effect = [
        _scalar_result(execution),
        _scalar_result(job),
        _scalars_result([msg]),
        _scalars_result([]),
        _scalar_result(None),
    ]

    service = OrchestrationService(db_manager, tenant_manager)

    result = await service.complete_job(
        job_id="job-123",
        result={"summary": "done"},
    )

    assert result["status"] == "success"
    assert execution.status == "complete"


@pytest.mark.asyncio
async def test_report_error_sets_blocked_not_failed(mock_db_manager):
    db_manager, session = mock_db_manager
    tenant_manager = Mock()
    tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

    execution = Mock(spec=AgentExecution)
    execution.job_id = "job-123"
    execution.status = "working"
    execution.block_reason = None

    session.execute.return_value = _scalar_result(execution)

    service = OrchestrationService(db_manager, tenant_manager)

    # Handover 0491: severity param removed, always sets blocked
    result = await service.report_error(
        job_id="job-123",
        error="Need input from user",
    )

    assert result["job_id"] == "job-123"
    assert result["message"] == "Error reported"
    assert execution.status == "blocked"
    assert execution.block_reason == "Need input from user"
