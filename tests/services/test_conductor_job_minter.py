# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6184: direct unit tests for the project-less conductor minter helpers.

``conductor_job_minter`` mints the dedicated, project-less chain conductor's
AgentJob + AgentExecution (the conductor owns no project). Regression at the
helper layer:

1. test_mint_conductor_job_creates_projectless_orchestrator
   mint_conductor_job inserts an orchestrator AgentJob with project_id IS NULL +
   its AgentExecution, and returns the execution agent_id.
2. test_projectless_conductor_staging_directive_shape
   the staging directive is the STOP-shaped USE_RUNTIME_MISSION payload (never a
   misleading 404), pointing the conductor at get_job_mission.

Parallel-safe: db_session fixture (TransactionalTestContext). Edition Scope: CE.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from giljo_mcp.services.conductor_job_minter import (
    mint_conductor_job,
    projectless_conductor_staging_directive,
)
from giljo_mcp.tenant import TenantManager


@pytest.mark.asyncio
async def test_mint_conductor_job_creates_projectless_orchestrator(db_session: AsyncSession) -> None:
    tenant = TenantManager.generate_tenant_key()

    agent_id = await mint_conductor_job(db_session, tenant_key=tenant, run_id="run-abc")

    assert agent_id, "mint must return a fresh agent_id"

    job = (
        await db_session.execute(
            select(AgentJob).where(
                AgentJob.tenant_key == tenant,
                AgentJob.job_type == "orchestrator",
            )
        )
    ).scalar_one()
    assert job.project_id is None, "the conductor owns NO project (project_id must be NULL)"
    assert job.job_metadata.get("chain_conductor") is True
    assert job.job_metadata.get("run_id") == "run-abc"

    execution = (
        await db_session.execute(
            select(AgentExecution).where(
                AgentExecution.agent_id == agent_id,
                AgentExecution.tenant_key == tenant,
            )
        )
    ).scalar_one()
    assert execution.job_id == job.job_id
    assert execution.agent_display_name == "orchestrator"
    assert execution.project_phase == "implementation"
    assert execution.status == "waiting"


def test_projectless_conductor_staging_directive_shape() -> None:
    directive = projectless_conductor_staging_directive("job-xyz")

    assert directive["status"] == "CHAIN_CONDUCTOR"
    assert directive["action"] == "USE_RUNTIME_MISSION"
    assert directive["identity"] == {"job_id": "job-xyz", "project_id": None}
    assert "get_job_mission" in directive["message"]
    assert directive["thin_client"] is True
