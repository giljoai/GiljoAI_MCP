# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Predecessor-context constants and preamble templates (HO1021).

`predecessor_job_id` on spawn_job is overloaded across two semantically distinct
workflows:
  - "chain"        : forward phase handoff (analyzer -> implementer -> documenter)
  - "replacement"  : reactivation, where a failed/blocked agent is being replaced

These need different preamble wording AND different gating. The legacy server
injected a single replacement-flavored preamble for every use of the parameter,
which (a) was semantically wrong for forward chains and (b) was redundant in
subagent execution modes where the orchestrator's CLI returns the predecessor
result inline (Task() / spawn_agent() / @-syntax) and the orchestrator can
splice findings into the next mission directly.

This module owns the constants, the role enumeration, and the two preamble
templates. The actual decision matrix (which template to render, when to skip
entirely) lives in JobLifecycleService._build_predecessor_context to keep the
DB-touching code in one place.

Neither preamble includes a `tenant_key="..."` arg in its example
get_agent_result(...) call -- that is a Wave 1 invariant (commit ffa779bf):
tenant_key is auto-injected server-side and must never appear in agent prose.
"""

from __future__ import annotations


VALID_PREDECESSOR_ROLES: frozenset[str] = frozenset({"chain", "replacement"})

# Execution modes where the orchestrator's CLI returns subagent results inline.
# In these modes, predecessor_role="chain" requires NO preamble injection at all
# because the orchestrator already has the predecessor result in working context
# and is expected to splice it into the successor's mission text directly.
# predecessor_role="replacement" still injects (rare but real: a failed Task()
# subagent being respawned legitimately needs the replacement preamble).
SUBAGENT_EXECUTION_MODES: frozenset[str] = frozenset({"claude_code_cli", "codex_cli", "gemini_cli"})

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
