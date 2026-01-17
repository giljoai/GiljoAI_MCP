# Handover 0420c: Update Core Files and Tests

**Date**: 2026-01-17
**Agent**: Documentation Manager
**Series**: Legacy Agent Coordination Removal (Part 3 of 4)
**Status**: COMPLETE (Planning document - work executed)
**Prerequisites**: 0420b MUST be complete

---

## 1. Objective

Migrate all callers from the deleted `agent_job_manager.py` to `OrchestrationService` and fix all broken tests. This is the BULK of the migration work, involving 9 files and complete test suite restoration.

**Success Criteria**:
- ✅ ALL tests pass (100% green)
- ✅ No imports of deleted `agent_job_manager.py` remain
- ✅ Coverage maintained >80% across all modified modules
- ✅ All function-level behavioral changes validated

**What This Achieves**:
- Completes the service layer migration for agent job management
- Restores test suite integrity after 0420b deletion
- Validates OrchestrationService as authoritative source for job lifecycle operations
- Eliminates technical debt from dual code paths

---

## 2. Context & Background

### Series Overview

This is **Part 3 of 4** in the Legacy Agent Coordination Removal series:

- **0420a**: Analysis and risk assessment (COMPLETE)
- **0420b**: Delete `agent_job_manager.py` and verify cascade (COMPLETE)
- **0420c**: Update core files and fix tests (THIS HANDOVER)
- **0420d**: Final cleanup and verification

### Problem Statement

After 0420b deleted `src/giljo_mcp/agent_job_manager.py`, we have:

1. **9 files with broken imports** requiring migration to `OrchestrationService`
2. **25+ broken tests** expecting old AgentJobManager API
3. **Function-level behavioral differences** between old and new implementations that require careful test updates

### Why This Matters

The deleted `agent_job_manager.py` was a 800+ line legacy module that duplicated functionality now in `OrchestrationService`. This handover completes the migration by:

- **Updating all callers** to use the service layer pattern
- **Fixing behavioral mismatches** in tests (validation, TODO tracking, async patterns)
- **Maintaining test coverage** while eliminating technical debt

### Architectural Context

**Service Layer Pattern** (established in Handovers 0120-0130):
```python
# OLD (deleted in 0420b)
from giljo_mcp.agent_job_manager import AgentJobManager
manager = AgentJobManager()
await manager.complete_job(job_id, result, tenant_key)

# NEW (OrchestrationService)
from giljo_mcp.services.orchestration_service import OrchestrationService
service = OrchestrationService(db_session)
await service.complete_job(job_id, result, tenant_key)
```

**Key Differences**:
- Service layer uses dependency injection (`AsyncSession`)
- Service layer has enhanced validation (stricter error handling)
- Service layer tracks TODO items for progress reporting
- Service layer uses Pydantic schemas for request/response

---

## 3. Scope of Work

### Files to HEAVILY MODIFY (2 files)

Core orchestration files requiring significant refactoring:

| File | Lines | Changes Required | Risk Level |
|------|-------|------------------|------------|
| `src/giljo_mcp/orchestrator.py` | ~800 | Remove import (line 26)<br>Migrate usage (line 115)<br>Add AsyncSession injection | HIGH |
| `src/giljo_mcp/workflow_engine.py` | ~500 | Remove import (line 25)<br>Migrate usage (line 61)<br>Convert to async service calls | HIGH |

### Files to MODIFY (7 files)

| File | Changes Required | Risk Level |
|------|------------------|------------|
| `src/giljo_mcp/tools/agent_job_status.py` | Remove import (line 26)<br>Use OrchestrationService | MEDIUM |
| `tests/test_orchestrator_routing.py` | Remove 3 deprecated test functions | LOW |
| `tests/test_agent_orchestrator_communication_tools.py` | Migrate to service layer mocks | HIGH |
| `tests/test_agent_job_status_tool.py` | Migrate to OrchestrationService | HIGH |
| `tests/integration/test_multi_tool_orchestration.py` | Migrate to async service | MEDIUM |
| `tests/websocket/test_mission_tracking_events.py` | Migrate to OrchestrationService | MEDIUM |
| `tests/services/test_agent_job_manager_mission_ack.py` | Fix import path | LOW |

