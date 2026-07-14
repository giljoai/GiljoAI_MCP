# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6177 / BE-6205 — full_protocol header mode agrees with CH_CAPABILITY.

The generic full_protocol header (the EXECUTION_MODE / FORBIDDEN-Task banner built in
agent_lifecycle.py) is gated on the mode passed to _generate_agent_protocol. It MUST
agree with CH_CAPABILITY for the same run.

BE-6177 first resolved the header mode from the RUN. BE-6205 REVERSES the conductor side
of that: under the owner-ratified model the project-less CONDUCTOR ALWAYS spawns each
sub-orchestrator in a FRESH TERMINAL (every execution_mode) and NEVER via Task(), so its
header must be TERMINAL-based — _resolve_chain_execution_mode now PINS the conductor
header to ``multi_terminal`` (the terminal / FORBIDDEN-Task banner), agreeing with the
reversed CH_CAPABILITY. A project-BOUND sub_orchestrator still resolves the RUN's mode
(its header describes how IT spawns its WORKERS). Failing layer = the rendered
protocol/header string.

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


_HEADER_MULTI = "EXECUTION_MODE: multi_terminal"
_HEADER_USER_TERMINALS = "The USER opens each agent's new session"


# ---------------------------------------------------------------------------
# Layer 1 — the pure renderer: the banner is gated on the resolved mode.
# multi_terminal renders the terminal header; a subagent mode (tool form
# "claude-code") suppresses it. Header MUST agree with CH_CAPABILITY.
# ---------------------------------------------------------------------------


def test_renderer_multi_terminal_renders_terminal_header():
    out = _generate_orchestrator_protocol(
        "job-1", "tenant-1", "exec-1", execution_mode="multi_terminal", tool="multi_terminal"
    )
    assert _HEADER_MULTI in out
    assert _HEADER_USER_TERMINALS in out


def test_renderer_claude_code_cli_omits_terminal_header():
    # claude_code_cli resolves to tool "claude-code"; the banner gate suppresses the
    # multi_terminal / FORBIDDEN-Task header for any non-multi_terminal mode.
    out = _generate_orchestrator_protocol(
        "job-1", "tenant-1", "exec-1", execution_mode="claude-code", tool="claude-code"
    )
    assert _HEADER_MULTI not in out
    assert "FORBIDDEN in this mode" not in out


# ---------------------------------------------------------------------------
# Layer 2 — the resolution: a chained orchestrator's header mode comes from the
# RUN, not the project column. This is the run-breaker that was RED before the fix.
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


@pytest.mark.asyncio
async def test_projectless_conductor_header_pinned_to_multi_terminal(db_manager):
    """BE-6205: a project-less conductor on a claude_code_cli run PINS its header mode to
    multi_terminal (it always spawns sub-orchs in fresh terminals, never via Task()),
    NOT the run's worker-spawn mode."""
    p1, p2 = str(uuid.uuid4()), str(uuid.uuid4())
    tenant_key = await _seed_run(
        db_manager, project_ids=[p1, p2], conductor_agent_id="cond-1", execution_mode="claude_code_cli"
    )
    svc = _svc(db_manager)
    async with svc._get_session(tenant_key) as session:
        mode = await svc._resolve_chain_execution_mode(
            session,
            _FakeJob(project_id=None),  # dedicated conductor is project-less
            _FakeExec("cond-1"),
            tenant_key,
        )
    assert mode == "multi_terminal"


@pytest.mark.asyncio
async def test_sub_orchestrator_resolves_run_mode(db_manager):
    """A project-bound sub_orchestrator resolves the RUN's mode via its project."""
    p1, p2 = str(uuid.uuid4()), str(uuid.uuid4())
    tenant_key = await _seed_run(
        db_manager, project_ids=[p1, p2], conductor_agent_id="cond-1", execution_mode="claude_code_cli"
    )
    svc = _svc(db_manager)
    async with svc._get_session(tenant_key) as session:
        mode = await svc._resolve_chain_execution_mode(
            session,
            _FakeJob(project_id=p2),
            _FakeExec("sub-1"),
            tenant_key,
        )
    assert mode == "claude_code_cli"


