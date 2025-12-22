"""
Performance Tests for Orchestrator Succession (Handover 0080)

Tests performance characteristics of succession operations:
- Succession latency (<5 seconds target)
- Handover summary token size (<10K target)
- Succession query performance (<100ms)
- Concurrent succession handling
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import Project
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from tests.fixtures.succession_fixtures import SuccessionTestData


# ============================================================================
# Performance Tests
# ============================================================================


@pytest.mark.asyncio
async def test_succession_latency_under_5_seconds(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    Create successor in <5s (target from handover doc).

    Measures time from Instance 1 completion to Instance 2 creation.
    """
    # Create Instance 1
    instance1 = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            instance_number=1,
            context_used=140000,
            context_budget=150000,
            status="working",
        )
    )

    db_session.add(instance1)
    await db_session.commit()
    await db_session.refresh(instance1)

    # Measure succession time
    start_time = time.perf_counter()

    # Create successor
    instance2 = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            instance_number=2,
            context_used=0,
            context_budget=150000,
            spawned_by=instance1.job_id,
            status="waiting",
        )
    )

    db_session.add(instance2)
    await db_session.flush()

    # Complete handover
    handover_summary = SuccessionTestData.generate_handover_summary()

    instance1.status = "complete"
    instance1.handover_to = instance2.job_id
    instance1.handover_summary = handover_summary
    instance1.succession_reason = "context_limit"
    instance1.completed_at = datetime.now(timezone.utc)

    # Send handover message
    handover_message = SuccessionTestData.generate_handover_message(
        from_job_id=instance1.job_id,
        to_job_id=instance2.job_id,
    )
    instance2.messages = [handover_message]

    await db_session.commit()

    end_time = time.perf_counter()
    latency_seconds = end_time - start_time

    # ========== VERIFICATIONS ==========

    # Target: <5 seconds (database operations should be fast)
    assert latency_seconds < 5.0, f"Succession took {latency_seconds:.2f}s (target: <5s)"

    # Log actual latency for monitoring
    print(f"\n✓ Succession latency: {latency_seconds:.3f}s")


