# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Project-less chain conductor server-side helpers (BE-6184).

The dedicated chain conductor is a PROJECT-LESS orchestrator: it owns NO project,
has its own ``agent_id``, and drives the whole sequence run. This module collects the
small server-side helpers specific to it:

- ``mint_conductor_job``: insert the conductor AgentJob + AgentExecution in the SAME
  transaction that creates the ``sequence_runs`` row, so a run can never exist without
  an addressable conductor (a failed insert rolls the run back; no orphans). The insert
  mirrors the canonical project-less orchestrator seed at ``install.py``.
- ``projectless_conductor_staging_directive``: the STOP-shaped directive returned when a
  project-less conductor mistakenly calls the staging path (it drives via the runtime
  mission path instead).

Factored out of the owning services to keep them under the 800-line guardrail.

Edition Scope: CE.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from giljo_mcp.models.base import generate_uuid
from giljo_mcp.schemas.jsonb_validators import validate_agent_job_metadata


async def mint_conductor_job(
    session: AsyncSession,
    *,
    tenant_key: str,
    run_id: str,
    conductor_label: str | None = None,
) -> str:
    """Insert the project-less conductor AgentJob + AgentExecution; return its agent_id.

    Uses the supplied (already tenant-bound) ``session`` so the writes are atomic
    with the caller's run-create transaction; the caller commits once. The job is
    ``project_id=NULL`` so the conductor is symmetric to every sub-orchestrator
    instead of owning the head project (the dual-hat collapse BE-6184 removes).

    ``agent_jobs.project_id`` is nullable (see ``agent_identity.py``), so no
    migration is required. The execution starts in ``project_phase="implementation"``
    (the conductor exists only to drive an in-flight run) and ``status="waiting"`` so
    the agent's first ``get_job_mission`` transitions it to ``working`` exactly like
    any other orchestrator.
    """
    job_id = generate_uuid()
    agent_id = generate_uuid()

    conductor_job = AgentJob(
        job_id=job_id,
        tenant_key=tenant_key,
        project_id=None,
        mission=None,
        job_type="orchestrator",
        status="active",
        job_metadata=validate_agent_job_metadata({"chain_conductor": True, "run_id": run_id}),
    )
    session.add(conductor_job)

    conductor_execution = AgentExecution(
        agent_id=agent_id,
        job_id=job_id,
        tenant_key=tenant_key,
        agent_display_name="orchestrator",
        agent_name=conductor_label or "Chain Conductor",
        status="waiting",
        health_status="unknown",
        project_phase="implementation",
    )
    session.add(conductor_execution)

    await session.flush()
    return agent_id


def projectless_conductor_staging_directive(job_id: str) -> dict[str, Any]:
    """STOP-shaped staging directive for the project-less chain conductor (BE-6184).

    The dedicated conductor has no project to stage; it receives its chain-drive
    protocol via the runtime mission path (get_job_mission), not staging. Returned by
    ``get_staging_instructions`` instead of the misleading "Project not found" 404.
    """
    return {
        "status": "CHAIN_CONDUCTOR",
        "action": "USE_RUNTIME_MISSION",
        "redirect": None,
        "identity": {"job_id": job_id, "project_id": None},
        "message": (
            "You are the dedicated chain conductor (no project of your own). There are no "
            "staging instructions for you; call get_job_mission to receive your chain-drive "
            "protocol and advance the run."
        ),
        "thin_client": True,
    }
