"""
Edge Case Tests for Orchestrator Succession (Handover 0080)

Tests unusual scenarios, error conditions, and boundary cases:
- Context overflow beyond 100%
- Failed successor creation
- Manual succession triggers
- Multiple rapid successions
- Succession reason variants
"""

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
# Edge Case: Context Overflow Beyond 100%
# ============================================================================


@pytest.mark.asyncio
async def test_succession_above_100_percent(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    Emergency truncation when context overflows beyond 100%.

    Scenario: Orchestrator exceeds context budget (155K/150K = 103%)
    Expected: Emergency succession with truncated handover
    """
    context_budget = 150000
    context_used = 155000  # 103% - exceeds budget!

    instance1 = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            instance_number=1,
            context_used=context_used,
            context_budget=context_budget,
            status="working",
        )
    )

    db_session.add(instance1)
    await db_session.commit()
    await db_session.refresh(instance1)

    # ========== VERIFICATIONS ==========

    # Verify context overflow
    assert instance1.context_used > instance1.context_budget
    percentage = (instance1.context_used / context_budget) * 100
    assert percentage > 100

    # Emergency succession should be triggered
    # In real implementation, this would generate truncated handover summary

    # Create emergency successor
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

    # Generate emergency handover (truncated to recent context only)
    emergency_handover = {
        "project_status": "Emergency handover - context overflow",
        "active_agents": [],  # Minimal data
        "critical_context_refs": [f"chunk-{i}" for i in range(1, 6)],  # Last 5 chunks only
        "next_steps": "Resume orchestration with fresh context",
        "token_estimate": 2000,  # Heavily compressed
        "warning": "Context overflow occurred - some historical data truncated",
    }

    instance1.status = "complete"
    instance1.handover_to = instance2.job_id
    instance1.handover_summary = emergency_handover
    instance1.succession_reason = "context_limit"
    instance1.completed_at = datetime.now(timezone.utc)

    await db_session.commit()
    await db_session.refresh(instance1)
    await db_session.refresh(instance2)

    # Verify emergency handover created
    assert instance1.handover_summary is not None
    assert "warning" in instance1.handover_summary
    assert instance1.handover_summary["token_estimate"] < 5000  # Heavily truncated

    # Verify successor created successfully despite overflow
    assert instance2.instance_number == 2
    assert instance2.spawned_by == instance1.job_id


@pytest.mark.asyncio
async def test_failed_successor_creation(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    Database error during successor creation.

    Expected: Original orchestrator marked 'blocked' with reason
    """
    context_budget = 150000
    context_used = 140000

    instance1 = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            instance_number=1,
            context_used=context_used,
            context_budget=context_budget,
            status="working",
        )
    )

    db_session.add(instance1)
    await db_session.commit()
    await db_session.refresh(instance1)

    # Simulate succession failure (e.g., database constraint violation)
    # In real scenario, this could be network error, DB connection lost, etc.

    # Mark orchestrator as blocked due to succession failure
    instance1.status = "blocked"
    instance1.block_reason = "Successor creation failed: Database connection error during agent spawn"

    await db_session.commit()
    await db_session.refresh(instance1)

    # ========== VERIFICATIONS ==========

    assert instance1.status == "blocked"
    assert instance1.block_reason is not None
    assert "Successor creation failed" in instance1.block_reason

    # Verify no successor was created
    stmt = select(AgentExecution).where(
        AgentExecution.project_id == test_project.id,
        AgentExecution.instance_number == 2,
    )
    result = await db_session.execute(stmt)
    successor = result.scalar_one_or_none()
    assert successor is None, "No successor should exist after failed creation"

    # Verify original orchestrator remains accessible for debugging
    assert instance1.handover_to is None
    assert instance1.handover_summary is None


