"""
Integration tests for message counter persistence.

Handover 0484 - Validates that message counter columns on AgentExecution
persist correctly across session operations.

Counter columns (Handover 0700c - replaced JSONB messages):
- messages_sent_count: Integer, default 0
- messages_waiting_count: Integer, default 0
- messages_read_count: Integer, default 0

Tests verify:
1. Counter columns persist after session expire/refresh
2. Counter values are correctly stored and retrieved
3. Multiple agents maintain independent counters
4. Counter columns default to 0 on new AgentExecution
"""

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project


@pytest.mark.asyncio
async def test_counter_columns_persist_after_refresh(db_session: AsyncSession):
    """
    Test that counter columns persist correctly after session expire and refresh.
    """
    tenant_key = f"test_tenant_{uuid4().hex[:8]}"

    product = Product(
        name="Counter Persist Product",
        tenant_key=tenant_key,
        product_memory={},
    )
    db_session.add(product)
    await db_session.flush()

    project = Project(
        name="Counter Persist Project",
        description="Test project for counter persistence",
        mission="Test counter persistence",
        tenant_key=tenant_key,
        product_id=product.id,
        status="active",
    )
    db_session.add(project)
    await db_session.flush()

    job = AgentJob(
        job_id=str(uuid4()),
        tenant_key=tenant_key,
        project_id=project.id,
        job_type="orchestrator",
        mission="Test counter persistence",
        status="active",
    )
    db_session.add(job)
    await db_session.flush()

    execution = AgentExecution(
        job_id=job.job_id,
        tenant_key=tenant_key,
        agent_display_name="orchestrator",
        status="working",
        messages_sent_count=5,
        messages_waiting_count=3,
        messages_read_count=7,
    )
    db_session.add(execution)
    await db_session.commit()

    # Expire all cached state and refresh from database
    db_session.expire_all()
    await db_session.refresh(execution)

    assert execution.messages_sent_count == 5, (
        f"sent_count should be 5, got {execution.messages_sent_count}"
    )
    assert execution.messages_waiting_count == 3, (
        f"waiting_count should be 3, got {execution.messages_waiting_count}"
    )
    assert execution.messages_read_count == 7, (
        f"read_count should be 7, got {execution.messages_read_count}"
    )


@pytest.mark.asyncio
async def test_counter_columns_default_to_zero(db_session: AsyncSession):
    """
    Test that counter columns default to 0 when not explicitly set.
    """
    tenant_key = f"test_tenant_{uuid4().hex[:8]}"

    product = Product(
        name="Default Counter Product",
        tenant_key=tenant_key,
        product_memory={},
    )
    db_session.add(product)
    await db_session.flush()

    project = Project(
        name="Default Counter Project",
        description="Test default counter values",
        mission="Test default counters",
        tenant_key=tenant_key,
        product_id=product.id,
        status="active",
    )
    db_session.add(project)
    await db_session.flush()

    job = AgentJob(
        job_id=str(uuid4()),
        tenant_key=tenant_key,
        project_id=project.id,
        job_type="implementer",
        mission="Test default counters",
        status="active",
    )
    db_session.add(job)
    await db_session.flush()

    # Create execution WITHOUT setting counter values
    execution = AgentExecution(
        job_id=job.job_id,
        tenant_key=tenant_key,
        agent_display_name="implementer",
        status="waiting",
    )
    db_session.add(execution)
    await db_session.commit()

    await db_session.refresh(execution)

    assert execution.messages_sent_count == 0, (
        f"Default sent_count should be 0, got {execution.messages_sent_count}"
    )
    assert execution.messages_waiting_count == 0, (
        f"Default waiting_count should be 0, got {execution.messages_waiting_count}"
    )
    assert execution.messages_read_count == 0, (
        f"Default read_count should be 0, got {execution.messages_read_count}"
    )


