# Handover 0388: Fix Orchestrator ID vs Agent ID Confusion

**Status:** COMPLETE (2026-01-04)
**Priority:** HIGH
**Commits:** b3832e6e, c05ed337 (partial)

## Problem

The staging prompt showed `job_id` as "Orchestrator ID", but the `get_orchestrator_instructions()` MCP tool expected `agent_id`. These are TWO DIFFERENT UUIDs:

- `job_id` = "What are we doing" (work order/instructions)
- `agent_id` = "Who am I" (executor identity, used for MCP tool calls)

Alpha trial feedback: Agent discovered mismatch and had to extract `agent_id` from MCP response identity block.

## Solution

Updated prompts to show both IDs with clear semantics:

```
IDENTITY:
- Orchestrator Agent ID: {agent_id}  # WHO - use for MCP tool calls
- Job ID: {job_id}                   # WHAT - work order reference
```

## Files Modified

| File | Change |
|------|--------|
| `src/giljo_mcp/thin_prompt_generator.py` | Added agent_id to return dict, updated IDENTITY sections |
| `api/endpoints/prompts.py` | Added agent_id to response and WebSocket events |
| `frontend/src/components/projects/LaunchTab.vue` | Display Agent ID first |

## Testing

- Verified Python files import without errors
- Frontend already handled both fields with fallback logic

## Completion Notes

- No database changes required
- Backward compatible: `orchestrator_id` key still returned
- Fills gap in 0384-0401 range
