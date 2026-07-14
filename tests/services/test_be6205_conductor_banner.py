# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6205 follow-up — the project-less CONDUCTOR gets a conductor-scoped FORBIDDEN banner.

BE-6205 pins the project-less chain conductor's full_protocol header to ``multi_terminal``
so it never steers itself with Task(). But the STOCK multi_terminal banner prose
("You create job ORDERS. The USER opens each agent's new session. You do NOT execute your
specialists yourself." / "User opens a new session and starts the agent from the dashboard") is FALSE
for the conductor: under BE-6205 the conductor RUNS the fresh-terminal launch command
ITSELF (CH_CHAIN_DRIVE STEP A), autonomously. A cold conductor that trusts that banner
could stall waiting for the user — the exact failure BE-6205 fixes.

This pins the conductor-scoped banner variant:
  - KEEPS the load-bearing "no Task() to spawn your sub-orchestrators" forbid.
  - REPLACES the USER-opens-terminals prose with conductor-autonomy wording.
  - ONLY the project-less conductor gets it; a non-conductor multi_terminal context
    (genuine sub-orch / solo orchestrator) keeps the STOCK banner unchanged.

Failing layer = the rendered protocol/banner string.
Edition Scope: CE.
"""

from __future__ import annotations

import uuid

import pytest

from giljo_mcp.models.sequence_runs import SequenceRun
from giljo_mcp.services.mission_service import MissionService
from giljo_mcp.services.protocol_sections.agent_lifecycle import (
    _generate_orchestrator_protocol,
)
from giljo_mcp.tenant import TenantManager


# Conductor-autonomy wording that MUST be present for the conductor variant.
_CONDUCTOR_AUTONOMY = "you spawn each sub-orchestrator YOURSELF"
_CONDUCTOR_RUN_CMD = "RUNNING the fresh-terminal launch command"

# Stock multi_terminal prose that MUST be ABSENT from the conductor variant
# (it tells the conductor the USER opens terminals — false under BE-6205).
_STOCK_USER_TERMINALS = "The USER opens each agent's new session"
_STOCK_NOT_EXECUTE = "you do NOT execute"


# ---------------------------------------------------------------------------
# Layer 1 — the pure renderer: is_chain_conductor selects the conductor variant.
# ---------------------------------------------------------------------------


def test_renderer_conductor_variant_has_autonomy_wording() -> None:
    out = _generate_orchestrator_protocol(
        "job-1",
        "tenant-1",
        "exec-1",
        execution_mode="multi_terminal",
        tool="multi_terminal",
        is_chain_conductor=True,
    )
    # Conductor-autonomy wording present.
    assert _CONDUCTOR_AUTONOMY in out
    assert _CONDUCTOR_RUN_CMD in out
    assert "Bash" in out and "PowerShell" in out
    # The contradictory stock prose is gone.
    assert _STOCK_USER_TERMINALS not in out
    assert _STOCK_NOT_EXECUTE not in out
    # The load-bearing forbid survives: no Task() to spawn sub-orchestrators.
    assert "Task(" in out
    # BE-6216: the conductor header is RELABELED off the colliding "EXECUTION_MODE:
    # multi_terminal" token (which contradicted CH_CAPABILITY's real-mode print) to a
    # non-colliding sub-orch-spawn label. See test_be6216_conductor_execution_mode_label.
    assert "SUB-ORCH SPAWN: FRESH TERMINAL" in out
    assert "EXECUTION_MODE: multi_terminal" not in out


def test_renderer_non_conductor_multi_terminal_keeps_stock_banner() -> None:
    # is_chain_conductor defaults False → genuine multi_terminal sub-orch / solo
    # orchestrator keeps the STOCK banner verbatim (no regression).
    out = _generate_orchestrator_protocol(
        "job-1",
        "tenant-1",
        "exec-1",
        execution_mode="multi_terminal",
        tool="multi_terminal",
    )
    assert _STOCK_USER_TERMINALS in out
    assert _CONDUCTOR_AUTONOMY not in out
    assert _CONDUCTOR_RUN_CMD not in out


# ---------------------------------------------------------------------------
# Layer 2 — end-to-end assembly: the discriminator is `not job.project_id`.
# ---------------------------------------------------------------------------


def _svc(db_manager) -> MissionService:
    return MissionService(db_manager=db_manager, tenant_manager=TenantManager())


async def _seed_run(db_manager, *, project_ids, conductor_agent_id, execution_mode):
    tenant_key = TenantManager.generate_tenant_key()
    async with db_manager.get_session_async() as session:
        session.add(
            SequenceRun(
                id=str(uuid.uuid4()),
                tenant_key=tenant_key,
                project_ids=project_ids,
                resolved_order=project_ids,
                current_index=0,
                execution_mode=execution_mode,
                status="running",
                locked=True,
                conductor_agent_id=conductor_agent_id,
                project_statuses=dict.fromkeys(project_ids, "pending"),
            )
        )
        await session.commit()
    return tenant_key


class _FakeJob:
    def __init__(self, *, project_id, job_type="orchestrator", job_id="job-x"):
        self.project_id = project_id
        self.job_type = job_type
        self.job_id = job_id
        self.mission = ""
        self.created_at = None


class _FakeExec:
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.agent_display_name = "orchestrator"
        self.agent_name = "orchestrator"
        self.spawned_by = None
        self.status = "working"
        self.started_at = None
        self.project_phase = None


class _FakeProject:
    def __init__(self, execution_mode):
        self.execution_mode = execution_mode
        self.auto_checkin_interval = 10
        # BE-6209b added a LIVE project_phase derivation that reads this column
        # (mission_service ~L817); the fake predates it. None = staging (not launched).
        self.implementation_launched_at = None


def _assemble(svc, *, job, execution, chain_mode, project):
    return svc._assemble_mission_context(
        job=job,
        execution=execution,
        project=project,
        agent_identity=None,
        all_project_executions=[execution],
        mission_lookup={job.job_id: ""},
        current_team_state=None,
        tenant_key="tk_x",
        integrations={},
        chain_execution_mode=chain_mode,
    )


@pytest.mark.asyncio
async def test_projectless_conductor_gets_autonomy_banner(db_manager) -> None:
    """End-to-end: a project-less conductor on a claude_code_cli run renders the
    conductor-autonomy banner (NOT the stock USER-opens-terminals prose)."""
    p1 = str(uuid.uuid4())
    tenant_key = await _seed_run(
        db_manager, project_ids=[p1], conductor_agent_id="cond-1", execution_mode="claude_code_cli"
    )
    svc = _svc(db_manager)
    job = _FakeJob(project_id=None, job_id="job-cond")
    execution = _FakeExec("cond-1")

    async with svc._get_session(tenant_key) as session:
        chain_mode = await svc._resolve_chain_execution_mode(session, job, execution, tenant_key)

    resp = _assemble(svc, job=job, execution=execution, chain_mode=chain_mode, project=None)

    assert _CONDUCTOR_AUTONOMY in resp.full_protocol
    assert _CONDUCTOR_RUN_CMD in resp.full_protocol
    assert _STOCK_USER_TERMINALS not in resp.full_protocol
    assert _STOCK_NOT_EXECUTE not in resp.full_protocol
    # Still forbids Task() for sub-orch spawn.
    assert "Task(" in resp.full_protocol


@pytest.mark.asyncio
async def test_project_bound_suborch_keeps_stock_banner(db_manager) -> None:
    """A project-BOUND sub-orchestrator on a multi_terminal run keeps the STOCK
    banner unchanged — the conductor variant is project-less-only."""
    p1 = str(uuid.uuid4())
    tenant_key = await _seed_run(
        db_manager, project_ids=[p1], conductor_agent_id="cond-1", execution_mode="multi_terminal"
    )
    svc = _svc(db_manager)
    job = _FakeJob(project_id=p1, job_id="job-sub")
    execution = _FakeExec("sub-1")

    async with svc._get_session(tenant_key) as session:
        chain_mode = await svc._resolve_chain_execution_mode(session, job, execution, tenant_key)
    assert chain_mode == "multi_terminal"

    resp = _assemble(svc, job=job, execution=execution, chain_mode=chain_mode, project=_FakeProject("multi_terminal"))

    assert _STOCK_USER_TERMINALS in resp.full_protocol
    assert _CONDUCTOR_AUTONOMY not in resp.full_protocol
    assert _CONDUCTOR_RUN_CMD not in resp.full_protocol
