# PROJECTPLAN_600: Complete System Restoration & Validation

**Version**: 1.0
**Created**: 2025-11-14
**Status**: Active - Master Plan
**Duration**: 2-3 weeks (13-18 days)
**Scope**: Handovers 0600-0631 (32 handovers)
**Priority**: 🔴 P0 CRITICAL - Production Readiness

---

## EXECUTIVE SUMMARY

The Handovers 0120-0130 refactoring successfully modularized the GiljoAI MCP architecture, extracting 6 specialized services from a god object and establishing clean separation of concerns. The system **works wonderfully** - orchestration executes, MCP tools function, agents coordinate - but the refactoring exposed critical gaps in our foundation:

**Root Cause**: Rapid migration from monolithic models.py to service layer revealed hidden migration chaos (44 migration chain, 14 missing tables, migration order bugs) and untested assumptions (456 test files, unknown pass rate, no fresh install validation).

**Current State**:
- ✅ **Service Layer**: 6 services extracted and working (ProductService, ProjectService, TaskService, MessageService, ContextService, OrchestrationService)
- ✅ **Core Features**: Orchestration proven, MCP tools functional, template system complete
- ✅ **Database Migration Created**: 20251114_create_missing_base_tables.py handles 14 missing tables
- ⚠️ **Migration Order Issue**: 20251114 migration runs too late in chain (needs reordering)
- ⚠️ **Fresh Install Untested**: Unknown if install.py works on clean system (<5 min target)
- ⚠️ **Test Suite Unknown**: 456 test files exist, pass rate unknown, coverage unknown
- ⚠️ **8 Critical Workflows**: End-to-end validation needed (product creation → project launch → agent execution → succession)
- ⚠️ **Self-Healing Pending**: Decorators not implemented, schema consolidation needed (44 migrations → 1 baseline)

**Where We Came From**:
- **November 12**: prior_to_major_refactor_november branch - app worked, migrations hidden in models.py
- **November 13-14**: Handovers 0120-0130 - Service extraction (198 commits, 429 files changed)
- **Today**: Switched to Alembic-first strategy, exposed migration chaos

**Where We're Going**:
- **Immediate** (Project 600): Working install.py, all features validated, 80%+ test coverage, production-ready foundation
- **Future** (Post-600): Self-healing architecture (baseline schema + on-demand decorators), SaaS evolution, zero-touch deployment

**Solution**: Systematic validation and restoration across 6 phases using hybrid CLI (local, sequential) and CCW (cloud, parallel) execution. Zero compromises - everything must work.

---

## COMPREHENSIVE ISSUE INVENTORY

### 🔴 Database & Installation (P0 - Blocks Everything)

**Issue #1: Migration Order Bug**
- **Problem**: 20251114_create_missing_base_tables.py runs at position 44 in chain
- **Impact**: Fresh install fails - tables referenced before creation
- **Fix**: Reorder to position 1 or consolidate into baseline schema
- **Files**: `migrations/versions/20251114_*.py`, `migrations/script.py.mako`
- **Test**: `python install.py` on clean database

**Issue #2: Fresh Install Untested**
- **Problem**: Unknown if install.py works end-to-end on clean system
- **Impact**: Can't deploy to new environments, dev setup unreliable
- **Fix**: Comprehensive fresh install testing (clean DB → working app <5 min)
- **Files**: `install.py`, all migration files
- **Test**: Docker container test, VM test, manual clean install

**Issue #3: 44-Migration Chain Complexity**
- **Problem**: Long migration chain (risk of dependency hell, slow installs)
- **Impact**: Hard to reason about schema, migration conflicts likely
- **Fix**: Consolidate 44 migrations → 1 baseline schema migration (post-validation)
- **Files**: All `migrations/versions/*.py`
- **Test**: Baseline migration creates identical schema to 44-chain

**Issue #4: pg_trgm Extension Dependency**
- **Problem**: PostgreSQL extension required but creation not verified in all scenarios
- **Impact**: Fresh install may fail if extension missing
- **Fix**: Robust extension check/create in install.py and migration
- **Files**: `installer/core/database.py`, base migration
- **Test**: Install on PostgreSQL without pg_trgm pre-installed

### 🟡 Service Layer (P1 - Core Functionality)

**Issue #5: Service Test Coverage Unknown**
- **Problem**: 6 services extracted, comprehensive tests not run
- **Impact**: Unknown reliability, regressions possible
- **Fix**: 80%+ coverage per service (unit + integration tests)
- **Files**: `tests/unit/test_*_service.py`, `tests/integration/test_*_service.py`
- **Test**: `pytest tests/ -v --cov=src/giljo_mcp/services --cov-report=term-missing`

**Services to Validate**:
1. ProductService (src/giljo_mcp/services/product_service.py)
2. ProjectService (src/giljo_mcp/services/project_service.py)
3. TaskService (src/giljo_mcp/services/task_service.py)
4. MessageService (src/giljo_mcp/services/message_service.py)
5. ContextService (src/giljo_mcp/services/context_service.py)
6. OrchestrationService (src/giljo_mcp/services/orchestration_service.py)

**Coverage Targets**:
- Unit tests: All public methods, error paths, edge cases
- Integration tests: Multi-tenant isolation, database transactions, service coordination
- Performance: No >5% degradation from baseline

### 🟡 API Endpoints (P1 - User-Facing)

**Issue #6: 84+ Endpoints Need Validation**
- **Problem**: No systematic endpoint validation post-refactoring
- **Impact**: Unknown if all routes work, authentication works, responses correct
- **Fix**: Categorize and test all 84+ endpoints
- **Files**: `api/endpoints/*.py` (14 files)
- **Test**: API integration tests, Postman/curl validation

**Endpoint Categories** (Handovers 0609-0618):
1. **Products** (api/endpoints/products.py) - 12 endpoints
2. **Projects** (api/endpoints/projects.py) - 15 endpoints
3. **Tasks** (api/endpoints/tasks.py) - 8 endpoints
4. **Templates** (api/endpoints/templates.py) - 13 endpoints
5. **Agent Jobs** (api/endpoints/agent_jobs.py) - 13 endpoints
6. **Settings** (api/endpoints/settings.py) - 7 endpoints
7. **Users** (api/endpoints/users.py) - 6 endpoints
8. **Slash Commands** (api/endpoints/slash_commands.py) - 4 endpoints
9. **Messages** (api/endpoints/messages.py) - 5 endpoints
10. **Health/Status** (api/endpoints/health.py, status.py) - 5 endpoints

**Good News**: No HTTP 501 stubs found during initial scan (all endpoints implemented)

### 🟡 Testing Infrastructure (P0 - Quality Gate)

**Issue #7: Test Suite Execution Unknown**
- **Problem**: 456 test files exist, unknown how many pass
- **Impact**: Can't validate refactoring didn't break things
- **Fix**: Run full test suite, fix all failures, establish baseline
- **Files**: `tests/**/*.py` (456 files)
- **Test**: `pytest tests/ -v --tb=short`

**Issue #8: Coverage Baseline Missing**
- **Problem**: No coverage metrics before/after refactoring
- **Impact**: Can't measure quality, may have blind spots
- **Fix**: Establish 80%+ coverage baseline, track per module
- **Files**: All `src/giljo_mcp/**/*.py`
- **Test**: `pytest --cov=src/giljo_mcp --cov-report=html`

**Issue #9: Integration Tests Need Fixing**
- **Problem**: Many integration tests likely broken (Agent model removed, service changes)
- **Impact**: Can't validate end-to-end workflows
- **Fix**: Update integration tests for service architecture
- **Files**: `tests/integration/**/*.py`
- **Test**: `pytest tests/integration/ -v`

### 🟢 Workflows (P1 - User Journeys)

**Issue #10: 8 Critical Workflows Need E2E Validation**
- **Problem**: No end-to-end workflow testing post-refactoring
- **Impact**: Unknown if complete user journeys work
- **Fix**: Manual + automated E2E tests for all critical workflows
- **Files**: N/A (behavioral testing)
- **Test**: See workflow list below

**Critical Workflows** (Handovers 0619-0621):
1. **Fresh Install** → First User Creation → Login → Dashboard
2. **Product Creation** → Vision Upload → Config Save → Activation
3. **Project Creation** → Task Assignment → Status Updates → Completion
4. **Orchestrator Launch** → Mission Assignment → Agent Selection → Workflow Execution
5. **Agent Job Lifecycle** → Create → Acknowledge → Execute → Complete/Fail
6. **Orchestrator Succession** → Context Monitoring → Successor Creation → Handover → Launch
7. **Template Management** → Customize → Save → Apply → Reset
8. **Multi-Tenant Isolation** → User A Product → User B Cannot Access → Database Verification

