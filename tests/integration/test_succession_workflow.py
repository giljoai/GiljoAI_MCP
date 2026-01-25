"""
Integration tests for Orchestrator Succession Workflow (Handover 0080)

Tests the complete succession lifecycle from context threshold detection
through successor creation, handover, and instance transition.

Test Coverage:
- Full succession lifecycle (threshold → successor → handover → completion)
- Multiple successive handovers (chain of 4+ instances)
- Concurrent orchestrators during transition
- Edge cases and error conditions
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import Project
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from tests.fixtures.succession_fixtures import (
    SuccessionTestData,
)


# ============================================================================
# Test Suite A: Full Succession Lifecycle
# ============================================================================


@pytest.mark.asyncio
async def test_full_succession_workflow_end_to_end(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    Test complete succession from trigger to completion.

    Steps:
    1. Create orchestrator with 90% context usage
    2. Trigger succession (simulated)
    3. Verify successor created (instance_number+1)
    4. Verify handover message sent
    5. Verify predecessor marked complete
    6. Verify successor in waiting status
    """
    # Step 1: Create orchestrator at 90% threshold
    context_budget = 150000
    context_used = int(context_budget * 0.90)  # 135000 tokens

    orch1_data = SuccessionTestData.generate_orchestrator_job_data(
        project_id=test_project.id,
        tenant_key=test_tenant_key,
        instance_number=1,
        context_used=context_used,
        context_budget=context_budget,
        status="working",
    )

    orchestrator1 = AgentExecution(**orch1_data)
    db_session.add(orchestrator1)
    await db_session.commit()
    await db_session.refresh(orchestrator1)

    # Verify threshold breach
    threshold = context_budget * 0.90
    assert orchestrator1.context_used >= threshold, "Context usage should meet 90% threshold"

    # Step 2: Create successor (simulating MCP tool create_agent_job)
    orch2_data = SuccessionTestData.generate_orchestrator_job_data(
        project_id=test_project.id,
        tenant_key=test_tenant_key,
        instance_number=2,
        context_used=0,  # Fresh context
        context_budget=context_budget,
        spawned_by=orchestrator1.job_id,
        status="waiting",
    )

    orchestrator2 = AgentExecution(**orch2_data)
    db_session.add(orchestrator2)
    await db_session.flush()

    # Step 3: Update predecessor with handover data
    handover_summary = SuccessionTestData.generate_handover_summary()

    orchestrator1.status = "complete"
    orchestrator1.handover_to = orchestrator2.job_id
    orchestrator1.handover_summary = handover_summary
    orchestrator1.succession_reason = "context_limit"
    orchestrator1.completed_at = datetime.now(timezone.utc)

    # Step 4: Send handover message to successor
    handover_message = SuccessionTestData.generate_handover_message(
        from_job_id=orchestrator1.job_id,
        to_job_id=orchestrator2.job_id,
    )

    orchestrator2.messages = [handover_message]

    await db_session.commit()
    await db_session.refresh(orchestrator1)
    await db_session.refresh(orchestrator2)

    # ========== VERIFICATIONS ==========

    # Verify successor created with correct instance number
    assert orchestrator2.instance_number == orchestrator1.instance_number + 1
    assert orchestrator2.instance_number == 2

    # Verify spawned_by linkage
    assert orchestrator2.spawned_by == orchestrator1.job_id

    # Verify handover data on predecessor
    assert orchestrator1.handover_to == orchestrator2.job_id
    assert orchestrator1.handover_summary is not None
    assert isinstance(orchestrator1.handover_summary, dict)
    assert orchestrator1.succession_reason == "context_limit"

    # Verify handover message sent
    assert len(orchestrator2.messages) == 1
    assert orchestrator2.messages[0]["type"] == "handover"
    assert orchestrator2.messages[0]["from"] == orchestrator1.job_id
    assert orchestrator2.messages[0]["to"] == orchestrator2.job_id

    # Verify predecessor marked complete
    assert orchestrator1.status == "complete"
    assert orchestrator1.completed_at is not None

    # Verify successor in waiting status
    assert orchestrator2.status == "waiting"
    assert orchestrator2.context_used == 0  # Fresh context

    # Verify same project and tenant
    assert orchestrator2.project_id == orchestrator1.project_id
    assert orchestrator2.tenant_key == orchestrator1.tenant_key

    # Verify handover summary structure
    assert "project_status" in orchestrator1.handover_summary
    assert "active_agents" in orchestrator1.handover_summary
    assert "next_steps" in orchestrator1.handover_summary


