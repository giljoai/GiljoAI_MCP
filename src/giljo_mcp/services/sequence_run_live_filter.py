# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Live-member filter for active sequence runs (BE-6200 / Unit E).

Extracted from ``sequence_run_service.py`` to keep that module under the 800-line
CI guardrail (mirrors the BE-6184 serialization split). Internal; the owning
service calls it inside ``list_active``.

A chain run whose ``status`` is stuck (e.g. ``pending`` forever — there is no
reaper for sequence_runs) but whose member projects were all closed is
effectively done. The cockpit's project-less Jobs nav resolves to the first
"active" run; such a wedged run would hijack it indefinitely. Filtering it out at
the read boundary unsticks it WITHOUT touching its row (no data surgery — CE
self-hosters have no operator). Solo users have no runs, so this is a no-op for
them.

Edition Scope: CE.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.domain.project_status import LIFECYCLE_FINISHED_STATUSES
from giljo_mcp.models.projects import Project
from giljo_mcp.models.sequence_runs import SequenceRun


def _run_member_ids(run: SequenceRun) -> list[str]:
    """Union of a run's resolved_order + project_ids as strings (order preserved)."""
    return [str(p) for p in ((run.resolved_order or []) + (run.project_ids or [])) if p]


async def filter_runs_with_live_members(
    *,
    session: AsyncSession,
    runs: list[SequenceRun],
    tenant_key: str,
) -> list[SequenceRun]:
    """Drop runs whose member PROJECT ROWS are ALL terminal.

    Terminality is keyed on the ACTUAL Project rows (resolved via the run's
    ``resolved_order`` / ``project_ids``), NOT the drift-prone
    ``run.project_statuses`` JSON — that JSON drifted on pre-BE-6198 builds when
    members were closed. A project row is terminal when its status is in
    ``LIFECYCLE_FINISHED_STATUSES`` (completed / cancelled / terminated /
    deleted) OR it is soft-deleted (``deleted_at`` set) OR the row is gone.

    A run with at least one live (non-terminal) member is kept. Tenant-scoped.
    N+1-safe: one IN-clause query over the union of all member project ids.
    """
    member_ids: set[str] = set()
    for run in runs:
        member_ids.update(_run_member_ids(run))

    if not member_ids:
        return runs

    rows = await session.execute(
        select(Project.id, Project.status, Project.deleted_at).where(
            Project.tenant_key == tenant_key,
            Project.id.in_(member_ids),
        )
    )
    live_project_ids: set[str] = {
        str(pid)
        for pid, status, deleted_at in rows.all()
        if deleted_at is None and status not in LIFECYCLE_FINISHED_STATUSES
    }

    return [run for run in runs if any(pid in live_project_ids for pid in _run_member_ids(run))]