### 🔵 Self-Healing Architecture (P2 - Future-Proofing)

**Issue #11: Self-Healing Decorators Not Implemented**
- **Problem**: Planned @ensure_table_exists decorators don't exist
- **Impact**: Schema drift risk, manual migration management required
- **Fix**: Implement decorator system (post-validation)
- **Files**: `src/giljo_mcp/utils/decorators.py` (new)
- **Test**: Delete table, call decorated method, verify table recreated

**Issue #12: Schema Consolidation Pending**
- **Problem**: 44 migrations hard to reason about
- **Impact**: Slow installs, complex dependency chain
- **Fix**: Create single baseline migration (post-validation)
- **Files**: `migrations/versions/baseline_schema.py` (new)
- **Test**: Baseline creates identical schema to 44-chain

---

## PROJECT PHASES

### Phase 0: Foundation & Diagnosis (Days 1-2)

**Duration**: 2 days
**Tool**: CLI (Local) - Sequential
**Handovers**: 0600, 0601, 0602
**Why CLI**: Requires database access, comprehensive codebase analysis, migration manipulation

#### Handover 0600: Comprehensive System Audit
**Agent**: deep-researcher
**Duration**: 4 hours
**Tasks**:
1. Scan all 31 database tables, verify schema matches models
2. Analyze 44 migration files, identify dependency chain
3. Catalog 84+ API endpoints, categorize by function
4. Audit 456 test files, estimate effort to fix
5. Document 6 services, identify test gaps
6. List 8 critical workflows for E2E testing

**Deliverables**:
- `handovers/600/0600_audit_report.md` - Complete system inventory
- `handovers/600/0600_migration_dependency_graph.txt` - Migration order visualization
- `handovers/600/0600_test_categorization.json` - Test file categorization
- Coverage baseline: Run `pytest --cov` and document results

**Success Criteria**:
- [ ] All 31 tables documented with field counts
- [ ] Migration dependency graph created
- [ ] 84+ endpoints categorized into 10 groups
- [ ] 456 test files categorized (unit/integration/e2e)
- [ ] Test execution baseline established (pass/fail/skip counts)
- [ ] Audit report committed

#### Handover 0601: Fix Migration Order & Fresh Install
**Agent**: installation-flow-agent
**Duration**: 6 hours
**Tasks**:
1. Move 20251114_create_missing_base_tables.py to position 1 in chain
2. Update all downstream migration dependencies
3. Test fresh install on clean PostgreSQL database
4. Validate pg_trgm extension creation
5. Verify all 31 tables created in correct order
6. Benchmark install time (<5 min target)

**Deliverables**:
- Fixed migration: `migrations/versions/00001_baseline_schema.py` (renamed/moved 20251114)
- Updated migrations: All dependent migrations reordered
- Test report: `handovers/600/0601_fresh_install_test.md`
- Install time benchmark: Documented in test report

**Success Criteria**:
- [ ] Migration reordered to position 1
- [ ] Fresh install completes successfully (<5 min)
- [ ] All 31 tables exist after install
- [ ] pg_trgm extension verified
- [ ] Default tenant + admin user created
- [ ] Commit: "fix: Reorder migration chain for fresh install success"

#### Handover 0602: Establish Test Baseline
**Agent**: tdd-implementor
**Duration**: 6 hours
**Tasks**:
1. Run full test suite: `pytest tests/ -v --tb=short`
2. Categorize failures (Agent model, service changes, integration broken)
3. Run coverage: `pytest --cov=src/giljo_mcp --cov-report=html`
4. Document baseline metrics (pass rate, coverage %)
5. Create fix plan for 50+ most critical test failures

**Deliverables**:
- Test baseline: `handovers/600/0602_test_baseline.md`
- Coverage report: `htmlcov/index.html` (gitignored, documented in baseline)
- Failure categorization: `handovers/600/0602_test_failures.json`
- Fix plan: Prioritized list of test fixes for Phase 5

**Success Criteria**:
- [ ] Full test suite executed (capture all output)
- [ ] Baseline metrics documented (X passing, Y failing, Z% coverage)
- [ ] Failures categorized by root cause
- [ ] Coverage report generated and analyzed
- [ ] Fix plan created (50+ critical tests identified)
- [ ] Commit: "test: Establish baseline metrics and failure analysis"

---

### Phase 1: Core Service Validation (Days 3-5)

**Duration**: 3 days
**Tool**: CCW (Cloud) - 6 Parallel Branches
**Handovers**: 0603-0608
**Why CCW**: Pure code changes, can run in parallel, no DB schema changes

**Parallel Execution**: Create 6 CCW branches simultaneously, each validates one service

#### Handover 0603: ProductService Validation
**Agent**: tdd-implementor
**CCW Branch**: `0603-product-service-tests`
**Duration**: 1 day
**Tasks**:
1. Read `src/giljo_mcp/services/product_service.py` (analyze all methods)
2. Create comprehensive unit tests: `tests/unit/test_product_service.py`
3. Create integration tests: `tests/integration/test_product_service.py`
4. Test multi-tenant isolation (product leakage prevention)
5. Achieve 80%+ coverage

**Test Coverage**:
- create_product() - success, validation errors, duplicate name
- get_product() - success, not found, wrong tenant
- update_product() - success, config_data preservation, vision upload
- delete_product() - soft delete, cascade projects
- activate_product() / deactivate_product() - single active enforcement
- list_products() - tenant isolation, pagination

**Deliverables**:
- Unit tests: `tests/unit/test_product_service.py` (80%+ coverage)
- Integration tests: `tests/integration/test_product_service.py`
- Test run output in PR description
- Coverage report snippet

**Success Criteria**:
- [ ] All ProductService methods tested
- [ ] 80%+ coverage achieved
- [ ] Multi-tenant isolation verified
- [ ] All tests pass locally
- [ ] PR created with test results

#### Handover 0604: ProjectService Validation
**Agent**: tdd-implementor
**CCW Branch**: `0604-project-service-tests`
**Duration**: 1 day
**Tasks**:
1. Read `src/giljo_mcp/services/project_service.py`
2. Create comprehensive unit tests: `tests/unit/test_project_service.py`
3. Create integration tests: `tests/integration/test_project_service.py`
4. Test product-project relationships (cascade, active constraints)
5. Achieve 80%+ coverage

**Test Coverage**:
- create_project() - success, validation, product association
- get_project() - success, not found, tenant isolation
- update_project() - status changes, mission updates
- delete_project() - soft delete, 10-day recovery window
- activate_project() / pause_project() - single active per product
- list_projects() - product filtering, tenant isolation

**Deliverables**:
- Unit tests: `tests/unit/test_project_service.py` (80%+ coverage)
- Integration tests: `tests/integration/test_project_service.py`
- Test run output in PR description
- Coverage report snippet

**Success Criteria**:
- [ ] All ProjectService methods tested
- [ ] 80%+ coverage achieved
- [ ] Product-project relationships verified
- [ ] All tests pass locally
- [ ] PR created with test results

#### Handover 0605: TaskService Validation
**Agent**: tdd-implementor
**CCW Branch**: `0605-task-service-tests`
**Duration**: 1 day
**Tasks**:
1. Read `src/giljo_mcp/services/task_service.py`
2. Create comprehensive tests (unit + integration)
3. Test project-task relationships
4. Achieve 80%+ coverage

**Success Criteria**: Same pattern as 0603/0604

#### Handover 0606: MessageService Validation
**Agent**: tdd-implementor
**CCW Branch**: `0606-message-service-tests`
**Duration**: 1 day
**Tasks**:
1. Read `src/giljo_mcp/services/message_service.py`
2. Create comprehensive tests (JSONB message handling)
3. Test agent-to-agent messaging, queue operations
4. Achieve 80%+ coverage

**Success Criteria**: Same pattern as 0603/0604

#### Handover 0607: ContextService Validation
**Agent**: tdd-implementor
**CCW Branch**: `0607-context-service-tests`
**Duration**: 1 day
**Tasks**:
1. Read `src/giljo_mcp/services/context_service.py`
2. Create comprehensive tests (context tracking, succession)
3. Test context budget calculations
4. Achieve 80%+ coverage

**Success Criteria**: Same pattern as 0603/0604

#### Handover 0608: OrchestrationService Validation
**Agent**: tdd-implementor
**CCW Branch**: `0608-orchestration-service-tests`
**Duration**: 1 day
**Tasks**:
1. Read `src/giljo_mcp/services/orchestration_service.py`
2. Create comprehensive tests (mission planning, agent selection, workflow)
3. Test AgentJobManager integration
4. Achieve 80%+ coverage

**Success Criteria**: Same pattern as 0603/0604