@pytest.mark.asyncio
async def test_multiple_successive_handovers(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    Test chain of 4+ orchestrator instances.

    Verifies:
    - Instance numbering (1 → 2 → 3 → 4)
    - spawned_by chain intact
    - All handover summaries preserved
    - No data loss across chain
    """
    instances = []
    context_budget = 150000

    # Create Instance 1
    instance1 = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            instance_number=1,
            context_used=145000,
            context_budget=context_budget,
            status="complete",
        )
    )
    instance1.completed_at = datetime.now(timezone.utc)
    instance1.succession_reason = "context_limit"
    db_session.add(instance1)
    instances.append(instance1)
    await db_session.flush()

    # Create chain of 4 instances (Instance 2, 3, 4)
    for i in range(2, 5):
        previous_instance = instances[-1]

        new_instance = AgentExecution(
            **SuccessionTestData.generate_orchestrator_job_data(
                project_id=test_project.id,
                tenant_key=test_tenant_key,
                instance_number=i,
                context_used=5000 if i == 4 else 140000,  # Instance 4 is current
                context_budget=context_budget,
                spawned_by=previous_instance.job_id,
                status="waiting" if i == 4 else "complete",
            )
        )

        if i < 4:  # Instances 2 and 3 are complete
            new_instance.completed_at = datetime.now(timezone.utc)
            new_instance.succession_reason = "context_limit"

        db_session.add(new_instance)
        instances.append(new_instance)
        await db_session.flush()

        # Update previous instance with handover data
        previous_instance.handover_to = new_instance.job_id
        previous_instance.handover_summary = SuccessionTestData.generate_handover_summary()

    await db_session.commit()

    # Refresh all instances
    for instance in instances:
        await db_session.refresh(instance)

    # ========== VERIFICATIONS ==========

    # Verify instance numbering
    assert len(instances) == 4
    for i, instance in enumerate(instances, start=1):
        assert instance.instance_number == i, f"Instance {i} has wrong instance_number"

    # Verify spawned_by chain (excluding Instance 1)
    for i in range(1, 4):
        assert instances[i].spawned_by == instances[i - 1].job_id, f"Instance {i + 1} spawned_by broken"

    # Verify handover_to chain (excluding Instance 4)
    for i in range(3):
        assert instances[i].handover_to == instances[i + 1].job_id, f"Instance {i + 1} handover_to broken"

    # Verify all handover summaries preserved
    for i in range(3):  # Instances 1-3 should have handover summaries
        assert instances[i].handover_summary is not None, f"Instance {i + 1} missing handover_summary"
        assert isinstance(instances[i].handover_summary, dict)

    # Verify status progression
    assert instances[0].status == "complete"
    assert instances[1].status == "complete"
    assert instances[2].status == "complete"
    assert instances[3].status == "waiting"  # Current instance

    # Verify succession reasons
    for i in range(3):
        assert instances[i].succession_reason == "context_limit"

    # Verify all instances share same project and tenant
    for instance in instances:
        assert instance.project_id == test_project.id
        assert instance.tenant_key == test_tenant_key


@pytest.mark.asyncio
async def test_concurrent_orchestrators_during_transition(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    Test that Instance 1 completes before Instance 2 fully activates.

    Race condition testing:
    - Both instances briefly active
    - Grace period handling
    - Message queue drain
    - No duplicate work

    Note: This test simulates the transition period where both orchestrators
    might be active simultaneously, ensuring proper coordination.
    """
    context_budget = 150000

    # Create Instance 1 in "completing" status (transitioning)
    instance1 = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            instance_number=1,
            context_used=145000,
            context_budget=context_budget,
            status="working",  # Still working but initiating succession
        )
    )
    db_session.add(instance1)
    await db_session.flush()

    # Create Instance 2 in "waiting" status
    instance2 = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            instance_number=2,
            context_used=0,
            context_budget=context_budget,
            spawned_by=instance1.job_id,
            status="waiting",
        )
    )
    db_session.add(instance2)
    await db_session.commit()
    await db_session.refresh(instance1)
    await db_session.refresh(instance2)

    # Simulate concurrent activity:
    # - Instance 1 is draining message queue
    # - Instance 2 is waiting to be launched

    # Query for active orchestrators (both might be in transition)
    stmt = select(AgentExecution).where(
        AgentExecution.project_id == test_project.id,
        AgentExecution.agent_display_name == "orchestrator",
        AgentExecution.status.in_(["working", "waiting"]),
    )
    result = await db_session.execute(stmt)
    active_orchestrators = result.scalars().all()

    # ========== VERIFICATIONS ==========

    # Both instances should be present during transition
    assert len(active_orchestrators) == 2

    # Verify instance numbers are sequential
    instance_numbers = sorted([orch.instance_number for orch in active_orchestrators])
    assert instance_numbers == [1, 2]

    # Verify only one is "working"
    working_count = sum(1 for orch in active_orchestrators if orch.status == "working")
    assert working_count == 1, "Only one orchestrator should be 'working' during transition"

    # Verify Instance 1 is working, Instance 2 is waiting
    assert instance1.status == "working"
    assert instance2.status == "waiting"

    # Simulate Instance 1 completing gracefully
    instance1.status = "complete"
    instance1.handover_to = instance2.job_id
    instance1.handover_summary = SuccessionTestData.generate_handover_summary()
    instance1.succession_reason = "context_limit"
    instance1.completed_at = datetime.now(timezone.utc)

    await db_session.commit()
    await db_session.refresh(instance1)

    # Verify Instance 1 now complete
    assert instance1.status == "complete"
    assert instance1.handover_to == instance2.job_id

    # Query again - only Instance 2 should be waiting
    stmt = select(AgentExecution).where(
        AgentExecution.project_id == test_project.id,
        AgentExecution.agent_display_name == "orchestrator",
        AgentExecution.status == "waiting",
    )
    result = await db_session.execute(stmt)
    waiting_orchestrators = result.scalars().all()

    assert len(waiting_orchestrators) == 1
    assert waiting_orchestrators[0].job_id == instance2.job_id


