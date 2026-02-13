# Test Coverage Analysis - Handover 0725

**Date**: 2026-02-07
**Analyzer**: Backend Integration Tester Agent
**Scope**: GiljoAI MCP Codebase Test Coverage Analysis

---

## Executive Summary

**Status**: ⚠️ CRITICAL COVERAGE GAPS DETECTED

- **Total Production Files**: 260 (125 in src/giljo_mcp, 114 in api, ~21 additional)
- **Total Test Files**: 589 test files
- **Coverage Run Status**: ❌ BLOCKED - 6 test files have import errors preventing coverage analysis
- **Estimated Coverage**: Unknown (blocked by import errors)
- **Target Coverage**: >80% overall

---

## 🚨 BLOCKING ISSUES

### 1. Import Errors - Test Collection Failures

**6 test files cannot be imported**, blocking coverage analysis:

#### Exception Name Mismatch (5 files)
**Root Cause**: Tests import `BaseGiljoException` but actual class is `BaseGiljoError`

**Location**: `src/giljo_mcp/exceptions.py:11`
```python
class BaseGiljoError(Exception):  # NOT BaseGiljoException
```

**Affected Test Files**:
1. `tests/services/test_agent_job_manager_exceptions.py`
   - Line 20: `from src.giljo_mcp.exceptions import BaseGiljoException, ResourceNotFoundError`

2. `tests/services/test_product_service_exceptions.py`
   - Line 30: `from src.giljo_mcp.exceptions import BaseGiljoException, ...`

3. `tests/services/test_project_service_exceptions.py`
   - Line 12: `from src.giljo_mcp.exceptions import BaseGiljoException, ...`

4. `tests/services/test_task_service_exceptions.py`
   - Line 18: `from src.giljo_mcp.exceptions import BaseGiljoException, ...`

5. `tests/services/test_user_service.py`
   - Line 32: `from src.giljo_mcp.exceptions import BaseGiljoException, ...`

**Additional Files** (not currently failing but will fail when run):
- `tests/unit/test_task_service.py`
- `tests/unit/test_product_service.py`
- `tests/unit/test_message_service.py`
- `tests/test_exception_handlers.py`

**Impact**: Exception handling tests completely blocked. Cannot verify exception-based error handling migration (0480 series).

---

#### WebSocket Manager Import Error (1 file)
**Root Cause**: Tests import `WebSocketManager` class that doesn't exist

**Location**: `tests/integration/test_websocket_broadcast.py:25`
```python
from api.websocket_manager import ConnectionInfo, WebSocketManager
# ERROR: WebSocketManager does not exist in api.websocket_manager
```

**What Exists**: `api/websocket_manager.py` only exports `ConnectionInfo` dataclass
**What's Missing**: `WebSocketManager` class (likely moved to different module)

**Actual WebSocket Module Structure**:
- `api/websocket.py` - Main WebSocket handling
- `api/websocket_service.py` - WebSocket service layer
- `api/websocket_manager.py` - Compatibility shim (ConnectionInfo only)
- `api/dependencies/websocket.py` - WebSocket dependencies

**Impact**: WebSocket broadcast integration tests blocked. Cannot verify real-time event propagation.

---

### 2. Skipped Tests - Technical Debt

**92 tests are skipped** across the codebase. Breakdown by category:

#### Production Bugs (5 skipped tests)
Critical production code blocked by bugs:

1. **UnboundLocalError in project_service.py** (2 tests)
   - `tests/api/test_projects_api.py:695` - "Production bug: UnboundLocalError for 'total_jobs' in project_service.py:1545"
   - `tests/api/test_projects_api.py:725` - Same issue
   - **Impact**: Project summary endpoint cannot be tested

2. **Complete endpoint validation errors** (1 test)
   - `tests/api/test_projects_api.py:768` - "Production bug: Complete endpoint validation causes 422 for valid projects"
   - **Impact**: Project completion workflow untested

