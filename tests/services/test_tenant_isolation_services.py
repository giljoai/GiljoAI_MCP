"""
TDD Tests for Tenant Isolation in Service Layer (Handover 0325)

These tests verify that all service layer database queries properly filter by tenant_key
to prevent cross-tenant data access.

Test Strategy: RED -> GREEN -> REFACTOR
- All tests should FAIL initially (RED phase)
- Fix production code to make tests pass (GREEN phase)
- Refactor for clarity (REFACTOR phase)

Coverage:
- message_service.py: send_message() - Line 111
- project_service.py: get_project(), update_mission(), get_or_create_session() - Lines 201, 438, 1950
- task_service.py: log_task() - Line 117
"""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select

from src.giljo_mcp.models import Product, Project, Task
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from src.giljo_mcp.tenant import TenantManager


# ============================================================================
# FIXTURES
# ============================================================================


@pytest_asyncio.fixture(scope="function")
async def two_tenant_service_setup(db_session, db_manager):
    """
    Create entities in two separate tenants for service layer testing.

    Returns a dict with entities for both tenants plus service instances.
    """
    from src.giljo_mcp.services.message_service import MessageService
    from src.giljo_mcp.services.project_service import ProjectService
    from src.giljo_mcp.services.task_service import TaskService

    tenant_a = TenantManager.generate_tenant_key()
    tenant_b = TenantManager.generate_tenant_key()

    # Create Product A for Tenant A
    product_a = Product(
        id=str(uuid.uuid4()),
        name="Service Test Product A",
        description="Product for tenant A service testing",
        tenant_key=tenant_a,
        is_active=True,
    )
    db_session.add(product_a)

    # Create Product B for Tenant B
    product_b = Product(
        id=str(uuid.uuid4()),
        name="Service Test Product B",
        description="Product for tenant B service testing",
        tenant_key=tenant_b,
        is_active=True,
    )
    db_session.add(product_b)

    await db_session.commit()
    await db_session.refresh(product_a)
    await db_session.refresh(product_b)

    # Create Project A for Tenant A
    project_a = Project(
        id=str(uuid.uuid4()),
        name="Service Test Project A",
        description="Project for tenant A service testing",
        mission="Test mission A",
        tenant_key=tenant_a,
        product_id=product_a.id,
        status="active",
    )
    db_session.add(project_a)

    # Create Project B for Tenant B
    project_b = Project(
        id=str(uuid.uuid4()),
        name="Service Test Project B",
        description="Project for tenant B service testing",
        mission="Test mission B",
        tenant_key=tenant_b,
        product_id=product_b.id,
        status="active",
    )
    db_session.add(project_b)

    await db_session.commit()
    await db_session.refresh(project_a)
    await db_session.refresh(project_b)

    # Create MCPAgentJob A for Tenant A
    # Valid status values: 'waiting', 'working', 'blocked', 'complete', 'failed', 'cancelled', 'decommissioned'
    agent_job_a = AgentExecution(
        job_id=str(uuid.uuid4()),
        tenant_key=tenant_a,
        project_id=project_a.id,
        agent_display_name="orchestrator",
        mission="Test orchestrator mission A",
        status="working",  # Valid status for active agent
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(agent_job_a)

    # Create MCPAgentJob B for Tenant B
    agent_job_b = AgentExecution(
        job_id=str(uuid.uuid4()),
        tenant_key=tenant_b,
        project_id=project_b.id,
        agent_display_name="orchestrator",
        mission="Test orchestrator mission B",
        status="working",  # Valid status for active agent
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(agent_job_b)

    await db_session.commit()
    await db_session.refresh(agent_job_a)
    await db_session.refresh(agent_job_b)

    # Create service instances for Tenant A (using test_session)
    tenant_manager = TenantManager()

    message_service_a = MessageService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        test_session=db_session,
    )

    project_service_a = ProjectService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        test_session=db_session,
    )

    task_service_a = TaskService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        session=db_session,  # TaskService uses 'session' not 'test_session'
    )

    return {
        "tenant_a": tenant_a,
        "tenant_b": tenant_b,
        "product_a": product_a,
        "product_b": product_b,
        "project_a": project_a,
        "project_b": project_b,
        "agent_job_a": agent_job_a,
        "agent_job_b": agent_job_b,
        "message_service_a": message_service_a,
        "project_service_a": project_service_a,
        "task_service_a": task_service_a,
        "db_manager": db_manager,
        "tenant_manager": tenant_manager,
    }


