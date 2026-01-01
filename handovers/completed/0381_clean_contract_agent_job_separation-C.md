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

## Database Schema Changes (Phase 2)

**Updated** (aggressive cleanup):

| Model | Old | New |
|-------|-----|-----|
| `Task.agent_job_id` | Column name | `Task.job_id` |
| `idx_task_agent_job` | Index name | `idx_task_job` |
| `idx_task_tenant_agent_job` | Index name | `idx_task_tenant_job` |

**Files Updated**:
- `src/giljo_mcp/models/tasks.py` - Column and index renames
- `src/giljo_mcp/agent_job_manager.py` - Query updated
- `src/giljo_mcp/services/task_service.py` - Response field renamed
- `src/giljo_mcp/services/message_service.py` - Internal param renamed

**Note**: Fresh installs via `install.py` will create correct schema. Existing installs need DB reset (dev mode).

---

## API Response Model Changes (Phase 2)

| File | Model | Old Field | New Field |
|------|-------|-----------|-----------|
| `api/endpoints/agent_jobs/models.py` | SpawnAgentResponse | `agent_job_id` | `job_id` |
| `api/schemas/task.py` | TaskResponse | `agent_job_id` | `job_id` |

**WebSocket Event Changes**:
- `api/websocket.py` - `agent:created` event now uses `job_id` (removed duplicate `agent_job_id`)
- `api/websocket_event_listener.py` - Event handler reads `job_id` (removed fallback)
- `api/endpoints/agent_jobs/lifecycle.py` - Spawn broadcast uses `job_id`

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

**Phase 1**: Removed backward compatibility aliases from service/tool layer
**Phase 2**: Extended cleanup to database schema and API response models

Total cleanup:
- ~25 files modified (runtime code + 24 test files)
- ~60 lines of backward compat code removed
- Database column `Task.agent_job_id` → `Task.job_id`
- API response fields standardized to `job_id`
- WebSocket events use canonical `job_id` field
- Clean contract: `job_id` (work order) + `agent_id` (executor)
- Zero `agent_job_id` references in runtime code (comments only)

---

## Progress Updates

### 2026-01-01 - Closeout Review
**Status:** Completed
**Work Done:**
- Verified all `agent_job_id` references in src/ and api/ are comments only (5 occurrences, all documentation)
- Phase 1 (service/tool layer) and Phase 2 (database schema, API responses) both complete
- All tests passing with new `job_id` contract
- WebSocket events use canonical `job_id` field

**Final Notes:**
- Clean contract established: `job_id` (work order) + `agent_id` (executor)
- ~25 files modified, ~60 lines backward compat code removed
- Database column `Task.agent_job_id` → `Task.job_id` complete
