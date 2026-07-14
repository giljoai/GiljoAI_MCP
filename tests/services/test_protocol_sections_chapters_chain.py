# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6165d — chain prompt chapters regression tests.

Covers the DoD matrix for _build_orchestrator_protocol with chain_ctx:

1. conductor + is_staging=True  → ch_chain_staging + ch_capability; NOT ch_chain_drive.
2. conductor + is_staging=False → ch_chain_drive + ch_capability; NOT ch_chain_staging.
   (BE-6215: the former ch_conductor chapter is folded INTO ch_chain_drive.)
3. chain_ctx=None (solo)        → NONE of ch_chain_staging/ch_chain_drive/ch_capability present;
                                   dict is byte-identical to a no-chain_ctx call.
4. sub_orchestrator role        → none of the 3 chain chapters render.
5. CH_CAPABILITY content differs for multi_terminal vs subagent-only mode.
6. PlatformRegistry (BE-9035c): can_spawn_terminals on the 2 MODES (multi_terminal True,
   subagent False); TERMINAL_CAPABLE_MODES == {multi_terminal}.
7. Frozenset identity: models.sequence_runs.VALID_EXECUTION_MODES is
   platform_registry.VALID_EXECUTION_MODES (same object, same 2 canonical tokens).

All tests are pure (no DB, no module-level mutable state) — safe under pytest-xdist -n auto.

