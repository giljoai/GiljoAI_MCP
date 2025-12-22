# Handover 0367d: MCPAgentJob Validation & Deprecation

**Date**: 2025-12-21
**Status**: Pending
**Priority**: HIGH
**Estimated Time**: 2-4 hours
**Dependencies**:
- Handover 0367a (Service Layer Cleanup) - MUST BE COMPLETE
- Handover 0367b (API Endpoint Migration) - MUST BE COMPLETE
- Handover 0367c (Tools/Monitoring Cleanup) - MUST BE COMPLETE

---

## Overview

Final validation phase for MCPAgentJob cleanup migration. Verify zero production code references, mark model for deprecation, run comprehensive test suite, and plan future table removal.

**Current State**:
- 0367a, 0367b, 0367c completed (service layer, API, tools all migrated)
- MCPAgentJob model still exists (not yet deprecated)
- mcp_agent_jobs table still contains historical data
- Test files (1,291 refs) not yet migrated

**Target State**:
- Zero MCPAgentJob references in production code (src/, api/)
- MCPAgentJob model marked with deprecation notice
- All tests passing (>80% coverage maintained)
- Table deprecation strategy documented
- Test migration plan documented for future handover

---

## Implementation Steps

### Step 1: Comprehensive Code Search (30 minutes)

**Objective**: Verify zero MCPAgentJob references in production code.

**Search Commands**:
```bash
# Search production code (should return 0 results)
grep -r "MCPAgentJob" src/ api/ --exclude-dir=__pycache__

# Search imports (should return 0 results)
grep -r "from.*models.*import.*MCPAgentJob" src/ api/
grep -r "import.*MCPAgentJob" src/ api/

# Search table references (should return 0 results)
grep -r "mcp_agent_jobs" src/ api/ --exclude-dir=__pycache__
```

**Expected Results**:
- **Production Code**: 0 matches in src/, api/
- **Test Code**: 1,291 matches in tests/ (deferred to future handover)
- **Model Definition**: 1 match in src/giljo_mcp/models.py (the model itself)

**Actions**:
1. Run each grep command and record results
2. If any production code references found, document file/line
3. Determine if reference is necessary (comment, docstring) or code (must fix)
4. Fix any remaining code references before proceeding
5. Document search results in handover completion notes

**Success Criteria**:
- [ ] Zero MCPAgentJob imports in src/, api/
- [ ] Zero mcp_agent_jobs table queries in src/, api/
- [ ] Only references are: model definition + test files

---

### Step 2: Mark MCPAgentJob Model for Deprecation (30 minutes)

**Objective**: Add deprecation notice to model class, document removal timeline.

**Current Model** (src/giljo_mcp/models.py):
```python
class MCPAgentJob(Base):
    __tablename__ = "mcp_agent_jobs"

    job_id = Column(Integer, primary_key=True, autoincrement=True)
    agent_template_id = Column(Integer, nullable=True)
    mission_text = Column(Text, nullable=True)
    status = Column(String(50), nullable=True)
    ...
```

**Deprecated Model** (add deprecation notice):
```python
class MCPAgentJob(Base):
    """
    DEPRECATED: This model is deprecated as of v3.2 (2025-12-21).
    Use AgentJob + AgentExecution dual-model architecture instead.

    Migration Timeline:
    - v3.2: Marked deprecated, production code migrated (Handover 0367a-c)
    - v3.3: Test code migrated (future handover)
    - v3.4: Model removed, table archived (future handover)

    Historical Context:
    MCPAgentJob conflated two concepts into a single entity:
    1. Work Order (what needs to be done) → now AgentJob
    2. Executor Instance (who is doing it) → now AgentExecution

    The dual-model architecture provides:
    - Better semantics (clear separation of concerns)
    - Retry support (reuse work order across attempts)
    - Lineage tracking (spawned_by/succeeded_by use work order IDs)

    See: handovers/0367_mcpagentjob_cleanup_roadmap.md
    See: handovers/Reference_docs/0358_model_mapping_reference.md
    """
    __tablename__ = "mcp_agent_jobs"

    job_id = Column(Integer, primary_key=True, autoincrement=True)
    agent_template_id = Column(Integer, nullable=True)
    mission_text = Column(Text, nullable=True)
    status = Column(String(50), nullable=True)
    ...
```

