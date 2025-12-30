# Handover 0380: update_agent_mission() MCP Tool

**Status**: Complete
**Date**: 2025-12-27
**Context Session**: Alpha testing revealed missing MCP tool for orchestrator staging flow

---

## Problem Statement

Alpha testing of the MCP server revealed that the staging prompt (Step 6) instructs the orchestrator to:

```
6. WRITE YOUR EXECUTION PLAN: Persist how you will coordinate agents during implementation.
   Call update_agent_mission(job_id='{orchestrator_id}', tenant_key='{self.tenant_key}', mission=YOUR_PLAN)
```

**But this MCP tool did not exist!**

### Impact

Without `update_agent_mission()`:
1. Orchestrator cannot persist its execution plan (parallel vs sequential, agent order, dependencies)
2. When user opens fresh terminal for implementation phase, orchestrator has no memory of staging decisions
3. The orchestrator receives placeholder text ("I am ready to create...") instead of real execution plan

---

## Root Cause Analysis

### Architecture Understanding

The orchestrator workflow has two phases:

```
STAGING (current terminal):
├── get_orchestrator_instructions() → context, fetch instructions, available agents
├── Orchestrator analyzes and plans
├── update_project_mission() → persist PROJECT mission (user-facing)
├── spawn_agent_job() for each specialist
├── update_agent_mission(job_id=ORCHESTRATOR_ID) → writes ITS OWN job ← MISSING!
└── Ready for implementation

IMPLEMENTATION (possibly fresh terminal):
├── Implementation prompt (7 hardcoded behavioral sections)
├── get_agent_mission(orchestrator_id) → retrieves persisted plan
└── Follows plan + behavioral guidance to coordinate agents
```

### HTTP MCP Architecture

Production MCP uses HTTP-only path (Handover 0334):

```
Client → /mcp endpoint → mcp_http.py → ToolAccessor → Database
```

The `@mcp.tool()` decorators in `orchestration.py` are for testing/legacy.
**ToolAccessor is authoritative for HTTP MCP.**

---

## Solution Implemented

### Files Modified

| File | Change |
|------|--------|
| `src/giljo_mcp/tools/tool_accessor.py` | Added `update_agent_mission()` method |
| `api/endpoints/mcp_http.py` | Added tool schema + handler mapping |
| `tests/tools/test_tool_accessor_update_agent_mission.py` | Integration test |

### New Method: ToolAccessor.update_agent_mission()

```python
async def update_agent_mission(
    self, job_id: str, tenant_key: str, mission: str
) -> dict[str, Any]:
    """
    Update the mission field of an AgentJob.

    Handover 0380: Used by orchestrators to persist their execution plan during staging.
    This allows fresh-session orchestrators to retrieve the plan via get_agent_mission()
    during implementation phase.

    Args:
        job_id: The AgentJob.job_id (work order UUID)
        tenant_key: Tenant isolation key
        mission: The execution plan/mission to persist

    Returns:
        {"success": True, "job_id": job_id, "mission_updated": True}
    """
```

### Key Features

1. **Tenant isolation**: Only updates jobs matching both `job_id` AND `tenant_key`
2. **WebSocket event**: Emits `job:mission_updated` for real-time UI updates
3. **Error handling**: Returns structured error for NOT_FOUND cases
4. **Logging**: Tracks mission updates for debugging

---

## Testing

### Test Cases

1. `test_update_agent_mission_success` - Basic update works
2. `test_update_agent_mission_not_found` - Returns error for missing job
3. `test_update_agent_mission_tenant_isolation` - Respects multi-tenant boundaries
4. `test_staging_to_implementation_flow` - E2E: write during staging, read in fresh session

### Running Tests

```bash
pytest tests/tools/test_tool_accessor_update_agent_mission.py -v
```

---

## How It Works

### During Staging (Orchestrator)

```python
# Step 6 of staging prompt
execution_plan = """
EXECUTION PLAN:
- Agent Order: sequential
- Phase 1: implementer-backend (API endpoints)
- Phase 2: implementer-frontend (Vue components)
- Phase 3: tester (integration tests)
- Checkpoints: After each phase, verify via get_workflow_status()
"""

# Orchestrator calls this MCP tool
result = update_agent_mission(
    job_id=orchestrator_id,
    tenant_key=tenant_key,
    mission=execution_plan
)
```

### During Implementation (Fresh Terminal)

```python
# Implementation prompt tells orchestrator to fetch its plan
mission_data = get_agent_mission(
    agent_job_id=orchestrator_id,
    tenant_key=tenant_key
)

# Returns:
# - mission: The execution plan written during staging
# - full_protocol: 6-phase agent lifecycle (behavioral guidance)
```

---

## Related Documents

- `agent_behaviour.txt` - Architecture: agent_id vs job_id, orchestrator writes own job
- `Agent instructions and where they live.md` - 3-layer instruction model
- Plan file: `C:\Users\giljo\.claude\plans\typed-watching-valiant.md`

---

## Deferred Work (Future PRs)

| Item | Priority | Notes |
|------|----------|-------|
| `mission_status` field | P2 | Store in `job_metadata`, not string-matching |
| Remove backward compat duplicates | P2 | Needs schema version bump |
| Consolidate 3 implementations | P3 | ToolAccessor is authoritative |
| Handover 0365 | P2 | Successor orchestrators get implementation prompt |

---

## Verification

After deployment, verify by:
1. Start alpha test project
2. Run staging flow - orchestrator should call `update_agent_mission()`
3. Close terminal
4. Open new terminal, launch implementation
5. Verify orchestrator retrieves its execution plan (not placeholder)

---

## References

- Staging prompt: `src/giljo_mcp/thin_prompt_generator.py:1010` (Step 6)
- Implementation prompt: `src/giljo_mcp/thin_prompt_generator.py:1097-1338`
- get_agent_mission: `src/giljo_mcp/services/orchestration_service.py:672-872`
