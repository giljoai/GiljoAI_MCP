# Handover 0367: MCPAgentJob Cleanup Migration - Master Roadmap

**Date**: 2025-12-21
**Status**: Pending
**Priority**: HIGH
**Estimated Total Time**: 22-32 hours (across 4 sub-handovers)
**Dependencies**:
- Handover 0358 (AgentJob/AgentExecution dual-model architecture) - COMPLETE
- Field mapping reference (0358_model_mapping_reference.md) - COMPLETE

---

## Executive Summary

GiljoAI MCP currently operates with a dual-model architecture for agent job management:
- **New System**: `AgentJob` (work order) + `AgentExecution` (executor/instance)
- **Legacy System**: `MCPAgentJob` (deprecated single-model approach)

**Current State**: 70% migration complete
- ✅ READ paths migrated (queries use new models)
- ⚠️ WRITE paths incomplete (creates/updates use both models)
- ⚠️ Bridge/fallback code maintains dual-system compatibility
- ⚠️ 367 production file references + 1,291 test file references

**Goal**: Complete migration to new dual-model architecture, remove all MCPAgentJob dependencies from production code, mark legacy model for deprecation.

---

## Why This Cleanup Is Critical

### 1. Technical Debt Accumulation
- **Dual-system maintenance burden**: Every agent job operation must consider both models
- **Data inconsistency risk**: Two sources of truth for the same information
- **Code complexity**: Bridge code, fallback logic, and conditional paths obscure intent
- **Developer confusion**: New developers must understand both systems

### 2. Performance Impact
- **Redundant database writes**: Creating both MCPAgentJob and AgentJob records
- **Query inefficiency**: Fallback queries check multiple tables
- **Memory overhead**: Two sets of models loaded in ORM

### 3. Feature Development Blocker
- **New features delayed**: Must maintain backward compatibility
- **Testing overhead**: Must test both code paths
- **Refactoring paralysis**: Fear of breaking legacy integrations

### 4. Semantic Clarity
The new dual-model architecture provides superior semantics:
- `AgentJob` = work order (what needs to be done, reusable across retries)
- `AgentExecution` = executor instance (who is doing it, one per attempt)
- `MCPAgentJob` conflates these concepts into a single entity

---

## Phase Overview

### Phase A: Service Layer Cleanup (0367a)
**Target**: `src/giljo_mcp/services/`
**Estimated Time**: 8-12 hours
**Files**: 8 critical service files (317 total refs)

**Key Actions**:
- Remove bridge code in `orchestration_service.py` (lines 1372-1398, 1815-1879)
- Remove `Job = MCPAgentJob` alias in `agent_job_manager.py`
- Replace legacy queries in `project_service.py` (44 refs)
- Migrate `message_service.py` job lookups (29 refs)

**Success Criteria**: All service layer code uses `AgentJob` + `AgentExecution` exclusively.

---

### Phase B: API Endpoint Migration (0367b)
**Target**: `api/endpoints/`
**Estimated Time**: 6-8 hours
**Files**: 7 endpoint modules (103 total refs)

**Key Actions**:
- Update `prompts.py` thin client prompt generation (28 refs)
- Migrate `statistics.py` aggregation queries (21 refs)
- Clean up `agent_jobs/` endpoint modules (filters, table_view, succession, operations)
- Verify response schema compatibility (JobResponse.id already migrated to str)

**Success Criteria**: All API endpoints return AgentJob-based responses; no MCPAgentJob queries.

---

### Phase C: Tools & Monitoring Cleanup (0367c)
**Target**: `src/giljo_mcp/tools/`, `src/giljo_mcp/orchestration/`
**Estimated Time**: 6-8 hours
**Files**: 8 files (102 total refs)

**Key Actions**:
- Update `agent_health_monitor.py` status checks (23 refs)
- Migrate `orchestrator.py` agent spawning logic (21 refs)
- Clean up `staging_rollback.py` rollback operations (18 refs)
- Remove fallback logic in `thin_prompt_generator.py` (17 refs)
- Update MCP tools (`orchestration_tools.py`, `agent_coordination.py`)

**Success Criteria**: No MCPAgentJob references in orchestration or monitoring code.

---

### Phase D: Validation & Deprecation (0367d)
**Target**: Model deprecation, test suite validation
**Estimated Time**: 2-4 hours

**Key Actions**:
- Run full test suite to verify no regressions
- Search codebase for remaining MCPAgentJob references
- Mark `MCPAgentJob` model with deprecation notice
- Document table deprecation strategy (keep table for historical data)
- Create plan for test file migration (deferred to future handover)

**Success Criteria**:
- Zero MCPAgentJob references in production code
- All tests passing
- Deprecation notice added to model
- Migration plan documented

---

## Success Criteria (Overall)

### Code Quality
- [ ] Zero `MCPAgentJob` imports in production code (`src/`, `api/`)
- [ ] Zero `mcp_agent_jobs` table queries in production code
- [ ] All bridge/fallback code removed
- [ ] All type aliases (`Job = MCPAgentJob`) removed

