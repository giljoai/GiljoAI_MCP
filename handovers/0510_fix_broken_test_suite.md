---
**Document Type:** Handover
**Handover ID:** 0510
**Title:** Fix Broken Test Suite - Restore 80%+ Coverage
**Version:** 1.0
**Created:** 2025-11-12
**Status:** Ready for Execution
**Duration:** 8-12 hours
**Scope:** Fix broken pytest tests from refactoring, restore 80%+ coverage
**Priority:** 🔴 P0 CRITICAL
**Tool:** 🖥️ CLI
**Parallel Execution:** ❌ No (Sequential after Phase 2)
**Parent Project:** Projectplan_500.md
---

# Handover 0510: Fix Broken Test Suite - Restore 80%+ Coverage

## 🎯 Mission Statement
Fix broken test suite from Handovers 0120-0130 refactoring. Update tests to use new service layer patterns, fix database fixtures, restore 80%+ test coverage.

## 📋 Prerequisites
- ✅ Phase 0-2 complete (Services, Endpoints, Frontend)
- Local PostgreSQL running
- Python virtual environment with pytest

## ⚠️ Problem Statement

**Evidence**: Projectplan_500.md line 170
- Tests broken after refactoring (0120-0130)
- Import errors (modules moved)
- Fixture errors (database schema changes)
- Service layer tests missing for new methods
- **Impact**: Cannot validate fixes, regression risk high

## ✅ Solution Approach

1. Fix imports (update paths after refactoring)
2. Update database fixtures (new schemas)
3. Add tests for new service methods (0500-0502)
4. Fix broken endpoint tests (0503-0506)
5. Achieve 80%+ coverage

## 📝 Implementation Tasks

### Task 1: Fix Test Imports (2 hours)
```python
# Old (broken)
from src.giljo_mcp.product_manager import ProductManager

# New (fixed)
from src.giljo_mcp.services.product_service import ProductService
```

**Files to update**:
- `tests/services/test_product_service.py`
- `tests/services/test_project_service.py`
- `tests/api/test_products.py`
- `tests/api/test_projects.py`

### Task 2: Update Database Fixtures (2 hours)
```python
# tests/conftest.py
@pytest.fixture
async def db_session():
    """Create test database session."""
    # Update schema to match current models
    # Add context_used, context_budget fields
    # Add succession fields
```

### Task 3: Add ProductService Tests (2 hours)
```python
# tests/services/test_product_service.py
async def test_upload_vision_document_chunking():
    """Test vision document chunking >25K tokens."""
    large_doc = "# Header\n" + ("Word " * 10000)
    chunks = await service.upload_vision_document(
        product_id, large_doc, "vision.md"
    )
    assert len(chunks) > 1

async def test_config_data_persistence():
    """Test config_data persists correctly."""
    product = await service.create_product(
        name="Test",
        config_data={"key": "value"}
    )
    assert product.config_data == {"key": "value"}
```

### Task 4: Add ProjectService Tests (2 hours)
```python
# tests/services/test_project_service.py
async def test_activate_project_single_active_constraint():
    """Test Single Active Project constraint."""
    # Activate project 1
    # Activate project 2
    # Assert project 1 auto-paused

async def test_get_project_summary_metrics():
    """Test summary includes job metrics."""
    # Create project with jobs
    # Verify summary accuracy
```

### Task 5: Add OrchestrationService Tests (2 hours)
```python
# tests/services/test_orchestration_service.py (NEW)
async def test_context_tracking_increments():
    """Test context_used increments on messages."""
    job = await service.create_orchestrator_job(...)
    await service.update_context_usage(job.id, 1000)
    assert job.context_used == initial + 1000

async def test_auto_succession_at_90_percent():
    """Test succession triggers at 90% context."""
    # Set low context_budget
    # Push to 91%
    # Verify successor created
```

### Task 6: Fix Endpoint Tests (2 hours)
Update API tests to match new endpoint structure from 0503-0506.

## ✅ Success Criteria
- [ ] All pytest tests pass
- [ ] Coverage >80%
- [ ] Zero import errors
- [ ] Database fixtures work
- [ ] New service methods have tests
- [ ] CI/CD pipeline passes

## 🔄 Rollback Plan
Tests don't affect production - safe to iterate.

## 📚 Related Handovers
**Depends on**: 0500-0509 (all previous phases)
**Blocks**: 0511 (E2E tests need unit tests passing first)

## 🛠️ Tool Justification
**Why CLI**: Pytest requires local database, fixtures, full environment

## 📊 Parallel Execution
**❌ Cannot parallelize** - Sequential after Phase 2

---
**Status:** Ready for Execution
**Estimated Effort:** 8-12 hours
**Archive Location:** `handovers/completed/0510_fix_broken_test_suite-COMPLETE.md`
