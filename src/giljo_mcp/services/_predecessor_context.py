# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

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

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.exceptions import ResourceNotFoundError, ValidationError

# Execution modes where the orchestrator's CLI returns subagent results inline.
# In these modes the server NEVER injects a predecessor preamble -- the
# orchestrator already has the result in working context (Task() / spawn_agent()
# / @-syntax return value) and is expected to splice findings into the
# successor's mission text directly. Single source: PlatformRegistry (re-exported
# here so existing importers keep resolving the name).
from giljo_mcp.platform_registry import SUBAGENT_EXECUTION_MODES
from giljo_mcp.repositories.agent_completion_repository import AgentCompletionRepository
from giljo_mcp.utils.log_sanitizer import sanitize


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
  get_agent_result(job_id="{predecessor_job_id}")

---
"""

PREDECESSOR_REPLACEMENT_PREAMBLE = """## PREDECESSOR CONTEXT (REPLACEMENT)
You are taking over from a previous agent who attempted this work but did not complete it cleanly. Read what they did, understand the gap, and complete or fix the work described in your mission below.

Previous Agent: {pred_display_name} (job_id: {predecessor_job_id})
Completion Summary: {pred_summary}
Commits: {pred_commits}

If git is enabled, run `git log --oneline -10` to see recent commits.
For full predecessor context, call:
  get_agent_result(job_id="{predecessor_job_id}")

---
"""

# BE-8003j: the isolated-PR chain hand-off. A web-coding predecessor (Claude Code
# web / Codex web) delivers its work as an isolated branch/PR rather than into a
# shared working tree, so its ``complete_job.result.branch`` is the successor's
# base — "launch order" becomes "merge order". Sourced automatically from the
# predecessor's completion record; appended to whichever preamble was chosen so the
# successor's seed says which branch to build ON. The human reviews/merges that PR
# as the pacing gate between phases (the same "checkpoint where the human already
# looks" philosophy as the Implement-button gate).
PREDECESSOR_BASE_BRANCH_BLOCK = """## BASE BRANCH (isolated-PR chain hand-off)
The previous phase delivered its work as an isolated branch/PR, not into a shared working tree. Base your work on its branch so you build ON its code, not a stale main:

  Branch to base on: {pred_branch}{pr_line}

Check out (or branch from) `{pred_branch}` before you start. The human reviews and merges that PR as the pacing gate between phases.

