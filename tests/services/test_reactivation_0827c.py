# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Reactivate Job & Dismiss Reactivation Tests - Handover 0827c

Tests that OrchestrationService correctly:
1. reactivate_job() transitions blocked -> working with accumulated duration
2. reactivate_job() rejects non-blocked agents
3. reactivate_job() rejects agents in closed projects
4. reactivate_job() increments reactivation_count
5. dismiss_reactivation() transitions blocked -> complete
6. dismiss_reactivation() rejects non-blocked agents
7. receive_messages() includes _reactivation_guidance for blocked agents
8. receive_messages() does NOT include guidance for working agents
"""

import random
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import ProjectStateError, ResourceNotFoundError
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.models.tasks import Message, MessageRecipient
from src.giljo_mcp.services.message_service import MessageService
from src.giljo_mcp.services.orchestration_service import OrchestrationService
from src.giljo_mcp.tenant import TenantManager


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_websocket_manager():
    mock = MagicMock()
    mock.broadcast_to_tenant = AsyncMock()
    mock.broadcast_message_sent = AsyncMock()
    mock.broadcast_message_received = AsyncMock()
    mock.broadcast_message_acknowledged = AsyncMock()
    mock.broadcast_job_message = AsyncMock()
    mock.broadcast_job_status_change = AsyncMock()
    return mock


@pytest.fixture
async def test_product(db_session: AsyncSession, test_tenant_key: str) -> Product:
    product = Product(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        name="Reactivation Test Product",
        description="Product for 0827c tests",
        product_memory={},
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


def _create_agent(
    db_session: AsyncSession,
    project_id: str,
    tenant_key: str,
    display_name: str,
    role: str,
    status: str,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> tuple[AgentJob, AgentExecution]:
    """Helper to create a job + execution pair."""
    job = AgentJob(
        job_id=str(uuid4()),
        tenant_key=tenant_key,
        project_id=project_id,
        job_type=role,
        mission=f"Test mission for {role}",
        status="completed" if status == "complete" else "active",
    )
    db_session.add(job)

    now = datetime.now(timezone.utc)
    agent = AgentExecution(
        job_id=job.job_id,
        tenant_key=tenant_key,
        agent_display_name=display_name,
        status=status,
        messages_sent_count=0,
        messages_waiting_count=0,
        messages_read_count=0,
        started_at=started_at or now - timedelta(minutes=3),
        completed_at=completed_at or (now if status == "complete" else None),
        accumulated_duration_seconds=0.0,
        reactivation_count=0,
    )
    db_session.add(agent)
    return job, agent


@pytest.fixture
async def active_project(
    db_session: AsyncSession,
    test_tenant_key: str,
    test_product: Product,
) -> Project:
    project = Project(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        name="Reactivation Test Project",
        description="Test project for 0827c",
        mission="Test reactivation feature",
        status="active",
        created_at=datetime.now(timezone.utc),
        series_number=random.randint(1, 999999),
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.fixture
async def blocked_agent(
    db_session: AsyncSession,
    test_tenant_key: str,
    active_project: Project,
) -> tuple[AgentJob, AgentExecution]:
    """Create a blocked agent (auto-blocked from complete by 0827b)."""
    started = datetime.now(timezone.utc) - timedelta(minutes=5)
    completed = datetime.now(timezone.utc) - timedelta(minutes=2)

    job, agent = _create_agent(
        db_session,
        active_project.id,
        test_tenant_key,
        "Folder-Creator",
        "builder",
        "blocked",
        started_at=started,
        completed_at=completed,
    )
    agent.block_reason = "Received message from File-Creator while completed"
    job.status = "completed"

    await db_session.commit()
    await db_session.refresh(agent)
    await db_session.refresh(job)
    return job, agent


@pytest.fixture
async def orchestration_service(
    db_manager: DatabaseManager,
    db_session: AsyncSession,
    mock_websocket_manager: MagicMock,
    test_tenant_key: str,
) -> OrchestrationService:
    from contextlib import asynccontextmanager

    tenant_manager = MagicMock(spec=TenantManager)
    tenant_manager.get_current_tenant.return_value = test_tenant_key

    @asynccontextmanager
    async def mock_get_session_async():
        yield db_session

    db_manager.get_session_async = mock_get_session_async

    service = OrchestrationService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        test_session=db_session,
        websocket_manager=mock_websocket_manager,
    )
    return service


@pytest.fixture
async def message_service(
    db_manager: DatabaseManager,
    db_session: AsyncSession,
    mock_websocket_manager: MagicMock,
    test_tenant_key: str,
) -> MessageService:
    from contextlib import asynccontextmanager

    tenant_manager = MagicMock(spec=TenantManager)
    tenant_manager.get_current_tenant.return_value = test_tenant_key

    @asynccontextmanager
    async def mock_get_session_async():
        yield db_session

    db_manager.get_session_async = mock_get_session_async

    service = MessageService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        websocket_manager=mock_websocket_manager,
        test_session=db_session,
    )
    return service


# ============================================================================
# reactivate_job Tests
# ============================================================================


class TestReactivateJob:
    """Test reactivate_job() transitions and state changes."""

    @pytest.mark.asyncio
    async def test_reactivate_blocked_agent_transitions_to_working(
        self,
        db_session: AsyncSession,
        orchestration_service: OrchestrationService,
        blocked_agent: tuple[AgentJob, AgentExecution],
        test_tenant_key: str,
    ):
        """Blocked agent should transition to working on reactivation."""
        job, agent = blocked_agent

        result = await orchestration_service.reactivate_job(
            job_id=job.job_id,
            tenant_key=test_tenant_key,
            reason="fix request from File-Creator",
        )

        assert result.status == "reactivated"
        assert result.job_id == job.job_id

        await db_session.refresh(agent)
        assert agent.status == "working"
        assert agent.block_reason is None
        assert agent.completed_at is None
        assert agent.started_at is not None

    @pytest.mark.asyncio
    async def test_reactivate_accumulates_duration(
        self,
        db_session: AsyncSession,
        orchestration_service: OrchestrationService,
        blocked_agent: tuple[AgentJob, AgentExecution],
        test_tenant_key: str,
    ):
        """Reactivation should accumulate prior working duration."""
        job, agent = blocked_agent

        # Agent worked for ~3 minutes (started 5m ago, completed 2m ago)
        prior_duration = (agent.completed_at - agent.started_at).total_seconds()

        await orchestration_service.reactivate_job(
            job_id=job.job_id,
            tenant_key=test_tenant_key,
            reason="fix request",
        )

        await db_session.refresh(agent)
        assert agent.accumulated_duration_seconds == pytest.approx(prior_duration, abs=1.0)

    @pytest.mark.asyncio
    async def test_reactivate_increments_count(
        self,
        db_session: AsyncSession,
        orchestration_service: OrchestrationService,
        blocked_agent: tuple[AgentJob, AgentExecution],
        test_tenant_key: str,
    ):
        """Reactivation should increment reactivation_count."""
        job, agent = blocked_agent
        assert agent.reactivation_count == 0

        result = await orchestration_service.reactivate_job(
            job_id=job.job_id,
            tenant_key=test_tenant_key,
            reason="fix request",
        )

        assert result.reactivation_count == 1
        await db_session.refresh(agent)
        assert agent.reactivation_count == 1

    @pytest.mark.asyncio
    async def test_reactivate_transitions_job_to_active(
        self,
        db_session: AsyncSession,
        orchestration_service: OrchestrationService,
        blocked_agent: tuple[AgentJob, AgentExecution],
        test_tenant_key: str,
    ):
        """Reactivation should transition completed job back to active."""
        job, agent = blocked_agent
        assert job.status == "completed"

        await orchestration_service.reactivate_job(
            job_id=job.job_id,
            tenant_key=test_tenant_key,
            reason="fix request",
        )

        await db_session.refresh(job)
        assert job.status == "active"
        assert job.completed_at is None

    @pytest.mark.asyncio
    async def test_reactivate_returns_instruction(
        self,
        orchestration_service: OrchestrationService,
        blocked_agent: tuple[AgentJob, AgentExecution],
        test_tenant_key: str,
    ):
        """Reactivation result should include step-by-step instruction."""
        job, _ = blocked_agent

        result = await orchestration_service.reactivate_job(
            job_id=job.job_id,
            tenant_key=test_tenant_key,
        )

        assert "reactivated" in result.instruction.lower()
        assert "todo_append" in result.instruction
        assert "complete_job" in result.instruction

    @pytest.mark.asyncio
    async def test_reactivate_non_blocked_raises_not_found(
        self,
        db_session: AsyncSession,
        orchestration_service: OrchestrationService,
        active_project: Project,
        test_tenant_key: str,
    ):
        """Reactivating a non-blocked agent should raise ResourceNotFoundError."""
        job, agent = _create_agent(
            db_session,
            active_project.id,
            test_tenant_key,
            "Worker",
            "worker",
            "working",
        )
        await db_session.commit()

        with pytest.raises(ResourceNotFoundError, match="not in blocked status"):
            await orchestration_service.reactivate_job(
                job_id=job.job_id,
                tenant_key=test_tenant_key,
            )

    @pytest.mark.asyncio
    async def test_reactivate_complete_agent_raises_not_found(
        self,
        db_session: AsyncSession,
        orchestration_service: OrchestrationService,
        active_project: Project,
        test_tenant_key: str,
    ):
        """Reactivating a complete (not blocked) agent should raise ResourceNotFoundError."""
        job, agent = _create_agent(
            db_session,
            active_project.id,
            test_tenant_key,
            "Done-Agent",
            "done",
            "complete",
        )
        await db_session.commit()

        with pytest.raises(ResourceNotFoundError, match="not in blocked status"):
            await orchestration_service.reactivate_job(
                job_id=job.job_id,
                tenant_key=test_tenant_key,
            )

    @pytest.mark.asyncio
    async def test_reactivate_closed_project_raises_state_error(
        self,
        db_session: AsyncSession,
        orchestration_service: OrchestrationService,
        blocked_agent: tuple[AgentJob, AgentExecution],
        active_project: Project,
        test_tenant_key: str,
    ):
        """Reactivating in a closed project should raise ProjectStateError."""
        job, agent = blocked_agent

        # Close the project
        active_project.status = "completed"
        await db_session.commit()

        with pytest.raises(ProjectStateError, match="closed out"):
            await orchestration_service.reactivate_job(
                job_id=job.job_id,
                tenant_key=test_tenant_key,
            )

    @pytest.mark.asyncio
    async def test_reactivate_broadcasts_websocket(
        self,
        orchestration_service: OrchestrationService,
        blocked_agent: tuple[AgentJob, AgentExecution],
        mock_websocket_manager: MagicMock,
        test_tenant_key: str,
    ):
        """Reactivation should broadcast an agent:status_changed WebSocket event."""
        job, _ = blocked_agent

        await orchestration_service.reactivate_job(
            job_id=job.job_id,
            tenant_key=test_tenant_key,
        )

        mock_websocket_manager.broadcast_to_tenant.assert_called_once()
        call_kwargs = mock_websocket_manager.broadcast_to_tenant.call_args.kwargs
        assert call_kwargs["event_type"] == "agent:status_changed"
        assert call_kwargs["data"]["status"] == "working"
        assert call_kwargs["data"]["old_status"] == "blocked"


# ============================================================================
# dismiss_reactivation Tests
# ============================================================================


class TestDismissReactivation:
    """Test dismiss_reactivation() transitions and state changes."""

    @pytest.mark.asyncio
    async def test_dismiss_transitions_to_complete(
        self,
        db_session: AsyncSession,
        orchestration_service: OrchestrationService,
        blocked_agent: tuple[AgentJob, AgentExecution],
        test_tenant_key: str,
    ):
        """Dismissing should return blocked agent to complete status."""
        job, agent = blocked_agent

        result = await orchestration_service.dismiss_reactivation(
            job_id=job.job_id,
            tenant_key=test_tenant_key,
            reason="FYI message only",
        )

        assert result.status == "dismissed"
        assert result.job_id == job.job_id

        await db_session.refresh(agent)
        assert agent.status == "complete"
        assert agent.block_reason is None

    @pytest.mark.asyncio
    async def test_dismiss_preserves_timestamps(
        self,
        db_session: AsyncSession,
        orchestration_service: OrchestrationService,
        blocked_agent: tuple[AgentJob, AgentExecution],
        test_tenant_key: str,
    ):
        """Dismissing should not touch completed_at or started_at."""
        job, agent = blocked_agent
        original_started = agent.started_at
        original_completed = agent.completed_at

        await orchestration_service.dismiss_reactivation(
            job_id=job.job_id,
            tenant_key=test_tenant_key,
        )

        await db_session.refresh(agent)
        assert agent.started_at == original_started
        assert agent.completed_at == original_completed

    @pytest.mark.asyncio
    async def test_dismiss_restores_job_completed(
        self,
        db_session: AsyncSession,
        orchestration_service: OrchestrationService,
        blocked_agent: tuple[AgentJob, AgentExecution],
        test_tenant_key: str,
    ):
        """Dismissing should restore job status to completed if no other active executions."""
        job, agent = blocked_agent

        # The auto-block in 0827b doesn't change job status, but if it was
        # already "completed", dismiss should keep it that way
        assert job.status == "completed"

        await orchestration_service.dismiss_reactivation(
            job_id=job.job_id,
            tenant_key=test_tenant_key,
        )

        await db_session.refresh(job)
        assert job.status == "completed"

    @pytest.mark.asyncio
    async def test_dismiss_non_blocked_raises_not_found(
        self,
        db_session: AsyncSession,
        orchestration_service: OrchestrationService,
        active_project: Project,
        test_tenant_key: str,
    ):
        """Dismissing a non-blocked agent should raise ResourceNotFoundError."""
        job, agent = _create_agent(
            db_session,
            active_project.id,
            test_tenant_key,
            "Worker",
            "worker",
            "working",
        )
        await db_session.commit()

        with pytest.raises(ResourceNotFoundError, match="not in blocked status"):
            await orchestration_service.dismiss_reactivation(
                job_id=job.job_id,
                tenant_key=test_tenant_key,
            )

    @pytest.mark.asyncio
    async def test_dismiss_broadcasts_websocket(
        self,
        orchestration_service: OrchestrationService,
        blocked_agent: tuple[AgentJob, AgentExecution],
        mock_websocket_manager: MagicMock,
        test_tenant_key: str,
    ):
        """Dismiss should broadcast an agent:status_changed WebSocket event."""
        job, _ = blocked_agent

        await orchestration_service.dismiss_reactivation(
            job_id=job.job_id,
            tenant_key=test_tenant_key,
        )

        mock_websocket_manager.broadcast_to_tenant.assert_called_once()
        call_kwargs = mock_websocket_manager.broadcast_to_tenant.call_args.kwargs
        assert call_kwargs["event_type"] == "agent:status_changed"
        assert call_kwargs["data"]["status"] == "complete"
        assert call_kwargs["data"]["old_status"] == "blocked"


# ============================================================================
# Reactivation Guidance in receive_messages Tests
# ============================================================================


class TestReactivationGuidance:
    """Test _reactivation_guidance in receive_messages() response."""

    @pytest.mark.asyncio
    async def test_blocked_agent_gets_guidance(
        self,
        db_session: AsyncSession,
        message_service: MessageService,
        blocked_agent: tuple[AgentJob, AgentExecution],
        active_project: Project,
        test_tenant_key: str,
    ):
        """Blocked agent with messages should get _reactivation_guidance in response."""
        job, agent = blocked_agent

        # Create a pending message for this agent
        sender_id = str(uuid4())
        msg = Message(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            project_id=active_project.id,
            content="Fix the missing subfolder",
            message_type="direct",
            priority="normal",
            status="pending",
            from_agent_id=sender_id,
            from_display_name="File-Creator",
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(msg)
        await db_session.flush()
        db_session.add(
            MessageRecipient(
                message_id=msg.id,
                agent_id=agent.agent_id,
                tenant_key=test_tenant_key,
            )
        )
        await db_session.commit()

        result = await message_service.receive_messages(
            agent_id=agent.agent_id,
            tenant_key=test_tenant_key,
        )

        assert hasattr(result, "_reactivation_guidance")
        guidance = result._reactivation_guidance
        assert guidance["your_status"] == "blocked"
        assert guidance["your_job_id"] == job.job_id
        assert "reactivate_job" in guidance["instruction"]
        assert "dismiss_reactivation" in guidance["instruction"]

    @pytest.mark.asyncio
    async def test_working_agent_has_no_guidance(
        self,
        db_session: AsyncSession,
        message_service: MessageService,
        active_project: Project,
        test_tenant_key: str,
    ):
        """Working agent should NOT get _reactivation_guidance."""
        job, agent = _create_agent(
            db_session,
            active_project.id,
            test_tenant_key,
            "Worker-Agent",
            "worker",
            "working",
        )
        await db_session.commit()
        await db_session.refresh(agent)

        # Create a pending message for this agent
        msg = Message(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            project_id=active_project.id,
            content="Status update",
            message_type="direct",
            priority="normal",
            status="pending",
            from_agent_id=str(uuid4()),
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(msg)
        await db_session.flush()
        db_session.add(
            MessageRecipient(
                message_id=msg.id,
                agent_id=agent.agent_id,
                tenant_key=test_tenant_key,
            )
        )
        await db_session.commit()

        result = await message_service.receive_messages(
            agent_id=agent.agent_id,
            tenant_key=test_tenant_key,
        )

        assert not hasattr(result, "_reactivation_guidance")

    @pytest.mark.asyncio
    async def test_blocked_agent_no_messages_no_guidance(
        self,
        db_session: AsyncSession,
        message_service: MessageService,
        blocked_agent: tuple[AgentJob, AgentExecution],
        test_tenant_key: str,
    ):
        """Blocked agent with no pending messages should NOT get guidance."""
        job, agent = blocked_agent

        result = await message_service.receive_messages(
            agent_id=agent.agent_id,
            tenant_key=test_tenant_key,
        )

        # No messages, so no guidance
        assert not hasattr(result, "_reactivation_guidance")
