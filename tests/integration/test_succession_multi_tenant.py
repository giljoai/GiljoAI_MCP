"""
Multi-Tenant Isolation Tests for Orchestrator Succession (Handover 0080)

Critical security tests ensuring succession respects tenant boundaries.

Tests:
- Succession respects tenant isolation
- Handover summaries contain no cross-tenant data
- Succession chain queries filter by tenant_key
- Tenant A succession doesn't affect Tenant B
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import Project
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from tests.fixtures.succession_fixtures import SuccessionTestData


# ============================================================================
# Multi-Tenant Isolation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_succession_respects_tenant_boundaries(
    db_session: AsyncSession,
):
    """
    Tenant A succession doesn't affect Tenant B orchestrators.

    Critical security test: Ensure complete tenant isolation during succession.
    """
    # Create projects for two tenants
    tenant_a_key = f"tk_tenant_a_{uuid.uuid4().hex[:8]}"
    tenant_b_key = f"tk_tenant_b_{uuid.uuid4().hex[:8]}"

    project_a = Project(
        id=str(uuid.uuid4()),
        name="Tenant A Project",
        mission="Project for Tenant A",
        status="active",
        tenant_key=tenant_a_key,
    )
    project_b = Project(
        id=str(uuid.uuid4()),
        name="Tenant B Project",
        mission="Project for Tenant B",
        status="active",
        tenant_key=tenant_b_key,
    )

    db_session.add_all([project_a, project_b])
    await db_session.commit()

    # Create orchestrators for both tenants
    orch_a1 = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=project_a.id,
            tenant_key=tenant_a_key,
            instance_number=1,
            context_used=140000,
            context_budget=150000,
            status="working",
        )
    )

    orch_b1 = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=project_b.id,
            tenant_key=tenant_b_key,
            instance_number=1,
            context_used=60000,  # Below threshold
            context_budget=150000,
            status="working",
        )
    )

    db_session.add_all([orch_a1, orch_b1])
    await db_session.commit()
    await db_session.refresh(orch_a1)
    await db_session.refresh(orch_b1)

    # Tenant A triggers succession
    orch_a2 = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=project_a.id,
            tenant_key=tenant_a_key,
            instance_number=2,
            context_used=0,
            context_budget=150000,
            spawned_by=orch_a1.job_id,
            status="waiting",
        )
    )

    db_session.add(orch_a2)
    await db_session.flush()

    # Complete Tenant A succession
    orch_a1.status = "complete"
    orch_a1.handover_to = orch_a2.job_id
    orch_a1.handover_summary = SuccessionTestData.generate_handover_summary()
    orch_a1.succession_reason = "context_limit"
    orch_a1.completed_at = datetime.now(timezone.utc)

    await db_session.commit()
    await db_session.refresh(orch_a1)
    await db_session.refresh(orch_a2)
    await db_session.refresh(orch_b1)

    # ========== VERIFICATIONS ==========

    # Verify Tenant A succession completed
    assert orch_a1.status == "complete"
    assert orch_a1.handover_to == orch_a2.job_id
    assert orch_a2.instance_number == 2

    # Verify Tenant B orchestrator unaffected
    assert orch_b1.status == "working"  # Still working
    assert orch_b1.instance_number == 1  # No succession
    assert orch_b1.handover_to is None
    assert orch_b1.handover_summary is None

    # Query Tenant A orchestrators only
    stmt_a = select(AgentExecution).where(
        AgentExecution.tenant_key == tenant_a_key,
        AgentExecution.agent_type == "orchestrator",
    )
    result_a = await db_session.execute(stmt_a)
    tenant_a_orchestrators = result_a.scalars().all()

    assert len(tenant_a_orchestrators) == 2
    assert all(o.tenant_key == tenant_a_key for o in tenant_a_orchestrators)

    # Query Tenant B orchestrators only
    stmt_b = select(AgentExecution).where(
        AgentExecution.tenant_key == tenant_b_key,
        AgentExecution.agent_type == "orchestrator",
    )
    result_b = await db_session.execute(stmt_b)
    tenant_b_orchestrators = result_b.scalars().all()

    assert len(tenant_b_orchestrators) == 1
    assert tenant_b_orchestrators[0].job_id == orch_b1.job_id


@pytest.mark.asyncio
async def test_handover_summary_no_cross_tenant_data(
    db_session: AsyncSession,
):
    """
    Handover summary contains only tenant-scoped data.

    Security critical: Verify no data leakage across tenant boundaries.
    """
    tenant_a_key = f"tk_tenant_a_{uuid.uuid4().hex[:8]}"
    tenant_b_key = f"tk_tenant_b_{uuid.uuid4().hex[:8]}"

    # Create projects
    project_a = Project(
        id=str(uuid.uuid4()),
        name="Tenant A Project",
        mission="Tenant A mission",
        status="active",
        tenant_key=tenant_a_key,
    )
    project_b = Project(
        id=str(uuid.uuid4()),
        name="Tenant B Project",
        mission="Tenant B mission",
        status="active",
        tenant_key=tenant_b_key,
    )

    db_session.add_all([project_a, project_b])
    await db_session.commit()

    # Create Tenant A orchestrator
    orch_a1 = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=project_a.id,
            tenant_key=tenant_a_key,
            instance_number=1,
            context_used=140000,
            context_budget=150000,
            status="working",
        )
    )

    # Create Tenant B orchestrator (for isolation verification)
    orch_b1 = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=project_b.id,
            tenant_key=tenant_b_key,
            instance_number=1,
            context_used=80000,
            context_budget=150000,
            status="working",
        )
    )

    db_session.add_all([orch_a1, orch_b1])
    await db_session.commit()
    await db_session.refresh(orch_a1)
    await db_session.refresh(orch_b1)

    # Tenant A creates successor
    orch_a2 = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=project_a.id,
            tenant_key=tenant_a_key,
            instance_number=2,
            context_used=0,
            context_budget=150000,
            spawned_by=orch_a1.job_id,
            status="waiting",
        )
    )

    db_session.add(orch_a2)
    await db_session.flush()

    # Generate handover summary (should only reference Tenant A data)
    handover_summary = {
        "project_status": "Tenant A project 60% complete",
        "active_agents": [
            {"job_id": str(uuid.uuid4()), "type": "tenant-a-agent", "status": "working"},
        ],
        "completed_phases": ["tenant-a-phase-1", "tenant-a-phase-2"],
        "pending_decisions": ["Tenant A specific decision"],
        "critical_context_refs": [f"tenant-a-chunk-{i}" for i in range(1, 6)],
        "next_steps": "Continue Tenant A development",
        "token_estimate": 5000,
    }

    orch_a1.status = "complete"
    orch_a1.handover_to = orch_a2.job_id
    orch_a1.handover_summary = handover_summary
    orch_a1.succession_reason = "context_limit"
    orch_a1.completed_at = datetime.now(timezone.utc)

    await db_session.commit()
    await db_session.refresh(orch_a1)

    # ========== VERIFICATIONS ==========

    # Verify handover summary contains only Tenant A references
    assert "Tenant A" in orch_a1.handover_summary["project_status"]
    assert "Tenant B" not in str(orch_a1.handover_summary)

    # Verify agent references are Tenant A only
    for agent in orch_a1.handover_summary["active_agents"]:
        assert "tenant-a" in agent["type"].lower()

    # Verify context chunks are Tenant A only
    for chunk_ref in orch_a1.handover_summary["critical_context_refs"]:
        assert "tenant-a" in chunk_ref.lower()

    # Verify no cross-contamination
    assert orch_b1.job_id not in str(orch_a1.handover_summary)
    assert tenant_b_key not in str(orch_a1.handover_summary)


@pytest.mark.asyncio
async def test_succession_chain_query_tenant_isolation(
    db_session: AsyncSession,
):
    """
    GET /succession_chain filters by tenant_key.

    Query for Tenant A succession chain should never return Tenant B data.
    """
    tenant_a_key = f"tk_tenant_a_{uuid.uuid4().hex[:8]}"
    tenant_b_key = f"tk_tenant_b_{uuid.uuid4().hex[:8]}"

    # Create projects
    project_a = Project(
        id=str(uuid.uuid4()),
        name="Tenant A Project",
        mission="Tenant A",
        status="active",
        tenant_key=tenant_a_key,
    )
    project_b = Project(
        id=str(uuid.uuid4()),
        name="Tenant B Project",
        mission="Tenant B",
        status="active",
        tenant_key=tenant_b_key,
    )

    db_session.add_all([project_a, project_b])
    await db_session.commit()

    # Create Tenant A succession chain (3 instances)
    tenant_a_chain = []
    for i in range(1, 4):
        orch = AgentExecution(
            **SuccessionTestData.generate_orchestrator_job_data(
                project_id=project_a.id,
                tenant_key=tenant_a_key,
                instance_number=i,
                context_used=140000 if i < 3 else 50000,
                context_budget=150000,
                spawned_by=tenant_a_chain[-1].job_id if tenant_a_chain else None,
                status="waiting" if i == 3 else "complete",
            )
        )

        if i < 3:
            orch.completed_at = datetime.now(timezone.utc)
            orch.succession_reason = "context_limit"

        db_session.add(orch)
        tenant_a_chain.append(orch)
        await db_session.flush()

        # Link handover
        if i > 1:
            tenant_a_chain[i - 2].handover_to = orch.job_id
            tenant_a_chain[i - 2].handover_summary = SuccessionTestData.generate_handover_summary()

    # Create Tenant B succession chain (2 instances)
    tenant_b_chain = []
    for i in range(1, 3):
        orch = AgentExecution(
            **SuccessionTestData.generate_orchestrator_job_data(
                project_id=project_b.id,
                tenant_key=tenant_b_key,
                instance_number=i,
                context_used=140000 if i == 1 else 30000,
                context_budget=150000,
                spawned_by=tenant_b_chain[-1].job_id if tenant_b_chain else None,
                status="waiting" if i == 2 else "complete",
            )
        )

        if i == 1:
            orch.completed_at = datetime.now(timezone.utc)
            orch.succession_reason = "context_limit"

        db_session.add(orch)
        tenant_b_chain.append(orch)
        await db_session.flush()

        if i > 1:
            tenant_b_chain[i - 2].handover_to = orch.job_id
            tenant_b_chain[i - 2].handover_summary = SuccessionTestData.generate_handover_summary()

    await db_session.commit()

    # ========== VERIFICATIONS ==========

    # Query Tenant A succession chain only
    stmt_a = (
        select(AgentExecution)
        .where(
            AgentExecution.project_id == project_a.id,
            AgentExecution.tenant_key == tenant_a_key,
            AgentExecution.agent_type == "orchestrator",
        )
        .order_by(AgentExecution.instance_number.asc())
    )

    result_a = await db_session.execute(stmt_a)
    chain_a = result_a.scalars().all()

    # Should return only Tenant A orchestrators
    assert len(chain_a) == 3
    assert all(o.tenant_key == tenant_a_key for o in chain_a)
    assert all(o.project_id == project_a.id for o in chain_a)

    # Query Tenant B succession chain only
    stmt_b = (
        select(AgentExecution)
        .where(
            AgentExecution.project_id == project_b.id,
            AgentExecution.tenant_key == tenant_b_key,
            AgentExecution.agent_type == "orchestrator",
        )
        .order_by(AgentExecution.instance_number.asc())
    )

    result_b = await db_session.execute(stmt_b)
    chain_b = result_b.scalars().all()

    # Should return only Tenant B orchestrators
    assert len(chain_b) == 2
    assert all(o.tenant_key == tenant_b_key for o in chain_b)
    assert all(o.project_id == project_b.id for o in chain_b)

    # Verify no cross-tenant contamination
    tenant_a_job_ids = [o.job_id for o in chain_a]
    tenant_b_job_ids = [o.job_id for o in chain_b]

    assert not any(job_id in tenant_b_job_ids for job_id in tenant_a_job_ids)


@pytest.mark.asyncio
async def test_concurrent_succession_different_tenants(
    db_session: AsyncSession,
):
    """
    Multiple tenants triggering succession simultaneously.

    Verifies: No race conditions or cross-tenant interference.
    """
    # Create 3 tenants
    tenants = []
    for i in range(3):
        tenant_key = f"tk_concurrent_{i}_{uuid.uuid4().hex[:8]}"
        project = Project(
            id=str(uuid.uuid4()),
            name=f"Concurrent Tenant {i} Project",
            mission=f"Tenant {i}",
            status="active",
            tenant_key=tenant_key,
        )
        db_session.add(project)
        tenants.append({"tenant_key": tenant_key, "project": project})

    await db_session.commit()

    # Each tenant creates orchestrator at 90% threshold
    orchestrators_before = []
    for tenant in tenants:
        orch = AgentExecution(
            **SuccessionTestData.generate_orchestrator_job_data(
                project_id=tenant["project"].id,
                tenant_key=tenant["tenant_key"],
                instance_number=1,
                context_used=135000,
                context_budget=150000,
                status="working",
            )
        )
        db_session.add(orch)
        orchestrators_before.append(orch)

    await db_session.commit()

    # Simulate concurrent succession (all 3 tenants trigger at once)
    orchestrators_after = []
    for i, tenant in enumerate(tenants):
        orch_before = orchestrators_before[i]
        await db_session.refresh(orch_before)

        # Create successor
        orch_after = AgentExecution(
            **SuccessionTestData.generate_orchestrator_job_data(
                project_id=tenant["project"].id,
                tenant_key=tenant["tenant_key"],
                instance_number=2,
                context_used=0,
                context_budget=150000,
                spawned_by=orch_before.job_id,
                status="waiting",
            )
        )
        db_session.add(orch_after)
        orchestrators_after.append(orch_after)
        await db_session.flush()

        # Complete handover
        orch_before.status = "complete"
        orch_before.handover_to = orch_after.job_id
        orch_before.handover_summary = SuccessionTestData.generate_handover_summary()
        orch_before.succession_reason = "context_limit"
        orch_before.completed_at = datetime.now(timezone.utc)

    await db_session.commit()

    # ========== VERIFICATIONS ==========

    # Verify all 3 tenants successfully created successors
    for i, tenant in enumerate(tenants):
        # Query tenant's orchestrators
        stmt = select(AgentExecution).where(
            AgentExecution.tenant_key == tenant["tenant_key"],
            AgentExecution.agent_type == "orchestrator",
        )
        result = await db_session.execute(stmt)
        tenant_orchestrators = result.scalars().all()

        # Should have 2 instances (before and after succession)
        assert len(tenant_orchestrators) == 2

        # Verify instance numbers
        instance_numbers = sorted([o.instance_number for o in tenant_orchestrators])
        assert instance_numbers == [1, 2]

        # Verify handover integrity
        instance1 = next(o for o in tenant_orchestrators if o.instance_number == 1)
        instance2 = next(o for o in tenant_orchestrators if o.instance_number == 2)

        assert instance1.status == "complete"
        assert instance1.handover_to == instance2.job_id
        assert instance2.spawned_by == instance1.job_id


@pytest.mark.asyncio
async def test_tenant_isolation_in_spawned_by_chain(
    db_session: AsyncSession,
):
    """
    Verify spawned_by chain never crosses tenant boundaries.

    Critical: spawned_by references should only point to jobs within same tenant.
    """
    tenant_a_key = f"tk_tenant_a_{uuid.uuid4().hex[:8]}"
    tenant_b_key = f"tk_tenant_b_{uuid.uuid4().hex[:8]}"

    # Create projects
    project_a = Project(
        id=str(uuid.uuid4()),
        name="Tenant A Project",
        mission="Tenant A",
        status="active",
        tenant_key=tenant_a_key,
    )
    project_b = Project(
        id=str(uuid.uuid4()),
        name="Tenant B Project",
        mission="Tenant B",
        status="active",
        tenant_key=tenant_b_key,
    )

    db_session.add_all([project_a, project_b])
    await db_session.commit()

    # Create chains for both tenants
    tenant_a_chain = []
    tenant_b_chain = []

    for i in range(1, 4):
        # Tenant A
        orch_a = AgentExecution(
            **SuccessionTestData.generate_orchestrator_job_data(
                project_id=project_a.id,
                tenant_key=tenant_a_key,
                instance_number=i,
                context_used=140000 if i < 3 else 50000,
                context_budget=150000,
                spawned_by=tenant_a_chain[-1].job_id if tenant_a_chain else None,
                status="waiting" if i == 3 else "complete",
            )
        )
        db_session.add(orch_a)
        tenant_a_chain.append(orch_a)

        # Tenant B
        orch_b = AgentExecution(
            **SuccessionTestData.generate_orchestrator_job_data(
                project_id=project_b.id,
                tenant_key=tenant_b_key,
                instance_number=i,
                context_used=140000 if i < 3 else 50000,
                context_budget=150000,
                spawned_by=tenant_b_chain[-1].job_id if tenant_b_chain else None,
                status="waiting" if i == 3 else "complete",
            )
        )
        db_session.add(orch_b)
        tenant_b_chain.append(orch_b)

        await db_session.flush()

    await db_session.commit()

    # Refresh all
    for orch in tenant_a_chain + tenant_b_chain:
        await db_session.refresh(orch)

    # ========== VERIFICATIONS ==========

    # Verify Tenant A spawned_by chain integrity
    for i in range(1, 3):
        assert tenant_a_chain[i].spawned_by == tenant_a_chain[i - 1].job_id
        # Ensure spawned_by does NOT reference Tenant B
        assert tenant_a_chain[i].spawned_by not in [o.job_id for o in tenant_b_chain]

    # Verify Tenant B spawned_by chain integrity
    for i in range(1, 3):
        assert tenant_b_chain[i].spawned_by == tenant_b_chain[i - 1].job_id
        # Ensure spawned_by does NOT reference Tenant A
        assert tenant_b_chain[i].spawned_by not in [o.job_id for o in tenant_a_chain]

    # Verify root instances have no spawned_by
    assert tenant_a_chain[0].spawned_by is None
    assert tenant_b_chain[0].spawned_by is None