### Functional Validation
- [ ] All API endpoints return correct data using new models
- [ ] Agent job creation uses only `AgentJob` + `AgentExecution`
- [ ] Agent job queries use only `agent_jobs` + `agent_executions` tables
- [ ] WebSocket events emit correct agent_id (not legacy job_id)

### Testing
- [ ] Pytest suite passes (>80% coverage maintained)
- [ ] Integration tests validate agent lifecycle
- [ ] No regressions in agent job management workflows

### Documentation
- [ ] Model deprecation notice added to `MCPAgentJob`
- [ ] Migration completion documented in devlog
- [ ] Test migration plan documented for future handover

---

## Risk Assessment

### High Risk
**Data Loss**: Incorrect query migrations could lose historical job data
- **Mitigation**: Review all queries against field mapping reference (0358)
- **Mitigation**: Test with production-like data before deployment

**Broken Workflows**: Agent spawning/succession could fail if model relationships break
- **Mitigation**: Integration tests for full agent lifecycle
- **Mitigation**: Rollback plan for each phase (see individual handovers)

### Medium Risk
**Performance Regression**: New queries might be slower than legacy queries
- **Mitigation**: Add database indexes if needed (agent_jobs.product_id, agent_executions.agent_id)
- **Mitigation**: Monitor query performance during testing

**Test Suite Failures**: Tests might rely on MCPAgentJob fixtures
- **Mitigation**: Fix production code first, defer test migration to 0367d
- **Mitigation**: Maintain backward compatibility in fixtures temporarily

### Low Risk
**Frontend Breakage**: UI already uses JobResponse.id (str) from Handover 0358
- **Mitigation**: Verify WebSocket events emit correct IDs

---

## Timeline Estimate

| Phase | Handover | Estimated Time | Cumulative |
|-------|----------|----------------|------------|
| A | 0367a | 8-12 hours | 8-12 hours |
| B | 0367b | 6-8 hours | 14-20 hours |
| C | 0367c | 6-8 hours | 20-28 hours |
| D | 0367d | 2-4 hours | 22-32 hours |

**Total**: 22-32 hours (3-4 full working days)

**Recommended Execution**: Sequential (A → B → C → D) to minimize integration risk.

---

## Dependencies & Prerequisites

### Required Before Starting
- ✅ Handover 0358 complete (dual-model architecture implemented)
- ✅ Field mapping reference available (0358_model_mapping_reference.md)
- ✅ Test environment with production-like data
- ✅ Database backup before migration

### External Dependencies
- None (internal refactoring only)

---

## Rollback Strategy

### Per-Phase Rollback
Each handover (0367a-d) includes a specific rollback plan. General approach:
1. Revert Git commits for the phase
2. Restore database from pre-phase backup
3. Restart server to clear ORM cache
4. Verify legacy code path still functional

### Emergency Rollback
If critical issues arise mid-migration:
1. Revert all commits since 0367a start
2. Re-enable bridge code in orchestration_service.py
3. Restore MCPAgentJob queries in service layer
4. Document issues for future attempt

**Recovery Time Objective**: <15 minutes (Git revert + server restart)

---

## Post-Migration Cleanup (Future Work)

### Deferred to Future Handovers
- **Test file migration**: 1,291 refs across 169 files (scoped separately)
- **Table removal**: Keep `mcp_agent_jobs` table for 2 release cycles (historical data)
- **Model removal**: Remove `MCPAgentJob` class after 2 release cycles (v3.4+)

### Monitoring Plan
- Monitor error logs for 1 week post-deployment
- Track agent job creation/query performance metrics
- Watch for user-reported issues in agent workflows

---

## Notes

### Why Not Big Bang Migration?
- **Risk**: 367 production refs + 1,291 test refs too large for single handover
- **Testing**: Incremental validation easier than full regression suite
- **Rollback**: Smaller blast radius per phase

### Why Service Layer First (0367a)?
- **Foundation**: Services are the source of truth for data operations
- **Cascade**: API endpoints (0367b) depend on service layer being clean
- **Testing**: Service tests validate correctness before exposing to API

### Why Tests Last (0367d)?
- **Production First**: User-facing code takes priority
- **Scope**: 1,291 test refs warrant dedicated handover series
- **Compatibility**: Fixtures can maintain backward compatibility temporarily

---

## Related Documentation

- [0358_model_mapping_reference.md](Reference_docs/0358_model_mapping_reference.md) - Field mapping AgentJob ↔ MCPAgentJob
- [docs/SERVICES.md](../docs/SERVICES.md) - Service layer patterns
- [docs/ORCHESTRATOR.md](../docs/ORCHESTRATOR.md) - Agent lifecycle documentation

---

**Next Steps**: Execute handovers in sequence: 0367a → 0367b → 0367c → 0367d
