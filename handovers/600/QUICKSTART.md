# Project 600: Quick Start Guide for Vibe Coding

**For**: Developers executing Project 600 day-by-day
**Total Duration**: 2-3 weeks (13-18 days)
**Handovers**: 32 (0600-0631)
**Approach**: Mix of CLI (local, sequential) and CCW (cloud, parallel)

---

## Overview

Project 600 restores and validates the complete GiljoAI MCP system after the 0120-0130 refactoring. We're proving everything works - fresh install, all services, all endpoints, all workflows. **Zero compromises**.

**Key Phases**:
1. **Phase 0** (Days 1-2): Foundation - fix migration order, establish test baseline
2. **Phase 1** (Days 3-5): Validate 6 services (parallel CCW execution)
3. **Phase 2** (Days 6-7): Validate 84+ API endpoints (parallel CCW execution)
4. **Phase 3** (Days 8-10): Validate 8 critical workflows (sequential CLI execution)
5. **Phase 4** (Days 11-12): Implement self-healing (decorators + baseline schema)
6. **Phase 5** (Days 13-15): Comprehensive testing (unit + integration + E2E)
7. **Phase 6** (Days 16-18): Documentation (parallel CCW execution)

---

## Week 1: Foundation + Services (Days 1-5)

### Day 1 - Morning: Handover 0600 (CLI - 4 hours)
**Agent**: deep-researcher
**Goal**: Comprehensive system audit (catalog everything)

**Prompt**:
```
Read handovers/600/0600_comprehensive_system_audit.md and handovers/600/AGENT_REFERENCE_GUIDE.md.

Execute Handover 0600: Comprehensive System Audit

Tasks:
1. Scan all 31 database tables (verify schema matches models)
2. Analyze 44 migration files (identify dependency chain)
3. Catalog 84+ API endpoints (categorize by function)
4. Audit 456 test files (estimate effort to fix)
5. Document 6 services (identify test gaps)
6. List 8 critical workflows for E2E testing

Create: handovers/600/0600_audit_report.md with complete system inventory
```

**Expected Output**:
- `handovers/600/0600_audit_report.md` (comprehensive inventory)
- Migration dependency graph
- Test categorization JSON
- Coverage baseline metrics

---

### Day 1 - Afternoon: Handover 0601 (CLI - 6 hours)
**Agent**: installation-flow-agent
**Goal**: Fix migration order, test fresh install

**Prompt**:
```
Read handovers/600/0601_fix_migration_order_fresh_install.md and handovers/600/AGENT_REFERENCE_GUIDE.md.

Execute Handover 0601: Fix Migration Order & Fresh Install

Tasks:
1. Move 20251114_create_missing_base_tables.py to position 1 in migration chain
2. Update all downstream migration dependencies
3. Test fresh install on clean PostgreSQL database
4. Validate pg_trgm extension creation
5. Verify all 31 tables created in correct order
6. Benchmark install time (<5 min target)

Create: handovers/600/0601_fresh_install_test.md with results
```

**Expected Output**:
- Fixed migration (reordered to position 1)
- Fresh install passes (<5 min)
- All 31 tables created
- Commit: "fix: Reorder migration chain for fresh install success"

---

### Day 2: Handover 0602 (CLI - 6 hours)
**Agent**: tdd-implementor
**Goal**: Establish test baseline (run all tests, document failures)

**Prompt**:
```
Read handovers/600/0602_establish_test_baseline.md and handovers/600/AGENT_REFERENCE_GUIDE.md.

Execute Handover 0602: Establish Test Baseline

Tasks:
1. Run full test suite: pytest tests/ -v --tb=short
2. Categorize failures (Agent model, service changes, integration broken)
3. Run coverage: pytest --cov=src/giljo_mcp --cov-report=html
4. Document baseline metrics (pass rate, coverage %)
5. Create fix plan for 50+ most critical test failures

Create: handovers/600/0602_test_baseline.md with metrics and fix plan
```

**Expected Output**:
- Test baseline report (X passing, Y failing, Z% coverage)
- Failure categorization
- Fix plan for critical tests
- Commit: "test: Establish baseline metrics and failure analysis"

---

### Days 3-5: Handovers 0603-0608 (CCW - 6 Parallel Branches)
**Agents**: tdd-implementor (6 instances)
**Goal**: Validate all 6 services (80%+ coverage each)

**Execute in Claude Code Web (CCW) - Create 6 branches in parallel**:

