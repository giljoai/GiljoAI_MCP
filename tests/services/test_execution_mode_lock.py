"""
Tests for execution_mode lock after staging (Handover 0343)

BEHAVIOR TESTED:
- execution_mode can be changed BEFORE mission is generated (staging)
- execution_mode CANNOT be changed AFTER mission is generated
- Other fields CAN be changed after mission is generated

Updated for Handover 0730: Exception-based patterns (no success wrapper)
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.exceptions import ProjectStateError
from src.giljo_mcp.models import Project
from src.giljo_mcp.services.project_service import ProjectService
from src.giljo_mcp.tenant import TenantManager


@pytest.mark.asyncio
async def test_update_execution_mode_allowed_before_staging(
    db_manager, db_session: AsyncSession, tenant_manager: TenantManager
):
    """
    GIVEN: A project with NO mission (staging not complete)
    WHEN: Attempting to change execution_mode
    THEN: Should succeed
    """
    # Setup tenant
    tenant_key = TenantManager.generate_tenant_key()
    tenant_manager.set_current_tenant(tenant_key)

    # Create project WITHOUT mission (empty = no staging yet)
    project = Project(
        name="Pre-Staging Project",
        mission="",  # Empty - no staging
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
    result = await service.update_project(project.id, {"execution_mode": "autonomous"})

    # Handover 0731c: Returns ProjectData model (typed returns)
    assert result.execution_mode == "autonomous"
    assert result.id == project.id


@pytest.mark.asyncio
async def test_update_execution_mode_blocked_after_mission_generated(
    db_manager, db_session: AsyncSession, tenant_manager: TenantManager
):
    """
    GIVEN: A project with a generated mission (staging complete)
    WHEN: Attempting to change execution_mode
    THEN: Should raise ProjectStateError
    """
    # Setup tenant
    tenant_key = TenantManager.generate_tenant_key()
    tenant_manager.set_current_tenant(tenant_key)

    # Create project WITH mission (staging complete)
    project = Project(
        name="Post-Staging Project",
        mission="This is the orchestrator-generated mission for the project.",
        description="Test description",
        tenant_key=tenant_key,
        status="active",
        execution_mode="interactive",
    )
    db_session.add(project)
    await db_session.commit()

    # Action: Try to update execution_mode (should raise ProjectStateError)
    service = ProjectService(db_manager, tenant_manager, test_session=db_session)

    # Handover 0730: Exception-based pattern
    with pytest.raises(ProjectStateError) as exc_info:
        await service.update_project(project.id, {"execution_mode": "autonomous"})

    # Assert: Error message indicates mission/staging lock
    error_msg = str(exc_info.value).lower()
    assert "mission" in error_msg or "staging" in error_msg, (
        f"Expected error about mission/staging, got: {exc_info.value}"
    )


@pytest.mark.asyncio
async def test_update_other_fields_still_allowed_after_staging(
    db_manager, db_session: AsyncSession, tenant_manager: TenantManager
):
    """
    GIVEN: A project with a generated mission (staging complete)
    WHEN: Updating name or description (not execution_mode)
    THEN: Should succeed - only execution_mode is locked
    """
    # Setup tenant
    tenant_key = TenantManager.generate_tenant_key()
    tenant_manager.set_current_tenant(tenant_key)

    # Create project with mission (staged)
    project = Project(
        name="Locked Project",
        mission="Original generated mission",
        description="Original description",
        tenant_key=tenant_key,
        status="active",
        execution_mode="interactive",
    )
    db_session.add(project)
    await db_session.commit()

    # Action: Update OTHER fields (name, description)
    service = ProjectService(db_manager, tenant_manager, test_session=db_session)
    result = await service.update_project(
        project.id,
        {
            "name": "Updated Name",
            "description": "Updated description",
        },
    )

    # Handover 0731c: Returns ProjectData model (typed returns)
    assert result.name == "Updated Name"
    assert result.description == "Updated description"
    assert result.execution_mode == "interactive"  # Should remain unchanged


@pytest.mark.asyncio
async def test_execution_mode_unlocked_with_whitespace_only_mission(
    db_manager, db_session: AsyncSession, tenant_manager: TenantManager
):
    """
    GIVEN: A project with whitespace-only mission (not real staging)
    WHEN: Attempting to change execution_mode
    THEN: Should succeed (whitespace doesn't count as staging)
    """
    # Setup tenant
    tenant_key = TenantManager.generate_tenant_key()
    tenant_manager.set_current_tenant(tenant_key)

    # Create project with whitespace mission
    project = Project(
        name="Whitespace Mission Project",
        mission="   \n\t  ",  # Whitespace only
        description="Test description",
        tenant_key=tenant_key,
        status="draft",
        execution_mode="interactive",
    )
    db_session.add(project)
    await db_session.commit()

    # Action: Update execution_mode (should succeed - whitespace doesn't count)
    service = ProjectService(db_manager, tenant_manager, test_session=db_session)
    result = await service.update_project(project.id, {"execution_mode": "autonomous"})

    # Handover 0731c: Returns ProjectData model (typed returns)
    assert result.execution_mode == "autonomous"