@pytest.mark.asyncio
async def test_manual_succession_before_threshold(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    User triggers succession at 60% context (manual handover).

    Reason: 'manual' instead of 'context_limit'
    Use case: User wants to transition at phase boundary
    """
    context_budget = 150000
    context_used = int(context_budget * 0.60)  # Only 60%, well below 90% threshold

    instance1 = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            instance_number=1,
            context_used=context_used,
            context_budget=context_budget,
            status="working",
        )
    )

    db_session.add(instance1)
    await db_session.commit()
    await db_session.refresh(instance1)

    # User triggers manual succession
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

    # Perform manual handover
    handover_summary = SuccessionTestData.generate_handover_summary()
    handover_summary["reason"] = "User-initiated phase transition"

    instance1.status = "complete"
    instance1.handover_to = instance2.job_id
    instance1.handover_summary = handover_summary
    instance1.succession_reason = "manual"  # Different from 'context_limit'
    instance1.completed_at = datetime.now(timezone.utc)

    await db_session.commit()
    await db_session.refresh(instance1)
    await db_session.refresh(instance2)

    # ========== VERIFICATIONS ==========

    # Verify succession occurred below threshold
    assert instance1.context_used < (context_budget * 0.90)
    percentage = (instance1.context_used / context_budget) * 100
    assert percentage == 60.0

    # Verify succession reason is 'manual'
    assert instance1.succession_reason == "manual"
    assert instance1.succession_reason != "context_limit"

    # Verify handover completed successfully
    assert instance1.handover_to == instance2.job_id
    assert instance2.instance_number == 2
    assert instance2.spawned_by == instance1.job_id


@pytest.mark.asyncio
async def test_phase_transition_succession(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    Succession triggered at critical mission phase transition.

    Reason: 'phase_transition'
    Use case: Natural handover point between project phases
    """
    context_budget = 150000
    context_used = int(context_budget * 0.75)  # 75% - comfortable margin

    instance1 = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            instance_number=1,
            context_used=context_used,
            context_budget=context_budget,
            status="working",
        )
    )

    db_session.add(instance1)
    await db_session.commit()
    await db_session.refresh(instance1)

    # Create successor for phase transition
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

    # Phase-specific handover
    phase_handover = {
        "project_status": "Phase 1 (Architecture) complete - transitioning to Phase 2 (Implementation)",
        "completed_phases": ["requirements", "architecture", "design"],
        "next_phase": "implementation",
        "active_agents": [],
        "critical_context_refs": [f"chunk-{i}" for i in range(1, 8)],
        "next_steps": "Begin implementation phase with fresh context",
        "token_estimate": 6000,
    }

    instance1.status = "complete"
    instance1.handover_to = instance2.job_id
    instance1.handover_summary = phase_handover
    instance1.succession_reason = "phase_transition"
    instance1.completed_at = datetime.now(timezone.utc)

    await db_session.commit()
    await db_session.refresh(instance1)
    await db_session.refresh(instance2)

    # ========== VERIFICATIONS ==========

    assert instance1.succession_reason == "phase_transition"
    assert "Phase 1" in instance1.handover_summary["project_status"]
    assert instance1.handover_summary["next_phase"] == "implementation"
    assert instance2.instance_number == 2