**Phase 1 CLI Merge Protocol**:
After each CCW branch completes:
1. Locally: `git fetch origin`, `git merge origin/060X-service-tests`
2. Run tests: `pytest tests/unit/test_X_service.py tests/integration/test_X_service.py -v`
3. Verify coverage: `pytest --cov=src/giljo_mcp/services/X_service.py`
4. If pass: Keep merge. If fail: Investigate and fix.
5. After all 6 merged: Run full service test suite

---

### Phase 2: API Endpoint Validation (Days 6-7)

**Duration**: 2 days
**Tool**: CCW (Cloud) - 10 Parallel Branches
**Handovers**: 0609-0618
**Why CCW**: API endpoint tests, no DB schema changes, parallel execution safe

**Parallel Execution**: Create 10 CCW branches simultaneously, each validates one endpoint category

#### Handover 0609: Products API Validation
**Agent**: api-tester
**CCW Branch**: `0609-products-api-tests`
**Duration**: 4 hours
**Tasks**:
1. Read `api/endpoints/products.py`
2. Create API integration tests: `tests/api/test_products_api.py`
3. Test all 12 product endpoints (CRUD, activate, deactivate, vision upload, config)
4. Validate authentication, multi-tenant isolation, error responses

**Endpoints to Test** (12 total):
- GET /api/v1/products (list)
- POST /api/v1/products (create)
- GET /api/v1/products/{id} (get)
- PUT /api/v1/products/{id} (update)
- DELETE /api/v1/products/{id} (soft delete)
- POST /api/v1/products/{id}/activate
- POST /api/v1/products/{id}/deactivate
- POST /api/v1/products/{id}/vision/upload
- GET /api/v1/products/{id}/config
- PUT /api/v1/products/{id}/config
- GET /api/v1/products/active (get active product)
- POST /api/v1/products/{id}/recover (undelete)

**Deliverables**:
- API tests: `tests/api/test_products_api.py`
- Test run output in PR
- Response schema validation (Pydantic models verified)

**Success Criteria**:
- [ ] All 12 endpoints tested (happy path + error cases)
- [ ] Authentication verified (401 on no token)
- [ ] Multi-tenant isolation verified (403 on wrong tenant)
- [ ] All tests pass
- [ ] PR created

#### Handover 0610: Projects API Validation
**Agent**: api-tester
**CCW Branch**: `0610-projects-api-tests`
**Duration**: 4 hours
**Tasks**: Same pattern as 0609, test 15 project endpoints

**Endpoints** (15 total): list, create, get, update, delete, activate, pause, cancel, complete, launch, recover, summary, tasks, timeline, etc.

#### Handover 0611: Tasks API Validation
**Agent**: api-tester
**CCW Branch**: `0611-tasks-api-tests`
**Duration**: 3 hours
**Tasks**: Test 8 task endpoints

#### Handover 0612: Templates API Validation
**Agent**: api-tester
**CCW Branch**: `0612-templates-api-tests`
**Duration**: 4 hours
**Tasks**: Test 13 template endpoints (CRUD, reset, diff, preview, history)

#### Handover 0613: Agent Jobs API Validation
**Agent**: api-tester
**CCW Branch**: `0613-agent-jobs-api-tests`
**Duration**: 4 hours
**Tasks**: Test 13 agent job endpoints (create, acknowledge, complete, fail, succession, etc.)

#### Handover 0614: Settings API Validation
**Agent**: api-tester
**CCW Branch**: `0614-settings-api-tests`
**Duration**: 3 hours
**Tasks**: Test 7 settings endpoints (get/update user settings, admin settings tabs)

#### Handover 0615: Users API Validation
**Agent**: api-tester
**CCW Branch**: `0615-users-api-tests`
**Duration**: 3 hours
**Tasks**: Test 6 user endpoints (CRUD, password reset, role management)

#### Handover 0616: Slash Commands API Validation
**Agent**: api-tester
**CCW Branch**: `0616-slash-commands-api-tests`
**Duration**: 2 hours
**Tasks**: Test 4 slash command endpoints (/gil_handover, etc.)

#### Handover 0617: Messages API Validation
**Agent**: api-tester
**CCW Branch**: `0617-messages-api-tests`
**Duration**: 3 hours
**Tasks**: Test 5 message endpoints (queue operations, JSONB handling)

#### Handover 0618: Health/Status API Validation
**Agent**: api-tester
**CCW Branch**: `0618-health-status-api-tests`
**Duration**: 2 hours
**Tasks**: Test 5 health/status endpoints (health check, metrics, DB status)

**Phase 2 CLI Merge Protocol**:
Same as Phase 1 - merge each completed branch locally, run tests, verify pass

---

### Phase 3: Critical Workflow Validation (Days 8-10)

**Duration**: 3 days
**Tool**: CLI (Local) - Sequential
**Handovers**: 0619-0621
**Why CLI**: End-to-end testing requires running backend, database, WebSocket events

#### Handover 0619: Core Workflows E2E Testing
**Agent**: integration-tester
**Duration**: 1 day
**Tasks**:
1. Workflow 1: Fresh Install → First User → Login → Dashboard
2. Workflow 2: Product Creation → Vision Upload → Config Save → Activation
3. Workflow 3: Project Creation → Task Assignment → Status Updates → Completion
4. Create automated E2E tests: `tests/e2e/test_core_workflows.py`

**Test Details**:

**Workflow 1: Fresh Install & Onboarding**
```python
def test_fresh_install_workflow():
    # 1. Clean database
    # 2. Run install.py
    # 3. Navigate to /welcome
    # 4. Create first user (admin)
    # 5. Login with credentials
    # 6. Verify dashboard loads
    # 7. Verify default tenant created
```

**Workflow 2: Product Lifecycle**
```python
def test_product_lifecycle():
    # 1. Create product (POST /api/v1/products)
    # 2. Upload vision doc (POST /api/v1/products/{id}/vision/upload)
    # 3. Save config_data (PUT /api/v1/products/{id}/config)
    # 4. Activate product (POST /api/v1/products/{id}/activate)
    # 5. Verify single active product constraint
    # 6. Deactivate product
    # 7. Delete product (soft delete)
```

**Workflow 3: Project Lifecycle**
```python
def test_project_lifecycle():
    # 1. Create project under active product
    # 2. Assign tasks to project
    # 3. Update project status (active → paused → active)
    # 4. Complete tasks
    # 5. Complete project
    # 6. Verify cascade to tasks
```

**Deliverables**:
- E2E tests: `tests/e2e/test_core_workflows.py`
- Test run output: `handovers/600/0619_workflow_test_results.md`
- Screen recordings (optional): Capture workflows in UI

**Success Criteria**:
- [ ] All 3 workflows pass automated tests
- [ ] Manual validation completed (screenshots/recording)
- [ ] All tests pass
- [ ] Commit: "test: Add E2E tests for core workflows"

#### Handover 0620: Orchestration Workflows E2E Testing
**Agent**: integration-tester
**Duration**: 1 day
**Tasks**:
1. Workflow 4: Orchestrator Launch → Mission Assignment → Agent Selection → Workflow Execution
2. Workflow 5: Agent Job Lifecycle → Create → Acknowledge → Execute → Complete/Fail
3. Create automated E2E tests: `tests/e2e/test_orchestration_workflows.py`

**Test Details**:

**Workflow 4: Orchestrator Execution**
```python
def test_orchestrator_workflow():
    # 1. Create product with vision
    # 2. Create project
    # 3. Launch orchestrator (create agent job)
    # 4. Verify MissionPlanner generates condensed mission
    # 5. Verify AgentSelector chooses appropriate agents
    # 6. Verify WorkflowEngine coordinates agents
    # 7. Monitor WebSocket events (job:status_changed)
    # 8. Verify orchestrator completes successfully
```

**Workflow 5: Agent Job Lifecycle**
```python
def test_agent_job_lifecycle():
    # 1. Create agent job (POST /api/v1/agent-jobs)
    # 2. Verify job status = 'pending'
    # 3. Acknowledge job (simulating agent)
    # 4. Verify status = 'in_progress'
    # 5. Post messages to communication queue
    # 6. Complete job with success
    # 7. Verify status = 'completed'
    # 8. Test failure path (fail job)
```

**Deliverables**:
- E2E tests: `tests/e2e/test_orchestration_workflows.py`
- Test run output: `handovers/600/0620_orchestration_test_results.md`
- WebSocket event log (verify real-time updates)

**Success Criteria**:
- [ ] Workflows 4-5 pass automated tests
- [ ] WebSocket events verified
- [ ] AgentJobManager integration confirmed
- [ ] Commit: "test: Add E2E tests for orchestration workflows"

