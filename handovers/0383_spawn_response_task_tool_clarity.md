# Handover 0383: Spawn Response Task Tool Clarity

**Status**: Ready
**Date**: 2026-01-01
**Priority**: HIGH
**Estimated Hours**: 1-2 hours
**Context**: Alpha testing revealed orchestrator confusion between agent_name and agent_type

---

## Problem Statement

Alpha testing revealed that orchestrators may confuse `agent_name` (template filename) with `agent_type` (UI category) when writing execution plans that use `Task(subagent_type=...)`.

### The Failure Scenario

```python
# Orchestrator spawns agent
spawn_agent_job(
    agent_type="implementer",           # UI category
    agent_name="implementer-frontend",  # Template filename
    ...
)

# Response only shows both fields - no explicit guidance
{
    "job_id": "...",
    "agent_name": "implementer-frontend",
    "agent_type": "implementer"
}

# Orchestrator writes execution plan using WRONG field
"Task(subagent_type='implementer', ...)"  # WRONG - used agent_type

# Implementation phase fails
# Task tool looks for .claude/agents/implementer.md - doesn't exist!
```

### Why It's Confusing

1. **Semantic similarity**: `agent_name` vs `agent_type` are easy to mix up
2. **Works when they match**: Simple cases like `analyzer/analyzer` don't expose the bug
3. **Cross-session boundary**: Staging orchestrator writes plan, implementation orchestrator executes

---

## Solution: Option B + C

### Option B: Echo task_tool_usage in Spawn Response

Add explicit Task tool example to spawn_agent_job response:

```python
{
    "success": True,
    "job_id": "uuid-here",
    "agent_id": "uuid-here",
    "agent_name": "implementer-frontend",
    "agent_type": "implementer",
    "task_tool_usage": "Task(subagent_type='implementer-frontend', ...)"  # NEW
}
```

### Option C: Warning When Names Differ

When `agent_name != agent_type`, add explicit warning:

```python
{
    "success": True,
    "job_id": "uuid-here",
    "agent_name": "implementer-frontend",
    "agent_type": "implementer",
    "task_tool_usage": "Task(subagent_type='implementer-frontend', ...)",
    "warning": "agent_name differs from agent_type - Task tool MUST use agent_name"  # NEW
}
```

---

## Files to Modify

### 1. src/giljo_mcp/tools/orchestration.py

**Location**: `spawn_agent_job()` function (~line 2600-2650)

**Change**: Add `task_tool_usage` and conditional `warning` to response dict

```python
# After successful spawn, build response
response = {
    "success": True,
    "job_id": str(job.job_id),
    "agent_id": str(execution.agent_id),
    "agent_name": agent_name,
    "agent_type": agent_type,
    # Option B: Explicit Task tool usage
    "task_tool_usage": f"Task(subagent_type='{agent_name}', ...)",
}

# Option C: Warning when names differ
if agent_name != agent_type:
    response["warning"] = (
        f"agent_name '{agent_name}' differs from agent_type '{agent_type}'. "
        "Task tool MUST use agent_name (template filename), NOT agent_type."
    )
```

### 2. src/giljo_mcp/services/orchestration_service.py

**Location**: `spawn_agent_job()` method in OrchestrationService

**Change**: Mirror the same response structure if service layer returns response

### 3. api/endpoints/mcp_http.py

**Location**: spawn_agent_job handler

**Change**: Ensure new fields pass through to response

---

## Testing

### Unit Tests

```python
# tests/tools/test_spawn_agent_job_clarity.py

def test_spawn_response_includes_task_tool_usage():
    """Option B: Response includes explicit Task tool example"""
    result = await spawn_agent_job(
        agent_type="implementer",
        agent_name="implementer-frontend",
        mission="Build frontend",
        project_id=project_id,
        tenant_key=tenant_key
    )

    assert result["task_tool_usage"] == "Task(subagent_type='implementer-frontend', ...)"

def test_spawn_response_warning_when_names_differ():
    """Option C: Warning shown when agent_name != agent_type"""
    result = await spawn_agent_job(
        agent_type="implementer",
        agent_name="implementer-frontend",  # Different!
        ...
    )

    assert "warning" in result
    assert "agent_name" in result["warning"]
    assert "MUST use agent_name" in result["warning"]

def test_spawn_response_no_warning_when_names_match():
    """No warning when agent_name == agent_type"""
    result = await spawn_agent_job(
        agent_type="analyzer",
        agent_name="analyzer",  # Same!
        ...
    )

    assert "warning" not in result
```

### Integration Test

```python
def test_orchestrator_uses_correct_field_in_execution_plan():
    """E2E: Verify orchestrator picks up task_tool_usage correctly"""
    # 1. Spawn agent with different name/type
    # 2. Verify response includes task_tool_usage
    # 3. Simulate orchestrator writing execution plan
    # 4. Verify plan uses agent_name, not agent_type
```

---

## Success Criteria

1. [ ] spawn_agent_job response includes `task_tool_usage` field
2. [ ] Warning appears when `agent_name != agent_type`
3. [ ] No warning when names match (clean response)
4. [ ] All existing tests pass
5. [ ] New tests added and passing
6. [ ] Alpha test repeated - orchestrator uses correct field

---

## Deferred Work

**Handover 0384**: Full rename refactor (`agent_name` -> `template_name`, `agent_type` -> `agent_category`)
- Requires comprehensive research across frontend, backend, database, prompts
- Breaking change - defer to v4.0
- This handover (0383) is the interim fix

---

## Related Documents

- **0381**: Clean contract - agent_id/job_id separation (similar clarity issue)
- **0380**: update_agent_mission() MCP tool
- **Alpha Test Feedback**: Session where confusion was identified

---

## Implementation Notes

- This is a LOW-RISK change - only adds fields to response
- No breaking changes to existing consumers
- Immediate benefit for orchestrator clarity
- ~30 minutes implementation time

---

## Verification

After implementation:
1. Run spawn_agent_job with `agent_name="implementer-frontend"`, `agent_type="implementer"`
2. Verify response includes `task_tool_usage` with correct agent_name
3. Verify `warning` field present
4. Run staging flow - verify orchestrator writes correct Task tool calls