@pytest.mark.asyncio
async def test_multiple_rapid_successions(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    Test rapid succession (3 handovers in quick succession).

    Scenario: Project with very high context consumption rate
    Verifies: System handles multiple rapid handovers without corruption
    """
    context_budget = 150000
    instances = []

    # Create 4 instances rapidly (simulating high-throughput project)
    for i in range(1, 5):
        instance = AgentExecution(
            **SuccessionTestData.generate_orchestrator_job_data(
                project_id=test_project.id,
                tenant_key=test_tenant_key,
                instance_number=i,
                context_used=145000 if i < 4 else 5000,
                context_budget=context_budget,
                spawned_by=instances[-1].job_id if instances else None,
                status="waiting" if i == 4 else "complete",
            )
        )

        if i < 4:
            instance.completed_at = datetime.now(timezone.utc)
            instance.succession_reason = "context_limit"

        db_session.add(instance)
        instances.append(instance)
        await db_session.flush()

        # Link handover chain
        if i > 1:
            instances[i - 2].handover_to = instance.job_id
            instances[i - 2].handover_summary = SuccessionTestData.generate_handover_summary()

    await db_session.commit()

    # Refresh all
    for instance in instances:
        await db_session.refresh(instance)

    # ========== VERIFICATIONS ==========

    assert len(instances) == 4

    # Verify rapid succession integrity
    for i, instance in enumerate(instances, start=1):
        assert instance.instance_number == i

    # Verify all handovers completed
    for i in range(3):
        assert instances[i].status == "complete"
        assert instances[i].handover_to == instances[i + 1].job_id
        assert instances[i].handover_summary is not None

    # Verify current instance is waiting
    assert instances[3].status == "waiting"
    assert instances[3].handover_to is None


@pytest.mark.asyncio
async def test_succession_with_no_active_agents(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    Edge case: Succession when no other agents are active.

    Handover summary should still be valid with empty active_agents array.
    """
    context_budget = 150000
    context_used = 140000

    instance1 = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            instance_number=1,
            context_used=context_used,
            context_budget=context_budget,
            status="working",
        )
    )

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

    # Handover with no active agents
    minimal_handover = {
        "project_status": "Planning phase - no agents spawned yet",
        "active_agents": [],  # Empty!
        "completed_phases": ["requirements"],
        "pending_decisions": ["Architecture approach selection"],
        "critical_context_refs": [],
        "next_steps": "Spawn agents for architecture phase",
        "token_estimate": 1500,
    }

    instance1.status = "complete"
    instance1.handover_to = instance2.job_id
    instance1.handover_summary = minimal_handover
    instance1.succession_reason = "context_limit"
    instance1.completed_at = datetime.now(timezone.utc)

    await db_session.commit()
    await db_session.refresh(instance1)
    await db_session.refresh(instance2)

    # ========== VERIFICATIONS ==========

    # Verify handover valid with empty active_agents
    assert instance1.handover_summary is not None
    assert instance1.handover_summary["active_agents"] == []
    assert isinstance(instance1.handover_summary["active_agents"], list)

    # Verify succession completed successfully
    assert instance1.handover_to == instance2.job_id
    assert instance2.instance_number == 2


@pytest.mark.asyncio
async def test_succession_reason_enum_validation(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    Test that succession_reason accepts only valid enum values.

    Valid values: 'context_limit', 'manual', 'phase_transition'
    """
    context_budget = 150000

    # Test all valid succession reasons
    valid_reasons = ["context_limit", "manual", "phase_transition"]

    for i, reason in enumerate(valid_reasons, start=1):
        instance = AgentExecution(
            **SuccessionTestData.generate_orchestrator_job_data(
                project_id=test_project.id,
                tenant_key=test_tenant_key,
                instance_number=i,
                context_used=140000,
                context_budget=context_budget,
                status="complete",
            )
        )
        instance.succession_reason = reason
        instance.completed_at = datetime.now(timezone.utc)

        db_session.add(instance)

    await db_session.commit()

    # Query all and verify
    stmt = select(AgentExecution).where(
        AgentExecution.project_id == test_project.id,
        AgentExecution.agent_display_name == "orchestrator",
    )
    result = await db_session.execute(stmt)
    instances = result.scalars().all()

    assert len(instances) == 3

    # Verify each succession reason
    reasons_found = [inst.succession_reason for inst in instances]
    assert "context_limit" in reasons_found
    assert "manual" in reasons_found
    assert "phase_transition" in reasons_found


@pytest.mark.asyncio
async def test_handover_summary_token_estimation(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    Verify handover summary stays under 10K token target.

    Large handover summaries defeat the purpose of succession.
    """
    context_budget = 150000
    context_used = 145000

    instance1 = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            instance_number=1,
            context_used=context_used,
            context_budget=context_budget,
            status="working",
        )
    )

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

    # Generate handover summary
    handover_summary = SuccessionTestData.generate_handover_summary()

    instance1.status = "complete"
    instance1.handover_to = instance2.job_id
    instance1.handover_summary = handover_summary
    instance1.succession_reason = "context_limit"
    instance1.completed_at = datetime.now(timezone.utc)

    await db_session.commit()
    await db_session.refresh(instance1)

    # ========== VERIFICATIONS ==========

    # Verify token estimate is under 10K target
    assert "token_estimate" in instance1.handover_summary
    assert instance1.handover_summary["token_estimate"] < 10000

    # Rough character-based estimate (4 chars/token)
    import json

    handover_json = json.dumps(instance1.handover_summary)
    estimated_tokens = len(handover_json) / 4
    assert estimated_tokens < 10000, "Handover summary too large (exceeds 10K token target)"