### Function-Level Risk Assessment

**HIGH RISK FUNCTIONS** (behavioral changes):

| Function | Old Behavior | New Behavior | Test Impact |
|----------|--------------|--------------|-------------|
| `complete_job()` | Simple status update | Validation + status update | Tests expecting simple success will fail |
| `report_progress()` | Basic progress tracking | TODO tracking required | Tests need `todo_items` parameter |

**MEDIUM RISK FUNCTIONS** (schema changes):

| Function | Change Impact | Test Updates Required |
|----------|---------------|----------------------|
| `report_error()` | Already sets blocked (Handover 0416) | Tests updated in 0416 - verify compatibility |
| `get_pending_jobs()` | Schema differences (Pydantic) | Minor mock updates for return structure |

**LOW RISK FUNCTIONS** (simple migrations):

| Function | Change Impact | Test Updates Required |
|----------|---------------|----------------------|
| `acknowledge_job()` | Direct API match | Update import only |
| `get_agent_mission()` | Direct API match | Update import only |

### Test Impact Summary

| Category | Files | Impact Level | Estimated Time |
|----------|-------|--------------|----------------|
| Direct tool tests | 5 files | HIGH - Must rewrite | 2-3 hours |
| Integration tests | 12 files | MEDIUM - Update mocks | 1-2 hours |
| Service tests | 8 files | LOW - Already test service | 30 min |

---

## 4. Implementation Plan

### Phase 4: Update Core Files (2-3 hours)

**CRITICAL**: Run tests after EACH file modification to detect cascading failures early.

#### Step 4.1: Update `orchestrator.py`

**File**: `src/giljo_mcp/orchestrator.py`

**Changes**:
```python
# Line 26 - REMOVE
from giljo_mcp.agent_job_manager import AgentJobManager

# ADD
from giljo_mcp.services.orchestration_service import OrchestrationService

# Line 115 - MODIFY
# OLD
manager = AgentJobManager()
await manager.complete_job(job_id, result, tenant_key)

# NEW
async with get_db_session() as session:
    service = OrchestrationService(session)
    await service.complete_job(job_id, result, tenant_key)
```

**Run Tests**: `pytest tests/test_orchestrator_routing.py -v`

#### Step 4.2: Update `workflow_engine.py`

**File**: `src/giljo_mcp/workflow_engine.py`

**Changes**:
```python
# Line 25 - REMOVE
from giljo_mcp.agent_job_manager import AgentJobManager

# ADD
from giljo_mcp.services.orchestration_service import OrchestrationService

# Line 61 - MODIFY (convert to async service)
# OLD
manager = AgentJobManager()
result = manager.get_workflow_status(project_id, tenant_key)

# NEW
async with get_db_session() as session:
    service = OrchestrationService(session)
    result = await service.get_workflow_status(project_id, tenant_key)
```

**Run Tests**: `pytest tests/integration/test_workflow_engine.py -v`

#### Step 4.3: Update `agent_job_status.py`

**File**: `src/giljo_mcp/tools/agent_job_status.py`

**Changes**:
```python
# Line 26 - REMOVE
from giljo_mcp.agent_job_manager import AgentJobManager

# ADD
from giljo_mcp.services.orchestration_service import OrchestrationService

# Update all tool functions to use OrchestrationService
# Example pattern:
async def complete_job_tool(job_id: str, result: dict, tenant_key: str):
    async with get_db_session() as session:
        service = OrchestrationService(session)
        return await service.complete_job(job_id, result, tenant_key)
```

**Run Tests**: `pytest tests/test_agent_job_status_tool.py -v`

---