@pytest.mark.asyncio
async def test_handover_summary_under_10k_tokens(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    Token count estimation for handover summary (<10K target).

    Uses character-based estimation (4 chars ≈ 1 token).
    """
    instance = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            instance_number=1,
            context_used=140000,
            context_budget=150000,
            status="complete",
        )
    )

    # Generate handover summary
    handover_summary = SuccessionTestData.generate_handover_summary()
    instance.handover_summary = handover_summary
    instance.succession_reason = "context_limit"
    instance.completed_at = datetime.now(timezone.utc)

    db_session.add(instance)
    await db_session.commit()
    await db_session.refresh(instance)

    # ========== VERIFICATIONS ==========

    # Serialize to JSON
    handover_json = json.dumps(instance.handover_summary)
    char_count = len(handover_json)

    # Estimate tokens (rough: 4 chars per token)
    estimated_tokens = char_count / 4

    assert estimated_tokens < 10000, f"Handover summary: {estimated_tokens:.0f} tokens (target: <10K)"

    # Verify explicit token_estimate field
    if "token_estimate" in instance.handover_summary:
        assert instance.handover_summary["token_estimate"] < 10000

    print(f"\n✓ Handover summary size: {estimated_tokens:.0f} tokens ({char_count} chars)")


@pytest.mark.asyncio
async def test_succession_query_performance(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    GET /succession_chain executes in <100ms.

    Query all orchestrators for project ordered by instance_number.
    """
    # Create chain of 10 instances
    for i in range(1, 11):
        instance = AgentExecution(
            **SuccessionTestData.generate_orchestrator_job_data(
                project_id=test_project.id,
                tenant_key=test_tenant_key,
                instance_number=i,
                context_used=50000,
                context_budget=150000,
                status="waiting",
            )
        )
        db_session.add(instance)

    await db_session.commit()

    # Measure query performance
    start_time = time.perf_counter()

    stmt = (
        select(AgentExecution)
        .where(
            AgentExecution.project_id == test_project.id,
            AgentExecution.tenant_key == test_tenant_key,
            AgentExecution.agent_type == "orchestrator",
        )
        .order_by(AgentExecution.instance_number.asc())
    )

    result = await db_session.execute(stmt)
    orchestrators = result.scalars().all()

    end_time = time.perf_counter()
    query_time_ms = (end_time - start_time) * 1000

    # ========== VERIFICATIONS ==========

    assert len(orchestrators) == 10

    # Target: <100ms (should be much faster with indexes)
    assert query_time_ms < 100, f"Query took {query_time_ms:.2f}ms (target: <100ms)"

    print(f"\n✓ Succession chain query: {query_time_ms:.2f}ms")


@pytest.mark.asyncio
async def test_concurrent_successions_different_projects(
    db_session: AsyncSession,
    test_tenant_key: str,
):
    """
    10 projects triggering succession simultaneously.

    No deadlocks, no race conditions.
    """
    # Create 10 projects
    projects = []
    for i in range(10):
        project = Project(
            id=str(uuid.uuid4()),
            name=f"Concurrent Project {i}",
            mission=f"Project {i}",
            status="active",
            tenant_key=test_tenant_key,
        )
        db_session.add(project)
        projects.append(project)

    await db_session.commit()

    # Create orchestrator for each project
    orchestrators = []
    for project in projects:
        orch = AgentExecution(
            **SuccessionTestData.generate_orchestrator_job_data(
                project_id=project.id,
                tenant_key=test_tenant_key,
                instance_number=1,
                context_used=135000,
                context_budget=150000,
                status="working",
            )
        )
        db_session.add(orch)
        orchestrators.append(orch)

    await db_session.commit()

    # Measure concurrent succession performance
    start_time = time.perf_counter()

    # Simulate concurrent successions
    async def create_succession(orch):
        successor = AgentExecution(
            **SuccessionTestData.generate_orchestrator_job_data(
                project_id=orch.project_id,
                tenant_key=test_tenant_key,
                instance_number=2,
                context_used=0,
                context_budget=150000,
                spawned_by=orch.job_id,
                status="waiting",
            )
        )
        db_session.add(successor)
        await db_session.flush()

        orch.status = "complete"
        orch.handover_to = successor.job_id
        orch.handover_summary = SuccessionTestData.generate_handover_summary()
        orch.succession_reason = "context_limit"
        orch.completed_at = datetime.now(timezone.utc)

    # Execute concurrently
    await asyncio.gather(*[create_succession(orch) for orch in orchestrators])

    await db_session.commit()

    end_time = time.perf_counter()
    total_time_seconds = end_time - start_time

    # ========== VERIFICATIONS ==========

    # Verify all successions completed
    stmt = select(AgentExecution).where(
        AgentExecution.tenant_key == test_tenant_key,
        AgentExecution.agent_type == "orchestrator",
    )
    result = await db_session.execute(stmt)
    all_orchestrators = result.scalars().all()

    # Should have 20 orchestrators (10 original + 10 successors)
    assert len(all_orchestrators) == 20

    # Verify no failures (all completed or waiting)
    statuses = [o.status for o in all_orchestrators]
    assert all(s in ["complete", "waiting"] for s in statuses)

    print(f"\n✓ Concurrent successions: {total_time_seconds:.2f}s for 10 projects")


@pytest.mark.asyncio
async def test_large_handover_summary_performance(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    Test serialization performance of large (but under 10K) handover summary.
    """
    instance = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            instance_number=1,
            context_used=140000,
            context_budget=150000,
            status="complete",
        )
    )

    # Generate large handover summary
    large_summary = {
        "project_status": "75% complete - large project with extensive history",
        "active_agents": [
            {"job_id": str(uuid.uuid4()), "type": f"agent-{i}", "status": "working", "progress": 50}
            for i in range(20)  # 20 active agents
        ],
        "completed_phases": [f"phase-{i}" for i in range(50)],  # 50 completed phases
        "pending_decisions": [f"Decision {i}: Choose implementation approach" for i in range(30)],
        "critical_context_refs": [f"chunk-{i}" for i in range(100)],  # 100 context refs
        "message_count": 500,
        "next_steps": "Proceed with remaining implementation tasks" * 10,  # Longer text
        "token_estimate": 9500,  # Just under 10K
    }

    # Measure serialization time
    start_time = time.perf_counter()

    instance.handover_summary = large_summary
    instance.succession_reason = "context_limit"
    instance.completed_at = datetime.now(timezone.utc)

    db_session.add(instance)
    await db_session.commit()

    end_time = time.perf_counter()
    serialization_time_ms = (end_time - start_time) * 1000

    # ========== VERIFICATIONS ==========

    # Serialization should be fast (<500ms)
    assert serialization_time_ms < 500, f"JSONB serialization took {serialization_time_ms:.2f}ms"

    # Verify data integrity
    await db_session.refresh(instance)
    assert len(instance.handover_summary["active_agents"]) == 20
    assert len(instance.handover_summary["completed_phases"]) == 50
    assert len(instance.handover_summary["critical_context_refs"]) == 100

    print(f"\n✓ Large handover JSONB serialization: {serialization_time_ms:.2f}ms")


@pytest.mark.asyncio
async def test_succession_chain_query_scaling(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    Test query performance with long succession chain (50 instances).

    Verifies indexes prevent O(n²) query performance.
    """
    # Create chain of 50 instances
    for i in range(1, 51):
        instance = AgentExecution(
            **SuccessionTestData.generate_orchestrator_job_data(
                project_id=test_project.id,
                tenant_key=test_tenant_key,
                instance_number=i,
                context_used=50000,
                context_budget=150000,
                status="waiting",
            )
        )
        db_session.add(instance)

    await db_session.commit()

    # Measure query performance
    start_time = time.perf_counter()

    stmt = (
        select(AgentExecution)
        .where(
            AgentExecution.project_id == test_project.id,
            AgentExecution.agent_type == "orchestrator",
        )
        .order_by(AgentExecution.instance_number.asc())
    )

    result = await db_session.execute(stmt)
    orchestrators = result.scalars().all()

    end_time = time.perf_counter()
    query_time_ms = (end_time - start_time) * 1000

    # ========== VERIFICATIONS ==========

    assert len(orchestrators) == 50

    # Should still be fast even with 50 instances (indexed query)
    assert query_time_ms < 200, f"Query took {query_time_ms:.2f}ms for 50 instances"

    print(f"\n✓ Query performance (50 instances): {query_time_ms:.2f}ms")
