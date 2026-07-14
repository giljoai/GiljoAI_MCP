# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""INF-6049b — tests for the stage_project / implement_project MCP tools.

Covers the load-bearing DoD for the two new project-lifecycle tools:

- MCP-transport boundary tests for BOTH tools (regression-at-the-failing-layer;
  the BE-5042 gap — a tool can pass every service test yet fail at the FastMCP
  @mcp.tool wrapper). Driven through ``create_connected_server_and_client_session``.
- The SACRED human gate: implement_project returns a DISTINGUISHABLE structured
  error for "staging not complete" vs "press Implement in the dashboard", NEVER
  sets ``implementation_launched_at``, and offers no bypass.
- Tenant isolation: another tenant's project is not found.
- stage_project mode-matrix: all 5 modes produce non-empty staging prompts and
  always end on the explicit STOP instruction.
- The per-terminal agent seed initiation protocol appears in the multi_terminal
  implementation prompt.
- Equivalence: stage_project's staging prompt is byte-identical to what the REST
  ``GET /api/prompts/staging`` endpoint produces for the same project + mode
  (proves the tool reuses the engine and the shared extraction did not fork it).
- A direct unit matrix for the shared gate fn.

Pattern reference: tests/integration/test_request_approval_mcp_transport.py
(in-memory FastMCP transport + shared-session ToolAccessor + tenant monkeypatch).
"""

from __future__ import annotations

import json
import random
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from mcp.shared.memory import create_connected_server_and_client_session
from sqlalchemy import select

from giljo_mcp import platform_registry
from giljo_mcp.exceptions import ImplementationNotReadyError
from giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from giljo_mcp.models.organizations import Organization
from giljo_mcp.models.products import Product
from giljo_mcp.models.projects import Project
from giljo_mcp.models.sequence_runs import SequenceRun
from giljo_mcp.services.project_staging_service import ProjectStagingService
from giljo_mcp.tenant import TenantManager
from giljo_mcp.tools.tool_accessor._project_tools import (
    _STAGING_CHAIN_CONTINUE_INSTRUCTION,
    _STAGING_STOP_INSTRUCTION,
)


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers (mirror the harness decoders used by the other transport tests)
# ---------------------------------------------------------------------------


def _payload(call_tool_result) -> dict:
    if getattr(call_tool_result, "structuredContent", None):
        return call_tool_result.structuredContent
    first_block = call_tool_result.content[0]
    text = getattr(first_block, "text", None)
    if text is None:
        raise AssertionError(f"unexpected content block: {first_block!r}")
    return json.loads(text)


def _error_text(call_tool_result) -> str:
    parts = []
    for block in call_tool_result.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts)


async def _seed_product_project(
    db_session,
    tenant_key: str,
    *,
    staging_status: str | None = None,
    launched: bool = False,
    execution_mode: str = "claude_code_cli",
) -> dict:
    """Create org + product + project (product linked) for ``tenant_key``."""
    suffix = uuid4().hex[:8]
    org = Organization(name=f"Org {suffix}", slug=f"org-{suffix}", tenant_key=tenant_key, is_active=True)
    db_session.add(org)
    await db_session.flush()

    product = Product(
        id=str(uuid4()),
        name=f"Product {suffix}",
        description="INF-6049b lifecycle-tool tests",
        tenant_key=tenant_key,
        is_active=True,
        product_memory={},
    )
    db_session.add(product)
    await db_session.flush()

    project = Project(
        id=str(uuid4()),
        tenant_key=tenant_key,
        product_id=product.id,
        name=f"Project {suffix}",
        description="x",
        mission="x",
        status="active",
        execution_mode=execution_mode,
        staging_status=staging_status,
        implementation_launched_at=datetime.now(UTC) if launched else None,
        series_number=random.randint(1, 9000),
    )
    db_session.add(project)
    await db_session.commit()
    return {"project": project, "product": product}


async def _seed_orchestrator_and_agent(db_session, tenant_key: str, project) -> dict:
    """Seed a non-terminal orchestrator execution + one waiting child agent."""
    orch_job = AgentJob(
        job_id=str(uuid4()),
        tenant_key=tenant_key,
        project_id=project.id,
        job_type="orchestrator",
        mission="orchestrate",
        status="active",
        created_at=datetime.now(UTC),
    )
    db_session.add(orch_job)
    await db_session.flush()

    orch_exec = AgentExecution(
        id=str(uuid4()),
        agent_id=str(uuid4()),
        job_id=orch_job.job_id,
        tenant_key=tenant_key,
        agent_display_name="orchestrator",
        status="idle",
        started_at=datetime.now(UTC),
    )
    db_session.add(orch_exec)
    await db_session.flush()

    child_job = AgentJob(
        job_id=str(uuid4()),
        tenant_key=tenant_key,
        project_id=project.id,
        job_type="implementer",
        mission="implement",
        status="active",
        created_at=datetime.now(UTC),
    )
    db_session.add(child_job)
    await db_session.flush()

    child_exec = AgentExecution(
        id=str(uuid4()),
        agent_id=str(uuid4()),
        job_id=child_job.job_id,
        tenant_key=tenant_key,
        agent_display_name="implementer",
        status="waiting",
        spawned_by=orch_exec.agent_id,
        started_at=datetime.now(UTC),
    )
    db_session.add(child_exec)
    await db_session.commit()
    return {"orchestrator": orch_exec, "child": child_exec}


# ---------------------------------------------------------------------------
# Fixtures: shared-session ToolAccessor + tenant-aware in-memory MCP client
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def primary_tenant_key() -> str:
    return TenantManager.generate_tenant_key()


@pytest_asyncio.fixture
async def secondary_tenant_key() -> str:
    return TenantManager.generate_tenant_key()


class _TenantSwitch:
    def __init__(self, value: str):
        self.value = value


@pytest_asyncio.fixture
async def lifecycle_mcp_client(db_manager, db_session, primary_tenant_key, monkeypatch):
    """Yield ``(new_client, tenant_switch)`` for in-memory FastMCP transport tests.

    The ToolAccessor is built with ``test_session=db_session`` so the
    ThinClientPromptGenerator the lifecycle tools construct does its reads/writes
    (orchestrator creation, staged-state persist) inside the rolled-back test
    transaction. ``_resolve_tenant`` / ``_resolve_user_id`` are monkeypatched on
    ``_base`` (the _call_tool + wrapper call site) since the in-memory transport
    has no auth middleware.
    """
    from api import app_state
    from api.endpoints import mcp_sdk_server
    from api.endpoints.mcp_tools import _base
    from giljo_mcp.tools.tool_accessor import ToolAccessor

    state = app_state.state
    prior_tool_accessor = state.tool_accessor
    prior_tenant_manager = state.tenant_manager
    prior_db_manager = state.db_manager

    if state.tenant_manager is None:
        state.tenant_manager = TenantManager()
    state.db_manager = db_manager

    state.tool_accessor = ToolAccessor(
        db_manager=db_manager,
        tenant_manager=state.tenant_manager,
        test_session=db_session,
    )

    tenant_switch = _TenantSwitch(primary_tenant_key)
    monkeypatch.setattr(_base, "_resolve_tenant", lambda ctx: tenant_switch.value)
    monkeypatch.setattr(_base, "_resolve_user_id", lambda ctx: None)

    def _new_client():
        return create_connected_server_and_client_session(mcp_sdk_server.mcp)

    try:
        yield _new_client, tenant_switch
    finally:
        state.tool_accessor = prior_tool_accessor
        state.tenant_manager = prior_tenant_manager
        state.db_manager = prior_db_manager


# ---------------------------------------------------------------------------
# stage_project — transport boundary + mode matrix + STOP instruction
# ---------------------------------------------------------------------------


async def test_stage_project_through_transport_returns_prompt_and_stops(
    lifecycle_mcp_client, db_session, primary_tenant_key
):
    new_client, _switch = lifecycle_mcp_client
    seeded = await _seed_product_project(db_session, primary_tenant_key)

    async with new_client() as session:
        result = await session.call_tool("stage_project", {"project_id": seeded["project"].id, "mode": "claude"})

    assert result.isError is False, _error_text(result)
    payload = _payload(result)
    assert payload["status"] == "staged"
    assert payload["mode"] == "claude"
    # BE-9035c collapse: the per-CLI short token 'claude' now STORES execution_mode
    # 'subagent' (the harness identity moves to the 'tool' slot); only 'multi_terminal'
    # stores 'multi_terminal'.
    assert payload["execution_mode"] == "subagent"
    assert payload["prompt"], "staging prompt must be non-empty"
    assert payload["orchestrator_id"]
    assert payload["estimated_prompt_tokens"] > 0
    # The SACRED stop instruction must be present in the returned payload.
    assert "STOP" in payload["next_action"]["why"]
    assert "Implement" in payload["next_action"]["why"]

    # Staged state persisted on the project row (in the test transaction).
    row = (await db_session.execute(select(Project).where(Project.id == seeded["project"].id))).scalar_one()
    assert row.staging_status == "staged"
    assert row.execution_mode == "subagent"


# BE-9035c collapse: execution_mode is now 'multi_terminal' | 'subagent'. Every per-CLI
# short token (claude/codex/gemini/antigravity) folds to the stored 'subagent' mode (its
# harness identity lands in the 'tool' slot); only 'multi_terminal' stores 'multi_terminal'.
@pytest.mark.parametrize(
    "mode,expected_execution_mode",
    [
        ("multi_terminal", "multi_terminal"),
        ("subagent", "subagent"),
        ("claude", "subagent"),
        ("codex", "subagent"),
        ("gemini", "subagent"),
        ("antigravity", "subagent"),
    ],
)
async def test_stage_project_mode_matrix_all_non_empty(
    lifecycle_mcp_client, db_session, primary_tenant_key, mode, expected_execution_mode
):
    new_client, _switch = lifecycle_mcp_client
    seeded = await _seed_product_project(db_session, primary_tenant_key, execution_mode=None)

    async with new_client() as session:
        result = await session.call_tool("stage_project", {"project_id": seeded["project"].id, "mode": mode})

    assert result.isError is False, _error_text(result)
    payload = _payload(result)
    assert payload["prompt"], f"mode {mode} produced an empty prompt"
    assert payload["execution_mode"] == expected_execution_mode
    assert "STOP" in payload["next_action"]["why"]


async def test_stage_project_invalid_mode_rejected_at_boundary(lifecycle_mcp_client, db_session, primary_tenant_key):
    new_client, _switch = lifecycle_mcp_client
    seeded = await _seed_product_project(db_session, primary_tenant_key)

    async with new_client() as session:
        result = await session.call_tool("stage_project", {"project_id": seeded["project"].id, "mode": "bogus"})

    assert result.isError is True, "invalid mode must be rejected (Literal boundary validation)"


# ---------------------------------------------------------------------------
# BE-9015: stage_project next_action is chain-aware (two-sided, MCP-boundary)
# ---------------------------------------------------------------------------


async def _seed_active_chain_run(db_session, tenant_key: str, project_id: str) -> str:
    """Seed an ACTIVE (running) SequenceRun whose project_ids contains ``project_id``.

    That makes ``find_active_run_for_project`` resolve it, so stage_project takes the
    chain-member branch. tenant_key-scoped, active status ('running') so the query's
    (pending/running/stalled) filter matches.
    """
    run = SequenceRun(
        id=str(uuid4()),
        tenant_key=tenant_key,
        project_ids=[project_id],
        resolved_order=[project_id],
        execution_mode="claude_code_cli",
        status="running",
        project_statuses={project_id: "pending"},
    )
    db_session.info["tenant_key"] = tenant_key
    db_session.add(run)
    await db_session.commit()
    return run.id


async def test_stage_project_solo_next_action_is_stop_byte_identical(
    lifecycle_mcp_client, db_session, primary_tenant_key
):
    """BE-9015 two-sided guard — SOLO half (load-bearing regression guard). A project with
    NO active chain run keeps the SACRED human Implement gate: stage_project's
    next_action.why is BYTE-IDENTICAL to _STAGING_STOP_INSTRUCTION. This proves the
    chain-awareness change did NOT disturb the solo gate (CI1-EM2 note 4)."""
    new_client, _switch = lifecycle_mcp_client
    seeded = await _seed_product_project(db_session, primary_tenant_key)

    async with new_client() as session:
        result = await session.call_tool("stage_project", {"project_id": seeded["project"].id, "mode": "claude"})

    assert result.isError is False, _error_text(result)
    why = _payload(result)["next_action"]["why"]
    assert why == _STAGING_STOP_INSTRUCTION, "solo next_action must be byte-identical to the STOP instruction"


async def test_stage_project_chain_member_continues_not_stop(lifecycle_mcp_client, db_session, primary_tenant_key):
    """BE-9015 two-sided guard — CHAIN half (the bug fix). A project that belongs to an
    ACTIVE chain run must NOT receive the solo STOP-HERE instruction (which wedges a chain
    sub-orchestrator waiting for a dashboard Implement click chain mode never has). Its
    next_action is the chain-continue instruction (a single get_job_mission carries it
    straight into implementation)."""
    new_client, _switch = lifecycle_mcp_client
    seeded = await _seed_product_project(db_session, primary_tenant_key)
    await _seed_active_chain_run(db_session, primary_tenant_key, seeded["project"].id)

    async with new_client() as session:
        result = await session.call_tool("stage_project", {"project_id": seeded["project"].id, "mode": "claude"})

    assert result.isError is False, _error_text(result)
    payload = _payload(result)
    why = payload["next_action"]["why"]
    # Chain member -> the continue instruction, byte-identical to the new constant...
    assert why == _STAGING_CHAIN_CONTINUE_INSTRUCTION
    # ...and NEVER the solo STOP string (the exact wedge the field bug hit).
    assert _STAGING_STOP_INSTRUCTION not in why
    assert "STOP HERE" not in why
    assert "MANUALLY press Implement" not in why
    assert "get_job_mission" in why
    # Staging itself is unchanged — only the next_action branches on chain membership.
    assert payload["status"] == "staged"
    assert payload["prompt"], "staging prompt must still be produced on the chain path"


# ---------------------------------------------------------------------------
# implement_project — the SACRED human gate (distinguishable structured errors)
# ---------------------------------------------------------------------------


async def test_implement_project_gate_staging_incomplete(lifecycle_mcp_client, db_session, primary_tenant_key):
    new_client, _switch = lifecycle_mcp_client
    seeded = await _seed_product_project(db_session, primary_tenant_key, staging_status="staged", launched=False)

    async with new_client() as session:
        result = await session.call_tool("implement_project", {"project_id": seeded["project"].id})

    assert result.isError is False, _error_text(result)
    payload = _payload(result)
    assert payload["status"] == "gate_not_passed"
    assert payload["reason"] == "staging_incomplete"
    assert payload["next_action"]["tool"] == "stage_project"
    assert "stage_project" in payload["next_action"]["why"]


async def test_implement_project_gate_not_launched_names_dashboard_action(
    lifecycle_mcp_client, db_session, primary_tenant_key
):
    new_client, _switch = lifecycle_mcp_client
    seeded = await _seed_product_project(
        db_session, primary_tenant_key, staging_status="staging_complete", launched=False
    )

    async with new_client() as session:
        result = await session.call_tool("implement_project", {"project_id": seeded["project"].id})

    assert result.isError is False, _error_text(result)
    payload = _payload(result)
    assert payload["status"] == "gate_not_passed"
    assert payload["reason"] == "not_launched"
    # Names the exact dashboard action the agent must ask the user to take.
    assert payload["next_action"]["tool"] is None
    assert "Implement" in payload["next_action"]["why"]
    assert "dashboard" in payload["next_action"]["why"]

    # SACRED gate: implement_project must NOT have stamped implementation_launched_at.
    row = (await db_session.execute(select(Project).where(Project.id == seeded["project"].id))).scalar_one()
    assert row.implementation_launched_at is None, "implement_project must NEVER set implementation_launched_at"


async def test_implement_project_happy_path_returns_prompt_with_agent_seed(
    lifecycle_mcp_client, db_session, primary_tenant_key
):
    new_client, _switch = lifecycle_mcp_client
    seeded = await _seed_product_project(
        db_session,
        primary_tenant_key,
        staging_status="staging_complete",
        launched=True,
        execution_mode="multi_terminal",
    )
    seeded_team = await _seed_orchestrator_and_agent(db_session, primary_tenant_key, seeded["project"])

    async with new_client() as session:
        result = await session.call_tool("implement_project", {"project_id": seeded["project"].id})

    assert result.isError is False, _error_text(result)
    payload = _payload(result)
    assert payload["status"] == "ready"
    assert payload["prompt"], "implementation prompt must be non-empty"
    assert payload["agent_count"] >= 1
    assert payload["orchestrator_job_id"]
    # BE-6182: orchestrator_job_id must be the orchestrator's JOB id, NOT its agent_id
    # (the field name + every consumer — get_job_mission, report_progress, the
    # conductor advance loop — key off the job_id). The seed gives the orchestrator
    # distinct job_id/agent_id uuids, so this is a sharp regression guard.
    orch_exec = seeded_team["orchestrator"]
    assert payload["orchestrator_job_id"] == orch_exec.job_id, "must return the orchestrator JOB id"
    assert payload["orchestrator_job_id"] != orch_exec.agent_id, "must NOT return the orchestrator agent_id"
    # INF-6049b deliverable #3: multi_terminal impl prompt carries the per-terminal
    # agent seed initiation protocol (health_check -> get_job_mission -> execute).
    assert "PER-SESSION AGENT SEED" in payload["prompt"]
    assert "get_job_mission" in payload["prompt"]


async def test_implement_project_subagent_election_never_renders_multi_terminal_seed(
    lifecycle_mcp_client, db_session, primary_tenant_key
):
    """BE-9099 boundary test (regression-at-the-failing-layer, through the transport):
    a project with the canonical UI election ``execution_mode='subagent'`` must NEVER
    receive the multi_terminal per-session seed at implement — the BE-9035c regression
    where subagent fell through to ``multi_terminal_orchestrator``. Driven through the
    real FastMCP ``implement_project`` tool -> ``_detected_harness(ctx)`` -> implement()
    -> prompt-type selection -> render. The in-memory client resolves to the generic
    harness floor, so this exercises the harness-neutral subagent builder end-to-end."""
    new_client, _switch = lifecycle_mcp_client
    seeded = await _seed_product_project(
        db_session,
        primary_tenant_key,
        staging_status="staging_complete",
        launched=True,
        execution_mode="subagent",
    )
    await _seed_orchestrator_and_agent(db_session, primary_tenant_key, seeded["project"])

    async with new_client() as session:
        result = await session.call_tool("implement_project", {"project_id": seeded["project"].id})

    assert result.isError is False, _error_text(result)
    payload = _payload(result)
    assert payload["status"] == "ready"
    prompt = payload["prompt"]
    assert "PER-SESSION AGENT SEED" not in prompt, "subagent election leaked the multi_terminal seed"
    assert "Open a NEW SESSION" not in prompt, "subagent election leaked the multi_terminal seed"
    # still a real orchestrator implementation prompt (harness-neutral subagent builder).
    assert "get_job_mission" in prompt


@pytest.mark.parametrize("execution_mode", sorted(platform_registry.VALID_EXECUTION_MODES))
async def test_implement_project_mode_matrix_every_registry_mode_accepted(
    lifecycle_mcp_client, db_session, primary_tenant_key, execution_mode
):
    """BE-9035a regression (design §4 item 1): implement_project must accept EVERY
    execution_mode the registry knows about. Parametrized over the LIVE registry set
    (not a hand-copied list) so a 7th platform automatically joins this matrix and a
    future omission 400s here instead of shipping. The live bug: generic_mcp was
    missing from a hand-copied ``supported_execution_modes`` tuple in
    ``ThinClientLifecycleMixin.implement()``, so a solo generic_mcp project 400'd at
    implement -- proven fixed here at the MCP-transport boundary (the layer the bug
    actually shipped at)."""
    new_client, _switch = lifecycle_mcp_client
    seeded = await _seed_product_project(
        db_session,
        primary_tenant_key,
        staging_status="staging_complete",
        launched=True,
        execution_mode=execution_mode,
    )
    await _seed_orchestrator_and_agent(db_session, primary_tenant_key, seeded["project"])

    async with new_client() as session:
        result = await session.call_tool("implement_project", {"project_id": seeded["project"].id})

    assert result.isError is False, f"execution_mode={execution_mode!r}: {_error_text(result)}"
    payload = _payload(result)
    assert payload["status"] == "ready"
    assert payload["prompt"], f"execution_mode={execution_mode!r} produced an empty prompt"


async def test_implement_project_cross_tenant_not_found(
    lifecycle_mcp_client, db_session, primary_tenant_key, secondary_tenant_key
):
    new_client, switch = lifecycle_mcp_client
    # Tenant A owns a fully-launched project.
    switch.value = primary_tenant_key
    seeded = await _seed_product_project(
        db_session, primary_tenant_key, staging_status="staging_complete", launched=True
    )
    await _seed_orchestrator_and_agent(db_session, primary_tenant_key, seeded["project"])

    # Tenant B tries to implement tenant A's project -> not found (tenant isolation).
    switch.value = secondary_tenant_key
    async with new_client() as session:
        result = await session.call_tool("implement_project", {"project_id": seeded["project"].id})

    assert result.isError is True, "TENANT LEAK: tenant B must not reach tenant A's project"
    err = _error_text(result).lower()
    # Tenant B is blocked: production returns a clean not-found (tenant-scoped query
    # sees no row); the shared-test-session path trips the ORM tenant-context guard.
    # Either way tenant B never receives tenant A's prompt — that is the property.
    assert "not found" in err or "tenant" in err, f"expected a tenant-isolation block, got: {err!r}"
    assert "gate_not_passed" not in err and "ready" not in err


async def test_implement_project_cross_tenant_returns_clean_not_found_no_guard_leak(
    lifecycle_mcp_client, db_session, primary_tenant_key, secondary_tenant_key
):
    """BE-3006d regression (at the MCP transport layer): a cross-tenant
    implement_project trips ``TenantIsolationError`` (a plain RuntimeError) inside
    the accessor. The ``_call_tool`` catch-all must classify it as a KNOWN
    security-boundary rejection and re-raise a CLEAN, fixed "not found" — NOT
    sanitize it to the generic internal-error message (the regression PR #26's CE
    CI caught) and NOT surface the raw guard str() (which leaks internal guard
    phrasing + the model name).

    This asserts the real security PROPERTY, not just isError: the agent sees a
    truthful not-found and NONE of the guard internals.
    """
    new_client, switch = lifecycle_mcp_client
    switch.value = primary_tenant_key
    seeded = await _seed_product_project(
        db_session, primary_tenant_key, staging_status="staging_complete", launched=True
    )
    await _seed_orchestrator_and_agent(db_session, primary_tenant_key, seeded["project"])

    # Tenant B reaches for tenant A's project.
    switch.value = secondary_tenant_key
    async with new_client() as session:
        result = await session.call_tool("implement_project", {"project_id": seeded["project"].id})

    assert result.isError is True, "TENANT LEAK: tenant B must not reach tenant A's project"
    err = _error_text(result)
    err_lower = err.lower()

    # POSITIVE half of the contract: a clean, truthful not-found reaches the agent.
    assert "not found" in err_lower, f"expected a clean not-found, got: {err!r}"

    # NEGATIVE half: NONE of the tenant-guard internals leak to the agent. The raw
    # guard message is "...Tenant context required for ORM statement touching:
    # Project; ..." — assert each of those fragments is absent.
    for leak in ("ORM statement", "flush-derived", "Project", "Tenant context", "tenant_key"):
        assert leak not in err, f"tenant-guard internal leaked to the agent ({leak!r}): {err!r}"

    # And it must NOT have fallen back to the generic sanitized 500 message — that
    # IS the CE-mode regression this guards against (no "not found" in it).
    assert "unexpected internal error" not in err_lower, (
        f"cross-tenant block was sanitized to the generic 500 instead of clean not-found: {err!r}"
    )

    # No leak of a successful payload either.
    assert "gate_not_passed" not in err and '"ready"' not in err


# ---------------------------------------------------------------------------
# Equivalence: stage_project prompt == GET /api/prompts/staging prompt
# ---------------------------------------------------------------------------


async def test_stage_project_equivalent_to_rest_staging(lifecycle_mcp_client, db_session, primary_tenant_key):
    """stage_project's staging prompt is byte-identical to the REST staging
    endpoint's for the same project + mode.

    The REST endpoint is invoked FIRST (it creates the orchestrator and persists
    'staged'); stage_project then re-stages, and ThinClientPromptGenerator's
    find-or-create orchestrator returns the SAME orchestrator_id/agent_id, so the
    deterministic staging prompt must match exactly. Proves the tool reuses the
    engine and the shared extraction did not fork the generation path.
    """
    from unittest.mock import MagicMock

    from api.endpoints import prompts
    from giljo_mcp.services.project_service import ProjectService

    new_client, _switch = lifecycle_mcp_client
    seeded = await _seed_product_project(db_session, primary_tenant_key, execution_mode=None)

    current_user = MagicMock()
    current_user.id = uuid4()
    current_user.tenant_key = primary_tenant_key
    current_user.username = "equiv-user"

    ws_dep = MagicMock()
    ws_dep.is_available.return_value = False

    # BE-3006a: the endpoint now owns its staged-state write via
    # project_service.lifecycle.mark_staged. Calling the endpoint function
    # directly (not through FastAPI DI) means we must supply that service; wire
    # it to the same test session so the write lands in this transaction.
    tenant_manager = MagicMock()
    tenant_manager.get_current_tenant.return_value = primary_tenant_key
    project_service = ProjectService(
        db_manager=MagicMock(),
        tenant_manager=tenant_manager,
        test_session=db_session,
    )

    # REST first (tool=claude-code + execution_mode=claude_code_cli == mode "claude").
    rest_response = await prompts.generate_staging_prompt(
        project_id=seeded["project"].id,
        tool="claude-code",
        execution_mode="claude_code_cli",
        current_user=current_user,
        db=db_session,
        ws_dep=ws_dep,
        project_service=project_service,
    )

    async with new_client() as session:
        tool_result = await session.call_tool("stage_project", {"project_id": seeded["project"].id, "mode": "claude"})
    assert tool_result.isError is False, _error_text(tool_result)
    tool_payload = _payload(tool_result)

    assert tool_payload["prompt"] == rest_response.prompt, (
        "stage_project staging prompt must be content-equivalent to GET /api/prompts/staging"
    )
    assert tool_payload["orchestrator_id"] == rest_response.orchestrator_id


# ---------------------------------------------------------------------------
# Shared gate fn — direct unit matrix (no DB)
# ---------------------------------------------------------------------------


class _GateProject:
    def __init__(self, staging_status, implementation_launched_at):
        self.id = "p-gate"
        self.staging_status = staging_status
        self.implementation_launched_at = implementation_launched_at


# These are sync checks; async def keeps them compatible with the module-level
# asyncio pytestmark (no "sync function marked asyncio" warning) without awaiting.
async def test_check_implementation_allowed_staging_incomplete():
    with pytest.raises(ImplementationNotReadyError) as exc:
        ProjectStagingService.check_implementation_allowed(_GateProject("staged", None))
    assert exc.value.reason == "staging_incomplete"


async def test_check_implementation_allowed_not_launched():
    with pytest.raises(ImplementationNotReadyError) as exc:
        ProjectStagingService.check_implementation_allowed(_GateProject("staging_complete", None))
    assert exc.value.reason == "not_launched"
    # Byte-identical to the original inline 404 detail (REST behavior unchanged).
    assert exc.value.message == "Implementation has not been launched yet for this project."


async def test_check_implementation_allowed_passes_when_both_set():
    # Both preconditions met -> no raise.
    ProjectStagingService.check_implementation_allowed(_GateProject("staging_complete", datetime.now(UTC)))
