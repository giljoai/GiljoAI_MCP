# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6207 — STEP A assembly: the conductor runs ONE direct command (file-less).

The cold-start gap: a raw conductor reached CH_CHAIN_DRIVE STEP A but the spawn
command was a four-level nested-quoted one-liner an agent reformatted into wt-breaking
array form (0x80070002). BE-6207 reshapes STEP A to a FILE-LESS one-liner: the conductor
runs ONE direct terminal command ($PWD self-resolves the cwd, the tiny prompt inline),
substituting only two UUIDs. The conductor ALWAYS opens each sub-orch in its OWN FRESH
TERMINAL (every execution_mode); execution_mode governs only how the sub-orch spawns its
WORKERS.

These assembly tests pin:
  - STEP A carries the one-line direct spawn command (no files).
  - The fatal nested one-liner / Start-Process / file shapes are GONE (regression lock).
  - The VERBATIM directive is present (the load-bearing latitude reducer).
  - CH_CAPABILITY clause 2 is mode-INDEPENDENT fresh-terminal sub-orch spawn.
  - SOLO deletion test: chain_ctx=None leaks no terminal-spawn prose.

Pure-string assertions (no DB, no module-level mutable state) — parallel-safe.
Edition Scope: CE.
"""

from __future__ import annotations

import uuid

from giljo_mcp.services.protocol_sections.chapters_chain import (
    _build_ch_capability,
    _build_ch_chain_drive,
)


def _drive(execution_mode: str = "claude_code_cli") -> str:
    return _build_ch_chain_drive(
        run_id="RUN123",
        resolved_order=["p1", "p2"],
        current_index=0,
        execution_mode=execution_mode,
        conductor_agent_id="cond-1",
        job_id="job-1",
    )


# ---------------------------------------------------------------------------
# STEP A carries the atomic artifact (two files + one run line)
# ---------------------------------------------------------------------------


# BE-9035c collapse: the direct per-harness spawn commands (with the concrete
# `claude --dangerously-skip-permissions` binary baked in) now render on the
# 'multi_terminal' path; a subagent-folded mode gets the <your-harness> placeholder
# block instead. STEP A's direct wt/gnome commands are therefore asserted here on
# the multi_terminal render.
def test_step_a_has_windows_direct_wt_command() -> None:
    chapter = _drive("multi_terminal")
    assert "wt -w 0 new-tab --title 'giljo sub-orch' -d \"$PWD\"" in chapter, "STEP A carries the direct wt command"
    assert "claude --dangerously-skip-permissions" in chapter


def test_step_a_has_linux_direct_gnome_command() -> None:
    chapter = _drive("multi_terminal")
    assert 'gnome-terminal --working-directory="$PWD"' in chapter, "STEP A carries the direct gnome-terminal command"
    assert "claude --dangerously-skip-permissions" in chapter


def test_step_a_regression_no_nested_no_startprocess_no_files() -> None:
    """All 0x80070002 failure classes must never reappear in STEP A."""
    chapter = _drive("claude_code_cli")
    assert "Start-Process wt -ArgumentList '" not in chapter, "the nested single-string ArgumentList form is the bug"
    assert 'powershell.exe -Command "Start-Process wt' not in chapter
    # NB: the STEP A directive legitimately NAMES Start-Process as a "do NOT" — so we lock
    # the COMMAND shape (no files, direct wt) here and the exact no-Start-Process command
    # in test_be6205_conductor_spawn_render; we don't forbid the warning text itself.
    assert "launch.ps1" not in chapter and "suborch.txt" not in chapter, "file-less: no launcher/prompt FILES"
    assert "<YOUR_CWD>" not in chapter, "$PWD self-resolves the cwd; no placeholder for the agent to mangle"


def test_step_a_has_verbatim_directive() -> None:
    """The single sharp directive — reducing latitude is the whole point."""
    chapter = _drive("claude_code_cli")
    low = chapter.lower()
    assert "verbatim" in low, "STEP A must tell the conductor to copy the launcher verbatim"
    assert "-argumentlist" in low, "the directive must explicitly forbid -ArgumentList reformatting"
    assert "do not" in low


def test_step_a_substitutes_uuid_placeholders_inline() -> None:
    chapter = _drive("claude_code_cli")
    assert "<P_i>" in chapter
    assert "<SUB_ORCH_JOB_ID>" in chapter


def test_step_a_keeps_idempotent_reuse_resolution() -> None:
    """STEP A still resolves + reuses the already-minted sub-orch (BE-6198 idempotency)."""
    chapter = _drive("claude_code_cli")
    low = chapter.lower()
    assert "get_workflow_status" in chapter
    assert "idempotent" in low
    assert "already minted" in low or "already-minted" in low
    assert "never mints a duplicate" in low or "never a duplicate" in low


def test_step_a_fails_loud_on_headless() -> None:
    """Headless (no DISPLAY / WAYLAND_DISPLAY) → STOP + re-stage in a subagent mode."""
    chapter = _drive("claude_code_cli")
    assert "DISPLAY" in chapter
    assert "WAYLAND_DISPLAY" in chapter
    assert "re-stage" in chapter.lower()


# ---------------------------------------------------------------------------
# CH_CAPABILITY clause 2 — fresh-terminal sub-orch spawn, no Task() sub-orch language
# ---------------------------------------------------------------------------


def test_ch_capability_subagent_spawns_suborch_in_fresh_terminal() -> None:
    cap = _build_ch_capability(execution_mode="claude_code_cli", can_spawn_terminals=True)
    low = cap.lower()
    assert "fresh" in low and "terminal" in low, "sub-orch spawn is always a fresh terminal"
    assert "run each p_i as a real task()" not in low, "the old Task()-spawns-the-sub-orch language must be gone"
    assert "worker" in low
    assert "REAL Task()" in cap, "Task() is the sub-orch's WORKER mechanism in subagent modes"


def test_ch_capability_multi_terminal_spawns_suborch_in_fresh_terminal() -> None:
    cap = _build_ch_capability(execution_mode="multi_terminal", can_spawn_terminals=True)
    low = cap.lower()
    assert "fresh" in low and "terminal" in low
    assert "worker" in low


# ---------------------------------------------------------------------------
# SOLO deletion test — no terminal-spawn prose leaks into a solo protocol
# ---------------------------------------------------------------------------


def test_solo_protocol_has_no_terminal_spawn_leak() -> None:
    from giljo_mcp.services.protocol_builder import _build_orchestrator_protocol

    solo = _build_orchestrator_protocol(
        cli_mode=True,
        project_id=str(uuid.uuid4()),
        orchestrator_id="job-solo",
        tenant_key="tk_solo",
        include_implementation_reference=False,
        chain_ctx=None,
    )
    blob = "\n".join(str(v) for v in solo.values())
    assert "launch.ps1" not in blob, "solo render must not leak the conductor launcher artifact"
    assert "gnome-terminal" not in blob
    assert "CH_CHAIN_DRIVE" not in blob
