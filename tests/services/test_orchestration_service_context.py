"""
Test suite for OrchestrationService report_progress functionality.

Tests cover:
- report_progress with TODO mode updates job_metadata with steps
- report_progress with regular progress does not set todo_steps

HANDOVER 0422: Removed tests for update_context_usage(), estimate_message_tokens(), and trigger_succession()
which were methods testing dead token budget code (removed from OrchestrationService).
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.giljo_mcp.services.orchestration_service import OrchestrationService
from src.giljo_mcp.models.agent_identity import AgentExecution
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
    return tenant_manager


@pytest.mark.asyncio
async def test_report_progress_todo_updates_job_metadata_steps(mock_db_manager, mock_tenant_manager):
    """Test that report_progress(mode='todo') updates job_metadata with steps summary."""
    db_manager, session = mock_db_manager
    tenant_manager = mock_tenant_manager
    tenant_manager.get_current_tenant.return_value = "tenant-test-steps"

    service = OrchestrationService(db_manager=db_manager, tenant_manager=tenant_manager)

    # Stub MessageService to avoid hitting real queue/WebSocket
    mock_message_service = MagicMock()
    mock_message_service.send_message = AsyncMock(return_value={"success": True, "message_id": "msg-steps-001"})
    service._message_service = mock_message_service

    job = AgentExecution(
        job_id=str(uuid4()),
        tenant_key="tenant-test-steps",
        project_id=str(uuid4()),
        agent_display_name="implementer",
        agent_name="impl-steps-1",
        mission="Test mission for TODO steps",
        status="working",
        job_metadata={},
    )

    # Mock database lookup for job
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=job)
    session.execute = AsyncMock(return_value=result)

    progress_payload = {
        "mode": "todo",
        "total_steps": 5,
        "completed_steps": 2,
        "current_step": "Writing tests for TODO steps",
    }

    response = await service.report_progress(
        job_id=job.job_id,
        progress=progress_payload,
        tenant_key="tenant-test-steps",
    )

    # Service call should succeed
    assert response["status"] == "success"

    # MessageService should be used
    mock_message_service.send_message.assert_awaited_once()

    # job_metadata should contain normalized TODO steps summary
    assert isinstance(job.job_metadata, dict)
    assert "todo_steps" in job.job_metadata
    steps = job.job_metadata["todo_steps"]
    assert steps["total_steps"] == 5
    assert steps["completed_steps"] == 2
    assert steps["current_step"] == "Writing tests for TODO steps"


@pytest.mark.asyncio
async def test_report_progress_non_todo_does_not_set_steps(mock_db_manager, mock_tenant_manager):
    """Test that non-todo progress payloads do not set todo_steps metadata."""
    db_manager, session = mock_db_manager
    tenant_manager = mock_tenant_manager
    tenant_manager.get_current_tenant.return_value = "tenant-test-steps"

    service = OrchestrationService(db_manager=db_manager, tenant_manager=tenant_manager)

    mock_message_service = MagicMock()
    mock_message_service.send_message = AsyncMock(return_value={"success": True, "message_id": "msg-progress-001"})
    service._message_service = mock_message_service

    job = AgentExecution(
        job_id=str(uuid4()),
        tenant_key="tenant-test-steps",
        project_id=str(uuid4()),
        agent_display_name="implementer",
        agent_name="impl-progress-1",
        mission="Test mission for regular progress",
        status="working",
        job_metadata={},
    )

    # Mock database lookup
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=job)
    session.execute = AsyncMock(return_value=result)

    progress_payload = {
        "percent": 50,
        "message": "Half done",
    }

    response = await service.report_progress(
        job_id=job.job_id,
        progress=progress_payload,
        tenant_key="tenant-test-steps",
    )

    assert response["status"] == "success"
    mock_message_service.send_message.assert_awaited_once()

    # No todo_steps summary should be set for non-todo progress
    assert isinstance(job.job_metadata, dict)
    assert "todo_steps" not in job.job_metadata