**Actions**:
1. Add deprecation docstring to MCPAgentJob class
2. Include migration timeline (v3.2 → v3.3 → v3.4)
3. Reference handover documentation
4. Document semantic rationale for dual-model architecture
5. Commit change with descriptive message

**Success Criteria**:
- [ ] Deprecation notice added to MCPAgentJob model
- [ ] Timeline documented (v3.2 → v3.4)
- [ ] Handover references included
- [ ] Commit message explains deprecation

---

### Step 3: Run Full Test Suite (1-2 hours)

**Objective**: Validate no regressions from 0367a-c migrations.

**Test Execution Plan**:

1. **Service Layer Tests** (from 0367a):
   ```bash
   pytest tests/services/test_orchestration_service.py -v
   pytest tests/services/test_agent_job_manager.py -v
   pytest tests/services/test_project_service.py -v
   pytest tests/services/test_message_service.py -v
   ```

2. **API Endpoint Tests** (from 0367b):
   ```bash
   pytest tests/api/test_prompts.py -v
   pytest tests/api/test_statistics.py -v
   pytest tests/api/agent_jobs/ -v
   pytest tests/api/projects/test_status.py -v
   ```

3. **Tools/Orchestration Tests** (from 0367c):
   ```bash
   pytest tests/orchestration/ -v
   pytest tests/tools/ -v
   ```

4. **Full Suite with Coverage**:
   ```bash
   pytest tests/ --cov=src/giljo_mcp --cov=api --cov-report=html --cov-report=term
   ```

**Expected Results**:
- **Test Pass Rate**: 100% (all tests pass)
- **Coverage**: >80% maintained (no regression from pre-migration)
- **Failed Tests**: 0 in production code paths

**Known Acceptable Failures**:
- Test files using MCPAgentJob fixtures (deferred to future handover)
- Tests explicitly testing legacy MCPAgentJob behavior (can be skipped)