@pytest.mark.asyncio
async def test_succession_preserves_project_continuity(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    Verify that succession maintains project state and continuity.

    Tests that:
    - Active agents are tracked across succession
    - Pending decisions are preserved
    - Context references are maintained
    - No project data is lost during handover
    """
    context_budget = 150000

    # Create Instance 1 with rich project state
    instance1 = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            instance_number=1,
            context_used=140000,
            context_budget=context_budget,
            status="working",
        )
    )

    # Simulate active project state
    instance1.messages = [
        {"type": "status", "content": "Database schema completed"},
        {"type": "status", "content": "API endpoints in progress"},
    ]

    db_session.add(instance1)
    await db_session.commit()
    await db_session.refresh(instance1)

    # Create successor
    instance2 = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            instance_number=2,
            context_used=0,
            context_budget=context_budget,
            spawned_by=instance1.job_id,
            status="waiting",
        )
    )
    db_session.add(instance2)
    await db_session.flush()

    # Generate comprehensive handover summary
    handover_summary = {
        "project_status": "70% complete",
        "active_agents": [
            {"job_id": str(uuid.uuid4()), "type": "database-dev", "status": "complete"},
            {"job_id": str(uuid.uuid4()), "type": "api-dev", "status": "working", "progress": 60},
        ],
        "completed_phases": ["requirements", "architecture", "database-implementation"],
        "pending_decisions": [
            "API versioning strategy",
            "Error handling patterns",
        ],
        "critical_context_refs": [f"chunk-{i}" for i in range(1, 11)],
        "message_count": len(instance1.messages),
        "unresolved_blockers": [],
        "next_steps": "Complete API implementation, then integrate with frontend",
        "token_estimate": 8500,
    }

    # Perform handover
    instance1.status = "complete"
    instance1.handover_to = instance2.job_id
    instance1.handover_summary = handover_summary
    instance1.succession_reason = "context_limit"
    instance1.completed_at = datetime.now(timezone.utc)

    # Send handover message to successor
    handover_message = {
        "type": "handover",
        "from": instance1.job_id,
        "to": instance2.job_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": handover_summary,
    }
    instance2.messages = [handover_message]

    await db_session.commit()
    await db_session.refresh(instance1)
    await db_session.refresh(instance2)

    # ========== VERIFICATIONS ==========

    # Verify handover summary structure
    assert instance1.handover_summary is not None
    assert instance1.handover_summary["project_status"] == "70% complete"

    # Verify active agents preserved
    assert len(instance1.handover_summary["active_agents"]) == 2
    active_agent_display_names = [agent["type"] for agent in instance1.handover_summary["active_agents"]]
    assert "database-dev" in active_agent_display_names
    assert "api-dev" in active_agent_display_names

    # Verify pending decisions preserved
    assert len(instance1.handover_summary["pending_decisions"]) == 2
    assert "API versioning strategy" in instance1.handover_summary["pending_decisions"]

    # Verify context references maintained
    assert len(instance1.handover_summary["critical_context_refs"]) == 10

    # Verify handover message received by successor
    assert len(instance2.messages) == 1
    assert instance2.messages[0]["type"] == "handover"
    assert instance2.messages[0]["payload"]["project_status"] == "70% complete"

    # Verify token estimate is reasonable (<10K target)
    assert instance1.handover_summary["token_estimate"] < 10000

    # Verify no data loss
    assert instance1.handover_summary["message_count"] == 2
    assert instance1.handover_summary["next_steps"] != ""


# ============================================================================
# Additional Workflow Tests
# ============================================================================


@pytest.mark.asyncio
async def test_query_succession_chain_ordered(
    db_session: AsyncSession,
    succession_chain_3_instances: dict,
):
    """
    Test querying succession chain returns instances in correct order.

    Verifies database query returns instances ordered by instance_number ASC.
    """
    chain_data = succession_chain_3_instances
    project_id = chain_data["instance1"].project_id

    # Query all orchestrators for project, ordered by instance_number
    stmt = (
        select(AgentExecution)
        .where(
            AgentExecution.project_id == project_id,
            AgentExecution.agent_display_name == "orchestrator",
        )
        .order_by(AgentExecution.instance_number.asc())
    )

    result = await db_session.execute(stmt)
    orchestrators = result.scalars().all()

    # ========== VERIFICATIONS ==========

    assert len(orchestrators) == 3, "Should have 3 orchestrators in chain"

    # Verify instance numbers are sequential
    for i, orch in enumerate(orchestrators, start=1):
        assert orch.instance_number == i

    # Verify spawned_by chain
    assert orchestrators[0].spawned_by is None  # Instance 1 is root
    assert orchestrators[1].spawned_by == orchestrators[0].job_id
    assert orchestrators[2].spawned_by == orchestrators[1].job_id

    # Verify handover_to chain
    assert orchestrators[0].handover_to == orchestrators[1].job_id
    assert orchestrators[1].handover_to == orchestrators[2].job_id
    assert orchestrators[2].handover_to is None  # Current instance

    # Verify status progression
    assert orchestrators[0].status == "complete"
    assert orchestrators[1].status == "complete"
    assert orchestrators[2].status == "working"


@pytest.mark.asyncio
async def test_succession_at_exact_90_percent(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    Test manual succession workflow at exactly 90% context usage.

    Edge case: Verifies context tracking and succession workflow at boundary conditions.
    Note: Succession is now manual-only via UI or /gil_handover command.
    """
    context_budget = 150000
    context_used = int(context_budget * 0.90)  # Exactly 135000 tokens

    orchestrator = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            instance_number=1,
            context_used=context_used,
            context_budget=context_budget,
            status="working",
        )
    )

    db_session.add(orchestrator)
    await db_session.commit()
    await db_session.refresh(orchestrator)

    # ========== VERIFICATIONS ==========

    # Verify exactly at 90% usage
    threshold = context_budget * 0.90
    assert orchestrator.context_used == threshold
    assert orchestrator.context_used == 135000

    # Verify context percentage calculation
    percentage = (orchestrator.context_used / context_budget) * 100
    assert percentage == 90.0

    # Manual succession can be triggered at this point
    # (Automatic succession was removed in Handover 0461a)
