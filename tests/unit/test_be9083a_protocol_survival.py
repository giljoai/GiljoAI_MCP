# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-9083a — unit tests for the protocol_survival helpers.

The (phase x role) checklist is an authoritative steering wheel: a wrong cell is
worse than none (CE-0026 precedent), so every cell is pinned on its distinctive
tool calls and the unresolvable cells are pinned to None. The MCP-transport half
(the BE-5042 failing-layer proof for all six cells) lives in
tests/integration/test_be9083a_next_required_actions_mcp_boundary.py.

Pure functions — no DB, no module-level mutable state. Edition Scope: Both.
"""

from __future__ import annotations

import pytest

from giljo_mcp.services.protocol_survival import (
    PROTOCOL_END_MARKER,
    build_truncation_check,
    compute_next_required_actions,
)


def _cell(**kwargs) -> list[str]:
    result = compute_next_required_actions(**kwargs)
    assert result is not None
    return result


def _all_cells() -> dict[str, list[str]]:
    return {
        "worker": _cell(job_type="implementer", phase=None),
        "conductor": _cell(job_type="orchestrator", phase="implementation", is_chain_conductor=True),
        "chain_suborch_staging": _cell(job_type="orchestrator", phase="staging", is_chain_member=True),
        "chain_suborch_impl": _cell(job_type="orchestrator", phase="implementation", is_chain_member=True),
        "solo_staging": _cell(job_type="orchestrator", phase="staging"),
        "solo_impl": _cell(job_type="orchestrator", phase="implementation"),
    }


def test_every_cell_is_numbered_and_within_budget() -> None:
    """Every cell renders a numbered checklist of <= 15 entries (the measured
    cross-harness safe budget is ~200 lines total; the checklist must stay tiny)."""
    for name, checklist in _all_cells().items():
        assert 1 <= len(checklist) <= 15, f"{name}: {len(checklist)} entries"
        for i, item in enumerate(checklist, start=1):
            assert item.startswith(f"{i}. "), f"{name} item {i} is not numbered: {item[:40]!r}"


def test_cells_are_distinct_and_carry_their_signature_steps() -> None:
    cells = _all_cells()

    worker = "\n".join(cells["worker"])
    assert "report_progress" in worker
    assert "complete_job" in worker
    assert "write_project_closeout" not in worker, "a worker must never be steered to closeout tools"

    conductor = "\n".join(cells["conductor"])
    assert "ready_to_advance" in conductor
    assert "spawn" in conductor.lower()
    assert "update_project_mission" not in conductor, "the conductor owns no project mission"

    suborch_staging = "\n".join(cells["chain_suborch_staging"])
    assert "update_project_mission" in suborch_staging
    assert "INERT" in suborch_staging
    assert "protocol_etag" in suborch_staging
    assert "get_job_mission" in suborch_staging
    assert "Implement" not in suborch_staging, "chain mode has no human Implement gate"

    suborch_impl = "\n".join(cells["chain_suborch_impl"])
    assert "write_project_closeout" in suborch_impl
    assert "Hub" in suborch_impl
    assert suborch_impl.index("complete_job") < suborch_impl.index("write_project_closeout"), (
        "the closeout order (complete_job FIRST) is load-bearing — the inverse raises COMPLETION_BLOCKED"
    )

    solo_staging = "\n".join(cells["solo_staging"])
    assert "Implement" in solo_staging, "solo staging ends at the human Implement gate"
    assert "spawn_job" in solo_staging

    solo_impl = "\n".join(cells["solo_impl"])
    assert "write_project_closeout" in solo_impl
    assert "Hub" not in solo_impl, "solo has no chain Hub thread protocol"

    # No two cells may render identically (a duplicate means a lost distinction).
    rendered = ["\n".join(c) for c in cells.values()]
    assert len(set(rendered)) == len(rendered)


def test_unresolvable_orchestrator_cells_return_none() -> None:
    """No checklist beats a wrong checklist: an orchestrator with no live phase
    signal (and not a conductor) gets None, which the serializer strips."""
    assert compute_next_required_actions(job_type="orchestrator", phase=None) is None
    assert compute_next_required_actions(job_type="orchestrator", phase=None, is_chain_member=True) is None
    # An unknown phase token is equally unresolvable — never guess a cell.
    assert compute_next_required_actions(job_type="orchestrator", phase="weird") is None


@pytest.mark.parametrize("job_type", ["implementer", "tester", "reviewer", "documenter", None, ""])
def test_every_non_orchestrator_job_type_gets_the_worker_cell(job_type) -> None:
    assert compute_next_required_actions(job_type=job_type, phase=None) == _cell(job_type="implementer", phase=None)


def test_conductor_wins_over_chain_member_flag() -> None:
    """The project-less conductor can never be a project-bound member; if both flags
    ever arrive True, the conductor cell (the more specific role) must win."""
    both = compute_next_required_actions(
        job_type="orchestrator", phase="implementation", is_chain_member=True, is_chain_conductor=True
    )
    assert both == _cell(job_type="orchestrator", phase="implementation", is_chain_conductor=True)


def test_truncation_check_names_marker_size_and_real_recovery() -> None:
    """The head sentinel states the size, the tail marker, and the recovery ladder:
    protocol_etag refetch first, then the BE-9083d per-section refetch (section=<name>
    from protocol_toc). 9083a shipped this sentinel with 'section fetch ships later';
    9083d deliberately closed that dangling reference — it must never come back."""
    text = build_truncation_check(41_234)
    assert "~41234 chars" in text
    assert PROTOCOL_END_MARKER in text
    assert "protocol_etag" in text
    assert "section=" in text
    assert "protocol_toc" in text
    assert "ships later" not in text