@pytest.mark.asyncio
async def test_multiple_agents_independent_counters(db_session: AsyncSession):
    """
    Test that multiple agents in the same project maintain independent counters.

    Simulates orchestrator sending messages to implementer and tester,
    each with different counter states.
    """
    tenant_key = f"test_tenant_{uuid4().hex[:8]}"

    product = Product(
        name="Multi Agent Product",
        tenant_key=tenant_key,
        product_memory={},
    )
    db_session.add(product)
    await db_session.flush()

    project = Project(
        name="Multi Agent Project",
        description="Test independent counters",
        mission="Test multi-agent counters",
        tenant_key=tenant_key,
        product_id=product.id,
        status="active",
    )
    db_session.add(project)
    await db_session.flush()

    # Create orchestrator (sender - 2 sent, 0 waiting, 0 read)
    orch_job = AgentJob(
        job_id=str(uuid4()),
        tenant_key=tenant_key,
        project_id=project.id,
        job_type="orchestrator",
        mission="Orchestrate project",
        status="active",
    )
    db_session.add(orch_job)
    await db_session.flush()

    orchestrator = AgentExecution(
        job_id=orch_job.job_id,
        tenant_key=tenant_key,
        agent_display_name="orchestrator",
        status="working",
        messages_sent_count=2,
        messages_waiting_count=0,
        messages_read_count=0,
    )

    # Create implementer (0 sent, 1 waiting, 0 read)
    impl_job = AgentJob(
        job_id=str(uuid4()),
        tenant_key=tenant_key,
        project_id=project.id,
        job_type="implementer",
        mission="Implement features",
        status="active",
    )
    db_session.add(impl_job)
    await db_session.flush()

    implementer = AgentExecution(
        job_id=impl_job.job_id,
        tenant_key=tenant_key,
        agent_display_name="implementer",
        status="waiting",
        messages_sent_count=0,
        messages_waiting_count=1,
        messages_read_count=0,
    )

    # Create tester (0 sent, 0 waiting, 1 read)
    tester_job = AgentJob(
        job_id=str(uuid4()),
        tenant_key=tenant_key,
        project_id=project.id,
        job_type="tester",
        mission="Run tests",
        status="active",
    )
    db_session.add(tester_job)
    await db_session.flush()

    tester = AgentExecution(
        job_id=tester_job.job_id,
        tenant_key=tenant_key,
        agent_display_name="tester",
        status="waiting",
        messages_sent_count=0,
        messages_waiting_count=0,
        messages_read_count=1,
    )

    db_session.add_all([orchestrator, implementer, tester])
    await db_session.commit()

    # Simulate page refresh - expire and re-query from database
    db_session.expire_all()

    result = await db_session.execute(
        select(AgentExecution)
        .where(AgentExecution.tenant_key == tenant_key)
        .order_by(AgentExecution.agent_display_name)
    )
    refreshed_agents = result.scalars().all()

    assert len(refreshed_agents) == 3, (
        f"Should find 3 agents, found {len(refreshed_agents)}"
    )

    # Find agents by display name
    orch = next(a for a in refreshed_agents if a.agent_display_name == "orchestrator")
    impl = next(a for a in refreshed_agents if a.agent_display_name == "implementer")
    test_agent = next(a for a in refreshed_agents if a.agent_display_name == "tester")

    # Verify orchestrator counters
    assert orch.messages_sent_count == 2, (
        f"Orchestrator sent should be 2, got {orch.messages_sent_count}"
    )
    assert orch.messages_waiting_count == 0
    assert orch.messages_read_count == 0

    # Verify implementer counters
    assert impl.messages_sent_count == 0
    assert impl.messages_waiting_count == 1, (
        f"Implementer waiting should be 1, got {impl.messages_waiting_count}"
    )
    assert impl.messages_read_count == 0

    # Verify tester counters
    assert test_agent.messages_sent_count == 0
    assert test_agent.messages_waiting_count == 0
    assert test_agent.messages_read_count == 1, (
        f"Tester read should be 1, got {test_agent.messages_read_count}"
    )