### Phase 5: Update Tests (3-4 hours)

**CRITICAL**: Each test file has specific behavioral expectations that must be preserved.

#### Step 5.1: Remove Deprecated Tests

**File**: `tests/test_orchestrator_routing.py`

**Changes**:
- Remove 3 deprecated test functions that tested AgentJobManager directly
- Keep tests that verify orchestrator routing logic (still valid)
- Update imports if any reference old manager

**Run Tests**: `pytest tests/test_orchestrator_routing.py -v`

#### Step 5.2: Migrate Communication Tools Tests

**File**: `tests/test_agent_orchestrator_communication_tools.py`

**Changes**:
```python
# Update fixtures
@pytest.fixture
async def orchestration_service(db_session):
    return OrchestrationService(db_session)

# Update tests to use service
async def test_complete_job(orchestration_service):
    result = await orchestration_service.complete_job(
        job_id="test-job",
        result={"status": "success"},
        tenant_key="tenant_abc"
    )
    assert result["status"] == "completed"
```

**Behavioral Changes to Handle**:
- `complete_job()` now validates result structure (must be dict)
- `report_progress()` now requires `todo_items` parameter for TODO tracking

**Run Tests**: `pytest tests/test_agent_orchestrator_communication_tools.py -v`

#### Step 5.3: Migrate Job Status Tool Tests

**File**: `tests/test_agent_job_status_tool.py`

**Changes**:
- Update mocks to use OrchestrationService
- Update test expectations for Pydantic schemas
- Verify error handling matches new validation logic

**Run Tests**: `pytest tests/test_agent_job_status_tool.py -v`

#### Step 5.4: Migrate Integration Tests

**File**: `tests/integration/test_multi_tool_orchestration.py`

**Changes**:
- Convert synchronous calls to async service calls
- Update fixtures to inject AsyncSession
- Verify end-to-end workflow still functions

**Run Tests**: `pytest tests/integration/test_multi_tool_orchestration.py -v`

#### Step 5.5: Migrate WebSocket Tests

**File**: `tests/websocket/test_mission_tracking_events.py`

**Changes**:
- Update mocks to use OrchestrationService
- Verify WebSocket events still fire correctly
- Test event payload structure matches Pydantic schemas

**Run Tests**: `pytest tests/websocket/test_mission_tracking_events.py -v`

#### Step 5.6: Fix Import Path

**File**: `tests/services/test_agent_job_manager_mission_ack.py`

**Changes**:
```python
# REMOVE
from giljo_mcp.agent_job_manager import AgentJobManager

# ADD
from giljo_mcp.services.orchestration_service import OrchestrationService

# Update test class/fixtures
class TestOrchestrationServiceMissionAck:
    # ... tests remain functionally identical
```

**Run Tests**: `pytest tests/services/test_agent_job_manager_mission_ack.py -v`

---

### Phase 6: Full Test Suite Validation

**Run Complete Test Suite**:
```bash
pytest tests/ --cov=src/giljo_mcp --cov-report=html -v
```

**Success Criteria**:
- ✅ ALL tests pass (100% green)
- ✅ Coverage remains >80%
- ✅ No import errors for deleted `agent_job_manager.py`

**If Tests Fail**:
1. Identify failing test category (tool/integration/service)
2. Check for behavioral mismatches (validation, schemas, async)
3. Update test expectations OR fix service implementation
4. Re-run tests for that category
5. Repeat until green

---

## 5. Technical Details

### Service Layer Pattern

**Dependency Injection**:
```python
# Core pattern for all service usage
from giljo_mcp.services.orchestration_service import OrchestrationService
from giljo_mcp.database import get_db_session

async def some_orchestration_operation():
    async with get_db_session() as session:
        service = OrchestrationService(session)
        result = await service.complete_job(job_id, result, tenant_key)
        await session.commit()  # Explicit transaction control
```

### Key Behavioral Differences

**1. Validation Enforcement**:

```python
# OLD (AgentJobManager) - Loose validation
manager = AgentJobManager()
await manager.complete_job(job_id, None, tenant_key)  # Accepts None

# NEW (OrchestrationService) - Strict validation
service = OrchestrationService(session)
await service.complete_job(job_id, None, tenant_key)  # RAISES ValidationError
```

**2. TODO Tracking**:

```python
# OLD (AgentJobManager) - Optional TODO items
await manager.report_progress(job_id, {"percent": 50}, tenant_key)

# NEW (OrchestrationService) - TODO items tracked
await service.report_progress(
    job_id,
    {"percent": 50},
    tenant_key,
    todo_items=[{"content": "Task 1", "status": "completed"}]
)
```

**3. Schema Differences**:

```python
# OLD (AgentJobManager) - Returns dict
result = await manager.get_pending_jobs(agent_type, tenant_key)
# result: {"jobs": [...]}

# NEW (OrchestrationService) - Returns Pydantic model
result = await service.get_pending_jobs(agent_type, tenant_key)
# result: PendingJobsResponse(jobs=[...])
```

### Async Context Managers

**Pattern for Database Sessions**:
```python
# CORRECT
async with get_db_session() as session:
    service = OrchestrationService(session)
    result = await service.complete_job(job_id, result, tenant_key)
    # Session auto-commits/rollbacks

# INCORRECT
session = get_db_session()  # Missing async context
service = OrchestrationService(session)  # Session not properly managed
```

### Test Fixture Updates

**Before (AgentJobManager)**:
```python
@pytest.fixture
def agent_job_manager():
    return AgentJobManager()

def test_complete_job(agent_job_manager):
    result = agent_job_manager.complete_job(job_id, result, tenant_key)
```

**After (OrchestrationService)**:
```python
@pytest.fixture
async def orchestration_service(db_session):
    return OrchestrationService(db_session)

async def test_complete_job(orchestration_service):
    result = await orchestration_service.complete_job(job_id, result, tenant_key)
```

---

## 6. Integration Points

### Upstream Dependencies (What This Depends On)

**0420b MUST be complete**:
- `src/giljo_mcp/agent_job_manager.py` deleted
- All tests currently failing with import errors
- Closeout notes from 0420b contain exact list of failing tests

**Service Layer**:
- `OrchestrationService` (`src/giljo_mcp/services/orchestration_service.py`)
- `AgentJobManager` (service layer version in `services/`)
- Database session management (`giljo_mcp.database.get_db_session`)

### Downstream Impact (What Depends on This)

**0420d Final Cleanup**:
- Relies on all tests passing from 0420c
- Uses coverage report to identify orphaned code
- Verifies no remaining references to deleted module

**Production Code**:
- All MCP tools using `agent_job_status.py`
- Orchestrator instances using job lifecycle operations
- Workflow engine using status tracking

### Integration Report Section

If you discover undocumented dependencies, missing imports, or cascading issues not in the original analysis, document here (max 300 words):

**Format**:
```markdown
## Integration Report

### Discovered Dependencies
- [File path]: [Issue description]
- [File path]: [Issue description]

### Resolution Status
- ✅ Resolved: [Description]
- ⏸️ Deferred to 0420d: [Description]

### Cascade Impact
- [Affected files]: [Impact level: HIGH/MEDIUM/LOW]
```

---

## 7. Testing Requirements

### Test Categories and Coverage

**Unit Tests** (must pass):
- `tests/test_orchestrator_routing.py` - Orchestrator routing logic
- `tests/test_agent_job_status_tool.py` - MCP tool wrappers
- `tests/test_agent_orchestrator_communication_tools.py` - Communication tools

**Integration Tests** (must pass):
- `tests/integration/test_multi_tool_orchestration.py` - End-to-end workflows
- `tests/integration/test_workflow_engine.py` - Workflow engine operations

