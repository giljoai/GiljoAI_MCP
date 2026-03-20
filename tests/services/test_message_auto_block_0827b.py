"""
Auto-Block on Post-Completion Message Tests - Handover 0827b

Tests that MessageService correctly:
1. Transitions completed agents to 'blocked' when they receive a direct message
2. Does NOT auto-block when agent is in working/waiting/blocked status
3. Does NOT auto-block on broadcast messages
4. Does NOT auto-block when project is closed out (completed/cancelled)
5. Sets appropriate block_reason with sender display name
"""

import random
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.services.message_service import MessageService
from src.giljo_mcp.tenant import TenantManager


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_websocket_manager():
    """Mock WebSocket manager for testing without real WebSocket connections."""
    mock = MagicMock()
    mock.broadcast_message_sent = AsyncMock()
    mock.broadcast_message_received = AsyncMock()
    mock.broadcast_message_acknowledged = AsyncMock()
    mock.broadcast_job_message = AsyncMock()
    mock.broadcast_job_status_change = AsyncMock()
    return mock


@pytest.fixture
async def test_product(db_session: AsyncSession, test_tenant_key: str) -> Product:
    """Create a test product."""
    product = Product(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        name="Auto-Block Test Product",
        description="Product for 0827b auto-block tests",
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
) -> tuple[AgentJob, AgentExecution]:
    """Helper to create a job + execution pair."""
    job = AgentJob(
        job_id=str(uuid4()),
        tenant_key=tenant_key,
        project_id=project_id,
        job_type=role,
        mission=f"Test mission for {role}",
        status="active" if status != "complete" else "completed",
    )
    db_session.add(job)

    agent = AgentExecution(
        job_id=job.job_id,
        tenant_key=tenant_key,
        agent_display_name=display_name,
        status=status,
        messages_sent_count=0,
        messages_waiting_count=0,
        messages_read_count=0,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc) if status == "complete" else None,
    )
    db_session.add(agent)
    return job, agent


