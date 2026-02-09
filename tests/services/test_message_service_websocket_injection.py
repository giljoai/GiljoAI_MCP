"""
Unit test for MessageService WebSocket injection (Handover 0293)

Tests that websocket_manager is properly injected and broadcast methods are called.
This is a unit test focusing on the core behavior without HTTP layer complexity.

Updated for Handover 0730: Exception-based error handling patterns.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.giljo_mcp.models import Project
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.services.message_service import MessageService


@pytest.mark.asyncio
async def test_message_service_websocket_injection(db_session, db_manager, tenant_manager):
    """
    BEHAVIOR: When MessageService is instantiated WITH websocket_manager,
    sending a message should call broadcast_message_sent.

    This test verifies the core bug fix: websocket_manager injection works.

    Updated for Handover 0730: Exception-based error handling patterns.
    - Requires AgentJob and AgentExecution for broadcast to have recipients
    - Success is indicated by NOT raising an exception (no 'success' key)
    """
    # Create a test tenant key
    from src.giljo_mcp.tenant import TenantManager

    tenant_key = TenantManager.generate_tenant_key()

    # Create a test project in the database
    project = Project(
        id=str(uuid4()),
        name="Test Project",
        description="Test project",
        mission="Test mission",
        tenant_key=tenant_key,
        status="active",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Create an agent job and execution so broadcast has recipients
    agent_job = AgentJob(
        job_id=str(uuid4()),
        project_id=project.id,
        tenant_key=tenant_key,
        job_type="test-agent",
        status="active",  # AgentJob status: active, completed, cancelled
        mission="Test mission",
    )
    db_session.add(agent_job)
    await db_session.flush()

    agent_execution = AgentExecution(
        agent_id=str(uuid4()),
        job_id=agent_job.job_id,
        tenant_key=tenant_key,
        agent_name="test-agent",
        agent_display_name="Test Agent",
        status="waiting",  # Active status for broadcast targeting
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(agent_execution)
    await db_session.commit()
    await db_session.refresh(agent_execution)

    # Create mock WebSocket manager with all required broadcast methods
    mock_ws_manager = MagicMock()
    mock_ws_manager.broadcast_message_sent = AsyncMock(return_value=None)
    mock_ws_manager.broadcast_message_received = AsyncMock(return_value=None)

    # Override db_manager.get_session_async to return our test session
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def get_test_session():
        yield db_session

    db_manager.get_session_async = get_test_session

    # Create MessageService WITH websocket_manager injected
    message_service = MessageService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        websocket_manager=mock_ws_manager,  # This is the fix we're testing
        test_session=db_session,  # Use test session for proper transaction handling
    )

    # Send a message (from orchestrator to all, which should reach our test agent)
    result = await message_service.send_message(
        to_agents=["all"],
        content="STAGING_COMPLETE: Mission created, 3 agents spawned",
        project_id=project.id,
        message_type="broadcast",
        from_agent="orchestrator",
        tenant_key=tenant_key,
    )

    # Handover 0730: Assert message was sent successfully (exception-based pattern)
    # Success is indicated by NOT raising an exception and having a message_id
    assert "message_id" in result
    assert result["message_id"] is not None  # Should have recipients now

    # CRITICAL ASSERTION: WebSocket broadcast MUST be called
    mock_ws_manager.broadcast_message_sent.assert_called_once()

    # Verify broadcast was called with correct parameters
    call_kwargs = mock_ws_manager.broadcast_message_sent.call_args.kwargs
    assert call_kwargs["project_id"] == project.id
    assert call_kwargs["from_agent"] == "orchestrator"
    assert "STAGING_COMPLETE" in call_kwargs["content_preview"]
    assert call_kwargs["tenant_key"] == tenant_key


@pytest.mark.asyncio
async def test_message_service_without_websocket_manager(db_session, db_manager, tenant_manager):
    """
    BEHAVIOR: When MessageService is instantiated WITHOUT websocket_manager,
    sending a message should NOT call any broadcast (no crash, graceful degradation).

    This test verifies backward compatibility.
    """
    # Create a test tenant key
    from src.giljo_mcp.tenant import TenantManager

    tenant_key = TenantManager.generate_tenant_key()

    # Create a test project
    project = Project(
        id=str(uuid4()),
        name="Test Project",
        description="Test project",
        mission="Test mission",
        tenant_key=tenant_key,
        status="active",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Override db_manager.get_session_async to return our test session
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def get_test_session():
        yield db_session

    db_manager.get_session_async = get_test_session

    # Create MessageService WITHOUT websocket_manager (old behavior)
    message_service = MessageService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        # websocket_manager NOT provided
    )

    # Send a message
    result = await message_service.send_message(
        to_agents=["all"],
        content="Test message",
        project_id=project.id,
        message_type="broadcast",
        from_agent="test_agent",
    )

    # Handover 0730: Assert message was sent successfully (exception-based pattern)
    # Success is indicated by NOT raising an exception and having a message_id
    assert "message_id" in result
    # message_id may be None if no recipients were found (empty project broadcast)
    # but for this test we expect graceful degradation without crash
