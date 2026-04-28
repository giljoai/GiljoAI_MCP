# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Predecessor-context constants, preamble templates, and semantic auto-detection
(HO1023 -- pre-staging chain fix; supersedes HO1022's pred_execution-only signal).

Two-mode design:
  - multi_terminal: server injects a preamble (chain or replacement, auto-
    detected from the predecessor's work-order status + completion record).
  - subagent_*    : server NEVER injects -- the orchestrator's CLI returned
    the predecessor result inline and is expected to splice findings into the
    successor's mission text directly.

Auto-detection rule (HO1023):
  - pred_job.status in {failed, blocked, decommissioned}             -> REPLACEMENT
  - pred_execution.result.status in {force_completed, failed,
        blocked, error}                                              -> REPLACEMENT
  - otherwise (predecessor is healthy, still running, or pre-execution)
                                                                      -> CHAIN

Why CHAIN is the default at spawn time:
  In multi_terminal mode the orchestrator pre-spawns ALL phases up front during
  staging, BEFORE any of them run. The successor's preamble is rendered AT SPAWN
  TIME (and stored in the mission text) -- so when the orchestrator spawns
  Phase 2 with predecessor=Phase1, Phase1 is necessarily in `waiting` status
  with no completion record yet. Treating "no completion record" as "failure"
  (the HO1022 heuristic) baked the REPLACEMENT preamble into every healthy
  forward chain. HO1023 fixes that: REPLACEMENT only when there's an explicit
  failure signal on the predecessor's work order or completion result.
  Reactivation flows still work -- when the orchestrator respawns a successor
  AFTER a confirmed failure, pred_job.status is failed/blocked at that point
  and the REPLACEMENT preamble correctly renders.

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

# AgentJob.status values on the predecessor that indicate explicit failure /
# decommission. Trigger REPLACEMENT preamble.
_REPLACEMENT_JOB_STATUSES: frozenset[str] = frozenset({"failed", "blocked", "decommissioned"})

# pred_execution.result.status values (set by the agent or by orchestrator
# force-completion via complete_job result dict) that indicate the predecessor
# did not complete cleanly. Trigger REPLACEMENT preamble.
_REPLACEMENT_RESULT_STATUSES: frozenset[str] = frozenset({"force_completed", "failed", "blocked", "error"})


def _detect_replacement_semantics(pred_job: Any, pred_execution: Any) -> bool:
    """Return True when the predecessor record carries an EXPLICIT failure
    signal, False otherwise.

    HO1023: chain is the default at spawn time. The successor's preamble is
    rendered when the orchestrator calls spawn_job, which in multi_terminal
    staging happens BEFORE the predecessor has run. A missing pred_execution
    therefore does NOT mean failure -- it usually means pre-execution.

    Signals checked (in order):
      1. pred_job.status in {failed, blocked, decommissioned}    -> REPLACEMENT
      2. pred_execution.result.status in failure markers          -> REPLACEMENT
      3. otherwise                                                -> CHAIN
    """
    if pred_job is not None:
        job_status = str(getattr(pred_job, "status", "") or "").lower()
        if job_status in _REPLACEMENT_JOB_STATUSES:
            return True
    if pred_execution is not None:
        result_status = str((pred_execution.result or {}).get("status") or "").lower()
        if result_status in _REPLACEMENT_RESULT_STATUSES:
            return True
    return False


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