@pytest.fixture
async def active_project_with_agents(
    db_session: AsyncSession,
    test_tenant_key: str,
    test_product: Product,
) -> tuple[Project, AgentExecution, AgentExecution]:
    """Create an active project with a working sender and a completed recipient."""
    project = Project(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        name="Auto-Block Test Project",
        description="Test project for 0827b",
        mission="Test auto-block feature",
        status="active",
        created_at=datetime.now(timezone.utc),
        series_number=random.randint(1, 999999),
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    _, sender = _create_agent(
        db_session, project.id, test_tenant_key,
        "File-Creator", "creator", "working",
    )
    _, recipient = _create_agent(
        db_session, project.id, test_tenant_key,
        "Folder-Creator", "builder", "complete",
    )

    await db_session.commit()
    await db_session.refresh(sender)
    await db_session.refresh(recipient)

    return project, sender, recipient


@pytest.fixture
async def message_service(
    db_manager: DatabaseManager,
    db_session: AsyncSession,
    mock_websocket_manager: MagicMock,
    test_tenant_key: str,
) -> MessageService:
    """Create MessageService instance with mocked WebSocket manager and test session."""
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
# Test Cases
# ============================================================================


class TestAutoBlockCompletedRecipient:
    """Test that direct messages to completed agents trigger auto-block."""

    @pytest.mark.asyncio
    async def test_direct_message_to_completed_agent_blocks(
        self,
        db_session: AsyncSession,
        message_service: MessageService,
        active_project_with_agents: tuple[Project, AgentExecution, AgentExecution],
        test_tenant_key: str,
    ):
        """Direct message to a completed agent should flip status to 'blocked'."""
        project, sender, recipient = active_project_with_agents

        await message_service.send_message(
            to_agents=[recipient.agent_display_name],
            content="Fix the missing subfolder",
            project_id=project.id,
            message_type="direct",
            from_agent=sender.agent_id,
            tenant_key=test_tenant_key,
        )

        # Refresh recipient to see the status change
        await db_session.refresh(recipient)
        assert recipient.status == "blocked"

    @pytest.mark.asyncio
    async def test_auto_block_sets_reason_with_sender_name(
        self,
        db_session: AsyncSession,
        message_service: MessageService,
        active_project_with_agents: tuple[Project, AgentExecution, AgentExecution],
        test_tenant_key: str,
    ):
        """Block reason should include the sender's display name."""
        project, sender, recipient = active_project_with_agents

        await message_service.send_message(
            to_agents=[recipient.agent_display_name],
            content="Fix the missing subfolder",
            project_id=project.id,
            message_type="direct",
            from_agent=sender.agent_id,
            tenant_key=test_tenant_key,
        )

        await db_session.refresh(recipient)
        assert recipient.block_reason is not None
        assert "File-Creator" in recipient.block_reason

    @pytest.mark.asyncio
    async def test_auto_block_fires_websocket_event(
        self,
        db_session: AsyncSession,
        message_service: MessageService,
        active_project_with_agents: tuple[Project, AgentExecution, AgentExecution],
        mock_websocket_manager: MagicMock,
        test_tenant_key: str,
    ):
        """Auto-block should broadcast an agent:status_changed WebSocket event."""
        project, sender, recipient = active_project_with_agents

        await message_service.send_message(
            to_agents=[recipient.agent_display_name],
            content="Fix the missing subfolder",
            project_id=project.id,
            message_type="direct",
            from_agent=sender.agent_id,
            tenant_key=test_tenant_key,
        )

        mock_websocket_manager.broadcast_job_status_change.assert_called_once()
        call_kwargs = mock_websocket_manager.broadcast_job_status_change.call_args
        assert call_kwargs.kwargs["old_status"] == "complete"
        assert call_kwargs.kwargs["new_status"] == "blocked"


class TestAutoBlockSkipConditions:
    """Test that auto-block does NOT trigger in certain conditions."""

    @pytest.mark.asyncio
    async def test_message_to_working_agent_does_not_block(
        self,
        db_session: AsyncSession,
        message_service: MessageService,
        active_project_with_agents: tuple[Project, AgentExecution, AgentExecution],
        test_tenant_key: str,
    ):
        """A message to a 'working' agent should NOT change its status."""
        project, sender, recipient = active_project_with_agents

        # Make recipient working instead of complete
        recipient.status = "working"
        recipient.completed_at = None
        await db_session.commit()

        await message_service.send_message(
            to_agents=[recipient.agent_display_name],
            content="How is progress?",
            project_id=project.id,
            message_type="direct",
            from_agent=sender.agent_id,
            tenant_key=test_tenant_key,
        )

        await db_session.refresh(recipient)
        assert recipient.status == "working"
        assert recipient.block_reason is None

    @pytest.mark.asyncio
    async def test_broadcast_to_completed_agent_does_not_block(
        self,
        db_session: AsyncSession,
        message_service: MessageService,
        active_project_with_agents: tuple[Project, AgentExecution, AgentExecution],
        test_tenant_key: str,
    ):
        """Broadcast messages should NOT auto-block completed agents."""
        project, sender, recipient = active_project_with_agents

        await message_service.send_message(
            to_agents=["all"],
            content="Phase 2 complete",
            project_id=project.id,
            message_type="direct",
            from_agent=sender.agent_id,
            tenant_key=test_tenant_key,
        )

        await db_session.refresh(recipient)
        # Should still be complete — broadcasts don't trigger auto-block
        assert recipient.status == "complete"

    @pytest.mark.asyncio
    async def test_message_in_closed_project_does_not_block(
        self,
        db_session: AsyncSession,
        message_service: MessageService,
        active_project_with_agents: tuple[Project, AgentExecution, AgentExecution],
        test_tenant_key: str,
    ):
        """Messages in a completed project should NOT auto-block."""
        project, sender, recipient = active_project_with_agents

        # Close out the project
        project.status = "completed"
        await db_session.commit()

        await message_service.send_message(
            to_agents=[recipient.agent_display_name],
            content="FYI: project wrapped up",
            project_id=project.id,
            message_type="direct",
            from_agent=sender.agent_id,
            tenant_key=test_tenant_key,
        )

        await db_session.refresh(recipient)
        assert recipient.status == "complete"

    @pytest.mark.asyncio
    async def test_message_in_cancelled_project_does_not_block(
        self,
        db_session: AsyncSession,
        message_service: MessageService,
        active_project_with_agents: tuple[Project, AgentExecution, AgentExecution],
        test_tenant_key: str,
    ):
        """Messages in a cancelled project should NOT auto-block."""
        project, sender, recipient = active_project_with_agents

        project.status = "cancelled"
        await db_session.commit()

        await message_service.send_message(
            to_agents=[recipient.agent_display_name],
            content="Cancelled notice",
            project_id=project.id,
            message_type="direct",
            from_agent=sender.agent_id,
            tenant_key=test_tenant_key,
        )

        await db_session.refresh(recipient)
        assert recipient.status == "complete"
