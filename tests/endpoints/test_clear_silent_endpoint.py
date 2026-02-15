"""
Tests for the clear-silent REST endpoint (Handover 0491 Phase 3).

Tests the POST /api/agent-jobs/{agent_id}/clear-silent endpoint.
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob


@pytest_asyncio.fixture
async def silent_agent_for_endpoint(db_session: AsyncSession):
    """Create a silent agent for endpoint testing."""
    tenant_key = f"test_tenant_{uuid.uuid4().hex[:8]}"
    job_id = str(uuid.uuid4())
    agent_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())

    from src.giljo_mcp.models import Project

    project = Project(
        id=project_id,
        name="Test Project Silent Endpoint",
        description="test",
        mission="test",
        status="active",
        tenant_key=tenant_key,
    )
    db_session.add(project)

    job = AgentJob(
        job_id=job_id,
        tenant_key=tenant_key,
        project_id=project_id,
        job_type="worker",
        mission="Test mission for endpoint",
        status="active",
    )
    db_session.add(job)

    execution = AgentExecution(
        agent_id=agent_id,
        job_id=job_id,
        tenant_key=tenant_key,
        agent_display_name="endpoint-test-worker",
        agent_name="Endpoint Test Worker",
        status="silent",
        progress=40,
        last_progress_at=datetime.now(timezone.utc) - timedelta(minutes=20),
        health_status="unknown",
        tool_type="universal",
    )
    db_session.add(execution)
    await db_session.commit()
    await db_session.refresh(execution)

    return execution, tenant_key


class TestClearSilentEndpoint:
    """Test the clear-silent endpoint logic directly."""

    @pytest.mark.asyncio
    async def test_clear_silent_sets_working(self, db_session, silent_agent_for_endpoint):
        """Clearing a silent agent should set status to working."""
        from src.giljo_mcp.services.silence_detector import clear_silent_status

        execution, tenant_key = silent_agent_for_endpoint
        ws_mock = AsyncMock()

        result = await clear_silent_status(
            session=db_session,
            agent_id=str(execution.agent_id),
            tenant_key=tenant_key,
            ws_manager=ws_mock,
        )

        assert result is not None
        assert result["status"] == "working"
        assert result["agent_id"] == str(execution.agent_id)

        await db_session.refresh(execution)
        assert execution.status == "working"

    @pytest.mark.asyncio
    async def test_clear_silent_updates_progress_timestamp(self, db_session, silent_agent_for_endpoint):
        """Clearing should update last_progress_at to current time."""
        from src.giljo_mcp.services.silence_detector import clear_silent_status

        execution, tenant_key = silent_agent_for_endpoint
        old_progress = execution.last_progress_at
        ws_mock = AsyncMock()

        await clear_silent_status(
            session=db_session,
            agent_id=str(execution.agent_id),
            tenant_key=tenant_key,
            ws_manager=ws_mock,
        )

        await db_session.refresh(execution)
        assert execution.last_progress_at > old_progress

    @pytest.mark.asyncio
    async def test_clear_silent_emits_websocket(self, db_session, silent_agent_for_endpoint):
        """Clearing should emit a WebSocket status_changed event."""
        from src.giljo_mcp.services.silence_detector import clear_silent_status

        execution, tenant_key = silent_agent_for_endpoint
        ws_mock = AsyncMock()

        await clear_silent_status(
            session=db_session,
            agent_id=str(execution.agent_id),
            tenant_key=tenant_key,
            ws_manager=ws_mock,
        )

        ws_mock.broadcast_event_to_tenant.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_silent_rejects_non_silent_agent(self, db_session):
        """Clearing a non-silent agent should return None (not found for clearing)."""
        from src.giljo_mcp.services.silence_detector import clear_silent_status

        tenant_key = f"test_tenant_{uuid.uuid4().hex[:8]}"
        job_id = str(uuid.uuid4())
        agent_id = str(uuid.uuid4())
        project_id = str(uuid.uuid4())

        from src.giljo_mcp.models import Project

        project = Project(
            id=project_id,
            name="Non-Silent Project",
            description="test",
            mission="test",
            status="active",
            tenant_key=tenant_key,
        )
        db_session.add(project)

        job = AgentJob(
            job_id=job_id,
            tenant_key=tenant_key,
            project_id=project_id,
            job_type="worker",
            mission="Non-silent mission",
            status="active",
        )
        db_session.add(job)

        execution = AgentExecution(
            agent_id=agent_id,
            job_id=job_id,
            tenant_key=tenant_key,
            agent_display_name="non-silent-worker",
            agent_name="Non-Silent Worker",
            status="working",
            progress=50,
            last_progress_at=datetime.now(timezone.utc),
            health_status="unknown",
            tool_type="universal",
        )
        db_session.add(execution)
        await db_session.commit()

        ws_mock = AsyncMock()

        result = await clear_silent_status(
            session=db_session,
            agent_id=str(agent_id),
            tenant_key=tenant_key,
            ws_manager=ws_mock,
        )

        assert result is None
        ws_mock.broadcast_event_to_tenant.assert_not_called()

    @pytest.mark.asyncio
    async def test_clear_silent_nonexistent_agent(self, db_session):
        """Clearing a nonexistent agent should return None."""
        from src.giljo_mcp.services.silence_detector import clear_silent_status

        ws_mock = AsyncMock()

        result = await clear_silent_status(
            session=db_session,
            agent_id=str(uuid.uuid4()),
            tenant_key="nonexistent_tenant",
            ws_manager=ws_mock,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_clear_silent_respects_tenant_isolation(self, db_session, silent_agent_for_endpoint):
        """Clearing with wrong tenant_key should fail (tenant isolation)."""
        from src.giljo_mcp.services.silence_detector import clear_silent_status

        execution, tenant_key = silent_agent_for_endpoint
        ws_mock = AsyncMock()

        result = await clear_silent_status(
            session=db_session,
            agent_id=str(execution.agent_id),
            tenant_key="wrong_tenant_key",
            ws_manager=ws_mock,
        )

        assert result is None

        # Agent should still be silent
        await db_session.refresh(execution)
        assert execution.status == "silent"
