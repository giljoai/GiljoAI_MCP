# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6197 / BE-6206 (§14) — CH_CHAIN_DRIVE collapsed 4-step per-project cycle.

§14 (CHAIN_ARCHITECTURE.md) removed the per-project gate: the conductor's spawn IS the
release and a released sub-orch runs FREE. So the old "wait for staging_complete"
(STEP B) and "launch_implementation to cross the gate" (STEP C) steps are GONE — the
drive is now SPAWN (STEP A) → poll closeout (STEP B) → advance by spawning the next.

These tests pin the collapsed prose:
  - spawn_job is the per-project release; launch_implementation is NOT instructed
  - the drive does NOT tell the conductor to wait on staging_complete
  - project_closeout_at is the closeout signal; status "complete" alone is rejected
  - crash-resume RESPAWNS the current sub-orch (not only "launch the next")
  - the conductor-precedence clause and the final complete_job + series summary survive

All tests are pure (no DB, no module-level mutable state) — safe under
pytest-xdist -n auto. Edition Scope: CE.
"""

from __future__ import annotations

import re

from giljo_mcp.services.protocol_sections.chapters_chain import _build_ch_chain_drive


def _drive() -> str:
    return _build_ch_chain_drive(
        run_id="r",
        resolved_order=["p1", "p2", "p3"],
        current_index=0,
        execution_mode="claude_code_cli",
        conductor_agent_id="c1",
        job_id="j1",
    )


def test_spawn_is_the_release_no_launch_gate() -> None:
    """§14: spawn_job is the per-project release; launch_implementation is REMOVED."""
    chapter = _drive()
    assert "spawn_job" in chapter, "the conductor releases each project by spawning its sub-orch"
    assert "launch_implementation" not in chapter, (
        "§14: the conductor no longer crosses a per-project gate — launch_implementation is gone from the drive"
    )


def test_no_staging_complete_wait() -> None:
    """§14: the drive no longer tells the conductor to wait on staging_complete."""
    chapter = _drive()
    low = chapter.lower()
    assert "staging_complete" not in chapter, "the removed STEP B staging-complete wait must be gone"
    assert "wait for p_i to reach staging-complete" not in low, "the staging-complete wait step must be gone"


def test_polls_closeout() -> None:
    """STEP D uses project_closeout_at as the closeout signal, not status 'complete' alone."""
    chapter = _drive()
    assert "project_closeout_at" in chapter
    # Whitespace-robust: the prose legitimately wraps 'status "complete" alone' across a line.
    flat = re.sub(r"\s+", " ", chapter.lower())
    assert 'do not advance on status "complete" alone' in flat, (
        "the prose must warn against advancing on status 'complete' alone"
    )


def test_crash_resume_respawn() -> None:
    """Crash-resume RESPAWNS the current sub-orch when its closeout is NULL and it's dead."""
    chapter = _drive()
    resume_start = chapter.find("CRASH-RESUME")
    assert resume_start != -1, "the CRASH-RESUME section must be present"
    resume = chapter[resume_start:]
    low = resume.lower()
    assert "respawn" in low, "crash-resume must instruct RESPAWN of the current sub-orch"
    assert "spawn_job" in resume, "respawn routes through spawn_job"
    # the respawn guidance must go beyond the old "launch the next" advice
    assert "launch the next" in low or "merely" in low, (
        "the respawn guidance must explicitly contrast with only launching the next project"
    )


def test_conductor_precedence_and_finale_preserved() -> None:
    """The precedence clause + the final complete_job/series summary survive the rework."""
    chapter = _drive()
    # conductor-precedence clause + server-enforced error code
    assert "CONDUCTOR_CHAIN_INCOMPLETE" in chapter
    assert "does not apply" in chapter.lower()
    # series summary + self-complete finale
    assert "SERIES SUMMARY" in chapter
    # BE-6199: the series-summary tag is the vocab-accepted "chore"
    # (was "chain-summary", which the tag vocabulary rejected with a 422).
    assert 'tags=["chore"]' in chapter
    assert "complete_job" in chapter
    # tools-only ban and no batch-unlock guarantees still hold
    assert "TOOLS ONLY" in chapter
    assert "batch-unlock" in chapter
