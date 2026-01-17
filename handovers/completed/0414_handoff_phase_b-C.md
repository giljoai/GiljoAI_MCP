# Handover 0414: Handoff to Fresh Agent (Phase 0414b)

**Created**: 2026-01-11
**From**: Phase 0414a agent (context at 61%)
**To**: Fresh agent for Phase 0414b+

---

## Fresh Agent Start Prompt

Copy this entire prompt to start a fresh agent:

```
You are continuing Handover 0414: Rename `agent_type` to `agent_display_name` across the GiljoAI MCP codebase.

## CRITICAL CONTEXT (from Phase 0414a research)

### Semantic Meaning
- `agent_name` = NORTH STAR (template lookup key for color, rules, behavior) - DO NOT CHANGE
- `agent_display_name` = UI LABEL ONLY (what humans see on agent cards) - NEW NAME
- `agent_type` = OLD ambiguous name being replaced by `agent_display_name`

### Database Verified (2026-01-11)
```
agent_executions table:
  agent_type    | varchar(100) | not null  <-- RENAME to agent_display_name
  agent_name    | varchar(255) |           <-- KEEP (template lookup key)

agent_jobs table:
  job_type      | varchar(100) | not null  <-- DO NOT RENAME (different concept)
```

### Scope Summary
| Category | Occurrences |
|----------|-------------|
| Backend (src/, api/) | ~420 |
| Frontend | 151 |
| Tests | 961 |
| **GRAND TOTAL** | **~1,532** |

### DO NOT RENAME (Different Semantic Meaning)
- `AgentJob.job_type` - work order type, NOT executor type
- `subagent_type` - Task tool parameter (different concept)
- `agent_types` (plural) - RENAME to `agent_display_names`

### ZOMBIE CODE TO REMOVE IN 0414c (~200 lines)
1. `api/websocket.py:640-721` - `broadcast_agent_spawn()`, `broadcast_agent_complete()` - ZERO production callers
2. `api/websocket_service.py:16-42, 191-247` - `notify_agent_status()`, `notify_sub_agent_spawned()`, `notify_sub_agent_completed()` - ZERO callers
3. `src/giljo_mcp/orchestrator.py:1298-1300` - Dead code: `AgentRole(from_execution.agent_type)` created but never used

### Compound Variables & Functions to Rename
Backend:
- `by_agent_type` → `by_agent_display_name`
- `sender_agent_type` → `sender_agent_display_name`
- `agent_type_query`, `agent_type_result` → `agent_display_name_*`
- `max_agent_types` → `max_agent_display_names`

Frontend:
- `getAgentType()` → `getAgentDisplayName()`
- `getAgentTypeColor()` → `getAgentDisplayNameColor()`
- `agentTypeLabel` → `agentDisplayNameLabel`
- `data-agent-type` → `data-agent-display-name`
- `.agent-type-cell`, `.agent-type-secondary` CSS classes

## REQUIRED READING
1. `F:\GiljoAI_MCP\CLAUDE.md` - Project context
2. `F:\GiljoAI_MCP\handovers\0414_agent_display_name_migration.md` - Full handover details
3. `F:\GiljoAI_MCP\handovers\0414a_inventory_agent_type.md` - COMPLETE INVENTORY (this is your bible)
4. `F:\GiljoAI_MCP\handovers\Reference_docs\QUICK_LAUNCH.txt` - TDD discipline

## PHASE STATUS
- [x] **0414a**: Complete inventory - DONE (see 0414a_inventory_agent_type.md)
- [ ] **0414b**: Write TDD tests (RED phase) - START HERE
- [ ] **0414c**: Clean zombie code (~200 lines)
- [ ] **0414d**: Verify existing tests pass
- [ ] **0414e**: Execute name changes (~1,532 occurrences)
- [ ] **0414f**: Full E2E testing with Chrome extension

## YOUR TASK: Phase 0414b (TDD RED)

Write failing tests BEFORE any implementation. Tests should FAIL because `agent_display_name` doesn't exist yet.

### Test Files to Create

1. **Backend Model Test**: `tests/models/test_agent_display_name_migration.py`
   - Test that AgentExecution has `agent_display_name` field
   - Test that `agent_type` field does NOT exist (after migration)

2. **Backend API Test**: `tests/api/test_agent_display_name_schemas.py`
   - Test that API responses contain `agent_display_name`
   - Test that WebSocket events contain `agent_display_name`

3. **Frontend Test**: `frontend/src/components/projects/__tests__/AgentDisplayName.spec.js`
   - Test that components receive `agent_display_name` prop
   - Test that UI displays `agent_display_name`

### TDD Discipline
1. Write test FIRST (should FAIL - RED)
2. Run test to confirm it fails
3. DO NOT implement yet - that's Phase 0414e

### Migration Order (for 0414e)
1. DATABASE (Alembic migration + SQLAlchemy model)
2. API_SCHEMA (Pydantic models)
3. SERVICE_LAYER (services, repositories)
4. MCP_TOOLS (tool parameters)
5. API_ENDPOINTS (route handlers)
6. FRONTEND (Vue components, stores)
7. TESTS (fixtures, assertions)

## Key Files Reference

### Database/Models
- `src/giljo_mcp/models/agent_identity.py:170-174` - AgentExecution.agent_type Column

### API Schemas (14 occurrences)
- `api/schemas/agent_job.py:25,58,131`
- `api/endpoints/agent_jobs/models.py:21,94`
- `api/events/schemas.py:176,207,231,281,509,523,549,577,594`

### Services (~100 occurrences)
- `src/giljo_mcp/services/orchestration_service.py` - MOST occurrences
- `src/giljo_mcp/services/agent_job_manager.py`
- `src/giljo_mcp/services/message_service.py`

### MCP Tools (~80 occurrences)
- `src/giljo_mcp/tools/orchestration.py` - spawn_agent_job tool
- `src/giljo_mcp/tools/agent_coordination.py`

### Frontend (151 occurrences)
- `frontend/src/components/projects/JobsTab.vue` - main agent display
- `frontend/src/components/projects/LaunchTab.vue`
- `frontend/src/composables/useAgentData.js`

## Principles (Non-Negotiable)
1. TDD: RED → GREEN → REFACTOR
2. Use subagents from `.claude/agents/`
3. No bandaids - production-grade only
4. Chrome extension testing for UI verification
5. Clean zombie code BEFORE renaming (0414c)

## Git State
- Branch: `master`
- Clean baseline: `c1d122d1`
- Rollback command: `git reset --hard c1d122d1`

START WITH PHASE 0414b. Read the inventory document first.
```

---

## Summary of Phase 0414a Findings

### What Was Discovered

1. **Total Scope**: ~1,532 occurrences across ~150 files
2. **Database**: `agent_executions.agent_type` (varchar 100) confirmed
3. **Dual-Model**: AgentJob uses `job_type`, AgentExecution uses `agent_type`
4. **Zombie Code**: ~200 lines of dead code identified for removal
5. **Tenant Integration**: All agent_type queries include tenant_key filtering
6. **WebSocket Events**: All include agent_type in payload for UI display

### Files Created
- `handovers/0414a_inventory_agent_type.md` - Complete categorized inventory
- `handovers/0414_handoff_phase_b.md` - This handoff document

### Key Insight
The `AgentRole` enum (6 values) doesn't match actual `agent_type` values (custom names like "tdd-implementor"). Dead code at orchestrator.py:1298-1299 reveals this mismatch.
