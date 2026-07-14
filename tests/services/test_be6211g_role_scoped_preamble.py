# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6211g move (b) + BE-6214 seam relocation — role-scoped conductor/sub-orch stream.

Move (b) — root-fix the finale: the project-less chain conductor's protocol BODY
excises the solo PHASE-3 CLOSEOUT finale (its only finale is CH_CHAIN_DRIVE's
series-summary). Solo / sub-orch / worker keep the finale byte-identical. These tests
are unchanged.

BE-6214 — the override-first preamble builders (CH_CONDUCTOR_PREAMBLE /
CH_SUBORCH_PREAMBLE) are DELETED; their three seams (handed scope /
escalate-to-conductor-via-Hub / advance-not-complete_job) now live inside the chain
chapters themselves (CH_CHAIN_DRIVE / CH_SUB_ORCHESTRATOR). The former preamble-content
tests are rewritten to assert that seam relocation.

All tests are PURE (sync builders, no DB). Edition Scope: CE.
"""

from __future__ import annotations

from giljo_mcp.services.protocol_sections.agent_lifecycle import _generate_orchestrator_protocol
from giljo_mcp.services.protocol_sections.chapters_chain import (
    _build_ch_chain_drive,
    _build_ch_sub_orchestrator,
)


# The solo PHASE-3 finale heading (em-dash U+2014) and the kept tail anchor.
_PHASE3_FINALE = "### PHASE 3 — CLOSEOUT"
_CHAIN_FINALE = "### CHAIN FINALE (chain conductor"
_ORCHESTRATOR_CONSTRAINTS = "## ORCHESTRATOR CONSTRAINTS"


def _proto(*, is_chain_conductor: bool) -> str:
    return _generate_orchestrator_protocol(
        job_id="job-6211g",
        tenant_key="tk_6211g",
        executor_id="exec-6211g",
        execution_mode="multi_terminal",
        tool="multi_terminal",
        is_chain_conductor=is_chain_conductor,
    )


# ---------------------------------------------------------------------------
# Move (b) — conductor finale excision
# ---------------------------------------------------------------------------


def test_conductor_body_excises_solo_phase3_finale() -> None:
    """is_chain_conductor=True drops the solo PHASE-3 CLOSEOUT finale and replaces
    it with the chain-finale note; the kept ORCHESTRATOR CONSTRAINTS tail remains."""
    conductor = _proto(is_chain_conductor=True)
    assert _PHASE3_FINALE not in conductor, "conductor must NOT carry the solo PHASE-3 CLOSEOUT finale"
    assert _CHAIN_FINALE in conductor, "conductor must carry the chain-finale replacement note"
    assert _ORCHESTRATOR_CONSTRAINTS in conductor, "the ORCHESTRATOR CONSTRAINTS tail must survive the finale slice"


def test_non_conductor_body_keeps_solo_phase3_finale() -> None:
    """is_chain_conductor=False (solo / sub-orch / worker) keeps the PHASE-3 finale
    byte-for-byte and never sees the conductor chain-finale note (freeze guard:
    proves the finale trim never leaks above the is_chain_conductor early return)."""
    non_conductor = _proto(is_chain_conductor=False)
    assert _PHASE3_FINALE in non_conductor, "non-conductor MUST keep the solo PHASE-3 CLOSEOUT finale"
    assert _ORCHESTRATOR_CONSTRAINTS in non_conductor
    assert "### CHAIN FINALE" not in non_conductor, "the conductor chain-finale note must never leak to non-conductor"


# ---------------------------------------------------------------------------
# BE-6214: the override-first preamble builders are DELETED. Their three seams now
# live in the chain chapters (CH_CHAIN_DRIVE / CH_SUB_ORCHESTRATOR), so the runtime
# injector no longer prepends a separate banner. These tests assert the seam
# RELOCATION; the move-(b) finale-excision tests above are unchanged.
# ---------------------------------------------------------------------------


def test_conductor_seams_live_in_ch_chain_drive() -> None:
    """The three conductor seams (handed scope / escalation sink via the Hub /
    advance-not-complete_job) are reconciled inside CH_CHAIN_DRIVE itself, replacing
    the deleted override-first preamble."""
    chapter = _build_ch_chain_drive(
        run_id="run-xyz",
        resolved_order=["p1", "p2", "p3"],
        current_index=0,
        execution_mode="multi_terminal",
        conductor_agent_id="cond-1",
        job_id="job-xyz",
    )

    # Seam 1 — handed scope (suppress the solo continuation-hunt).
    assert "SCOPE IS HANDED" in chapter
    assert "scan for a project to continue" in chapter
    # Seam 2 — escalation SINK + Hub-thread discovery.
    assert 'search_threads(query="run-xyz"' in chapter
    assert "ESCALATION" in chapter
    # Seam 3 — ADVANCE, not complete_job (server refuses a premature finale).
    assert "CONDUCTOR_CHAIN_INCOMPLETE" in chapter
    assert "ADVANCE" in chapter


def test_suborch_seams_live_in_ch_sub_orchestrator() -> None:
    """The three sub-orch seams (handed scope / escalate-to-conductor / closeout-is-
    handoff) are reconciled inside CH_SUB_ORCHESTRATOR itself, replacing the deleted
    override-first preamble."""
    chapter = _build_ch_sub_orchestrator(
        run_id="run-xyz",
        position=2,
        n_projects=3,
        execution_mode="multi_terminal",
    )

    # Seam 1 — handed scope.
    assert "SCOPE IS HANDED" in chapter
    assert "scan for a project to continue" in chapter
    # Seam 2 — escalate BLOCKERS/decisions to the conductor via the Hub thread, NOT the
    # user. search_threads alone is satisfied by the staging-complete post (an unrelated
    # use), so this MUST also assert the conductor-not-user escalation redirect — that is
    # the load-bearing half of seam 2 (BE-6214 audit: the redirect was the lost seam).
    assert "search_threads" in chapter
    low = chapter.lower()
    assert "escalat" in low, "sub-orch must carry the blocker-escalation seam (route to conductor)"
    assert "not the user" in low, "escalation must redirect AWAY from the user to the conductor"
    # Seam 3 — closeout is the handoff (the conductor's advance signal).
    assert "write_project_closeout" in chapter