**Service Tests** (must pass):
- `tests/services/test_agent_job_manager_mission_ack.py` - Mission acknowledgment
- `tests/services/test_orchestration_service.py` - Service layer operations

**WebSocket Tests** (must pass):
- `tests/websocket/test_mission_tracking_events.py` - Real-time event emission

### Test Execution Strategy

**Incremental Testing** (after each file modification):
```bash
# After updating orchestrator.py
pytest tests/test_orchestrator_routing.py -v

# After updating workflow_engine.py
pytest tests/integration/test_workflow_engine.py -v

# After updating agent_job_status.py
pytest tests/test_agent_job_status_tool.py -v
```

**Full Suite Validation** (after all modifications):
```bash
pytest tests/ --cov=src/giljo_mcp --cov-report=html -v
```

### Coverage Requirements

**Target**: >80% coverage maintained across all modified modules

**Key Modules**:
- `src/giljo_mcp/orchestrator.py` - >80%
- `src/giljo_mcp/workflow_engine.py` - >80%
- `src/giljo_mcp/tools/agent_job_status.py` - >80%

**Coverage Report**:
```bash
pytest tests/ --cov=src/giljo_mcp --cov-report=html
# Open htmlcov/index.html to view detailed coverage
```

### Test Failure Debugging

**Common Failure Patterns**:

1. **Import Errors**: Missing `OrchestrationService` import
   - Fix: Add import, verify path

2. **Validation Errors**: Service enforces stricter validation
   - Fix: Update test data to match schema requirements

3. **Async Errors**: Missing `await` or async context
   - Fix: Ensure all service calls use `async with get_db_session()`

4. **Schema Mismatches**: Old tests expect dict, new returns Pydantic
   - Fix: Update test assertions to use model attributes

---

## 8. Validation Criteria

### Phase 4 Validation (Core Files)

**After Each File Modification**:
- ✅ File saves without syntax errors
- ✅ No import errors on module load
- ✅ Related tests pass (see Phase 4 steps)

**After All Core Files Updated**:
- ✅ `orchestrator.py` uses OrchestrationService
- ✅ `workflow_engine.py` uses async service calls
- ✅ `agent_job_status.py` uses service layer
- ✅ No references to deleted `agent_job_manager.py`

### Phase 5 Validation (Tests)

**After Each Test File Updated**:
- ✅ Test file imports successfully
- ✅ All tests in file pass
- ✅ No deprecation warnings

**After All Test Files Updated**:
- ✅ 100% of tests pass (green)
- ✅ Coverage >80% across modified modules
- ✅ No skipped or xfailed tests

### Final Validation

**Complete Test Suite**:
```bash
pytest tests/ --cov=src/giljo_mcp --cov-report=html -v
```

**Success Criteria**:
- ✅ ALL tests pass (100% green)
- ✅ Coverage >80% maintained
- ✅ No import errors for `agent_job_manager.py`
- ✅ All behavioral changes validated

**Failure Handling**:
- If <95% tests pass: Debug and fix before closeout
- If coverage <80%: Add tests for uncovered code paths
- If import errors remain: Check for missed references in 0420a analysis

---

## 9. Risks & Mitigations

### High Risk Areas

**Risk 1: Behavioral Mismatches in Tests**

**Description**: Tests written for AgentJobManager's loose validation will fail with OrchestrationService's strict validation.

**Likelihood**: HIGH
**Impact**: MEDIUM (test failures, not production issues)

**Mitigation**:
- Review all test data for schema compliance
- Update test expectations to match Pydantic validation
- Run tests incrementally to catch issues early

**Contingency**:
- If >10 tests fail: Create detailed mapping of failures by category
- Prioritize fixing tool tests (highest impact) first
- Defer low-priority integration tests to 0420d if time-constrained

---

**Risk 2: Async Context Management Errors**

**Description**: Missing `async with` blocks or improper session management can cause database connection leaks.

**Likelihood**: MEDIUM
**Impact**: HIGH (production database issues)