# ============================================================================
# MESSAGE_SERVICE.PY TESTS (Line 111)
# ============================================================================


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_message_service_send_message_blocks_cross_tenant_project(db_session, two_tenant_service_setup):
    """
    Test: message_service.py send_message() - Line 111

    Verify that send_message() validates project belongs to sender's tenant.
    Tenant A should NOT be able to send messages to Tenant B's project.
    """
    tenant_a = two_tenant_service_setup["tenant_a"]
    project_b = two_tenant_service_setup["project_b"]
    agent_job_a = two_tenant_service_setup["agent_job_a"]
    message_service_a = two_tenant_service_setup["message_service_a"]

    # Tenant A tries to send message to Tenant B's project
    result = await message_service_a.send_message(
        from_agent=agent_job_a.job_id,
        to_agents=["all"],  # Broadcast to all agents
        content="Cross-tenant test message",
        project_id=project_b.id,  # Tenant B's project!
        tenant_key=tenant_a,
    )

    # Should fail - cannot send to cross-tenant project
    assert result.get("success") is False or result.get("error") is not None, \
        "Cross-tenant message send allowed! Security vulnerability at message_service.py:111"


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_message_service_same_tenant_succeeds(db_session, two_tenant_service_setup):
    """
    Verify that same-tenant message sending still works.
    """
    tenant_a = two_tenant_service_setup["tenant_a"]
    project_a = two_tenant_service_setup["project_a"]
    agent_job_a = two_tenant_service_setup["agent_job_a"]
    message_service_a = two_tenant_service_setup["message_service_a"]

    # Tenant A sends message to Tenant A's project - should succeed
    result = await message_service_a.send_message(
        from_agent=agent_job_a.job_id,
        to_agents=["all"],  # Broadcast to all agents
        content="Same-tenant test message",
        project_id=project_a.id,  # Tenant A's project
        tenant_key=tenant_a,
    )

    # Should succeed for same-tenant
    assert result.get("success") is True or result.get("message_id") is not None, \
        "Same-tenant message send failed!"


