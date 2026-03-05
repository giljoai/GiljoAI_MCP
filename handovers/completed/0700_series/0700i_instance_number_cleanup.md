# Handover 0700i: instance_number Column Cleanup

## Context

**Decision**: Pre-release cleanup - remove the deprecated instance_number column from AgentExecution.

**Rationale**:
- Handover 0461b deprecated instance_number for single-instance-per-agent model
- Handover 0700d removes the legacy succession system (trigger_succession endpoint, etc.)
- The column was used for succession ordering (Orchestrator #1 -> #2 -> #3)
- With succession removed, all agents are effectively instance 1
- No external users exist - safe to remove pre-v1.0

**Reference**: Strategic direction change documented in dead_code_audit.md (2026-02-04)

## Research Summary

**Total References Found:** ~500 lines across ~80 files

**Key Finding:** After succession removal (0700d), the instance_number column serves ONLY as:
1. An ordering mechanism to find latest execution per job
2. A UI display field (showing Instance #1)

Neither of these functions is essential once succession is removed. The latest execution queries can use id DESC (UUID + timestamp semantics) or started_at DESC instead.

## Usage Categories

| Category | Count | Files | Action |
|----------|-------|-------|--------|
| Model/Schema definition | 15 lines | 2 | DELETE column + constraints |
| ORDER BY queries (get latest) | ~40 usages | 15 | REFACTOR to started_at DESC |
| Setting instance_number=1 | ~25 usages | 10 | DELETE (no longer needed) |
| API response fields | ~15 usages | 8 | REMOVE from responses |
| Frontend display | ~30 usages | 12 | REMOVE Instance #N display |
| Succession test files | ~200 lines | 7 | DELETE entire files |
| Test fixtures | ~100 usages | 25 | UPDATE to remove field |
| Archived migrations | ~50 lines | 6 | NO ACTION (read-only archive) |

**Summary:** ~100-150 lines of dead code deletion + ~40 query refactors + ~100 test updates

## Recommendation

**Full removal** of the instance_number column is recommended.

After succession removal (0700d), the column serves no functional purpose. The get latest execution pattern can be replaced with started_at ordering, which is semantically more correct anyway (we want the most recently started execution, not the highest instance number).

## Scope

Remove AgentExecution.instance_number column and all related code.


### Affected Components

**1. Model Definition** (src/giljo_mcp/models/agent_identity.py):
- Column definition: Lines 180-185
- UniqueConstraint: (agent_id, instance_number) -> Line 324
- CheckConstraint: instance_number >= 1 -> Line 334
- Index: idx_agent_executions_instance -> Line 320
- Relationship order_by: Line 114

**2. Services with ORDER BY Queries** (Critical - REFACTOR):

| File | Lines | Pattern |
|------|-------|---------|
| orchestration_service.py | 991, 1301, 1495, 1719, 1926, 3062, 3455, 3575 | .order_by(AgentExecution.instance_number.desc()) |
| message_service.py | 208, 276, 360, 715, 1246 | .order_by(AgentExecution.instance_number.desc()) |
| agent_job_manager.py | 241, 318, 460, 522, 625 | .order_by(AgentExecution.instance_number) |
| agent_health_monitor.py | 173, 188, 259, 274, 349, 364 | max(instance_number) subquery |
| thin_prompt_generator.py | 203, 253 | .order_by(AgentExecution.instance_number.desc()) |

**3. API Endpoints**:
- api/endpoints/prompts.py - 10 usages (parameter + response)
- api/endpoints/agent_jobs/table_view.py - 3 usages
- api/endpoints/agent_jobs/executions.py - 3 usages
- api/endpoints/agent_jobs/simple_handover.py - 2 usages
- api/endpoints/projects/status.py - 2 usages

**4. Frontend Components**:
- AgentTableView.vue - Displays Instance #N column
- LaunchSuccessorDialog.vue - Shows instance number in dialog
- SuccessionTimeline.vue - Entire component may be dead
- MessageStream.vue - Instance number in messages
- agentJobsStore.js - Stores and uses instance_number

**5. Succession Test Files** (DELETE ENTIRELY after 0700d):
- tests/integration/test_succession_workflow.py
- tests/integration/test_succession_multi_tenant.py
- tests/integration/test_succession_edge_cases.py
- tests/integration/test_succession_database_integrity.py
- tests/performance/test_succession_performance.py
- tests/security/test_succession_security.py
- tests/smoke/test_succession_smoke.py
- tests/fixtures/succession_fixtures.py

**6. Migration Files**:
- migrations/versions/baseline_v32_unified.py - Update to remove column

## Tasks

### Phase 1: Update Model (Database Schema)

1. [ ] Remove column from AgentExecution model (lines 180-185)

2. [ ] Remove constraints from __table_args__:
   - DELETE: Index(idx_agent_executions_instance, job_id, instance_number)
   - DELETE: UniqueConstraint(agent_id, instance_number, name=uq_agent_instance)
   - DELETE: CheckConstraint(instance_number >= 1, ...)

3. [ ] Update AgentJob relationship order_by (Line 114):
   - FROM: order_by=AgentExecution.instance_number
   - TO: order_by=AgentExecution.started_at

4. [ ] Update __repr__ method to remove instance reference

### Phase 2: Refactor ORDER BY Queries (CRITICAL)

5. [ ] Replace instance_number ordering with started_at DESC
   
   Replacement pattern:
   FROM: .order_by(AgentExecution.instance_number.desc()).limit(1)
   TO: .order_by(AgentExecution.started_at.desc()).limit(1)

6. [ ] Special case: agent_health_monitor.py subqueries
   FROM: func.max(AgentExecution.instance_number).label(max_instance)
   TO: func.max(AgentExecution.started_at).label(latest_started)

### Phase 3: Remove from API Layer

7. [ ] Update Pydantic schemas:
   - api/schemas/prompt.py - Remove instance_number field
   - api/endpoints/agent_jobs/models.py - Remove from AgentJobResponse, ExecutionResponse

8. [ ] Update API endpoints:
   - api/endpoints/prompts.py - Remove parameter and response field
   - api/endpoints/agent_jobs/*.py - Remove from responses

### Phase 4: Update Frontend

9. [ ] Remove Instance column from AgentTableView.vue
10. [ ] Update LaunchSuccessorDialog.vue to not reference instance_number
11. [ ] Remove instance number display from MessageStream.vue
12. [ ] Update agentJobsStore.js to not track instance_number

### Phase 5: Delete Succession Tests

13. [ ] Delete succession test files (after 0700d completes)

### Phase 6: Update Remaining Tests

14. [ ] Update test fixtures to remove instance_number parameter
15. [ ] Update test assertions that check instance_number

### Phase 7: Migration and Verification

16. [ ] Update baseline migration to remove column
17. [ ] Run verification tests


## Verification

- [ ] Column removed from model definition
- [ ] All constraints/indexes removed
- [ ] Zero active code references (grep returns 0)
- [ ] All ORDER BY queries updated to use started_at
- [ ] API responses no longer include instance_number
- [ ] Frontend no longer displays Instance #N
- [ ] All tests pass
- [ ] Fresh install completes without errors

## Risk Assessment

**RISK: MEDIUM-HIGH** - Wide-reaching refactor with ~40 query changes

**Mitigation**:
- Phase 2 (ORDER BY refactor) is the critical path - test thoroughly
- The started_at column already exists and is populated
- Succession tests are already testing deprecated functionality
- No external users - cannot break backwards compatibility

**Edge Case Considerations**:
- Jobs with NULL started_at: Add fallback to id ordering
- Historical data: started_at may be NULL for old records
- Consider: COALESCE(started_at, created_at) pattern

**Rollback Plan**:
- Git revert commit
- Re-run fresh install to restore column
- Model changes are easily reversible

## Dependencies

- **Depends on**: 0700d (succession removal - tests will not pass if succession tests still run)
- **Depends on**: 0700b (if executed first, this becomes simpler)
- **Blocks**: None

## Estimated Effort

- **Lines removed**: ~400-500 (model + dead tests + fixtures)
- **Lines modified**: ~200 (query refactors + API updates + frontend)
- **Files modified**: ~40-50
- **Files deleted**: 8 (succession test files)
- **Test updates**: ~100 test fixture changes
- **Time estimate**: 2-3 sessions (Phase 2 is time-intensive)

## Notes

- **Critical**: The ORDER BY refactor (Phase 2) must be done carefully - each query purpose should be verified
- **Alternative ordering**: Using started_at DESC is semantically correct because we want the most recently started execution
- **Frontend**: The Instance #N display can be completely removed - it is only relevant for succession
- **Consider**: Whether to keep SuccessionTimeline.vue or delete it entirely (may be dead component)
- **install.py**: Lines 1095 and 1121 set instance_number=1 for demo data - update or remove


## Appendix: Full File List

### Files to Modify (src/):
1. src/giljo_mcp/models/agent_identity.py
2. src/giljo_mcp/services/orchestration_service.py
3. src/giljo_mcp/services/message_service.py
4. src/giljo_mcp/services/agent_job_manager.py
5. src/giljo_mcp/services/project_service.py
6. src/giljo_mcp/monitoring/agent_health_monitor.py
7. src/giljo_mcp/thin_prompt_generator.py
8. src/giljo_mcp/job_monitoring.py
9. src/giljo_mcp/slash_commands/handover.py
10. src/giljo_mcp/repositories/agent_job_repository.py
11. src/giljo_mcp/tools/agent.py
12. src/giljo_mcp/tools/agent_coordination.py
13. src/giljo_mcp/tools/agent_job_status.py
14. src/giljo_mcp/tools/context.py
15. src/giljo_mcp/tools/orchestration.py
16. src/giljo_mcp/tools/tool_accessor.py
17. src/giljo_mcp/tools/write_360_memory.py

### Files to Modify (api/):
1. api/endpoints/prompts.py
2. api/endpoints/agent_jobs/table_view.py
3. api/endpoints/agent_jobs/executions.py
4. api/endpoints/agent_jobs/simple_handover.py
5. api/endpoints/agent_jobs/messages.py
6. api/endpoints/agent_jobs/lifecycle.py
7. api/endpoints/agent_jobs/status.py
8. api/endpoints/agent_jobs/models.py
9. api/endpoints/projects/status.py
10. api/endpoints/projects/models.py
11. api/schemas/prompt.py
12. api/websocket.py

### Files to Modify (frontend/):
1. frontend/src/components/orchestration/AgentTableView.vue
2. frontend/src/components/projects/LaunchSuccessorDialog.vue
3. frontend/src/components/projects/SuccessionTimeline.vue
4. frontend/src/components/projects/MessageStream.vue
5. frontend/src/components/projects/MessageInput.vue
6. frontend/src/components/projects/AgentExecutionModal.vue
7. frontend/src/components/projects/LaunchTab.vue
8. frontend/src/components/messages/MessageModal.vue
9. frontend/src/stores/agentJobsStore.js
10. frontend/src/stores/websocketEventRouter.js

### Files to Delete:
1. tests/integration/test_succession_workflow.py
2. tests/integration/test_succession_multi_tenant.py
3. tests/integration/test_succession_edge_cases.py
4. tests/integration/test_succession_database_integrity.py
5. tests/performance/test_succession_performance.py
6. tests/security/test_succession_security.py
7. tests/smoke/test_succession_smoke.py
8. tests/fixtures/succession_fixtures.py

### Migration Files (Update):
1. migrations/versions/baseline_v32_unified.py
2. install.py (demo data creation)