#### Handover 0621: Advanced Workflows E2E Testing
**Agent**: integration-tester
**Duration**: 1 day
**Tasks**:
1. Workflow 6: Orchestrator Succession → Context Monitoring → Successor Creation → Handover → Launch
2. Workflow 7: Template Management → Customize → Save → Apply → Reset
3. Workflow 8: Multi-Tenant Isolation → User A Product → User B Cannot Access → Database Verification
4. Create automated E2E tests: `tests/e2e/test_advanced_workflows.py`

**Test Details**:

**Workflow 6: Orchestrator Succession**
```python
def test_orchestrator_succession():
    # 1. Create orchestrator job
    # 2. Simulate context usage (90%+ of budget)
    # 3. Trigger succession (MCP tool or /gil_handover)
    # 4. Verify successor created (instance_number += 1)
    # 5. Verify handover summary generated (<10K tokens)
    # 6. Verify lineage tracking (spawned_by chain)
    # 7. Test manual launch via UI button
```

**Workflow 7: Template Management**
```python
def test_template_workflow():
    # 1. Get default template
    # 2. Customize template (edit in Monaco editor simulation)
    # 3. Save tenant-specific template
    # 4. Apply template to product
    # 5. Verify template resolution cascade
    # 6. Reset template to default
    # 7. Verify cache invalidation (3-layer cache)
```

**Workflow 8: Multi-Tenant Isolation**
```python
def test_multi_tenant_isolation():
    # 1. Create User A, Tenant A, Product A
    # 2. Create User B, Tenant B, Product B
    # 3. User A: GET /api/v1/products (verify only Product A visible)
    # 4. User B: GET /api/v1/products/{product_a_id} (verify 403 Forbidden)
    # 5. Database query: Verify tenant_id enforcement
    # 6. Test cascade delete isolation
```

**Deliverables**:
- E2E tests: `tests/e2e/test_advanced_workflows.py`
- Multi-tenant security report: `handovers/600/0621_security_validation.md`
- Test run output

**Success Criteria**:
- [ ] Workflows 6-8 pass automated tests
- [ ] Multi-tenant isolation verified (zero leakage)
- [ ] Succession handover verified
- [ ] Template system validated
- [ ] Commit: "test: Add E2E tests for advanced workflows"

---

### Phase 4: Self-Healing Implementation (Days 11-12)

**Duration**: 2 days
**Tool**: CLI (Local) - Sequential
**Handovers**: 0622-0623
**Why CLI**: Database schema manipulation, decorator implementation requires local testing

#### Handover 0622: Self-Healing Decorators Implementation
**Agent**: architectural-engineer
**Duration**: 1 day
**Tasks**:
1. Design @ensure_table_exists decorator pattern
2. Implement decorator: `src/giljo_mcp/utils/decorators.py`
3. Apply decorators to critical service methods
4. Test: Delete table, call method, verify table recreated
5. Document self-healing strategy

**Implementation**:

```python
# src/giljo_mcp/utils/decorators.py

from functools import wraps
from sqlalchemy import inspect
from src.giljo_mcp.models import Base

def ensure_table_exists(model_class):
    """
    Decorator to ensure database table exists before method execution.
    If table missing, creates it on-demand from SQLAlchemy model.

    Usage:
        @ensure_table_exists(Product)
        def create_product(self, data): ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check if table exists
            engine = get_engine()  # Get SQLAlchemy engine
            inspector = inspect(engine)
            table_name = model_class.__tablename__

            if table_name not in inspector.get_table_names():
                # Table missing - create it on-demand
                logger.warning(f"Table {table_name} missing - creating on-demand")
                model_class.__table__.create(engine)
                logger.info(f"Table {table_name} created successfully")

            return func(*args, **kwargs)
        return wrapper
    return decorator
```

**Apply to Services**:
```python
# src/giljo_mcp/services/product_service.py

from src.giljo_mcp.utils.decorators import ensure_table_exists
from src.giljo_mcp.models import Product

class ProductService:
    @ensure_table_exists(Product)
    def create_product(self, data): ...

    @ensure_table_exists(Product)
    def get_product(self, product_id): ...
```

**Test Strategy**:
```python
# tests/unit/test_decorators.py

def test_ensure_table_exists_recreates_missing_table():
    # 1. Drop products table
    # 2. Call create_product()
    # 3. Verify table exists
    # 4. Verify product created successfully
```

**Deliverables**:
- Decorator implementation: `src/giljo_mcp/utils/decorators.py`
- Applied to 6 services (all critical methods)
- Tests: `tests/unit/test_decorators.py`
- Documentation: `docs/guides/self_healing_architecture.md`

**Success Criteria**:
- [ ] @ensure_table_exists decorator implemented
- [ ] Applied to all service CRUD methods
- [ ] Tests pass (table recreation verified)
- [ ] Documentation created
- [ ] Commit: "feat: Implement self-healing table decorators"

#### Handover 0623: Schema Consolidation (Baseline Migration)
**Agent**: database-architect
**Duration**: 1 day
**Tasks**:
1. Create baseline schema migration consolidating all 44 migrations
2. Generate single migration: `migrations/versions/baseline_schema.py`
3. Verify baseline creates identical schema to 44-chain
4. Update install.py to use baseline for fresh installs
5. Document migration consolidation strategy

**Implementation**:

```python
# migrations/versions/baseline_schema.py
"""Baseline schema - consolidates 44 migrations into single schema

Revision ID: baseline_001
Revises: None
Create Date: 2025-11-14

This migration creates the complete GiljoAI MCP schema from scratch.
For existing installations, use the 44-migration chain.
For fresh installs, use this baseline for speed.
"""

def upgrade():
    # Create all 31 tables in correct order
    # 1. Users & tenants
    op.create_table('users', ...)
    op.create_table('tenants', ...)

    # 2. Products, projects, tasks
    op.create_table('products', ...)
    op.create_table('projects', ...)
    op.create_table('tasks', ...)

    # 3. MCP agent jobs
    op.create_table('mcp_agent_jobs', ...)

    # 4. Templates, messages, context
    op.create_table('agent_templates', ...)
    op.create_table('template_archives', ...)
    op.create_table('agent_messages', ...)
    op.create_table('context_usage', ...)

    # ... all 31 tables

    # Create indexes, constraints, extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

def downgrade():
    # Drop all tables
    pass  # Baseline has no downgrade
```

**Verification**:
```bash
# Test 1: Fresh install with baseline
dropdb giljo_mcp && createdb giljo_mcp
alembic upgrade baseline_001
pg_dump giljo_mcp > baseline_schema.sql

# Test 2: Fresh install with 44-chain
dropdb giljo_mcp && createdb giljo_mcp
alembic upgrade head
pg_dump giljo_mcp > chain_schema.sql

# Compare schemas (should be identical)
diff baseline_schema.sql chain_schema.sql
```

**Deliverables**:
- Baseline migration: `migrations/versions/baseline_schema.py`
- Updated install.py (use baseline for fresh installs)
- Schema comparison report: `handovers/600/0623_schema_verification.md`
- Migration strategy doc: `docs/guides/migration_strategy.md`

**Success Criteria**:
- [ ] Baseline migration created (all 31 tables)
- [ ] Schema verification passes (baseline == 44-chain)
- [ ] Fresh install uses baseline (<2 min vs 5 min)
- [ ] Documentation updated
- [ ] Commit: "feat: Add baseline schema migration for fast installs"

---

### Phase 5: Comprehensive Testing (Days 13-15)

**Duration**: 3 days
**Tool**: CLI (Local) - Sequential
**Handovers**: 0624-0626
**Why CLI**: Full test suite execution, coverage analysis, performance benchmarks

#### Handover 0624: Unit Test Suite Completion
**Agent**: tdd-implementor
**Duration**: 1 day
**Tasks**:
1. Fix all remaining unit test failures (from 0602 baseline)
2. Achieve 80%+ coverage on all modules
3. Add missing tests for edge cases
4. Run full unit test suite: `pytest tests/unit/ -v --cov=src/giljo_mcp --cov-report=html`

**Focus Areas**:
- Service layer: 6 services (ProductService, ProjectService, TaskService, MessageService, ContextService, OrchestrationService)
- Utilities: decorators, helpers, validators
- Models: SQLAlchemy model methods
- MCP tools: All 20+ MCP tools (thin client, succession, template, etc.)

**Coverage Targets** (per module):
- Services: 85%+ (critical path)
- Models: 75%+ (mostly SQLAlchemy boilerplate)
- MCP Tools: 80%+
- Utilities: 90%+

**Deliverables**:
- Fixed unit tests (all passing)
- Coverage report: `htmlcov/index.html`
- Coverage summary: `handovers/600/0624_coverage_report.md`
- Missing test identification: Document any intentional gaps

