# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Message Counter Atomic & Self-Healing Tests

Tests for two root-cause bug fixes to message counter logic:

Fix 1 (Atomic SQL UPDATE in complete_job):
  OrchestrationService.complete_job() now uses atomic SQL UPDATE
  instead of ORM stale-read for counter increments when auto-creating
  a completion_report message to the orchestrator.

Fix 2 (Self-healing counter in receive_messages):
  MessageService.receive_messages() now counts actual remaining
  pending messages (SET) instead of blindly decrementing (subtract).
  This self-heals any drifted counters on every receive call.
"""

import random
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select

from src.giljo_mcp.models import (
    AgentExecution,
    AgentJob,
    AgentTemplate,
    Message,
    Product,
    Project,
)
from src.giljo_mcp.models.tasks import MessageRecipient
from src.giljo_mcp.schemas.service_responses import MessageListResult
from src.giljo_mcp.services.message_service import MessageService
from src.giljo_mcp.services.orchestration_service import OrchestrationService
from src.giljo_mcp.tenant import TenantManager

# ============================================================================
# Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def tenant_key() -> str:
    """Generate a valid tenant key for test isolation."""
    return TenantManager.generate_tenant_key()


@pytest_asyncio.fixture
async def other_tenant_key() -> str:
    """Generate a second tenant key for cross-tenant isolation tests."""
    return TenantManager.generate_tenant_key()


@pytest_asyncio.fixture
async def agent_templates(db_session, tenant_key):
    """Create agent templates needed by spawn_agent_job validation."""
    template_names = ["specialist-1", "orchestrator"]
    for name in template_names:
        template = AgentTemplate(
            tenant_key=tenant_key,
            name=name,
            role=name,
            description=f"Test template for {name}",
            system_instructions=f"# {name}\nTest agent.",
            is_active=True,
        )
        db_session.add(template)
    await db_session.commit()


@pytest_asyncio.fixture
async def test_product(db_session, tenant_key) -> Product:
    """Create a test product for project association."""
    product = Product(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        name=f"Counter Test Product {uuid.uuid4().hex[:6]}",
        description="Product for counter fix tests",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def project(db_session, tenant_key, agent_templates, test_product) -> Project:
    """Create a test project with required fields."""
    proj = Project(
        id=str(uuid.uuid4()),
        name="Counter Fix Test Project",
        description="Integration test project for counter bug fixes",
        mission="Test atomic and self-healing counter logic",
        status="active",
        tenant_key=tenant_key,
        product_id=test_product.id,
        implementation_launched_at=datetime.now(timezone.utc),
        series_number=random.randint(1, 999999),
    )
    db_session.add(proj)
    await db_session.commit()
    await db_session.refresh(proj)
    return proj


@pytest_asyncio.fixture
async def orch_service(db_session, db_manager) -> OrchestrationService:
    """Create OrchestrationService with shared test session."""
    tm = TenantManager()
    return OrchestrationService(
        db_manager=db_manager,
        tenant_manager=tm,
        test_session=db_session,
    )


@pytest_asyncio.fixture
async def msg_service(db_manager, db_session) -> MessageService:
    """Create MessageService with shared test session and mocked WebSocket."""
    from contextlib import asynccontextmanager
    from unittest.mock import AsyncMock, MagicMock

    tm = TenantManager()

    @asynccontextmanager
    async def mock_get_session_async():
        yield db_session

    db_manager.get_session_async = mock_get_session_async

    mock_ws = MagicMock()
    mock_ws.broadcast_message_sent = AsyncMock()
    mock_ws.broadcast_message_received = AsyncMock()
    mock_ws.broadcast_message_acknowledged = AsyncMock()
    mock_ws.broadcast_job_message = AsyncMock()

    return MessageService(
        db_manager=db_manager,
        tenant_manager=tm,
        websocket_manager=mock_ws,
        test_session=db_session,
    )


# ============================================================================
# Fix 1: Atomic SQL UPDATE in complete_job
# ============================================================================


@pytest.mark.asyncio
class TestCompleteJobAtomicCounterUpdate:
    """Verify complete_job uses atomic SQL UPDATE for counter increments."""

    async def test_complete_job_increments_orchestrator_waiting_count(
        self, db_session, orch_service, project, tenant_key
    ):
        """After complete_job, orchestrator's messages_waiting_count increases by 1.

        When a specialist completes, a completion_report message is auto-created
        for the orchestrator. The orchestrator's waiting count must reflect this.
        """
        # Arrange: spawn orchestrator, then specialist
        orch_spawn = await orch_service.spawn_agent_job(
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            mission="Orchestrate the project",
            project_id=project.id,
            tenant_key=tenant_key,
        )

        spec_spawn = await orch_service.spawn_agent_job(
            agent_display_name="specialist",
            agent_name="specialist-1",
            mission="Do specialized work",
            project_id=project.id,
            tenant_key=tenant_key,
        )

        # Verify orchestrator starts at 0 waiting
        orch_exec_stmt = select(AgentExecution).where(
            AgentExecution.agent_id == orch_spawn.agent_id,
            AgentExecution.tenant_key == tenant_key,
        )
        orch_exec = (await db_session.execute(orch_exec_stmt)).scalar_one()
        assert orch_exec.messages_waiting_count == 0

        # Act: complete the specialist job (triggers auto-message to orchestrator)
        result = await orch_service.complete_job(
            job_id=spec_spawn.job_id,
            result={"summary": "Work done"},
            tenant_key=tenant_key,
        )
        assert result.status == "success"

        # Assert: orchestrator waiting count incremented by 1
        await db_session.refresh(orch_exec)
        assert orch_exec.messages_waiting_count == 1, (
            f"Expected orchestrator waiting_count=1 after specialist completion, "
            f"got {orch_exec.messages_waiting_count}"
        )

    async def test_complete_job_increments_agent_sent_count(
        self, db_session, orch_service, project, tenant_key
    ):
        """After complete_job, the completing agent's messages_sent_count increases by 1.

        The auto-generated completion_report counts as a sent message
        for the specialist agent that completed.
        """
        # Arrange: spawn orchestrator, then specialist
        await orch_service.spawn_agent_job(
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            mission="Orchestrate the project",
            project_id=project.id,
            tenant_key=tenant_key,
        )

        spec_spawn = await orch_service.spawn_agent_job(
            agent_display_name="specialist",
            agent_name="specialist-1",
            mission="Do specialized work",
            project_id=project.id,
            tenant_key=tenant_key,
        )

        # Verify specialist starts at 0 sent
        spec_exec_stmt = select(AgentExecution).where(
            AgentExecution.agent_id == spec_spawn.agent_id,
            AgentExecution.tenant_key == tenant_key,
        )
        spec_exec = (await db_session.execute(spec_exec_stmt)).scalar_one()
        assert spec_exec.messages_sent_count == 0

        # Act: complete the specialist
        result = await orch_service.complete_job(
            job_id=spec_spawn.job_id,
            result={"summary": "Implemented feature"},
            tenant_key=tenant_key,
        )
        assert result.status == "success"

        # Assert: specialist sent_count incremented by 1
        await db_session.refresh(spec_exec)
        assert spec_exec.messages_sent_count == 1, (
            f"Expected specialist sent_count=1 after completion, "
            f"got {spec_exec.messages_sent_count}"
        )

    async def test_complete_job_counter_uses_tenant_key(
        self, db_session, orch_service, project, tenant_key, other_tenant_key
    ):
        """The atomic UPDATE filters by tenant_key, verifying tenant isolation.

        A completion for tenant A must not affect counter values for
        an agent in tenant B that happens to share the same agent_id.
        """
        # Arrange: spawn orchestrator and specialist in tenant A
        orch_spawn = await orch_service.spawn_agent_job(
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            mission="Orchestrate",
            project_id=project.id,
            tenant_key=tenant_key,
        )

        spec_spawn = await orch_service.spawn_agent_job(
            agent_display_name="specialist",
            agent_name="specialist-1",
            mission="Do work",
            project_id=project.id,
            tenant_key=tenant_key,
        )

        # Create a decoy execution in tenant B with the same agent_id as
        # the orchestrator, to verify tenant isolation of the UPDATE
        decoy_job = AgentJob(
            job_id=str(uuid.uuid4()),
            tenant_key=other_tenant_key,
            project_id=project.id,
            job_type="orchestrator",
            mission="Decoy orchestrator in other tenant",
            status="active",
        )
        db_session.add(decoy_job)

        decoy_exec = AgentExecution(
            agent_id=orch_spawn.agent_id,  # Same agent_id as tenant A orchestrator
            job_id=decoy_job.job_id,
            tenant_key=other_tenant_key,
            agent_display_name="orchestrator",
            status="waiting",
            messages_sent_count=0,
            messages_waiting_count=0,
            messages_read_count=0,
        )
        db_session.add(decoy_exec)
        await db_session.commit()

        # Act: complete the specialist in tenant A
        await orch_service.complete_job(
            job_id=spec_spawn.job_id,
            result={"summary": "Done"},
            tenant_key=tenant_key,
        )

        # Assert: tenant A orchestrator got the counter bump
        orch_exec_stmt = select(AgentExecution).where(
            AgentExecution.agent_id == orch_spawn.agent_id,
            AgentExecution.tenant_key == tenant_key,
        )
        orch_exec = (await db_session.execute(orch_exec_stmt)).scalar_one()
        assert orch_exec.messages_waiting_count == 1

        # Assert: tenant B decoy was NOT affected
        await db_session.refresh(decoy_exec)
        assert decoy_exec.messages_waiting_count == 0, (
            f"Tenant B decoy waiting_count should be 0 (untouched), "
            f"got {decoy_exec.messages_waiting_count}"
        )


# ============================================================================
# Fix 2: Self-Healing Counter in receive_messages
# ============================================================================


@pytest_asyncio.fixture
async def project_with_messaging_agents(
    db_session, tenant_key, test_product
) -> tuple[Project, list[AgentExecution], list[AgentJob]]:
    """Create a project with agents suitable for messaging tests.

    Returns (project, [orchestrator_exec, analyzer_exec], [orch_job, analyzer_job]).
    Messages can be sent to these agents and then received.
    """
    proj = Project(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        product_id=test_product.id,
        name="Messaging Counter Test Project",
        description="For self-healing counter tests",
        mission="Test receive_messages counter behavior",
        status="active",
        created_at=datetime.now(timezone.utc),
        series_number=random.randint(1, 999999),
    )
    db_session.add(proj)
    await db_session.commit()
    await db_session.refresh(proj)

    agent_configs = [
        ("orchestrator", "waiting"),
        ("analyzer", "waiting"),
    ]

    agents = []
    jobs = []
    for display_name, status in agent_configs:
        job = AgentJob(
            job_id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            project_id=proj.id,
            job_type=display_name,
            mission=f"Test mission for {display_name}",
            status="active",
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
        )
        db_session.add(agent)
        agents.append(agent)
        jobs.append(job)

    await db_session.commit()
    for agent in agents:
        await db_session.refresh(agent)

    return proj, agents, jobs


@pytest.mark.asyncio
class TestReceiveMessagesSelfHealingCounter:
    """Verify receive_messages uses self-healing counter logic."""

    async def test_receive_messages_sets_waiting_to_actual_pending(
        self,
        db_session,
        msg_service,
        project_with_messaging_agents,
        tenant_key,
    ):
        """After receiving messages, waiting_count equals actual remaining pending.

        If there were 3 pending messages and the agent receives 2 (limit=2),
        waiting_count should be set to 1 (the actual remaining), not
        decremented from whatever the counter was before.
        """
        proj, agents, _jobs = project_with_messaging_agents
        orchestrator = agents[0]
        analyzer = agents[1]

        # Create 3 pending messages for the analyzer
        for i in range(3):
            msg = Message(
                tenant_key=tenant_key,
                project_id=proj.id,
                content=f"Test message {i}",
                message_type="directive",
                status="pending",
                from_agent_id=str(orchestrator.agent_id),
            )
            db_session.add(msg)
            await db_session.flush()
            db_session.add(MessageRecipient(
                message_id=msg.id,
                agent_id=analyzer.agent_id,
                tenant_key=tenant_key,
            ))

        # Set waiting_count to 3 to reflect the 3 pending messages
        analyzer.messages_waiting_count = 3
        await db_session.commit()
        await db_session.refresh(analyzer)

        # Act: receive only 2 messages (limit=2)
        result = await msg_service.receive_messages(
            agent_id=analyzer.agent_id,
            limit=2,
            tenant_key=tenant_key,
        )

        assert isinstance(result, MessageListResult)
        assert result.count == 2

        # Assert: waiting_count is actual remaining pending (1), not 3-2=1
        # This happens to be the same in the happy path, but the mechanism
        # is different: SET to actual pending count, not blind subtract.
        await db_session.refresh(analyzer)
        assert analyzer.messages_waiting_count == 1, (
            f"Expected waiting_count=1 (1 remaining pending), "
            f"got {analyzer.messages_waiting_count}"
        )

    async def test_receive_messages_increments_read_count(
        self,
        db_session,
        msg_service,
        project_with_messaging_agents,
        tenant_key,
    ):
        """read_count increases by the number of messages received."""
        proj, agents, _jobs = project_with_messaging_agents
        orchestrator = agents[0]
        analyzer = agents[1]

        # Create 2 pending messages for the analyzer
        for i in range(2):
            msg = Message(
                tenant_key=tenant_key,
                project_id=proj.id,
                content=f"Read count test message {i}",
                message_type="directive",
                status="pending",
                from_agent_id=str(orchestrator.agent_id),
            )
            db_session.add(msg)
            await db_session.flush()
            db_session.add(MessageRecipient(
                message_id=msg.id,
                agent_id=analyzer.agent_id,
                tenant_key=tenant_key,
            ))

        analyzer.messages_waiting_count = 2
        await db_session.commit()
        await db_session.refresh(analyzer)

        assert analyzer.messages_read_count == 0

        # Act: receive all 2 messages
        result = await msg_service.receive_messages(
            agent_id=analyzer.agent_id,
            limit=10,
            tenant_key=tenant_key,
        )

        assert result.count == 2

        # Assert: read_count incremented by 2
        await db_session.refresh(analyzer)
        assert analyzer.messages_read_count == 2, (
            f"Expected read_count=2 after receiving 2 messages, "
            f"got {analyzer.messages_read_count}"
        )

    async def test_receive_messages_self_heals_drifted_counter(
        self,
        db_session,
        msg_service,
        project_with_messaging_agents,
        tenant_key,
    ):
        """If waiting_count was wrong (drifted), after receive it is corrected.

        This is the core value of the self-healing pattern. Even if the
        counter drifted to an incorrect value (e.g. due to a past bug,
        concurrent race, or failed counter update), the next receive_messages
        call resets it to the actual pending message count.
        """
        proj, agents, _jobs = project_with_messaging_agents
        orchestrator = agents[0]
        analyzer = agents[1]

        # Create 3 pending messages
        for i in range(3):
            msg = Message(
                tenant_key=tenant_key,
                project_id=proj.id,
                content=f"Drift test message {i}",
                message_type="directive",
                status="pending",
                from_agent_id=str(orchestrator.agent_id),
            )
            db_session.add(msg)
            await db_session.flush()
            db_session.add(MessageRecipient(
                message_id=msg.id,
                agent_id=analyzer.agent_id,
                tenant_key=tenant_key,
            ))

        # Deliberately set a WRONG waiting_count to simulate drift
        # Actual pending = 3, but counter says 99 (drifted)
        analyzer.messages_waiting_count = 99
        await db_session.commit()
        await db_session.refresh(analyzer)
        assert analyzer.messages_waiting_count == 99  # Confirm drifted state

        # Act: receive 1 message (limit=1)
        result = await msg_service.receive_messages(
            agent_id=analyzer.agent_id,
            limit=1,
            tenant_key=tenant_key,
        )

        assert result.count == 1

        # Assert: waiting_count HEALED to actual remaining pending (2),
        # NOT blindly decremented from 99 to 98
        await db_session.refresh(analyzer)
        assert analyzer.messages_waiting_count == 2, (
            f"Expected self-healed waiting_count=2 (2 actually pending), "
            f"got {analyzer.messages_waiting_count}. "
            f"Counter should have been SET to actual pending, not decremented."
        )

    async def test_receive_messages_self_heals_zero_drift(
        self,
        db_session,
        msg_service,
        project_with_messaging_agents,
        tenant_key,
    ):
        """Counter heals even when drifted to 0 with messages still pending.

        Tests the opposite drift direction: counter is 0 but there are
        actually pending messages. After receive, the remaining pending
        count is correctly reflected.
        """
        proj, agents, _jobs = project_with_messaging_agents
        orchestrator = agents[0]
        analyzer = agents[1]

        # Create 2 pending messages
        for i in range(2):
            msg = Message(
                tenant_key=tenant_key,
                project_id=proj.id,
                content=f"Zero drift test message {i}",
                message_type="directive",
                status="pending",
                from_agent_id=str(orchestrator.agent_id),
            )
            db_session.add(msg)
            await db_session.flush()
            db_session.add(MessageRecipient(
                message_id=msg.id,
                agent_id=analyzer.agent_id,
                tenant_key=tenant_key,
            ))

        # Counter is 0 but actually 2 pending (drifted down)
        analyzer.messages_waiting_count = 0
        await db_session.commit()
        await db_session.refresh(analyzer)

        # Act: receive 1 message
        result = await msg_service.receive_messages(
            agent_id=analyzer.agent_id,
            limit=1,
            tenant_key=tenant_key,
        )

        assert result.count == 1

        # Assert: healed to 1 (actual remaining)
        await db_session.refresh(analyzer)
        assert analyzer.messages_waiting_count == 1, (
            f"Expected self-healed waiting_count=1, got {analyzer.messages_waiting_count}"
        )

    async def test_receive_messages_counter_with_tenant_isolation(
        self,
        db_session,
        msg_service,
        project_with_messaging_agents,
        tenant_key,
        other_tenant_key,
    ):
        """Counter update filters by tenant_key, ensuring tenant isolation.

        A receive operation in tenant A must not affect counter values
        for agents in tenant B.
        """
        proj, agents, _jobs = project_with_messaging_agents
        orchestrator = agents[0]
        analyzer = agents[1]

        # Create a pending message for the analyzer in tenant A
        msg = Message(
            tenant_key=tenant_key,
            project_id=proj.id,
            content="Tenant A message",
            message_type="directive",
            status="pending",
            from_agent_id=str(orchestrator.agent_id),
        )
        db_session.add(msg)
        await db_session.flush()
        db_session.add(MessageRecipient(
            message_id=msg.id,
            agent_id=analyzer.agent_id,
            tenant_key=tenant_key,
        ))

        analyzer.messages_waiting_count = 1

        # Create a decoy execution in tenant B with same agent_id
        decoy_job = AgentJob(
            job_id=str(uuid.uuid4()),
            tenant_key=other_tenant_key,
            project_id=proj.id,
            job_type="analyzer",
            mission="Decoy analyzer in other tenant",
            status="active",
        )
        db_session.add(decoy_job)

        decoy_exec = AgentExecution(
            agent_id=analyzer.agent_id,  # Same agent_id as tenant A
            job_id=decoy_job.job_id,
            tenant_key=other_tenant_key,
            agent_display_name="analyzer",
            status="waiting",
            messages_sent_count=0,
            messages_waiting_count=5,  # Pre-set counter in tenant B
            messages_read_count=0,
        )
        db_session.add(decoy_exec)
        await db_session.commit()

        # Act: receive messages for tenant A
        result = await msg_service.receive_messages(
            agent_id=analyzer.agent_id,
            limit=10,
            tenant_key=tenant_key,
        )

        assert result.count == 1

        # Assert: tenant A counter updated correctly
        await db_session.refresh(analyzer)
        assert analyzer.messages_waiting_count == 0

        # Assert: tenant B decoy NOT affected
        await db_session.refresh(decoy_exec)
        assert decoy_exec.messages_waiting_count == 5, (
            f"Tenant B decoy waiting_count should remain 5 (untouched), "
            f"got {decoy_exec.messages_waiting_count}"
        )

    async def test_receive_messages_read_count_accumulates(
        self,
        db_session,
        msg_service,
        project_with_messaging_agents,
        tenant_key,
    ):
        """Multiple receive calls accumulate read_count correctly.

        read_count uses atomic INCREMENT (not SET), so successive
        receive calls should add to the running total.
        """
        proj, agents, _jobs = project_with_messaging_agents
        orchestrator = agents[0]
        analyzer = agents[1]

        # Create 4 pending messages
        for i in range(4):
            msg = Message(
                tenant_key=tenant_key,
                project_id=proj.id,
                content=f"Accumulation test message {i}",
                message_type="directive",
                status="pending",
                from_agent_id=str(orchestrator.agent_id),
            )
            db_session.add(msg)
            await db_session.flush()
            db_session.add(MessageRecipient(
                message_id=msg.id,
                agent_id=analyzer.agent_id,
                tenant_key=tenant_key,
            ))

        analyzer.messages_waiting_count = 4
        await db_session.commit()
        await db_session.refresh(analyzer)

        # Act: first receive (get 2 messages)
        result1 = await msg_service.receive_messages(
            agent_id=analyzer.agent_id,
            limit=2,
            tenant_key=tenant_key,
        )
        assert result1.count == 2

        await db_session.refresh(analyzer)
        assert analyzer.messages_read_count == 2
        assert analyzer.messages_waiting_count == 2  # 2 remaining

        # Act: second receive (get remaining 2)
        result2 = await msg_service.receive_messages(
            agent_id=analyzer.agent_id,
            limit=10,
            tenant_key=tenant_key,
        )
        assert result2.count == 2

        # Assert: read_count accumulated to 4
        await db_session.refresh(analyzer)
        assert analyzer.messages_read_count == 4, (
            f"Expected accumulated read_count=4, got {analyzer.messages_read_count}"
        )
        assert analyzer.messages_waiting_count == 0
