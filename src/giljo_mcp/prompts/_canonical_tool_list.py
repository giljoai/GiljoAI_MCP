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
CANONICAL_ORCHESTRATOR_TOOLS: tuple[str, ...] = (
    "mcp__giljo_mcp__health_check",
    "mcp__giljo_mcp__fetch_context",
    "mcp__giljo_mcp__spawn_job",
    "mcp__giljo_mcp__get_agent_mission",
    "mcp__giljo_mcp__send_message",
    "mcp__giljo_mcp__receive_messages",
    "mcp__giljo_mcp__inspect_messages",
    "mcp__giljo_mcp__report_progress",
    "mcp__giljo_mcp__set_agent_status",
    "mcp__giljo_mcp__get_workflow_status",
    "mcp__giljo_mcp__update_project_mission",
    "mcp__giljo_mcp__update_agent_mission",
    "mcp__giljo_mcp__complete_job",
    "mcp__giljo_mcp__close_job",
    "mcp__giljo_mcp__reactivate_job",
    "mcp__giljo_mcp__dismiss_reactivation",
    "mcp__giljo_mcp__write_360_memory",
    "mcp__giljo_mcp__close_project_and_update_memory",
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
