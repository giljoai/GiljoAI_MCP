# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""UI-2 / BE-6177 — per-project archive in a chain run.

Archiving (close-out) ONE chain member must:
  1. Update only that project's entry in project_statuses.
  2. NOT flip the run to status=completed while other members are still active.
  3. Solo path (project not in any run) stays a clean no-op — byte-identical.

These tests target mark_chain_member_status (the helper called by the REST
archive path via close_completed_agents_with_commit) at the service layer.

Edition Scope: CE.
"""

from __future__ import annotations

import uuid

import pytest

from giljo_mcp.models.sequence_runs import SequenceRun
from giljo_mcp.services.project_helpers import mark_chain_member_status
from giljo_mcp.services.sequence_run_service import SequenceRunService
from giljo_mcp.tenant import TenantManager


pytestmark = pytest.mark.asyncio


async def _seed_run(
    db_manager,
    *,
    project_ids: list[str],
    project_statuses: dict[str, str],
    status: str = "running",
) -> tuple[str, str]:
    """Seed a sequence run; return (tenant_key, run_id)."""
    tenant_key = TenantManager.generate_tenant_key()
    run_id = str(uuid.uuid4())
    async with db_manager.get_session_async() as session:
        run = SequenceRun(
            id=run_id,
            tenant_key=tenant_key,
            project_ids=project_ids,
            resolved_order=project_ids,
            current_index=0,
            execution_mode="claude_code_cli",
            status=status,
            locked=True,
            project_statuses=project_statuses,
        )
        session.add(run)
        await session.commit()
    return tenant_key, run_id


async def _fetch_run(db_manager, *, run_id: str, tenant_key: str) -> dict:
    svc = SequenceRunService(db_manager=db_manager, tenant_manager=TenantManager())
    return await svc.get(run_id=run_id, tenant_key=tenant_key)


async def test_archive_one_member_updates_only_that_member(db_manager):
    """Closing P1 sets project_statuses[p1]=completed; P2 entry is unchanged."""
    p1, p2 = str(uuid.uuid4()), str(uuid.uuid4())
    tenant_key, run_id = await _seed_run(
        db_manager,
        project_ids=[p1, p2],
        project_statuses={p1: "implementing", p2: "implementing"},
    )

    changed = await mark_chain_member_status(
        db_manager=db_manager,
        tenant_manager=TenantManager(),
        project_id=p1,
        tenant_key=tenant_key,
        status="completed",
    )

    assert changed is True
    run = await _fetch_run(db_manager, run_id=run_id, tenant_key=tenant_key)
    statuses = run.get("project_statuses") or {}
    assert statuses[p1] == "completed", f"expected p1=completed, got {statuses}"
    assert statuses[p2] == "implementing", f"p2 must stay implementing, got {statuses}"


async def test_archive_one_member_does_not_complete_run_while_other_active(db_manager):
    """After closing P1, run.status stays 'running' — NOT flipped to 'completed'."""
    p1, p2 = str(uuid.uuid4()), str(uuid.uuid4())
    tenant_key, run_id = await _seed_run(
        db_manager,
        project_ids=[p1, p2],
        project_statuses={p1: "implementing", p2: "implementing"},
    )

    await mark_chain_member_status(
        db_manager=db_manager,
        tenant_manager=TenantManager(),
        project_id=p1,
        tenant_key=tenant_key,
        status="completed",
    )

    run = await _fetch_run(db_manager, run_id=run_id, tenant_key=tenant_key)
    assert run["status"] == "running", f"run must stay 'running' while p2 is still active; got {run['status']!r}"


async def test_archive_last_member_still_does_not_auto_complete_run(db_manager):
    """mark_chain_member_status never flips run.status — only complete_chain_run_if_finished
    (called by the conductor) may do that.  Archiving the last member leaves status
    unchanged (complete_chain_run_if_finished is out-of-scope for this helper)."""
    p1 = str(uuid.uuid4())
    tenant_key, run_id = await _seed_run(
        db_manager,
        project_ids=[p1],
        project_statuses={p1: "implementing"},
    )

    await mark_chain_member_status(
        db_manager=db_manager,
        tenant_manager=TenantManager(),
        project_id=p1,
        tenant_key=tenant_key,
        status="completed",
    )

    run = await _fetch_run(db_manager, run_id=run_id, tenant_key=tenant_key)
    # mark_chain_member_status only writes project_statuses — status flip belongs
    # to complete_chain_run_if_finished (conductor path, not archive REST path).
    assert run["status"] == "running", f"mark_chain_member_status must NOT flip run.status; got {run['status']!r}"


async def test_archive_solo_project_is_noop(db_manager):
    """A project with no active run is a clean no-op (solo byte-identical)."""
    solo_pid = str(uuid.uuid4())
    tenant_key = TenantManager.generate_tenant_key()

    changed = await mark_chain_member_status(
        db_manager=db_manager,
        tenant_manager=TenantManager(),
        project_id=solo_pid,
        tenant_key=tenant_key,
        status="completed",
    )

    assert changed is False