**Mitigation**:
- Use standard pattern: `async with get_db_session() as session:`
- Review all service calls for proper context management
- Run integration tests to verify no connection leaks

**Contingency**:
- If connection errors occur: Add explicit session cleanup
- Monitor connection pool during test runs
- Add timeout tests to detect leaks

---

**Risk 3: Undiscovered Dependencies**

**Description**: Files not identified in 0420a analysis may import deleted `agent_job_manager.py`.

**Likelihood**: LOW
**Impact**: MEDIUM (additional work required)

**Mitigation**:
- Run full test suite before starting modifications
- Document all discovered dependencies in Integration Report
- Grep codebase for `agent_job_manager` imports

**Contingency**:
- If discovered: Add to Phase 4/5 task list
- If >5 additional files: Escalate to 0420d for batching
- Update 0420a analysis with findings for future reference

---

**Risk 4: Coverage Regression**

**Description**: Removing tests or incomplete migrations may drop coverage below 80%.

**Likelihood**: LOW
**Impact**: MEDIUM (CI pipeline failures)

**Mitigation**:
- Run coverage report after each phase
- Replace deleted tests with equivalent service layer tests
- Focus on covering new code paths in OrchestrationService

**Contingency**:
- If coverage drops: Add missing tests before closeout
- Identify uncovered lines via HTML coverage report
- Defer non-critical coverage improvements to 0420d

---

## 10. Execution Checklist

### Pre-Execution Verification

- [ ] 0420b is marked complete in handover document
- [ ] Read 0420b closeout notes for failing test list
- [ ] Verify `src/giljo_mcp/agent_job_manager.py` is deleted
- [ ] Run tests to confirm current failure state: `pytest tests/ -v`
- [ ] Create feature branch: `git checkout -b 0420c-update-core-and-tests`

### Phase 4: Update Core Files

- [ ] **Step 4.1**: Update `orchestrator.py`
  - [ ] Remove AgentJobManager import (line 26)
  - [ ] Add OrchestrationService import
  - [ ] Migrate usage at line 115 to async service
  - [ ] Run: `pytest tests/test_orchestrator_routing.py -v`
  - [ ] Verify: All orchestrator tests pass

- [ ] **Step 4.2**: Update `workflow_engine.py`
  - [ ] Remove AgentJobManager import (line 25)
  - [ ] Add OrchestrationService import
  - [ ] Migrate usage at line 61 to async service
  - [ ] Run: `pytest tests/integration/test_workflow_engine.py -v`
  - [ ] Verify: All workflow tests pass

- [ ] **Step 4.3**: Update `agent_job_status.py`
  - [ ] Remove AgentJobManager import (line 26)
  - [ ] Add OrchestrationService import
  - [ ] Update all tool functions to use service layer
  - [ ] Run: `pytest tests/test_agent_job_status_tool.py -v`
  - [ ] Verify: All tool tests pass (or documented failures)

### Phase 5: Update Tests

- [ ] **Step 5.1**: Update `test_orchestrator_routing.py`
  - [ ] Remove 3 deprecated test functions
  - [ ] Update imports
  - [ ] Run: `pytest tests/test_orchestrator_routing.py -v`
  - [ ] Verify: All tests pass

- [ ] **Step 5.2**: Update `test_agent_orchestrator_communication_tools.py`
  - [ ] Update fixtures to use OrchestrationService
  - [ ] Update test expectations for validation changes
  - [ ] Add `todo_items` parameter to progress tests
  - [ ] Run: `pytest tests/test_agent_orchestrator_communication_tools.py -v`
  - [ ] Verify: All tests pass

- [ ] **Step 5.3**: Update `test_agent_job_status_tool.py`
  - [ ] Update mocks to use OrchestrationService
  - [ ] Update schema expectations
  - [ ] Run: `pytest tests/test_agent_job_status_tool.py -v`
  - [ ] Verify: All tests pass

