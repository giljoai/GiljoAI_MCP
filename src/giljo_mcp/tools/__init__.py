"""
GiljoAI MCP Tools Package (HTTP-only)

This project is HTTP-only (JSON-RPC over HTTP at /mcp endpoint).
All MCP tools are implemented in api/endpoints/mcp_http.py via service layer.

=============================================================================
PUBLIC MCP TOOLS (exposed via /mcp HTTP endpoint)
=============================================================================
Messaging: send_message, receive_messages, list_messages
  - Implemented in: api/endpoints/mcp_http.py via MessageService
  - Database: Message table with multi-tenant isolation
  - Contract: Handover 0295

Jobs: acknowledge_job, report_progress, complete_job, report_error
  - Implemented in: api/endpoints/mcp_http.py via AgentJobManager
  - Database: AgentJob (work orders) + AgentExecution (executors)

Orchestration: get_orchestrator_instructions, spawn_agent_job, etc.
  - Implemented in: api/endpoints/mcp_http.py via OrchestrationService
  - Database: AgentJob, AgentExecution, Project, Product tables

Projects: create_project, activate_project, etc.
  - Implemented in: api/endpoints/mcp_http.py via ProjectService
  - Database: Project table

Context: fetch_product_context, fetch_vision_document, fetch_tech_stack, etc.
  - Implemented in: api/endpoints/mcp_http.py via ContextService
  - Database: Product, VisionDocument, ContextConfiguration tables

=============================================================================
ARCHITECTURE NOTE
=============================================================================
Stdio/FastMCP transport was removed in Handover 0334.
All clients connect via HTTP MCP with X-API-Key authentication.
See: docs/MCP_OVER_HTTP_INTEGRATION.md
"""

__all__: list[str] = []