**Actions**:
1. Run each test command and record results
2. If failures occur, categorize by root cause:
   - Production code bug (must fix immediately)
   - Test fixture using MCPAgentJob (defer to future handover)
   - Unrelated pre-existing failure (document, don't block)
3. Fix production code bugs before proceeding
4. Document test results in handover completion notes

**Success Criteria**:
- [ ] All service layer tests pass
- [ ] All API endpoint tests pass
- [ ] All orchestration/tools tests pass
- [ ] Coverage >80% maintained
- [ ] Zero production code test failures

---

### Step 4: Integration Test Validation (30-45 minutes)

**Objective**: Validate end-to-end workflows using new models.

**Test Scenarios**:

1. **Project Launch → Agent Spawn**:
   - Create project via API
   - Launch project (spawns orchestrator)
   - Verify AgentJob + AgentExecution created (no MCPAgentJob)
   - Check spawned_by is null (orchestrator is root)

2. **Agent Spawning Chain**:
   - Orchestrator spawns child agent
   - Verify child AgentExecution.spawned_by = orchestrator agent_id (UUID)
   - Child spawns grandchild
   - Verify grandchild.spawned_by = child agent_id (UUID)

3. **Orchestrator Succession**:
   - Trigger orchestrator handover (90% context)
   - Verify new AgentJob + AgentExecution created
   - Verify old AgentExecution.succeeded_by = new agent_id (UUID)
   - Verify new AgentExecution.spawned_by = old agent_id (UUID)

4. **Message Routing**:
   - Send message to agent via agent_id (UUID)
   - Verify message delivered to correct agent
   - Verify no MCPAgentJob lookups in logs

5. **Health Monitoring**:
   - Check agent health via agent_id (UUID)
   - Verify status from AgentExecution
   - Verify context usage from AgentExecution

6. **Staging Rollback**:
   - Trigger staging failure
   - Verify rollback soft-deletes AgentExecution (status = "cancelled")
   - Verify AgentJob preserved (work order history)

**Actions**:
1. Run each integration test scenario
2. Verify expected behavior using new models
3. Check database for MCPAgentJob records (should only be historical)
4. Verify WebSocket events emit agent_id (UUID), not job_id (int)
5. Document any unexpected behavior

**Success Criteria**:
- [ ] Project launch creates AgentJob + AgentExecution
- [ ] Spawning chain uses agent_id (UUID) for spawned_by
- [ ] Succession uses agent_id (UUID) for succeeded_by
- [ ] Message routing works with agent_id (UUID)
- [ ] Health monitoring queries AgentExecution
- [ ] Rollback preserves AgentJob, cancels AgentExecution

---

### Step 5: Document Table Deprecation Strategy (30 minutes)

**Objective**: Plan for eventual mcp_agent_jobs table removal.

**Deprecation Timeline**:

| Version | Timeline | Action | Rationale |
|---------|----------|--------|-----------|
| **v3.2** | 2025-12-21 | Production code migrated (0367a-c) | Remove active dependencies |
| **v3.3** | Q1 2026 | Test code migrated (future handover) | Remove test dependencies |
| **v3.4** | Q2 2026 | Table archived, model removed | Safe to remove after 2 releases |

**Table Archival Strategy**:

1. **Archive Historical Data** (before removal):
   ```sql
   -- Create archive table (one-time)
   CREATE TABLE mcp_agent_jobs_archive AS
   SELECT * FROM mcp_agent_jobs;

   -- Add archive metadata
   ALTER TABLE mcp_agent_jobs_archive
   ADD COLUMN archived_at TIMESTAMP DEFAULT NOW();
   ```

2. **Verify No Dependencies**:
   - Grep codebase for mcp_agent_jobs references (should be 0)
   - Check foreign key constraints (should be none)
   - Verify no production queries (confirmed in Step 1)

3. **Drop Table** (v3.4+):
   ```sql
   -- Final safety check
   SELECT COUNT(*) FROM mcp_agent_jobs;  -- Should be > 0 (historical data)

   -- Drop table
   DROP TABLE mcp_agent_jobs;
   ```

**Migration Script** (create for v3.4):
- Script location: `migrations/archive_mcp_agent_jobs.sql`
- Include rollback: `CREATE TABLE mcp_agent_jobs AS SELECT * FROM mcp_agent_jobs_archive;`

**Actions**:
1. Document table deprecation timeline
2. Create archive strategy documentation
3. Add migration script template for v3.4
4. Update ROADMAP.md with deprecation milestones
5. Commit documentation changes

**Success Criteria**:
- [ ] Deprecation timeline documented (v3.2 → v3.4)
- [ ] Archive strategy defined (SQL scripts)
- [ ] Migration script template created
- [ ] ROADMAP.md updated with milestones

---

### Step 6: Plan Test File Migration (30 minutes)

**Objective**: Document scope and strategy for future test migration handover.

**Test Migration Scope**:
- **Files**: 169 test files
- **References**: 1,291 MCPAgentJob references
- **Categories**:
  - Fixtures using MCPAgentJob (highest priority)
  - Unit tests querying mcp_agent_jobs table
  - Integration tests creating MCPAgentJob records
  - Mock objects using MCPAgentJob attributes

**Migration Strategy**:

1. **Phase 1: Fixture Migration** (highest impact):
   - Replace MCPAgentJob fixtures with AgentJob + AgentExecution
   - Update factory functions to create dual models
   - Preserve test data relationships

2. **Phase 2: Unit Test Migration**:
   - Update assertions to use AgentJob + AgentExecution
   - Replace job_id (int) with agent_id (UUID)
   - Update field mappings per 0358 reference

3. **Phase 3: Integration Test Migration**:
   - Replace end-to-end flows using MCPAgentJob
   - Verify WebSocket events emit agent_id (UUID)
   - Test dual-model creation/queries

**Estimated Effort**:
- Fixtures: 4-6 hours (20-30 fixture files)
- Unit Tests: 12-16 hours (100+ test files)
- Integration Tests: 6-8 hours (40+ test files)
- **Total**: 22-30 hours (3-4 full working days)

**Handover Scope** (future):
- Create: `0368_test_file_migration_roadmap.md`
- Phases: `0368a_fixture_migration.md`, `0368b_unit_test_migration.md`, `0368c_integration_test_migration.md`

**Actions**:
1. Document test migration scope (files, refs, categories)
2. Define migration strategy (fixtures → unit → integration)
3. Estimate effort per phase
4. Create placeholder handover outline (0368 series)
5. Add to ROADMAP.md as future work

**Success Criteria**:
- [ ] Test migration scope documented (169 files, 1,291 refs)
- [ ] Migration strategy defined (3 phases)
- [ ] Effort estimate documented (22-30 hours)
- [ ] Future handover placeholder created (0368 series)
- [ ] ROADMAP.md updated with test migration milestone

---

## Success Criteria

### Code Quality
- [ ] Zero MCPAgentJob imports in src/, api/ (verified via grep)
- [ ] Zero mcp_agent_jobs queries in production code
- [ ] Deprecation notice added to MCPAgentJob model
- [ ] All code follows new dual-model architecture

### Functional Validation
- [ ] All production tests pass (>80% coverage)
- [ ] Integration tests validate end-to-end workflows
- [ ] No regressions in agent lifecycle operations
- [ ] WebSocket events emit agent_id (UUID) correctly

### Documentation
- [ ] Table deprecation strategy documented (v3.2 → v3.4)
- [ ] Test migration plan documented (0368 series)
- [ ] Migration completion logged in devlog
- [ ] ROADMAP.md updated with deprecation milestones

### Database
- [ ] mcp_agent_jobs table contains only historical data
- [ ] No new records inserted into mcp_agent_jobs
- [ ] Archive strategy defined for v3.4 removal
- [ ] Migration script template created

---

## Rollback Plan

### If Critical Issues Found in Validation
1. **Stop Immediately** - Do not proceed to deprecation
2. **Document Issue** - Record specific failure (test, workflow, etc.)
3. **Assess Severity**:
   - **Critical**: Revert 0367a-c, restore MCPAgentJob usage
   - **High**: Fix issue in current handover, re-run validation
   - **Low**: Document as known issue, proceed with deprecation
4. **Re-validate** - After fix, re-run full test suite

### If Issues Arise Post-Deprecation
1. **Assess Impact** - Production data corruption? User-facing bug?
2. **Emergency Rollback** (if critical):
   - Revert 0367a-c commits
   - Restore bridge code in orchestration_service.py
   - Restart server
3. **Surgical Fix** (if non-critical):
   - Fix specific bug without reverting handovers
   - Deploy patch
4. **Document Incident** - Add to handover notes

**Recovery Time**:
- Emergency Rollback: <15 minutes
- Surgical Fix: 1-2 hours

---

## Testing Strategy

### Validation Testing
- Run full pytest suite (src/, api/)
- Run integration tests (end-to-end workflows)
- Manual smoke tests (UI, MCP tools)

### Regression Testing
- Compare coverage reports (pre vs post migration)
- Verify no performance regression (query times)
- Check error logs for new exceptions

### Database Validation
- Query mcp_agent_jobs (should be historical only)
- Query agent_jobs + agent_executions (should be active)
- Verify no orphaned records (foreign key integrity)

---

## Deliverables

### Code Changes
1. **Deprecation Notice** - MCPAgentJob model docstring updated
2. **Migration Script Template** - `migrations/archive_mcp_agent_jobs.sql`

### Documentation
1. **Table Deprecation Strategy** - Added to docs/architecture/
2. **Test Migration Plan** - Placeholder handovers/0368_*.md
3. **Devlog Entry** - docs/devlogs/2025-12-21_mcpagentjob_cleanup_complete.md
4. **ROADMAP Update** - Deprecation milestones added

### Validation Report
1. **Code Search Results** - Grep output (0 production refs)
2. **Test Results** - Pytest output (>80% coverage, all passing)
3. **Integration Test Results** - End-to-end workflow validation
4. **Database Audit** - Historical data count, active data migration verified

---

## Migration Completion Checklist

### Pre-Validation
- [ ] Handover 0367a complete (service layer)
- [ ] Handover 0367b complete (API endpoints)
- [ ] Handover 0367c complete (tools/orchestration)

### Validation Phase
- [ ] Code search confirms 0 production references
- [ ] Full test suite passes (>80% coverage)
- [ ] Integration tests validate end-to-end workflows
- [ ] Database audit confirms migration success

### Deprecation Phase
- [ ] MCPAgentJob model marked deprecated
- [ ] Table deprecation strategy documented
- [ ] Test migration plan documented
- [ ] ROADMAP.md updated

### Post-Migration
- [ ] Devlog entry created
- [ ] Migration completion announced to team
- [ ] Monitor error logs for 1 week
- [ ] Schedule test migration (0368 series)

---

## Notes

### Why Not Remove Model Immediately?
- **Historical Data**: mcp_agent_jobs table contains records from pre-migration
- **Test Compatibility**: 1,291 test refs still use MCPAgentJob
- **Phased Approach**: Deprecate → migrate tests → remove (2 release cycles)
- **Rollback Safety**: Keeping model allows emergency rollback if needed

### Why Not Migrate Tests in This Handover?
- **Scope**: 1,291 refs across 169 files too large for single handover
- **Priority**: Production code takes precedence over test code
- **Effort**: Test migration estimated at 22-30 hours (separate handover series)
- **Risk**: Test migration failures don't block production deployment

### Timeline Rationale (v3.2 → v3.4)
- **v3.2** (now): Production code migrated, users benefit immediately
- **v3.3** (Q1 2026): Test code migrated, full codebase clean
- **v3.4** (Q2 2026): Table removed, tech debt fully eliminated
- **2 Releases**: Industry standard for deprecation cycles

### Migration Success Metrics
- **Code Quality**: 0 production refs, 100% dual-model usage
- **Stability**: No regressions, >80% coverage maintained
- **Performance**: No degradation in query/creation times
- **User Impact**: Zero (migration is internal refactoring)

---

## Related Documentation

- [0367_mcpagentjob_cleanup_roadmap.md](0367_mcpagentjob_cleanup_roadmap.md) - Master roadmap
- [0367a_service_layer_cleanup.md](0367a_service_layer_cleanup.md) - Service layer migration
- [0367b_api_endpoint_migration.md](0367b_api_endpoint_migration.md) - API endpoint migration
- [0367c_tools_monitoring_cleanup.md](0367c_tools_monitoring_cleanup.md) - Tools/orchestration migration
- [0358_model_mapping_reference.md](Reference_docs/0358_model_mapping_reference.md) - Field mapping reference

---

## Final Sign-Off

Upon completion of this handover, the MCPAgentJob cleanup migration (0367a-d) is **COMPLETE**.

**Production Code Status**: ✅ Migrated (0 MCPAgentJob references)
**Model Status**: ⚠️ Deprecated (marked for removal in v3.4)
**Table Status**: 📦 Historical (no new inserts, archive plan ready)
**Test Code Status**: ⏳ Pending (deferred to 0368 series)

**Next Steps**:
1. Monitor production for 1 week (watch error logs)
2. Schedule test migration (Handover 0368 series)
3. Plan table archival for v3.4 release

---

**Migration Complete**: 2025-12-21 (pending execution)