#### Branch 1: 0603-product-service-tests
**Prompt**:
```
You are the tdd-implementor agent working on Handover 0603: ProductService Validation.

CONTEXT: Read handovers/600/AGENT_REFERENCE_GUIDE.md for universal project context.

TASK:
1. Read src/giljo_mcp/services/product_service.py (analyze all methods)
2. Create comprehensive unit tests: tests/unit/test_product_service.py (80%+ coverage)
3. Create integration tests: tests/integration/test_product_service.py
4. Test multi-tenant isolation (product leakage prevention)
5. Run: pytest tests/unit/test_product_service.py -v --cov=src/giljo_mcp/services/product_service.py --cov-report=term-missing

DELIVERABLES:
- Unit tests with 80%+ coverage
- Integration tests (multi-tenant isolation)
- Test run output in PR description
- Coverage report snippet

SUCCESS: All tests pass, 80%+ coverage, multi-tenant isolation verified
```

**Create PR when done, merge locally after review**

#### Branch 2: 0604-project-service-tests
**Prompt**: [Same pattern as 0603, replace ProductService → ProjectService]

#### Branch 3: 0605-task-service-tests
**Prompt**: [Same pattern as 0603, replace ProductService → TaskService]

#### Branch 4: 0606-message-service-tests
**Prompt**: [Same pattern as 0603, replace ProductService → MessageService]

#### Branch 5: 0607-context-service-tests
**Prompt**: [Same pattern as 0603, replace ProductService → ContextService]

#### Branch 6: 0608-orchestration-service-tests
**Prompt**: [Same pattern as 0603, replace ProductService → OrchestrationService]

**CLI Merge Protocol (After Each CCW Branch)**:
```bash
# Locally merge each completed CCW branch
git fetch origin
git merge origin/0603-product-service-tests

# Run tests locally
pytest tests/unit/test_product_service.py tests/integration/test_product_service.py -v

# Verify coverage
pytest --cov=src/giljo_mcp/services/product_service.py

# If pass: Keep merge. If fail: Investigate and fix.

# Repeat for all 6 branches
```

**After All 6 Merged**:
```bash
# Run full service test suite
pytest tests/unit/test_*_service.py tests/integration/test_*_service.py -v --cov=src/giljo_mcp/services
```

---

## Week 2: APIs + Workflows + Self-Healing (Days 6-12)

### Days 6-7: Handovers 0609-0618 (CCW - 10 Parallel Branches)
**Agents**: api-tester (10 instances)
**Goal**: Validate all 84+ API endpoints

**Execute in CCW - Create 10 branches in parallel**:

#### Branch 1: 0609-products-api-tests
**Prompt**:
```
You are the api-tester agent working on Handover 0609: Products API Validation.

CONTEXT: Read handovers/600/AGENT_REFERENCE_GUIDE.md for universal project context.

TASK:
1. Read api/endpoints/products.py (12 product endpoints)
2. Create API integration tests: tests/api/test_products_api.py
3. Test all 12 endpoints (list, create, get, update, delete, activate, deactivate, vision upload, config, etc.)
4. Validate authentication (401 on no token), multi-tenant isolation (403 on wrong tenant)
5. Run: pytest tests/api/test_products_api.py -v

DELIVERABLES:
- API tests for all 12 product endpoints
- Authentication verified (401/403)
- Response schema validation
- Test run output in PR description

SUCCESS: All 12 endpoints tested, 100% passing
```

#### Branches 2-10: [Same pattern for other endpoint groups]
- 0610: Projects API (15 endpoints)
- 0611: Tasks API (8 endpoints)
- 0612: Templates API (13 endpoints)
- 0613: Agent Jobs API (13 endpoints)
- 0614: Settings API (7 endpoints)
- 0615: Users API (6 endpoints)
- 0616: Slash Commands API (4 endpoints)
- 0617: Messages API (5 endpoints)
- 0618: Health/Status API (5 endpoints)

**CLI Merge Protocol**: Same as Phase 1 (merge each branch locally, run tests)

---

### Day 8: Handover 0619 (CLI - 1 day)
**Agent**: integration-tester
**Goal**: Core workflows E2E testing

**Prompt**:
```
Read handovers/600/0619_core_workflows_e2e_testing.md and handovers/600/AGENT_REFERENCE_GUIDE.md.

Execute Handover 0619: Core Workflows E2E Testing

Workflows to test:
1. Fresh Install → First User → Login → Dashboard
2. Product Creation → Vision Upload → Config Save → Activation
3. Project Creation → Task Assignment → Status Updates → Completion

Tasks:
1. Create automated E2E tests: tests/e2e/test_core_workflows.py
2. Test each workflow end-to-end (manual + automated)
3. Capture test output

Run: pytest tests/e2e/test_core_workflows.py -v

Create: handovers/600/0619_workflow_test_results.md
```

