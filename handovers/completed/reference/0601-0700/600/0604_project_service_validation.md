# Handover 0604: ProjectService Validation

**Phase**: 1
**Tool**: CCW (Cloud)
**Agent Type**: tdd-implementor
**Duration**: 1 day
**Parallel Group**: Group A (Services)
**Depends On**: 0602

---

## Context

**Read First**: `handovers/600/AGENT_REFERENCE_GUIDE.md` for universal project context.

**Previous Handovers**: Handover 0602 established test baseline, documenting current coverage and failure patterns. Migration order fixed in 0601.

**This Handover**: Create comprehensive unit and integration tests for ProjectService, achieving 80%+ coverage while validating product-project relationships, single active project per product enforcement, soft delete with 10-day recovery window, and multi-tenant isolation.

---

## Specific Objectives

- **Objective 1**: Create comprehensive unit tests for all ProjectService methods (80%+ coverage)
- **Objective 2**: Create integration tests for product-project relationships and database transactions
- **Objective 3**: Validate project lifecycle (CRUD, activate/pause/cancel/complete)
- **Objective 4**: Test soft delete with 10-day recovery window
- **Objective 5**: Verify single active project per product enforcement
- **Objective 6**: Ensure cascade behavior (product deactivation → projects paused)

---

## Tasks

### Task 1: Read and Analyze ProjectService
**What**: Read ProjectService implementation to understand all methods and edge cases
**Why**: Must understand implementation before writing comprehensive tests
**Files**: `src/giljo_mcp/services/project_service.py`
**Commands**:
```bash
# Read service implementation
cat src/giljo_mcp/services/project_service.py
```

**Methods to Test**:
- `create_project(product_id, tenant_key, name, description, mission_text)`
- `get_project(project_id, tenant_key)`
- `update_project(project_id, tenant_key, **kwargs)`
- `delete_project(project_id, tenant_key)` - Soft delete with recovery window
- `recover_project(project_id, tenant_key)` - Undelete within 10 days
- `purge_deleted_projects()` - Permanent delete after 10 days
- `activate_project(project_id, tenant_key)` - Single active per product
- `pause_project(project_id, tenant_key)`
- `cancel_project(project_id, tenant_key)`
- `complete_project(project_id, tenant_key)`
- `list_projects(tenant_key, product_id=None, filters=None)`
- `get_project_summary(project_id, tenant_key)` - Stats and metrics

### Task 2: Create Unit Test Structure
**What**: Create unit test file with fixtures and test class structure
**Why**: Organized test structure enables comprehensive coverage
**Files**: `tests/unit/test_project_service.py`

**Example Structure**:
```python
import pytest
from datetime import datetime, timedelta
from src.giljo_mcp.services.project_service import ProjectService
from src.giljo_mcp.models import Project, Product

@pytest.fixture
def project_service(db_session):
    """Fixture providing ProjectService instance"""
    return ProjectService(db_session)

@pytest.fixture
def test_product(db_session, test_tenant_key):
    """Fixture providing a test product"""
    # Create and return product for project association
    pass

@pytest.fixture
def sample_project_data():
    """Fixture providing sample project data"""
    return {
        "name": "Test Project",
        "description": "A test project for validation",
        "mission_text": "Build amazing features"
    }

class TestProjectServiceCreate:
    """Tests for project creation"""
    # ... create tests

class TestProjectServiceLifecycle:
    """Tests for project lifecycle (activate, pause, cancel, complete)"""
    # ... lifecycle tests

class TestProjectServiceSoftDelete:
    """Tests for soft delete and recovery"""
    # ... soft delete tests
```

### Task 3: Implement CRUD Tests
**What**: Write unit tests for create, read, update, delete operations
**Why**: Core functionality must be rock-solid
**Files**: `tests/unit/test_project_service.py`

**Test Coverage** (26 tests):

**Create Tests** (7 tests):
- `test_create_project_success` - Happy path
- `test_create_project_with_mission` - Mission text provided
- `test_create_project_under_active_product` - Product must be active
- `test_create_project_duplicate_name_same_product` - Duplicate validation
- `test_create_project_duplicate_name_different_product` - Allowed across products
- `test_create_project_product_not_found` - Product validation
- `test_create_project_wrong_tenant` - Tenant isolation

**Read Tests** (6 tests):
- `test_get_project_success` - Retrieve existing project
- `test_get_project_not_found` - 404 handling
- `test_get_project_wrong_tenant` - Tenant isolation
- `test_list_projects_all` - List all projects for tenant
- `test_list_projects_by_product` - Filter by product_id
- `test_list_projects_by_status` - Filter by status

**Update Tests** (6 tests):
- `test_update_project_name` - Name update
- `test_update_project_description` - Description update
- `test_update_project_mission_text` - Mission update
- `test_update_project_not_found` - 404 handling
- `test_update_project_wrong_tenant` - Tenant isolation
- `test_update_project_duplicate_name` - Name uniqueness validation