3. **Message Model Refactoring** (2 tests)
   - `tests/repositories/test_statistics_repository.py:355` - "BUG: Message model doesn't have from_agent field (removed in Handover 0116)"
   - `tests/repositories/test_statistics_repository.py:370` - Same issue
   - **Impact**: Statistics aggregation untested for message sources

---

#### MCPAgentJob Refactoring Needed (8 tests)
**TODO(0127a-2)**: Comprehensive refactoring needed for MCPAgentJob model

- `tests/integration/test_backup_integration.py:21`
- `tests/integration/test_hierarchical_context.py:14`
- `tests/integration/test_message_queue_integration.py:10`
- `tests/integration/test_orchestrator_template.py:15`
- `tests/integration/test_upgrade_validation.py:15`
- `tests/performance/test_database_benchmarks.py:36`

**Impact**: Integration tests and performance benchmarks blocked. Cannot verify:
- Backup/restore functionality
- Context hierarchy
- Message queue integration
- Orchestrator template generation
- Database upgrade validation
- Performance characteristics

---

#### Template System Tests (21 skipped tests)
**Reason**: "Templates are system-managed and cannot be modified"

All in `tests/api/test_templates_api.py`:
- Lines 345, 352, 357, 362, 367, 372 - Update/delete operations
- Lines 411, 416, 421, 426, 433, 438, 443, 450, 455 - History/restore operations
- Lines 501, 600, 607, 624, 662, 669 - Diff/cache operations

**Analysis**: Tests are correctly skipped (system templates are immutable). However, **no alternative tests verify template read-only enforcement**.

**Gap**: Template immutability is enforced by skipping tests, not by testing enforcement logic.

---

#### Test Infrastructure Issues (11 tests)
**Cookie persistence/auth issues**:

All in `tests/api/test_tasks_api.py`:
- Lines 499, 598, 646, 700, 839 - "Test client cookie persistence - auth test infrastructure issue"

**Routing issues**:
- Lines 857, 893, 915, 981 - "Endpoint routing issue - /summary/ returns 404"

**Isolation issues**:
- Line 578 - "Admin user fixture different tenant - test isolation issue"
- Line 305 - "Projects API endpoint issue - testing task creation only"

**Impact**: Task API endpoints have >10 tests skipped. Task management workflow coverage incomplete.

---

#### Architecture Changes (14 tests)
**Features removed or refactored**:

1. **CLI Mode Rules** (`test_orchestration_service_cli_rules.py`):
   - Lines 258, 320, 376, 421, 455, 488, 608, 636
   - Reason: Fields renamed/removed in implementation
   - Fields: `spawning_examples`, `agent_display_name_usage`, `forbidden_patterns`, `lifecycle_flow`

2. **Cancel Endpoint Removed** (`test_agent_jobs_api.py`):
   - Lines 726, 869 - "cancel endpoint removed - passive HTTP architecture"

3. **Report Progress Changed** (`test_orchestration_service_context.py`):
   - Lines 42, 53 - "report_progress() functionality changed - uses TodoWriteRepository instead of job_metadata"

4. **Message Service Contract** (`test_message_service_contract.py`):
   - Lines 406, 550 - Session isolation issues

5. **Product Service Consolidation** (`test_orchestration_service_consolidation.py`):
   - Lines 81, 157 - Consolidation logic changed

**Impact**: Tests track technical debt from architecture evolution. Should be updated or removed.

---

#### WebSocket Tests (6 tests)
**Reason**: "WebSocket tests require full app setup - run in integration tests"

- `tests/api/test_depth_controls.py:257`
- `tests/api/test_simple_handover.py:427`
- `tests/api/test_unified_message_send.py:379`
- `tests/test_agent_templates_api.py:598, 604, 613`

**Impact**: WebSocket event testing deferred to integration suite. Need to verify integration tests cover these scenarios.

---

#### Security Tests (4 tests)
**CSRF disabled** (`test_security_comprehensive.py`):
- Lines 214, 220, 227 - "CSRF middleware disabled by default - requires frontend integration"

