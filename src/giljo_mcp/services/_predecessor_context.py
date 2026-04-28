# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Predecessor-context constants, preamble templates, and semantic auto-detection
(HO1022 -- supersedes HO1021's role parameter).

Two-mode design:
  - multi_terminal: server injects a preamble (chain or replacement, auto-
    detected from the predecessor's completion record).
  - subagent_*    : server NEVER injects -- the orchestrator's CLI returned
    the predecessor result inline and is expected to splice findings into the
    successor's mission text directly.

Auto-detection rule:
  - pred_execution is None (predecessor never reached complete_job)  -> REPLACEMENT
  - pred_execution.result.status in {force_completed, failed, blocked, error}  -> REPLACEMENT
  - otherwise                                                        -> CHAIN

Neither preamble includes a `tenant_key="..."` arg in its example
get_agent_result(...) call -- Wave 1 invariant from commit ffa779bf:
tenant_key is auto-injected server-side and must never appear in agent prose.
"""

from __future__ import annotations

from typing import Any


# Execution modes where the orchestrator's CLI returns subagent results inline.
# In these modes the server NEVER injects a predecessor preamble -- the
# orchestrator already has the result in working context (Task() / spawn_agent()
# / @-syntax return value) and is expected to splice findings into the
# successor's mission text directly.
SUBAGENT_EXECUTION_MODES: frozenset[str] = frozenset({"claude_code_cli", "codex_cli", "gemini_cli"})

# pred_execution.result.status values that indicate the predecessor was
# replaced/failed/force-completed rather than completing cleanly. When any of
# these (or a missing pred_execution entirely) is observed, the server renders
# the REPLACEMENT preamble. Otherwise the CHAIN preamble.
_REPLACEMENT_RESULT_STATUSES: frozenset[str] = frozenset({"force_completed", "failed", "blocked", "error"})


def _detect_replacement_semantics(pred_execution: Any) -> bool:
    """Return True when the predecessor record indicates a failed/force-closed
    handoff (replacement semantics), False when it looks like a clean forward
    chain.

    Signals (in order):
      - pred_execution is None: predecessor never reached complete_job, so the
        successor is almost certainly picking up after a failure -- replacement.
      - result.status is one of the replacement markers -- replacement.
      - otherwise -- chain.
    """
    if pred_execution is None:
        return True
    pred_result = getattr(pred_execution, "result", None) or {}
    result_status = str(pred_result.get("status") or "").lower()
    return result_status in _REPLACEMENT_RESULT_STATUSES


PREDECESSOR_CHAIN_PREAMBLE = """## PRIOR PHASE OUTPUT
You are continuing a workflow. The previous phase completed successfully and produced the work below. Use this as input for the work described in your mission below.

Previous Agent: {pred_display_name} (job_id: {predecessor_job_id})
Completion Summary: {pred_summary}
Commits: {pred_commits}

If you need full predecessor context (decisions, files changed, detail not in the summary above), call:
  mcp__giljo_mcp__get_agent_result(job_id="{predecessor_job_id}")

---
"""

PREDECESSOR_REPLACEMENT_PREAMBLE = """## PREDECESSOR CONTEXT (REPLACEMENT)
You are taking over from a previous agent who attempted this work but did not complete it cleanly. Read what they did, understand the gap, and complete or fix the work described in your mission below.

Previous Agent: {pred_display_name} (job_id: {predecessor_job_id})
Completion Summary: {pred_summary}
Commits: {pred_commits}

If git is enabled, run `git log --oneline -10` to see recent commits.
For full predecessor context, call:
  mcp__giljo_mcp__get_agent_result(job_id="{predecessor_job_id}")

---
"""
