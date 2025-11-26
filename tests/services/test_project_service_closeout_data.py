"""
Unit tests for ProjectService.get_closeout_data (Handover 0249a).
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import MCPAgentJob, Product, Project
from src.giljo_mcp.services.project_service import ProjectService
from src.giljo_mcp.tenant import TenantManager


@pytest.mark.asyncio
async def test_get_closeout_data_all_agents_complete(
    db_manager, db_session: AsyncSession, tenant_manager: TenantManager
):
    """Closeout data reflects all agents completed successfully."""
    tenant_key = TenantManager.generate_tenant_key()
    tenant_manager.set_current_tenant(tenant_key)

    project = Project(
        name="Closeout Ready",
        mission="Finish the reporting module",
        description="Reporting work",
        tenant_key=tenant_key,
        status="active",
    )
    db_session.add(project)
    await db_session.flush()

    for i in range(3):
        db_session.add(
            MCPAgentJob(
                job_id=f"agent-complete-{i}",
                tenant_key=tenant_key,
                project_id=project.id,
                agent_type="developer",
                mission="Implement feature",
                status="complete",
            )
        )

    await db_session.commit()

    service = ProjectService(db_manager, tenant_manager)
    result = await service.get_closeout_data(project.id, db_session=db_session)

    assert result["success"] is True
    data = result["data"]
    assert data["agent_count"] == 3
    assert data["all_agents_complete"] is True
    assert data["has_failed_agents"] is False
    assert "close_project_and_update_memory" in data["closeout_prompt"]


@pytest.mark.asyncio
async def test_get_closeout_data_with_failed_agents(
    db_manager, db_session: AsyncSession, tenant_manager: TenantManager
):
    """Closeout data reports failed agents and incomplete status."""
    tenant_key = TenantManager.generate_tenant_key()
    tenant_manager.set_current_tenant(tenant_key)

    project = Project(
        name="Mixed Outcomes",
        mission="Ship analytics",
        description="Analytics work",
        tenant_key=tenant_key,
        status="active",
    )
    db_session.add(project)
    await db_session.flush()

    db_session.add(
        MCPAgentJob(
            job_id="agent-ok-1",
            tenant_key=tenant_key,
            project_id=project.id,
            agent_type="developer",
            mission="Implement",
            status="complete",
        )
    )
    db_session.add(
        MCPAgentJob(
            job_id="agent-failed-1",
            tenant_key=tenant_key,
            project_id=project.id,
            agent_type="tester",
            mission="Test",
            status="failed",
        )
    )
    db_session.add(
        MCPAgentJob(
            job_id="agent-working-1",
            tenant_key=tenant_key,
            project_id=project.id,
            agent_type="analyst",
            mission="Analyze",
            status="working",
        )
    )

    await db_session.commit()

    service = ProjectService(db_manager, tenant_manager)
    result = await service.get_closeout_data(project.id, db_session=db_session)

    assert result["success"] is True
    data = result["data"]
    assert data["all_agents_complete"] is False
    assert data["has_failed_agents"] is True
    assert any("failed" in item.lower() for item in data["checklist"])


@pytest.mark.asyncio
async def test_get_closeout_data_with_git_integration(
    db_manager, db_session: AsyncSession, tenant_manager: TenantManager
):
    """Closeout data reflects Git integration when enabled on the product."""
    tenant_key = TenantManager.generate_tenant_key()
    tenant_manager.set_current_tenant(tenant_key)

    product = Product(
        name="Git Product",
        tenant_key=tenant_key,
        product_memory={"git_integration": {"enabled": True, "repo_name": "demo-repo"}},
    )
    db_session.add(product)
    await db_session.flush()

    project = Project(
        name="Git Enabled Project",
        mission="Ship CLI",
        description="CLI delivery",
        tenant_key=tenant_key,
        product_id=product.id,
        status="active",
    )
    db_session.add(project)
    db_session.add(
        MCPAgentJob(
            job_id="agent-complete-git",
            tenant_key=tenant_key,
            project_id=project.id,
            agent_type="developer",
            mission="Implement",
            status="complete",
        )
    )

    await db_session.commit()

    service = ProjectService(db_manager, tenant_manager)
    result = await service.get_closeout_data(project.id, db_session=db_session)

    assert result["success"] is True
    data = result["data"]
    assert data["has_git_commits"] is True
    assert any("git" in item.lower() for item in data["checklist"])


@pytest.mark.asyncio
async def test_get_closeout_data_tenant_isolation(
    db_manager, db_session: AsyncSession, tenant_manager: TenantManager
):
    """Closeout data cannot be fetched across tenants."""
    tenant_one = TenantManager.generate_tenant_key()
    tenant_two = TenantManager.generate_tenant_key()

    project = Project(
        name="Tenant One Project",
        mission="Isolation check",
        description="Isolation test",
        tenant_key=tenant_one,
        status="active",
    )
    db_session.add(project)
    await db_session.commit()

    tenant_manager.set_current_tenant(tenant_two)
    service = ProjectService(db_manager, tenant_manager)
    result = await service.get_closeout_data(project.id)

    assert result["success"] is False
    assert "not found" in result["error"].lower()