**Delete Tests** (7 tests):
- `test_delete_project_soft_delete` - Status set to 'deleted'
- `test_delete_project_deleted_at_timestamp` - Timestamp set (datetime.utcnow)
- `test_delete_project_cascade_tasks` - Tasks also soft deleted
- `test_delete_project_not_found` - 404 handling
- `test_delete_project_wrong_tenant` - Tenant isolation
- `test_delete_project_already_deleted` - Idempotent operation
- `test_delete_project_with_agent_jobs` - Agent jobs handling

### Task 4: Implement Lifecycle Tests
**What**: Write tests for activate/pause/cancel/complete transitions
**Why**: Project state machine must be correct
**Files**: `tests/unit/test_project_service.py`

**Test Coverage** (12 tests):

**Activation Tests** (5 tests):
- `test_activate_project_success` - Activation works
- `test_activate_project_deactivates_others_in_product` - Single active per product
- `test_activate_project_different_products_independent` - Products independent
- `test_activate_project_product_must_be_active` - Product active check
- `test_activate_project_already_active` - Idempotent operation

**Pause Tests** (2 tests):
- `test_pause_project_success` - Pause active project
- `test_pause_project_already_paused` - Idempotent operation

**Cancel Tests** (2 tests):
- `test_cancel_project_success` - Cancel project
- `test_cancel_project_cascade_tasks` - Tasks cancelled too

**Complete Tests** (3 tests):
- `test_complete_project_success` - Complete project
- `test_complete_project_incomplete_tasks` - Validation (all tasks must be complete)
- `test_complete_project_sets_completed_at` - Timestamp verification

**Example Test**:
```python
def test_activate_project_deactivates_others_in_product(
    self, project_service, test_product, test_tenant_key
):
    """Test single active project per product enforcement"""
    # Arrange: Create two projects under same product
    project1 = project_service.create_project(
        product_id=test_product.id,
        tenant_key=test_tenant_key,
        name="Project 1",
        description="First project"
    )
    project2 = project_service.create_project(
        product_id=test_product.id,
        tenant_key=test_tenant_key,
        name="Project 2",
        description="Second project"
    )
    project_service.activate_project(project1.id, test_tenant_key)

    # Act: Activate second project
    project_service.activate_project(project2.id, test_tenant_key)

    # Assert: Project 2 active, Project 1 paused
    project2_refreshed = project_service.get_project(project2.id, test_tenant_key)
    assert project2_refreshed.status == 'active'

    project1_refreshed = project_service.get_project(project1.id, test_tenant_key)
    assert project1_refreshed.status == 'paused'
```

### Task 5: Implement Soft Delete and Recovery Tests
**What**: Write tests for soft delete, recovery, and auto-purge after 10 days
**Why**: Critical feature for data recovery
**Files**: `tests/unit/test_project_service.py`

**Test Coverage** (8 tests):
- `test_soft_delete_sets_deleted_status` - Status = 'deleted'
- `test_soft_delete_sets_deleted_at_timestamp` - Timestamp set
- `test_soft_delete_hides_from_list` - Deleted projects not in list_projects()
- `test_recover_project_within_10_days` - Recovery works
- `test_recover_project_restores_status` - Status restored to 'paused'
- `test_recover_project_clears_deleted_at` - Timestamp cleared
- `test_purge_deleted_projects_after_10_days` - Auto-purge old deletions
- `test_purge_deleted_projects_preserves_recent` - Recent deletions kept

**Example Test**:
```python
def test_purge_deleted_projects_after_10_days(self, project_service, test_product, test_tenant_key):
    """Test that deleted projects are purged after 10 days"""
    # Arrange: Create project, delete it, set deleted_at to 11 days ago
    project = project_service.create_project(
        product_id=test_product.id,
        tenant_key=test_tenant_key,
        name="Old Project",
        description="Will be purged"
    )
    project_service.delete_project(project.id, test_tenant_key)

    # Manually set deleted_at to 11 days ago
    project.deleted_at = datetime.utcnow() - timedelta(days=11)
    db_session.commit()

    # Act: Run purge
    purged_count = project_service.purge_deleted_projects()

    # Assert: Project permanently deleted
    assert purged_count == 1
    with pytest.raises(NotFoundError):
        project_service.get_project(project.id, test_tenant_key)
```

### Task 6: Create Integration Tests
**What**: Create integration test file for product-project relationships and cascades
**Why**: Validate ProjectService works correctly with ProductService and database
**Files**: `tests/integration/test_project_service.py`

**Test Coverage** (12 tests):

**Multi-Tenant Isolation** (3 tests):
- `test_tenant_isolation_create` - Tenant A creates project, Tenant B cannot see it
- `test_tenant_isolation_update` - Tenant A cannot update Tenant B's project
- `test_tenant_isolation_delete` - Tenant A cannot delete Tenant B's project

