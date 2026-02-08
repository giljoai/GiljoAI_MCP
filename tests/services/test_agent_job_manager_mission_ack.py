"""
Test mission_acknowledged_at tracking in AgentJobManager (Handover 0233)
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.services.agent_job_manager import AgentJobManager
from src.giljo_mcp.tenant import TenantManager


@pytest.fixture
def tenant_manager():
    """Create a TenantManager for testing."""
    return TenantManager()


@pytest.mark.asyncio
async def test_status_transition_to_working_sets_mission_acknowledged_at(
    db_manager: DatabaseManager, db_session: AsyncSession, tenant_manager: TenantManager
):
    """Test that transitioning to 'working' status sets mission_acknowledged_at"""
    tenant_key = TenantManager.generate_tenant_key()
    manager = AgentJobManager(db_manager, tenant_manager)

    # Create product and project for testing
    product = Product(
        id=str(uuid4()),
        tenant_key=tenant_key,
        name="Test Product",
        description="Test product for mission ack tests",
        product_memory={},
    )
    db_session.add(product)
    await db_session.commit()

    project = Project(
        id=str(uuid4()),
        tenant_key=tenant_key,
        product_id=product.id,
        name="Test Project",
        description="Test project",
        mission="Test mission",
        status="active",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(project)
    await db_session.commit()

    # Spawn agent (creates job in 'waiting' status)
    job_id, agent_id, display_name, status = await manager.spawn_agent(
        project_id=project.id,
        agent_display_name="implementer",
        mission="Test mission",
        tenant_key=tenant_key,
    )

    # Get execution to check mission_acknowledged_at
    execution = await manager.get_execution_by_agent_id(agent_id, tenant_key)
    assert execution.mission_acknowledged_at is None
    assert execution.status == "waiting"

    # Transition to 'working' status
    await manager.update_agent_status(agent_id=agent_id, status="working", tenant_key=tenant_key)

    # Verify mission_acknowledged_at is set
    execution = await manager.get_execution_by_agent_id(agent_id, tenant_key)
    assert execution.mission_acknowledged_at is not None
    assert isinstance(execution.mission_acknowledged_at, datetime)


@pytest.mark.asyncio
async def test_mission_acknowledged_at_only_set_once(
    db_manager: DatabaseManager, db_session: AsyncSession, tenant_manager: TenantManager
):
    """Test that mission_acknowledged_at is only set on FIRST transition to working"""
    tenant_key = TenantManager.generate_tenant_key()
    manager = AgentJobManager(db_manager, tenant_manager)

    # Create product and project
    product = Product(
        id=str(uuid4()),
        tenant_key=tenant_key,
        name="Test Product",
        description="Test product for mission ack tests",
        product_memory={},
    )
    db_session.add(product)
    await db_session.commit()

    project = Project(
        id=str(uuid4()),
        tenant_key=tenant_key,
        product_id=product.id,
        name="Test Project",
        description="Test project",
        mission="Test mission",
        status="active",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(project)
    await db_session.commit()

    # Spawn agent and transition to working
    job_id, agent_id, display_name, status = await manager.spawn_agent(
        project_id=project.id,
        agent_display_name="implementer",
        mission="Test mission",
        tenant_key=tenant_key,
    )

    await manager.update_agent_status(agent_id=agent_id, status="working", tenant_key=tenant_key)

    execution = await manager.get_execution_by_agent_id(agent_id, tenant_key)
    first_ack_time = execution.mission_acknowledged_at
    assert first_ack_time is not None

    # Transition to 'blocked' then back to 'working'
    await manager.update_agent_status(agent_id=agent_id, status="blocked", tenant_key=tenant_key)
    await manager.update_agent_status(agent_id=agent_id, status="working", tenant_key=tenant_key)

    # Verify timestamp UNCHANGED (idempotent)
    execution = await manager.get_execution_by_agent_id(agent_id, tenant_key)
    assert execution.mission_acknowledged_at == first_ack_time


@pytest.mark.asyncio
async def test_other_status_transitions_dont_set_mission_acknowledged_at(
    db_manager: DatabaseManager, db_session: AsyncSession, tenant_manager: TenantManager
):
    """Test that non-'working' status transitions don't set mission_acknowledged_at"""
    tenant_key = TenantManager.generate_tenant_key()
    manager = AgentJobManager(db_manager, tenant_manager)

    # Create product and project
    product = Product(
        id=str(uuid4()),
        tenant_key=tenant_key,
        name="Test Product",
        description="Test product for mission ack tests",
        product_memory={},
    )
    db_session.add(product)
    await db_session.commit()

    project = Project(
        id=str(uuid4()),
        tenant_key=tenant_key,
        product_id=product.id,
        name="Test Project",
        description="Test project",
        mission="Test mission",
        status="active",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(project)
    await db_session.commit()

    # Spawn agent
    job_id, agent_id, display_name, status = await manager.spawn_agent(
        project_id=project.id,
        agent_display_name="implementer",
        mission="Test mission",
        tenant_key=tenant_key,
    )

    execution = await manager.get_execution_by_agent_id(agent_id, tenant_key)
    assert execution.mission_acknowledged_at is None

    # Transition to 'failed' (not 'working')
    await manager.update_agent_status(agent_id=agent_id, status="failed", tenant_key=tenant_key)

    # Verify mission_acknowledged_at is still None
    execution = await manager.get_execution_by_agent_id(agent_id, tenant_key)
    assert execution.mission_acknowledged_at is None
