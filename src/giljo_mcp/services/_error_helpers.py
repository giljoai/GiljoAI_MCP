# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Shared "not found or wrong state" error builder for job/execution lookups.

TSK-9003 (follow-up from BE-8003b, PR #261): ``OrchestrationAgentStateService``
disambiguated its status-filtered lookup misses (unknown job_id vs exists-but-
wrong-state) via a private ``_not_found_or_wrong_state_error`` method, but the
three siblings that hit the exact same ambiguity -- ``job_completion_service``,
``mission_service``, ``progress_service`` -- each kept their own copy of the old
ambiguous "No active execution found for job {id}" message. Lifted here (a
service-instance method can't be imported across services without pulling in
that service's whole state) so every site shares one message + one
``build_next_action`` envelope.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from giljo_mcp.exceptions import ResourceNotFoundError
from giljo_mcp.repositories.agent_job_repository import AgentJobRepository
from giljo_mcp.schemas.service_responses import build_next_action


if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from giljo_mcp.database import DatabaseManager


async def not_found_or_wrong_state_error(
    session: AsyncSession,
    tenant_key: str,
    job_id: str,
    *,
    expected_status: str,
    method: str,
    db_manager: DatabaseManager,
    job_repo: AgentJobRepository | None = None,
) -> ResourceNotFoundError:
    """Disambiguate a status-filtered lookup miss (BE-8003b).

    A status-filtered execution lookup (e.g. "the active one", "the blocked
    one") returns None for TWO different reasons that used to collapse into one
    ambiguous "not found or not in status X" message: the job_id does not exist
    in this tenant at all, or it exists but its latest execution is in a
    different status. The field report (2026-06-28) measured ~5 recovery calls
    burned resolving that ambiguity by trial and error. Split it here so the
    message names which case it is and points at ``diagnose_project_state`` for
    recovery.

    ``job_repo``: a caller that already OWNS an ``AgentJobRepository`` instance
    (OrchestrationAgentStateService's ``self._job_repo`` -- the seam its tests
    mock) passes it so lookups go through that instance; callers without one
    (the three siblings) omit it and a repo is built from ``db_manager``.
    """
    if job_repo is None:
        job_repo = AgentJobRepository(db_manager)
    latest = await job_repo.get_latest_execution_for_job(session, tenant_key, job_id)
    if latest is None:
        return ResourceNotFoundError(
            message=(
                f"No job found with ID {job_id} in this tenant. The job_id may be "
                "mistyped, belong to a different tenant, or never have been spawned."
            ),
            context={
                "job_id": job_id,
                "method": method,
                "reason": "unknown_job_id",
                "next_action": build_next_action(
                    tool="diagnose_project_state",
                    why=(
                        "job_id not found in this tenant. If you know which project owns "
                        "it, call diagnose_project_state(project_id=...) to see its agents' "
                        "current job_ids and statuses."
                    ),
                ),
            },
        )

    job = await job_repo.get_agent_job_by_job_id(session, tenant_key, job_id)
    project_id = str(job.project_id) if job and job.project_id else None
    return ResourceNotFoundError(
        message=(
            f"Job {job_id} exists but its latest execution is in '{latest.status}' status, not '{expected_status}'."
        ),
        context={
            "job_id": job_id,
            "method": method,
            "reason": "wrong_state",
            "actual_status": latest.status,
            "expected_status": expected_status,
            "next_action": build_next_action(
                tool="diagnose_project_state",
                args_hint={"project_id": project_id} if project_id else None,
                why=(
                    f"Job is in '{latest.status}' status, not '{expected_status}'. Call "
                    "diagnose_project_state to see the current agent/job state and the "
                    "suggested recovery step."
                ),
            ),
        },
    )
