# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6208g — additive chain-field polish: conductor role-trim + opt-in protocol ETag.

Two strictly-additive fixes to the SHARED get_job_mission response shape:

  Fix 1 (opt-in protocol ETag): when the caller passes a known protocol_etag, the
  unchanged static identity+protocol block is omitted on a re-fetch and a cache
  signal is returned. With the flag UNSET the wire payload is byte-identical to today
  (the two new fields are stripped from serialization at their defaults).

  Fix 2 (conductor role-trim): the project-less chain conductor (is_chain_conductor)
  drops the worker-spawn coordination-action block it never acts on. Solo / sub-orch /
  worker protocols are unchanged.

Pure tests (no DB, no module-level mutable state) — parallel-safe under xdist.
Edition Scope: CE.
"""

from __future__ import annotations

from giljo_mcp.schemas.responses.orchestration import MissionResponse
from giljo_mcp.services.mission_service import MissionService
from giljo_mcp.services.protocol_sections.agent_lifecycle import _generate_orchestrator_protocol


# Worker-spawn coordination-action markers that only a project-bound orchestrator acts on.
_WORKER_SPAWN_MARKERS = (
    "**COORDINATION ACTIONS (use as needed within the loop):**",
    "**Spawn a replacement agent:**",
    "**Spawn verification agent (after all deliverable agents complete):**",
    "**Implementation-phase verification spawning:**",
)


def _proto(*, is_chain_conductor: bool) -> str:
    return _generate_orchestrator_protocol(
        job_id="job-6208g",
        tenant_key="tk_6208g",
        executor_id="exec-6208g",
        execution_mode="multi_terminal",
        tool="multi_terminal",
        is_chain_conductor=is_chain_conductor,
    )


# ---------------------------------------------------------------------------
# Fix 2 — conductor role-trim
# ---------------------------------------------------------------------------


def test_conductor_protocol_omits_worker_spawn_block() -> None:
    """is_chain_conductor=True drops the worker-spawn coordination-action block."""
    conductor = _proto(is_chain_conductor=True)
    for marker in _WORKER_SPAWN_MARKERS:
        assert marker not in conductor, f"conductor protocol must NOT carry worker-spawn marker: {marker!r}"
    # The trimmed conductor note replaces the block.
    assert "**COORDINATION ACTIONS (chain conductor):**" in conductor, "conductor must get the trimmed note"
    # The surrounding non-trimmed content is intact.
    assert "**PROGRESS REPORTING (MANDATORY after every coordination action):**" in conductor
    # BE-6211g (move b): the conductor's solo PHASE-3 CLOSEOUT finale is now excised and
    # replaced with the chain-finale note (its only finale is CH_CHAIN_DRIVE's series-
    # summary). The kept ORCHESTRATOR CONSTRAINTS tail still follows. Conductor stream
    # changes BY DESIGN.
    assert "### PHASE 3 — CLOSEOUT" not in conductor
    assert "### CHAIN FINALE (chain conductor" in conductor
    assert "## ORCHESTRATOR CONSTRAINTS" in conductor


def test_suborch_and_solo_keep_worker_spawn_block() -> None:
    """is_chain_conductor=False (solo / sub-orch / worker path) keeps the full block."""
    non_conductor = _proto(is_chain_conductor=False)
    for marker in _WORKER_SPAWN_MARKERS:
        assert marker in non_conductor, f"non-conductor protocol MUST carry worker-spawn marker: {marker!r}"
    assert "**COORDINATION ACTIONS (chain conductor):**" not in non_conductor, (
        "the conductor-only trimmed note must never leak into a non-conductor protocol"
    )


def test_trim_is_the_only_body_difference() -> None:
    """Re-splicing BOTH excised blocks back into the conductor body — and normalizing
    the BE-9103 role-scoped git bullet — reproduces the non-conductor body below the
    FORBIDDEN banner, proving the conductor trims (BE-6208g worker-spawn + BE-6211g
    PHASE-3 finale) and the role-scoped bullet are the ONLY body differences."""
    from giljo_mcp.services.protocol_sections.agent_lifecycle import (
        _CONDUCTOR_CLOSEOUT_NOTE,
        _CONDUCTOR_COORDINATION_NOTE,
        _ORCHESTRATOR_CONSTRAINTS_ANCHOR,
        _PHASE3_CLOSEOUT_START,
        _PROGRESS_REPORTING_ANCHOR,
        _WORKER_SPAWN_BLOCK_START,
    )
    from giljo_mcp.services.protocol_sections.orchestrator_body import (
        _GIT_CONSTRAINT_CONDUCTOR,
        _GIT_CONSTRAINT_SELF_ADOPT,
    )

    non_conductor = _proto(is_chain_conductor=False)
    conductor = _proto(is_chain_conductor=True)

    # Extract the verbatim worker-spawn block from the non-conductor body.
    ws_start = non_conductor.find(_WORKER_SPAWN_BLOCK_START)
    ws_end = non_conductor.find(_PROGRESS_REPORTING_ANCHOR)
    assert ws_start != -1 and ws_end != -1 and ws_start < ws_end
    worker_block = non_conductor[ws_start:ws_end]

    # Extract the verbatim PHASE-3 finale block from the non-conductor body (BE-6211g).
    fin_start = non_conductor.find(_PHASE3_CLOSEOUT_START)
    fin_end = non_conductor.find(_ORCHESTRATOR_CONSTRAINTS_ANCHOR)
    assert fin_start != -1 and fin_end != -1 and fin_start < fin_end
    finale_block = non_conductor[fin_start:fin_end]

    # Reverse BOTH trims on the conductor body and confirm it equals the non-conductor body
    # EXCEPT for the FORBIDDEN banner (BE-6205 conductor-autonomy variant, pre-existing).
    restored = conductor.replace(_CONDUCTOR_COORDINATION_NOTE, worker_block, 1)
    restored = restored.replace(_CONDUCTOR_CLOSEOUT_NOTE, finale_block, 1)
    # BE-9103: the git-commit constraint bullet is role-scoped (the conductor never
    # self-adopts, so it carries the compact delegate-only line) — normalize it too.
    restored = restored.replace(_GIT_CONSTRAINT_CONDUCTOR, _GIT_CONSTRAINT_SELF_ADOPT, 1)
    # Compare from the shared body anchor onward (banner differs by design).
    anchor = "## Orchestrator Coordination Protocol (3 Phases)"
    assert restored[restored.find(anchor) :] == non_conductor[non_conductor.find(anchor) :], (
        "conductor trims must remove ONLY the worker-spawn + PHASE-3 finale blocks "
        "and swap the role-scoped git bullet; the rest of the body is byte-identical"
    )
    # Freeze: the finale trim is conductor-only — it must never leak to the non-conductor body.
    assert _PHASE3_CLOSEOUT_START in non_conductor, "the PHASE-3 finale must remain in the non-conductor body"


# ---------------------------------------------------------------------------
# Fix 1 — opt-in protocol ETag envelope (byte-identical when unset)
# ---------------------------------------------------------------------------

# BE-6211c (S-4a): get_agent_mission now ALWAYS emits protocol_etag, so it is a
# standard wire key on every mission response (the JSON envelope gains one benign
# additive key). protocol_unchanged remains opt-in and is stripped at its default.
_LEGACY_KEYS = {
    "job_id",
    "agent_id",
    "agent_name",
    "agent_display_name",
    "agent_identity",
    "mission",
    "project_id",
    "parent_job_id",
    "status",
    "created_at",
    "started_at",
    "thin_client",
    "full_protocol",
    "current_team_state",
    "project_phase",
    "blocked",
    "error",
    "user_instruction",
    "protocol_etag",
}


def test_mission_response_emits_etag_and_omits_unchanged_by_default() -> None:
    """BE-6211c: a standard mission response carries protocol_etag (always emitted),
    while protocol_unchanged stays stripped from the wire at its default (False)."""
    resp = MissionResponse(job_id="j1", agent_identity="ID", full_protocol="PROTO", protocol_etag="abc123")
    dumped = resp.model_dump(mode="json")
    assert set(dumped.keys()) == _LEGACY_KEYS, f"unexpected wire keys: {set(dumped) ^ _LEGACY_KEYS}"
    assert dumped["protocol_etag"] == "abc123"
    assert "protocol_unchanged" not in dumped


def test_mission_response_includes_cache_signal_when_set() -> None:
    """Flag SET on an unchanged re-fetch → the static block is omitted AND the cache
    signal (etag + protocol_unchanged) is present in the serialized payload."""
    resp = MissionResponse(
        job_id="j1",
        agent_identity=None,
        full_protocol=None,
        protocol_etag="deadbeef",
        protocol_unchanged=True,
    )
    dumped = resp.model_dump(mode="json")
    assert dumped["protocol_etag"] == "deadbeef"
    assert dumped["protocol_unchanged"] is True
    assert dumped["agent_identity"] is None
    assert dumped["full_protocol"] is None


def test_mission_response_etag_present_without_match() -> None:
    """A mismatched re-fetch returns the fresh etag (so the caller updates its cache)
    while still carrying the full static block; protocol_unchanged stays stripped (False)."""
    resp = MissionResponse(
        job_id="j1",
        agent_identity="ID",
        full_protocol="PROTO",
        protocol_etag="freshhash",
    )
    dumped = resp.model_dump(mode="json")
    assert dumped["protocol_etag"] == "freshhash"
    assert "protocol_unchanged" not in dumped, "False protocol_unchanged is stripped from the wire"
    assert dumped["full_protocol"] == "PROTO"


def test_compute_protocol_etag_is_stable_and_collision_resistant() -> None:
    """The etag is deterministic over (identity, protocol) and the NUL separator keeps
    distinct pairs from colliding on concatenation."""
    a = MissionService._compute_protocol_etag("ID", "PROTO")
    b = MissionService._compute_protocol_etag("ID", "PROTO")
    assert a == b, "etag must be deterministic"

    # Concatenation collision guard: ("AB", "C") vs ("A", "BC") must differ.
    assert MissionService._compute_protocol_etag("AB", "C") != MissionService._compute_protocol_etag("A", "BC")

    # None segments are tolerated and distinct from empty-vs-content.
    assert MissionService._compute_protocol_etag(None, None) != MissionService._compute_protocol_etag("ID", "PROTO")
