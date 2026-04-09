# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Team context header generation for agent missions."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.giljo_mcp.models import AgentExecution


def _generate_team_context_header(
    current_job: AgentExecution,
    all_project_jobs: list[AgentExecution],
    mission_lookup: dict[str, str] | None = None,
) -> str:
    """
    Generate team-aware context header for agent missions (Handover 0353, 0358b, 0367a).

    This header provides each agent with:
    - YOUR IDENTITY: Role + agent_id for MCP tool calls
    - YOUR TEAM: Roster of all agents on the project
    - YOUR DEPENDENCIES: Upstream/downstream relationships (inferred from roles)
    - COORDINATION: Messaging guidance

    Handover 0367a: Removed MCPAgentJob support - now AgentExecution only.
    For AgentExecution, mission is retrieved from mission_lookup dict or job relationship.

    Args:
        current_job: The agent execution receiving the mission
        all_project_jobs: All agent executions on the same project
        mission_lookup: Optional dict mapping job_id to mission text (for dual-model)

    Returns:
        Multi-line markdown header to prepend to the mission text
    """
    # AgentExecution only
    agent_name = getattr(current_job, "agent_name", None) or getattr(current_job, "agent_display_name", "unknown")
    agent_display_name = getattr(current_job, "agent_display_name", "unknown")

    # For AgentExecution, use agent_id
    agent_id = getattr(current_job, "agent_id", "unknown")
    job_id = getattr(current_job, "job_id", agent_id)

    # Build YOUR IDENTITY section (use agent_id for MCP calls)
    identity_section = f"""## YOUR IDENTITY
You are **{agent_name.upper()}** (agent_id: `{agent_id}`, job_id: `{job_id}`)
Role: {agent_display_name}
"""

    # Build YOUR TEAM section
    num_agents = len(all_project_jobs)
    team_rows = []
    for job in all_project_jobs:
        role_name = getattr(job, "agent_name", None) or getattr(job, "agent_display_name", "unknown")

        # Get mission: prefer lookup dict (avoids lazy load), then direct attribute
        # IMPORTANT: Check mission_lookup FIRST to avoid SQLAlchemy lazy load errors
        # when AgentExecution objects are accessed outside session context (Handover 0366 fix)
        mission_text = ""
        if mission_lookup and hasattr(job, "job_id") and job.job_id in mission_lookup:
            mission_text = mission_lookup[job.job_id]
        elif hasattr(job, "mission") and job.mission:
            mission_text = job.mission

        # Extract a short deliverable summary from the mission (first 80 chars)
        deliverable_preview = (mission_text or "")[:80].replace("\n", " ")
        if len(mission_text or "") > 80:
            deliverable_preview += "..."
        job_agent_id = getattr(job, "agent_id", "unknown")
        team_rows.append(
            f"| {role_name} | `{job_agent_id}` | {getattr(job, 'agent_display_name', 'unknown')} | {deliverable_preview} |"
        )

    team_table = "\n".join(team_rows)
    team_section = f"""## YOUR TEAM
This project has {num_agents} agent(s) working together:

| Agent | agent_id | Role | Deliverables |
|-------|----------|------|--------------|
{team_table}
"""

    # Build YOUR DEPENDENCIES section
    # Infer basic dependencies based on common role relationships
    dependencies_upstream = []
    dependencies_downstream = []

    # Common dependency patterns (can be expanded)
    dependency_rules = {
        "analyzer": {"upstream": [], "downstream": ["implementer", "documenter", "tester"]},
        "implementer": {"upstream": ["analyzer"], "downstream": ["tester", "reviewer", "documenter"]},
        "tester": {"upstream": ["implementer"], "downstream": ["reviewer"]},
        "reviewer": {"upstream": ["implementer", "tester"], "downstream": ["documenter"]},
        "documenter": {"upstream": ["analyzer", "implementer", "reviewer"], "downstream": []},
    }

    # Get other agents (exclude current by agent_id or job_id)
    current_id = getattr(current_job, "agent_id", None) or getattr(current_job, "job_id", None)
    other_agents = [
        j for j in all_project_jobs if (getattr(j, "agent_id", None) or getattr(j, "job_id", None)) != current_id
    ]
    other_types = {getattr(j, "agent_display_name", "unknown") for j in other_agents}

    if agent_display_name in dependency_rules:
        rules = dependency_rules[agent_display_name]
        dependencies_upstream.extend([upstream for upstream in rules["upstream"] if upstream in other_types])
        dependencies_downstream.extend([downstream for downstream in rules["downstream"] if downstream in other_types])

    if dependencies_upstream:
        upstream_text = f"- You depend on: {', '.join(dependencies_upstream)} (wait for their outputs if needed)"
    else:
        upstream_text = "- You depend on: None (you can start immediately)"

    if dependencies_downstream:
        downstream_text = (
            f"- Others depend on you: {', '.join(dependencies_downstream)} (notify them when your work is ready)"
        )
    else:
        downstream_text = "- Others depend on you: None"

    dependencies_section = f"""## YOUR DEPENDENCIES
{upstream_text}
{downstream_text}
"""

    # Build COORDINATION section
    coordination_section = f"""## COORDINATION
- **UUID-ONLY MESSAGING**: Always use agent_id UUIDs from the team table above when addressing agents
- Use `mcp__giljo_mcp__send_message(to_agents=["{agent_id}"], from_agent="{agent_id}", ...)` with UUID values
- Use `mcp__giljo_mcp__receive_messages` to check for instructions or updates
- When you complete a deliverable, send a brief status message to downstream agents using their agent_id UUIDs
- Use `to_agents=['all']` for broadcast messages to the entire team
- NEVER use display names (e.g., "orchestrator", "implementer") in to_agents - use the UUID from the team table
- Check `full_protocol` for detailed messaging and progress reporting guidance

---

"""

    return identity_section + "\n" + team_section + "\n" + dependencies_section + "\n" + coordination_section
