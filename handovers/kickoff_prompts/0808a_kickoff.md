# 0808a Research: CW-2 — Orchestrator Cannot Reactivate (reopen_job)

## Context

You are a research agent investigating whether CW-2 from the February 2026 Handover Report is still a valid issue or has been superseded by subsequent work.

**CW-2 Original Claim**: "Orchestrator Cannot Reactivate — no `reopen_job()` tool. Orchestrator handover (0498) may partially cover this use case."

**Severity**: Critical (as originally filed)

**Chain log**: `F:\GiljoAI_MCP\handovers\0808_tier2_chain_log.json` — update your session entry when done.

## Your Task

1. **Map the agent job lifecycle state machine** — find ALL status transitions in the codebase:
   - Where are AgentJob statuses defined? (model, constants, enums)
   - What MCP tools trigger status changes? Trace each: tool name -> service method -> DB update
   - What statuses exist? Map the full state diagram.

2. **Trace the "reactivation" scenario** — what happens when:
   - An orchestrator wants to give MORE work to a completed agent
   - An orchestrator wants to unblock a blocked agent
   - A continuation orchestrator (0497e successor) needs to work with prior agents

3. **Check if 0498 + 0497e already solve this**:
   - Read `handovers/completed/0498_early_termination_protocol-C.md` (or find it)
   - Read `handovers/completed/0497e_fresh_agent_recovery_flow-C.md` (or find it)
   - Does the handover/successor mechanism make reopen_job unnecessary?
   - Can you send a message to a completed agent? Does that matter?

4. **Check the actual MCP tools available to orchestrators**:
   - List all MCP tools an orchestrator can call
   - Is there any tool that changes agent status back from completed/blocked?
   - Is `send_message()` sufficient as a "wake up" mechanism?

5. **Deliver verdict**: VALID BUG / BY DESIGN / SUPERSEDED / NON-ISSUE
   - Include explicit function call chains you traced
   - If VALID: describe what's needed and estimate effort
   - If SUPERSEDED: cite the specific mechanism that replaced it

## Key Files to Start With

- `src/giljo_mcp/models/agent_identity.py` — AgentJob model, status field
- `src/giljo_mcp/services/orchestration_service.py` — status transition methods
- `src/giljo_mcp/tools/` — MCP tool definitions
- `src/giljo_mcp/services/agent_job_manager.py` — job lifecycle management

## Output

Update the chain log JSON at `F:\GiljoAI_MCP\handovers\0808_tier2_chain_log.json` with:
- `status`: "complete"
- `started_at` / `completed_at`: timestamps
- `verdict`: your determination
- `verdict_reasoning`: 2-3 sentence summary
- `code_flows_traced`: array of "function_a() -> function_b() -> ..." chains you mapped
- `findings`: detailed writeup (can be multi-paragraph)
- `implementation_needed`: true/false
- `notes_for_next`: if implementation needed, what should be built

Use Serena MCP tools for efficient code navigation. Do NOT read entire files — use symbol search and overview tools.