**Product-Project Relationships** (4 tests):
- `test_create_project_product_must_exist` - Foreign key validation
- `test_create_project_product_must_be_active` - Business rule validation
- `test_list_projects_scoped_to_product` - Product filtering
- `test_product_deletion_cascades_to_projects` - Cascade soft delete

**Cascade Behavior** (3 tests):
- `test_product_deactivation_pauses_active_projects` - Product deactivated → projects paused
- `test_project_deletion_cascades_to_tasks` - Project deleted → tasks deleted
- `test_project_completion_requires_all_tasks_complete` - Validation

**Database Transactions** (2 tests):
- `test_activate_project_atomic` - Activation is atomic (single active at a time)
- `test_create_project_rollback_on_error` - Database error triggers rollback

**Example Integration Test**:
```python
def test_product_deactivation_pauses_active_projects(self, db_session):
    """Test that deactivating a product pauses all active projects"""
    # Arrange: Product with active project
    product_service = ProductService(db_session)
    project_service = ProjectService(db_session)

    product = product_service.create_product(
        tenant_key="test-tenant",
        name="Test Product",
        description="Product with projects"
    )
    product_service.activate_product(product.id, "test-tenant")

    project = project_service.create_project(
        product_id=product.id,
        tenant_key="test-tenant",
        name="Test Project",
        description="Active project"
    )
    project_service.activate_project(project.id, "test-tenant")

    # Act: Deactivate product
    product_service.deactivate_product(product.id, "test-tenant")

    # Assert: Project paused
    project_refreshed = project_service.get_project(project.id, "test-tenant")
    assert project_refreshed.status == 'paused'
```

### Task 7: Run Tests and Verify Coverage
**What**: Execute tests and verify 80%+ coverage target met
**Why**: Ensure comprehensive testing before PR
**Commands**:
```bash
# Run unit tests with coverage
pytest tests/unit/test_project_service.py -v \
  --cov=src/giljo_mcp/services/project_service.py \
  --cov-report=term-missing

# Run integration tests
pytest tests/integration/test_project_service.py -v

# Generate coverage report snippet for PR
pytest tests/unit/test_project_service.py \
  --cov=src/giljo_mcp/services/project_service.py \
  --cov-report=term | grep -A 10 "TOTAL"
```

**Expected Output**:
- Unit tests: 53+ tests passing
- Integration tests: 12+ tests passing
- Coverage: ≥ 80% on ProjectService
- All tests pass (100% pass rate)

---

## Success Criteria

- [ ] **Unit Tests**: 53+ unit tests created covering all ProjectService methods
- [ ] **Integration Tests**: 12+ integration tests for product-project relationships
- [ ] **Coverage**: ≥ 80% coverage on ProjectService (verified via pytest --cov)
- [ ] **All Tests Pass**: 100% pass rate (no failures, no skips)
- [ ] **Multi-Tenant Verified**: Zero tenant leakage
- [ ] **Soft Delete Verified**: 10-day recovery window working
- [ ] **Single Active Project**: Database constraint enforced correctly
- [ ] **PR Created**: Branch `0604-project-service-tests` with test results

---

## Validation Steps

**How to verify this handover is complete:**

```bash
# Step 1: Run unit tests
pytest tests/unit/test_project_service.py -v --cov=src/giljo_mcp/services/project_service.py --cov-report=term-missing
# Expected: 53+ tests pass, ≥ 80% coverage

# Step 2: Run integration tests
pytest tests/integration/test_project_service.py -v
# Expected: 12+ tests pass

# Step 3: Check coverage percentage
pytest tests/unit/test_project_service.py --cov=src/giljo_mcp/services/project_service.py --cov-report=term | grep "TOTAL"
# Expected: TOTAL coverage ≥ 80%
```

---

## Deliverables

### Code
- **Created**:
  - `tests/unit/test_project_service.py` - Unit tests (53+ tests)
  - `tests/integration/test_project_service.py` - Integration tests (12+ tests)

### Git Commit
- **Message**: `test: Add comprehensive ProjectService tests (Handover 0604)`
- **Branch**: `0604-project-service-tests` (CCW execution)

---

## Dependencies

### Requires (Before Starting)
- **Handover 0602**: Test baseline established
- **Files**: `src/giljo_mcp/services/project_service.py` must exist

### Blocks (What's Waiting)
- **Handover 0610**: Projects API validation depends on ProjectService tests passing

---

## Notes for Agent

### CCW (Cloud) Execution
This is a CCW handover for parallel execution:

- Create branch: `0604-project-service-tests`
- Write tests assuming ProjectService interface
- Create PR with test results in description

### Quality Checklist
Before marking this handover complete:

- [ ] All tests pass (100% pass rate)
- [ ] Coverage ≥ 80%
- [ ] Multi-tenant isolation verified
- [ ] Soft delete recovery tested
- [ ] PR created with test results

---

**Document Control**:
- **Handover**: 0604
- **Created**: 2025-11-14
- **Status**: Ready for execution
