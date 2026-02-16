"""
Tests for SilenceDetector background service (Handover 0491 Phase 3).

Tests cover:
- Detection of agents past silence threshold
- Configurable threshold from settings
- NULL last_progress_at handling (treat as silent)
- Auto-clear silent status on MCP call
- Clear-silent REST endpoint
- Full lifecycle integration: working -> silent -> MCP call -> working -> complete
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def working_agent_with_recent_progress(db_session: AsyncSession):
    """Create a working agent with recent progress (should NOT be marked silent)."""
    tenant_key = f"test_tenant_{uuid.uuid4().hex[:8]}"
    job_id = str(uuid.uuid4())
    agent_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())

    # Create project
    from src.giljo_mcp.models import Project

    project = Project(
        id=project_id,
        name="Test Project",
        description="test",
        mission="test",
        status="active",
        tenant_key=tenant_key,
    )
    db_session.add(project)

    # Create job
    job = AgentJob(
        job_id=job_id,
        tenant_key=tenant_key,
        project_id=project_id,
        job_type="worker",
        mission="Test mission",
        status="active",
    )
    db_session.add(job)

    # Create execution with recent progress
    execution = AgentExecution(
        agent_id=agent_id,
        job_id=job_id,
        tenant_key=tenant_key,
        agent_display_name="worker",
        agent_name="Test Worker",
        status="working",
        progress=50,
        last_progress_at=datetime.now(timezone.utc) - timedelta(minutes=2),
        health_status="unknown",
        tool_type="universal",
    )
    db_session.add(execution)
    await db_session.commit()
    await db_session.refresh(execution)

    return execution, tenant_key


@pytest_asyncio.fixture
async def stale_working_agent(db_session: AsyncSession):
    """Create a working agent with stale progress (should be marked silent)."""
    tenant_key = f"test_tenant_{uuid.uuid4().hex[:8]}"
    job_id = str(uuid.uuid4())
    agent_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())

    from src.giljo_mcp.models import Project

    project = Project(
        id=project_id,
        name="Test Project Stale",
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
        mission="Test mission stale",
        status="active",
    )
    db_session.add(job)

    execution = AgentExecution(
        agent_id=agent_id,
        job_id=job_id,
        tenant_key=tenant_key,
        agent_display_name="stale-worker",
        agent_name="Stale Worker",
        status="working",
        progress=30,
        last_progress_at=datetime.now(timezone.utc) - timedelta(minutes=20),
        health_status="unknown",
        tool_type="universal",
    )
    db_session.add(execution)
    await db_session.commit()
    await db_session.refresh(execution)

    return execution, tenant_key


@pytest_asyncio.fixture
async def null_progress_working_agent(db_session: AsyncSession):
    """Create a working agent with NULL last_progress_at (should be marked silent)."""
    tenant_key = f"test_tenant_{uuid.uuid4().hex[:8]}"
    job_id = str(uuid.uuid4())
    agent_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())

    from src.giljo_mcp.models import Project

    project = Project(
        id=project_id,
        name="Test Project Null Progress",
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
        mission="Test mission null",
        status="active",
    )
    db_session.add(job)

    execution = AgentExecution(
        agent_id=agent_id,
        job_id=job_id,
        tenant_key=tenant_key,
        agent_display_name="null-progress-worker",
        agent_name="Null Progress Worker",
        status="working",
        progress=10,
        last_progress_at=None,
        health_status="unknown",
        tool_type="universal",
    )
    db_session.add(execution)
    await db_session.commit()
    await db_session.refresh(execution)

    return execution, tenant_key


@pytest_asyncio.fixture
async def silent_agent(db_session: AsyncSession):
    """Create an agent already in silent status (for clear-silent testing)."""
    tenant_key = f"test_tenant_{uuid.uuid4().hex[:8]}"
    job_id = str(uuid.uuid4())
    agent_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())

    from src.giljo_mcp.models import Project

    project = Project(
        id=project_id,
        name="Test Project Silent",
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
        mission="Test mission silent",
        status="active",
    )
    db_session.add(job)

    execution = AgentExecution(
        agent_id=agent_id,
        job_id=job_id,
        tenant_key=tenant_key,
        agent_display_name="silent-worker",
        agent_name="Silent Worker",
        status="silent",
        progress=40,
        last_progress_at=datetime.now(timezone.utc) - timedelta(minutes=25),
        health_status="unknown",
        tool_type="universal",
    )
    db_session.add(execution)
    await db_session.commit()
    await db_session.refresh(execution)

    return execution, tenant_key


# ---------------------------------------------------------------------------
# Unit Tests: SilenceDetector._detect_silent_agents
# ---------------------------------------------------------------------------


class TestSilenceDetectorDetection:
    """Test silence detection logic."""

    @pytest.mark.asyncio
    async def test_stale_agent_detected_as_silent(self, db_session, stale_working_agent):
        """Agent with last_progress_at older than threshold should be marked silent."""
        from src.giljo_mcp.services.silence_detector import SilenceDetector

        execution, tenant_key = stale_working_agent
        ws_mock = AsyncMock()

        detector = SilenceDetector(db_manager=MagicMock(), ws_manager=ws_mock)

        # Run detection with 10-minute threshold
        count = await detector._detect_silent_agents(db_session, threshold_minutes=10)

        assert count > 0

        # Verify the agent was marked silent
        await db_session.refresh(execution)
        assert execution.status == "silent"

    @pytest.mark.asyncio
    async def test_recent_agent_not_detected(self, db_session, working_agent_with_recent_progress):
        """Agent with recent progress should NOT be marked silent."""
        from src.giljo_mcp.services.silence_detector import SilenceDetector

        execution, tenant_key = working_agent_with_recent_progress
        ws_mock = AsyncMock()

        detector = SilenceDetector(db_manager=MagicMock(), ws_manager=ws_mock)

        count = await detector._detect_silent_agents(db_session, threshold_minutes=10)

        assert count == 0

        # Verify the agent is still working
        await db_session.refresh(execution)
        assert execution.status == "working"

    @pytest.mark.asyncio
    async def test_null_progress_treated_as_silent(self, db_session, null_progress_working_agent):
        """Agent with NULL last_progress_at and status=working should be marked silent."""
        from src.giljo_mcp.services.silence_detector import SilenceDetector

        execution, tenant_key = null_progress_working_agent
        ws_mock = AsyncMock()

        detector = SilenceDetector(db_manager=MagicMock(), ws_manager=ws_mock)

        count = await detector._detect_silent_agents(db_session, threshold_minutes=10)

        assert count > 0

        await db_session.refresh(execution)
        assert execution.status == "silent"

    @pytest.mark.asyncio
    async def test_websocket_event_emitted_on_detection(self, db_session, stale_working_agent):
        """WebSocket event should be emitted when agent is marked silent."""
        from src.giljo_mcp.services.silence_detector import SilenceDetector

        execution, tenant_key = stale_working_agent
        ws_mock = AsyncMock()

        detector = SilenceDetector(db_manager=MagicMock(), ws_manager=ws_mock)

        await detector._detect_silent_agents(db_session, threshold_minutes=10)

        # Verify WebSocket broadcast was called
        ws_mock.broadcast_event_to_tenant.assert_called()
        call_kwargs = ws_mock.broadcast_event_to_tenant.call_args
        assert call_kwargs.kwargs["tenant_key"] == tenant_key

    @pytest.mark.asyncio
    async def test_configurable_threshold(self, db_session, stale_working_agent):
        """Detection should respect the configurable threshold."""
        from src.giljo_mcp.services.silence_detector import SilenceDetector

        execution, tenant_key = stale_working_agent
        ws_mock = AsyncMock()

        detector = SilenceDetector(db_manager=MagicMock(), ws_manager=ws_mock)

        # With a 30-minute threshold, the 20-minute-stale agent should NOT be silent
        count = await detector._detect_silent_agents(db_session, threshold_minutes=30)

        assert count == 0

        await db_session.refresh(execution)
        assert execution.status == "working"

    @pytest.mark.asyncio
    async def test_non_working_agents_ignored(self, db_session, silent_agent):
        """Agents not in 'working' status should not be affected."""
        from src.giljo_mcp.services.silence_detector import SilenceDetector

        execution, tenant_key = silent_agent
        ws_mock = AsyncMock()

        detector = SilenceDetector(db_manager=MagicMock(), ws_manager=ws_mock)

        count = await detector._detect_silent_agents(db_session, threshold_minutes=10)

        # Already silent agent should not be re-detected
        assert count == 0


# ---------------------------------------------------------------------------
# Unit Tests: auto_clear_silent
# ---------------------------------------------------------------------------


class TestAutoClearSilent:
    """Test auto-clear silent status on MCP call."""

    @pytest.mark.asyncio
    async def test_auto_clear_resets_to_working(self, db_session, silent_agent):
        """Auto-clear should set silent agent back to working."""
        from src.giljo_mcp.services.silence_detector import auto_clear_silent

        execution, tenant_key = silent_agent
        ws_mock = AsyncMock()

        await auto_clear_silent(
            session=db_session,
            job_id=execution.job_id,
            ws_manager=ws_mock,
        )

        await db_session.refresh(execution)
        assert execution.status == "working"

    @pytest.mark.asyncio
    async def test_auto_clear_updates_last_progress_at(self, db_session, silent_agent):
        """Auto-clear should update last_progress_at to now."""
        from src.giljo_mcp.services.silence_detector import auto_clear_silent

        execution, tenant_key = silent_agent
        old_progress = execution.last_progress_at
        ws_mock = AsyncMock()

        await auto_clear_silent(
            session=db_session,
            job_id=execution.job_id,
            ws_manager=ws_mock,
        )

        await db_session.refresh(execution)
        assert execution.last_progress_at is not None
        assert execution.last_progress_at > old_progress

    @pytest.mark.asyncio
    async def test_auto_clear_emits_websocket_event(self, db_session, silent_agent):
        """Auto-clear should emit a WebSocket status change event."""
        from src.giljo_mcp.services.silence_detector import auto_clear_silent

        execution, tenant_key = silent_agent
        ws_mock = AsyncMock()

        await auto_clear_silent(
            session=db_session,
            job_id=execution.job_id,
            ws_manager=ws_mock,
        )

        ws_mock.broadcast_event_to_tenant.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_clear_noop_for_non_silent(self, db_session, working_agent_with_recent_progress):
        """Auto-clear should be a no-op for agents not in 'silent' status."""
        from src.giljo_mcp.services.silence_detector import auto_clear_silent

        execution, tenant_key = working_agent_with_recent_progress
        old_status = execution.status
        ws_mock = AsyncMock()

        await auto_clear_silent(
            session=db_session,
            job_id=execution.job_id,
            ws_manager=ws_mock,
        )

        await db_session.refresh(execution)
        assert execution.status == old_status
        ws_mock.broadcast_event_to_tenant.assert_not_called()

    @pytest.mark.asyncio
    async def test_auto_clear_nonexistent_job(self, db_session):
        """Auto-clear with nonexistent job_id should be a silent no-op."""
        from src.giljo_mcp.services.silence_detector import auto_clear_silent

        ws_mock = AsyncMock()

        # Should not raise
        await auto_clear_silent(
            session=db_session,
            job_id=str(uuid.uuid4()),
            ws_manager=ws_mock,
        )

        ws_mock.broadcast_event_to_tenant.assert_not_called()


# ---------------------------------------------------------------------------
# Unit Tests: SilenceDetector lifecycle
# ---------------------------------------------------------------------------


class TestSilenceDetectorLifecycle:
    """Test start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_creates_task(self):
        """Starting detector should create an asyncio task."""
        from src.giljo_mcp.services.silence_detector import SilenceDetector

        db_mock = MagicMock()
        ws_mock = AsyncMock()

        detector = SilenceDetector(db_manager=db_mock, ws_manager=ws_mock)

        # Patch the loop to avoid actually running
        with patch.object(detector, "_monitoring_loop", new_callable=AsyncMock):
            await detector.start()
            assert detector.running is True
            assert detector._task is not None

            await detector.stop()
            assert detector.running is False

    @pytest.mark.asyncio
    async def test_start_idempotent(self):
        """Starting twice should not create a second task."""
        from src.giljo_mcp.services.silence_detector import SilenceDetector

        db_mock = MagicMock()
        ws_mock = AsyncMock()

        detector = SilenceDetector(db_manager=db_mock, ws_manager=ws_mock)

        with patch.object(detector, "_monitoring_loop", new_callable=AsyncMock):
            await detector.start()
            first_task = detector._task
            await detector.start()  # Second start
            assert detector._task is first_task  # Same task

            await detector.stop()


