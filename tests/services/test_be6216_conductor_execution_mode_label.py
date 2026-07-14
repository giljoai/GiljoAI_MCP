# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6216 (2) — the conductor must never read TWO execution_mode values.

The project-less chain conductor's FORBIDDEN-spawn banner (agent_lifecycle.py) pinned a
literal "EXECUTION_MODE: multi_terminal" header. But CH_CAPABILITY prints the run's REAL
server-resolved mode ("EXECUTION MODE = claude_code_cli" on a subagent run). On every
non-multi_terminal chain the conductor therefore saw two contradictory values for the
same field -- the #1 correctness risk flagged by the field report.

BE-6216 keeps the multi_terminal PIN structurally (the no-Task() FORBIDDEN banner needs
it to render for the conductor) but RELABELS the header line to a non-colliding token
("SUB-ORCH SPAWN: FRESH TERMINAL (every mode) ...") and adds a body line clarifying the
run's execution_mode governs only how sub-orchs spawn their WORKERS. So CH_CAPABILITY
becomes the single authoritative execution-mode print, and the banner is now a
spawn-rule header, not a second mode value.

RED before BE-6216: the conductor banner contained "EXECUTION_MODE: multi_terminal",
contradicting CH_CAPABILITY. GREEN after: the banner header carries the relabeled token
and no "EXECUTION_MODE:" value at all. Failing layer = the rendered protocol string.

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
from giljo_mcp.services.protocol_sections.chapters_chain import _build_ch_capability
from giljo_mcp.tenant import TenantManager


# The relabeled header token (non-colliding) and the OLD colliding token.
_NEW_HEADER = "SUB-ORCH SPAWN: FRESH TERMINAL"
_OLD_COLLIDING = "EXECUTION_MODE: multi_terminal"


# ---------------------------------------------------------------------------
# Layer 1 — the pure renderer: the conductor banner header is relabeled.
# ---------------------------------------------------------------------------


def test_conductor_banner_drops_colliding_execution_mode_token() -> None:
    out = _generate_orchestrator_protocol(
        "job-1",
        "tenant-1",
        "exec-1",
        execution_mode="multi_terminal",
        tool="multi_terminal",
        is_chain_conductor=True,
    )
    # Relabeled, non-colliding header present; old contradictory token gone.
    assert _NEW_HEADER in out
    assert "ROLE: CHAIN CONDUCTOR" in out
    assert _OLD_COLLIDING not in out
    # The banner explicitly disclaims being an execution_mode and points at CH_CAPABILITY.
    assert "This header is NOT an execution_mode" in out
    assert "WORKERS" in out
    # Load-bearing forbid + conductor-autonomy wording survive (no regression).
    assert "Task(" in out
    assert "you spawn each sub-orchestrator YOURSELF" in out


def test_non_conductor_multi_terminal_banner_keeps_execution_mode_header() -> None:
    """The relabel is conductor-gated: a genuine multi_terminal sub-orch / solo
    orchestrator (is_chain_conductor=False) keeps the stock EXECUTION_MODE header
    verbatim, because there its real mode IS multi_terminal -- no contradiction."""
    out = _generate_orchestrator_protocol(
        "job-1",
        "tenant-1",
        "exec-1",
        execution_mode="multi_terminal",
        tool="multi_terminal",
    )
    assert _OLD_COLLIDING in out
    assert _NEW_HEADER not in out


# ---------------------------------------------------------------------------
# Layer 1b — the two surfaces the conductor reads (banner + CH_CAPABILITY) carry
# exactly ONE execution-mode value between them: CH_CAPABILITY prints the REAL mode,
# the banner prints none. This is the "never two EXECUTION_MODE values" proof.
# ---------------------------------------------------------------------------


def test_banner_and_ch_capability_yield_single_execution_mode_value() -> None:
    banner = _generate_orchestrator_protocol(
        "job-1",
        "tenant-1",
        "exec-1",
        execution_mode="multi_terminal",  # the structural conductor pin (keeps the no-Task banner)
        tool="multi_terminal",
        is_chain_conductor=True,
    )
    # CH_CAPABILITY renders from the run's REAL resolved mode (subagent run).
    ch_cap = _build_ch_capability(execution_mode="claude_code_cli", can_spawn_terminals=True)

    # The banner carries NO execution_mode value; CH_CAPABILITY is the sole print, REAL mode.
    assert _OLD_COLLIDING not in banner
    assert "EXECUTION_MODE" not in banner  # the relabel removed the field entirely
    assert "EXECUTION MODE = claude_code_cli" in ch_cap
    # And CH_CAPABILITY does not itself contradict with a multi_terminal value.
    assert "EXECUTION MODE = multi_terminal" not in ch_cap


# ---------------------------------------------------------------------------
# Layer 2 — end-to-end assembly: the conductor's assembled protocol carries the
# relabeled banner and never the old colliding EXECUTION_MODE token.
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
        self.agent_name = "Chain Conductor"
        self.spawned_by = None
        self.status = "working"
        self.started_at = None
        self.project_phase = None


@pytest.mark.asyncio
async def test_subagent_conductor_assembled_banner_drops_colliding_token(db_manager) -> None:
    """End-to-end at the assembly layer: a project-less conductor on a claude_code_cli
    chain renders the relabeled SUB-ORCH SPAWN banner into full_protocol and NEVER the
    old colliding "EXECUTION_MODE: multi_terminal" token. (CH_CAPABILITY's real-mode print
    is injected on the runtime get_job_mission path, asserted directly above.)"""
    p1 = str(uuid.uuid4())
    tenant_key = await _seed_run(
        db_manager, project_ids=[p1], conductor_agent_id="cond-1", execution_mode="claude_code_cli"
    )
    svc = _svc(db_manager)
    job = _FakeJob(project_id=None, job_id="job-cond")
    execution = _FakeExec("cond-1")

    async with svc._get_session(tenant_key) as session:
        chain_mode = await svc._resolve_chain_execution_mode(session, job, execution, tenant_key)

    resp = svc._assemble_mission_context(
        job=job,
        execution=execution,
        project=None,
        agent_identity=None,
        all_project_executions=[execution],
        mission_lookup={job.job_id: ""},
        current_team_state=None,
        tenant_key=tenant_key,
        integrations={},
        chain_execution_mode=chain_mode,
    )

    protocol = resp.full_protocol
    # The old contradictory banner token is gone; the relabeled header is present.
    assert _OLD_COLLIDING not in protocol
    assert _NEW_HEADER in protocol