Edition Scope: CE.
"""

from __future__ import annotations

import uuid


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_COMMON_ARGS = {
    "cli_mode": True,
    "project_id": "proj-chain-test",
    "orchestrator_id": "job-chain-test",
    "tenant_key": "tk_chain_test",
    "include_implementation_reference": False,
}

_CHAIN_CHAPTERS = frozenset({"ch_capability", "ch_chain_staging", "ch_chain_drive"})


def _make_chain_ctx(
    *,
    role: str = "conductor",
    is_staging: bool = True,
    resolved_order: list[str] | None = None,
    conductor_agent_id: str | None = None,
    execution_mode: str = "multi_terminal",
):
    """Return a ChainContext without a DB round-trip.

    BE-6177: ChainContext now carries the run's execution_mode (the chain chapters
    are driven off it, not the tool param). Defaults to multi_terminal.
    """
    from giljo_mcp.services.sequence_chain_context import ChainContext

    return ChainContext(
        run_id=str(uuid.uuid4()),
        role=role,
        current_index=0,
        resolved_order=resolved_order or [str(uuid.uuid4()), str(uuid.uuid4())],
        is_staging=is_staging,
        conductor_agent_id=conductor_agent_id or str(uuid.uuid4()),
        execution_mode=execution_mode,
    )


def _build(**kwargs):
    from giljo_mcp.services.protocol_builder import _build_orchestrator_protocol

    return _build_orchestrator_protocol(**_COMMON_ARGS, **kwargs)


# ---------------------------------------------------------------------------
# 1. conductor + is_staging=True
# ---------------------------------------------------------------------------


def test_conductor_staging_emits_staging_and_capability_not_drive() -> None:
    """Conductor at staging phase: ch_chain_staging + ch_capability; NOT ch_chain_drive."""
    conductor_id = str(uuid.uuid4())
    ctx = _make_chain_ctx(role="conductor", is_staging=True, conductor_agent_id=conductor_id)
    result = _build(chain_ctx=ctx, conductor_agent_id=conductor_id)

    assert "ch_capability" in result, "Conductor at staging must include ch_capability"
    assert "ch_chain_staging" in result, "Conductor at staging must include ch_chain_staging"
    assert "ch_chain_drive" not in result, "ch_chain_drive must NOT appear at staging phase"

    # BE-6177 (B1): ch_conductor is phase-gated to IMPLEMENTATION. During staging
    # its park-loop (set_agent_status "sleeping") would hit STAGING_LOCK (403) and
    # contradicts CH_CHAIN_STAGING's "STOP after staging" — so it must NOT render.
    assert "ch_conductor" not in result, "ch_conductor must NOT render during staging (phase-gated, B1)"

    # Sanity: run_id and project count appear in the staging chapter
    assert ctx.run_id in result["ch_chain_staging"], "run_id must appear in CH_CHAIN_STAGING"
    assert f"{len(ctx.resolved_order)}-project" in result["ch_chain_staging"], (
        "Project count must appear in CH_CHAIN_STAGING"
    )


# ---------------------------------------------------------------------------
# 2. conductor + is_staging=False (implementation)
# ---------------------------------------------------------------------------


def test_conductor_implementation_emits_drive_and_capability_not_staging() -> None:
    """Conductor at implementation phase: ch_chain_drive + ch_capability; NOT ch_chain_staging.
    BE-6215: ch_conductor is folded into ch_chain_drive (no separate chapter key)."""
    conductor_id = str(uuid.uuid4())
    ctx = _make_chain_ctx(role="conductor", is_staging=False, conductor_agent_id=conductor_id)
    result = _build(chain_ctx=ctx, conductor_agent_id=conductor_id)

    assert "ch_capability" in result, "Conductor at implementation must include ch_capability"
    assert "ch_chain_drive" in result, "Conductor at implementation must include ch_chain_drive"
    assert "ch_chain_staging" not in result, "ch_chain_staging must NOT appear at implementation phase"
    assert "ch_conductor" not in result, "BE-6215: ch_conductor is folded into ch_chain_drive (no separate key)"
    assert "YOU ARE ADDRESSABLE: USER DIRECTIVE RELAY" in result["ch_chain_drive"], (
        "the folded directive-relay protocol must render inside ch_chain_drive"
    )

    # Sanity: run_id appears in the drive chapter. BE-6186 removed the inert
    # TERMINATE_CHAIN escape hatch (the server ignored it); the real exit is the
    # dashboard back-out, so the drive chapter must NOT carry a TERMINATE_CHAIN clause.
    assert ctx.run_id in result["ch_chain_drive"], "run_id must appear in CH_CHAIN_DRIVE"
    assert "TERMINATE_CHAIN" not in result["ch_chain_drive"], (
        "BE-6186: the inert TERMINATE_CHAIN clause must be gone from CH_CHAIN_DRIVE"
    )


def test_conductor_generic_mcp_drive_uses_placeholder_not_validated_claude() -> None:
    """BE-9033 (failing-layer regression) — a generic_mcp chain conductor's CH_CHAIN_DRIVE
    STEP A must embed the <your-harness> placeholder spawn block, NOT the multi-CLI listing
    with [claude | VALIDATED]. That tag is what made an opencode conductor spawn a CLAUDE
    terminal for its sub-orchestrator in the field. This asserts through the assembled
    conductor mission chapter (the layer the agent actually receives), one above the
    isolated render_suborch_spawn_command unit tests."""
    conductor_id = str(uuid.uuid4())
    ctx = _make_chain_ctx(
        role="conductor", is_staging=False, conductor_agent_id=conductor_id, execution_mode="generic_mcp"
    )
    drive = _build(chain_ctx=ctx, conductor_agent_id=conductor_id)["ch_chain_drive"]

    assert "<your-harness>" in drive, "generic_mcp STEP A must carry the self-substitution placeholder"
    assert "VALIDATED" not in drive, "the [claude | VALIDATED] tag must not reach a generic_mcp conductor"
    assert "[claude" not in drive, "no per-harness claude launch line for a generic_mcp conductor"
    assert "cmd /k <your-harness> --prompt" in drive, "Windows launch is the BE-9015 `cmd /k` form"


# ---------------------------------------------------------------------------
# 3. chain_ctx=None — solo byte-identical
# ---------------------------------------------------------------------------


def test_solo_path_byte_identical_to_no_chain_ctx() -> None:
    """chain_ctx=None → none of the 3 chain chapters; dict identical to baseline call."""
    baseline = _build()
    explicit_none = _build(chain_ctx=None)

    assert baseline == explicit_none, "Passing chain_ctx=None must produce byte-identical output to omitting it"

    for ch in _CHAIN_CHAPTERS:
        assert ch not in baseline, f"{ch} must not appear in solo (no-chain) output"


# ---------------------------------------------------------------------------
# 4. sub_orchestrator — no chain chapters
# ---------------------------------------------------------------------------


def test_sub_orchestrator_emits_no_chain_chapters() -> None:
    """sub_orchestrator role → none of the 3 chain chapters render."""
    ctx = _make_chain_ctx(role="sub_orchestrator", is_staging=False)
    result = _build(chain_ctx=ctx)

    for ch in _CHAIN_CHAPTERS:
        assert ch not in result, f"sub_orchestrator must NOT emit {ch}"


# ---------------------------------------------------------------------------
# 5. CH_CAPABILITY branch differs by mode + can_spawn_terminals
# ---------------------------------------------------------------------------


def test_ch_capability_multi_terminal_branch() -> None:
    """BE-6182: multi_terminal renders the GUARANTEED-isolation context-hygiene line
    + the 4-part flat contract (no runtime probe)."""
    from giljo_mcp.services.protocol_sections.chapters_chain import _build_ch_capability

    cap = _build_ch_capability(execution_mode="multi_terminal", can_spawn_terminals=True)

    assert "EXECUTION MODE = multi_terminal" in cap, "must state the resolved mode as fact"
    assert "IMMUTABLE" in cap, "must state the mode is immutable"
    assert "GUARANTEED" in cap, "multi_terminal context isolation is guaranteed"
    assert "FAIL LOUD" in cap, "fail-loud fallback must replace the silent downgrade"
    # The removed runtime re-probe must be gone.
    assert "VERIFY" not in cap, "BE-6182: the runtime terminal self-probe is removed"
    assert "try to spawn" not in cap.lower(), "BE-6182: no 'try to spawn a terminal' probe"


def test_ch_capability_subagent_mode_isolation_is_best_effort() -> None:
    """BE-6205 (REVERSES the BE-6182 clause-2 framing): in a subagent mode the conductor
    STILL opens each sub-orchestrator in its OWN FRESH TERMINAL (sub-orch isolation
    GUARANTEED). Task()/subagent is the WORKER mechanism — its isolation is BEST-EFFORT.
    The old "run each P_i as a REAL Task()" sub-orch-spawn language is gone."""
    from giljo_mcp.services.protocol_sections.chapters_chain import _build_ch_capability

    cap = _build_ch_capability(execution_mode="claude_code_cli", can_spawn_terminals=False)
    low = cap.lower()

    assert "claude_code_cli" in cap, "must name the resolved subagent mode"
    # Sub-orch spawn is a fresh terminal in EVERY mode now (isolation guaranteed).
    assert "fresh" in low and "terminal" in low, "sub-orch spawn must be a fresh terminal"
    assert "GUARANTEED" in cap, "BE-6205: fresh-terminal sub-orch isolation IS guaranteed"
    # Task() survives ONLY as the WORKER mechanism, worded best-effort.
    assert "REAL Task()" in cap, "Task() is the sub-orch's WORKER mechanism in a subagent mode"
    assert "WORKER" in cap, "the Task() form is scoped to WORKERS, not sub-orch spawning"
    assert "BEST-EFFORT" in cap, "worker isolation must be worded as best-effort"
    assert "run each p_i as a real task()" not in low, "the reversed sub-orch-spawn-via-Task() language must be gone"
    assert "inline" in low, "must forbid running work inline"


def test_ch_capability_is_a_contract_not_a_probe() -> None:
    """BE-6182: every render is a flat server-resolved contract — no self-downgrade,
    no 'if unsure' decision tree, and the gate + immutability clauses are present."""
    from giljo_mcp.services.protocol_sections.chapters_chain import _build_ch_capability

    for mode, spawn in (("multi_terminal", True), ("claude_code_cli", True), ("codex_cli", False)):
        cap = _build_ch_capability(execution_mode=mode, can_spawn_terminals=spawn)
        assert "CONTRACT" in cap, f"{mode}: must render as a contract"
        # BE-6206 (§14): CH_CAPABILITY is gateless — the conductor's fresh-terminal
        # spawn IS each project's release. No launch_implementation gate, no
        # staging_complete wait survives in the spawn contract.
        assert "no per-project gate" in cap.lower(), f"{mode}: must state there is NO per-project gate"
        assert "launch_implementation" not in cap.lower(), f"{mode}: gateless — launch_implementation must be gone"
        assert "staging_complete" not in cap.lower(), f"{mode}: gateless — staging_complete wait must be gone"
        assert "re-probe" in cap.lower() or "do not re-probe" in cap.lower(), (
            f"{mode}: must instruct NOT to re-probe the harness"
        )
        # The fail-loud fallback must FORBID a self-downgrade (the prose may name
        # "no silent downgrade" as the rule), and must never instruct the agent to
        # downgrade itself ("if unsure ... downgrade to subagents").
        assert "never silently switch modes" in cap.lower(), f"{mode}: must forbid self-switching modes"
        assert "if unsure" not in cap.lower(), f"{mode}: the old 'if unsure' downgrade tree must be gone"


def test_conductor_ch_capability_present_for_mode() -> None:
    """Assembler renders ch_capability for a multi_terminal conductor (the flat
    contract, driven off the run's execution_mode)."""
    from giljo_mcp.services.protocol_builder import _build_orchestrator_protocol

    ctx = _make_chain_ctx(role="conductor", is_staging=True)
    # multi_terminal + cli_mode=False: effective_tool stays "multi_terminal"
    result = _build_orchestrator_protocol(
        cli_mode=False,
        project_id="proj-chain-mode-test",
        orchestrator_id="job-chain-mode-test",
        tenant_key="tk_chain_mode",
        include_implementation_reference=False,
        tool="multi_terminal",
        chain_ctx=ctx,
    )
    cap = result.get("ch_capability", "")
    assert cap, "ch_capability must be present for a conductor"
    assert "EXECUTION MODE = multi_terminal" in cap, (
        f"Assembler must render the multi_terminal contract; got: {cap[:300]!r}"
    )


# ---------------------------------------------------------------------------
# 6. PlatformRegistry: can_spawn_terminals on all rows + TERMINAL_CAPABLE_MODES
# ---------------------------------------------------------------------------


def test_platform_registry_can_spawn_terminals_all_rows() -> None:
    """BE-9035c: the 2 MODES carry can_spawn_terminals — multi_terminal True, subagent False.

    The collapse generalized the old generic_mcp opt-out to the WHOLE subagent mode:
    subagent terminal ability is a runtime session/harness property, never assumed from
    the mode. (HARNESSES have no can_spawn_terminals — terminal ability is not a harness
    fact either; it is a live SESSION capability.)"""
    from giljo_mcp.platform_registry import MODES

    assert len(MODES) == 2, f"Expected 2 registered modes, got {len(MODES)}"
    by_mode = {m.execution_mode: m for m in MODES}
    assert by_mode["multi_terminal"].can_spawn_terminals is True, (
        "multi_terminal is intrinsically terminal-capable (a human opens a terminal per agent)"
    )
    assert by_mode["subagent"].can_spawn_terminals is False, (
        "subagent terminal ability is a runtime session property, never assumed from the mode"
    )


def test_terminal_capable_modes_populated() -> None:
    """BE-9035c: TERMINAL_CAPABLE_MODES == {multi_terminal}; subagent is the one mode absent."""
    from giljo_mcp.platform_registry import TERMINAL_CAPABLE_MODES, VALID_EXECUTION_MODES

    assert isinstance(TERMINAL_CAPABLE_MODES, frozenset), "TERMINAL_CAPABLE_MODES must be a frozenset"
    assert {"multi_terminal"} == TERMINAL_CAPABLE_MODES, (
        f"only multi_terminal is intrinsically terminal-capable, got {TERMINAL_CAPABLE_MODES}"
    )
    assert VALID_EXECUTION_MODES - {"subagent"} == TERMINAL_CAPABLE_MODES, (
        "subagent (BE-9035c generalizes the old generic_mcp opt-out to the whole mode) is the "
        "one valid mode absent from TERMINAL_CAPABLE_MODES"
    )


# ---------------------------------------------------------------------------
# 7. Frozenset identity: sequence_runs.VALID_EXECUTION_MODES is platform_registry.VALID_EXECUTION_MODES
# ---------------------------------------------------------------------------


def test_valid_execution_modes_same_object() -> None:
    """models.sequence_runs.VALID_EXECUTION_MODES is the same object as platform_registry's.

    BE-6165d reconciliation: sequence_runs.py now imports from platform_registry
    instead of re-declaring a parallel frozenset literal. The identity test
    confirms the reconciliation is in place and that a 6th platform added to
    platform_registry is automatically accepted in the sequence layer.
    """
    import giljo_mcp.models.sequence_runs as sr_module
    import giljo_mcp.platform_registry as pr_module

    assert sr_module.VALID_EXECUTION_MODES is pr_module.VALID_EXECUTION_MODES, (
        "sequence_runs.VALID_EXECUTION_MODES must be the SAME object as "
        "platform_registry.VALID_EXECUTION_MODES (imported, not re-declared)"
    )
    assert frozenset({"multi_terminal", "subagent"}) == sr_module.VALID_EXECUTION_MODES, (
        "BE-9035c: VALID_EXECUTION_MODES must contain exactly the 2 canonical execution modes"
    )


# ---------------------------------------------------------------------------
# 8. Bonus: solo byte-identical round-trip (the 3 existing tests must stay green)
# ---------------------------------------------------------------------------


def test_conductor_staging_does_not_pollute_solo_render() -> None:
    """A conductor render and a solo render have disjoint chapter key sets."""
    solo = _build()
    conductor_id = str(uuid.uuid4())
    ctx = _make_chain_ctx(role="conductor", is_staging=True, conductor_agent_id=conductor_id)
    conductor = _build(chain_ctx=ctx, conductor_agent_id=conductor_id)

    # chain chapters appear in conductor, not in solo
    for ch in _CHAIN_CHAPTERS:
        assert ch not in solo, f"{ch} leaked into solo render"
    assert "ch_chain_staging" in conductor

    # core chapters present in both
    for core_ch in ("ch1_your_mission", "ch2_startup_sequence", "ch3_agent_spawning_rules"):
        assert core_ch in solo
        assert core_ch in conductor


# ---------------------------------------------------------------------------
# BE-6177: staging-prompt hardening regression (A2 / A4 / B1 / B2)
# ---------------------------------------------------------------------------


def test_chain_staging_emits_short_mode_token_not_execution_mode() -> None:
    """A2: CH_CHAIN_STAGING calls stage_project(mode="claude"), NEVER
    execution_mode="claude_code_cli" (wrong param name AND wrong vocabulary —
    the prior text hard-failed the first write of every chain stage)."""
    from giljo_mcp.services.protocol_sections.chapters_chain import _build_ch_chain_staging

    chapter = _build_ch_chain_staging(
        run_id="run-x",
        resolved_order=["head", "p2"],
        execution_mode="claude_code_cli",
        job_id="job-x",
    )
    assert 'mode="claude"' in chapter, "must emit the short stage mode token"
    assert "claude_code_cli" not in chapter, "must NOT leak the execution_mode vocabulary into stage_project"
    assert 'execution_mode="' not in chapter, "must NOT call stage_project with the execution_mode= param"


def test_chain_staging_states_complete_job_is_last_and_stages_all() -> None:
    """B2 + BE-6186: the authoritative staging script states complete_job is the LAST
    call and stages EVERY project (head included, symmetric) — no stranded 2..N trap."""
    from giljo_mcp.services.protocol_sections.chapters_chain import _build_ch_chain_staging

    chapter = _build_ch_chain_staging(
        run_id="run-x", resolved_order=["head", "p2", "p3"], execution_mode="claude_code_cli", job_id="job-77"
    )
    low = chapter.lower()
    assert "complete_job" in low and "last" in low, "must state complete_job is the LAST call"
    assert "job-77" in chapter, "the real conductor job_id must appear"
    # BE-6186: every project (including the head) is staged in one symmetric pass.
    assert "every project" in low, "must describe staging EVERY project symmetrically"


def test_chain_drive_threads_real_job_id() -> None:
    """A4: CH_CHAIN_DRIVE uses the real job_id, not a <your job_id> placeholder."""
    from giljo_mcp.services.protocol_sections.chapters_chain import _build_ch_chain_drive

    chapter = _build_ch_chain_drive(
        run_id="run-x",
        resolved_order=["head", "p2"],
        current_index=0,
        execution_mode="claude_code_cli",
        conductor_agent_id="cond-1",
        job_id="job-real-99",
    )
    assert "job-real-99" in chapter, "real job_id must be threaded into progress/closeout calls"
    assert "<your job_id>" not in chapter, "the placeholder must be replaced"


def test_ch_capability_probe_removed_regardless_of_can_spawn() -> None:
    """BE-6182 (supersedes BE-6177 A4): the runtime 'try to open a terminal'
    self-probe is removed for BOTH can_spawn values — the server-resolved mode is
    authoritative and the fail-loud fallback is the only honest escape hatch."""
    from giljo_mcp.services.protocol_sections.chapters_chain import _build_ch_capability

    for spawn in (True, False):
        cap = _build_ch_capability(execution_mode="claude_code_cli", can_spawn_terminals=spawn)
        assert "CAN YOU OPEN AN INDEPENDENT OS TERMINAL" not in cap, (
            f"can_spawn={spawn}: the runtime probe must be gone"
        )
        # The contract still tells a genuinely-incapable harness to fail loud.
        assert "RE-STAGE" in cap, f"can_spawn={spawn}: fail-loud fallback must instruct re-staging"


def test_conductor_implementation_emits_conductor_chapter() -> None:
    """BE-6215: the conductor addressability + directive-relay protocol (formerly the
    standalone ch_conductor chapter, phase-gated to implementation) is FOLDED into
    ch_chain_drive — so at implementation it renders inside the drive chapter, embedding
    the conductor's agent_id, and there is no separate ch_conductor key."""
    conductor_id = str(uuid.uuid4())
    ctx = _make_chain_ctx(role="conductor", is_staging=False, conductor_agent_id=conductor_id)
    result = _build(chain_ctx=ctx, conductor_agent_id=conductor_id)
    assert "ch_conductor" not in result, "BE-6215: no separate ch_conductor chapter (folded)"
    drive = result["ch_chain_drive"]
    assert "YOU ARE ADDRESSABLE: USER DIRECTIVE RELAY" in drive, "directive-relay protocol must live in ch_chain_drive"
    assert "DIRECTIVE RELAY" in drive and "NO WORKER-PROTOCOL FORK" in drive, "relay + no-worker-fork must survive"
    assert conductor_id in drive, "the conductor's agent_id must be embedded in the drive chapter"


# ---------------------------------------------------------------------------
# BE-6186: project-less symmetric-head conductor staging (no agents, no dual-hat)
# ---------------------------------------------------------------------------


def test_chain_staging_head_is_symmetric_not_special() -> None:
    """BE-6186: the head is symmetric with 2..N. The script must NOT call the head
    'already staged' or instruct spawning the head's agents (the dual-hat collapse)."""
    from giljo_mcp.services.protocol_sections.chapters_chain import _build_ch_chain_staging

    chapter = _build_ch_chain_staging(
        run_id="run-x", resolved_order=["head-pid", "p2"], execution_mode="multi_terminal", job_id="job-x"
    )
    low = chapter.lower()
    assert "already staged" not in low, "BE-6186: the dual-hat 'head already staged' language must be gone"
    assert "symmetric" in low, "must state the head is symmetric with the rest"
    assert "head-pid" in chapter, "the head project id must appear in the run order"


def test_chain_staging_spawns_no_agents_and_stages_every_project() -> None:
    """BE-6186: the conductor spawns NO agents and stages EVERY project (head included)
    with its own sub-orchestrator. No two-phase / mission-less agent-spawn prose."""
    from giljo_mcp.services.protocol_sections.chapters_chain import _build_ch_chain_staging

    chapter = _build_ch_chain_staging(
        run_id="run-x", resolved_order=["head", "p2"], execution_mode="multi_terminal", job_id="job-x"
    )
    low = chapter.lower()
    assert "two-phase" not in low, "BE-6186: the head agent-spawn (two-phase) prose must be gone"
    assert "mission-less" not in low, "BE-6186: no mission-less agent-spawn for the conductor"
    assert "spawn no agents" in low, "the conductor must be told to spawn NO agents"
    assert "stage_project" in chapter, "the conductor stages each project's sub-orchestrator"
    # The conductor writes the chain mission on its OWN job, not via a head project mission.
    assert 'update_job_mission(job_id="job-x"' in chapter, "chain mission is written to the conductor's own job"


def test_chain_staging_writes_chain_mission_to_own_job_not_head_project() -> None:
    """BE-6186: the chain mission is written via update_job_mission on the conductor's
    OWN job_id, NOT via update_project_mission(head_pid) (the dropped dual-hat path)."""
    from giljo_mcp.services.protocol_sections.chapters_chain import _build_ch_chain_staging

    chapter = _build_ch_chain_staging(
        run_id="run-x", resolved_order=["head-pid", "p2"], execution_mode="multi_terminal", job_id="job-77"
    )
    assert "job-77" in chapter, "the conductor's own job_id must appear"
    assert 'update_job_mission(job_id="job-77"' in chapter, "chain mission goes to update_job_mission on own job"
    # The dropped dual-hat write (chain mission onto the head project) must be gone.
    assert 'update_project_mission(project_id="head-pid", mission=<chain' not in chapter, (
        "BE-6186: the chain mission must NOT be written onto the head project"
    )


# ---------------------------------------------------------------------------
# BE-6208d: conductor closeout-precedence contradiction reconciled in-line
# ---------------------------------------------------------------------------


def test_chain_drive_phase3_closeout_line_carries_override_adjacent() -> None:
    """BE-6208d: the conductor chapter must NOT quote the solo PHASE 3
    "complete_job your orchestrator job" instruction without the override
    (does-NOT-apply / overridden) framing adjacent — so a blind agent can never
    follow the solo finale wrong-first."""
    from giljo_mcp.services.protocol_sections.chapters_chain import _build_ch_chain_drive

    chapter = _build_ch_chain_drive(
        run_id="run-x",
        resolved_order=["head", "p2"],
        current_index=0,
        execution_mode="multi_terminal",
        conductor_agent_id="cond-1",
        job_id="job-real-99",
    )

    quote = "complete_job your\norchestrator job"
    idx = chapter.find(quote)
    assert idx != -1, "the solo PHASE 3 closeout line must be quoted so it can be explicitly overridden"

    # A window around the quote must carry the override framing — the instruction
    # is never presented unconditionally.
    window = chapter[max(0, idx - 200) : idx + 200].lower()
    assert "does not apply" in window or "overridden" in window, (
        "the quoted PHASE 3 closeout line must have override framing adjacent"
    )


def test_chain_drive_override_precedes_series_summary_completion() -> None:
    """BE-6208d: the in-force override appears BEFORE the SERIES SUMMARY's
    valid complete_job — the contradiction resolves immediate-first, not deferred."""
    from giljo_mcp.services.protocol_sections.chapters_chain import _build_ch_chain_drive

    chapter = _build_ch_chain_drive(
        run_id="run-x",
        resolved_order=["head", "p2"],
        current_index=0,
        execution_mode="multi_terminal",
        conductor_agent_id="cond-1",
        job_id="job-real-99",
    )
    low = chapter.lower()
    override_idx = low.find("conductor precedence")
    summary_idx = low.find("series summary")
    assert 0 <= override_idx < summary_idx, "the override must be front-loaded, ahead of the SERIES SUMMARY finale"
    # The override must explicitly forbid calling complete_job at the precedence point.
    assert "do not call complete_job" in low, "the override must explicitly forbid an early conductor complete_job"


# ---------------------------------------------------------------------------
# BE-6211b: sub-orchestrator step-7 closeout order (REAL BUG — stalls chain advance)
# ---------------------------------------------------------------------------


def _suborch(execution_mode: str = "multi_terminal"):
    from giljo_mcp.services.protocol_sections.chapters_chain import _build_ch_sub_orchestrator

    return _build_ch_sub_orchestrator(
        run_id="run-x",
        position=2,
        n_projects=3,
        execution_mode=execution_mode,
    )


def _suborch_step7(text: str) -> str:
    """Return the step-7 region of a CH_SUB_ORCHESTRATOR render (closeout step)."""
    start = text.find("7. CLOSE OUT")
    assert start != -1, "CH_SUB_ORCHESTRATOR must contain a step 7 (CLOSE OUT)"
    return text[start:]


def test_suborch_step7_complete_job_before_write_project_closeout() -> None:
    """BE-6211b (REAL BUG): the sub-orchestrator's step-7 closeout must call
    complete_job BEFORE write_project_closeout. The inverse raises
    COMPLETION_BLOCKED (the orchestrator execution is still open when
    write_project_closeout's readiness gate runs) and stalls every chain advance.
    Server-true order matches the solo PHASE-3 closeout + the existing readiness gate."""
    step7 = _suborch_step7(_suborch())

    cj = step7.find("complete_job")
    wpc = step7.find("write_project_closeout")
    assert cj != -1, "step 7 must name complete_job"
    assert wpc != -1, "step 7 must name write_project_closeout"
    assert cj < wpc, (
        "complete_job must come BEFORE write_project_closeout in step 7 (server-enforced "
        "readiness gate); the inverse raises COMPLETION_BLOCKED and stalls the chain"
    )


def test_suborch_step7_is_mode_agnostic_byte_identical() -> None:
    """BE-6211b: step 7 is NOT execution_mode-branched, so the closeout ordering
    renders byte-identical for solo-style (multi_terminal) and subagent
    (claude_code_cli) modes — no mode can follow the wrong order."""
    assert _suborch_step7(_suborch("multi_terminal")) == _suborch_step7(_suborch("claude_code_cli")), (
        "step 7 must be byte-identical across execution modes (mode-agnostic closeout)"
    )


# ---------------------------------------------------------------------------
# BE-6221e: conductor HALT-after-staging human-in-the-loop gate (chain-only prose)
# ---------------------------------------------------------------------------


def test_chain_staging_halts_for_user_go_after_staging() -> None:
    """BE-6221e: CH_CHAIN_STAGING's end-of-staging section firmly HALTS the conductor
    until the user's EXPLICIT GO — report the staged plan + chain mission, then STOP; do
    NOT spawn / drive / re-call get_job_mission to start driving until the user says go
    (or presses 'Implement Chain')."""
    from giljo_mcp.services.protocol_sections.chapters_chain import _build_ch_chain_staging

    chapter = _build_ch_chain_staging(
        run_id="run-go", resolved_order=["p1", "p2"], execution_mode="multi_terminal", job_id="job-go"
    )
    low = chapter.lower()
    assert "halt after staging" in low, "the staging chapter must firmly HALT after staging"
    assert "explicit go" in low, "must require the user's EXPLICIT GO"
    assert "implement chain" in low, "must name the dashboard GO equivalent"
    assert "do not re-call get_job_mission" in low, "must forbid self-driving via get_job_mission"
    assert "do not drive" in low, "must forbid driving before the GO"
    assert "do not spawn any sub-orchestrator" in low, "must forbid spawning before the GO"


def test_chain_drive_proceeds_only_after_user_go() -> None:
    """BE-6221e: the top of CH_CHAIN_DRIVE reinforces the gate — proceed ONLY after the
    user's explicit GO; if it has not been given the conductor is not cleared to drive."""
    from giljo_mcp.services.protocol_sections.chapters_chain import _build_ch_chain_drive

    chapter = _build_ch_chain_drive(
        run_id="run-go",
        resolved_order=["p1", "p2"],
        current_index=0,
        execution_mode="multi_terminal",
        conductor_agent_id="cond-go",
        job_id="job-go",
    )
    low = chapter.lower()
    assert "proceed only after the user's explicit go" in low, "the drive chapter must gate on the user's GO"
    assert "not cleared to drive" in low, "must state the conductor is not cleared to drive without the GO"


_BE6221E_GO_GATE_STRINGS = (
    "HALT AFTER STAGING",
    "WAIT FOR THE USER'S EXPLICIT GO",
    "PROCEED ONLY AFTER THE USER'S EXPLICIT GO",
)


def test_be6221e_go_gate_prose_absent_from_solo_render() -> None:
    """SOLO IS SACRED: the BE-6221e firm HALT-for-GO prose lives only in the chain-gated
    chapters — none of it appears in a solo (chain_ctx=None) orchestrator render."""
    solo = _build()  # chain_ctx omitted -> solo path
    blob = "\n".join(str(v) for v in solo.values())
    for needle in _BE6221E_GO_GATE_STRINGS:
        assert needle not in blob, f"BE-6221e chain-only GO-gate prose leaked into the solo render: {needle!r}"