**Expected Output**: All 3 workflows pass (automated + manual validation)

---

### Day 9: Handover 0620 (CLI - 1 day)
**Agent**: integration-tester
**Goal**: Orchestration workflows E2E testing

**Prompt**:
```
Read handovers/600/0620_orchestration_workflows_e2e_testing.md and handovers/600/AGENT_REFERENCE_GUIDE.md.

Execute Handover 0620: Orchestration Workflows E2E Testing

Workflows to test:
4. Orchestrator Launch → Mission Assignment → Agent Selection → Workflow Execution
5. Agent Job Lifecycle → Create → Acknowledge → Execute → Complete/Fail

Tasks:
1. Create automated E2E tests: tests/e2e/test_orchestration_workflows.py
2. Verify MissionPlanner, AgentSelector, WorkflowEngine coordination
3. Verify WebSocket events (job:status_changed, job:completed, job:failed)

Run: pytest tests/e2e/test_orchestration_workflows.py -v

Create: handovers/600/0620_orchestration_test_results.md
```

**Expected Output**: Workflows 4-5 pass, WebSocket events verified

---

### Day 10: Handover 0621 (CLI - 1 day)
**Agent**: integration-tester
**Goal**: Advanced workflows E2E testing

**Prompt**:
```
Read handovers/600/0621_advanced_workflows_e2e_testing.md and handovers/600/AGENT_REFERENCE_GUIDE.md.

Execute Handover 0621: Advanced Workflows E2E Testing

Workflows to test:
6. Orchestrator Succession → Context Monitoring → Successor Creation → Handover → Launch
7. Template Management → Customize → Save → Apply → Reset
8. Multi-Tenant Isolation → User A Product → User B Cannot Access → Database Verification

Tasks:
1. Create automated E2E tests: tests/e2e/test_advanced_workflows.py
2. Verify succession handover (<10K tokens)
3. Verify template resolution cascade (product → tenant → system)
4. Verify zero tenant leakage (database query verification)

Run: pytest tests/e2e/test_advanced_workflows.py -v

Create: handovers/600/0621_security_validation.md (multi-tenant report)
```

**Expected Output**: Workflows 6-8 pass, multi-tenant isolation verified

---

### Day 11: Handover 0622 (CLI - 1 day)
**Agent**: architectural-engineer
**Goal**: Implement self-healing decorators

**Prompt**:
```
Read handovers/600/0622_self_healing_decorators_implementation.md and handovers/600/AGENT_REFERENCE_GUIDE.md.

Execute Handover 0622: Self-Healing Decorators Implementation

Tasks:
1. Design @ensure_table_exists decorator pattern
2. Implement decorator: src/giljo_mcp/utils/decorators.py
3. Apply decorators to critical service methods (all 6 services)
4. Test: Delete table, call method, verify table recreated
5. Create tests: tests/unit/test_decorators.py

Create: docs/guides/self_healing_architecture.md

Run: pytest tests/unit/test_decorators.py -v
```

**Expected Output**: Decorator implemented, applied to services, tests pass

---

### Day 12: Handover 0623 (CLI - 1 day)
**Agent**: database-architect
**Goal**: Create baseline schema migration

**Prompt**:
```
Read handovers/600/0623_schema_consolidation_baseline_migration.md and handovers/600/AGENT_REFERENCE_GUIDE.md.

Execute Handover 0623: Schema Consolidation (Baseline Migration)

Tasks:
1. Create baseline schema migration consolidating all 44 migrations
2. Generate: migrations/versions/baseline_schema.py (all 31 tables)
3. Verify baseline creates identical schema to 44-chain
4. Update install.py to use baseline for fresh installs

Verification:
dropdb giljo_mcp && createdb giljo_mcp && alembic upgrade baseline_001
pg_dump giljo_mcp > baseline_schema.sql

dropdb giljo_mcp && createdb giljo_mcp && alembic upgrade head
pg_dump giljo_mcp > chain_schema.sql

diff baseline_schema.sql chain_schema.sql  # Should be identical

Create: handovers/600/0623_schema_verification.md
```

**Expected Output**: Baseline migration created, schema verification passes, fresh install <2-3 min

---

## Week 3: Testing + Docs (Days 13-18)

### Day 13: Handover 0624 (CLI - 1 day)
**Agent**: tdd-implementor
**Goal**: Unit test suite completion (80%+ coverage)

