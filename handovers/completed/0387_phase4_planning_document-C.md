# Plan: 0387 Phase 4 - JSONB Messages Normalization (Series Roadmap)

**Planning Date:** 2026-01-17
**Model:** 0420 Series (Legacy Agent Coordination Removal)
**Estimated Complexity:** 28-36 hours across 5 sub-handovers
**Risk Level:** HIGH - Affects core dashboard functionality

---

## Executive Summary

Remove `AgentExecution.messages` JSONB field to establish **single source of truth** (Message table only). Currently, every message is written to BOTH the Message table AND the JSONB field, causing:

1. **Data duplication** - Same data stored twice
2. **Sync risk** - Dual-write can get out of sync
3. **Future agent confusion** - New code might write to one or the other
4. **Not production-grade** - Open source contributors will see "hacky" architecture

**Solution**: Counter columns on `AgentExecution` + stop JSONB writes + frontend reads counters.

---

## Cascade Impact Summary (from Deep Research)

### Backend Impact
| Category | Count | Files |
|----------|-------|-------|
| WRITES | 21 operations | 3 production + 1 script |
| READS | 22 operations | 7 production + 1 script |
| JSONB Path Queries | 2 | table_view.py, filters.py |
| **Total Production Files** | **8** | |

### Frontend Impact
| Category | Count | Notes |
|----------|-------|-------|
| Files with dependencies | 12 | |
| HIGH impact | 4 | Core store, modal, composable |
| MEDIUM impact | 3 | Display components |
| LOW impact | 5 | Already have fallback |

**Key Finding**: Frontend already has fallback architecture checking for `messages_sent_count`, `messages_waiting_count`, `messages_read_count` fields.

### Test Impact
| Category | Count |
|----------|-------|
| Test files affected | 17 |
| Test functions affected | 53+ |
| Tests to DELETE | 5 |
| Tests to REWRITE | 12 |
| Tests to UPDATE (fixtures) | 36+ |

---

## Sub-Handover Series

| Handover | Scope | Hours | Prerequisite |
|----------|-------|-------|--------------|
| **0387e** | Add counter columns + migration + TDD | 6-8h | None |
| **0387f** | Backend: Stop JSONB writes, read from counters | 8-10h | 0387e complete |
| **0387g** | Frontend: Use counters, simplify WebSocket | 6-8h | 0387f complete |
| **0387h** | Test updates + cleanup | 6-8h | 0387g complete |
| **0387i** | Deprecate JSONB column + final verification | 2-4h | 0387h complete |

**Total: 28-36 hours across 5 handovers**

---

## Phase 0: Safety Net (FIRST ACTION)

**CRITICAL - Do this before ANY code changes:**

```bash
# 1. Create feature branch
git checkout -b 0387-jsonb-normalization

# 2. Database backup
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/pg_dump.exe -U postgres giljo_mcp > backup_pre_0387_phase4.sql

# 3. Document baseline
pytest tests/ --tb=no -q | grep -E "passed|failed"
# Record: Total test count, coverage percentage
```

---

## Handover 0387e: Add Counter Columns (6-8 hours)

### Scope
Add `messages_sent_count`, `messages_waiting_count`, `messages_read_count` columns to `AgentExecution` model with migration and atomic update methods.

### TDD Approach (RED -> GREEN -> REFACTOR)

**RED Phase - Write failing tests first:**
```python
# tests/unit/test_message_counters.py
async def test_increment_sent_count():
    """Counter increments atomically when message sent."""

async def test_decrement_waiting_increment_read():
    """Waiting decrements and read increments on acknowledgment."""

async def test_counters_survive_refresh():
    """Counters persist after page refresh (no JSONB derivation)."""
```

### Files to Modify
| File | Changes |
|------|---------|
| `src/giljo_mcp/models/agent_identity.py` | Add 3 counter columns |
| `src/giljo_mcp/services/agent_job_manager.py` | Add counter update methods |
| `src/giljo_mcp/repositories/agent_job_repository.py` | Add counter queries |
| `alembic/versions/xxxx_add_message_counters.py` | Migration script |

### Success Criteria
- [ ] 3 counter columns exist on AgentExecution
- [ ] Migration backfills counters from existing Message table data
- [ ] Atomic increment/decrement methods exist
- [ ] All new tests pass (GREEN)
- [ ] Existing tests still pass

---

## Handover 0387f: Backend Stop JSONB Writes (8-10 hours)

### Scope
Modify `MessageService` to stop writing to JSONB, update counters instead. Update all backend reads to use counters or Message table.

### Files to Modify (21 WRITE locations)

