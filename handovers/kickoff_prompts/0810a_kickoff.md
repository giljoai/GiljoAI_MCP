# 0810a Research: #40 + #41 — Workflow Status Orchestrator Distinction + Per-Agent Status

## Context

You are a research agent investigating whether #40 and #41 from the TinyContacts MCP Enhancement List are still valid issues.

**#40 Original Claim**: "Workflow status doesn't distinguish orchestrator from sub-agents" (P2, E1)
**#41 Original Claim**: "Per-agent status in workflow response" (P2, E2)

**Chain log**: `F:\GiljoAI_MCP\handovers\0808_tier2_chain_log.json` — update your session entry when done.

## Your Task

1. **Map `get_workflow_status()` completely**:
   - Find the MCP tool definition (name, parameters, description)
   - Trace: MCP tool handler -> service method -> DB queries -> response construction
   - Document the EXACT JSON response schema (every field)
   - Does it already include `is_orchestrator` or `role` or `agent_type`?

2. **Check if orchestrator distinction exists**:
   - How are orchestrators identified in the DB? (role field? is_orchestrator flag? template?)
   - Does `get_workflow_status()` already filter or tag orchestrators differently?
   - Does the `phase` field (added in 0411a) implicitly distinguish them?
   - Check: does `AgentJob.role` exist? What values can it have?

3. **Check if per-agent status already exists**:
   - Does the response include individual agent statuses?
   - Post-Feb work added `per-agent todo/message counts` (commit `a00a863e`) — is this sufficient?
   - What agent-level detail is in the response vs missing?

4. **Check what the orchestrator actually needs**:
   - When an orchestrator calls `get_workflow_status()`, what decisions does it make?
   - Does it need to know which agent is the orchestrator? Why?
   - Does it need per-agent status breakdowns? For what purpose?
   - Read the orchestrator prompt to understand expected usage patterns

5. **Deliver verdict for EACH item separately**:
   - #40: VALID / BY DESIGN / SUPERSEDED / NON-ISSUE
   - #41: VALID / BY DESIGN / SUPERSEDED / NON-ISSUE
   - Include the actual JSON response shape you found
   - If VALID: what specific fields should be added?

## Key Files to Start With

- `src/giljo_mcp/tools/` — find the get_workflow_status tool
- `src/giljo_mcp/services/orchestration_service.py` — the service method
- `src/giljo_mcp/models/agent_identity.py` — AgentJob model fields
- Commit `a00a863e` — per-agent todo/message counts addition

## Output

Update the chain log JSON at `F:\GiljoAI_MCP\handovers\0808_tier2_chain_log.json` with your session entry fields filled in. Since you investigate 2 items, include verdicts for both in `verdict` (e.g., "#40: BY DESIGN, #41: VALID BUG").

Use Serena MCP tools for efficient code navigation. Do NOT read entire files — use symbol search and overview tools.
