"""
GiljoAI MCP Tools Package (HTTP-only)

This package used to expose FastMCP (stdio) registration helpers. As of v3,
the project is HTTP-only (JSON-RPC over HTTP). To preserve import compatibility
for older scripts/tests, we provide lightweight placeholders that raise a clear
error if called. No stdio registration is performed here.
"""

from typing import Any


def _removed(*_: Any, **__: Any):
    raise NotImplementedError(
        "FastMCP/stdio tool registration has been removed; use HTTP JSON-RPC via api/endpoints/mcp_http.py."
    )


# Compatibility placeholders (no stdio support)
register_agent_tools = _removed
register_agent_communication_tools = _removed
register_agent_coordination_tools = _removed
register_external_agent_coordination_tools = _removed
register_agent_job_status_tools = _removed
register_agent_messaging_tools = _removed
register_agent_status_tools = _removed
register_context_tools = _removed
register_message_tools = _removed
register_optimization_tools = _removed
register_orchestration_tools = _removed
register_project_tools = _removed
register_project_closeout_tools = _removed
register_succession_tools = _removed
register_task_tools = _removed
register_template_tools = _removed


__all__ = [
    "register_agent_communication_tools",
    "register_agent_coordination_tools",
    "register_agent_job_status_tools",
    "register_agent_messaging_tools",
    "register_agent_status_tools",
    "register_agent_tools",
    "register_context_tools",
    "register_external_agent_coordination_tools",
    "register_message_tools",
    "register_optimization_tools",
    "register_orchestration_tools",
    "register_project_closeout_tools",
    "register_project_tools",
    "register_succession_tools",
    "register_task_tools",
    "register_template_tools",
]
