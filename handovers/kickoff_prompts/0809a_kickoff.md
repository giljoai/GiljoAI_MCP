# 0809a Research: CW-4 — Duration Timer Not Reactivated

## Context

You are a research agent investigating whether CW-4 from the February 2026 Handover Report is still a valid issue or has been superseded.

**CW-4 Original Claim**: "Duration Timer Not Reactivated — No mechanism to resume timing across sessions"

**Severity**: Medium (as originally filed)

**Chain log**: `F:\GiljoAI_MCP\handovers\0808_tier2_chain_log.json` — update your session entry when done.

## Your Task

1. **Find the timer mechanism**:
   - Where is "duration" stored? (AgentJob field? Project field? Frontend computed?)
   - How is it started? What triggers it?
   - How is it displayed? (Jobs tab? Project view? Dashboard?)
   - Is it server-side (DB column with timestamps) or client-side (JS interval)?

2. **Trace the timer lifecycle**:
   - Project created -> timer starts (how?)
   - Agent working -> timer running (how?)
   - Project handed over (0498 handover) -> what happens to timer?
   - Continuation orchestrator spawned (0497e) -> timer state?

3. **Check what "reactivation" means in practice**:
   - Is there a `started_at` / `completed_at` on AgentJob? On Project?
   - Is duration computed as `completed_at - created_at`? Or is it tracked separately?
   - When a project is handed over, does the new orchestrator get a new start time?
   - Is there a `paused` state or `total_active_duration` accumulator?

4. **Assess user impact**:
   - Does the dashboard show duration? Where exactly?
   - Is this a cosmetic issue (wrong number displayed) or functional (no timer at all)?
   - What does the user actually see during a multi-session project?

5. **Deliver verdict**: VALID BUG / BY DESIGN / SUPERSEDED / NON-ISSUE / COSMETIC
   - Include function/field traces
   - If VALID: describe scope and estimate effort
   - If COSMETIC: describe what's wrong and whether it matters

## Key Files to Start With

- `src/giljo_mcp/models/agent_identity.py` — AgentJob/AgentExecution models, timestamp fields
- `src/giljo_mcp/models/project.py` — Project model, any duration fields
- `frontend/src/components/projects/JobsTab.vue` — duration display
- `frontend/src/components/projects/ProjectTabs.vue` — project-level duration
- `src/giljo_mcp/services/orchestration_service.py` — handover flow

## Output

Update the chain log JSON at `F:\GiljoAI_MCP\handovers\0808_tier2_chain_log.json` with your session entry fields filled in.

Use Serena MCP tools for efficient code navigation. Do NOT read entire files — use symbol search and overview tools.