**Rate limiting disabled**:
- Line 80 - "Rate limiting disabled in test environment to avoid flaky tests"

**Impact**: Security features disabled in tests. No verification of CSRF protection or rate limiting in production.

---

#### Installer Tests (8 tests)
**Reason**: "Not all components available"

All in `tests/installer/`:
- `integration/test_installation_flow.py:25`
- `unit/test_config_manager.py:32`
- `unit/test_docker.py:24`
- `unit/test_health_checker.py:22`
- `unit/test_postgresql.py:24`
- `unit/test_profile.py:31`
- `unit/test_redis.py:24`
- `unit/test_service_manager.py:23`

**Impact**: Installation flow completely untested. Cannot verify one-liner installation (Handover 0100).

---

#### E2E/Integration Tests (3 tests)
- `tests/integration/test_json_mission_generation.py:466` - "E2E MCP tool tests require full database setup"
- `tests/integration/test_orchestration_e2e.py:130, 146` - Database injection issues

**Impact**: End-to-end workflows untested. Cannot verify real-world agent orchestration.

---

#### Refactored/Deprecated Tests (5 tests)
- `tests/tools/test_context_depth_config.py:34, 68, 88, 108` - "Refactored in Handover 0246b - internal functions removed"
- `tests/unit/test_thin_prompt_generator_execution_mode.py:340, 368` - Execution mode changes
- `tests/integration/test_product_ws_event.py:111` - Product WebSocket events
- `tests/unit/test_frontend_config_service.py:148` - "JavaScript tests - documentation only"

---

## 📊 Coverage Gaps by Category

### 1. Critical Code Paths (<80% Coverage - ESTIMATED)

⚠️ **Cannot verify due to import errors, but based on skipped tests:**

#### Authentication & Authorization
**Production Files**:
- `api/auth_utils.py`
- `api/endpoints/auth.py`
- `api/endpoints/auth_models.py`
- `api/endpoints/auth_pin_recovery.py`
- `api/middleware/auth.py`
- `api/middleware/auth_rate_limiter.py`
- `src/giljo_mcp/auth/dependencies.py`
- `src/giljo_mcp/services/auth_service.py`

**Test Files**:
- `tests/api/test_auth_org_endpoints.py`
- `tests/integration/test_auth.py`
- `tests/integration/test_auth_endpoints.py`
- `tests/integration/test_auth_org_flow.py`
- `tests/integration/test_server_mode_auth.py`
- `tests/services/test_auth_service.py`
- `tests/services/test_authservice_org_integration.py`
- `tests/unit/test_auth_manager_unified.py`
- `tests/unit/test_websocket_auth_unified.py`

**Gaps**:
- ✅ Auth service tests exist
- ❌ Rate limiting tests skipped (line 80)
- ❌ CSRF protection tests skipped (lines 214, 220, 227)
- ❌ PIN recovery flow coverage unknown

---

#### Multi-Tenant Isolation
**Production Files**:
- All database queries in `src/giljo_mcp/repositories/`
- All service layer methods in `src/giljo_mcp/services/`
- All API endpoints in `api/endpoints/`

**Test Files**:
- `tests/integration/test_multi_tenant_isolation.py`
- `tests/integration/test_product_isolation_complete.py`
- `tests/integration/test_user_tenant_isolation.py`
- `tests/integration/test_field_priority_tenant_isolation.py`
- `tests/services/test_tenant_isolation_services.py`
- `tests/tools/test_tenant_isolation_mcp_tools.py`
- `tests/test_multi_tenant_comprehensive.py`
- `tests/test_tenant_isolation.py`

**Gaps**:
- ✅ Comprehensive tenant isolation tests exist (15 test files)
- ⚠️ Need to verify ALL database queries filter by tenant_key
- ⚠️ Need to verify ALL MCP tools enforce tenant isolation

---

#### WebSocket Real-Time Events
**Production Files**:
- `api/websocket.py`
- `api/websocket_service.py`
- `api/websocket_manager.py`
- `api/websocket_event_listener.py`
- `api/dependencies/websocket.py`

