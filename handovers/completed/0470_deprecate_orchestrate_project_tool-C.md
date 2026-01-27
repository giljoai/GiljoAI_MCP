# Handover 0470: Deprecate orchestrate_project MCP Tool

**Status**: COMPLETED
**Created**: 2026-01-26
**Completed**: 2026-01-27
**Tool Removed**: 2026-01-27 (ahead of scheduled 2026-03-01 removal)

## Summary

The `orchestrate_project` MCP tool has been deprecated because it bypasses the staging workflow introduced in the 0246 series.

## Background

### What orchestrate_project Does

The tool executes a full automated orchestration workflow:
1. Loads product and validates vision
2. Chunks vision documents if needed
3. Creates or uses existing project
4. Auto-generates mission plans via `MissionPlanner`
5. Auto-selects agents via `select_agents_for_mission()`
6. Assigns missions to selected agents
7. Coordinates workflow (waterfall pattern)
8. Returns comprehensive results

### Why It's Being Deprecated

The current recommended orchestrator workflow is **manual/staged**:
1. `get_orchestrator_instructions()` → fetch mission and context
2. `get_available_agents()` → discover available agents
3. `spawn_agent_job()` → create agent jobs with specific missions
4. `update_project_mission()` → persist mission plan

This manual workflow provides:
- Human-in-the-loop control over agent selection
- Explicit mission assignment per agent
- Staging phase separation from implementation
- Better alignment with thin-client architecture (0246 series)

### Git History

| Date | Commit | Description |
|------|--------|-------------|
| 2025-10-20 | `14a580fe` | Created (Handover 0020 Phase 3B) |
| 2025-11-03 | `fff92b2a` | Exposed in MCP HTTP adapter |
| 2026-01-23 | `a36c5c67` | Refactored to use OrchestrationService (0450) |
| 2026-01-26 | - | **DEPRECATED** |

## Changes Made

### Files Modified

1. **api/endpoints/mcp_http.py**
   - Commented out tool schema in `MCP_TOOLS` list
   - Commented out tool_map entry for `orchestrate_project`
   - Added deprecation comment with date and TODO

2. **api/endpoints/mcp_tools.py**
   - Commented out tool_map entry
   - Commented out documentation entry
   - Added deprecation comment with date and TODO

3. **src/giljo_mcp/tools/tool_accessor.py**
   - Added deprecation warning in docstring
   - Added `warnings.warn()` call with DeprecationWarning

4. **src/giljo_mcp/services/orchestration_service.py**
   - Added deprecation warning in docstring
   - Added `warnings.warn()` call with DeprecationWarning

## Deprecation Pattern

```python
# In docstring:
"""
DEPRECATED 2026-01-26: This tool bypasses the staging workflow.
Use get_orchestrator_instructions() + spawn_agent_job() instead.
TODO: Remove after 2026-03-01 if no issues discovered.
"""

# At runtime:
import warnings
warnings.warn(
    "orchestrate_project is deprecated since 2026-01-26. "
    "Use get_orchestrator_instructions() + spawn_agent_job() instead.",
    DeprecationWarning,
    stacklevel=2
)
```

## Migration Guide

### Before (Deprecated)
```python
result = await orchestrate_project(
    project_id="proj-123",
    tenant_key="tenant-abc"
)
# Auto-generates missions and spawns agents
```

### After (Recommended)
```python
# Step 1: Get orchestrator instructions
instructions = await get_orchestrator_instructions(
    job_id="orchestrator-job-id",
    tenant_key="tenant-abc"
)

# Step 2: Discover available agents
agents = await get_available_agents(
    tenant_key="tenant-abc",
    active_only=True
)

# Step 3: Spawn agents with specific missions
for agent_config in your_selected_agents:
    await spawn_agent_job(
        agent_display_name=agent_config.display_name,
        agent_name=agent_config.name,
        mission=agent_config.mission,
        project_id="proj-123",
        tenant_key="tenant-abc"
    )

# Step 4: Persist mission plan
await update_project_mission(
    project_id="proj-123",
    mission="Your condensed mission plan"
)
```

## Monitoring Period

**Duration**: 2026-01-26 to 2026-03-01 (~5 weeks)

### What to Monitor

1. **Server logs**: Check for any `DeprecationWarning` messages indicating usage
2. **Error reports**: Any failures related to missing `orchestrate_project` tool
3. **User feedback**: Any complaints about missing functionality

### Success Criteria for Removal

- No DeprecationWarning logs for 4+ weeks
- No error reports related to this tool
- No user complaints about missing functionality

## Removal Checklist (for 2026-03-01)

When removing the tool after the monitoring period:

- [ ] Delete commented code in `api/endpoints/mcp_http.py`
- [ ] Delete commented code in `api/endpoints/mcp_tools.py`
- [ ] Delete `orchestrate_project()` method from `tool_accessor.py`
- [ ] Delete `orchestrate_project()` method from `orchestration_service.py`
- [ ] Delete related tests in `tests/unit/test_mcp_orchestration_tools.py`
- [ ] Delete API endpoint in `api/endpoints/agent_jobs/orchestration.py`
- [ ] Update CLAUDE.md if it references `orchestrate_project`
- [ ] Archive this handover to `handovers/completed/`

## Related Handovers

- **0020**: Original implementation of MCP orchestration tools
- **0088**: Thin client architecture
- **0246a-c**: Orchestrator workflow pipeline (staging workflow)
- **0450**: Consolidation of orchestrator logic to OrchestrationService
