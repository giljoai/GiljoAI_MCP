# Handover 0370: get_agent_mission Parameter Fix

**Date**: 2025-12-22
**Priority**: CRITICAL
**Status**: IN PROGRESS
**Estimated Effort**: 2-3 hours
**Related**: Bug Report `F:\TinyContacts\0366_GET_AGENT_MISSION_BUG_REPORT.md`

---

## Executive Summary

The `get_agent_mission` MCP tool fails with parameter mismatch error because:
- MCP HTTP schema (`mcp_http.py:415`) expects `agent_job_id`
- ToolAccessor (`tool_accessor.py:754`) expects `job_id`

**Impact**: ALL agents fail immediately when trying to fetch their mission after spawn.

---

## Root Cause Analysis

### Bug Chain

1. Agent calls: `mcp__giljo-mcp__get_agent_mission(agent_job_id="xxx", tenant_key="yyy")`
2. MCP HTTP handler extracts `arguments["agent_job_id"]`
3. Calls `tool_accessor.get_agent_mission(**arguments)`
4. ToolAccessor signature is `def get_agent_mission(self, job_id: str, ...)`
5. **Result**: `got an unexpected keyword argument 'agent_job_id'`

### Secondary Issue

`generic_agent_template.py` tells agents to use `agent_id` (executor UUID) instead of `agent_job_id` with `job_id` value (work order UUID).

---

## Audit Results

### MCP Tool Parameter Consistency (10 tools audited)

| Tool | Status |
|------|--------|
| `get_agent_mission` | **MISMATCH** |
| `spawn_agent_job` | OK |
| `acknowledge_job` | OK |
| `report_progress` | OK |
| `complete_job` | OK |
| `report_error` | OK |
| `get_workflow_status` | OK |
| `get_orchestrator_instructions` | OK |
| `get_pending_jobs` | OK |
| `get_next_instruction` | OK |

**Finding**: Only 1 tool has parameter mismatch. All other 9 tools are consistent.

### Thin Prompt Consistency

| File | Status |
|------|--------|
| `thin_prompt_generator.py` | CORRECT |
| `template_seeder.py` | CORRECT |
| `mcp_tool_catalog.py` | CORRECT |
| `orchestration_service.py` (prompts) | CORRECT |
| **`generic_agent_template.py`** | **BROKEN** |

---

## Files to Modify

### 1. `src/giljo_mcp/tools/tool_accessor.py` (Line 754)

**From**:
```python
async def get_agent_mission(self, job_id: str, tenant_key: str) -> dict[str, Any]:
    """Get agent-specific mission (delegates to OrchestrationService)"""
    return await self._orchestration_service.get_agent_mission(agent_job_id=job_id, tenant_key=tenant_key)
```

**To**:
```python
async def get_agent_mission(self, agent_job_id: str, tenant_key: str) -> dict[str, Any]:
    """Get agent-specific mission (delegates to OrchestrationService)"""
    return await self._orchestration_service.get_agent_mission(agent_job_id=agent_job_id, tenant_key=tenant_key)
```

### 2. `src/giljo_mcp/templates/generic_agent_template.py` (Lines 93, 108-111)

**Line 93 - Documentation fix**:
```python
# FROM:
- `mcp__giljo-mcp__get_agent_mission(agent_id, tenant_key)` - Fetches mission + protocol

# TO:
- `mcp__giljo-mcp__get_agent_mission(agent_job_id, tenant_key)` - Fetches mission + protocol
```

**Lines 108-111 - Example fix**:
```python
# FROM:
result = mcp__giljo-mcp__get_agent_mission(
    agent_id="{agent_id}",
    tenant_key="{tenant_key}"
)

# TO:
result = mcp__giljo-mcp__get_agent_mission(
    agent_job_id="{job_id}",
    tenant_key="{tenant_key}"
)
```

### 3. `src/giljo_mcp/services/orchestration_service.py` (Commit only)

**Status**: Lazy-load fix already applied (lines 90-102), just needs commit.

---

## Success Criteria

1. `get_agent_mission` accepts `agent_job_id` parameter without error
2. Spawned agent can successfully fetch its mission
3. All existing tests pass
4. New unit test validates parameter handling

## Verification Steps

```python
# This call should succeed:
mcp__giljo-mcp__get_agent_mission(
    agent_job_id="valid-job-uuid",
    tenant_key="valid-tenant"
)
```

---

## Semantic Reference (0366 Definition)

| Term | Meaning | Use For |
|------|---------|---------|
| `job_id` | Work order UUID (WHAT) | Mission, progress, completion |
| `agent_id` | Executor UUID (WHO) | Messaging, status |
| `agent_job_id` | DEPRECATED alias for job_id | Legacy compatibility |

---

## Testing Strategy

### Unit Test
- `test_tool_accessor_get_agent_mission_with_agent_job_id`

### Integration Test
- `test_spawn_then_fetch_mission_e2e`

### Manual Test
1. Start server
2. Create project, spawn agent job
3. Call `get_agent_mission` with returned `job_id` as `agent_job_id`
4. Verify mission returned

---

## Rollback Plan

If issues arise, revert:
1. `tool_accessor.py` - change parameter back to `job_id`
2. `generic_agent_template.py` - revert template changes

Risk: LOW - changes are isolated to parameter naming.

---

## Related Documents

- Bug Report: `F:\TinyContacts\0366_GET_AGENT_MISSION_BUG_REPORT.md`
- 0366 Series: `handovers/completed/0366*`
- Model Reference: `handovers/Reference_docs/0358_model_mapping_reference.md`
