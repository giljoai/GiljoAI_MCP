"""
Integration tests for create_successor_orchestrator (Handover 0461f).

Validates that the simplified succession:
1. Does NOT create new AgentExecution rows
2. Returns the SAME agent_id (no swap)
3. Resets context_used to 0
4. Creates 360 Memory entry with session_handover type
"""

from unittest.mock import patch
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import AgentJob, Product, Project
from src.giljo_mcp.models.agent_identity import AgentExecution
from src.giljo_mcp.services.orchestration_service import OrchestrationService


@pytest_asyncio.fixture
async def test_product_and_project(db_session, test_tenant_key):
    """Create a test product and project with proper relationships."""
    # Create product
    product = Product(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        name="Test Product",
        description="Test product for succession tests",
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    # Create project linked to product
    project = Project(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        product_id=product.id,
        name="Test Project",
        description="Test project for succession tests",
        mission="Test mission for succession tests",
        status="active",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    return product, project


class TestCreateSuccessorOrchestrator:
    """Tests for the simplified create_successor_orchestrator method."""

    @pytest.mark.asyncio
    async def test_no_new_execution_created(
        self,
        db_session: AsyncSession,
        orchestration_service_with_session: OrchestrationService,
        test_tenant_key: str,
        test_product_and_project,
    ):
        """Verify NO new AgentExecution row is created during succession."""
        service = orchestration_service_with_session
        product, project = test_product_and_project

        # Create an orchestrator agent job and execution
        spawn_result = await service.spawn_agent_job(
            agent_display_name="orchestrator",
            agent_name="orchestrator-coordinator",
            mission="Coordinate project execution",
            project_id=str(project.id),
            tenant_key=test_tenant_key,
        )

        assert spawn_result.get("success") is True
        job_id = spawn_result["job_id"]
        agent_id = spawn_result["agent_id"]

        # Get initial count of AgentExecution rows
        result = await db_session.execute(select(AgentExecution).where(AgentExecution.job_id == job_id))
        executions_before = result.scalars().all()
        count_before = len(executions_before)
        assert count_before == 1  # Should have one execution from spawn

        # Update context_used to simulate work
        execution = executions_before[0]
        execution.context_used = 50000
        await db_session.commit()

        # Mock write_360_memory to avoid actual memory writes
        with patch("src.giljo_mcp.tools.write_360_memory.write_360_memory") as mock_write:
            mock_write.return_value = {"success": True, "entry_id": str(uuid4())}

            # Call create_successor_orchestrator
            result = await service.create_successor_orchestrator(
                current_job_id=job_id,
                tenant_key=test_tenant_key,
                reason="manual",
            )

        assert result["success"] is True

        # Verify count of AgentExecution rows remains the same
        result = await db_session.execute(select(AgentExecution).where(AgentExecution.job_id == job_id))
        executions_after = result.scalars().all()
        count_after = len(executions_after)

        assert count_after == count_before  # No new execution created
        assert count_after == 1  # Still just one

    @pytest.mark.asyncio
    async def test_same_agent_id_returned(
        self,
        db_session: AsyncSession,
        orchestration_service_with_session: OrchestrationService,
        test_tenant_key: str,
        test_product_and_project,
    ):
        """Verify agent_id stays the same (no swap)."""
        service = orchestration_service_with_session
        product, project = test_product_and_project

        # Create an orchestrator agent job and execution
        spawn_result = await service.spawn_agent_job(
            agent_display_name="orchestrator",
            agent_name="orchestrator-coordinator",
            mission="Coordinate project execution",
            project_id=str(project.id),
            tenant_key=test_tenant_key,
        )

        original_agent_id = spawn_result["agent_id"]
        job_id = spawn_result["job_id"]

        # Mock write_360_memory
        with patch("src.giljo_mcp.tools.write_360_memory.write_360_memory") as mock_write:
            mock_write.return_value = {"success": True, "entry_id": str(uuid4())}

            # Call create_successor_orchestrator
            result = await service.create_successor_orchestrator(
                current_job_id=job_id,
                tenant_key=test_tenant_key,
                reason="context_limit",
            )

        assert result["success"] is True
        assert result["agent_id"] == original_agent_id  # SAME agent_id, not new

        # Verify in database
        result = await db_session.execute(select(AgentExecution).where(AgentExecution.agent_id == original_agent_id))
        execution = result.scalar_one_or_none()
        assert execution is not None
        assert execution.agent_id == original_agent_id

    @pytest.mark.asyncio
    async def test_context_reset_to_zero(
        self,
        db_session: AsyncSession,
        orchestration_service_with_session: OrchestrationService,
        test_tenant_key: str,
        test_product_and_project,
    ):
        """Verify context_used is reset to 0."""
        service = orchestration_service_with_session
        product, project = test_product_and_project

        # Create an orchestrator agent job and execution
        spawn_result = await service.spawn_agent_job(
            agent_display_name="orchestrator",
            agent_name="orchestrator-coordinator",
            mission="Coordinate project execution",
            project_id=str(project.id),
            tenant_key=test_tenant_key,
        )

        job_id = spawn_result["job_id"]
        agent_id = spawn_result["agent_id"]

        # Update context_used to simulate work
        result = await db_session.execute(select(AgentExecution).where(AgentExecution.agent_id == agent_id))
        execution = result.scalar_one()
        original_context_used = 75000
        execution.context_used = original_context_used
        await db_session.commit()

        # Mock write_360_memory
        with patch("src.giljo_mcp.tools.write_360_memory.write_360_memory") as mock_write:
            mock_write.return_value = {"success": True, "entry_id": str(uuid4())}

            # Call create_successor_orchestrator
            result = await service.create_successor_orchestrator(
                current_job_id=job_id,
                tenant_key=test_tenant_key,
                reason="manual",
            )

        assert result["success"] is True
        assert result["context_reset"] is True
        assert result["old_context_used"] == original_context_used
        assert result["new_context_used"] == 0

        # Verify in database
        await db_session.refresh(execution)
        assert execution.context_used == 0  # Reset to zero

    @pytest.mark.asyncio
    async def test_360_memory_entry_created(
        self,
        db_session: AsyncSession,
        orchestration_service_with_session: OrchestrationService,
        test_tenant_key: str,
        test_product_and_project,
    ):
        """Verify 360 Memory entry is created with session_handover type."""
        service = orchestration_service_with_session
        product, project = test_product_and_project

        # Create an orchestrator agent job and execution
        spawn_result = await service.spawn_agent_job(
            agent_display_name="orchestrator",
            agent_name="orchestrator-coordinator",
            mission="Coordinate project execution",
            project_id=str(project.id),
            tenant_key=test_tenant_key,
        )

        job_id = spawn_result["job_id"]
        agent_id = spawn_result["agent_id"]

        # Update execution to have realistic state
        result = await db_session.execute(select(AgentExecution).where(AgentExecution.agent_id == agent_id))
        execution = result.scalar_one()
        execution.context_used = 80000
        execution.progress = 65
        execution.current_task = "Spawning backend agents"
        await db_session.commit()

        # Mock write_360_memory to verify it's called with correct parameters
        with patch("src.giljo_mcp.tools.write_360_memory.write_360_memory") as mock_write:
            mock_entry_id = str(uuid4())
            mock_write.return_value = {"success": True, "entry_id": mock_entry_id}

            # Call create_successor_orchestrator
            result = await service.create_successor_orchestrator(
                current_job_id=job_id,
                tenant_key=test_tenant_key,
                reason="manual",
            )

        # Verify write_360_memory was called
        assert mock_write.called
        call_args = mock_write.call_args

        # Check that it was called with correct parameters
        assert call_args.kwargs["project_id"] == str(project.id)
        assert call_args.kwargs["tenant_key"] == test_tenant_key
        assert call_args.kwargs["entry_type"] == "session_handover"
        assert call_args.kwargs["author_job_id"] == job_id

        # Verify summary contains context information
        summary = call_args.kwargs["summary"]
        assert "manual" in summary
        assert "80000" in summary  # context_used

        # Verify result indicates memory entry was created
        assert result["success"] is True
        assert result.get("memory_entry_created") is True

    @pytest.mark.asyncio
    async def test_only_orchestrators_allowed(
        self,
        db_session: AsyncSession,
        orchestration_service_with_session: OrchestrationService,
        test_tenant_key: str,
        test_product_and_project,
    ):
        """Verify only orchestrators can use succession."""
        service = orchestration_service_with_session
        product, project = test_product_and_project

        # Create a NON-orchestrator agent (implementer)
        spawn_result = await service.spawn_agent_job(
            agent_display_name="implementer",
            agent_name="backend-implementer",
            mission="Implement authentication endpoint",
            project_id=str(project.id),
            tenant_key=test_tenant_key,
        )

        job_id = spawn_result["job_id"]

        # Try to create successor for non-orchestrator
        result = await service.create_successor_orchestrator(
            current_job_id=job_id,
            tenant_key=test_tenant_key,
            reason="manual",
        )

        # Should fail with error
        assert result["success"] is False
        assert "error" in result
        assert "orchestrator" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_return_format(
        self,
        db_session: AsyncSession,
        orchestration_service_with_session: OrchestrationService,
        test_tenant_key: str,
        test_product_and_project,
    ):
        """Verify the return format includes all required fields."""
        service = orchestration_service_with_session
        product, project = test_product_and_project

        # Create an orchestrator agent job and execution
        spawn_result = await service.spawn_agent_job(
            agent_display_name="orchestrator",
            agent_name="orchestrator-coordinator",
            mission="Coordinate project execution",
            project_id=str(project.id),
            tenant_key=test_tenant_key,
        )

        job_id = spawn_result["job_id"]
        agent_id = spawn_result["agent_id"]

        # Update context_used
        result = await db_session.execute(select(AgentExecution).where(AgentExecution.agent_id == agent_id))
        execution = result.scalar_one()
        execution.context_used = 50000
        await db_session.commit()

        # Mock write_360_memory
        with patch("src.giljo_mcp.tools.write_360_memory.write_360_memory") as mock_write:
            mock_write.return_value = {"success": True, "entry_id": str(uuid4())}

            # Call create_successor_orchestrator
            result = await service.create_successor_orchestrator(
                current_job_id=job_id,
                tenant_key=test_tenant_key,
                reason="context_limit",
            )

        # Verify all required fields are present
        assert result["success"] is True
        assert "job_id" in result
        assert result["job_id"] == job_id

        assert "agent_id" in result
        assert result["agent_id"] == agent_id

        assert "context_reset" in result
        assert result["context_reset"] is True

        assert "old_context_used" in result
        assert result["old_context_used"] == 50000

        assert "new_context_used" in result
        assert result["new_context_used"] == 0

        assert "reason" in result
        assert result["reason"] == "context_limit"

        assert "message" in result
        assert "360 Memory" in result["message"]
        assert "fetch_context" in result["message"]

    @pytest.mark.asyncio
    async def test_fallback_to_job_id_lookup(
        self,
        db_session: AsyncSession,
        orchestration_service_with_session: OrchestrationService,
        test_tenant_key: str,
        test_product_and_project,
    ):
        """Verify lookup works with job_id when agent_id not provided."""
        service = orchestration_service_with_session
        product, project = test_product_and_project

        # Create an orchestrator agent job and execution
        spawn_result = await service.spawn_agent_job(
            agent_display_name="orchestrator",
            agent_name="orchestrator-coordinator",
            mission="Coordinate project execution",
            project_id=str(project.id),
            tenant_key=test_tenant_key,
        )

        job_id = spawn_result["job_id"]

        # Mock write_360_memory
        with patch("src.giljo_mcp.tools.write_360_memory.write_360_memory") as mock_write:
            mock_write.return_value = {"success": True, "entry_id": str(uuid4())}

            # Call using job_id (not agent_id)
            result = await service.create_successor_orchestrator(
                current_job_id=job_id,  # Using job_id
                tenant_key=test_tenant_key,
                reason="manual",
            )

        # Should succeed
        assert result["success"] is True
        assert result["job_id"] == job_id

    @pytest.mark.asyncio
    async def test_nonexistent_job_returns_error(
        self,
        db_session: AsyncSession,
        orchestration_service_with_session: OrchestrationService,
        test_tenant_key: str,
    ):
        """Verify error when job doesn't exist."""
        service = orchestration_service_with_session

        fake_job_id = str(uuid4())

        # Try to create successor for nonexistent job
        result = await service.create_successor_orchestrator(
            current_job_id=fake_job_id,
            tenant_key=test_tenant_key,
            reason="manual",
        )

        # Should fail with error
        assert result["success"] is False
        assert "error" in result
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_tenant_isolation(
        self,
        db_session: AsyncSession,
        orchestration_service_with_session: OrchestrationService,
        test_tenant_key: str,
        test_product_and_project,
    ):
        """Verify tenant isolation - can't access other tenant's jobs."""
        service = orchestration_service_with_session
        product, project = test_product_and_project

        # Create an orchestrator for test_tenant_key
        spawn_result = await service.spawn_agent_job(
            agent_display_name="orchestrator",
            agent_name="orchestrator-coordinator",
            mission="Coordinate project execution",
            project_id=str(project.id),
            tenant_key=test_tenant_key,
        )

        job_id = spawn_result["job_id"]

        # Try to access with different tenant_key
        different_tenant = "different-tenant-key"

        result = await service.create_successor_orchestrator(
            current_job_id=job_id,
            tenant_key=different_tenant,  # Wrong tenant
            reason="manual",
        )

        # Should fail - can't find job for this tenant
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_preserves_job_relationship(
        self,
        db_session: AsyncSession,
        orchestration_service_with_session: OrchestrationService,
        test_tenant_key: str,
        test_product_and_project,
    ):
        """Verify AgentExecution.job_id relationship is preserved."""
        service = orchestration_service_with_session
        product, project = test_product_and_project

        # Create an orchestrator agent job and execution
        spawn_result = await service.spawn_agent_job(
            agent_display_name="orchestrator",
            agent_name="orchestrator-coordinator",
            mission="Coordinate project execution",
            project_id=str(project.id),
            tenant_key=test_tenant_key,
        )

        job_id = spawn_result["job_id"]
        agent_id = spawn_result["agent_id"]

        # Mock write_360_memory
        with patch("src.giljo_mcp.tools.write_360_memory.write_360_memory") as mock_write:
            mock_write.return_value = {"success": True, "entry_id": str(uuid4())}

            # Call create_successor_orchestrator
            await service.create_successor_orchestrator(
                current_job_id=job_id,
                tenant_key=test_tenant_key,
                reason="manual",
            )

        # Verify AgentExecution still points to same AgentJob
        result = await db_session.execute(select(AgentExecution).where(AgentExecution.agent_id == agent_id))
        execution = result.scalar_one()
        assert execution.job_id == job_id

        # Verify AgentJob still exists and is linked
        result = await db_session.execute(select(AgentJob).where(AgentJob.job_id == job_id))
        job = result.scalar_one()
        assert job.job_id == job_id
        assert job.project_id == project.id
