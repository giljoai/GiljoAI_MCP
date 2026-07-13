# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Canonical orchestrator MCP tool list — single source of truth.

CE-0033: extracted so the spawn-prompt builders and the orchestrator identity
prompt share one list. Drift across these surfaces caused the v2 friction
where the ToolSearch hint inside the identity arrived too late to save the
first round-trips.
"""

from __future__ import annotations


# The load-bearing tools every orchestrator needs schemas for.
# Order chosen for readability; runtime order is irrelevant — ToolSearch
# resolves them as a batch.
#
# INF-6049b / BE-6115a decision (deliberate exclusion): stage_project /
# implement_project / launch_implementation are NOT listed here. This tuple is the
# IN-JOB orchestrator boot bundle — the schemas a spawned orchestrator
# ToolSearch-loads at startup. Those three are USER/driving-agent lifecycle tools
# invoked from a human-facing session to drive a project through staging -> human
# gate -> implement; they are never called from inside a spawned job, so preloading
# them into the orchestrator boot would bloat its ToolSearch with tools it never uses.
# For launch_implementation this exclusion is ALSO load-bearing security (BE-6115a):
# it is the CLI door that flips implementation_launched_at, and keeping it out of the
# orchestrator's auto-loaded bundle means a spawned/staging agent has no schema for it
# and cannot self-unlock implementation — the human gate stays sacred. They are
# surfaced (callable, load-on-demand) via get_giljo_guide's lifecycle section instead
# — the correct home for tools used at specific lifecycle points.
CANONICAL_ORCHESTRATOR_TOOLS: tuple[str, ...] = (
    "mcp__giljo_mcp__health_check",
    "mcp__giljo_mcp__get_giljo_guide",
    "mcp__giljo_mcp__get_context",
    "mcp__giljo_mcp__spawn_job",
    "mcp__giljo_mcp__get_job_mission",
    # BE-9017 (F3): the staging prompt's step 2 calls get_staging_instructions, so
    # it must be in the orchestrator's ToolSearch boot bundle — its omission left the
    # schema unloaded exactly when the staging flow needs it (same class of late-hint
    # friction CE-0033 fixed for the rest of this roster).
    "mcp__giljo_mcp__get_staging_instructions",
    # BE-9012d: send_message / receive_messages / get_messages (the retired bus)
    # dropped in favor of the Hub. post_to_thread + get_thread_history replace them
    # in the SOLO orchestrator's own core coordination loop (Unblock / Broadcast /
    # RECEIVE, orchestrator_body.py) so they stay in the boot bundle -- every
    # orchestrator hits them on its first wake-up, not just a chain role. The
    # broader Hub roster (create_thread / join_thread / search_threads / get_my_turn)
    # stays a deliberate ToolSearch add-on for chain roles only (see
    # CH_SUB_ORCHESTRATOR's "ADD ... to your FIRST ToolSearch query" note in
    # chapters_chain.py) rather than a boot-bundle default.
    "mcp__giljo_mcp__post_to_thread",
    "mcp__giljo_mcp__get_thread_history",
    "mcp__giljo_mcp__report_progress",
    "mcp__giljo_mcp__set_agent_status",
    "mcp__giljo_mcp__get_workflow_status",
    "mcp__giljo_mcp__update_project_mission",
    "mcp__giljo_mcp__update_job_mission",
    "mcp__giljo_mcp__complete_job",
    "mcp__giljo_mcp__close_job",
    "mcp__giljo_mcp__resolve_reactivation",
    "mcp__giljo_mcp__write_memory_entry",
    "mcp__giljo_mcp__write_project_closeout",
    "mcp__giljo_mcp__get_agent_result",
    "mcp__giljo_mcp__create_task",
    "mcp__giljo_mcp__create_project",
    "mcp__giljo_mcp__list_projects",
    "mcp__giljo_mcp__request_approval",
)


def render_toolsearch_query() -> str:
    """Render the ``select:...`` query string for one ToolSearch call.

    Returns a comma-separated string of all canonical tools, prefixed with
    the ``select:`` directive recognised by Claude Code's ToolSearch.
    """
    return "select:" + ",".join(CANONICAL_ORCHESTRATOR_TOOLS)


def render_toolsearch_call_one_line() -> str:
    """Render the full ToolSearch invocation as a single executable line."""
    return f'ToolSearch(query="{render_toolsearch_query()}", max_results=25)'
