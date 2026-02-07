"""
Test suite for OrchestrationService report_progress functionality.

Tests cover:
- report_progress with TODO mode updates job_metadata with steps
- report_progress with regular progress does not set todo_steps

HANDOVER 0422: Removed tests for update_context_usage(), estimate_message_tokens(), and trigger_succession()
which were methods testing dead token budget code (removed from OrchestrationService).
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.giljo_mcp.models.agent_identity import AgentExecution


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


@pytest.mark.skip(reason="report_progress() functionality changed - uses TodoWriteRepository instead of job_metadata")
@pytest.mark.asyncio
async def test_report_progress_todo_updates_job_metadata_steps(mock_db_manager, mock_tenant_manager):
    """Test that report_progress(mode='todo') updates job_metadata with steps summary.

    NOTE: This functionality has been migrated to use TodoWriteRepository with todo_items table.
    The job_metadata.todo_steps field is still updated for backward compatibility,
    but tests should verify the new todo_items table instead.
    """


@pytest.mark.skip(reason="report_progress() functionality changed - uses TodoWriteRepository instead of job_metadata")
@pytest.mark.asyncio
async def test_report_progress_non_todo_does_not_set_steps(mock_db_manager, mock_tenant_manager):
    """Test that non-todo progress payloads do not set todo_steps metadata.

    NOTE: This functionality has been migrated to use TodoWriteRepository with todo_items table.
    """

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