- [ ] **Step 5.4**: Update `test_multi_tool_orchestration.py`
  - [ ] Convert to async service calls
  - [ ] Update fixtures for AsyncSession
  - [ ] Run: `pytest tests/integration/test_multi_tool_orchestration.py -v`
  - [ ] Verify: Integration tests pass

- [ ] **Step 5.5**: Update `test_mission_tracking_events.py`
  - [ ] Update mocks to use OrchestrationService
  - [ ] Verify WebSocket event payloads
  - [ ] Run: `pytest tests/websocket/test_mission_tracking_events.py -v`
  - [ ] Verify: WebSocket tests pass

- [ ] **Step 5.6**: Update `test_agent_job_manager_mission_ack.py`
  - [ ] Fix import path to OrchestrationService
  - [ ] Update test class name
  - [ ] Run: `pytest tests/services/test_agent_job_manager_mission_ack.py -v`
  - [ ] Verify: Service tests pass

### Phase 6: Full Validation

- [ ] Run complete test suite: `pytest tests/ --cov=src/giljo_mcp --cov-report=html -v`
- [ ] Verify: 100% of tests pass (green)
- [ ] Verify: Coverage >80% maintained
- [ ] Verify: No import errors for deleted module
- [ ] Open `htmlcov/index.html` and review coverage report
- [ ] Document any coverage gaps for 0420d

### Closeout

- [ ] Create Integration Report section if undocumented dependencies discovered
- [ ] Update 0420d handover with:
  - [ ] Final test count and pass rate
  - [ ] Coverage percentage (with link to HTML report)
  - [ ] List of deleted vs migrated tests
  - [ ] Remaining cleanup items discovered
- [ ] Commit changes: `git commit -m "feat(0420c): Migrate to OrchestrationService and fix tests"`
- [ ] Mark handover complete: Update status to "COMPLETE" in this document

---

## Appendix A: Quick Reference

### File Modification Summary

| File | Modifications | Test Command |
|------|--------------|--------------|
| `orchestrator.py` | Import + line 115 migration | `pytest tests/test_orchestrator_routing.py -v` |
| `workflow_engine.py` | Import + line 61 migration | `pytest tests/integration/test_workflow_engine.py -v` |
| `agent_job_status.py` | Import + all tool functions | `pytest tests/test_agent_job_status_tool.py -v` |
| `test_orchestrator_routing.py` | Remove 3 functions | `pytest tests/test_orchestrator_routing.py -v` |
| `test_agent_orchestrator_communication_tools.py` | Fixtures + validation | `pytest tests/test_agent_orchestrator_communication_tools.py -v` |
| `test_agent_job_status_tool.py` | Mocks + schemas | `pytest tests/test_agent_job_status_tool.py -v` |
| `test_multi_tool_orchestration.py` | Async conversion | `pytest tests/integration/test_multi_tool_orchestration.py -v` |
| `test_mission_tracking_events.py` | Mocks + payloads | `pytest tests/websocket/test_mission_tracking_events.py -v` |
| `test_agent_job_manager_mission_ack.py` | Import path | `pytest tests/services/test_agent_job_manager_mission_ack.py -v` |

### Common Patterns

**Service Layer Import**:
```python
from giljo_mcp.services.orchestration_service import OrchestrationService
from giljo_mcp.database import get_db_session
```

**Async Service Usage**:
```python
async with get_db_session() as session:
    service = OrchestrationService(session)
    result = await service.complete_job(job_id, result, tenant_key)
```

**Test Fixture Pattern**:
```python
@pytest.fixture
async def orchestration_service(db_session):
    return OrchestrationService(db_session)
```

### Key Behavioral Changes

| Function | Old Behavior | New Behavior |
|----------|--------------|--------------|
| `complete_job()` | Accepts None for result | Validates result is dict |
| `report_progress()` | Optional TODO items | Tracks TODO items |
| `get_pending_jobs()` | Returns dict | Returns Pydantic model |

---

**End of Handover Document**
