"""
TDD Tests for Tenant Isolation - TaskService and Integration Workflows

Split from test_tenant_isolation_services.py during test file reorganization.

These tests verify that TaskService database queries properly filter by tenant_key
and that cross-service integration workflows enforce tenant isolation end-to-end.

Test Strategy: RED -> GREEN -> REFACTOR

Updated (0730-fix): Tests updated for exception-based error handling (0730 series)
and Task.product_id NOT NULL constraint (0433).

Coverage:
- task_service.py: log_task() - Line 117
- Integration: Full cross-service tenant isolation workflow
"""

import pytest

from src.giljo_mcp.exceptions import ResourceNotFoundError, ValidationError


# ============================================================================
# TASK_SERVICE.PY TESTS (Line 117)
# ============================================================================


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_task_service_log_task_blocks_cross_tenant_project(db_session, two_tenant_service_setup):
    """
    Test: task_service.py log_task() - Line 117

    Verify that log_task() validates project belongs to tenant.
    Tenant A should NOT be able to log tasks to Tenant B's project.

    Updated (0730-fix): log_task now raises ResourceNotFoundError for invalid project_id
    and requires product_id (per handover 0433).
    """
    tenant_a = two_tenant_service_setup["tenant_a"]
    product_a = two_tenant_service_setup["product_a"]
    project_b = two_tenant_service_setup["project_b"]
    task_service_a = two_tenant_service_setup["task_service_a"]

    # Tenant A tries to log task to Tenant B's project - should raise ResourceNotFoundError
    with pytest.raises(ResourceNotFoundError) as exc_info:
        await task_service_a.log_task(
            product_id=product_a.id,  # Required per 0433
            project_id=project_b.id,  # Tenant B's project!
            content="Malicious task creation attempt",
            category="Cross-tenant task",
            tenant_key=tenant_a,
        )

    # Should fail - cannot log task to cross-tenant project
    # The error should indicate project validation issue
    assert "project" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_task_service_log_task_same_tenant_succeeds(db_session, two_tenant_service_setup):
    """
    Verify that same-tenant task logging still works.

    Updated (0730-fix): log_task now requires product_id (per handover 0433).
    log_task returns task_id string directly on success.
    """
    tenant_a = two_tenant_service_setup["tenant_a"]
    product_a = two_tenant_service_setup["product_a"]
    project_a = two_tenant_service_setup["project_a"]
    task_service_a = two_tenant_service_setup["task_service_a"]

    # Tenant A logs task to Tenant A's project - should succeed
    result = await task_service_a.log_task(
        product_id=product_a.id,  # Required per 0433
        project_id=project_a.id,
        content="Valid task creation",
        category="Same-tenant task",
        tenant_key=tenant_a,
    )

    # log_task returns task_id string directly on success
    # Should succeed for same-tenant (result is either a dict with task_id or a string task_id)
    if isinstance(result, dict):
        assert result.get("success") is True or result.get("task_id") is not None, "Same-tenant task logging failed!"
    else:
        # result is task_id string
        assert result is not None and isinstance(result, str), "Same-tenant task logging failed!"


# ============================================================================
# INTEGRATION TESTS - FULL WORKFLOW
# ============================================================================


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_full_tenant_isolation_workflow(db_session, two_tenant_service_setup):
    """
    Integration test: Verify complete tenant isolation across all services.

    This test attempts a full workflow of cross-tenant access attempts
    and verifies that ALL are blocked.

    Updated (0730-fix): Services now raise exceptions instead of returning
    {"success": False}, so we expect exceptions for cross-tenant access.
    """
    tenant_a = two_tenant_service_setup["tenant_a"]
    project_b = two_tenant_service_setup["project_b"]
    product_a = two_tenant_service_setup["product_a"]

    project_service_a = two_tenant_service_setup["project_service_a"]
    task_service_a = two_tenant_service_setup["task_service_a"]

    # Track violations
    violations = []

    # Test 1: Cross-tenant project access - should raise ResourceNotFoundError
    try:
        await project_service_a.get_project(project_id=project_b.id, tenant_key=tenant_a)
        violations.append("get_project() allowed cross-tenant access - no exception raised")
    except ResourceNotFoundError:
        pass  # Expected behavior

    # Test 2: Cross-tenant mission update - should raise ResourceNotFoundError
    try:
        await project_service_a.update_project_mission(
            project_id=project_b.id, mission="Hijacked mission", tenant_key=tenant_a
        )
        violations.append("update_project_mission() allowed cross-tenant modification - no exception raised")
    except ResourceNotFoundError:
        pass  # Expected behavior

    # Test 3: Cross-tenant task creation - should raise ValidationError
    try:
        await task_service_a.log_task(
            product_id=product_a.id,  # Required per 0433
            project_id=project_b.id,
            content="Cross-tenant attack",
            category="Malicious task",
            tenant_key=tenant_a,
        )
        violations.append("log_task() allowed cross-tenant creation - no exception raised")
    except (ValidationError, ResourceNotFoundError):
        pass  # Expected behavior

    # Assert no violations occurred
    assert len(violations) == 0, "CRITICAL: Tenant isolation violated!\nViolations:\n" + "\n".join(
        f"- {v}" for v in violations
    )


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_tenant_isolation_does_not_break_normal_access(db_session, two_tenant_service_setup):
    """
    Integration test: Verify that tenant isolation doesn't break normal access.

    This test performs legitimate same-tenant operations and verifies they succeed.

    Updated (0730-fix): Services now return data directly on success
    and require product_id for log_task (per handover 0433).
    """
    tenant_a = two_tenant_service_setup["tenant_a"]
    product_a = two_tenant_service_setup["product_a"]
    project_a = two_tenant_service_setup["project_a"]

    project_service_a = two_tenant_service_setup["project_service_a"]
    task_service_a = two_tenant_service_setup["task_service_a"]

    # Track failures
    failures = []

    # Test 1: Same-tenant project access - should succeed without raising exception
    try:
        result = await project_service_a.get_project(project_id=project_a.id, tenant_key=tenant_a)
        # Service returns project data dict on success
        if result is None:
            failures.append("get_project() returned None for same-tenant access")
    except Exception as e:
        failures.append(f"get_project() raised exception for same-tenant access: {e}")

    # Test 2: Same-tenant task creation - should succeed without raising exception
    try:
        result = await task_service_a.log_task(
            product_id=product_a.id,  # Required per 0433
            project_id=project_a.id,
            content="Same-tenant task",
            category="Valid task",
            tenant_key=tenant_a,
        )
        if result is None:
            failures.append("log_task() returned None for same-tenant access")
    except Exception as e:
        failures.append(f"log_task() raised exception for same-tenant access: {e}")

    # Assert no failures occurred
    assert len(failures) == 0, "Normal access broken by tenant isolation!\nFailures:\n" + "\n".join(
        f"- {f}" for f in failures
    )