@pytest.mark.asyncio
async def test_counter_query_by_tenant_key(db_session: AsyncSession):
    """
    Test that counter queries filter correctly by tenant_key.

    Agents with waiting messages should be found only within their tenant.
    """
    tenant_key_a = f"test_tenant_a_{uuid4().hex[:8]}"
    tenant_key_b = f"test_tenant_b_{uuid4().hex[:8]}"

    # Create hierarchy for tenant A
    product_a = Product(
        name="Product A Counter",
        tenant_key=tenant_key_a,
        product_memory={},
    )
    db_session.add(product_a)
    await db_session.flush()

    project_a = Project(
        name="Project A Counter",
        description="Tenant A counter test",
        mission="Test A",
        tenant_key=tenant_key_a,
        product_id=product_a.id,
        status="active",
    )
    db_session.add(project_a)
    await db_session.flush()

    job_a = AgentJob(
        job_id=str(uuid4()),
        tenant_key=tenant_key_a,
        project_id=project_a.id,
        job_type="implementer",
        mission="Agent A",
        status="active",
    )
    db_session.add(job_a)
    await db_session.flush()

    # Agent A: has waiting messages
    agent_a = AgentExecution(
        job_id=job_a.job_id,
        tenant_key=tenant_key_a,
        agent_display_name="implementer",
        status="working",
        messages_waiting_count=3,
    )

    # Create hierarchy for tenant B
    product_b = Product(
        name="Product B Counter",
        tenant_key=tenant_key_b,
        product_memory={},
    )
    db_session.add(product_b)
    await db_session.flush()

    project_b = Project(
        name="Project B Counter",
        description="Tenant B counter test",
        mission="Test B",
        tenant_key=tenant_key_b,
        product_id=product_b.id,
        status="active",
    )
    db_session.add(project_b)
    await db_session.flush()

    job_b = AgentJob(
        job_id=str(uuid4()),
        tenant_key=tenant_key_b,
        project_id=project_b.id,
        job_type="tester",
        mission="Agent B",
        status="active",
    )
    db_session.add(job_b)
    await db_session.flush()

    # Agent B: no waiting messages
    agent_b = AgentExecution(
        job_id=job_b.job_id,
        tenant_key=tenant_key_b,
        agent_display_name="tester",
        status="working",
        messages_waiting_count=0,
    )

    db_session.add_all([agent_a, agent_b])
    await db_session.commit()

    # Query agents with waiting messages in tenant A only
    result = await db_session.execute(
        select(AgentExecution).where(
            AgentExecution.tenant_key == tenant_key_a,
            AgentExecution.messages_waiting_count > 0,
        )
    )
    agents_with_waiting = result.scalars().all()

    assert len(agents_with_waiting) == 1, (
        f"Should find 1 agent with waiting messages in tenant A, found {len(agents_with_waiting)}"
    )
    assert agents_with_waiting[0].tenant_key == tenant_key_a
    assert agents_with_waiting[0].messages_waiting_count == 3

    # Verify tenant B query returns no agents with waiting messages
    result_b = await db_session.execute(
        select(AgentExecution).where(
            AgentExecution.tenant_key == tenant_key_b,
            AgentExecution.messages_waiting_count > 0,
        )
    )
    agents_b_waiting = result_b.scalars().all()
    assert len(agents_b_waiting) == 0, (
        "Should find 0 agents with waiting messages in tenant B"
    )


@pytest.mark.asyncio
async def test_counter_update_and_requery(db_session: AsyncSession):
    """
    Test updating counters and re-querying to verify persistence.

    Simulates the full lifecycle: initial state -> increment -> verify -> decrement -> verify.
    """
    tenant_key = f"test_tenant_{uuid4().hex[:8]}"

    product = Product(
        name="Update Requery Product",
        tenant_key=tenant_key,
        product_memory={},
    )
    db_session.add(product)
    await db_session.flush()

    project = Project(
        name="Update Requery Project",
        description="Test counter update and requery",
        mission="Test lifecycle",
        tenant_key=tenant_key,
        product_id=product.id,
        status="active",
    )
    db_session.add(project)
    await db_session.flush()

    job = AgentJob(
        job_id=str(uuid4()),
        tenant_key=tenant_key,
        project_id=project.id,
        job_type="implementer",
        mission="Test lifecycle",
        status="active",
    )
    db_session.add(job)
    await db_session.flush()

    execution = AgentExecution(
        job_id=job.job_id,
        tenant_key=tenant_key,
        agent_display_name="implementer",
        status="working",
        messages_sent_count=0,
        messages_waiting_count=0,
        messages_read_count=0,
    )
    db_session.add(execution)
    await db_session.commit()

    agent_id = execution.agent_id

    # Step 1: Simulate sending (increment sent_count)
    execution.messages_sent_count += 2
    await db_session.commit()

    db_session.expire_all()
    result = await db_session.execute(
        select(AgentExecution).where(AgentExecution.agent_id == agent_id)
    )
    refreshed = result.scalar_one()
    assert refreshed.messages_sent_count == 2

    # Step 2: Simulate receiving messages (increment waiting_count)
    refreshed.messages_waiting_count += 3
    await db_session.commit()

    db_session.expire_all()
    result = await db_session.execute(
        select(AgentExecution).where(AgentExecution.agent_id == agent_id)
    )
    refreshed = result.scalar_one()
    assert refreshed.messages_waiting_count == 3

    # Step 3: Simulate reading (decrement waiting, increment read)
    refreshed.messages_waiting_count -= 2
    refreshed.messages_read_count += 2
    await db_session.commit()

    db_session.expire_all()
    result = await db_session.execute(
        select(AgentExecution).where(AgentExecution.agent_id == agent_id)
    )
    refreshed = result.scalar_one()
    assert refreshed.messages_waiting_count == 1, (
        f"Should have 1 waiting after reading 2 of 3, got {refreshed.messages_waiting_count}"
    )
    assert refreshed.messages_read_count == 2, (
        f"Should have 2 read, got {refreshed.messages_read_count}"
    )
    assert refreshed.messages_sent_count == 2, (
        f"Sent count should remain 2, got {refreshed.messages_sent_count}"
    )