**Test Files**:
- ❌ `tests/integration/test_websocket_broadcast.py` - BLOCKED (import error)
- `tests/websocket/test_message_counter_events.py`
- `tests/test_ws_auth_simple.py`
- `tests/performance/test_websocket_performance.py`

**Gaps**:
- ❌ WebSocket broadcast tests blocked by import error
- ❌ 6 WebSocket tests skipped (deferred to integration)
- ⚠️ Message counter events have 1 skipped test (line 451)

---

#### Database Operations
**Production Files**:
- `src/giljo_mcp/database.py`
- `src/giljo_mcp/models.py` (32 tables)
- `src/giljo_mcp/repositories/*.py` (20+ repositories)

**Test Files**:
- `tests/repositories/test_*.py` (multiple)
- `tests/integration/test_handover_0035_database_schema.py`
- `tests/performance/test_database_benchmarks.py` - SKIPPED

**Gaps**:
- ❌ Database benchmarks skipped (MCPAgentJob refactoring)
- ❌ Schema CHECK constraints not tested (SQLite limitation, line 125)
- ⚠️ Repository tests exist but coverage percentage unknown

---

#### MCP Tools
**Production Files**:
- `src/giljo_mcp/tools/*.py` (20+ tools)
- Tool categories: agent, context, message, project, task, product, orchestration

**Test Files**:
- `tests/tools/test_*.py` (multiple)
- `tests/tools/test_tenant_isolation_mcp_tools.py`
- `tests/integration/test_json_mission_generation.py` - SKIPPED

**Gaps**:
- ❌ E2E MCP tool tests skipped (line 466)
- ❌ Context depth config tests skipped (4 tests, Handover 0246b refactoring)
- ⚠️ Individual tool tests exist but integration coverage unknown

---

### 2. Services Layer Coverage

**Production Services** (18 files):
1. `agent_job_manager.py`
2. `auth_service.py`
3. `claude_config_manager.py`
4. `config_service.py`
5. `consolidation_service.py`
6. `context_service.py`
7. `git_service.py`
8. `message_service.py`
9. `orchestration_service.py`
10. `org_service.py`
11. `product_service.py`
12. `project_service.py`
13. `serena_detector.py`
14. `settings_service.py`
15. `task_service.py`
16. `template_service.py`
17. `user_service.py`
18. `vision_summarizer.py`

**Test Files** (54 service test files):
- See full list in "List service test files" section

**Coverage Status**:
- ✅ All services have test files
- ❌ 6 exception test files blocked by import errors
- ⚠️ Exception handling migration (0480 series) cannot be verified

**Service-Specific Gaps**:

1. **agent_job_manager.py**:
   - ❌ `test_agent_job_manager_exceptions.py` - BLOCKED (BaseGiljoException import)
   - ✅ `test_agent_job_manager_mission_ack.py` - OK

2. **product_service.py**:
   - ❌ `test_product_service_exceptions.py` - BLOCKED (BaseGiljoException import)
   - ✅ Multiple other product service tests exist

3. **project_service.py**:
   - ❌ `test_project_service_exceptions.py` - BLOCKED (BaseGiljoException import)
   - ❌ 2 tests blocked by production bug (UnboundLocalError)

4. **task_service.py**:
   - ❌ `test_task_service_exceptions.py` - BLOCKED (BaseGiljoException import)

5. **user_service.py**:
   - ❌ `test_user_service.py` - BLOCKED (BaseGiljoException import)

---

### 3. API Endpoints Coverage

**Production Endpoints** (69 files across categories):
- Admin, agent management, auth, configuration, downloads
- MCP HTTP, messages, network, orchestration
- Organizations (3 files), products (6 files), projects (6 files)
- Settings, statistics, tasks, templates (5 files)
- Users, vision documents, WebSocket bridge

**Test Files**:
- `tests/api/test_*.py` (50+ API test files)

**Coverage Gaps**:

