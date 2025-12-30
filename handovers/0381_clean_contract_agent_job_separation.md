# Handover 0381: Clean Contract - agent_id / job_id Separation

**Status**: Complete
**Date**: 2025-12-27
**Context Session**: Alpha testing revealed backward compatibility aliases causing duplicate data and confusion

---

## Problem Statement

Alpha testing of the MCP server revealed duplicated data in responses:
- `job_id` appearing 3 times
- `agent_id` appearing 2 times
- `agent_job_id` as a backward compatibility alias throughout

User explicitly requested: "we should not have any bridging, proxy or translation from new to old we should be on the new contract of agent_id and job_id separation... I don't want bandaids"

---

## The Clean Contract

### Core Concepts

| Field | Meaning | Persistence |
|-------|---------|-------------|
| `job_id` | Work order UUID - "what are you working on" | Persists across succession |
| `agent_id` | Executor UUID - "who is executing" | Changes on succession |

### MCP Tool Parameter Names

**Before** (with backward compat):
```python
get_agent_mission(agent_job_id="uuid", tenant_key="key")  # Confusing name
```

**After** (clean contract):
```python
get_agent_mission(job_id="uuid", tenant_key="key")  # Clear: work order UUID
```

### Response Structure

**Before**:
```python
{
    "success": True,
    "agent_job_id": "uuid",  # Backward compat
    "job_id": "uuid",        # Duplicate
    "agent_id": "uuid",      # Sometimes duplicated
    # ... plus other backward compat fields
}
```

**After**:
```python
{
    "success": True,
    "job_id": "uuid",    # Work order (what)
    "agent_id": "uuid",  # Executor (who)
    # Clean, no duplicates
}
```

---

## Files Modified

### Core Service Layer

| File | Changes |
|------|---------|
| `src/giljo_mcp/tools/tool_accessor.py` | Removed 6 backward compat fields from `get_orchestrator_instructions()`, updated `get_agent_mission()` signature |
| `src/giljo_mcp/services/orchestration_service.py` | Removed all backward compat aliases, renamed `agent_job_id` param to `job_id` in `get_agent_mission()` |
| `src/giljo_mcp/tools/orchestration.py` | Removed 5 backward compat fields from response dictionaries |

### MCP HTTP Schema

| File | Changes |
|------|---------|
| `api/endpoints/mcp_http.py` | Updated `get_agent_mission` schema: `agent_job_id` -> `job_id` |

### Prompt Templates

| File | Changes |
|------|---------|
| `src/giljo_mcp/thin_prompt_generator.py` | Updated MCP tool call examples to use `job_id` |
| `src/giljo_mcp/templates/generic_agent_template.py` | Updated MCP tool documentation |
| `src/giljo_mcp/template_seeder.py` | Updated MCP tool examples |
| `src/giljo_mcp/prompt_generation/mcp_tool_catalog.py` | Updated all tool parameter documentation |

### API Endpoints

| File | Changes |
|------|---------|
| `api/endpoints/agent_jobs/succession.py` | Updated to use clean contract fields |
| `src/giljo_mcp/models/schemas.py` | `SuccessionResponse` schema: `successor_job_id` -> `job_id`, `current_job_id` -> `current_agent_id` |

### Tests

| File | Changes |
|------|---------|
| `tests/tools/test_tool_accessor_update_agent_mission.py` | Updated `agent_job_id` -> `job_id` |

---

## Breaking Changes

### MCP Tool Contract Changes

1. **`get_agent_mission()`** - Parameter renamed:
   - Old: `agent_job_id` (confusing - it's actually job_id)
   - New: `job_id` (clear - work order UUID)

2. **Response fields removed**:
   - `agent_job_id` alias removed (use `job_id`)
   - Various duplicate fields removed

### API Endpoint Changes

1. **`POST /agent-jobs/{job_id}/trigger-succession`** response schema:
   - `current_job_id` -> `current_agent_id`
   - `successor_job_id` -> `job_id`

---

## Database Column Names Unchanged

The following database columns are **NOT** changed (would require migration):
- `Task.agent_job_id` - FK to AgentJob
- Index `idx_task_agent_job`
- Index `idx_task_tenant_agent_job`

These column names are internal implementation details, not API contracts.

---

## Testing

### Run Specific Tests

```bash
# Test the update_agent_mission MCP tool
pytest tests/tools/test_tool_accessor_update_agent_mission.py -v

# Test staging to implementation flow
pytest tests/tools/test_tool_accessor_update_agent_mission.py::test_staging_to_implementation_flow -v
```

### Known Test Updates Needed

Tests expecting old response structure will need updates:
- `tests/api/test_agent_jobs_api.py` - Multiple assertions for `agent_job_id`
- `tests/integration/test_agent_card_realtime.py` - Spawning tests
- `tests/fixtures/test_mock_agent_simulator.py` - Mock data

---

## Verification

After deployment, verify by:
1. Call `get_agent_mission(job_id="uuid", tenant_key="key")`
2. Verify response contains `job_id` and `agent_id` (no duplicates)
3. Verify no `agent_job_id` backward compat field in response
4. Run staging -> implementation flow

---

## Related Handovers

- **0380**: Added `update_agent_mission()` MCP tool (enabling this cleanup)
- **0366-0378**: Agent ID vs Job ID refactor series (conceptual foundation)
- **0358b**: Dual-model architecture (AgentJob + AgentExecution)

---

## Summary

Removed all backward compatibility aliases for `agent_job_id`:
- ~15 files modified
- ~50 lines of backward compat code removed
- Clean contract: `job_id` (work order) + `agent_id` (executor)
- No more duplicate fields in responses
- MCP tool parameter `agent_job_id` renamed to `job_id`