**message_service.py (14 locations)**:
- Remove `_persist_to_jsonb()` method calls
- Remove `_persist_single_message_to_jsonb()`
- Remove `_persist_broadcast_message_to_jsonb()`
- Remove `_update_jsonb_message_status()`
- Replace with counter increment calls

**agent_job_repository.py (1 location)**:
- Line 200-207: Remove `job.messages = messages` pattern

### Files to Modify (22 READ locations)

**project_service.py (line 235)**:
- Replace `execution.messages or []` with counter fields

**orchestration_service.py (lines 1799-1802)**:
- Replace JSONB read with counter fields

**orchestrator_succession.py (line 269)**:
- Replace JSONB read with Message table query

**table_view.py (lines 158, 199-205)**:
- Replace `jsonb_path_exists()` with Message table subquery
- Replace JSONB iteration with counter fields

**filters.py (line 125)**:
- Replace `jsonb_path_exists()` with Message table subquery

**statistics.py (lines 388-392)**:
- Replace JSONB iteration with counter fields

**agent_management.py (lines 124, 181)**:
- Replace `job.messages or []` with counter fields

### Success Criteria
- [ ] Zero JSONB writes in MessageService
- [ ] All reads use counters or Message table
- [ ] WebSocket events include counter values
- [ ] API responses include counter fields
- [ ] All tests pass (may need updates)

---

## Handover 0387g: Frontend Use Counters (6-8 hours)

### Scope
Update frontend to exclusively use counter fields, simplify WebSocket handlers, handle MessageAuditModal specially.

### Files to Modify (12 files)

**HIGH Priority:**

