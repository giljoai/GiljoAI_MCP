# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Chain-conductor mission mirror (BE-6186).

When the dedicated chain CONDUCTOR (a project-less orchestrator,
``job_metadata.chain_conductor == True``) writes its job mission via
``update_job_mission``, that mission IS the chain mission: the cross-project plan.
This helper mirrors that text into ``sequence_runs.chain_mission`` (the FE-facing
column) through the owning ``SequenceRunService`` so the dashboard renders it.

The conductor's job is the ONLY write channel into ``chain_mission`` at runtime
(the FE edit pen is the other, pre-Implement). A NON-conductor job never reaches the
write here, so there is no leakage.

Best-effort by contract: every failure is swallowed so the primary
``update_agent_mission`` write is never broken. The most common expected refusal is
an ultralocked run (chain_mission becomes read-only at Implement); that is normal
and must not surface as an error.

Factored out of ``mission_service.py`` to keep that module under the 800-line
guardrail (BE-6186). Edition Scope: CE.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.models import AgentJob


logger = logging.getLogger(__name__)


async def mirror_chain_mission_for_conductor(
    *,
    session: AsyncSession,
    job: AgentJob,
    tenant_key: str,
    mission: str,
    db_manager: Any,
    tenant_manager: Any,
    repo: Any,
    websocket_manager: Any | None = None,
) -> None:
    """Mirror a chain conductor's job mission into ``sequence_runs.chain_mission``.

    No-op for a non-conductor job (``job_metadata.chain_conductor`` falsy). The run
    is found by the conductor's ``run_id`` (stamped on the job at mint), falling back
    to ``find_active_run_for_conductor`` by the conductor execution's agent_id. The
    write routes through ``SequenceRunService.update`` (tenant-scoped). Every failure
    is logged and swallowed; this is a best-effort side-effect.
    """
    metadata = job.job_metadata or {}
    if not metadata.get("chain_conductor"):
        return

    try:
        from giljo_mcp.services.sequence_run_service import SequenceRunService

        # BE-6199 (Unit B live-update fix): pass the websocket_manager so the
        # SequenceRunService.update() below fires the sequence:updated WS event and
        # the chain-mission window live-fills at staging time. Without it, the mission
        # only rendered after a manual refresh / launch_implementation forced a refetch.
        svc = SequenceRunService(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            session=session,
            websocket_manager=websocket_manager,
        )

        run_id = metadata.get("run_id")
        if not run_id:
            execution = await repo.get_execution_with_job(session, tenant_key, job.job_id)
            agent_id = str(execution.agent_id) if execution is not None else None
            if agent_id is not None:
                run = await svc.find_active_run_for_conductor(conductor_agent_id=agent_id, tenant_key=tenant_key)
                run_id = run.get("id") if run is not None else None
        if not run_id:
            return

        await svc.update(run_id=run_id, tenant_key=tenant_key, chain_mission=mission)
        logger.info(
            "[BE-6186] Mirrored chain conductor mission into sequence_runs.chain_mission",
            extra={"job_id": job.job_id, "run_id": run_id, "tenant_key": tenant_key},
        )
    except Exception as exc:  # noqa: BLE001 - best-effort mirror, never break the primary write
        logger.warning(
            "[BE-6186] chain_mission mirror failed (non-fatal) for job %s: %s",
            job.job_id,
            exc,
        )
