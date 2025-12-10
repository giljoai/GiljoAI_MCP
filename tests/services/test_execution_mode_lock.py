"""
Tests for execution_mode lock after staging (Handover 0343)

BEHAVIOR TESTED:
- execution_mode can be changed BEFORE orchestrator exists
- execution_mode CANNOT be changed AFTER orchestrator exists
- Other fields CAN be changed after orchestrator exists
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import MCPAgentJob, Project
from src.giljo_mcp.services.project_service import ProjectService
from src.giljo_mcp.tenant import TenantManager


@pytest.mark.asyncio
async def test_update_execution_mode_allowed_before_staging(
    db_manager, db_session: AsyncSession, tenant_manager: TenantManager
):
    """
    GIVEN: A project with NO orchestrator job
    WHEN: Attempting to change execution_mode
    THEN: Should succeed
    """
    # Setup tenant
    tenant_key = TenantManager.generate_tenant_key()
    tenant_manager.set_current_tenant(tenant_key)

    # Create project WITHOUT orchestrator
    project = Project(
        name="Pre-Staging Project",
        mission="Test mission",
        description="Test description",
        tenant_key=tenant_key,
        status="draft",
        execution_mode="interactive",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Action: Update execution_mode (should succeed)
    service = ProjectService(db_manager, tenant_manager, test_session=db_session)
    result = await service.update_project(
        project.id,
        {"execution_mode": "autonomous"}
    )

    # Assert: Success
    assert result["success"] is True, f"Expected success, got error: {result.get('error')}"
    assert result["data"]["execution_mode"] == "autonomous"


@pytest.mark.asyncio
async def test_update_execution_mode_blocked_after_orchestrator_exists(
    db_manager, db_session: AsyncSession, tenant_manager: TenantManager
):
    """
    GIVEN: A project with an existing orchestrator job
    WHEN: Attempting to change execution_mode
    THEN: Should return error indicating mode is locked
    """
    # Setup tenant
    tenant_key = TenantManager.generate_tenant_key()
    tenant_manager.set_current_tenant(tenant_key)

    # Create project
    project = Project(
        name="Post-Staging Project",
        mission="Test mission",
        description="Test description",
        tenant_key=tenant_key,
        status="active",
        execution_mode="interactive",
    )
    db_session.add(project)
    await db_session.flush()

    # Create orchestrator job (triggers lock)
    orchestrator_job = MCPAgentJob(
        job_id="orchestrator-001",
        tenant_key=tenant_key,
        project_id=project.id,
        agent_type="orchestrator",
        mission="Orchestrate project execution",
        status="waiting",
    )
    db_session.add(orchestrator_job)
    await db_session.commit()

    # Action: Try to update execution_mode (should fail)
    service = ProjectService(db_manager, tenant_manager, test_session=db_session)
    result = await service.update_project(
        project.id,
        {"execution_mode": "autonomous"}
    )

    # Assert: Failure with specific error message
    assert result["success"] is False, "Expected failure when updating execution_mode after staging"
    assert "error" in result
    error_msg = result["error"].lower()
    assert "orchestrator" in error_msg or "staging" in error_msg, \
        f"Expected error about orchestrator/staging, got: {result['error']}"


@pytest.mark.asyncio
async def test_update_other_fields_still_allowed_after_staging(
    db_manager, db_session: AsyncSession, tenant_manager: TenantManager
):
    """
    GIVEN: A project with an existing orchestrator job
    WHEN: Updating name or description (not execution_mode)
    THEN: Should succeed - only execution_mode is locked
    """
    # Setup tenant
    tenant_key = TenantManager.generate_tenant_key()
    tenant_manager.set_current_tenant(tenant_key)

    # Create project
    project = Project(
        name="Locked Project",
        mission="Original mission",
        description="Original description",
        tenant_key=tenant_key,
        status="active",
        execution_mode="interactive",
    )
    db_session.add(project)
    await db_session.flush()

    # Create orchestrator job (triggers execution_mode lock)
    orchestrator_job = MCPAgentJob(
        job_id="orchestrator-002",
        tenant_key=tenant_key,
        project_id=project.id,
        agent_type="orchestrator",
        mission="Orchestrate project",
        status="waiting",
    )
    db_session.add(orchestrator_job)
    await db_session.commit()

    # Action: Update OTHER fields (name, description, mission)
    service = ProjectService(db_manager, tenant_manager, test_session=db_session)
    result = await service.update_project(
        project.id,
        {
            "name": "Updated Name",
            "description": "Updated description",
            "mission": "Updated mission"
        }
    )

    # Assert: Success - other fields can still be updated
    assert result["success"] is True, f"Expected success for non-execution_mode updates, got: {result.get('error')}"
    assert result["data"]["name"] == "Updated Name"
    assert result["data"]["description"] == "Updated description"
    assert result["data"]["mission"] == "Updated mission"
    assert result["data"]["execution_mode"] == "interactive"  # Should remain unchanged


@pytest.mark.asyncio
async def test_execution_mode_lock_is_tenant_isolated(
    db_manager, db_session: AsyncSession, tenant_manager: TenantManager
):
    """
    GIVEN: Two projects in different tenants, both with orchestrators
    WHEN: Attempting to update execution_mode for each
    THEN: Lock applies per-tenant (tenant A orchestrator doesn't lock tenant B project)
    """
    # Setup Tenant A
    tenant_key_a = TenantManager.generate_tenant_key()
    project_a = Project(
        name="Tenant A Project",
        mission="Mission A",
        description="Description A",
        tenant_key=tenant_key_a,
        status="active",
        execution_mode="interactive",
    )
    db_session.add(project_a)
    await db_session.flush()

    # Orchestrator for Tenant A
    orchestrator_a = MCPAgentJob(
        job_id="orchestrator-a",
        tenant_key=tenant_key_a,
        project_id=project_a.id,
        agent_type="orchestrator",
        mission="Orchestrate A",
        status="waiting",
    )
    db_session.add(orchestrator_a)

    # Setup Tenant B (no orchestrator yet)
    tenant_key_b = TenantManager.generate_tenant_key()
    project_b = Project(
        name="Tenant B Project",
        mission="Mission B",
        description="Description B",
        tenant_key=tenant_key_b,
        status="active",
        execution_mode="interactive",
    )
    db_session.add(project_b)
    await db_session.commit()

    # Action: Tenant A should be LOCKED
    tenant_manager.set_current_tenant(tenant_key_a)
    service_a = ProjectService(db_manager, tenant_manager, test_session=db_session)
    result_a = await service_a.update_project(
        project_a.id,
        {"execution_mode": "autonomous"}
    )
    assert result_a["success"] is False, "Tenant A should be locked"

    # Action: Tenant B should be UNLOCKED (no orchestrator)
    tenant_manager.set_current_tenant(tenant_key_b)
    service_b = ProjectService(db_manager, tenant_manager, test_session=db_session)
    result_b = await service_b.update_project(
        project_b.id,
        {"execution_mode": "autonomous"}
    )
    assert result_b["success"] is True, "Tenant B should be unlocked"
    assert result_b["data"]["execution_mode"] == "autonomous"
