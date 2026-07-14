# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-9055 — chain completion self-heals from the REAL project statuses.

Whether a chain conductor may ever finish was decided SOLELY by the run's
denormalized ``project_statuses`` JSON copy — and every write to that copy is
best-effort with errors swallowed (three writer sites). One swallowed write
used to mean a chain that could NEVER complete, recoverable only by cancelling
a successful chain. This exact denormalized-copy drift class shipped bugs twice
before (pre-BE-6181, pre-BE-6198).

The fix (``heal_chain_member_statuses``, reusing the BE-6200 read-boundary
rule): when the copy says "not finished", the completion guards re-check the
member's REAL ``projects`` row and repair the copy before refusing.

Regression tests at the failing layer (the service-layer completion guards):

1. test_guard_heals_stale_copy_and_allows_completion — corrupt the copy while
   the real projects are completed; the C1 guard heals and does NOT raise, and
   the repaired copy is persisted.
2. test_purge_heals_stale_copy_and_completes_run — same corruption; the run
   purge (chain finish line) heals and purges.
3. test_guard_still_blocks_genuinely_incomplete_chain — the load-bearing happy
   path: a member whose real row is still active keeps blocking completion.
4. test_soft_deleted_member_heals_to_terminated — a soft-deleted member row
   counts as terminal (BE-6200 rule) and unblocks the chain.

Seeding mirrors tests/services/test_be6198_closeout_chain_sync.py (the real
closeout path + minted conductor). DB-touching: db_session fixture
(TransactionalTestContext). No module-level mutable state. No ordering
dependencies. Parallel-safe. Edition Scope: Both.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.exceptions import ResourceNotFoundError, ValidationError
from giljo_mcp.models import Product, Project
from giljo_mcp.services.job_completion_service import JobCompletionService
from giljo_mcp.services.project_helpers import complete_chain_run_if_finished
from giljo_mcp.services.sequence_run_service import SequenceRunService
from giljo_mcp.tenant import TenantManager
from giljo_mcp.tools.project_closeout import close_project_and_update_memory


pytestmark = pytest.mark.asyncio

# See test_be6198_closeout_chain_sync.py: the closeout input gate needs a
# non-None db_manager, but the injected-session path never dereferences it.
_DB_MANAGER_SENTINEL = object()