# ---------------------------------------------------------------------------
# Integration Test: Full Lifecycle
# ---------------------------------------------------------------------------


class TestSilenceDetectorIntegration:
    """Integration test: working -> silent (timeout) -> MCP call -> working."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, db_session):
        """
        Full lifecycle test:
        1. Agent starts as 'working' with stale progress
        2. Silence detector marks it as 'silent'
        3. MCP call triggers auto_clear_silent -> back to 'working'
        4. Agent completes normally
        """
        from src.giljo_mcp.services.silence_detector import SilenceDetector, auto_clear_silent

        tenant_key = f"test_tenant_{uuid.uuid4().hex[:8]}"
        job_id = str(uuid.uuid4())
        agent_id = str(uuid.uuid4())
        project_id = str(uuid.uuid4())

        from src.giljo_mcp.models import Project

        project = Project(
            id=project_id,
            name="Lifecycle Test Project",
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
            job_type="lifecycle-worker",
            mission="Test lifecycle mission",
            status="active",
        )
        db_session.add(job)

        # Step 1: Agent is working with stale progress (15 minutes ago)
        execution = AgentExecution(
            agent_id=agent_id,
            job_id=job_id,
            tenant_key=tenant_key,
            agent_display_name="lifecycle-worker",
            agent_name="Lifecycle Worker",
            status="working",
            progress=50,
            last_progress_at=datetime.now(timezone.utc) - timedelta(minutes=15),
            health_status="unknown",
            tool_type="universal",
        )
        db_session.add(execution)
        await db_session.commit()
        await db_session.refresh(execution)

        assert execution.status == "working"

        # Step 2: Silence detector runs and marks agent as silent
        ws_mock = AsyncMock()
        detector = SilenceDetector(db_manager=MagicMock(), ws_manager=ws_mock)

        count = await detector._detect_silent_agents(db_session, threshold_minutes=10)
        assert count == 1

        await db_session.refresh(execution)
        assert execution.status == "silent"

        # Step 3: Agent makes an MCP call, auto-clear triggers
        await auto_clear_silent(
            session=db_session,
            job_id=job_id,
            ws_manager=ws_mock,
        )

        await db_session.refresh(execution)
        assert execution.status == "working"
        assert execution.last_progress_at > datetime.now(timezone.utc) - timedelta(seconds=5)

        # Step 4: Agent completes normally
        execution.status = "complete"
        execution.progress = 100
        execution.completed_at = datetime.now(timezone.utc)
        await db_session.commit()
        await db_session.refresh(execution)

        assert execution.status == "complete"

    @pytest.mark.asyncio
    async def test_multiple_stale_agents_detected(self, db_session):
        """Multiple stale agents across different tenants should all be detected."""
        from src.giljo_mcp.services.silence_detector import SilenceDetector

        from src.giljo_mcp.models import Project

        ws_mock = AsyncMock()
        detector = SilenceDetector(db_manager=MagicMock(), ws_manager=ws_mock)

        agents = []
        for i in range(3):
            tenant_key = f"test_tenant_multi_{uuid.uuid4().hex[:8]}"
            project_id = str(uuid.uuid4())
            job_id = str(uuid.uuid4())
            agent_id = str(uuid.uuid4())

            project = Project(
                id=project_id,
                name=f"Multi Test Project {i}",
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
                mission=f"Multi test mission {i}",
                status="active",
            )
            db_session.add(job)

            execution = AgentExecution(
                agent_id=agent_id,
                job_id=job_id,
                tenant_key=tenant_key,
                agent_display_name=f"multi-worker-{i}",
                agent_name=f"Multi Worker {i}",
                status="working",
                progress=30,
                last_progress_at=datetime.now(timezone.utc) - timedelta(minutes=15),
                health_status="unknown",
                tool_type="universal",
            )
            db_session.add(execution)
            agents.append(execution)

        await db_session.commit()

        count = await detector._detect_silent_agents(db_session, threshold_minutes=10)
        assert count == 3

        for agent in agents:
            await db_session.refresh(agent)
            assert agent.status == "silent"
