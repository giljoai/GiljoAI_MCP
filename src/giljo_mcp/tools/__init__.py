"""
GiljoAI MCP Tools Package (HTTP-only)

This package used to expose FastMCP (stdio) registration helpers. As of v3,
the project is HTTP-only (JSON-RPC over HTTP). To preserve import compatibility
for older scripts/tests, we provide lightweight placeholders that raise a clear
error if called. No stdio registration is performed here.

=============================================================================
PUBLIC MCP TOOLS (exposed via /mcp HTTP endpoint)
=============================================================================
Messaging: send_message, receive_messages, acknowledge_message, list_messages
  - Implemented in: api/endpoints/mcp_http.py via MessageService
  - Database: Message table with multi-tenant isolation
  - Contract: Handover 0295

Jobs: acknowledge_job, report_progress, complete_job, report_error
  - Implemented in: api/endpoints/mcp_http.py via AgentJobManager
  - Database: MCPAgentJob table

Orchestration: get_orchestrator_instructions, spawn_agent_job, etc.
  - Implemented in: api/endpoints/mcp_http.py via OrchestrationService
  - Database: MCPAgentJob, Project, Product tables

Projects: create_project, activate_project, etc.
  - Implemented in: api/endpoints/mcp_http.py via ProjectService
  - Database: Project table

Context: fetch_product_context, fetch_vision_document, fetch_tech_stack, etc.
  - Implemented in: api/endpoints/mcp_http.py via ContextService
  - Database: Product, VisionDocument, ContextConfiguration tables

=============================================================================
INTERNAL/LEGACY (NOT exposed via /mcp, for backward compatibility only)
=============================================================================
agent_messaging.py - FastMCP/stdio messaging tools
  - WARNING: Internal use only, use MessageService instead
  - Retained for: stdio compatibility, testing, debugging
  - See: Handover 0298

agent_communication.py - Legacy communication tools
  - WARNING: Internal use only, use MessageService instead
  - Retained for: legacy orchestrator code, backward compatibility
  - See: Handover 0298

agent_message_queue.py - Queue abstraction (use MessageService instead)
  - WARNING: Internal use only, use MessageService for new code
  - Retained for: JSONB counter persistence, legacy compatibility
  - See: Handover 0298

All legacy modules are marked INTERNAL/LEGACY in their module docstrings.
See Handover 0295 for the canonical messaging contract.
See Handover 0298 for cleanup decisions.
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