# ============================================================================
# PROJECT_SERVICE.PY TESTS (Lines 201, 438, 1950)
# ============================================================================


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_project_service_get_project_blocks_cross_tenant(db_session, two_tenant_service_setup):
    """
    Test: project_service.py get_project() - Line 201

    Verify that get_project() filters by tenant_key.
    Tenant A should NOT be able to get Tenant B's project by ID.
    """
    tenant_a = two_tenant_service_setup["tenant_a"]
    project_b = two_tenant_service_setup["project_b"]
    project_service_a = two_tenant_service_setup["project_service_a"]

    # Tenant A tries to get Tenant B's project
    result = await project_service_a.get_project(
        project_id=project_b.id,  # Tenant B's project!
        tenant_key=tenant_a,
    )

    # Should fail or return None - cannot access cross-tenant project
    assert result is None or result.get("success") is False or result.get("error") is not None, \
        "Cross-tenant project access allowed! Security vulnerability at project_service.py:201"


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_project_service_get_project_same_tenant_succeeds(db_session, two_tenant_service_setup):
    """
    Verify that same-tenant get_project() still works.
    """
    tenant_a = two_tenant_service_setup["tenant_a"]
    project_a = two_tenant_service_setup["project_a"]
    project_service_a = two_tenant_service_setup["project_service_a"]

    # Tenant A gets Tenant A's project - should succeed
    result = await project_service_a.get_project(
        project_id=project_a.id,
        tenant_key=tenant_a,
    )

    # Should succeed for same-tenant
    assert result is not None, "Same-tenant get_project() failed!"
    if isinstance(result, dict):
        assert result.get("success") is True or "id" in result, "Same-tenant get_project() returned error"


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_project_service_update_mission_blocks_cross_tenant(db_session, two_tenant_service_setup):
    """
    Test: project_service.py update_mission() - Line 438

    Verify that update_mission() filters by tenant_key.
    Tenant A should NOT be able to update Tenant B's project mission.
    """
    tenant_a = two_tenant_service_setup["tenant_a"]
    project_b = two_tenant_service_setup["project_b"]
    project_service_a = two_tenant_service_setup["project_service_a"]

    # Tenant A tries to update Tenant B's project mission
    result = await project_service_a.update_project_mission(
        project_id=project_b.id,  # Tenant B's project!
        mission="Malicious mission update attempt",
        tenant_key=tenant_a,
    )

    # Should fail - cannot update cross-tenant project
    assert result is None or result.get("success") is False or result.get("error") is not None, \
        "Cross-tenant mission update allowed! Security vulnerability at project_service.py:438"

    # Verify mission was NOT changed
    await db_session.refresh(project_b)
    assert project_b.mission == "Test mission B", \
        "Cross-tenant mission was modified! Data corruption."


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_project_service_switch_project_blocks_cross_tenant(db_session, two_tenant_service_setup):
    """
    Test: project_service.py switch_project() - Line 1950

    Verify that switch_project() filters by tenant_key.
    Tenant A should NOT be able to switch to Tenant B's project.
    """
    tenant_a = two_tenant_service_setup["tenant_a"]
    project_b = two_tenant_service_setup["project_b"]
    project_service_a = two_tenant_service_setup["project_service_a"]

    # Tenant A tries to switch to Tenant B's project
    result = await project_service_a.switch_project(
        project_id=project_b.id,  # Tenant B's project!
        tenant_key=tenant_a,
    )

    # Should fail - cannot switch to cross-tenant project
    assert result is None or result.get("success") is False or result.get("error") is not None, \
        "Cross-tenant project switch allowed! Security vulnerability at project_service.py:1950"


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
    """
    tenant_a = two_tenant_service_setup["tenant_a"]
    project_b = two_tenant_service_setup["project_b"]
    task_service_a = two_tenant_service_setup["task_service_a"]

    # Tenant A tries to log task to Tenant B's project
    result = await task_service_a.log_task(
        project_id=project_b.id,  # Tenant B's project!
        content="Malicious task creation attempt",
        category="Cross-tenant task",
        tenant_key=tenant_a,
    )

    # Should fail - cannot log task to cross-tenant project
    assert result is None or result.get("success") is False or result.get("error") is not None, \
        "Cross-tenant task logging allowed! Security vulnerability at task_service.py:117"


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_task_service_log_task_same_tenant_succeeds(db_session, two_tenant_service_setup):
    """
    Verify that same-tenant task logging still works.
    """
    tenant_a = two_tenant_service_setup["tenant_a"]
    project_a = two_tenant_service_setup["project_a"]
    task_service_a = two_tenant_service_setup["task_service_a"]

    # Tenant A logs task to Tenant A's project - should succeed
    result = await task_service_a.log_task(
        project_id=project_a.id,
        content="Valid task creation",
        category="Same-tenant task",
        tenant_key=tenant_a,
    )

    # Should succeed for same-tenant
    assert result is not None and (result.get("success") is True or result.get("task_id") is not None), \
        "Same-tenant task logging failed!"


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
    """
    tenant_a = two_tenant_service_setup["tenant_a"]
    tenant_b = two_tenant_service_setup["tenant_b"]
    project_a = two_tenant_service_setup["project_a"]
    project_b = two_tenant_service_setup["project_b"]

    message_service_a = two_tenant_service_setup["message_service_a"]
    project_service_a = two_tenant_service_setup["project_service_a"]
    task_service_a = two_tenant_service_setup["task_service_a"]

    # Track violations
    violations = []

    # Test 1: Cross-tenant project access
    result = await project_service_a.get_project(project_id=project_b.id, tenant_key=tenant_a)
    if result and (result.get("success") is True or "id" in str(result)):
        violations.append("get_project() allowed cross-tenant access")

    # Test 2: Cross-tenant mission update
    result = await project_service_a.update_project_mission(
        project_id=project_b.id,
        mission="Hijacked mission",
        tenant_key=tenant_a
    )
    if result and result.get("success") is True:
        violations.append("update_project_mission() allowed cross-tenant modification")

    # Test 3: Cross-tenant task creation
    result = await task_service_a.log_task(
        project_id=project_b.id,
        content="Cross-tenant attack",
        category="Malicious task",
        tenant_key=tenant_a
    )
    if result and (result.get("success") is True or result.get("task_id")):
        violations.append("log_task() allowed cross-tenant creation")

    # Assert no violations occurred
    assert len(violations) == 0, \
        f"CRITICAL: Tenant isolation violated!\nViolations:\n" + "\n".join(f"- {v}" for v in violations)


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_tenant_isolation_does_not_break_normal_access(db_session, two_tenant_service_setup):
    """
    Integration test: Verify that tenant isolation doesn't break normal access.

    This test performs legitimate same-tenant operations and verifies they succeed.
    """
    tenant_a = two_tenant_service_setup["tenant_a"]
    project_a = two_tenant_service_setup["project_a"]

    project_service_a = two_tenant_service_setup["project_service_a"]
    task_service_a = two_tenant_service_setup["task_service_a"]

    # Track failures
    failures = []

    # Test 1: Same-tenant project access
    result = await project_service_a.get_project(project_id=project_a.id, tenant_key=tenant_a)
    if result is None or (isinstance(result, dict) and result.get("success") is False):
        failures.append("get_project() failed for same-tenant access")

    # Test 2: Same-tenant task creation
    result = await task_service_a.log_task(
        project_id=project_a.id,
        content="Same-tenant task",
        category="Valid task",
        tenant_key=tenant_a
    )
    if result is None or (isinstance(result, dict) and result.get("success") is False):
        failures.append("log_task() failed for same-tenant access")

    # Assert no failures occurred
    assert len(failures) == 0, \
        f"Normal access broken by tenant isolation!\nFailures:\n" + "\n".join(f"- {f}" for f in failures)