**Success Criteria**:
- [ ] 100% unit tests passing
- [ ] Overall coverage ≥ 80%
- [ ] No module below 70% coverage
- [ ] Coverage report committed (summary only, not HTML)
- [ ] Commit: "test: Achieve 80%+ unit test coverage"

#### Handover 0625: Integration Test Suite Completion
**Agent**: integration-tester
**Duration**: 1 day
**Tasks**:
1. Fix all remaining integration test failures
2. Add missing integration tests (service coordination, database transactions)
3. Verify multi-tenant isolation in all scenarios
4. Run full integration test suite: `pytest tests/integration/ -v`

**Focus Areas**:
- Service interactions (ProductService + ProjectService coordination)
- Database transactions (rollback on error)
- Multi-tenant isolation (zero leakage)
- WebSocket events (real-time updates)
- AgentJobManager integration

**Test Scenarios**:
- Product activation cascades to projects (deactivate projects when product deactivated)
- Project soft delete recoverable within 10 days
- Agent job lifecycle (create → acknowledge → complete)
- Template resolution cascade (product → tenant → system)
- Orchestrator succession (context monitoring → successor creation)

**Deliverables**:
- Fixed integration tests (all passing)
- Integration test report: `handovers/600/0625_integration_test_report.md`
- Multi-tenant security verification

**Success Criteria**:
- [ ] 100% integration tests passing
- [ ] Multi-tenant isolation verified (zero leakage)
- [ ] Database transactions verified (rollback on error)
- [ ] WebSocket events verified
- [ ] Commit: "test: Complete integration test suite"

#### Handover 0626: E2E Test Suite & Performance Benchmarks
**Agent**: integration-tester
**Duration**: 1 day
**Tasks**:
1. Run all E2E tests from Phase 3 (0619-0621)
2. Add performance benchmarks (API response times, database query times)
3. Verify no >5% performance degradation from baseline
4. Create automated E2E test suite (can run in CI/CD)

**Performance Benchmarks**:
- Fresh install time: <5 min (target: 2-3 min with baseline schema)
- API response time: <100ms (p95), <50ms (p50)
- Database query time: <10ms (simple queries), <50ms (complex joins)
- WebSocket latency: <20ms
- Test suite execution: <10 min (unit + integration), <30 min (full suite)

**Benchmark Tests**:
```python
# tests/performance/test_benchmarks.py

def test_api_response_times():
    # Measure p50, p95, p99 for all endpoints
    # Verify <100ms p95

def test_database_query_performance():
    # Measure SELECT, INSERT, UPDATE, DELETE times
    # Verify <10ms for indexed queries

def test_fresh_install_time():
    # Measure end-to-end install time
    # Verify <5 min (target: 2-3 min)
```

**Deliverables**:
- E2E test suite: `tests/e2e/` (all tests passing)
- Performance benchmarks: `tests/performance/test_benchmarks.py`
- Benchmark report: `handovers/600/0626_performance_report.md`
- CI/CD configuration: `.github/workflows/test.yml` (optional)

**Success Criteria**:
- [ ] All E2E tests passing
- [ ] Performance benchmarks meet targets (no >5% degradation)
- [ ] Fresh install <5 min (ideally 2-3 min)
- [ ] API p95 <100ms
- [ ] Commit: "test: Add performance benchmarks and E2E suite"

---

### Phase 6: Documentation & Handoff (Days 16-18)

**Duration**: 3 days
**Tool**: CCW (Cloud) - 5 Parallel Branches
**Handovers**: 0627-0631
**Why CCW**: Pure documentation work, can run in parallel

#### Handover 0627: Update CLAUDE.md & System Architecture Docs
**Agent**: documentation-specialist
**CCW Branch**: `0627-update-claude-md`
**Duration**: 4 hours
**Tasks**:
1. Update `CLAUDE.md` with Project 600 completion status
2. Update `docs/SERVER_ARCHITECTURE_TECH_STACK.md` (reflect service layer, self-healing)
3. Update `docs/TECHNICAL_ARCHITECTURE.md` (hybrid architecture: baseline + decorators)
4. Document migration strategy (baseline vs 44-chain)

**Updates**:
- CLAUDE.md: Add "Project 600 Complete" section, update tech stack, update testing info
- Architecture docs: Document 6 services, self-healing decorators, baseline schema
- Migration docs: Document two-path strategy (baseline for fresh, 44-chain for existing)

**Deliverables**:
- Updated: `CLAUDE.md`
- Updated: `docs/SERVER_ARCHITECTURE_TECH_STACK.md`
- Updated: `docs/TECHNICAL_ARCHITECTURE.md`
- Updated: `docs/guides/migration_strategy.md`
- PR with all doc updates

**Success Criteria**:
- [ ] CLAUDE.md reflects current state (Project 600 complete, 80%+ test coverage)
- [ ] Architecture docs accurate (service layer, self-healing, baseline schema)
- [ ] PR created and merged

#### Handover 0628: Create Developer Guides
**Agent**: documentation-specialist
**CCW Branch**: `0628-developer-guides`
**Duration**: 4 hours
**Tasks**:
1. Create service layer guide: `docs/guides/service_layer_guide.md`
2. Create testing guide: `docs/guides/testing_guide.md`
3. Create self-healing guide: `docs/guides/self_healing_architecture.md`
4. Create migration guide: `docs/guides/migration_strategy.md`

**Content**:
- Service Layer Guide: How to add new services, patterns, examples
- Testing Guide: Unit/integration/E2E test patterns, coverage targets, CI/CD
- Self-Healing Guide: @ensure_table_exists usage, when to use, limitations
- Migration Guide: Baseline vs 44-chain, when to consolidate, how to create migrations

**Deliverables**:
- `docs/guides/service_layer_guide.md`
- `docs/guides/testing_guide.md`
- `docs/guides/self_healing_architecture.md`
- `docs/guides/migration_strategy.md`
- PR with all new guides

**Success Criteria**:
- [ ] All 4 guides created
- [ ] Code examples included and tested
- [ ] Clear, concise, practical
- [ ] PR created and merged

#### Handover 0629: Create User Guides
**Agent**: documentation-specialist
**CCW Branch**: `0629-user-guides`
**Duration**: 4 hours
**Tasks**:
1. Update product management guide: `docs/user_guides/product_management_guide.md`
2. Update project management guide: `docs/user_guides/project_management_guide.md`
3. Update orchestrator succession guide: `docs/user_guides/orchestrator_succession_guide.md`
4. Update template management guide: `docs/user_guides/template_management_guide.md`

**Updates**:
- Product Management: Reflect tested workflows, vision upload, config_data
- Project Management: Reflect soft delete, 10-day recovery, single active per product
- Orchestrator Succession: Reflect tested succession workflow, /gil_handover command
- Template Management: Reflect template resolution cascade, cache layer

**Deliverables**:
- Updated user guides (4 files)
- Screenshots (optional, if missing)
- PR with all updates

**Success Criteria**:
- [ ] All user guides accurate and tested
- [ ] Workflows match E2E tests
- [ ] PR created and merged

#### Handover 0630: Create Handover 0632 (Project 600 Completion Report)
**Agent**: documentation-specialist
**CCW Branch**: `0630-handover-0632`
**Duration**: 3 hours
**Tasks**:
1. Create `handovers/0632_project_600_completion_report.md`
2. Summarize all 32 handovers (0600-0631)
3. Document final metrics (test coverage, performance, install time)
4. Create lessons learned section
5. Identify next steps (roadmap for 0700+)

**Content**:
```markdown
# Handover 0632: Project 600 Completion Report

## Executive Summary
[What was accomplished, key metrics]

## Handover Summary (0600-0631)
[Table of all 32 handovers with status, deliverables]

## Final Metrics
- Test Coverage: X% overall, Y% per service
- Performance: Fresh install Z min, API p95 W ms
- All 8 workflows validated
- 84+ endpoints tested

## Lessons Learned
[What went well, what to improve]

## Next Steps
[Roadmap for 0700+ handovers]

## Migration to Production
[Deployment checklist, rollback plan]
```

**Deliverables**:
- `handovers/0632_project_600_completion_report.md`
- Final metrics document
- PR

**Success Criteria**:
- [ ] Completion report created
- [ ] All handovers documented
- [ ] Metrics accurate
- [ ] PR created and merged

#### Handover 0631: Update README_FIRST.md & Cleanup
**Agent**: documentation-specialist
**CCW Branch**: `0631-readme-cleanup`
**Duration**: 2 hours
**Tasks**:
1. Update `docs/README_FIRST.md` (reflect Project 600 completion)
2. Cleanup obsolete handover files (0510, 0511 drafts)
3. Update `handovers/HANDOVER_INSTRUCTIONS.md` (add Project 600 as example)
4. Final documentation audit (broken links, outdated info)

