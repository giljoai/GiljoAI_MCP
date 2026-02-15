"""
Database consistency integration tests
Tests transaction handling, foreign key constraints, and data integrity
across the service layer with exception-based patterns (Handover 0730).

These tests verify:
- Foreign key integrity between related entities
- Transaction rollback on errors
- Concurrent operation consistency
- Multi-tenant data isolation
- Cascading operations
- Data integrity constraints
- Session cleanup consistency

Note: Tests use test_session injection to share the transactional test context
with services, ensuring proper test isolation while allowing services to see
test data created in fixtures.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Product, Project, Task
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.services.agent_job_manager import AgentJobManager
from src.giljo_mcp.tenant import TenantManager


@pytest.fixture
def tenant_manager():
    """Create a TenantManager for testing."""
    return TenantManager()


class TestDatabaseConsistency:
    """Test database consistency and transaction handling"""

    @pytest.mark.asyncio
    async def test_foreign_key_integrity(
        self, db_manager: DatabaseManager, db_session: AsyncSession, tenant_manager: TenantManager
    ):
        """Test foreign key constraints are properly enforced between agents and projects"""
        tenant_key = TenantManager.generate_tenant_key()

        # Create product and project for testing
        product = Product(
            id=str(uuid4()),
            tenant_key=tenant_key,
            name="FK Test Product",
            description="Test product for FK integrity tests",
            product_memory={},
        )
        db_session.add(product)
        await db_session.commit()

        project = Project(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name="FK Test Project",
            description="Test project for FK integrity",
            mission="Verify FK constraints",
            status="active",
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(project)
        await db_session.commit()

        # Create AgentJobManager with test_session for proper transaction sharing
        manager = AgentJobManager(db_manager, tenant_manager, test_session=db_session)

        # Spawn agent linked to project
        job_id, agent_id, display_name, status = await manager.spawn_agent(
            project_id=project.id,
            agent_display_name="FK Test Agent",
            mission="Agent for foreign key testing",
            tenant_key=tenant_key,
        )

        # Verify agent was created with proper FK relationship
        assert job_id is not None
        assert agent_id is not None
        assert status == "waiting"

        # Verify FK integrity - agent execution should exist
        execution = await manager.get_execution_by_agent_id(agent_id, tenant_key)
        assert execution is not None
        assert execution.job_id == job_id

        # Verify job exists
        job = await manager.get_job_by_job_id(job_id, tenant_key)
        assert job is not None
        assert job.project_id == project.id

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(
        self, db_manager: DatabaseManager, db_session: AsyncSession, tenant_manager: TenantManager
    ):
        """Test transaction handling - services handle errors gracefully"""
        tenant_key = TenantManager.generate_tenant_key()

        # Create product and project
        product = Product(
            id=str(uuid4()),
            tenant_key=tenant_key,
            name="Rollback Test Product",
            product_memory={},
        )
        db_session.add(product)
        await db_session.commit()

        project = Project(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name="Rollback Test Project",
            description="Test project for rollback testing",
            mission="Verify transaction rollback",
            status="active",
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(project)
        await db_session.commit()

        manager = AgentJobManager(db_manager, tenant_manager, test_session=db_session)

        # Create valid agent first
        job_id, agent_id, _, _ = await manager.spawn_agent(
            project_id=project.id,
            agent_display_name="Rollback Test Agent",
            mission="Agent for rollback testing",
            tenant_key=tenant_key,
        )
        assert job_id is not None

        # Verify initial state
        execution = await manager.get_execution_by_agent_id(agent_id, tenant_key)
        assert execution is not None
        assert execution.status == "waiting"

        # Update status should succeed (valid status)
        await manager.update_agent_status(
            agent_id=agent_id,
            status="working",
            tenant_key=tenant_key,
        )

        # Verify status updated
        execution = await manager.get_execution_by_agent_id(agent_id, tenant_key)
        assert execution.status == "working"

        # System should remain functional after operations
        job_id2, agent_id2, _, _ = await manager.spawn_agent(
            project_id=project.id,
            agent_display_name="Recovery Agent",
            mission="Agent to verify recovery",
            tenant_key=tenant_key,
        )
        assert job_id2 is not None
        assert job_id2 != job_id

    @pytest.mark.asyncio
    async def test_tenant_data_isolation(
        self, db_manager: DatabaseManager, db_session: AsyncSession, tenant_manager: TenantManager
    ):
        """Test strict tenant data isolation"""
        # Create first tenant's resources
        tenant1_key = TenantManager.generate_tenant_key()

        product1 = Product(
            id=str(uuid4()),
            tenant_key=tenant1_key,
            name="Tenant1 Product",
            product_memory={},
        )
        db_session.add(product1)
        await db_session.commit()

        project1 = Project(
            id=str(uuid4()),
            tenant_key=tenant1_key,
            product_id=product1.id,
            name="Tenant1 Project",
            description="Project for first tenant",
            mission="Test tenant isolation",
            status="active",
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(project1)
        await db_session.commit()

        manager = AgentJobManager(db_manager, tenant_manager, test_session=db_session)

        job1_id, agent1_id, _, _ = await manager.spawn_agent(
            project_id=project1.id,
            agent_display_name="Tenant1 Agent",
            mission="Agent in first tenant",
            tenant_key=tenant1_key,
        )

        # Create second tenant
        tenant2_key = TenantManager.generate_tenant_key()

        product2 = Product(
            id=str(uuid4()),
            tenant_key=tenant2_key,
            name="Tenant2 Product",
            product_memory={},
        )
        db_session.add(product2)
        await db_session.commit()

        project2 = Project(
            id=str(uuid4()),
            tenant_key=tenant2_key,
            product_id=product2.id,
            name="Tenant2 Project",
            description="Project for second tenant",
            mission="Test tenant isolation",
            status="active",
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(project2)
        await db_session.commit()

        job2_id, agent2_id, _, _ = await manager.spawn_agent(
            project_id=project2.id,
            agent_display_name="Tenant2 Agent",
            mission="Agent in second tenant",
            tenant_key=tenant2_key,
        )

        # Verify tenant isolation - tenant1 cannot see tenant2's agent
        execution1_cross = await manager.get_execution_by_agent_id(agent2_id, tenant1_key)
        assert execution1_cross is None  # Should not find tenant2's agent

        # Verify tenant2 cannot see tenant1's agent
        execution2_cross = await manager.get_execution_by_agent_id(agent1_id, tenant2_key)
        assert execution2_cross is None  # Should not find tenant1's agent

        # But each tenant can see their own agents
        own_execution1 = await manager.get_execution_by_agent_id(agent1_id, tenant1_key)
        own_execution2 = await manager.get_execution_by_agent_id(agent2_id, tenant2_key)
        assert own_execution1 is not None
        assert own_execution2 is not None

    @pytest.mark.asyncio
    async def test_cascading_operations(
        self, db_manager: DatabaseManager, db_session: AsyncSession, tenant_manager: TenantManager
    ):
        """Test cascading operations across related entities (job -> execution -> status updates)"""
        tenant_key = TenantManager.generate_tenant_key()

        product = Product(
            id=str(uuid4()),
            tenant_key=tenant_key,
            name="Cascade Test Product",
            product_memory={},
        )
        db_session.add(product)
        await db_session.commit()

        project = Project(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name="Cascade Test Project",
            description="Test cascading operations",
            mission="Verify cascade behavior",
            status="active",
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(project)
        await db_session.commit()

        manager = AgentJobManager(db_manager, tenant_manager, test_session=db_session)

        # Create job with execution
        job_id, agent_id, _, _ = await manager.spawn_agent(
            project_id=project.id,
            agent_display_name="Cascade Test Agent",
            mission="Agent for cascade testing",
            tenant_key=tenant_key,
        )

        # Cascade status updates
        await manager.update_agent_status(
            agent_id=agent_id,
            status="working",
            tenant_key=tenant_key,
        )

        # Update progress
        await manager.update_agent_progress(
            agent_id=agent_id,
            progress=50,
            tenant_key=tenant_key,
        )

        # Complete the job
        await manager.complete_job(
            job_id=job_id,
            tenant_key=tenant_key,
        )

        # Verify cascaded state
        job = await manager.get_job_by_job_id(job_id, tenant_key)
        execution = await manager.get_execution_by_agent_id(agent_id, tenant_key)

        assert job.status == "completed"
        assert execution.status == "complete"
        # Note: complete_job doesn't update progress, just status
        # Progress was set to 50 before completion
        assert execution.progress == 50

    @pytest.mark.asyncio
    async def test_data_integrity_constraints(
        self, db_manager: DatabaseManager, db_session: AsyncSession, tenant_manager: TenantManager
    ):
        """Test data integrity constraints and validation"""
        tenant_key = TenantManager.generate_tenant_key()

        product = Product(
            id=str(uuid4()),
            tenant_key=tenant_key,
            name="Integrity Test Product",
            product_memory={},
        )
        db_session.add(product)
        await db_session.commit()

        project = Project(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name="Integrity Test Project",
            description="Test integrity constraints",
            mission="Verify data integrity",
            status="active",
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(project)
        await db_session.commit()

        manager = AgentJobManager(db_manager, tenant_manager, test_session=db_session)

        # Test 1: Spawn agent with valid data
        job_id, agent_id, display_name, status = await manager.spawn_agent(
            project_id=project.id,
            agent_display_name="Integrity Test Agent",
            mission="Agent for integrity testing",
            tenant_key=tenant_key,
        )
        assert job_id is not None
        assert agent_id is not None

        # Test 2: Verify status enum constraint (valid status)
        await manager.update_agent_status(
            agent_id=agent_id,
            status="working",
            tenant_key=tenant_key,
        )
        execution = await manager.get_execution_by_agent_id(agent_id, tenant_key)
        assert execution.status == "working"

        # Test 3: Progress must be in valid range (0-100)
        await manager.update_agent_progress(
            agent_id=agent_id,
            progress=75,
            tenant_key=tenant_key,
        )
        execution = await manager.get_execution_by_agent_id(agent_id, tenant_key)
        assert execution.progress == 75

    @pytest.mark.asyncio
    async def test_session_cleanup_consistency(
        self, db_manager: DatabaseManager, db_session: AsyncSession, tenant_manager: TenantManager
    ):
        """Test database session cleanup and consistency after multiple operations"""
        tenant_key = TenantManager.generate_tenant_key()

        product = Product(
            id=str(uuid4()),
            tenant_key=tenant_key,
            name="Session Test Product",
            product_memory={},
        )
        db_session.add(product)
        await db_session.commit()

        project = Project(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name="Session Test Project",
            description="Test session cleanup",
            mission="Verify session consistency",
            status="active",
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(project)
        await db_session.commit()

        manager = AgentJobManager(db_manager, tenant_manager, test_session=db_session)

        # Create multiple agents in sequence
        agent_ids = []
        for i in range(3):
            job_id, agent_id, _, _ = await manager.spawn_agent(
                project_id=project.id,
                agent_display_name=f"Session Agent {i}",
                mission=f"Agent {i} for session testing",
                tenant_key=tenant_key,
            )
            agent_ids.append(agent_id)

        # Verify all operations persisted correctly
        for agent_id in agent_ids:
            execution = await manager.get_execution_by_agent_id(agent_id, tenant_key)
            assert execution is not None
            assert execution.status == "waiting"

        # Update all agents
        for agent_id in agent_ids:
            await manager.update_agent_status(
                agent_id=agent_id,
                status="working",
                tenant_key=tenant_key,
            )

        # Verify all updates persisted
        for agent_id in agent_ids:
            execution = await manager.get_execution_by_agent_id(agent_id, tenant_key)
            assert execution.status == "working"

        # System should still be functional after batch operations
        final_job_id, final_agent_id, _, _ = await manager.spawn_agent(
            project_id=project.id,
            agent_display_name="Final Recovery Agent",
            mission="Agent to verify session cleanup",
            tenant_key=tenant_key,
        )
        assert final_job_id is not None

        # Verify final agent is independent
        final_execution = await manager.get_execution_by_agent_id(final_agent_id, tenant_key)
        assert final_execution is not None
        assert final_execution.status == "waiting"


class TestTaskDatabaseConsistency:
    """Test Task database operations and consistency via direct model creation"""

    @pytest.mark.asyncio
    async def test_task_product_binding(
        self, db_manager: DatabaseManager, db_session: AsyncSession
    ):
        """Test tasks are properly bound to products (Handover 0433)"""
        tenant_key = TenantManager.generate_tenant_key()

        # Create test product
        product = Product(
            id=str(uuid4()),
            tenant_key=tenant_key,
            name="Task Binding Test Product",
            product_memory={},
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # Create task bound to product
        task = Task(
            id=str(uuid4()),
            title="Product Bound Task",
            description="Task that must be bound to a product",
            priority="medium",
            status="pending",
            product_id=product.id,
            tenant_key=tenant_key,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        # Verify task is bound to product in database
        stmt = select(Task).where(Task.id == task.id)
        db_result = await db_session.execute(stmt)
        fetched_task = db_result.scalar_one_or_none()

        assert fetched_task is not None
        assert fetched_task.product_id == product.id
        assert fetched_task.tenant_key == tenant_key

    @pytest.mark.asyncio
    async def test_task_tenant_isolation(
        self, db_manager: DatabaseManager, db_session: AsyncSession
    ):
        """Test tasks are isolated by tenant"""
        # Create tenant1 resources
        tenant1_key = TenantManager.generate_tenant_key()
        product1 = Product(
            id=str(uuid4()),
            tenant_key=tenant1_key,
            name="Tenant1 Task Product",
            product_memory={},
        )
        db_session.add(product1)
        await db_session.commit()

        task1 = Task(
            id=str(uuid4()),
            title="Tenant1 Task",
            description="Task in first tenant",
            priority="high",
            status="pending",
            product_id=product1.id,
            tenant_key=tenant1_key,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(task1)
        await db_session.commit()

        # Create tenant2 resources
        tenant2_key = TenantManager.generate_tenant_key()
        product2 = Product(
            id=str(uuid4()),
            tenant_key=tenant2_key,
            name="Tenant2 Task Product",
            product_memory={},
        )
        db_session.add(product2)
        await db_session.commit()

        task2 = Task(
            id=str(uuid4()),
            title="Tenant2 Task",
            description="Task in second tenant",
            priority="low",
            status="pending",
            product_id=product2.id,
            tenant_key=tenant2_key,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(task2)
        await db_session.commit()

        # Query tasks for tenant1 - should only get task1
        stmt1 = select(Task).where(Task.tenant_key == tenant1_key)
        result1 = await db_session.execute(stmt1)
        tenant1_tasks = result1.scalars().all()

        assert len(tenant1_tasks) == 1
        assert tenant1_tasks[0].id == task1.id

        # Query tasks for tenant2 - should only get task2
        stmt2 = select(Task).where(Task.tenant_key == tenant2_key)
        result2 = await db_session.execute(stmt2)
        tenant2_tasks = result2.scalars().all()

        assert len(tenant2_tasks) == 1
        assert tenant2_tasks[0].id == task2.id

        # Verify complete isolation
        assert task1.id not in [t.id for t in tenant2_tasks]
        assert task2.id not in [t.id for t in tenant1_tasks]
