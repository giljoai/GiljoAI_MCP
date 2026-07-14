# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-9083c — protocol truncation survival (c): payload diet.

Four deletion-only levers, each tested at the layer it changed:

1. ``slice_chain_mission_for_position`` — the inlined CHAIN MISSION is sliced to the
   sub-orch's OWN ``### P_i`` block, with tolerance on degenerate missions (no headers
   → whole; position absent → whole + WARNING). NEVER errors.
2. ``_build_ch_sub_orchestrator`` inlines only that slice + a get_context pointer.
3. ``trim_embedded_protocol_for_chain(..., "sub_orchestrator")`` now ALSO trims the solo
   PHASE-1 STARTUP ritual (superseded by CH_SUB_ORCHESTRATOR step 5), keeping the
   load-bearing team-state / TODO mechanics in the replacement note; SOLO is untouched.
4. The four heavy read tools advertise ``_meta["anthropic/maxResultSizeChars"]`` on
   tools/list (item 3), inert on non-Claude-Code harnesses.

Pure functions + a tools/list read — no DB, no module-level mutable state → parallel-safe
under pytest-xdist. Edition Scope: Both.
"""

from __future__ import annotations

import asyncio

from giljo_mcp.services.protocol_sections.agent_lifecycle import _generate_orchestrator_protocol
from giljo_mcp.services.protocol_sections.chapters_chain import _build_ch_sub_orchestrator
from giljo_mcp.services.protocol_sections.orchestrator_body import (
    _SUBORCH_PHASE1_END,
    _SUBORCH_PHASE1_START,
    slice_chain_mission_for_position,
    trim_embedded_protocol_for_chain,
)


_MISSION_3 = (
    "### P_1 (aaaa):\n"
    "consumes = the repo baseline\n"
    "produces = endpoint_1.py\n"
    "must leave = ThingService.do_1 callable\n\n"
    "### P_2 (bbbb):\n"
    "consumes = output of P_1 upstream\n"
    "produces = endpoint_2.py\n"
    "must leave = migration ce_0002 idempotent\n\n"
    "### P_3 (cccc):\n"
    "consumes = output of P_2\n"
    "produces = endpoint_3.py\n"
    "must leave = router registered"
)


# ---------------------------------------------------------------------------
# 1. slice_chain_mission_for_position — happy path
# ---------------------------------------------------------------------------


def test_slice_returns_only_own_block() -> None:
    """Position 2 gets exactly the P_2 block — not P_1, not P_3."""
    sliced = slice_chain_mission_for_position(_MISSION_3, 2)
    assert sliced.startswith("### P_2 (bbbb):")
    assert "produces = endpoint_2.py" in sliced
    assert "P_1 (aaaa)" not in sliced
    assert "### P_3" not in sliced


def test_slice_first_and_last_positions() -> None:
    """First block stops at the next header; the last block runs to end-of-mission."""
    first = slice_chain_mission_for_position(_MISSION_3, 1)
    assert first.startswith("### P_1 (aaaa):")
    assert "### P_2" not in first
    last = slice_chain_mission_for_position(_MISSION_3, 3)
    assert last.startswith("### P_3 (cccc):")
    assert "must leave = router registered" in last


def test_slice_ignores_body_references_to_other_projects() -> None:
    """A body line mentioning 'P_1' inside P_2's block does not prematurely end P_1's
    slice — only markdown headers anchor a boundary (the P_2 body 'output of P_1' upstream
    reference is safely inside P_2's own block, and P_1's slice stops at the real ### P_2)."""
    first = slice_chain_mission_for_position(_MISSION_3, 1)
    assert (
        first
        == "### P_1 (aaaa):\nconsumes = the repo baseline\nproduces = endpoint_1.py\nmust leave = ThingService.do_1 callable"
    )


def test_slice_word_boundary_p2_not_p20() -> None:
    """P_2 must not match P_20 (digit word-boundary), or a 20+-project chain slices wrong."""
    mission = "### P_2 (a):\nfoo\n\n### P_20 (b):\nbar"
    assert slice_chain_mission_for_position(mission, 2) == "### P_2 (a):\nfoo"
    assert slice_chain_mission_for_position(mission, 20) == "### P_20 (b):\nbar"


# ---------------------------------------------------------------------------
# 1b. slice tolerance — NEVER errors on a degenerate mission
# ---------------------------------------------------------------------------


def test_slice_no_headers_ships_whole() -> None:
    """A freeform / legacy mission with no ### P_i headers ships WHOLE (tolerance) — a
    weak model must not lose its contract to an over-eager slice."""
    freeform = "Do the thing. Consume the repo. Produce the endpoint. Leave it callable."
    assert slice_chain_mission_for_position(freeform, 2) == freeform


def test_slice_position_absent_ships_whole_and_warns(caplog) -> None:
    """Headers exist but not for this position → ship WHOLE + a WARNING (nothing silently
    withheld)."""
    import logging

    with caplog.at_level(logging.WARNING):
        out = slice_chain_mission_for_position(_MISSION_3, 5)
    assert out == _MISSION_3
    assert any("position 5" in r.message for r in caplog.records)


def test_slice_empty_is_returned_as_is() -> None:
    assert slice_chain_mission_for_position("", 1) == ""


# ---------------------------------------------------------------------------
# 2. _build_ch_sub_orchestrator inlines only the slice + the get_context pointer
# ---------------------------------------------------------------------------


def test_suborch_chapter_inlines_only_its_slice() -> None:
    """CH_SUB_ORCHESTRATOR for position 2 inlines P_2's block only and points at
    get_context for the cross-project mission — the whole mission is no longer inlined."""
    chapter = _build_ch_sub_orchestrator(
        run_id="run-9083c", position=2, n_projects=3, execution_mode="multi_terminal", chain_mission=_MISSION_3
    )
    assert "### P_2 (bbbb):" in chapter
    assert "produces = endpoint_2.py" in chapter
    # The other projects' contracts are NOT inlined.
    assert "produces = endpoint_1.py" not in chapter
    assert "produces = endpoint_3.py" not in chapter
    # The cross-project awareness pointer is present.
    assert "get_context" in chapter
    assert "CHAIN-MISSION SLICE (P_2" in chapter


def test_suborch_chapter_degenerate_mission_inlines_whole() -> None:
    """A freeform mission (no P_i headers) is inlined whole into the chapter (tolerance)."""
    freeform = "Freeform mission with no per-project headers at all."
    chapter = _build_ch_sub_orchestrator(
        run_id="run-9083c", position=1, n_projects=1, execution_mode="multi_terminal", chain_mission=freeform
    )
    assert freeform in chapter


# ---------------------------------------------------------------------------
# 3. sub-orch PHASE-1 trim — fires, removes the human-gate seams, keeps mechanics
# ---------------------------------------------------------------------------


def _solo_suborch() -> str:
    return _generate_orchestrator_protocol(
        job_id="j",
        tenant_key="t",
        executor_id="e",
        execution_mode="multi_terminal",
        tool="multi_terminal",
        is_chain_conductor=False,
    )


def test_phase1_trim_fires_and_removes_human_gate_seams() -> None:
    """The sub-orch trim removes the solo PHASE-1 STARTUP ritual: the multi-terminal
    human-gate seam ('Copy agent prompts from the dashboard to start them') is gone, and
    the chain-correct entry (cite CH_SUB_ORCHESTRATOR step 5) replaces it."""
    solo = _solo_suborch()
    trimmed = trim_embedded_protocol_for_chain(solo, "sub_orchestrator")
    assert len(trimmed) < len(solo)
    # The removed span existed in the solo body.
    assert _SUBORCH_PHASE1_START in solo
    # The human-gate seam is gone from the trimmed sub-orch body.
    assert "Copy agent prompts from the dashboard to start them" not in trimmed
    # The chain-correct replacement note is present and cites step 5.
    assert "### PHASE 1 — STARTUP (chain sub-orchestrator)" in trimmed
    assert "CH_SUB_ORCHESTRATOR step 5" in trimmed


def test_phase1_trim_preserves_load_bearing_mechanics() -> None:
    """The non-superseded mechanics (read current_team_state + the pre-planned TODOs, begin
    PHASE 2) are KEPT in the replacement note — nothing load-bearing is orphaned."""
    trimmed = trim_embedded_protocol_for_chain(_solo_suborch(), "sub_orchestrator")
    assert "current_team_state" in trimmed
    assert "pre-planned coordination TODOs" in trimmed
    assert "### PHASE 2 — ACTIVE COORDINATION" in trimmed  # kept byte-for-byte after the cut


def test_solo_render_is_untouched_by_the_new_trim() -> None:
    """SOLO IS SACRED: the injector-only trim never runs on the solo path, so the solo
    orchestrator body still contains its full PHASE-1 STARTUP block (the end anchor is the
    PHASE 2 header, present in both)."""
    solo = _solo_suborch()
    assert _SUBORCH_PHASE1_START in solo
    assert _SUBORCH_PHASE1_END in solo


# ---------------------------------------------------------------------------
# 4. tools/list advertises _meta["anthropic/maxResultSizeChars"] on the heavy tools
# ---------------------------------------------------------------------------


def test_heavy_tools_advertise_max_result_size_meta() -> None:
    """get_job_mission / get_staging_instructions / get_thread_history / list_projects carry
    the inline-size hint on tools/list; a non-heavy tool (spawn_job) does not."""
    import api.endpoints.mcp_tools  # noqa: F401 — registration side effect
    from api.endpoints.mcp_tools._base import MCP_MAX_RESULT_SIZE_CHARS, mcp

    tools = {t.name: t for t in asyncio.run(mcp.list_tools())}
    for name in ("get_job_mission", "get_staging_instructions", "get_thread_history", "list_projects"):
        assert tools[name].meta == {"anthropic/maxResultSizeChars": MCP_MAX_RESULT_SIZE_CHARS}, name
    # A non-heavy tool carries no such hint.
    assert tools["spawn_job"].meta is None