**Deliverables**:
- Updated: `docs/README_FIRST.md`
- Cleaned: Obsolete handover files removed
- Updated: `handovers/HANDOVER_INSTRUCTIONS.md`
- PR with cleanup

**Success Criteria**:
- [ ] README_FIRST.md accurate
- [ ] All broken links fixed
- [ ] Obsolete files removed
- [ ] PR created and merged

---

## EXECUTION GUIDE FOR DEVELOPER

### Quick Reference Table

| Phase | Days | Tool | Execution | Agents | Handovers | Parallel Groups |
|-------|------|------|-----------|--------|-----------|-----------------|
| **0: Foundation** | 1-2 | CLI | Sequential | deep-researcher, installation-flow-agent, tdd-implementor | 0600-0602 | None |
| **1: Services** | 3-5 | CCW | 6 Parallel Branches | tdd-implementor | 0603-0608 | 6 (one per service) |
| **2: APIs** | 6-7 | CCW | 10 Parallel Branches | api-tester | 0609-0618 | 10 (one per endpoint group) |
| **3: Workflows** | 8-10 | CLI | Sequential | integration-tester | 0619-0621 | None |
| **4: Self-Healing** | 11-12 | CLI | Sequential | architectural-engineer, database-architect | 0622-0623 | None |
| **5: Testing** | 13-15 | CLI | Sequential | tdd-implementor, integration-tester | 0624-0626 | None |
| **6: Docs** | 16-18 | CCW | 5 Parallel Branches | documentation-specialist | 0627-0631 | 5 (one per doc category) |

### Visual Timeline

```
Week 1: Foundation + Services
┌─────┬─────┬─────┬─────┬─────┐
│ D1  │ D2  │ D3  │ D4  │ D5  │
├─────┼─────┼─────┼─────┼─────┤
│ CLI │ CLI │ CCW │ CCW │ CCW │
│0600 │0601 │0603 │Cont.│Cont.│
│     │0602 │0604 │     │     │
│     │     │0605 │     │     │
│     │     │0606 │     │     │
│     │     │0607 │     │     │
│     │     │0608 │     │     │
└─────┴─────┴─────┴─────┴─────┘

Week 2: APIs + Workflows + Self-Healing
┌─────┬─────┬─────┬─────┬─────┐
│ D6  │ D7  │ D8  │ D9  │ D10 │
├─────┼─────┼─────┼─────┼─────┤
│ CCW │ CCW │ CLI │ CLI │ CLI │
│0609 │Cont.│0619 │0620 │0621 │
│0610 │     │     │     │     │
│0611 │     │     │     │     │
│0612 │     │     │     │     │
│0613 │     │     │     │     │
│0614 │     │     │     │     │
│0615 │     │     │     │     │
│0616 │     │     │     │     │
│0617 │     │     │     │     │
│0618 │     │     │     │     │
└─────┴─────┴─────┴─────┴─────┘

Week 3: Self-Healing + Testing + Docs
┌─────┬─────┬─────┬─────┬─────┬─────┐
│ D11 │ D12 │ D13 │ D14 │ D15 │ D16-18 │
├─────┼─────┼─────┼─────┼─────┼────────┤
│ CLI │ CLI │ CLI │ CLI │ CLI │  CCW   │
│0622 │0623 │0624 │0625 │0626 │ 0627   │
│     │     │     │     │     │ 0628   │
│     │     │     │     │     │ 0629   │
│     │     │     │     │     │ 0630   │
│     │     │     │     │     │ 0631   │
└─────┴─────┴─────┴─────┴─────┴────────┘
```

### CLI vs CCW Decision Guide

**Use CLI (Local) when**:
- ✅ Database schema changes required
- ✅ Migration manipulation needed
- ✅ End-to-end testing (requires running backend)
- ✅ Service implementation (requires DB fixtures)
- ✅ Performance benchmarks (requires local environment)
- ✅ Sequential execution required (dependencies between tasks)

**Use CCW (Cloud) when**:
- ✅ Pure code changes (no DB schema changes)
- ✅ API endpoint tests (stateless, can mock DB)
- ✅ Documentation work
- ✅ Parallel execution possible (no dependencies)
- ✅ Independent branches can merge later

**Parallel Execution Groups**:
1. **Phase 1** (Services): 6 parallel CCW branches (0603-0608)
2. **Phase 2** (APIs): 10 parallel CCW branches (0609-0618)
3. **Phase 6** (Docs): 5 parallel CCW branches (0627-0631)

**Merge Protocol**:
- After each CCW branch completes: Merge locally, run tests, verify pass
- After each CLI handover completes: Commit to master, push

---

## HANDOVER MAPPING TABLE

| Handover | Title | Phase | Tool | Agent Type | Parallel Group | Depends On | Duration |
|----------|-------|-------|------|------------|----------------|------------|----------|
| **0600** | Comprehensive System Audit | 0 | CLI | deep-researcher | Sequential | None | 4h |
| **0601** | Fix Migration Order & Fresh Install | 0 | CLI | installation-flow-agent | Sequential | 0600 | 6h |
| **0602** | Establish Test Baseline | 0 | CLI | tdd-implementor | Sequential | 0601 | 6h |
| **0603** | ProductService Validation | 1 | CCW | tdd-implementor | Group A (Services) | 0602 | 1d |
| **0604** | ProjectService Validation | 1 | CCW | tdd-implementor | Group A (Services) | 0602 | 1d |
| **0605** | TaskService Validation | 1 | CCW | tdd-implementor | Group A (Services) | 0602 | 1d |
| **0606** | MessageService Validation | 1 | CCW | tdd-implementor | Group A (Services) | 0602 | 1d |
| **0607** | ContextService Validation | 1 | CCW | tdd-implementor | Group A (Services) | 0602 | 1d |
| **0608** | OrchestrationService Validation | 1 | CCW | tdd-implementor | Group A (Services) | 0602 | 1d |
| **0609** | Products API Validation | 2 | CCW | api-tester | Group B (APIs) | 0603-0608 | 4h |
| **0610** | Projects API Validation | 2 | CCW | api-tester | Group B (APIs) | 0603-0608 | 4h |
| **0611** | Tasks API Validation | 2 | CCW | api-tester | Group B (APIs) | 0603-0608 | 3h |
| **0612** | Templates API Validation | 2 | CCW | api-tester | Group B (APIs) | 0603-0608 | 4h |
| **0613** | Agent Jobs API Validation | 2 | CCW | api-tester | Group B (APIs) | 0603-0608 | 4h |
| **0614** | Settings API Validation | 2 | CCW | api-tester | Group B (APIs) | 0603-0608 | 3h |
| **0615** | Users API Validation | 2 | CCW | api-tester | Group B (APIs) | 0603-0608 | 3h |
| **0616** | Slash Commands API Validation | 2 | CCW | api-tester | Group B (APIs) | 0603-0608 | 2h |
| **0617** | Messages API Validation | 2 | CCW | api-tester | Group B (APIs) | 0603-0608 | 3h |
| **0618** | Health/Status API Validation | 2 | CCW | api-tester | Group B (APIs) | 0603-0608 | 2h |
| **0619** | Core Workflows E2E Testing | 3 | CLI | integration-tester | Sequential | 0609-0618 | 1d |
| **0620** | Orchestration Workflows E2E Testing | 3 | CLI | integration-tester | Sequential | 0619 | 1d |
| **0621** | Advanced Workflows E2E Testing | 3 | CLI | integration-tester | Sequential | 0620 | 1d |
| **0622** | Self-Healing Decorators Implementation | 4 | CLI | architectural-engineer | Sequential | 0621 | 1d |
| **0623** | Schema Consolidation (Baseline Migration) | 4 | CLI | database-architect | Sequential | 0622 | 1d |
| **0624** | Unit Test Suite Completion | 5 | CLI | tdd-implementor | Sequential | 0623 | 1d |
| **0625** | Integration Test Suite Completion | 5 | CLI | integration-tester | Sequential | 0624 | 1d |
| **0626** | E2E Test Suite & Performance Benchmarks | 5 | CLI | integration-tester | Sequential | 0625 | 1d |
| **0627** | Update CLAUDE.md & System Architecture Docs | 6 | CCW | documentation-specialist | Group C (Docs) | 0626 | 4h |
| **0628** | Create Developer Guides | 6 | CCW | documentation-specialist | Group C (Docs) | 0626 | 4h |
| **0629** | Create User Guides | 6 | CCW | documentation-specialist | Group C (Docs) | 0626 | 4h |
| **0630** | Create Handover 0632 (Completion Report) | 6 | CCW | documentation-specialist | Group C (Docs) | 0626 | 3h |
| **0631** | Update README_FIRST.md & Cleanup | 6 | CCW | documentation-specialist | Group C (Docs) | 0626 | 2h |