1. **Templates** (5 files):
   - Production: `api/endpoints/templates/*.py`
   - Tests: `tests/api/test_templates_api.py` (21 tests skipped)
   - Gap: No tests verify template immutability enforcement

2. **Tasks**:
   - Production: `api/endpoints/tasks.py`
   - Tests: `tests/api/test_tasks_api.py` (11 tests skipped)
   - Gap: Cookie persistence issues block auth testing

3. **Projects** (6 files):
   - Production: `api/endpoints/projects/*.py`
   - Tests: `tests/api/test_projects_api.py` (3 tests blocked by bugs)
   - Gap: Summary/completion endpoints untested

4. **Agent Jobs** (11 files):
   - Production: `api/endpoints/agent_jobs/*.py`
   - Tests: `tests/api/test_agent_jobs_api.py` (2 tests skipped - cancel removed)
   - Gap: Cancel endpoint removed but tests not updated

5. **Auth** (3 files):
   - Production: `api/endpoints/auth*.py`
   - Tests: Multiple auth test files
   - Gap: Rate limiting and CSRF disabled in tests

---

### 4. Production Files Potentially Missing Tests

**High Priority** (based on file analysis, needs coverage.json to confirm):

1. **Middleware**:
   - `api/middleware/auth_rate_limiter.py` - Rate limiting logic
   - `api/middleware/input_validator.py` - Input validation
   - Gap: Rate limiting tests skipped

2. **Broker**:
   - `api/broker/__init__.py` - Message broker
   - Gap: No visible test file for broker module

3. **Repositories** (20+ files):
   - `src/giljo_mcp/repositories/*.py`
   - Tests exist but coverage percentage unknown
   - Gap: `test_statistics_repository.py` has 2 tests blocked by bug

4. **MCP Tools**:
   - `src/giljo_mcp/tools/context_tools/*.py`
   - Gap: Context depth config tests skipped (4 tests)

5. **Prompt Generation**:
   - `src/giljo_mcp/thin_prompt_generator.py`
   - `src/giljo_mcp/mission_planner.py`
   - Tests exist but execution mode tests have 2 skipped

6. **File Staging**:
   - `src/giljo_mcp/file_staging.py`
   - Gap: No visible test file

7. **Setup**:
   - `src/giljo_mcp/setup/state_manager.py`
   - Gap: Installer tests skipped (8 tests)

---

## 🔍 Test Quality Issues

### 1. Tests Importing Non-Existent Modules

**Critical**: 9 test files import `BaseGiljoException` which doesn't exist:
- Should import `BaseGiljoError` from `src/giljo_mcp/exceptions.py`

**Recommendation**: Search and replace across test suite:
```python
# WRONG
from src.giljo_mcp.exceptions import BaseGiljoException

# CORRECT
from src.giljo_mcp.exceptions import BaseGiljoError
```

---

### 2. Tests Skipped for Production Bugs

**5 tests document production bugs**:

1. `project_service.py:1545` - UnboundLocalError for 'total_jobs'
2. Project complete endpoint validation causes 422 for valid projects
3. Message model missing 'from_agent' field (removed in Handover 0116)

**Recommendation**: Fix production bugs, then re-enable tests.

---

### 3. Tests Skipped for Test Infrastructure Issues

**11 tests skipped due to test infrastructure**:
- Cookie persistence issues (5 tests)
- Endpoint routing issues (4 tests)
- Tenant isolation in fixtures (2 tests)

**Recommendation**: Fix test infrastructure before coverage analysis.

---

### 4. Outdated Tests (Technical Debt)

**14+ tests skipped for architecture changes**:
- CLI mode rules refactored
- Cancel endpoint removed
- Report progress changed
- Fields renamed/removed

**Recommendation**: Update tests or remove if features deprecated.

---

### 5. Test Collection Warnings

**3 warnings** about classes with `__init__` constructors:
- `tests/installer/fixtures/test_configs.py:12` - `TestEnvironment`
- `tests/test_discovery_comprehensive.py:20` - `TestResults`
- `tests/test_scenarios.py:18` - `TestScenarioRunner`

