# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6211a — tool-surface contract reconciliation regression tests.

Covers the two RED-GREEN DoD assertions for the contract-coherence sweep:

1. health_check reports the INSTALLED version (get_installed_version()), not the
   stale hardcoded "1.0.0" (wart d, a real bug).
2. CH_CHAIN_DRIVE's STEP B + crash-resume read ``ready_to_advance`` as THE
   advance signal (C-5.2), while keeping the "do NOT advance on status alone"
   guard, and the drive chapter renders byte-identical for solo-style
   (multi_terminal) and subagent (claude_code_cli) execution modes.

All tests are pure (no DB, no module-level mutable state) — safe under pytest-xdist.

Edition Scope: CE.
"""

from __future__ import annotations

import asyncio


# ---------------------------------------------------------------------------
# 1. health_check version is the installed version, not a stale literal
# ---------------------------------------------------------------------------


def test_health_check_version_is_installed_version() -> None:
    """wart d (real bug): health_check must report get_installed_version(), not '1.0.0'."""
    from giljo_mcp.services.orchestration_service import OrchestrationService
    from giljo_mcp.services.version_service import get_installed_version

    result = asyncio.run(OrchestrationService.health_check())

    assert result["version"] == get_installed_version(), (
        "health_check version must equal the installed VERSION, not a hardcoded literal"
    )
    assert result["version"] != "1.0.0" or get_installed_version() == "1.0.0", (
        "the stale hardcoded '1.0.0' must be gone (unless the installed version genuinely is 1.0.0)"
    )


# ---------------------------------------------------------------------------
# 2. CH_CHAIN_DRIVE re-points to ready_to_advance + byte-identical across modes
# ---------------------------------------------------------------------------


def _drive(execution_mode: str = "multi_terminal"):
    from giljo_mcp.services.protocol_sections.chapters_chain import _build_ch_chain_drive

    return _build_ch_chain_drive(
        run_id="run-x",
        resolved_order=["head", "p2"],
        current_index=0,
        execution_mode=execution_mode,
        conductor_agent_id="cond-1",
        job_id="job-real-99",
    )


def test_chain_drive_uses_ready_to_advance_signal() -> None:
    """C-5.2: STEP B + crash-resume read ready_to_advance as THE go-signal; the
    'do NOT advance on status alone' guard is preserved."""
    chapter = _drive()
    low = chapter.lower()

    assert "ready_to_advance" in chapter, "CH_CHAIN_DRIVE must reference ready_to_advance as the advance signal"
    # The status-alone guard must survive the re-point.
    assert "do not advance on status" in low, "the 'do NOT advance on status alone' guard must be kept"


def test_chain_drive_signal_prose_mode_agnostic_byte_identical() -> None:
    """C-5.2 DoD: the re-pointed advance-signal prose is mode-agnostic. STEP B and the
    crash-resume branch carry NO execution-mode interpolation, so that whole region
    (from STEP B through the SERIES SUMMARY) renders byte-identical for solo-style
    (multi_terminal) and subagent (claude_code_cli) modes. (The earlier STEP A spawn
    command is legitimately mode-dependent and is excluded from this region.)"""

    def _signal_region(text: str) -> str:
        start = text.find("STEP B — WAIT FOR")
        assert start != -1, "CH_CHAIN_DRIVE must contain STEP B"
        return text[start:]

    assert _signal_region(_drive("multi_terminal")) == _signal_region(_drive("claude_code_cli")), (
        "the advance-signal prose (STEP B + crash-resume) must be byte-identical across execution modes"
    )