---

## TESTING STRATEGY

### Phase 0-2: Establish Baseline & Build Foundation
**Goal**: Understand current state, fix critical blockers (migration order, fresh install)

**Approach**:
1. **Audit** (0600): Catalog everything, establish metrics baseline
2. **Fix** (0601): Fix migration order, test fresh install
3. **Baseline** (0602): Run full test suite, document failures

### Phase 1: Service Layer Validation
**Goal**: 80%+ test coverage on all 6 services, prove multi-tenant isolation

**Approach**:
1. **Unit Tests**: All public methods, error paths, edge cases
2. **Integration Tests**: Service coordination, database transactions, tenant isolation
3. **Coverage**: 80%+ per service (85%+ for critical services like ProductService, OrchestrationService)

**Parallel Execution**: 6 CCW branches (one per service) → Merge locally after each completes

### Phase 2: API Endpoint Validation
**Goal**: All 84+ endpoints tested, authentication verified, response schemas validated

**Approach**:
1. **API Tests**: Happy path + error cases for all endpoints
2. **Authentication**: Verify 401 on missing token, 403 on wrong tenant
3. **Schema Validation**: Pydantic models verified for all responses

**Parallel Execution**: 10 CCW branches (one per endpoint group) → Merge locally after each completes

### Phase 3: Workflow Validation
**Goal**: End-to-end validation of 8 critical user workflows

**Approach**:
1. **Automated E2E Tests**: Selenium/Playwright for UI, API tests for backend
2. **Manual Validation**: Screenshots/recordings for critical workflows
3. **WebSocket Verification**: Real-time event testing

**Sequential Execution**: CLI (requires running backend + DB)

### Phase 4-5: Self-Healing + Comprehensive Testing
**Goal**: Implement future-proofing, achieve >80% overall coverage

**Approach**:
1. **Self-Healing Decorators**: @ensure_table_exists for all critical methods
2. **Baseline Schema**: Consolidate 44 migrations → 1 baseline
3. **Unit Test Completion**: Fix all failures, 80%+ coverage
4. **Integration Test Completion**: 100% passing, multi-tenant verified
5. **E2E + Performance**: All workflows passing, benchmarks met

**Sequential Execution**: CLI (requires DB access, migration manipulation)

### Phase 6: Documentation
**Goal**: Complete, accurate, tested documentation

**Approach**:
1. **Update Existing**: CLAUDE.md, architecture docs, guides
2. **Create New**: Developer guides, completion report
3. **Verify**: Test all code examples, validate all links

**Parallel Execution**: 5 CCW branches (one per doc category)

---

## SUCCESS CRITERIA

### Must Have (Production Blockers)

**Installation & Database**:
- [ ] Fresh install completes in <5 min (target: 2-3 min with baseline schema)
- [ ] All 31 tables created in correct order
- [ ] pg_trgm extension installed automatically
- [ ] Migration chain fixed (20251114 migration at position 1 or consolidated)
- [ ] Baseline schema migration creates identical schema to 44-chain

**Services**:
- [ ] All 6 services have 80%+ test coverage
- [ ] ProductService: CRUD, activate/deactivate, vision upload, config_data persistence
- [ ] ProjectService: CRUD, activate/pause, soft delete, 10-day recovery
- [ ] TaskService: CRUD, project association, status updates
- [ ] MessageService: JSONB message handling, agent communication queue
- [ ] ContextService: Context tracking, succession monitoring
- [ ] OrchestrationService: Mission planning, agent selection, workflow execution

**API Endpoints**:
- [ ] All 84+ endpoints tested (happy path + error cases)
- [ ] Zero HTTP 501 errors
- [ ] Zero HTTP 404 endpoint errors
- [ ] Authentication verified (401 on missing token, 403 on wrong tenant)
- [ ] Response schemas validated (Pydantic models match)

**Workflows**:
- [ ] All 8 critical workflows pass E2E tests
- [ ] Fresh Install → First User → Login → Dashboard
- [ ] Product Creation → Vision Upload → Config Save → Activation
- [ ] Project Creation → Task Assignment → Status Updates → Completion
- [ ] Orchestrator Launch → Mission Assignment → Agent Selection → Workflow Execution
- [ ] Agent Job Lifecycle → Create → Acknowledge → Execute → Complete/Fail
- [ ] Orchestrator Succession → Context Monitoring → Successor Creation → Handover → Launch
- [ ] Template Management → Customize → Save → Apply → Reset
- [ ] Multi-Tenant Isolation → User A Product → User B Cannot Access → Database Verification

**Testing**:
- [ ] Overall test coverage ≥ 80%
- [ ] 100% unit tests passing
- [ ] 100% integration tests passing
- [ ] 100% E2E tests passing
- [ ] Multi-tenant isolation verified (zero leakage)
- [ ] Performance benchmarks met (no >5% degradation)

**Self-Healing**:
- [ ] @ensure_table_exists decorator implemented
- [ ] Applied to all service CRUD methods
- [ ] Table recreation verified (delete table, call method, verify recreated)
- [ ] Baseline schema migration created

**Documentation**:
- [ ] CLAUDE.md updated (Project 600 completion status)
- [ ] Architecture docs updated (service layer, self-healing, baseline schema)
- [ ] Developer guides created (service layer, testing, self-healing, migrations)
- [ ] User guides updated (product management, project management, succession, templates)
- [ ] Completion report created (Handover 0632)

### Should Have (Quality Enhancements)

**Performance**:
- [ ] API p95 response time <100ms
- [ ] API p50 response time <50ms
- [ ] Database query time <10ms (simple), <50ms (complex)
- [ ] WebSocket latency <20ms
- [ ] Test suite execution <10 min (unit + integration), <30 min (full suite)

**Code Quality**:
- [ ] Ruff + Black compliant (no linting errors)
- [ ] Full type hints (mypy clean)
- [ ] No deprecated code warnings
- [ ] Comprehensive error handling

**Documentation**:
- [ ] All code examples tested and working
- [ ] All links verified (no broken links)
- [ ] Screenshots/recordings for critical workflows (optional)
- [ ] CI/CD configuration documented (optional)

---

## PROGRESS TRACKING

**Progress Document**: `handovers/600/progress.json` (updated daily)

**Tracking Metrics**:
- Handover completion (X/32 complete)
- Test pass rate (unit, integration, E2E)
- Coverage percentage (overall, per module)
- Performance benchmarks (fresh install time, API response times)
- Workflow validation status (8/8 complete)

**Update Frequency**: Daily (end of each workday)

**Review Cadence**:
- Daily: Review progress.json, update handover statuses
- Weekly: Review overall phase completion, adjust timeline if needed
- End of project: Final metrics in Handover 0632 completion report

---

## RISK MITIGATION

### Risk 1: Test Failures Overwhelming
**Probability**: High (456 test files, unknown pass rate)
**Impact**: Could delay Phase 5 (days 13-15)

**Mitigation**:
- **0602**: Categorize failures by root cause (prioritize fixes)
- **0603-0608**: Fix service tests early (most critical)
- **0624**: Focus on critical tests first (80/20 rule - fix 20% of tests that cover 80% of code)
- **Fallback**: Extend Phase 5 by 1-2 days if needed

### Risk 2: Migration Order Fix Breaks Existing Installations
**Probability**: Medium (migration reordering is complex)
**Impact**: Could break existing dev environments

**Mitigation**:
- **0601**: Test thoroughly in clean environment (Docker container, VM)
- **Backup**: Full database backup before migration reordering
- **Rollback Plan**: Documented rollback steps in 0601 handover
- **Alternative**: If reordering too risky, consolidate into baseline only (new installs use baseline, existing use 44-chain)

### Risk 3: CCW Parallel Branches Conflict
**Probability**: Low (branches target different files)
**Impact**: Merge conflicts, wasted time

