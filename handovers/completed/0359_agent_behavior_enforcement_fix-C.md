# Handover 0359: Agent Behavior Enforcement Fix

**Status:** COMPLETE
**Date:** 2025-12-18
**Commits:** 5030d9f6, 40877f61, b6ef0332

---

## Problem Summary

Agents were misbehaving due to conflicting/incomplete instructions from 3 sources:

| Source | Content | Issue |
|--------|---------|-------|
| Agent Template `.claude/agents/*.md` | Full protocol, identity | Has placeholders like `{agent_id}` |
| Spawn Prompt `spawn_agent_job()` | Identity + startup | Used `{agent_type}` for receive_messages |
| Full Protocol `get_agent_mission()` | 5-phase lifecycle | Had literal `"your-type"` never replaced |

### Root Causes
1. `_generate_agent_protocol()` only accepted `job_id` and `tenant_key`, not `agent_name`
2. `receive_messages` requires `job_id` (UUID) but prompts used `agent_type`/`agent_name`
3. TodoWrite not mandatory in Phase 2
4. Progress format missing `steps_completed`/`steps_total` fields

---

## Solution: Fix Server-Side Prompts (No Template Changes)

All fixes were in dynamically generated prompts, NOT static agent templates.

### Changes Made

**1. Fixed `_generate_agent_protocol()` signature** (`orchestration_service.py:47-99`)
- Added `agent_name` parameter
- Replaced `"your-type"` with actual `{agent_name}` for `acknowledge_job`
- Fixed `receive_messages` to use `{job_id}` (UUID) for message routing

**2. Fixed spawn prompt** (`orchestration.py:838`)
- Changed `receive_messages(agent_id="{agent_type}")` to `receive_messages(agent_id="{agent_job_id}")`

**3. Added mandatory TodoWrite to Phase 2**
```
**MANDATORY FIRST STEP:**
1. Use TodoWrite to create 3-7 concrete tasks from your mission
2. Mark each todo as completed when finished
```

**4. Added step fields to progress format**
```python
progress={"percent": X, "message": "...", "steps_completed": Y, "steps_total": Z}
```

**5. Updated test** (`test_orchestration_service_agent_mission.py`)
- Changed from 6 phases to 5 phases (Handover 0359 consolidation)

**6. Fixed frontend template matching** (`AgentDetailsModal.vue`)
- Display agent name with optional role suffix
- Match templates by agent_type OR agent_name

---

## Key Insight

| Use Case | Field to Use | Why |
|----------|--------------|-----|
| Template matching (Task tool) | `agent_name` | SSOT per Handover 0351 |
| Message routing (receive_messages) | `job_id` (UUID) | Database queries by job_id |
| Logging/Display | `agent_name` | Human-readable |

---

## Files Modified

- `src/giljo_mcp/services/orchestration_service.py` - Protocol generation
- `src/giljo_mcp/tools/orchestration.py` - Spawn prompt
- `tests/services/test_orchestration_service_agent_mission.py` - Phase count
- `frontend/src/components/projects/AgentDetailsModal.vue` - Template matching

## Files NOT Modified

- `.claude/agents/*.md` - Agent templates unchanged (server prompts handle operational details)

---

## Testing

All 5 tests pass:
- `test_get_agent_mission_returns_full_protocol_by_default`
- `test_full_protocol_contains_five_phases`
- `test_full_protocol_references_mcp_tools`
- `test_full_protocol_includes_job_context`
- `test_response_backward_compatible_with_existing_fields`

---

## Token Impact

- Before: ~120 tokens in `full_protocol`
- After: ~150 tokens (+30 tokens for TodoWrite mandate and step fields)
- Trade-off: Small increase for reliable agent behavior
