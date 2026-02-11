"""
MessageService Staging Directive Tests - Handover 0709b

Tests that MessageService enriches broadcast responses with staging_directive
when a staging-phase orchestrator broadcasts to all agents.

Defense-in-depth Layer 5.5: Reinforced advisory stop signal for staging completion.

Conditions for directive:
1. Sender is an orchestrator (AgentJob.agent_name == "orchestrator")
2. Job is in staging phase (AgentJob.status == "waiting")
3. Message is a broadcast (to_agents resolves to multiple agents or ['all'])

This is the RED phase of TDD - tests written before implementation.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project

# Import models using modular imports
from src.giljo_mcp.schemas.service_responses import SendMessageResult
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
    return mock


@pytest.fixture
async def test_tenant_key() -> str:
    """Generate unique tenant key for test isolation."""
    return f"test-tenant-{uuid4().hex[:8]}"


@pytest.fixture
async def test_product(db_session: AsyncSession, test_tenant_key: str) -> Product:
    """Create a test product for tests."""
    product = Product(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        name="Test Product",
        description="Test product for staging directive tests",
        product_memory={},
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest.fixture
async def test_project_staging(
    db_session: AsyncSession,
    test_tenant_key: str,
    test_product: Product,
) -> tuple[Project, AgentExecution, list[AgentExecution]]:
    """
    Create a test project with:
    - Staging-phase orchestrator (status=waiting)
    - Multiple agent jobs/executions
    Returns tuple of (project, orchestrator_execution, other_agents).
    """
    # Create project
    project = Project(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        name="Test Project Staging",
        description="Test project with staging orchestrator",
        mission="Test mission",
        status="active",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Create staging orchestrator (status=waiting)
    orchestrator_job = AgentJob(
        job_id=str(uuid4()),
        tenant_key=test_tenant_key,
        project_id=project.id,
        job_type="orchestrator",
        mission="Orchestrator mission",
        status="active",  # Job is active, but execution is waiting
    )
    db_session.add(orchestrator_job)

    orchestrator_execution = AgentExecution(
        job_id=orchestrator_job.job_id,
        tenant_key=test_tenant_key,
        agent_display_name="orchestrator",
        agent_name="orchestrator",  # CRITICAL: Used for detection
        status="waiting",  # Staging phase        messages_sent_count=0,
        messages_waiting_count=0,
        messages_read_count=0,
    )
    db_session.add(orchestrator_execution)

    # Create agent jobs and executions
    agent_display_names = ["analyzer", "implementer", "tester"]
    other_agents = []
    for agent_display_name in agent_display_names:
        # Create work order (AgentJob)
        job = AgentJob(
            job_id=str(uuid4()),
            tenant_key=test_tenant_key,
            project_id=project.id,
            job_type=agent_display_name,
            mission=f"Test mission for {agent_display_name}",
            status="active",
        )
        db_session.add(job)

        # Create executor instance (AgentExecution)
        agent = AgentExecution(
            job_id=job.job_id,
            tenant_key=test_tenant_key,
            agent_display_name=agent_display_name,
            agent_name=agent_display_name,
            status="waiting",
            messages_sent_count=0,
            messages_waiting_count=0,
            messages_read_count=0,
        )
        db_session.add(agent)
        other_agents.append(agent)

    await db_session.commit()
    await db_session.refresh(orchestrator_execution)
    for agent in other_agents:
        await db_session.refresh(agent)

    return project, orchestrator_execution, other_agents


@pytest.fixture
async def test_project_implementation(
    db_session: AsyncSession,
    test_tenant_key: str,
    test_product: Product,
) -> tuple[Project, AgentExecution, list[AgentExecution]]:
    """
    Create a test project with:
    - Implementation-phase orchestrator (status=working)
    - Multiple agent jobs/executions
    Returns tuple of (project, orchestrator_execution, other_agents).
    """
    # Create project
    project = Project(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        name="Test Project Implementation",
        description="Test project with implementation orchestrator",
        mission="Test mission",
        status="active",
        created_at=datetime.now(timezone.utc),
        # NOTE: implementation_launched_at removed to avoid DB schema mismatch in tests
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Create implementation orchestrator (status=working)
    orchestrator_job = AgentJob(
        job_id=str(uuid4()),
        tenant_key=test_tenant_key,
        project_id=project.id,
        job_type="orchestrator",
        mission="Orchestrator mission",
        status="active",
    )
    db_session.add(orchestrator_job)

    orchestrator_execution = AgentExecution(
        job_id=orchestrator_job.job_id,
        tenant_key=test_tenant_key,
        agent_display_name="orchestrator",
        agent_name="orchestrator",
        status="working",  # Implementation phase (acknowledged)        messages_sent_count=0,
        messages_waiting_count=0,
        messages_read_count=0,
    )
    db_session.add(orchestrator_execution)

    # Create agent jobs and executions
    agent_display_names = ["analyzer", "implementer"]
    other_agents = []
    for agent_display_name in agent_display_names:
        # Create work order (AgentJob)
        job = AgentJob(
            job_id=str(uuid4()),
            tenant_key=test_tenant_key,
            project_id=project.id,
            job_type=agent_display_name,
            mission=f"Test mission for {agent_display_name}",
            status="active",
        )
        db_session.add(job)

        # Create executor instance (AgentExecution)
        agent = AgentExecution(
            job_id=job.job_id,
            tenant_key=test_tenant_key,
            agent_display_name=agent_display_name,
            agent_name=agent_display_name,
            status="waiting",
            messages_sent_count=0,
            messages_waiting_count=0,
            messages_read_count=0,
        )
        db_session.add(agent)
        other_agents.append(agent)

    await db_session.commit()
    await db_session.refresh(orchestrator_execution)
    for agent in other_agents:
        await db_session.refresh(agent)

    return project, orchestrator_execution, other_agents


@pytest.fixture
async def message_service(
    db_manager: DatabaseManager,
    db_session: AsyncSession,
    mock_websocket_manager: MagicMock,
) -> MessageService:
    """Create MessageService instance with mocked WebSocket manager and test session."""
    from contextlib import asynccontextmanager

    tenant_manager = TenantManager()

    # Mock db_manager.get_session_async() to return test session
    # This ensures MessageService uses the transactional test session
    @asynccontextmanager
    async def mock_get_session_async():
        yield db_session

    # Patch the db_manager's method
    db_manager.get_session_async = mock_get_session_async

    # Create service with mocked WebSocket manager and test_session
    service = MessageService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        websocket_manager=mock_websocket_manager,
        test_session=db_session,  # Share test transaction
    )

    return service


# ============================================================================
# Tests
# ============================================================================


@pytest.mark.asyncio
async def test_staging_orchestrator_broadcast_includes_directive(
    message_service: MessageService,
    test_project_staging: tuple[Project, AgentExecution, list[AgentExecution]],
    test_tenant_key: str,
):
    """
    Broadcast from staging orchestrator includes staging_directive.

    Conditions:
    - Sender is orchestrator (agent_name="orchestrator")
    - Job status is "waiting" (staging phase)
    - Broadcast to all agents

    Expected:
    - Response contains "staging_directive" with STOP action
    """
    project, orchestrator, other_agents = test_project_staging

    # Send broadcast from staging orchestrator
    result = await message_service.send_message(
        to_agents=["all"],
        content="STAGING_COMPLETE: Mission created, 3 agents spawned",
        project_id=project.id,
        message_type="broadcast",
        priority="normal",
        from_agent=orchestrator.agent_id,
        tenant_key=test_tenant_key,
    )

    # Handover 0731c: send_message returns SendMessageResult typed model
    assert isinstance(result, SendMessageResult)
    assert result.message_id is not None
    assert result.staging_directive is not None, "Response should include staging_directive for staging orchestrator broadcast"

    # Verify directive structure (typed StagingDirective model)
    directive = result.staging_directive
    assert directive.status == "STAGING_SESSION_COMPLETE"
    assert directive.action == "STOP"
    assert "STAGING IS COMPLETE" in directive.message
    assert "Do NOT proceed to implementation" in directive.message
    assert directive.implementation_gate == "LOCKED"
    assert directive.next_step is not None


@pytest.mark.asyncio
async def test_regular_agent_broadcast_no_directive(
    message_service: MessageService,
    test_project_staging: tuple[Project, AgentExecution, list[AgentExecution]],
    test_tenant_key: str,
):
    """
    Broadcast from regular agent does NOT include staging_directive.

    Conditions:
    - Sender is NOT orchestrator (agent_name="analyzer")
    - Broadcast to all agents

    Expected:
    - Response does NOT contain "staging_directive"
    """
    project, orchestrator, other_agents = test_project_staging
    regular_agent = other_agents[0]  # analyzer

    # Send broadcast from regular agent
    result = await message_service.send_message(
        to_agents=["all"],
        content="Status update from analyzer",
        project_id=project.id,
        message_type="broadcast",
        priority="normal",
        from_agent=regular_agent.agent_id,
        tenant_key=test_tenant_key,
    )

    # Handover 0731c: send_message returns SendMessageResult typed model
    assert isinstance(result, SendMessageResult)
    assert result.message_id is not None
    assert result.staging_directive is None, "Regular agent broadcasts should not include staging_directive"


@pytest.mark.asyncio
async def test_implementation_orchestrator_broadcast_no_directive(
    message_service: MessageService,
    test_project_implementation: tuple[Project, AgentExecution, list[AgentExecution]],
    test_tenant_key: str,
):
    """
    Broadcast from implementation-phase orchestrator does NOT include directive.

    Conditions:
    - Sender is orchestrator (agent_name="orchestrator")
    - Job status is "working" (implementation phase - acknowledged)
    - Broadcast to all agents

    Expected:
    - Response does NOT contain "staging_directive"
    """
    project, orchestrator, other_agents = test_project_implementation

    # Send broadcast from implementation-phase orchestrator
    result = await message_service.send_message(
        to_agents=["all"],
        content="Implementation progress update",
        project_id=project.id,
        message_type="broadcast",
        priority="normal",
        from_agent=orchestrator.agent_id,
        tenant_key=test_tenant_key,
    )

    # Handover 0731c: send_message returns SendMessageResult typed model
    assert isinstance(result, SendMessageResult)
    assert result.message_id is not None
    assert result.staging_directive is None, (
        "Implementation orchestrator broadcasts should not include staging_directive"
    )


@pytest.mark.asyncio
async def test_staging_directive_has_required_fields(
    message_service: MessageService,
    test_project_staging: tuple[Project, AgentExecution, list[AgentExecution]],
    test_tenant_key: str,
):
    """
    Verify staging_directive contains all required fields.

    Required fields:
    - status: "STAGING_SESSION_COMPLETE"
    - action: "STOP"
    - message: Clear instructions to stop
    - implementation_gate: "LOCKED"
    - next_step: What orchestrator should do
    """
    project, orchestrator, other_agents = test_project_staging

    # Send broadcast from staging orchestrator
    result = await message_service.send_message(
        to_agents=["all"],
        content="STAGING_COMPLETE",
        project_id=project.id,
        message_type="broadcast",
        priority="normal",
        from_agent=orchestrator.agent_id,
        tenant_key=test_tenant_key,
    )

    # Handover 0731c: Assert directive has all required fields (typed model)
    assert isinstance(result, SendMessageResult)
    assert result.staging_directive is not None
    directive = result.staging_directive

    # Required fields (typed StagingDirective model)
    assert directive.status == "STAGING_SESSION_COMPLETE"
    assert directive.action == "STOP"
    assert isinstance(directive.message, str)
    assert len(directive.message) > 0
    assert "STAGING IS COMPLETE" in directive.message
    assert directive.implementation_gate == "LOCKED"
    assert isinstance(directive.next_step, str)


@pytest.mark.asyncio
async def test_direct_message_no_directive(
    message_service: MessageService,
    test_project_staging: tuple[Project, AgentExecution, list[AgentExecution]],
    test_tenant_key: str,
):
    """
    Direct message (not broadcast) from orchestrator has no directive.

    Conditions:
    - Sender is staging orchestrator
    - Message sent to ONE specific agent (not broadcast)

    Expected:
    - Response does NOT contain "staging_directive"
    """
    project, orchestrator, other_agents = test_project_staging
    target_agent = other_agents[0]  # analyzer

    # Send direct message (not broadcast)
    result = await message_service.send_message(
        to_agents=[target_agent.agent_display_name],  # Single recipient
        content="Direct message to analyzer",
        project_id=project.id,
        message_type="direct",
        priority="normal",
        from_agent=orchestrator.agent_id,
        tenant_key=test_tenant_key,
    )

    # Handover 0731c: send_message returns SendMessageResult typed model
    assert isinstance(result, SendMessageResult)
    assert result.message_id is not None
    assert result.staging_directive is None, "Direct messages should not include staging_directive (only broadcasts)"