**Mitigation**:
- **File Separation**: Ensure each CCW branch touches different files (services, endpoints, docs)
- **Merge Early**: Merge each completed branch immediately (don't wait for all 6/10 to finish)
- **Conflict Resolution**: Use `git merge --no-ff` for explicit merge commits
- **Fallback**: If conflicts arise, merge sequentially instead of parallel

### Risk 4: Fresh Install Still Fails After 0601
**Probability**: Medium (complex dependencies, pg_trgm extension)
**Impact**: Blocks production deployment

**Mitigation**:
- **0601**: Test on multiple platforms (Windows, Linux, macOS)
- **Docker Test**: Create Dockerfile for clean-room testing
- **Logging**: Add verbose logging to install.py (diagnose failures quickly)
- **Fallback**: Document manual install steps if automated install fails

### Risk 5: Performance Degradation from Baseline Schema
**Probability**: Low (baseline should be faster, not slower)
**Impact**: Slower fresh installs

**Mitigation**:
- **0623**: Benchmark baseline vs 44-chain (should be 2-3x faster)
- **Verification**: Test on same hardware/environment
- **Rollback**: If baseline slower, keep 44-chain as primary (baseline as alternative)

### Risk 6: Self-Healing Decorators Introduce Bugs
**Probability**: Medium (new pattern, untested in production)
**Impact**: Unexpected table recreations, data loss risk

**Mitigation**:
- **0622**: Comprehensive testing (delete table, verify recreation, verify data preservation)
- **Logging**: Verbose logging when tables recreated (audit trail)
- **Opt-In**: Self-healing decorators optional (can disable via config flag)
- **Fallback**: If bugs found, remove decorators (keep baseline schema as primary safety net)

### Risk 7: Timeline Slippage (2-3 weeks → 4+ weeks)
**Probability**: Medium (optimistic timeline, unknown test failures)
**Impact**: Delayed production readiness

**Mitigation**:
- **Daily Tracking**: Update progress.json daily (catch slippage early)
- **Scope Flexibility**: De-prioritize "should have" items if needed (focus on "must have")
- **Parallel Execution**: Maximize CCW parallel branches (compress timeline)
- **Fallback**: If timeline slips, extend by 1 week (acceptable for production-grade quality)

---

## APPENDIX

### A. Database Schema (31 Tables)

**Core Tables** (8):
1. users - User accounts
2. tenants - Multi-tenant isolation
3. products - Product definitions
4. projects - Projects under products
5. tasks - Tasks under projects
6. templates - Agent templates (6 default per tenant)
7. template_archives - Template version history
8. settings - User + admin settings

**MCP Agent Tables** (5):
9. mcp_agent_jobs - Agent job lifecycle
10. agent_messages - Agent communication queue (JSONB)
11. context_usage - Context tracking for succession
12. orchestrator_instances - Orchestrator lineage
13. succession_handovers - Handover summaries

**Additional Tables** (18):
14. agent_job_results
15. agent_logs
16. api_keys
17. audit_logs
18. auth_tokens
19. config_data (JSONB)
20. deleted_projects (soft delete recovery)
21. file_uploads
22. health_checks
23. integration_configs
24. migrations (Alembic tracking)
25. notifications
26. permissions
27. roles
28. sessions
29. webhooks
30. workflow_states
31. websocket_connections

### B. Service Architecture

**6 Services Extracted from God Object**:

1. **ProductService** (`src/giljo_mcp/services/product_service.py`)
   - CRUD operations (create, read, update, delete)
   - Activation/deactivation (single active product enforcement)
   - Vision upload handling
   - config_data persistence

2. **ProjectService** (`src/giljo_mcp/services/project_service.py`)
   - CRUD operations
   - Activation/pause (single active per product)
   - Soft delete (10-day recovery window)
   - Status management

3. **TaskService** (`src/giljo_mcp/services/task_service.py`)
   - CRUD operations
   - Project association
   - Status updates
   - Task completion

4. **MessageService** (`src/giljo_mcp/services/message_service.py`)
   - JSONB message handling
   - Agent-to-agent communication queue
   - Message routing

5. **ContextService** (`src/giljo_mcp/services/context_service.py`)
   - Context usage tracking
   - Succession monitoring (90%+ context budget triggers)
   - Handover summary generation

6. **OrchestrationService** (`src/giljo_mcp/services/orchestration_service.py`)
   - Mission planning (MissionPlanner - condensed missions)
   - Agent selection (AgentSelector - capability matching)
   - Workflow execution (WorkflowEngine - waterfall/parallel coordination)
   - AgentJobManager integration

### C. Migration Chain Analysis

**44 Migration Files** (as of 2025-11-14):
- Position 1-10: Core tables (users, tenants, products, projects)
- Position 11-20: MCP agent tables (mcp_agent_jobs, agent_messages)
- Position 21-30: Template system (templates, template_archives)
- Position 31-40: Context tracking (context_usage, orchestrator_instances)
- Position 41-44: Missing tables (14 tables created by 20251114 migration)

**Issue**: 20251114_create_missing_base_tables.py runs at position 44, but creates tables referenced by earlier migrations (dependency hell).

**Solution**: Move 20251114 to position 1 OR consolidate all 44 into baseline schema.

### D. Testing Commands Reference

```bash
# Fresh Install Test
dropdb giljo_mcp && createdb giljo_mcp
python install.py
# Expected: <5 min, 31 tables created, default tenant + admin user

# Unit Tests (All)
pytest tests/unit/ -v --cov=src/giljo_mcp --cov-report=html
# Expected: 80%+ coverage, 100% passing

# Unit Tests (Single Service)
pytest tests/unit/test_product_service.py -v --cov=src/giljo_mcp/services/product_service.py --cov-report=term-missing
# Expected: 80%+ coverage, all tests pass

# Integration Tests
pytest tests/integration/ -v
# Expected: 100% passing, multi-tenant isolation verified

# E2E Tests
pytest tests/e2e/ -v
# Expected: All 8 workflows pass

# API Tests
pytest tests/api/ -v
# Expected: All 84+ endpoints tested, 100% passing

# Performance Benchmarks
pytest tests/performance/test_benchmarks.py -v
# Expected: Fresh install <5 min, API p95 <100ms, DB queries <10ms

# Full Test Suite
pytest tests/ -v --cov=src/giljo_mcp --cov-report=html
# Expected: 80%+ coverage, 100% passing, <30 min execution
```

### E. CLI vs CCW Execution Examples

**CLI (Local) Execution**:
```bash
# You're in Claude Code CLI
# Just provide instructions for handover:

"Read handovers/600/0600_comprehensive_system_audit.md and execute that handover.
Use deep-researcher agent approach: catalog all 31 tables, analyze 44 migrations,
categorize 84+ endpoints, audit 456 test files. Create audit report in
handovers/600/0600_audit_report.md"
```

**CCW (Cloud) Parallel Execution**:
```bash
# Open Claude Code Web
# Create new branch: 0603-product-service-tests
# Copy prompt from handover file:

"You are the tdd-implementor agent working on Handover 0603: ProductService Validation.

CONTEXT: Read handovers/600/AGENT_REFERENCE_GUIDE.md for universal project context.

TASK:
1. Read src/giljo_mcp/services/product_service.py (analyze all methods)
2. Create comprehensive unit tests: tests/unit/test_product_service.py (80%+ coverage)
3. Create integration tests: tests/integration/test_product_service.py
4. Test multi-tenant isolation (product leakage prevention)

DELIVERABLES:
- Unit tests with 80%+ coverage
- Integration tests
- Test run output in PR description
- Coverage report snippet

Run: pytest tests/unit/test_product_service.py -v --cov=src/giljo_mcp/services/product_service.py --cov-report=term-missing"
```

### F. Progress Tracking JSON Structure

See `handovers/600/progress.json` for full structure.

**Key Fields**:
- `project`: "600"
- `started`: "2025-11-14"
- `status`: "in_progress" | "completed"
- `phases`: Phase completion tracking
- `handovers`: Individual handover status
- `tests`: Test metrics (unit, integration, E2E, coverage)
- `validation`: Workflow validation status

**Update Daily**: Track completion, adjust timeline, identify blockers.

---

## CONCLUSION

Project 600 represents a **zero-compromise restoration and validation** of GiljoAI MCP. By systematically validating the service layer, testing all endpoints, proving workflows end-to-end, and implementing self-healing architecture, we establish a **production-ready foundation** for future growth.

**Timeline**: 2-3 weeks (13-18 days)
**Handovers**: 32 (0600-0631)
**Parallel Execution**: Maximize CCW branches (6+10+5 = 21 parallel executions)
**Quality Gate**: 80%+ test coverage, 100% workflow validation, <5 min fresh install

**Success Metric**: Complete system working flawlessly - no excuses, no compromises, everything tested.

**Next Steps After 600**: Self-healing architecture maturation, SaaS evolution (multi-region, zero-touch deployment), advanced orchestration features (multi-agent coordination, parallel workflows).

---

**Document Control**:
- **Created**: 2025-11-14
- **Last Updated**: 2025-11-14
- **Version**: 1.0
- **Status**: Active - Ready for Execution
- **Owner**: Documentation Manager Agent
- **Reviewed By**: N/A (initial version)
