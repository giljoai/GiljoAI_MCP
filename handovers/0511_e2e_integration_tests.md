---
**Document Type:** Handover
**Handover ID:** 0511
**Title:** E2E Integration Tests - Critical Workflows
**Version:** 1.0
**Created:** 2025-11-12
**Status:** Ready for Execution
**Duration:** 12-16 hours
**Scope:** Create end-to-end integration tests for all critical workflows
**Priority:** 🔴 P0 CRITICAL
**Tool:** 🖥️ CLI
**Parallel Execution:** ❌ No (Sequential after 0510)
**Parent Project:** Projectplan_500.md
---

# Handover 0511: E2E Integration Tests - Critical Workflows

## 🎯 Mission Statement
Create comprehensive end-to-end integration tests for all critical workflows: product lifecycle, project lifecycle, vision upload, orchestrator succession, and settings management.

## 📋 Prerequisites
- ✅ Handover 0510 complete (unit tests passing)
- Live PostgreSQL database
- Backend server running
- Frontend built

## ⚠️ Problem Statement

**Evidence**: Projectplan_500.md line 88
- No integration tests for complete workflows
- Refactoring broke workflows (found via manual testing)
- **Need**: Automated tests to prevent regressions

## ✅ Solution Approach

Create pytest integration tests that:
1. Start with clean database
2. Execute complete workflows
3. Verify state at each step
4. Test error conditions

## 📝 Implementation Tasks

### Task 1: Product Lifecycle E2E (3 hours)
**File**: `tests/integration/test_product_lifecycle.py` (NEW)

```python
async def test_complete_product_lifecycle():
    """Test: create → upload vision → activate → deactivate."""
    # 1. Create product
    product = await api.products.create(name="E2E Test")
    assert product.id

    # 2. Upload vision document
    vision_docs = await api.products.upload_vision(
        product.id, large_markdown_file
    )
    assert len(vision_docs) > 1  # Chunked

    # 3. Activate product
    response = await api.products.activate(product.id)
    assert response.product.is_active

    # 4. Deactivate
    deactivated = await api.products.deactivate(product.id)
    assert not deactivated.is_active
```

### Task 2: Project Lifecycle E2E (4 hours)
**File**: `tests/integration/test_project_lifecycle.py` (NEW)

```python
async def test_complete_project_lifecycle():
    """Test: create → activate → launch orchestrator → deactivate → complete."""
    # 1. Create project
    project = await api.projects.create(name="E2E", product_id=product_id)

    # 2. Activate
    activated = await api.projects.activate(project.id)
    assert activated.status == "active"

    # 3. Launch orchestrator
    launch_response = await api.projects.launch(project.id)
    assert launch_response.orchestrator_job_id

    # 4. Verify job created
    job = await api.agent_jobs.get(launch_response.orchestrator_job_id)
    assert job.agent_type == "orchestrator"

    # 5. Deactivate
    paused = await api.projects.deactivate(project.id)
    assert paused.status == "paused"

    # 6. Complete
    completed = await api.projects.complete(project.id)
    assert completed.status == "completed"
```

### Task 3: Succession Workflow E2E (3 hours)
**File**: `tests/integration/test_succession_workflow.py` (NEW)

```python
async def test_orchestrator_succession_workflow():
    """Test: create orchestrator → trigger succession → verify chain."""
    # 1. Create orchestrator job
    job = await orchestration_service.create_orchestrator_job(
        project_id, mission="Test"
    )

    # 2. Simulate context usage
    await orchestration_service.update_context_usage(job.id, 180000)  # 90%

    # 3. Check succession status
    status = await api.agent_jobs.check_succession_status(job.id)
    assert status.needs_succession

    # 4. Trigger succession
    successor = await api.agent_jobs.trigger_succession(job.id)
    assert successor.instance_number == 2

    # 5. Verify handover fields
    original = await api.agent_jobs.get(job.id)
    assert original.handover_to == successor.successor_job_id
```

### Task 4: Settings Persistence E2E (2 hours)
**File**: `tests/integration/test_settings_persistence.py` (NEW)

```python
async def test_settings_persistence():
    """Test settings persist correctly across sessions."""
    # 1. Update general settings
    await api.settings.update_general({"theme": "dark"})

    # 2. Restart server (simulate)
    # 3. Fetch settings
    settings = await api.settings.get_general()
    assert settings.theme == "dark"
```

### Task 5: Multi-Tenant Isolation E2E (3 hours)
**File**: `tests/integration/test_tenant_isolation.py` (NEW)

```python
async def test_tenant_isolation():
    """Test tenant A cannot access tenant B data."""
    # 1. Create product as tenant A
    # 2. Try to access as tenant B
    # 3. Verify 403/404
```

### Task 6: Error Handling E2E (2 hours)
Test error scenarios:
- Duplicate product activation
- Vision upload >10MB
- Invalid succession trigger

## ✅ Success Criteria
- [ ] All E2E tests pass
- [ ] Complete workflows tested
- [ ] Error conditions tested
- [ ] Multi-tenant isolation verified
- [ ] Tests run in CI/CD

## 🔄 Rollback Plan
Tests don't affect production - safe to iterate.

## 📚 Related Handovers
**Depends on**: 0510 (unit tests), 0500-0509 (implementation)

## 🛠️ Tool Justification
**Why CLI**: Integration tests need live backend + database

## 📊 Parallel Execution
**❌ Cannot parallelize** - Sequential after 0510

---
**Status:** Ready for Execution
**Estimated Effort:** 12-16 hours
**Archive Location:** `handovers/completed/0511_e2e_integration_tests-COMPLETE.md`