**Prompt**:
```
Read handovers/600/0624_unit_test_suite_completion.md and handovers/600/AGENT_REFERENCE_GUIDE.md.

Execute Handover 0624: Unit Test Suite Completion

Tasks:
1. Fix all remaining unit test failures (from 0602 baseline)
2. Achieve 80%+ coverage on all modules
3. Run: pytest tests/unit/ -v --cov=src/giljo_mcp --cov-report=html

Coverage targets:
- Services: 85%+
- Models: 75%+
- MCP Tools: 80%+
- Utilities: 90%+

Create: handovers/600/0624_coverage_report.md
```

**Expected Output**: 100% unit tests passing, 80%+ overall coverage

---

### Day 14: Handover 0625 (CLI - 1 day)
**Agent**: integration-tester
**Goal**: Integration test suite completion

**Prompt**:
```
Read handovers/600/0625_integration_test_suite_completion.md and handovers/600/AGENT_REFERENCE_GUIDE.md.

Execute Handover 0625: Integration Test Suite Completion

Tasks:
1. Fix all remaining integration test failures
2. Add missing integration tests (service coordination, database transactions)
3. Verify multi-tenant isolation in all scenarios
4. Run: pytest tests/integration/ -v

Create: handovers/600/0625_integration_test_report.md
```

**Expected Output**: 100% integration tests passing, multi-tenant isolation verified

---

### Day 15: Handover 0626 (CLI - 1 day)
**Agent**: integration-tester
**Goal**: E2E test suite & performance benchmarks

**Prompt**:
```
Read handovers/600/0626_e2e_test_suite_performance_benchmarks.md and handovers/600/AGENT_REFERENCE_GUIDE.md.

Execute Handover 0626: E2E Test Suite & Performance Benchmarks

Tasks:
1. Run all E2E tests from Phase 3 (0619-0621)
2. Add performance benchmarks: tests/performance/test_benchmarks.py
3. Verify no >5% performance degradation

Benchmarks:
- Fresh install: <5 min (target: 2-3 min)
- API p95: <100ms
- API p50: <50ms
- DB queries: <10ms (simple), <50ms (complex)

Create: handovers/600/0626_performance_report.md
```

**Expected Output**: All E2E tests pass, performance benchmarks met

---

### Days 16-18: Handovers 0627-0631 (CCW - 5 Parallel Branches)
**Agents**: documentation-specialist (5 instances)
**Goal**: Complete all documentation

**Execute in CCW - Create 5 branches in parallel**:

#### Branch 1: 0627-update-claude-md
**Prompt**:
```
You are the documentation-specialist agent working on Handover 0627: Update CLAUDE.md & System Architecture Docs.

CONTEXT: Read handovers/600/AGENT_REFERENCE_GUIDE.md for universal project context.

TASK:
1. Update CLAUDE.md with Project 600 completion status
2. Update docs/SERVER_ARCHITECTURE_TECH_STACK.md (reflect service layer, self-healing)
3. Update docs/TECHNICAL_ARCHITECTURE.md (hybrid architecture: baseline + decorators)
4. Document migration strategy (baseline vs 44-chain)

DELIVERABLES:
- Updated CLAUDE.md
- Updated architecture docs
- PR with all doc updates

SUCCESS: All docs accurate and reflect current state
```

#### Branch 2: 0628-developer-guides
**Prompt**: [Create service layer guide, testing guide, self-healing guide, migration guide]

#### Branch 3: 0629-user-guides
**Prompt**: [Update product management, project management, orchestrator succession, template management guides]

#### Branch 4: 0630-handover-0632
**Prompt**: [Create Handover 0632 completion report with final metrics]

#### Branch 5: 0631-readme-cleanup
**Prompt**: [Update README_FIRST.md, cleanup obsolete handover files]

**CLI Merge Protocol**: Same as previous phases (merge each branch locally after completion)

---

## Progress Tracking

### Daily Checklist
- [ ] Update `handovers/600/progress.json` with handover completion status
- [ ] Review test pass rate (unit, integration, E2E)
- [ ] Check coverage percentage (overall, per module)
- [ ] Document any blockers or timeline adjustments

### Weekly Review
- **End of Week 1**: Review Phase 0-1 completion (foundation + services)
- **End of Week 2**: Review Phase 2-4 completion (APIs + workflows + self-healing)
- **End of Week 3**: Review Phase 5-6 completion (testing + docs)

### Final Validation (Day 18)
Run comprehensive validation:
```bash
# Fresh install test
dropdb giljo_mcp && createdb giljo_mcp && python install.py
# Expected: <5 min, 31 tables, default tenant + admin

# Full test suite
pytest tests/ -v --cov=src/giljo_mcp --cov-report=html
# Expected: 80%+ coverage, 100% passing

# Performance benchmarks
pytest tests/performance/test_benchmarks.py -v
# Expected: All benchmarks met

# Manual workflow validation
# Execute all 8 workflows manually, capture screenshots
```

