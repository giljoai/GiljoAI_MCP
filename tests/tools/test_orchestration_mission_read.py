"""
Test mission_read_at tracking in get_orchestrator_instructions() tool - Handover 0233
"""
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import and_, select

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Product, Project
from src.giljo_mcp.models.agents import MCPAgentJob
from src.giljo_mcp.tools.orchestration import get_orchestrator_instructions


@pytest.mark.asyncio
async def test_get_orchestrator_instructions_sets_mission_read_at(db_manager: DatabaseManager):
    """
    Test that calling get_orchestrator_instructions() sets mission_read_at timestamp.

    Verifies:
    - mission_read_at is None before first call
    - mission_read_at is set after first call
    - mission_read_at is NOT updated on subsequent calls (idempotent)
    """
    tenant_key = str(uuid.uuid4())

    async with db_manager.get_session_async() as session:
        # Create product
        product = Product(
            id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            name="Test Product",
            description="Test product for mission read tracking",
            is_active=True
        )
        session.add(product)
        await session.flush()

        # Create project
        project = Project(
            id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name="Test Project",
            description="Test project requirements",
            mission="Test mission",
            status="active"
        )
        session.add(project)
        await session.flush()

        # Create orchestrator job (mission_read_at should be None initially)
        orchestrator = MCPAgentJob(
            job_id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            project_id=project.id,
            agent_type="orchestrator",
            agent_name="TestOrchestrator",
            status="waiting",
            mission="Test orchestrator mission",
            context_budget=150000,
            context_used=0,
            job_metadata={
                "field_priorities": {},
                "user_id": str(uuid.uuid4())
            }
        )
        session.add(orchestrator)
        await session.commit()

        orchestrator_id = orchestrator.job_id

        # Verify mission_read_at is None before first call
        result = await session.execute(
            select(MCPAgentJob).where(MCPAgentJob.job_id == orchestrator_id)
        )
        job = result.scalar_one()
        assert job.mission_read_at is None, "mission_read_at should be None initially"

    # FIRST CALL: Should set mission_read_at
    first_call_time = datetime.now(timezone.utc)
    result1 = await get_orchestrator_instructions(db_manager=db_manager, 
        orchestrator_id=orchestrator_id,
        tenant_key=tenant_key
    )

    assert "error" not in result1, f"First call failed: {result1.get('message')}"

    # Verify mission_read_at was set
    async with db_manager.get_session_async() as session:
        result = await session.execute(
            select(MCPAgentJob).where(MCPAgentJob.job_id == orchestrator_id)
        )
        job = result.scalar_one()
        assert job.mission_read_at is not None, "mission_read_at should be set after first call"
        assert job.mission_read_at >= first_call_time, "mission_read_at should be recent"

        first_read_timestamp = job.mission_read_at

    # SECOND CALL: Should NOT update mission_read_at (idempotent)
    result2 = await get_orchestrator_instructions(db_manager=db_manager, 
        orchestrator_id=orchestrator_id,
        tenant_key=tenant_key
    )

    assert "error" not in result2, f"Second call failed: {result2.get('message')}"

    # Verify mission_read_at was NOT updated
    async with db_manager.get_session_async() as session:
        result = await session.execute(
            select(MCPAgentJob).where(MCPAgentJob.job_id == orchestrator_id)
        )
        job = result.scalar_one()
        assert job.mission_read_at == first_read_timestamp, (
            "mission_read_at should NOT be updated on subsequent calls (idempotent)"
        )


@pytest.mark.asyncio
async def test_mission_read_at_multi_tenant_isolation(db_manager: DatabaseManager):
    """
    Test that mission_read_at tracking respects multi-tenant isolation.
    """
    tenant_key_1 = f"test-tenant-{uuid.uuid4()}"
    tenant_key_2 = f"test-tenant-{uuid.uuid4()}"

    async with db_manager.get_session_async() as session:
        # Create orchestrator for tenant 1
        product1 = Product(
            id=str(uuid.uuid4()),
            tenant_key=tenant_key_1,
            name="Product 1",
            description="Product 1",
            is_active=True
        )
        session.add(product1)
        await session.flush()

        project1 = Project(
            id=str(uuid.uuid4()),
            tenant_key=tenant_key_1,
            product_id=product1.id,
            name="Project 1",
            description="Project 1",
            mission="Test mission",
            status="active"
        )
        session.add(project1)
        await session.flush()

        orchestrator1 = MCPAgentJob(
            job_id=str(uuid.uuid4()),
            tenant_key=tenant_key_1,
            project_id=project1.id,
            agent_type="orchestrator",
            agent_name="Orchestrator1",
            status="waiting",
            mission="Mission 1",
            job_metadata={"field_priorities": {}}
        )
        session.add(orchestrator1)

        # Create orchestrator for tenant 2 (same job_id, different tenant)
        product2 = Product(
            id=str(uuid.uuid4()),
            tenant_key=tenant_key_2,
            name="Product 2",
            description="Product 2",
            is_active=True
        )
        session.add(product2)
        await session.flush()

        project2 = Project(
            id=str(uuid.uuid4()),
            tenant_key=tenant_key_2,
            product_id=product2.id,
            name="Project 2",
            description="Project 2",
            mission="Test mission",
            status="active"
        )
        session.add(project2)
        await session.flush()

        orchestrator2 = MCPAgentJob(
            job_id=orchestrator1.job_id,  # Same job_id
            tenant_key=tenant_key_2,  # Different tenant
            project_id=project2.id,
            agent_type="orchestrator",
            agent_name="Orchestrator2",
            status="waiting",
            mission="Mission 2",
            job_metadata={"field_priorities": {}}
        )
        session.add(orchestrator2)
        await session.commit()

        job_id = orchestrator1.job_id

    # Call with tenant_key_2
    result = await get_orchestrator_instructions(db_manager=db_manager, 
        orchestrator_id=job_id,
        tenant_key=tenant_key_2
    )

    # Should succeed for tenant_key_2 (not tenant_key_1)
    assert "error" not in result, "Should succeed for correct tenant"

    # Verify only tenant_key_2's job has mission_read_at set
    async with db_manager.get_session_async() as session:
        result = await session.execute(
            select(MCPAgentJob).where(
                and_(
                    MCPAgentJob.job_id == job_id,
                    MCPAgentJob.tenant_key == tenant_key_1
                )
            )
        )
        job1 = result.scalar_one()
        assert job1.mission_read_at is None, "Tenant 1 job should not have mission_read_at set"

        result = await session.execute(
            select(MCPAgentJob).where(
                and_(
                    MCPAgentJob.job_id == job_id,
                    MCPAgentJob.tenant_key == tenant_key_2
                )
            )
        )
        job2 = result.scalar_one()
        assert job2.mission_read_at is not None, "Tenant 2 job should have mission_read_at set"
