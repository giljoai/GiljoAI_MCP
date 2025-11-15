# Handover 0605: TaskService Validation

**Phase**: 1
**Tool**: CCW (Cloud)
**Agent Type**: tdd-implementor
**Duration**: 1 day
**Parallel Group**: Group A (Services)
**Depends On**: 0602

---

## Context

**Read First**: `handovers/600/AGENT_REFERENCE_GUIDE.md` for universal project context.

**Previous Handovers**: Handover 0602 established test baseline. Migration order fixed in 0601.

**This Handover**: Create comprehensive unit and integration tests for TaskService, achieving 80%+ coverage while validating project-task relationships, task lifecycle management, status transitions, and multi-tenant isolation.

---

## Specific Objectives

- **Objective 1**: Create comprehensive unit tests for all TaskService methods (80%+ coverage)
- **Objective 2**: Create integration tests for project-task relationships and cascades
- **Objective 3**: Validate task lifecycle (CRUD, status transitions)
- **Objective 4**: Test task assignment and completion tracking
- **Objective 5**: Verify cascade behavior (project deletion → tasks deleted)
- **Objective 6**: Ensure multi-tenant isolation

---

## Tasks

### Task 1: Read and Analyze TaskService
**What**: Read TaskService implementation to understand all methods
**Files**: `src/giljo_mcp/services/task_service.py`

**Methods to Test**:
- `create_task(project_id, tenant_key, title, description, assignee)`
- `get_task(task_id, tenant_key)`
- `update_task(task_id, tenant_key, **kwargs)`
- `delete_task(task_id, tenant_key)`
- `list_tasks(tenant_key, project_id=None, filters=None)`
- `assign_task(task_id, tenant_key, assignee)`
- `start_task(task_id, tenant_key)`
- `complete_task(task_id, tenant_key)`
- `block_task(task_id, tenant_key, reason)`
- `unblock_task(task_id, tenant_key)`

### Task 2: Implement CRUD Tests
**What**: Write unit tests for create, read, update, delete operations
**Files**: `tests/unit/test_task_service.py`

**Test Coverage** (30+ tests):

**Create Tests** (6 tests):
- `test_create_task_success`
- `test_create_task_with_assignee`
- `test_create_task_project_must_exist`
- `test_create_task_project_must_be_active`
- `test_create_task_missing_required_fields`
- `test_create_task_wrong_tenant`

**Read Tests** (5 tests):
- `test_get_task_success`
- `test_get_task_not_found`
- `test_get_task_wrong_tenant`
- `test_list_tasks_by_project`
- `test_list_tasks_by_status`

**Update Tests** (4 tests):
- `test_update_task_title`
- `test_update_task_description`
- `test_update_task_not_found`
- `test_update_task_wrong_tenant`

**Delete Tests** (4 tests):
- `test_delete_task_success`
- `test_delete_task_not_found`
- `test_delete_task_wrong_tenant`
- `test_delete_task_with_dependencies`

### Task 3: Implement Status Transition Tests
**What**: Write tests for task status lifecycle
**Files**: `tests/unit/test_task_service.py`

**Test Coverage** (11 tests):
- `test_assign_task_success`
- `test_start_task_success`
- `test_start_task_sets_started_at`
- `test_complete_task_success`
- `test_complete_task_sets_completed_at`
- `test_complete_task_already_complete`
- `test_block_task_success`
- `test_block_task_with_reason`
- `test_unblock_task_success`
- `test_status_transition_invalid`
- `test_status_history_tracking`

### Task 4: Create Integration Tests
**What**: Create integration tests for project-task relationships
**Files**: `tests/integration/test_task_service.py`

**Test Coverage** (10 tests):

**Multi-Tenant Isolation** (3 tests):
- `test_tenant_isolation_create`
- `test_tenant_isolation_update`
- `test_tenant_isolation_delete`

**Project-Task Relationships** (4 tests):
- `test_create_task_project_must_exist`
- `test_list_tasks_scoped_to_project`
- `test_project_deletion_cascades_to_tasks`
- `test_project_completion_requires_all_tasks_complete`

**Database Transactions** (3 tests):
- `test_create_task_rollback_on_error`
- `test_complete_task_atomic`
- `test_task_status_concurrent_updates`

### Task 5: Run Tests and Verify Coverage
**Commands**:
```bash
pytest tests/unit/test_task_service.py -v \
  --cov=src/giljo_mcp/services/task_service.py \
  --cov-report=term-missing

pytest tests/integration/test_task_service.py -v
```

---

## Success Criteria

- [ ] **Unit Tests**: 41+ unit tests created
- [ ] **Integration Tests**: 10+ integration tests
- [ ] **Coverage**: ≥ 80% coverage on TaskService
- [ ] **All Tests Pass**: 100% pass rate
- [ ] **PR Created**: Branch `0605-task-service-tests`

---

## Deliverables

### Code
- **Created**:
  - `tests/unit/test_task_service.py` (41+ tests)
  - `tests/integration/test_task_service.py` (10+ tests)

### Git Commit
- **Message**: `test: Add comprehensive TaskService tests (Handover 0605)`
- **Branch**: `0605-task-service-tests`

---

## Dependencies

### Requires
- **Handover 0602**: Test baseline established
- **Files**: `src/giljo_mcp/services/task_service.py`

### Blocks
- **Handover 0611**: Tasks API validation

---

## Notes for Agent

### CCW (Cloud) Execution
- Create branch: `0605-task-service-tests`
- Write comprehensive tests
- Create PR with results

---

**Document Control**:
- **Handover**: 0605
- **Created**: 2025-11-14
- **Status**: Ready for execution