---
"""


def _build_base_branch_block(pred_result: dict[str, Any]) -> str:
    """Render the isolated-PR base-branch hand-off block, or "" when absent.

    BE-8003j: the presence of a non-empty ``branch`` in the predecessor's
    ``complete_job.result`` IS the isolated-PR delivery signal — a web-coding
    predecessor records the branch it delivered, a shared-working-tree
    predecessor does not. So the block renders exactly when the predecessor
    handed off an isolated PR, and is byte-absent otherwise (no branch -> no
    block, today's preamble unchanged). ``pr_url`` is optional review context.
    """
    branch = (pred_result.get("branch") or "").strip()
    if not branch:
        return ""
    pr_url = (pred_result.get("pr_url") or "").strip()
    pr_line = f"\n  Predecessor PR:    {pr_url}" if pr_url else ""
    return PREDECESSOR_BASE_BRANCH_BLOCK.format(pred_branch=branch, pr_line=pr_line)


async def build_predecessor_context(
    session: AsyncSession,
    predecessor_job_id: str,
    tenant_key: str,
    project_id: str,
    mission: str,
    agent_display_name: str,
    execution_mode: str = "multi_terminal",
    *,
    logger: logging.Logger,
) -> str:
    """
    Build predecessor context for chain or replacement spawning, mode-gated.

    HO1022: Two-mode design. Server gates on execution_mode and auto-detects
    chain vs replacement semantics from the predecessor's completion record.
    Orchestrators never see this distinction -- they just pass
    predecessor_job_id when a successor needs a previous agent's output.

    +-----------------+----------------------------------------------------+
    | execution_mode  | server behavior                                    |
    +-----------------+----------------------------------------------------+
    | multi_terminal  | inject preamble (chain or replacement, auto-       |
    |                 | detected from pred_execution.result.status)        |
    | subagent_*      | NO preamble -- orchestrator's CLI returned the     |
    |                 | predecessor result inline and is expected to       |
    |                 | splice findings into the successor mission         |
    +-----------------+----------------------------------------------------+

    Validation always runs (predecessor existence + same-project check) so
    that a typo'd predecessor_job_id is caught even when the preamble is
    skipped.

    Args:
        session: Active database session
        predecessor_job_id: Job ID of the predecessor agent
        tenant_key: Tenant key for isolation
        project_id: Project UUID to validate predecessor belongs to same project
        mission: Original mission text
        agent_display_name: Display name of the successor agent (for logging)
        execution_mode: Project's execution_mode column value. Determines
                        whether any preamble is rendered at all.
        logger: Logger for diagnostic output (injected by the caller).

    Returns:
        Modified mission with predecessor context prepended (or unchanged
        mission in subagent modes).

    Raises:
        ResourceNotFoundError: Predecessor job not found
        ValidationError: Predecessor job belongs to a different project
    """
    # Always validate predecessor exists and belongs to same project + tenant.
    # This catches typo'd predecessor_job_id values even in the skip path.
    repo = AgentCompletionRepository()
    pred_job = await repo.get_predecessor_job(session, tenant_key, predecessor_job_id)

    if not pred_job:
        raise ResourceNotFoundError(
            message=f"Predecessor job '{predecessor_job_id}' not found",
            context={"predecessor_job_id": predecessor_job_id, "tenant_key": tenant_key},
        )
    if pred_job.project_id != project_id:
        raise ValidationError(
            message="Predecessor job belongs to a different project",
            context={
                "predecessor_job_id": predecessor_job_id,
                "predecessor_project_id": pred_job.project_id,
                "target_project_id": project_id,
            },
        )

    # Mode gate: subagent modes never get a preamble.
    # The orchestrator's CLI returned the predecessor result inline (Task() /
    # spawn_agent() / @-syntax) and is expected to splice findings into the
    # successor's mission text directly. Injecting a preamble here would
    # either duplicate that information or impose wrong-semantics framing.
    if execution_mode in SUBAGENT_EXECUTION_MODES:
        logger.info(
            "[PREDECESSOR_CONTEXT] Skipped: subagent mode, orchestrator splices inline",
            extra={
                "predecessor_job_id": sanitize(predecessor_job_id),
                "execution_mode": sanitize(execution_mode),
                "successor_display_name": sanitize(agent_display_name),
            },
        )
        return mission

    # Fetch predecessor's completion result for preamble rendering.
    pred_execution = await repo.get_completed_execution_for_job(session, tenant_key, predecessor_job_id)
    pred_display_name = pred_execution.agent_display_name if pred_execution else "Unknown"
    pred_result = (pred_execution.result or {}) if pred_execution else {}

    # Truncate summary to 2000 chars
    pred_summary = pred_result.get("summary", "No summary available")
    if len(pred_summary) > 2000:
        pred_summary = pred_summary[:2000] + " [TRUNCATED]"

    # Cap commits list to 10 entries
    pred_commits = pred_result.get("commits", ["No commits recorded"])
    if len(pred_commits) > 10:
        pred_commits = [*pred_commits[:10], f"... and {len(pred_commits) - 10} more"]

    # Auto-detect chain vs replacement from the predecessor's work-order
    # status FIRST, then its completion record. HO1023: the prior heuristic
    # of "no pred_execution -> replacement" was wrong for multi_terminal
    # staging, where the orchestrator pre-spawns chains BEFORE any phase
    # runs (so pred_execution is naturally None at spawn time without
    # implying failure). Replacement now requires an EXPLICIT failure
    # signal on the work order or the completion result.
    # Note: tenant_key is NOT included in the rendered get_agent_result(...)
    # call -- Wave 1 (commit ffa779bf) established that tenant_key is auto-
    # injected server-side and must never appear in agent-facing prose.
    is_replacement = _detect_replacement_semantics(pred_job, pred_execution)
    template = PREDECESSOR_REPLACEMENT_PREAMBLE if is_replacement else PREDECESSOR_CHAIN_PREAMBLE
    predecessor_context = template.format(
        pred_display_name=pred_display_name,
        predecessor_job_id=predecessor_job_id,
        pred_summary=pred_summary,
        pred_commits=pred_commits,
    )

    # BE-8003j: when the predecessor delivered an isolated PR (its result carries a
    # branch), append the base-branch hand-off so the successor's seed says which
    # branch to build ON. Byte-absent for shared-working-tree predecessors.
    base_branch_block = _build_base_branch_block(pred_result)

    mission = predecessor_context + base_branch_block + mission
    logger.info(
        "[PREDECESSOR_CONTEXT] Injected predecessor preamble",
        extra={
            "predecessor_job_id": sanitize(predecessor_job_id),
            "execution_mode": sanitize(execution_mode),
            "preamble_kind": "replacement" if is_replacement else "chain",
            "isolated_pr_handoff": bool(base_branch_block),
            "successor_display_name": sanitize(agent_display_name),
            "predecessor_display_name": sanitize(pred_display_name),
        },
    )
    return mission