**Issue**: Pytest cannot collect these as test classes
**Recommendation**: Remove `@dataclass` or rename classes (don't start with "Test")

---

## 📋 Recommendations

### Immediate Actions (Unblock Coverage Analysis)

1. **Fix Import Errors** (CRITICAL):
   ```bash
   # Search and replace in 9 test files
   find tests/ -name "*.py" -exec sed -i 's/BaseGiljoException/BaseGiljoError/g' {} +
   ```

2. **Fix WebSocket Import** (CRITICAL):
   - Investigate `WebSocketManager` location
   - Update `tests/integration/test_websocket_broadcast.py` imports
   - Or create compatibility shim in `api/websocket_manager.py`

3. **Re-run Coverage**:
   ```bash
   pytest tests/ --cov=src/giljo_mcp --cov=api --cov-report=term-missing --cov-report=json --cov-report=html
   ```

---

### Short-Term Actions (Fix Production Bugs)

4. **Fix UnboundLocalError** (HIGH):
   - File: `project_service.py:1545`
   - Issue: 'total_jobs' variable referenced before assignment
   - Re-enable 2 tests in `test_projects_api.py`

5. **Fix Project Complete Validation** (HIGH):
   - Endpoint: Project complete endpoint
   - Issue: Validation causes 422 for valid projects
   - Re-enable 1 test in `test_projects_api.py`

6. **Fix Statistics Repository** (MEDIUM):
   - File: Message model refactoring (Handover 0116)
   - Issue: 'from_agent' field removed but statistics still references it
   - Re-enable 2 tests in `test_statistics_repository.py`

---

### Medium-Term Actions (Technical Debt)

7. **Update Architecture Tests** (MEDIUM):
   - 14 tests skipped for architecture changes
   - Update or remove outdated tests
   - Document architecture evolution

8. **Fix Test Infrastructure** (MEDIUM):
   - Cookie persistence issues (5 tests)
   - Endpoint routing issues (4 tests)
   - Tenant isolation in fixtures (2 tests)

9. **Complete MCPAgentJob Refactoring** (LOW):
   - TODO(0127a-2): 8 tests blocked
   - Integration tests and performance benchmarks

10. **Installer Testing** (LOW):
    - 8 installer tests skipped
    - One-liner installation (Handover 0100) untested

---

### Long-Term Actions (Coverage Improvement)

11. **Security Testing** (HIGH):
    - Re-enable rate limiting tests (currently skipped to avoid flaky tests)
    - Re-enable CSRF tests (requires frontend integration)
    - Add production-like security testing

12. **WebSocket Coverage** (HIGH):
    - Fix WebSocketManager import
    - Re-enable 6 skipped WebSocket tests
    - Add integration tests for real-time events

13. **Template Immutability Testing** (MEDIUM):
    - 21 tests correctly skipped (templates immutable)
    - Add tests that verify immutability enforcement
    - Test that update/delete operations return proper errors

14. **E2E Testing** (MEDIUM):
    - Fix database injection issues (2 tests)
    - Re-enable MCP tool E2E tests
    - Add orchestrator end-to-end workflows

15. **Missing Test Files** (LOW):
    - Identify production files with <80% coverage (needs coverage.json)
    - Create test files for untested modules:
      - `api/broker/__init__.py`
      - `src/giljo_mcp/file_staging.py`
      - Any others identified by coverage report

---

## 📈 Coverage Metrics (Estimated)

**Cannot provide accurate metrics due to import errors blocking test execution.**

**Estimated based on test file analysis**:
- Services Layer: 75-85% (54 test files, 6 blocked)
- API Endpoints: 70-80% (50+ test files, 21-41 skipped)
- Multi-Tenant Isolation: 85-95% (15 dedicated test files)
- Authentication: 80-90% (16 test files, security tests skipped)
- WebSocket: 60-70% (blocked by import error)
- MCP Tools: 75-85% (multiple test files, E2E skipped)
- Database/Repositories: 70-80% (benchmarks skipped)

**Overall Estimate**: 70-80% (below 80% target)

---

## 🎯 Priority Matrix

| Priority | Category | Impact | Effort | Recommendation |
|----------|----------|--------|--------|----------------|
| **P0** | Fix import errors | CRITICAL | 1 hour | Fix immediately |
| **P1** | Production bugs (3) | HIGH | 4 hours | Fix this week |
| **P2** | Test infrastructure | MEDIUM | 8 hours | Fix next sprint |
| **P3** | Security testing | HIGH | 16 hours | Plan for next release |
| **P4** | Architecture tests | LOW | 4 hours | Update or remove |
| **P5** | MCPAgentJob refactoring | MEDIUM | 40 hours | Defer to v3.4 |

---

## 📝 Next Steps

1. **Unblock Coverage** (1-2 hours):
   - Fix 9 BaseGiljoException imports
   - Fix WebSocketManager import
   - Re-run coverage analysis

2. **Generate Accurate Report** (30 minutes):
   - Run: `pytest tests/ --cov=src/giljo_mcp --cov=api --cov-report=html`
   - Analyze coverage.json
   - Identify files with <80% coverage

3. **Fix Critical Production Bugs** (4-8 hours):
   - UnboundLocalError in project_service.py
   - Project complete validation
   - Statistics repository message model

4. **Create Handover for Fixes** (1 hour):
   - Document fixes needed
   - Assign to appropriate agent (TDD Implementor)
   - Track progress

---

## 📚 Appendix

### Skipped Tests Summary

| Category | Count | Examples |
|----------|-------|----------|
| Production Bugs | 5 | UnboundLocalError, validation errors |
| MCPAgentJob Refactoring | 8 | Integration, performance tests |
| Template System | 21 | Update/delete immutable templates |
| Test Infrastructure | 11 | Cookie persistence, routing |
| Architecture Changes | 14 | CLI rules, cancel endpoint |
| WebSocket | 6 | Full app setup required |
| Security | 4 | CSRF, rate limiting |
| Installer | 8 | Component availability |
| E2E | 3 | Database setup |
| Refactored | 5 | Handover 0246b changes |
| Platform-Specific | 3 | Windows/Linux/macOS |
| Other | 4 | JavaScript, session isolation |
| **TOTAL** | **92** | Across 589 test files |

---

### Import Error Details

**9 files importing BaseGiljoException** (should be BaseGiljoError):
1. tests/services/test_agent_job_manager_exceptions.py
2. tests/services/test_product_service_exceptions.py
3. tests/services/test_project_service_exceptions.py
4. tests/services/test_task_service_exceptions.py
5. tests/services/test_user_service.py
6. tests/unit/test_task_service.py
7. tests/unit/test_product_service.py
8. tests/unit/test_message_service.py
9. tests/test_exception_handlers.py

**1 file importing WebSocketManager** (doesn't exist):
1. tests/integration/test_websocket_broadcast.py

---

### Production File Count

- **src/giljo_mcp**: 125 Python files (excluding __init__.py)
- **api**: 114 Python files (excluding __init__.py)
- **Total**: ~260 production files

### Test File Count

- **tests/**: 589 test files (test_*.py pattern)

### Test-to-Production Ratio

- **Ratio**: 2.27:1 (589 tests / 260 production files)
- **Interpretation**: Good test coverage breadth, but import errors and skipped tests reduce effectiveness

---

## ✅ Conclusion

**The GiljoAI MCP codebase has extensive test coverage breadth (589 test files for 260 production files), but test effectiveness is severely degraded by:**

1. **6 import errors** blocking exception handling tests
2. **92 skipped tests** representing technical debt
3. **5 production bugs** preventing critical tests from running
4. **11 test infrastructure issues** blocking API endpoint tests

**Immediate action required**: Fix import errors to unblock coverage analysis, then address production bugs and test infrastructure issues.

**Target**: Achieve >80% coverage overall with all critical paths (auth, multi-tenant isolation, WebSocket, database) at >90% coverage.

---

**END OF REPORT**
