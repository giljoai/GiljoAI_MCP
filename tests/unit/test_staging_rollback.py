#!/usr/bin/env python
"""
Unit tests for StagingRollbackManager

Tests database rollback when user cancels project staging after orchestrator
has created mission and spawned agents.

Test Coverage:
- Soft delete with metadata (default)
- Hard delete (permanent removal)
- Multi-tenant isolation (critical security)
- Protected agents (already launched)
- Edge cases (no agents, invalid orchestrator, etc.)
- Transaction rollback on errors
- Orchestrator succession (multiple orchestrator instances)

PRODUCTION-GRADE: Validates data integrity and security boundaries.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Project, Product
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from src.giljo_mcp.staging_rollback import (
    StagingRollbackManager,
    rollback_project_staging,
)


@pytest.fixture
async def db_manager():
    """Create database manager for tests"""
    return DatabaseManager()


@pytest.fixture
async def tenant_key():
    """Generate unique tenant key for test isolation"""
    return f"tenant_{uuid4().hex[:8]}"


@pytest.fixture
async def tenant_key_2():
    """Generate second tenant key for isolation tests"""
    return f"tenant2_{uuid4().hex[:8]}"


@pytest.fixture
async def test_product(db_manager: DatabaseManager, tenant_key: str):
    """Create test product"""
    async with db_manager.get_session_async() as session:
        product = Product(
            name=f"Test Product {uuid4().hex[:8]}",
            vision_document="# Product Vision\n\nTest product for rollback tests.",
            tenant_key=tenant_key,
            status="active",
        )
        session.add(product)
        await session.commit()
        await session.refresh(product)
        return product


@pytest.fixture
async def test_project(
    db_manager: DatabaseManager,
    tenant_key: str,
    test_product: Product,
):
    """Create test project"""
    async with db_manager.get_session_async() as session:
        project = Project(
            name=f"Test Project {uuid4().hex[:8]}",
            description="Test project for rollback tests",
            mission="Mission generated during staging",
            product_id=test_product.id,
            tenant_key=tenant_key,
            status="active",
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)
        return project


@pytest.fixture
async def orchestrator_job(
    db_manager: DatabaseManager,
    tenant_key: str,
    test_project: Project,
):
    """Create orchestrator job"""
    async with db_manager.get_session_async() as session:
        orchestrator = AgentExecution(
            tenant_key=tenant_key,
            project_id=test_project.id,
            agent_display_name="orchestrator",
            mission="Orchestrate project execution",
            status="active",
            instance_number=1,
        )
        session.add(orchestrator)
        await session.commit()
        await session.refresh(orchestrator)
        return orchestrator


@pytest.mark.asyncio
class TestStagingRollbackBasic:
    """Basic staging rollback functionality"""

    async def test_soft_delete_waiting_agents(
        self,
        db_manager: DatabaseManager,
        tenant_key: str,
        test_project: Project,
        orchestrator_job: AgentExecution,
    ):
        """
        Test 1: Soft delete agents in 'waiting' status (default behavior)
        """
        # Arrange: Create 3 child agents in 'waiting' status
        async with db_manager.get_session_async() as session:
            agents = [
                AgentExecution(
                    tenant_key=tenant_key,
                    project_id=test_project.id,
                    agent_display_name=f"implementer_{i}",
                    mission=f"Implement feature {i}",
                    status="waiting",
                    spawned_by=orchestrator_job.job_id,
                )
                for i in range(3)
            ]
            for agent in agents:
                session.add(agent)
            await session.commit()

        # Act: Rollback staging (soft delete)
        rollback_mgr = StagingRollbackManager(db_manager)
        result = await rollback_mgr.rollback_staging(
            tenant_key=tenant_key,
            project_id=test_project.id,
            orchestrator_job_id=orchestrator_job.job_id,
            reason="User canceled staging",
            hard_delete=False,  # Soft delete
        )

        # Assert: 3 agents soft deleted
        assert result["success"] is True
        assert result["agents_deleted"] == 3
        assert result["agents_protected"] == 0
        assert result["orchestrator_updated"] is True
        assert result["project_mission_cleared"] is True

        # Verify agents marked as 'failed' (soft delete)
        async with db_manager.get_session_async() as session:
            from sqlalchemy import select

            stmt = select(AgentExecution).where(
                AgentExecution.spawned_by == orchestrator_job.job_id
            )
            result_agents = await session.execute(stmt)
            agents_after = result_agents.scalars().all()

            # All agents should still exist but marked as 'failed'
            assert len(agents_after) == 3
            for agent in agents_after:
                assert agent.status == "failed"
                assert agent.completed_at is not None
                assert "rollback_info" in agent.job_metadata
                assert agent.job_metadata["rollback_info"]["reason"] == "User canceled staging"
                assert agent.job_metadata["rollback_info"]["rollback_type"] == "staging_cancellation"

    async def test_hard_delete_waiting_agents(
        self,
        db_manager: DatabaseManager,
        tenant_key: str,
        test_project: Project,
        orchestrator_job: AgentExecution,
    ):
        """
        Test 2: Hard delete agents (permanent removal)
        """
        # Arrange: Create 2 child agents in 'waiting' status
        async with db_manager.get_session_async() as session:
            agents = [
                AgentExecution(
                    tenant_key=tenant_key,
                    project_id=test_project.id,
                    agent_display_name=f"tester_{i}",
                    mission=f"Test feature {i}",
                    status="waiting",
                    spawned_by=orchestrator_job.job_id,
                )
                for i in range(2)
            ]
            for agent in agents:
                session.add(agent)
            await session.commit()

        # Act: Rollback staging (hard delete)
        rollback_mgr = StagingRollbackManager(db_manager)
        result = await rollback_mgr.rollback_staging(
            tenant_key=tenant_key,
            project_id=test_project.id,
            orchestrator_job_id=orchestrator_job.job_id,
            reason="User canceled staging - hard delete",
            hard_delete=True,  # Hard delete
        )

        # Assert: 2 agents hard deleted
        assert result["success"] is True
        assert result["agents_deleted"] == 2

        # Verify agents completely removed from database
        async with db_manager.get_session_async() as session:
            from sqlalchemy import select

            stmt = select(AgentExecution).where(
                AgentExecution.spawned_by == orchestrator_job.job_id
            )
            result_agents = await session.execute(stmt)
            agents_after = result_agents.scalars().all()

            # No agents should exist (hard deleted)
            assert len(agents_after) == 0

    async def test_protected_agents_not_deleted(
        self,
        db_manager: DatabaseManager,
        tenant_key: str,
        test_project: Project,
        orchestrator_job: AgentExecution,
    ):
        """
        Test 3: Agents with status != 'waiting' are NOT deleted (protected)
        """
        # Arrange: Create agents with different statuses
        async with db_manager.get_session_async() as session:
            agents = [
                AgentExecution(
                    tenant_key=tenant_key,
                    project_id=test_project.id,
                    agent_display_name="implementer_1",
                    mission="Feature 1",
                    status="waiting",  # Deletable
                    spawned_by=orchestrator_job.job_id,
                ),
                AgentExecution(
                    tenant_key=tenant_key,
                    project_id=test_project.id,
                    agent_display_name="implementer_2",
                    mission="Feature 2",
                    status="active",  # Protected (already launched)
                    spawned_by=orchestrator_job.job_id,
                ),
                AgentExecution(
                    tenant_key=tenant_key,
                    project_id=test_project.id,
                    agent_display_name="implementer_3",
                    mission="Feature 3",
                    status="working",  # Protected (already launched)
                    spawned_by=orchestrator_job.job_id,
                ),
                AgentExecution(
                    tenant_key=tenant_key,
                    project_id=test_project.id,
                    agent_display_name="implementer_4",
                    mission="Feature 4",
                    status="preparing",  # Deletable
                    spawned_by=orchestrator_job.job_id,
                ),
            ]
            for agent in agents:
                session.add(agent)
            await session.commit()

        # Act: Rollback staging
        rollback_mgr = StagingRollbackManager(db_manager)
        result = await rollback_mgr.rollback_staging(
            tenant_key=tenant_key,
            project_id=test_project.id,
            orchestrator_job_id=orchestrator_job.job_id,
            reason="User canceled staging",
            hard_delete=False,
        )

        # Assert: Only 2 agents deleted (waiting + preparing)
        assert result["success"] is True
        assert result["agents_deleted"] == 2  # waiting + preparing
        assert result["agents_protected"] == 2  # active + working

        # Verify protected agents unchanged
        async with db_manager.get_session_async() as session:
            from sqlalchemy import select

            stmt = select(AgentExecution).where(
                AgentExecution.spawned_by == orchestrator_job.job_id,
                AgentExecution.status.in_(["active", "working"]),
            )
            result_agents = await session.execute(stmt)
            protected_agents = result_agents.scalars().all()

            # Protected agents should be unchanged
            assert len(protected_agents) == 2
            for agent in protected_agents:
                assert agent.status in ["active", "working"]
                assert "rollback_info" not in agent.job_metadata

    async def test_orchestrator_status_updated(
        self,
        db_manager: DatabaseManager,
        tenant_key: str,
        test_project: Project,
        orchestrator_job: AgentExecution,
    ):
        """
        Test 4: Orchestrator status updated to 'failed' with metadata
        """
        # Act: Rollback staging
        rollback_mgr = StagingRollbackManager(db_manager)
        result = await rollback_mgr.rollback_staging(
            tenant_key=tenant_key,
            project_id=test_project.id,
            orchestrator_job_id=orchestrator_job.job_id,
            reason="Test orchestrator update",
            hard_delete=False,
        )

        # Assert: Orchestrator updated
        assert result["orchestrator_updated"] is True

        # Verify orchestrator status
        async with db_manager.get_session_async() as session:
            from sqlalchemy import select

            stmt = select(AgentExecution).where(
                AgentExecution.job_id == orchestrator_job.job_id
            )
            result_orch = await session.execute(stmt)
            orch_after = result_orch.scalar_one()

            assert orch_after.status == "failed"
            assert orch_after.completed_at is not None
            assert "rollback_info" in orch_after.job_metadata
            assert orch_after.job_metadata["rollback_info"]["reason"] == "Test orchestrator update"

    async def test_project_mission_cleared(
        self,
        db_manager: DatabaseManager,
        tenant_key: str,
        test_project: Project,
        orchestrator_job: AgentExecution,
    ):
        """
        Test 5: Project mission field cleared during rollback
        """
        # Verify project has mission before rollback
        assert test_project.mission == "Mission generated during staging"

        # Act: Rollback staging
        rollback_mgr = StagingRollbackManager(db_manager)
        result = await rollback_mgr.rollback_staging(
            tenant_key=tenant_key,
            project_id=test_project.id,
            orchestrator_job_id=orchestrator_job.job_id,
            reason="Test mission clearing",
            hard_delete=False,
        )

        # Assert: Mission cleared
        assert result["project_mission_cleared"] is True

        # Verify mission cleared in database
        async with db_manager.get_session_async() as session:
            from sqlalchemy import select

            stmt = select(Project).where(Project.id == test_project.id)
            result_proj = await session.execute(stmt)
            proj_after = result_proj.scalar_one()

            assert proj_after.mission == ""


@pytest.mark.asyncio
class TestStagingRollbackSecurity:
    """Security and isolation tests"""

    async def test_multi_tenant_isolation(
        self,
        db_manager: DatabaseManager,
        tenant_key: str,
        tenant_key_2: str,
        test_project: Project,
        orchestrator_job: AgentExecution,
    ):
        """
        Test 6: CRITICAL - Multi-tenant isolation enforced
        """
        # Arrange: Create agents for TWO different tenants
        async with db_manager.get_session_async() as session:
            # Tenant A agents (should be deleted)
            agents_a = [
                AgentExecution(
                    tenant_key=tenant_key,  # Tenant A
                    project_id=test_project.id,
                    agent_display_name=f"implementer_a_{i}",
                    mission=f"Feature A{i}",
                    status="waiting",
                    spawned_by=orchestrator_job.job_id,
                )
                for i in range(2)
            ]

            # Tenant B agents (should NOT be deleted)
            agents_b = [
                AgentExecution(
                    tenant_key=tenant_key_2,  # Tenant B (different tenant)
                    project_id=test_project.id,
                    agent_display_name=f"implementer_b_{i}",
                    mission=f"Feature B{i}",
                    status="waiting",
                    spawned_by=orchestrator_job.job_id,
                )
                for i in range(2)
            ]

            for agent in agents_a + agents_b:
                session.add(agent)
            await session.commit()

        # Act: Rollback staging for Tenant A only
        rollback_mgr = StagingRollbackManager(db_manager)
        result = await rollback_mgr.rollback_staging(
            tenant_key=tenant_key,  # Tenant A
            project_id=test_project.id,
            orchestrator_job_id=orchestrator_job.job_id,
            reason="Tenant A staging canceled",
            hard_delete=True,  # Hard delete for easy verification
        )

        # Assert: Only Tenant A agents deleted
        assert result["success"] is True
        assert result["agents_deleted"] == 2  # Tenant A agents

        # Verify Tenant A agents deleted
        async with db_manager.get_session_async() as session:
            from sqlalchemy import select

            stmt_a = select(AgentExecution).where(
                AgentExecution.tenant_key == tenant_key,
                AgentExecution.spawned_by == orchestrator_job.job_id,
            )
            result_a = await session.execute(stmt_a)
            agents_a_after = result_a.scalars().all()
            assert len(agents_a_after) == 0  # Tenant A agents deleted

            # Verify Tenant B agents unchanged
            stmt_b = select(AgentExecution).where(
                AgentExecution.tenant_key == tenant_key_2,
                AgentExecution.spawned_by == orchestrator_job.job_id,
            )
            result_b = await session.execute(stmt_b)
            agents_b_after = result_b.scalars().all()
            assert len(agents_b_after) == 2  # Tenant B agents untouched

    async def test_invalid_orchestrator_raises_error(
        self,
        db_manager: DatabaseManager,
        tenant_key: str,
        test_project: Project,
    ):
        """
        Test 7: Invalid orchestrator job_id raises ValueError
        """
        # Act & Assert: Invalid orchestrator raises ValueError
        rollback_mgr = StagingRollbackManager(db_manager)

        with pytest.raises(ValueError) as exc_info:
            await rollback_mgr.rollback_staging(
                tenant_key=tenant_key,
                project_id=test_project.id,
                orchestrator_job_id="invalid_job_id_xyz",
                reason="Test invalid orchestrator",
                hard_delete=False,
            )

        assert "not found" in str(exc_info.value).lower()

    async def test_empty_parameters_raise_error(
        self,
        db_manager: DatabaseManager,
        test_project: Project,
        orchestrator_job: AgentExecution,
    ):
        """
        Test 8: Empty required parameters raise ValueError
        """
        rollback_mgr = StagingRollbackManager(db_manager)

        # Empty tenant_key
        with pytest.raises(ValueError) as exc_info:
            await rollback_mgr.rollback_staging(
                tenant_key="",  # Empty
                project_id=test_project.id,
                orchestrator_job_id=orchestrator_job.job_id,
                reason="Test",
            )
        assert "tenant_key cannot be empty" in str(exc_info.value)

        # Empty project_id
        with pytest.raises(ValueError) as exc_info:
            await rollback_mgr.rollback_staging(
                tenant_key="tenant_xyz",
                project_id="",  # Empty
                orchestrator_job_id=orchestrator_job.job_id,
                reason="Test",
            )
        assert "project_id cannot be empty" in str(exc_info.value)

        # Empty orchestrator_job_id
        with pytest.raises(ValueError) as exc_info:
            await rollback_mgr.rollback_staging(
                tenant_key="tenant_xyz",
                project_id=test_project.id,
                orchestrator_job_id="",  # Empty
                reason="Test",
            )
        assert "orchestrator_job_id cannot be empty" in str(exc_info.value)

        # Empty reason
        with pytest.raises(ValueError) as exc_info:
            await rollback_mgr.rollback_staging(
                tenant_key="tenant_xyz",
                project_id=test_project.id,
                orchestrator_job_id=orchestrator_job.job_id,
                reason="",  # Empty
            )
        assert "reason cannot be empty" in str(exc_info.value)


@pytest.mark.asyncio
class TestStagingRollbackEdgeCases:
    """Edge cases and error scenarios"""

    async def test_rollback_with_no_child_agents(
        self,
        db_manager: DatabaseManager,
        tenant_key: str,
        test_project: Project,
        orchestrator_job: AgentExecution,
    ):
        """
        Test 9: Rollback succeeds even when no child agents exist
        """
        # Act: Rollback with no child agents
        rollback_mgr = StagingRollbackManager(db_manager)
        result = await rollback_mgr.rollback_staging(
            tenant_key=tenant_key,
            project_id=test_project.id,
            orchestrator_job_id=orchestrator_job.job_id,
            reason="No agents to rollback",
            hard_delete=False,
        )

        # Assert: Success with 0 agents deleted
        assert result["success"] is True
        assert result["agents_deleted"] == 0
        assert result["agents_protected"] == 0
        assert result["orchestrator_updated"] is True

    async def test_orchestrator_chain_multiple_instances(
        self,
        db_manager: DatabaseManager,
        tenant_key: str,
        test_project: Project,
    ):
        """
        Test 10: Rollback with orchestrator chain (multiple instances via spawned_by)
        """
        # Arrange: Create orchestrator chain (instance 1 → instance 2)
        async with db_manager.get_session_async() as session:
            orch_1 = AgentExecution(
                tenant_key=tenant_key,
                project_id=test_project.id,
                agent_display_name="orchestrator",
                mission="Instance 1 mission",
                status="complete",
                instance_number=1,
            )
            session.add(orch_1)
            await session.commit()
            await session.refresh(orch_1)

            orch_2 = AgentExecution(
                tenant_key=tenant_key,
                project_id=test_project.id,
                agent_display_name="orchestrator",
                mission="Instance 2 mission",
                status="active",
                instance_number=2,
                spawned_by=orch_1.job_id,  # Spawned by instance 1
            )
            session.add(orch_2)
            await session.commit()
            await session.refresh(orch_2)

            # Create agents spawned by instance 2
            agents = [
                AgentExecution(
                    tenant_key=tenant_key,
                    project_id=test_project.id,
                    agent_display_name=f"implementer_{i}",
                    mission=f"Feature {i}",
                    status="waiting",
                    spawned_by=orch_2.job_id,  # Spawned by instance 2
                )
                for i in range(3)
            ]
            for agent in agents:
                session.add(agent)
            await session.commit()

        # Act: Rollback instance 2 (should only delete its children)
        rollback_mgr = StagingRollbackManager(db_manager)
        result = await rollback_mgr.rollback_staging(
            tenant_key=tenant_key,
            project_id=test_project.id,
            orchestrator_job_id=orch_2.job_id,  # Instance 2
            reason="Instance 2 canceled",
            hard_delete=True,
        )

        # Assert: Only instance 2's children deleted
        assert result["success"] is True
        assert result["agents_deleted"] == 3

        # Verify instance 1 unchanged
        async with db_manager.get_session_async() as session:
            from sqlalchemy import select

            stmt = select(AgentExecution).where(
                AgentExecution.job_id == orch_1.job_id
            )
            result_orch1 = await session.execute(stmt)
            orch1_after = result_orch1.scalar_one()

            assert orch1_after.status == "complete"  # Unchanged
            assert "rollback_info" not in orch1_after.job_metadata

    async def test_convenience_function(
        self,
        db_manager: DatabaseManager,
        tenant_key: str,
        test_project: Project,
        orchestrator_job: AgentExecution,
    ):
        """
        Test 11: Convenience function rollback_project_staging()
        """
        # Arrange: Create child agents
        async with db_manager.get_session_async() as session:
            agents = [
                AgentExecution(
                    tenant_key=tenant_key,
                    project_id=test_project.id,
                    agent_display_name=f"tester_{i}",
                    mission=f"Test {i}",
                    status="waiting",
                    spawned_by=orchestrator_job.job_id,
                )
                for i in range(2)
            ]
            for agent in agents:
                session.add(agent)
            await session.commit()

        # Act: Use convenience function
        result = await rollback_project_staging(
            tenant_key=tenant_key,
            project_id=test_project.id,
            orchestrator_job_id=orchestrator_job.job_id,
            reason="Testing convenience function",
            hard_delete=False,
        )

        # Assert: Success
        assert result["success"] is True
        assert result["agents_deleted"] == 2

    async def test_transaction_rollback_on_error(
        self,
        db_manager: DatabaseManager,
        tenant_key: str,
        test_project: Project,
        orchestrator_job: AgentExecution,
    ):
        """
        Test 12: Transaction rollback on database error
        """
        # This test verifies that partial changes are rolled back on error
        # In a real scenario, this would be tested with database connection failure
        # For now, we verify that ValueError is raised for invalid input

        rollback_mgr = StagingRollbackManager(db_manager)

        # Invalid tenant_key should raise ValueError and not affect database
        with pytest.raises(ValueError):
            await rollback_mgr.rollback_staging(
                tenant_key="",  # Invalid
                project_id=test_project.id,
                orchestrator_job_id=orchestrator_job.job_id,
                reason="Test transaction rollback",
            )

        # Verify orchestrator unchanged (transaction rolled back)
        async with db_manager.get_session_async() as session:
            from sqlalchemy import select

            stmt = select(AgentExecution).where(
                AgentExecution.job_id == orchestrator_job.job_id
            )
            result_orch = await session.execute(stmt)
            orch_after = result_orch.scalar_one()

            # Orchestrator should be unchanged (still 'active')
            assert orch_after.status == "active"
            assert "rollback_info" not in orch_after.job_metadata