---

## Quick Reference Table

| Day | Phase | Handovers | Tool | Agent | Duration | Notes |
|-----|-------|-----------|------|-------|----------|-------|
| **1** | 0 | 0600-0601 | CLI | deep-researcher, installation-flow-agent | 10h | Foundation (audit + fix migration) |
| **2** | 0 | 0602 | CLI | tdd-implementor | 6h | Test baseline |
| **3-5** | 1 | 0603-0608 | CCW | tdd-implementor | 3d | 6 services (parallel) |
| **6-7** | 2 | 0609-0618 | CCW | api-tester | 2d | 10 endpoint groups (parallel) |
| **8** | 3 | 0619 | CLI | integration-tester | 1d | Core workflows (3) |
| **9** | 3 | 0620 | CLI | integration-tester | 1d | Orchestration workflows (2) |
| **10** | 3 | 0621 | CLI | integration-tester | 1d | Advanced workflows (3) |
| **11** | 4 | 0622 | CLI | architectural-engineer | 1d | Self-healing decorators |
| **12** | 4 | 0623 | CLI | database-architect | 1d | Baseline schema |
| **13** | 5 | 0624 | CLI | tdd-implementor | 1d | Unit tests completion |
| **14** | 5 | 0625 | CLI | integration-tester | 1d | Integration tests completion |
| **15** | 5 | 0626 | CLI | integration-tester | 1d | E2E + performance |
| **16-18** | 6 | 0627-0631 | CCW | documentation-specialist | 3d | 5 doc branches (parallel) |

---

## Agent Activation Guide

### CLI (Local) Execution
**You're already in Claude Code CLI. Just provide instructions:**

```
Read handovers/600/06XX_handover_name.md and handovers/600/AGENT_REFERENCE_GUIDE.md.

Execute Handover 06XX: [Handover Title]

[Paste handover-specific prompt from this guide]
```

### CCW (Cloud) Parallel Execution
**Open Claude Code Web → Create new branch → Paste prompt:**

1. Open Claude Code Web
2. Create new branch: `06XX-feature-name`
3. Copy prompt from handover section above
4. Paste prompt (includes reference to AGENT_REFERENCE_GUIDE.md)
5. Let agent execute
6. Create PR to master
7. **Locally**: `git fetch origin && git merge origin/06XX-feature-name`
8. Run tests locally to verify
9. Repeat for all parallel branches

---

## Common Issues & Solutions

### Issue: Fresh install fails (Day 1-2)
**Solution**: Check PostgreSQL version (14+), verify pg_trgm extension, review migration order

### Issue: Test failures overwhelming (Day 2, 13-15)
**Solution**: Prioritize critical tests (80/20 rule), categorize by root cause, fix in batches

### Issue: CCW branches conflict (Days 3-7, 16-18)
**Solution**: Merge early and often, ensure branches touch different files, use `git merge --no-ff`

### Issue: Coverage below 80% (Day 13)
**Solution**: Focus on critical services first (ProductService, OrchestrationService), add edge case tests

### Issue: Performance degradation (Day 15)
**Solution**: Profile slow tests, check database query plans, verify no N+1 queries

### Issue: Timeline slipping (Any day)
**Solution**: De-prioritize "should have" items, extend timeline by 1 week if needed, focus on "must have" criteria

---

## Success Criteria Summary

By Day 18, the following MUST be true:

- [ ] Fresh install completes in <5 min (ideally 2-3 min with baseline schema)
- [ ] All 31 tables created correctly
- [ ] All 6 services validated (80%+ coverage each)
- [ ] All 84+ API endpoints tested (100% passing)
- [ ] All 8 critical workflows pass E2E tests
- [ ] Overall test coverage ≥ 80%
- [ ] 100% test pass rate (unit + integration + E2E)
- [ ] Multi-tenant isolation verified (zero leakage)
- [ ] Performance benchmarks met (no >5% degradation)
- [ ] Self-healing decorators implemented and tested
- [ ] Baseline schema migration created and verified
- [ ] All documentation updated and accurate
- [ ] Handover 0632 completion report created

**If all checkboxes pass**: Project 600 COMPLETE. System is production-ready.

---

**Document Control**:
- **Created**: 2025-11-14
- **Version**: 1.0
- **Audience**: Developers executing Project 600
- **Update Frequency**: As needed (if timeline or scope changes)
