# Handover 0603: ProductService Validation

**Phase**: 1
**Tool**: CCW (Cloud)
**Agent Type**: tdd-implementor
**Duration**: 1 day
**Parallel Group**: Group A (Services)
**Depends On**: 0602

---

## Context

**Read First**: `handovers/600/AGENT_REFERENCE_GUIDE.md` for universal project context.

**Previous Handovers**: Handover 0602 established test baseline, documenting current coverage (~58-65%) and failure patterns. Migration order fixed in 0601, fresh install working.

**This Handover**: Create comprehensive unit and integration tests for ProductService, achieving 80%+ coverage while validating multi-tenant isolation, product lifecycle management, vision upload handling, and single active product enforcement.

---

## Specific Objectives

- **Objective 1**: Create comprehensive unit tests for all ProductService methods (80%+ coverage)
- **Objective 2**: Create integration tests for database transactions and multi-tenant isolation
- **Objective 3**: Validate product lifecycle (CRUD, activate/deactivate, soft delete)
- **Objective 4**: Test vision upload and config_data persistence
- **Objective 5**: Verify single active product enforcement (database constraint validation)
- **Objective 6**: Ensure zero tenant leakage (User A cannot access User B's products)

---

## Tasks

### Task 1: Read and Analyze ProductService
**What**: Read ProductService implementation to understand all methods and edge cases
**Why**: Must understand implementation before writing comprehensive tests
**Files**: `src/giljo_mcp/services/product_service.py`
**Commands**:
```bash
# Read service implementation
cat src/giljo_mcp/services/product_service.py
```

**Methods to Test**:
- `create_product(tenant_key, name, description, vision_text, config_data)`
- `get_product(product_id, tenant_key)`
- `update_product(product_id, tenant_key, **kwargs)`
- `delete_product(product_id, tenant_key)` - Soft delete
- `activate_product(product_id, tenant_key)` - Single active enforcement
- `deactivate_product(product_id, tenant_key)`
- `list_products(tenant_key, filters=None)`
- `upload_vision(product_id, tenant_key, vision_file)`
- `get_vision(product_id, tenant_key)`
- `update_config_data(product_id, tenant_key, config_data)`
- `get_active_product(tenant_key)` - Returns single active product

### Task 2: Create Unit Test Structure
**What**: Create unit test file with fixtures and test class structure
**Why**: Organized test structure enables comprehensive coverage
**Files**: `tests/unit/test_product_service.py`

**Example Structure**:
```python
import pytest
from datetime import datetime
from src.giljo_mcp.services.product_service import ProductService
from src.giljo_mcp.models import Product

@pytest.fixture
def product_service(db_session):
    """Fixture providing ProductService instance"""
    return ProductService(db_session)

@pytest.fixture
def test_tenant_key():
    """Fixture providing test tenant key"""
    return "test-tenant-001"

@pytest.fixture
def sample_product_data():
    """Fixture providing sample product data"""
    return {
        "name": "Test Product",
        "description": "A test product for validation",
        "vision_text": "Build an amazing product",
        "config_data": {"setting1": "value1"}
    }

class TestProductServiceCreate:
    """Tests for product creation"""

    def test_create_product_success(self, product_service, test_tenant_key, sample_product_data):
        """Test successful product creation"""
        # Arrange, Act, Assert
        pass

    def test_create_product_duplicate_name(self, product_service, test_tenant_key):
        """Test duplicate product name handling"""
        pass

    def test_create_product_invalid_data(self, product_service, test_tenant_key):
        """Test validation error handling"""
        pass

class TestProductServiceRead:
    """Tests for product retrieval"""
    # ... tests for get_product, list_products, etc.

class TestProductServiceUpdate:
    """Tests for product updates"""
    # ... tests for update_product, config_data, vision

class TestProductServiceDelete:
    """Tests for product deletion"""
    # ... tests for soft delete, cascade behavior

class TestProductServiceActivation:
    """Tests for product activation"""
    # ... tests for activate, deactivate, single active enforcement
```

### Task 3: Implement CRUD Tests
**What**: Write unit tests for create, read, update, delete operations
**Why**: Core functionality must be rock-solid
**Files**: `tests/unit/test_product_service.py`

**Test Coverage**:

**Create Tests** (8 tests):
- `test_create_product_success` - Happy path
- `test_create_product_with_vision` - Vision text provided
- `test_create_product_with_config_data` - Config data persisted
- `test_create_product_duplicate_name_same_tenant` - Duplicate validation
- `test_create_product_duplicate_name_different_tenant` - Allowed across tenants
- `test_create_product_missing_required_fields` - Validation error
- `test_create_product_invalid_tenant_key` - Tenant validation
- `test_create_product_long_name` - Name length validation

**Read Tests** (6 tests):
- `test_get_product_success` - Retrieve existing product
- `test_get_product_not_found` - 404 handling
- `test_get_product_wrong_tenant` - Tenant isolation (403)
- `test_list_products_all` - List all products for tenant
- `test_list_products_filtered` - Filter by status/name
- `test_list_products_empty_tenant` - Empty result set

**Update Tests** (7 tests):
- `test_update_product_name` - Name update
- `test_update_product_description` - Description update
- `test_update_product_config_data_merge` - Config data merging
- `test_update_product_config_data_replace` - Config data replacement
- `test_update_product_not_found` - 404 handling
- `test_update_product_wrong_tenant` - Tenant isolation
- `test_update_product_duplicate_name` - Name uniqueness validation

**Delete Tests** (5 tests):
- `test_delete_product_soft_delete` - Status set to 'deleted'
- `test_delete_product_deleted_at_timestamp` - Timestamp set
- `test_delete_product_cascade_projects` - Projects also soft deleted
- `test_delete_product_not_found` - 404 handling
- `test_delete_product_wrong_tenant` - Tenant isolation

### Task 4: Implement Activation Tests
**What**: Write tests for activate/deactivate and single active product enforcement
**Why**: Critical business rule - only ONE active product per tenant
**Files**: `tests/unit/test_product_service.py`

**Test Coverage** (8 tests):
- `test_activate_product_success` - Activation works
- `test_activate_product_deactivates_others` - Previous active product deactivated
- `test_activate_product_already_active` - Idempotent operation
- `test_activate_product_not_found` - 404 handling
- `test_activate_product_wrong_tenant` - Tenant isolation
- `test_deactivate_product_success` - Deactivation works
- `test_get_active_product_returns_one` - Single active product returned
- `test_get_active_product_none_active` - Returns None if no active product

**Example Test**:
```python
def test_activate_product_deactivates_others(self, product_service, test_tenant_key):
    """Test that activating a product deactivates the previously active product"""
    # Arrange: Create two products, activate first
    product1 = product_service.create_product(
        tenant_key=test_tenant_key,
        name="Product 1",
        description="First product"
    )
    product2 = product_service.create_product(
        tenant_key=test_tenant_key,
        name="Product 2",
        description="Second product"
    )
    product_service.activate_product(product1.id, test_tenant_key)

    # Act: Activate second product
    product_service.activate_product(product2.id, test_tenant_key)

    # Assert: Product 2 active, Product 1 inactive
    active_product = product_service.get_active_product(test_tenant_key)
    assert active_product.id == product2.id

    product1_refreshed = product_service.get_product(product1.id, test_tenant_key)
    assert product1_refreshed.status == 'inactive'
```

### Task 5: Implement Vision Upload Tests
**What**: Write tests for vision file upload and retrieval
**Why**: Vision documents are critical for product planning
**Files**: `tests/unit/test_product_service.py`

**Test Coverage** (5 tests):
- `test_upload_vision_text` - Upload plain text vision
- `test_upload_vision_file` - Upload file (markdown/txt)
- `test_upload_vision_replaces_existing` - Overwrite existing vision
- `test_get_vision_success` - Retrieve vision text
- `test_get_vision_not_found` - 404 if product doesn't exist

### Task 6: Create Integration Tests
**What**: Create integration test file for cross-service and database scenarios
**Why**: Validate ProductService works correctly with real database
**Files**: `tests/integration/test_product_service.py`

**Test Coverage** (10 tests):

**Multi-Tenant Isolation** (4 tests):
- `test_tenant_isolation_create` - Tenant A creates product, Tenant B cannot see it
- `test_tenant_isolation_update` - Tenant A cannot update Tenant B's product
- `test_tenant_isolation_delete` - Tenant A cannot delete Tenant B's product
- `test_tenant_isolation_activate` - Tenant A activating doesn't affect Tenant B

**Database Transactions** (3 tests):
- `test_create_product_rollback_on_error` - Database error triggers rollback
- `test_update_product_concurrent_updates` - Optimistic locking or last-write-wins
- `test_activate_product_atomic` - Activation is atomic (one active at a time)

**Cascade Behavior** (3 tests):
- `test_delete_product_cascades_to_projects` - Projects soft deleted when product deleted
- `test_activate_product_cascades_to_projects` - Projects paused when product deactivated
- `test_product_with_projects_prevents_hard_delete` - Cannot hard delete if projects exist

**Example Integration Test**:
```python
def test_tenant_isolation_create(self, db_session):
    """Test that products are isolated by tenant"""
    # Arrange: Two tenants
    service_a = ProductService(db_session)
    service_b = ProductService(db_session)

    # Act: Tenant A creates product
    product_a = service_a.create_product(
        tenant_key="tenant-a",
        name="Product A",
        description="Tenant A's product"
    )

    # Assert: Tenant B cannot see Tenant A's product
    products_b = service_b.list_products(tenant_key="tenant-b")
    assert len(products_b) == 0

    # Assert: Tenant B cannot get Tenant A's product by ID
    with pytest.raises(PermissionError):  # Or 403 exception
        service_b.get_product(product_a.id, tenant_key="tenant-b")
```

### Task 7: Run Tests and Verify Coverage
**What**: Execute tests and verify 80%+ coverage target met
**Why**: Ensure comprehensive testing before PR
**Commands**:
```bash
# Run unit tests with coverage
pytest tests/unit/test_product_service.py -v \
  --cov=src/giljo_mcp/services/product_service.py \
  --cov-report=term-missing

# Run integration tests
pytest tests/integration/test_product_service.py -v

# Generate coverage report snippet for PR
pytest tests/unit/test_product_service.py \
  --cov=src/giljo_mcp/services/product_service.py \
  --cov-report=term | grep -A 10 "TOTAL"
```

**Expected Output**:
- Unit tests: 39+ tests passing
- Integration tests: 10+ tests passing
- Coverage: ≥ 80% on ProductService
- All tests pass (100% pass rate)

---

## Success Criteria

- [ ] **Unit Tests**: 39+ unit tests created covering all ProductService methods
- [ ] **Integration Tests**: 10+ integration tests for multi-tenant isolation and database transactions
- [ ] **Coverage**: ≥ 80% coverage on ProductService (verified via pytest --cov)
- [ ] **All Tests Pass**: 100% pass rate (no failures, no skips)
- [ ] **Multi-Tenant Verified**: Zero tenant leakage (User A cannot access User B's products)
- [ ] **Single Active Product**: Database constraint enforced correctly
- [ ] **PR Created**: Branch `0603-product-service-tests` with PR containing test results
- [ ] **Coverage Report**: Coverage snippet included in PR description

---

## Validation Steps

**How to verify this handover is complete:**

```bash
# Step 1: Run unit tests
pytest tests/unit/test_product_service.py -v --cov=src/giljo_mcp/services/product_service.py --cov-report=term-missing
# Expected: 39+ tests pass, ≥ 80% coverage

# Step 2: Run integration tests
pytest tests/integration/test_product_service.py -v
# Expected: 10+ tests pass, multi-tenant isolation verified

# Step 3: Verify no test failures
pytest tests/unit/test_product_service.py tests/integration/test_product_service.py --tb=short
# Expected: 0 failures, 0 errors

# Step 4: Check coverage percentage
pytest tests/unit/test_product_service.py --cov=src/giljo_mcp/services/product_service.py --cov-report=term | grep "TOTAL"
# Expected: TOTAL coverage ≥ 80%

# Step 5: Verify multi-tenant isolation test passes
pytest tests/integration/test_product_service.py::test_tenant_isolation_create -v
# Expected: PASSED
```

**Expected Output**:
- Unit tests: 39/39 passing (100%)
- Integration tests: 10/10 passing (100%)
- Coverage: 82-88% on ProductService
- Multi-tenant isolation: Verified (zero leakage)
- PR created with test run output and coverage report

---

## Deliverables

### Code
- **Created**:
  - `tests/unit/test_product_service.py` - Comprehensive unit tests (39+ tests)
  - `tests/integration/test_product_service.py` - Integration tests (10+ tests)

### Tests
- **Unit Tests**: 39+ tests covering:
  - CRUD operations (26 tests)
  - Activation/deactivation (8 tests)
  - Vision upload (5 tests)
- **Integration Tests**: 10+ tests covering:
  - Multi-tenant isolation (4 tests)
  - Database transactions (3 tests)
  - Cascade behavior (3 tests)

### Documentation
- **Updated**: PR description with:
  - Test run output (pytest -v)
  - Coverage report snippet
  - Summary of test coverage (what was tested)

### Git Commit
- **Message**: `test: Add comprehensive ProductService tests (Handover 0603)`
- **Branch**: `0603-product-service-tests` (CCW execution)
- **PR**: Created against master

---

## Dependencies

### Requires (Before Starting)
- **Handover 0602**: Test baseline established, understand current failure patterns
- **Files**: `src/giljo_mcp/services/product_service.py` must exist
- **Database**: Database migrations applied (for integration tests)

### Blocks (What's Waiting)
- **Handover 0609**: Products API validation depends on ProductService tests passing
- **Phase 1 Merge**: All 6 service validation handovers (0603-0608) merge together before Phase 2

---

## Notes for Agent

### CCW (Cloud) Execution
This is a CCW handover for parallel execution:

- Create branch: `0603-product-service-tests`
- Mock database if needed (use pytest fixtures)
- Write tests assuming ProductService interface (read source file)
- Create PR with test results in description
- Include coverage report snippet in PR

### Common Patterns
Reference from AGENT_REFERENCE_GUIDE.md:

- Service pattern: See "Common Patterns - Service Pattern" section
- Test pattern: See "Common Patterns - Test Pattern" section
- Multi-tenant isolation: See "Multi-Tenant Architecture" section

### Test Writing Strategy

**Unit Tests**:
- Test each method in isolation
- Mock database calls if needed
- Focus on business logic and validation
- Test error paths (not found, validation failures, permissions)

**Integration Tests**:
- Use real database (pytest fixtures provide db_session)
- Test cross-service interactions
- Validate database constraints (unique indexes, foreign keys)
- Test transaction rollback on errors

### Coverage Target Breakdown

**Target: 80%+ overall**

High priority (90%+ coverage):
- create_product() - Core functionality
- activate_product() - Critical business rule
- get_product() - High usage

Medium priority (80%+ coverage):
- update_product()
- delete_product()
- list_products()

Lower priority (70%+ coverage):
- Vision upload helpers
- Config data helpers

### Quality Checklist
Before marking this handover complete:

- [ ] Ruff + Black compliant (no linting errors)
- [ ] Full type hints on test functions
- [ ] Comprehensive docstrings for test classes
- [ ] Multi-tenant isolation verified (4+ tests)
- [ ] All tests pass (100% pass rate)
- [ ] Coverage ≥ 80% (verified with pytest --cov)
- [ ] PR description includes test results
- [ ] PR description includes coverage snippet

---

**Document Control**:
- **Handover**: 0603
- **Created**: 2025-11-14
- **Status**: Ready for execution
