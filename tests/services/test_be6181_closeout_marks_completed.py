# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6181 — closeout marks a chain member project_statuses="completed".

Regression at the FAILING layer (the missing terminal writer). The C1 conductor
guard (job_completion_service._guard_conductor_chain_incomplete) treats
{"completed","terminated"} as terminal in project_statuses, but NOTHING wrote
"completed" before BE-6181 — so a conductor could never finish a chain.

The shared writer ``mark_chain_member_status`` (reused by all three closeout
writers AND the launch-advance) is exercised directly here:

1. For a chain member it sets project_statuses[project]="completed" in the
   active run, MERGING with existing statuses.
2. For a solo project (no active run) it is a clean no-op returning False — no
   write, no error (solo stays byte-identical; Deletion Test holds).

DB-touching: db_session fixture (TransactionalTestContext). No module-level
mutable state. No ordering dependencies. Edition Scope: CE.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.models.sequence_runs import SequenceRun
from giljo_mcp.services.project_helpers import mark_chain_member_status
from giljo_mcp.services.sequence_run_service import SequenceRunService
from giljo_mcp.tenant import TenantManager


pytestmark = pytest.mark.asyncio


async def _seed_run(
    session: AsyncSession,
    tenant_key: str,
    *,
    resolved_order: list[str],
    project_statuses: dict[str, str] | None = None,
) -> str:
    run_id = str(uuid.uuid4())
    run = SequenceRun(
        id=run_id,
        tenant_key=tenant_key,
        project_ids=resolved_order,
        resolved_order=resolved_order,
        current_index=0,
        execution_mode="claude_code_cli",
        status="running",
        review_policy="per_card",
        project_statuses=project_statuses or {},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(run)
    session.info["tenant_key"] = tenant_key
    await session.flush()
    return run_id


async def test_closeout_marks_chain_member_completed(db_session: AsyncSession) -> None:
    """A chain member closeout sets project_statuses[member]="completed", merged."""
    tenant = TenantManager.generate_tenant_key()
    p0, p1 = str(uuid.uuid4()), str(uuid.uuid4())
    run_id = await _seed_run(
        db_session,
        tenant,
        resolved_order=[p0, p1],
        project_statuses={p0: "running"},
    )

    wrote = await mark_chain_member_status(
        db_manager=None,
        tenant_manager=TenantManager(),
        project_id=p0,
        tenant_key=tenant,
        status="completed",
        test_session=db_session,
    )
    assert wrote is True

    run_svc = SequenceRunService(db_manager=None, tenant_manager=TenantManager(), session=db_session)
    run = await run_svc.get(run_id=run_id, tenant_key=tenant)
    assert run["project_statuses"][p0] == "completed"
    # p1 untouched (merge, not overwrite of the whole map).
    assert p1 not in run["project_statuses"]


async def test_closeout_solo_is_noop(db_session: AsyncSession) -> None:
    """A solo project (no active run) closeout is a no-op returning False; no error."""
    tenant = TenantManager.generate_tenant_key()
    solo_pid = str(uuid.uuid4())

    wrote = await mark_chain_member_status(
        db_manager=None,
        tenant_manager=TenantManager(),
        project_id=solo_pid,
        tenant_key=tenant,
        status="completed",
        test_session=db_session,
    )
    assert wrote is False  # no run -> clean no-op