| File | Changes |
|------|---------|
| `stores/agentJobsStore.js` | Remove `deriveMessageCounters()`, use server counters |
| `stores/agentJobsStore.js` | Simplify WebSocket handlers (increment counters, don't track array) |
| `composables/useAgentData.js` | Update `getMessageCounts()` to use counter fields |
| `components/projects/MessageAuditModal.vue` | Fetch messages from API instead of JSONB |

**MEDIUM Priority:**

| File | Changes |
|------|---------|
| `components/AgentCard.vue` | Use counter fields for badges |
| `components/orchestration/OrchestratorCard.vue` | Use counter fields |
| `stores/orchestration.js` | Use counter fields |

**LOW Priority (already have fallback):**

| File | Changes |
|------|---------|
| `components/projects/JobsTab.vue` | Remove fallback to JSONB (counters always present) |

### MessageAuditModal Decision (REQUIRES YOUR INPUT)

The `MessageAuditModal.vue` displays actual message **content** (not just counts). Once we remove the JSONB array, this modal needs a data source:

**A** - Create new API endpoint `/api/jobs/{job_id}/messages` that queries Message table
*(Recommended - keeps feature, ~2 hours extra work)*

**B** - Deprecate MessageAuditModal entirely, users view messages elsewhere
*(Simpler - remove feature, save 2 hours)*

**C** - Keep JSONB for this modal only, remove everywhere else
*(Not recommended - defeats single source of truth goal)*

**D** - Other approach (please specify)

**Current Recommendation**: Option A

### Success Criteria
- [ ] All counters display correctly in UI
- [ ] WebSocket updates work (increment counters)
- [ ] MessageAuditModal shows messages (from API)
- [ ] No frontend code references `agent.messages` array
- [ ] All frontend tests pass

---

## Handover 0387h: Test Updates + Cleanup (6-8 hours)

### Tests to DELETE (5 tests)
```
tests/models/test_agent_execution.py::TestAgentExecutionMessages (2 tests)
tests/test_agent_communication_queue.py::test_jsonb_array_append
tests/test_agent_communication_queue.py::test_jsonb_message_update_acknowledgment
tests/test_agent_communication_queue.py::test_jsonb_query_filtering
```

### Tests to REWRITE (12 tests)
```
tests/integration/test_websocket_unified_platform.py (6 tests)
tests/integration/test_message_counter_persistence.py (3 tests)
tests/services/test_message_service_contract.py (3 tests)
```

### Fixtures to UPDATE (2 files)
```
tests/fixtures/base_fixtures.py - Remove messages field
tests/helpers/test_factories.py - Remove messages field
```

### Scripts to DEPRECATE
```
scripts/repair_jsonb_messages.py - No longer needed
scripts/README_repair_jsonb_messages.md - Archive
```

### Success Criteria
- [ ] All obsolete tests deleted
- [ ] All fixtures updated (no `messages=[]` in AgentExecution creation)
- [ ] All integration tests pass with new counter-based approach
- [ ] Test coverage >80% maintained
- [ ] No test references to `execution.messages` JSONB

---

## Handover 0387i: Deprecate JSONB Column (2-4 hours)

### Scope
Mark column as deprecated, verify everything works, prepare for future removal.

### Tasks
1. Add column comment: `DEPRECATED - Use counter columns instead`
2. Add deprecation warning in model docstring
3. Run full regression test suite
4. Manual E2E testing via dashboard
5. Create future migration stub for column removal

### DO NOT in this handover:
- [ ] DO NOT drop the column yet (keep for rollback safety)
- [ ] DO NOT remove from SQLAlchemy model yet

### Success Criteria
- [ ] Column marked deprecated in code comments
- [ ] All tests pass (100% green)
- [ ] Coverage >80%
- [ ] Manual testing complete
- [ ] Documentation updated (CLAUDE.md, docs/SERVICES.md)

---

## Rollback Plan

### Pre-Work Safety Net (from Phase 0)
- Branch: `0387-jsonb-normalization`
- Backup: `backup_pre_0387_phase4.sql`

### Rollback Decision Tree

```
Issue Detected?
    |
    +-> Minor bug (1-2 files)
    |   +-- Fix forward on branch
    |
    +-> Major breakage (tests failing, can't fix quickly)
    |   +-- git checkout master (code rollback only)
    |
    +-> Data corruption (unlikely)
        +-- pg_restore from backup
```

### Per-Handover Rollback
Each handover can be rolled back independently:
- 0387e: `git revert` migration, drop columns
- 0387f: Re-enable JSONB writes (code revert)
- 0387g: Frontend revert (npm rebuild)
- 0387h: Test revert (git checkout)
- 0387i: No permanent changes to revert

---

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Counter sync bugs | HIGH | MEDIUM | Atomic operations, comprehensive tests |
| Frontend display breaks | HIGH | LOW | Fallback architecture already exists |
| Performance regression | MEDIUM | LOW | Counter columns faster than JSONB derivation |
| Test coverage drops | MEDIUM | MEDIUM | Dedicated test update handover (0387h) |
| MessageAuditModal breaks | MEDIUM | MEDIUM | New API endpoint in 0387g |

---

## Benefits After Completion

1. **Single source of truth** - Message table is authoritative
2. **No sync bugs** - Counter columns updated atomically
3. **Cleaner code** - No dual-write pattern
4. **Better performance** - Counter reads faster than JSONB derivation
5. **Production-grade** - Open source ready architecture
6. **Future-proof** - New agents can't accidentally break messaging

---

## Verification Checklist (Final)

### Functional
- [ ] Message counters display correctly in dashboard
- [ ] WebSocket updates work in real-time
- [ ] MessageAuditModal shows message content
- [ ] Broadcast messages work correctly
- [ ] Orchestrator succession handover summary works

### Quality
- [ ] All tests pass (100% green)
- [ ] Coverage >80%
- [ ] No linting errors
- [ ] No TypeScript errors (frontend)

### Documentation
- [ ] CLAUDE.md updated (remove JSONB references)
- [ ] docs/SERVICES.md updated
- [ ] Handover 0387 marked complete

---

## Files Index (Complete)

### Backend Files to Modify (8 production)
1. `src/giljo_mcp/models/agent_identity.py`
2. `src/giljo_mcp/services/message_service.py`
3. `src/giljo_mcp/services/project_service.py`
4. `src/giljo_mcp/services/orchestration_service.py`
5. `src/giljo_mcp/repositories/agent_job_repository.py`
6. `src/giljo_mcp/orchestrator_succession.py`
7. `api/endpoints/agent_jobs/table_view.py`
8. `api/endpoints/agent_jobs/filters.py`

### API Files to Modify (2)
1. `api/endpoints/statistics.py`
2. `api/endpoints/agent_management.py`

### Frontend Files to Modify (12)
1. `frontend/src/stores/agentJobsStore.js`
2. `frontend/src/stores/agentJobs.js`
3. `frontend/src/stores/orchestration.js`
4. `frontend/src/composables/useAgentData.js`
5. `frontend/src/components/projects/JobsTab.vue`
6. `frontend/src/components/projects/MessageAuditModal.vue`
7. `frontend/src/components/AgentCard.vue`
8. `frontend/src/components/orchestration/OrchestratorCard.vue`
9. `frontend/src/components/StatusBoard/ActionIcons.vue`
10. Plus 3 test files

### Test Files to Modify (17)
- See Handover 0387h for complete list

### Scripts to Deprecate (2)
1. `scripts/repair_jsonb_messages.py`
2. `scripts/README_repair_jsonb_messages.md`