@pytest.mark.asyncio
async def test_solo_orchestrator_resolves_none(db_manager):
    """No active run → None, caller keeps the project-derived mode (byte-identical)."""
    svc = _svc(db_manager)
    tenant_key = TenantManager.generate_tenant_key()
    async with svc._get_session(tenant_key) as session:
        mode = await svc._resolve_chain_execution_mode(
            session,
            _FakeJob(project_id=str(uuid.uuid4())),
            _FakeExec("solo-1"),
            tenant_key,
        )
    assert mode is None


@pytest.mark.asyncio
async def test_conductor_header_is_terminal_based_agreeing_with_ch_capability(db_manager):
    """BE-6205 follow-up: end-to-end at the assembly layer, a project-less conductor on a
    claude_code_cli run renders the multi_terminal / FORBIDDEN-Task header — but with the
    CONDUCTOR-AUTONOMY banner variant, NOT the stock "the USER opens terminals" prose. The
    conductor self-spawns each sub-orch in a fresh terminal (CH_CHAIN_DRIVE STEP A), so the
    stock user-mediated banner would be false and could stall a cold conductor."""
    p1 = str(uuid.uuid4())
    tenant_key = await _seed_run(
        db_manager, project_ids=[p1], conductor_agent_id="cond-1", execution_mode="claude_code_cli"
    )
    svc = _svc(db_manager)

    job = _FakeJob(project_id=None, job_type="orchestrator", job_id="job-cond")
    execution = _FakeExec("cond-1")
    execution.agent_display_name = "orchestrator"
    execution.agent_name = "orchestrator"

    async with svc._get_session(tenant_key) as session:
        chain_mode = await svc._resolve_chain_execution_mode(session, job, execution, tenant_key)

    resp = svc._assemble_mission_context(
        job=job,
        execution=execution,
        project=None,  # project-less dedicated conductor
        agent_identity=None,
        all_project_executions=[execution],
        mission_lookup={job.job_id: ""},
        current_team_state=None,
        tenant_key=tenant_key,
        integrations={},
        chain_execution_mode=chain_mode,
    )

    # BE-6216: the conductor banner no longer prints the contradictory
    # "EXECUTION_MODE: multi_terminal" token (CH_CAPABILITY, injected at runtime, is now
    # the single authoritative execution-mode print). The banner is relabeled to a
    # non-colliding sub-orch-spawn header. (Was _HEADER_MULTI present.) Single-value proof
    # across banner + CH_CAPABILITY lives in test_be6216_conductor_execution_mode_label.
    assert _HEADER_MULTI not in resp.full_protocol
    assert "SUB-ORCH SPAWN: FRESH TERMINAL" in resp.full_protocol
    # Conductor-autonomy variant: self-spawn wording present, stock user-mediated prose gone.
    assert "you spawn each sub-orchestrator YOURSELF" in resp.full_protocol
    assert _HEADER_USER_TERMINALS not in resp.full_protocol


@pytest.mark.asyncio
async def test_multi_terminal_chain_still_renders_terminal_header(db_manager):
    """A multi_terminal chain run still renders the conductor's fresh-terminal sub-orch
    header (no regression). BE-6216: the header is the relabeled SUB-ORCH SPAWN token, and
    CH_CAPABILITY prints the single authoritative real mode ("EXECUTION MODE =
    multi_terminal", space form) -- not the old colliding "EXECUTION_MODE: multi_terminal"
    banner token."""
    p1 = str(uuid.uuid4())
    tenant_key = await _seed_run(
        db_manager, project_ids=[p1], conductor_agent_id="cond-1", execution_mode="multi_terminal"
    )
    svc = _svc(db_manager)

    job = _FakeJob(project_id=None, job_type="orchestrator", job_id="job-cond")
    execution = _FakeExec("cond-1")
    execution.agent_display_name = "orchestrator"
    execution.agent_name = "orchestrator"

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

    assert _HEADER_MULTI not in resp.full_protocol
    assert "SUB-ORCH SPAWN: FRESH TERMINAL" in resp.full_protocol