async def _seed_project(session: AsyncSession, tenant_key: str) -> str:
    product = Product(
        id=str(uuid.uuid4()),
        name=f"BE-9055 Product {uuid.uuid4().hex[:6]}",
        description="Chain product.",
        tenant_key=tenant_key,
        is_active=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(product)
    await session.flush()
    project = Project(
        id=str(uuid.uuid4()),
        name=f"BE-9055 {uuid.uuid4().hex[:6]}",
        description="Chain member.",
        mission="Be a chain member.",
        status="active",
        tenant_key=tenant_key,
        product_id=product.id,
        series_number=1,
        execution_mode="claude_code_cli",
        created_at=datetime.now(UTC),
    )
    session.add(project)
    session.info["tenant_key"] = tenant_key
    await session.flush()
    return project.id


def _run_svc(session: AsyncSession) -> SequenceRunService:
    return SequenceRunService(db_manager=None, tenant_manager=TenantManager(), session=session)


def _completion_svc(session: AsyncSession) -> JobCompletionService:
    return JobCompletionService(db_manager=None, tenant_manager=TenantManager(), test_session=session)


async def _seed_two_project_run(session: AsyncSession, tenant_key: str) -> dict:
    p1 = await _seed_project(session, tenant_key)
    p2 = await _seed_project(session, tenant_key)
    run = await _run_svc(session).create(
        project_ids=[p1, p2],
        resolved_order=[p1, p2],
        execution_mode="claude_code_cli",
        tenant_key=tenant_key,
    )
    run["_project_ids"] = [p1, p2]
    return run


async def _close_member(session: AsyncSession, project_id: str, tenant_key: str) -> None:
    await close_project_and_update_memory(
        project_id=project_id,
        summary="done",
        key_outcomes=["x"],
        decisions_made=["y"],
        tenant_key=tenant_key,
        db_manager=_DB_MANAGER_SENTINEL,
        session=session,
        force=True,
    )


async def _conductor_job_and_exec(session: AsyncSession, tenant_key: str, conductor_agent_id: str):
    from giljo_mcp.models.agent_identity import AgentExecution, AgentJob

    execution = (
        await session.execute(
            select(AgentExecution).where(
                AgentExecution.tenant_key == tenant_key,
                AgentExecution.agent_id == conductor_agent_id,
            )
        )
    ).scalar_one()
    job = (
        await session.execute(
            select(AgentJob).where(
                AgentJob.tenant_key == tenant_key,
                AgentJob.job_id == execution.job_id,
            )
        )
    ).scalar_one()
    return job, execution


async def _corrupt_copy(session: AsyncSession, run: dict, tenant_key: str, statuses: dict) -> None:
    """Simulate a swallowed best-effort write: force the copy stale."""
    await _run_svc(session).update(
        run_id=run["id"],
        tenant_key=tenant_key,
        project_statuses=statuses,
    )


# ---------------------------------------------------------------------------
# 1. THE regression: stale copy + really-completed projects -> guard heals
# ---------------------------------------------------------------------------


async def test_guard_heals_stale_copy_and_allows_completion(db_session: AsyncSession) -> None:
    tenant = TenantManager.generate_tenant_key()
    run = await _seed_two_project_run(db_session, tenant)
    p1, p2 = run["_project_ids"]

    # Both members REALLY finish via the real closeout path...
    for pid in (p1, p2):
        await _close_member(db_session, pid, tenant)

    # ...but the best-effort copy write for p2 was "swallowed" (stale copy).
    await _corrupt_copy(db_session, run, tenant, {p1: "completed", p2: "implementing"})

    # The C1 guard must self-heal from the real project rows and NOT raise.
    job, execution = await _conductor_job_and_exec(db_session, tenant, run["conductor_agent_id"])
    await _completion_svc(db_session)._guard_conductor_chain_incomplete(
        db_session, job, execution, tenant, str(job.job_id)
    )

    # And the repaired copy is persisted through the owning service.
    refetched = await _run_svc(db_session).get(run_id=run["id"], tenant_key=tenant)
    assert refetched["project_statuses"][p2] == "completed", "the guard must repair the stale copy, not just bypass it"


async def test_guard_heals_missing_copy_entry(db_session: AsyncSession) -> None:
    """A member missing from the copy entirely (never written) also heals."""
    tenant = TenantManager.generate_tenant_key()
    run = await _seed_two_project_run(db_session, tenant)
    p1, p2 = run["_project_ids"]

    for pid in (p1, p2):
        await _close_member(db_session, pid, tenant)

    await _corrupt_copy(db_session, run, tenant, {p1: "completed"})  # p2 entry gone

    job, execution = await _conductor_job_and_exec(db_session, tenant, run["conductor_agent_id"])
    await _completion_svc(db_session)._guard_conductor_chain_incomplete(
        db_session, job, execution, tenant, str(job.job_id)
    )


async def test_guard_proceeds_when_persisting_healed_copy_fails(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Persisting the repaired copy is best-effort: if sequence_run_service.update
    raises, the guard STILL proceeds off the in-memory healed value and does NOT
    block a really-finished chain (BE-9055 — a second swallowed write must not
    strand a successful chain either)."""
    tenant = TenantManager.generate_tenant_key()
    run = await _seed_two_project_run(db_session, tenant)
    p1, p2 = run["_project_ids"]

    # Both members REALLY finish, but p2's best-effort copy write was swallowed.
    for pid in (p1, p2):
        await _close_member(db_session, pid, tenant)
    await _corrupt_copy(db_session, run, tenant, {p1: "completed", p2: "implementing"})

    # Now force the persist of the REPAIRED copy to fail as well.
    async def _boom(self, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        raise RuntimeError("persist of healed statuses failed")

    monkeypatch.setattr(SequenceRunService, "update", _boom)

    # The guard heals from the real project rows in memory and must NOT raise
    # despite the failed persist — the healed in-memory copy drives the decision.
    job, execution = await _conductor_job_and_exec(db_session, tenant, run["conductor_agent_id"])
    await _completion_svc(db_session)._guard_conductor_chain_incomplete(
        db_session, job, execution, tenant, str(job.job_id)
    )


# ---------------------------------------------------------------------------
# 2. the finish line: stale copy no longer blocks the run purge
# ---------------------------------------------------------------------------


async def test_purge_heals_stale_copy_and_completes_run(db_session: AsyncSession) -> None:
    tenant = TenantManager.generate_tenant_key()
    run = await _seed_two_project_run(db_session, tenant)
    p1, p2 = run["_project_ids"]

    for pid in (p1, p2):
        await _close_member(db_session, pid, tenant)

    await _corrupt_copy(db_session, run, tenant, {p1: "completed", p2: "implementing"})

    purged = await complete_chain_run_if_finished(
        db_manager=None,
        tenant_manager=TenantManager(),
        conductor_agent_id=run["conductor_agent_id"],
        tenant_key=tenant,
        test_session=db_session,
    )
    assert purged is True, "a stale copy must not stop a really-finished chain from completing"

    with pytest.raises(ResourceNotFoundError):
        await _run_svc(db_session).get(run_id=run["id"], tenant_key=tenant)


# ---------------------------------------------------------------------------
# 3. TWO-SIDED: a genuinely incomplete chain still blocks (the happy path
#    of the guard is the load-bearing half)
# ---------------------------------------------------------------------------


async def test_guard_still_blocks_genuinely_incomplete_chain(db_session: AsyncSession) -> None:
    tenant = TenantManager.generate_tenant_key()
    run = await _seed_two_project_run(db_session, tenant)
    p1, _p2 = run["_project_ids"]

    # Only the FIRST member finishes; p2's row is really still active.
    await _close_member(db_session, p1, tenant)

    job, execution = await _conductor_job_and_exec(db_session, tenant, run["conductor_agent_id"])
    with pytest.raises(ValidationError) as ei:
        await _completion_svc(db_session)._guard_conductor_chain_incomplete(
            db_session, job, execution, tenant, str(job.job_id)
        )
    assert ei.value.error_code == "CONDUCTOR_CHAIN_INCOMPLETE"

    purged = await complete_chain_run_if_finished(
        db_manager=None,
        tenant_manager=TenantManager(),
        conductor_agent_id=run["conductor_agent_id"],
        tenant_key=tenant,
        test_session=db_session,
    )
    assert purged is False, "an in-flight chain must not be purged by the self-heal"


# ---------------------------------------------------------------------------
# 4. BE-6200 rule: a soft-deleted member row counts as terminal (terminated)
# ---------------------------------------------------------------------------


async def test_soft_deleted_member_heals_to_terminated(db_session: AsyncSession) -> None:
    tenant = TenantManager.generate_tenant_key()
    run = await _seed_two_project_run(db_session, tenant)
    p1, p2 = run["_project_ids"]

    await _close_member(db_session, p1, tenant)

    # p2 is soft-deleted out from under the chain (user deleted the project).
    p2_row = (
        await db_session.execute(select(Project).where(Project.id == p2, Project.tenant_key == tenant))
    ).scalar_one()
    p2_row.deleted_at = datetime.now(UTC)
    await db_session.flush()

    job, execution = await _conductor_job_and_exec(db_session, tenant, run["conductor_agent_id"])
    await _completion_svc(db_session)._guard_conductor_chain_incomplete(
        db_session, job, execution, tenant, str(job.job_id)
    )

    refetched = await _run_svc(db_session).get(run_id=run["id"], tenant_key=tenant)
    assert refetched["project_statuses"][p2] == "terminated", (
        "a soft-deleted member must heal to a terminal token the copy validator accepts"
    )
