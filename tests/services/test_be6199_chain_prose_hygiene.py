# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6199 — chain prose / response hygiene regressions (3 fixes).

Three small defects surfaced by the first clean end-to-end chain run:

#3 (REAL 422 bug) — the CH_CHAIN_DRIVE series-summary prose instructed
   write_memory_entry(..., tags=["chain-summary"]). "chain-summary" is NOT a
   member of CONTROLLED_TAG_VOCABULARY, so that call 422s. The example now uses
   the valid "chore" tag.

#4 — the project-less chain CONDUCTOR's final self-complete reaches the closeout
   phase but owns no project, so the solo "Call write_project_closeout()"
   next_action is wrong for it. _phase_response now branches on is_conductor and
   returns a chain-appropriate next step. Solo / project-bound orchestrators stay
   byte-identical.

#5 — the closeout-phase auto-ack only matched TODO names containing
   closeout / complete_job / close_project, so a conductor TODO named
   "Conductor self-complete" never auto-cleared. CLOSEOUT_TODO_PATTERN now also
   matches "self-complete" / "self_complete".

All tests are pure (no DB, no module-level mutable state) — safe under
pytest-xdist -n auto. Edition Scope: CE.
"""

from __future__ import annotations

import re

from giljo_mcp.domain.todo_kinds import CLOSEOUT_TODO_PATTERN  # BE-9012b: relocated from job_completion_service
from giljo_mcp.schemas.service_responses import build_next_action
from giljo_mcp.services.job_completion_service import JobCompletionService
from giljo_mcp.services.memory_entry_write_validator import CONTROLLED_TAG_VOCABULARY
from giljo_mcp.services.protocol_sections.chapters_chain import _build_ch_chain_drive


def _drive() -> str:
    return _build_ch_chain_drive(
        run_id="run-x",
        resolved_order=["head", "p2", "p3"],
        current_index=0,
        execution_mode="claude_code_cli",
        conductor_agent_id="cond-1",
        job_id="job-77",
    )


# ── Fix #3 — series-summary uses a VALID controlled-vocabulary tag ───────────


def test_series_summary_uses_valid_tag() -> None:
    """The series-summary write_memory_entry example uses a real vocab tag.

    "chain-summary" would 422 (not in CONTROLLED_TAG_VOCABULARY); the prose must
    show a valid tag instead, and "chore" is a member of the vocabulary.
    """
    chapter = _drive()
    assert "chain-summary" not in chapter
    assert 'tags=["chore"]' in chapter
    assert "chore" in CONTROLLED_TAG_VOCABULARY


def test_series_summary_still_renders_write_memory_entry() -> None:
    """The fix is prose-only — the write_memory_entry instruction is intact."""
    chapter = _drive()
    assert "write_memory_entry" in chapter
    assert "SERIES SUMMARY" in chapter


# ── Fix #4 — conductor complete_job next_action is chain-aware ───────────────


def test_conductor_complete_next_action_chain_aware() -> None:
    """A project-less conductor's closeout-phase response is NOT the solo closeout.

    It must not tell the conductor to write_project_closeout (it owns no project);
    it references the chain being complete and the series summary being done.
    """
    phase, _message, next_action = JobCompletionService._phase_response(
        is_staging_end=False,
        is_closeout_phase=True,
        is_conductor=True,
    )
    assert phase == "closeout"
    assert next_action["tool"] == "write_memory_entry"
    assert "Chain complete" in next_action["why"]
    assert "series summary" in next_action["why"]


def test_solo_closeout_next_action_byte_identical() -> None:
    """A project-bound (solo) orchestrator's closeout response is unchanged.

    is_conductor defaults to False, and the original closeout next_action (the
    write_project_closeout instruction) must be returned identically.
    """
    expected = build_next_action(
        tool="write_project_closeout",
        why=(
            "Call write_project_closeout() to write the project closeout (orchestrators "
            "coordinate, they do not commit code)."
        ),
    )
    # Explicit False and the default must both yield the original solo response.
    explicit = JobCompletionService._phase_response(is_staging_end=False, is_closeout_phase=True, is_conductor=False)
    default = JobCompletionService._phase_response(is_staging_end=False, is_closeout_phase=True)
    assert explicit == default
    assert explicit == ("closeout", "Orchestrator job completed; closeout recorded.", expected)


def test_conductor_closeout_swap_does_not_bleed_into_staging_end() -> None:
    """The is_conductor CLOSEOUT swap (write_project_closeout -> series-summary) stays
    confined to the closeout phase: at staging-end the conductor never gets the closeout
    next_action. BE-6221e gives staging-end its OWN conductor arm (HALT for the user's
    GO), so the staging-end conductor response is the await-GO wording — NOT the closeout
    swap and NOT the solo 'press Implement and drive'."""
    staging = JobCompletionService._phase_response(is_staging_end=True, is_closeout_phase=False, is_conductor=True)
    assert staging[0] == "staging_end"
    assert staging[2]["tool"] != "write_project_closeout", "the closeout swap must not bleed into staging-end"
    # BE-6221e: the staging-end conductor arm is the firm await-GO wording.
    assert "EXPLICIT GO" in staging[2]["why"], "staging-end conductor must be told to wait for the user's explicit GO"


# ── Fix #5 — "self-complete" TODO is matched by the auto-ack keyword set ──────


def test_self_complete_todo_auto_acked() -> None:
    """A "Conductor self-complete" TODO is matched by the closeout auto-ack pattern."""
    assert CLOSEOUT_TODO_PATTERN.search("Conductor self-complete") is not None
    # Underscore and space variants, case-insensitive, all match.
    assert CLOSEOUT_TODO_PATTERN.search("conductor self_complete") is not None
    assert CLOSEOUT_TODO_PATTERN.search("Self Complete the chain") is not None


def test_existing_closeout_keywords_still_match() -> None:
    """The pre-existing closeout/complete_job/close_project keywords still match."""
    assert CLOSEOUT_TODO_PATTERN.search("Closeout: write the 360") is not None
    assert CLOSEOUT_TODO_PATTERN.search("call complete_job") is not None
    assert CLOSEOUT_TODO_PATTERN.search("close_project and update memory") is not None


def test_normal_todo_not_auto_acked() -> None:
    """A normal work TODO is NOT matched by the closeout auto-ack pattern.

    The gate stays scoped — only self-referential closeout/self-complete TODOs
    auto-clear; real work still blocks.
    """
    assert CLOSEOUT_TODO_PATTERN.search("Implement the rate limiter") is None
    assert CLOSEOUT_TODO_PATTERN.search("Review the PR and merge") is None
    # "complete" alone (not self-complete / complete_job) must not trip it.
    assert CLOSEOUT_TODO_PATTERN.search("Mark the feature complete in the UI") is None


# ── BE-6212 — chain workflow smoothness (field-report seam fixes) ─────────────


def _suborch() -> str:
    from giljo_mcp.services.protocol_sections.chapters_chain import _build_ch_sub_orchestrator

    return _build_ch_sub_orchestrator(run_id="run-x", position=2, n_projects=3, execution_mode="claude_code_cli")


def test_drive_step_b_has_real_wake_mechanism() -> None:
    """C: STEP B gives a real harness wake (background sleep), not just the dashboard label —
    a literal conductor that only set_agent_status(sleeping) would stall the whole chain."""
    chapter = _drive()
    flat = re.sub(r"\s+", " ", chapter.lower())  # whitespace-robust (prose wraps across lines)
    assert "run_in_background" in chapter, "STEP B must name the background-run wake mechanism"
    assert "sleep 1" in chapter, "STEP B must reuse the `sleep 1 N` harness workaround idiom"
    assert "dashboard label" in flat, "STEP B must warn set_agent_status is only the dashboard label"
    assert "stalls the whole chain" in flat, "STEP B must warn that sleep-and-stop stalls the chain"


def test_drive_step_b_reads_hub_via_thread_history() -> None:
    """P1-4 (BE-9012d): STEP B reads the Hub via get_thread_history using the
    per-participant unread cursor (unread_only + mark_read) -- the bus's
    receive_messages is retired, so the Hub is the SOLE messaging surface now."""
    chapter = _drive()
    low = chapter.lower()
    assert "get_thread_history" in chapter, "STEP B must read the Hub via get_thread_history"
    assert "unread_only=true" in chapter, "STEP B must use the unread_only cursor"
    assert "mark_read=true" in chapter, "STEP B must use the mark_read cursor"
    assert "receive_messages" not in chapter, "receive_messages is retired (bus hard-removed)"
    assert "one messaging surface" in low, "STEP B must state there is only one messaging surface now"


def test_drive_step_b_hub_poll_uses_unread_cursor_single_surface() -> None:
    """BE-9012d (bus retirement, phase d): STEP B's Hub poll uses the server-persisted
    per-(thread, participant) unread cursor (unread_only + mark_read) instead of
    manually-carried after_message_id bookkeeping, now that user directives arrive on
    the SAME Hub thread as sub-orch notes -- one messaging surface, not the old
    "receive_messages vs. Hub" separate-channels framing (retired: the user directive
    inbox is folded into the Hub)."""
    chapter = _drive()
    flat = re.sub(r"\s+", " ", chapter.lower())  # whitespace-robust (prose wraps across lines)
    assert "unread_only=true" in chapter, "STEP B must use the unread_only cursor"
    assert "mark_read=true" in chapter, "STEP B must use the mark_read cursor"
    assert "only what's new since your last read" in flat, (
        "STEP B must say the cursor pulls only what's new since the last read"
    )
    # The old two-channel framing is RETIRED: the user directive now arrives ON the
    # Hub thread as a directed post, so there is nothing separate left to reconcile.
    assert "separate channels" not in flat, "the retired 'separate channels' framing must not reappear"
    assert "cannot drop either channel" not in flat, "the retired two-channel framing must not reappear"
    assert "after_message_id" not in chapter, "the manual after_message_id cursor is retired in favor of unread_only"
    assert "one messaging surface" in flat, "STEP B must state there is a single messaging surface"


def test_series_summary_clears_drive_todos_and_states_caps() -> None:
    """D: the finale tells the conductor to clear its drive TODOs first (kills the
    report_progress->retry dance) and surfaces the write_memory_entry caps inline."""
    chapter = _drive()
    low = chapter.lower()
    assert "clear your drive todos first" in low, "the finale must instruct clearing drive TODOs first"
    assert "orchestrator_incomplete_todos" in chapter, "the finale must name the gate it avoids"
    assert "1500" in chapter and "250" in chapter, "the summary/250-char caps must be surfaced before the call"


def test_suborch_posts_done_only_after_write_project_closeout() -> None:
    """B: CH_SUB_ORCHESTRATOR step 7 instructs the Hub DONE post strictly AFTER
    write_project_closeout, so the advance signal cannot lead the server gate."""
    chapter = _suborch()
    wpc = chapter.find("write_project_closeout")
    done = chapter.find("ONLY AFTER write_project_closeout RETURNS")
    assert wpc != -1 and done != -1, "step 7 must name write_project_closeout and the after-return Hub post"
    assert wpc < done, "the Hub DONE post must be instructed AFTER write_project_closeout"


def test_conductor_inbox_poll_has_background_wake() -> None:
    """C: BE-6215 folded the conductor inbox-poll into CH_CHAIN_DRIVE STEP B, so there is
    now ONE conductor loop carrying BOTH the background-wake idiom and the directive inbox
    poll — they cannot contradict (single source). BE-9012d: the directive inbox is now the
    Hub cursor poll (get_thread_history/unread_only/mark_read), not the retired
    receive_messages bus tool. Pin that the merged drive chapter keeps the wake idiom + the
    Hub-cursor directive inbox + the harmonized advance gate."""
    chapter = _build_ch_chain_drive(
        run_id="run-77",
        resolved_order=["p1", "p2"],
        current_index=0,
        execution_mode="multi_terminal",
        conductor_agent_id="cond-1",
        job_id="job-77",
    )
    flat = re.sub(r"\s+", " ", chapter.lower())  # whitespace-robust (prose wraps across lines)
    assert "run_in_background" in chapter, "the conductor loop must use the background-wake idiom"
    assert "sleep 1" in chapter
    # STEP B (the now-single conductor loop) warns set_agent_status only sets the dashboard
    # label and will not wake/re-invoke the conductor on its own.
    assert ("not re-invoke you" in flat) or ("not wake you" in flat), (
        "must warn set_agent_status will not wake/re-invoke the conductor on its own"
    )
    assert "ready_to_advance" in chapter, "the loop must advance on ready_to_advance"
    assert "receive_messages" not in chapter, "receive_messages is retired (bus hard-removed)"
    assert "get_thread_history" in chapter, "the folded directive inbox poll must live in the same drive loop"
