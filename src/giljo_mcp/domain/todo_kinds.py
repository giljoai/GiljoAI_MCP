# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Structural TODO-kind classification for the completion gate (BE-9012b, D7).

Single source of truth for the self-closeout / chain-drive TODO taxonomy. The
completion gate used to re-run three keyword regexes on *every* incomplete TODO
at ``complete_job`` time (``job_completion_service`` §rows 4-6 of
``handovers/INF-6201_PROPOSAL_hub_absorbs_bus.md``). That was the brittle
"closeout dance": a novel wording (the field-reported "Conductor self-complete")
missed the match and stranded a finale.

D7 relocates the classification to the WRITE boundary: ``progress_service``
stamps ``agent_todo_items.todo_kind`` once, when the TODO is persisted, and the
gate reads that durable marker instead of matching wording at completion time.
The gate is therefore wording-agnostic for everything written after this ships;
a mis-classification is one durable value in one place, correctable later (a
prompt sweep in build step (d) can have agents self-tag and drop the regexes
entirely).

The three regexes live here (relocated verbatim from ``job_completion_service``)
so both the write boundary (to persist the marker) and the gate (as a NULL
fallback for legacy rows written before this column existed — Data-facing DoD
answer (a): the reader tolerates the old shape) share ONE definition.
"""

from __future__ import annotations

import re


# The three kinds a self-referential-closeout TODO can carry. NULL/absent = an
# ordinary work TODO that always blocks completion until done. Kept short so the
# String(32) column is never truncated.
TODO_KIND_SELF_CLOSEOUT = "self_closeout"
TODO_KIND_CLOSEOUT_INTENT = "closeout_intent"
TODO_KIND_CHAIN_DRIVE = "chain_drive"


# Narrow: TODO content that literally describes the closeout call itself
# ("Closeout: ...", "complete_job", "close_project", "Conductor self-complete").
# Self-referential by definition — auto-clears on the closeout path regardless of
# wording. (BE-6199 added ``self-complete`` for the chain conductor's own TODO.)
CLOSEOUT_TODO_PATTERN = re.compile(r"(?i)\b(closeout|complete[_ ]job|close[_ ]project|self[_ -]complete)\b")

# Broad closeout-INTENT wording ("Wrap up and finalize the project", "Finish the
# project"). The act of closing out IS what such a TODO asks for, so it must never
# block the agent's OWN closeout call — but only on that call (is_closeout_phase),
# never on a mid-work completion. Deliberately conservative: closeout verb + a
# project/work noun; "Fix the failing test" does not match.
CLOSEOUT_INTENT_PATTERN = re.compile(
    r"(?i)\b(wrap[- ]?up|finaliz|finalis|conclude|complete|finish|close|sign[- ]?off|wind[- ]?down)\b"
    r".{0,40}\b(project|job|work|chain|run|task|orchestrat|sprint|everything|up)\b"
)

# The project-less chain CONDUCTOR's drive TODOs (poll P_i / advance / spawn next /
# series summary / finale). Done-by-definition once every chain project is terminal,
# but they match none of the closeout wording and would strand the finale. Consulted
# ONLY behind the conductor predicate at the gate (project_id None + chain_conductor),
# so a solo / sub-orchestrator TODO with this wording is genuine work and still blocks.
CHAIN_DRIVE_TODO_PATTERN = re.compile(
    r"(?i)\b(poll|advance|spawn[ _-]?next|next[ _-]?project|series[ _-]?summary|"
    r"chain[ _-]?finale|finale|drive[ _-]the[ _-]chain|conductor)\b"
)


def classify_todo_kind(content: str | None) -> str | None:
    """Classify a TODO's content into its self-closeout kind, or ``None``.

    Precedence mirrors the gate's original OR-order (narrow closeout first, then
    the broad intent matcher, then the conductor-only chain-drive family) so a
    string matching more than one family gets the most-specific durable kind.
    Returns ``None`` for ordinary work TODOs (the common case), which always
    block completion until genuinely done.
    """
    text = content or ""
    if CLOSEOUT_TODO_PATTERN.search(text):
        return TODO_KIND_SELF_CLOSEOUT
    if CLOSEOUT_INTENT_PATTERN.search(text):
        return TODO_KIND_CLOSEOUT_INTENT
    if CHAIN_DRIVE_TODO_PATTERN.search(text):
        return TODO_KIND_CHAIN_DRIVE
    return None
