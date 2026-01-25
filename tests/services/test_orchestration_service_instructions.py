"""
Tests for OrchestrationService instruction-related methods (Handover 0451 - Phase 1: RED).

These methods are being moved from tool_accessor.py to OrchestrationService:
- get_orchestrator_instructions() - Returns orchestrator context with framing-based instructions
- create_successor_orchestrator() - Creates successor execution, marks current as decommissioned
- update_agent_mission() - Updates AgentJob.mission field

NOTE: check_succession_status() tests removed in Handover 0461a (manual succession only).

All tests should FAIL initially (RED phase) since the methods don't exist yet in OrchestrationService.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.giljo_mcp.services.orchestration_service import OrchestrationService
from src.giljo_mcp.models import Product, Project, AgentTemplate
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution


# ============================================================================
# TestGetOrchestratorInstructions
# ============================================================================


class TestGetOrchestratorInstructions:
    """Tests for get_orchestrator_instructions() method."""

    @pytest.mark.asyncio
    async def test_returns_framing_based_context(
        self, db_session: AsyncSession, test_product, test_project
    ):
        """Test returns identity, project_description_inline, context_fetch_instructions, agent_templates."""
        # Ensure test_product uses same tenant_key as test_project
        test_product.tenant_key = test_project.tenant_key
        await db_session.commit()
        await db_session.refresh(test_product)

        # Link test_project to test_product
        test_project.product_id = test_product.id
        await db_session.commit()
        await db_session.refresh(test_project)

        # Setup: Create orchestrator job and execution
        orchestrator_job = AgentJob(

            job_id=str(uuid4()),
            job_type="orchestrator",
            tenant_key=test_project.tenant_key,
            project_id=test_project.id,
            mission="Orchestrate the project",
            status="active",  # AgentJob status: active, completed, cancelled
            job_metadata={"user_id": str(uuid4())},
        )
        db_session.add(orchestrator_job)
        await db_session.commit()

        orchestrator_execution = AgentExecution(
            agent_id=str(uuid4()),
            job_id=orchestrator_job.job_id,
            tenant_key=test_project.tenant_key,
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            instance_number=1,
            status="waiting",
            context_used=5000,
            context_budget=150000,
        )
        db_session.add(orchestrator_execution)
        await db_session.commit()

        # Create service
        service = OrchestrationService(db_manager=MagicMock(), tenant_manager=MagicMock(), websocket_manager=MagicMock())
        service._test_session = db_session

        # Act: Get orchestrator instructions
        result = await service.get_orchestrator_instructions(
            job_id=orchestrator_job.job_id,
            tenant_key=test_project.tenant_key,
        )

        # Assert: Returns framing-based context structure
        assert "identity" in result
        assert "job_id" in result["identity"]
        assert "agent_id" in result["identity"]
        assert "project_id" in result["identity"]
        assert "tenant_key" in result["identity"]

        assert "project_description_inline" in result
        assert "description" in result["project_description_inline"]
        assert "mission" in result["project_description_inline"]

        assert "context_fetch_instructions" in result
        assert isinstance(result["context_fetch_instructions"], dict)

        assert "agent_templates" in result
        assert isinstance(result["agent_templates"], list)

        assert "mcp_tools_available" in result
        assert isinstance(result["mcp_tools_available"], list)

        assert result["context_budget"] == 150000
        assert result["context_used"] == 5000

    @pytest.mark.asyncio
    async def test_validates_job_id_required(self, db_session: AsyncSession, test_project):
        """Test returns error if job_id is empty."""
        # Create service
        service = OrchestrationService(db_manager=MagicMock(), tenant_manager=MagicMock(), websocket_manager=MagicMock())
        service._test_session = db_session

        # Act: Call with empty job_id
        result = await service.get_orchestrator_instructions(
            job_id="",
            tenant_key=test_project.tenant_key,
        )

        # Assert: Returns validation error
        assert "error" in result
        assert result["error"] == "VALIDATION_ERROR"
        assert "Job ID is required" in result["message"]

    @pytest.mark.asyncio
    async def test_validates_tenant_key_required(self, db_session: AsyncSession):
        """Test returns error if tenant_key is empty."""
        # Create service
        service = OrchestrationService(db_manager=MagicMock(), tenant_manager=MagicMock(), websocket_manager=MagicMock())
        service._test_session = db_session

        # Act: Call with empty tenant_key
        result = await service.get_orchestrator_instructions(
            job_id=str(uuid4()),
            tenant_key="",
        )

        # Assert: Returns validation error
        assert "error" in result
        assert result["error"] == "VALIDATION_ERROR"
        assert "Tenant key is required" in result["message"]

    @pytest.mark.asyncio
    async def test_validates_job_is_orchestrator(
        self, db_session: AsyncSession, test_project
    ):
        """Test returns error if job_type != 'orchestrator'."""
        # Setup: Create non-orchestrator job (implementer)
        implementer_job = AgentJob(
            job_id=str(uuid4()),
            job_type="implementer",  # NOT orchestrator
            tenant_key=test_project.tenant_key,
            project_id=test_project.id,
            mission="Implement features",
            status="active",  # AgentJob: active, completed, cancelled
        )
        db_session.add(implementer_job)
        await db_session.commit()

        implementer_execution = AgentExecution(
            agent_id=str(uuid4()),
            job_id=implementer_job.job_id,
            tenant_key=test_project.tenant_key,
            agent_display_name="implementer",
            agent_name="implementer",
            instance_number=1,
            status="waiting",
        )
        db_session.add(implementer_execution)
        await db_session.commit()

        # Create service
        service = OrchestrationService(db_manager=MagicMock(), tenant_manager=MagicMock(), websocket_manager=MagicMock())
        service._test_session = db_session

        # Act: Call with implementer job
        result = await service.get_orchestrator_instructions(
            job_id=implementer_job.job_id,
            tenant_key=test_project.tenant_key,
        )

        # Assert: Returns validation error
        assert "error" in result
        assert result["error"] == "VALIDATION_ERROR"
        assert "not an orchestrator" in result["message"]

    @pytest.mark.asyncio
    async def test_enforces_tenant_isolation(self, db_session: AsyncSession, test_product):
        """Test enforces multi-tenant isolation (wrong tenant returns NOT_FOUND)."""
        tenant_a = "tenant-a"
        tenant_b = "tenant-b"

        # Setup: Create product in tenant A (need product for project)
        product_a = Product(
            id=str(uuid4()),
            name="Product A",
            tenant_key=tenant_a,
            is_active=True,
            product_memory={},
        )
        db_session.add(product_a)
        await db_session.commit()

        # Setup: Create orchestrator in tenant A
        project_a = Project(
            id=str(uuid4()),
            name="Project A",
            description="Project in tenant A",
            mission="Test mission for tenant A",  # Required field
            tenant_key=tenant_a,
            product_id=product_a.id,
        )
        db_session.add(project_a)
        await db_session.commit()

        orchestrator_job_a = AgentJob(
            job_id=str(uuid4()),
            job_type="orchestrator",
            tenant_key=tenant_a,
            project_id=project_a.id,
            mission="Orchestrate project A",
            status="active",  # AgentJob: active, completed, cancelled
        )
        db_session.add(orchestrator_job_a)
        await db_session.commit()

        orchestrator_execution_a = AgentExecution(
            agent_id=str(uuid4()),
            job_id=orchestrator_job_a.job_id,
            tenant_key=tenant_a,
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            instance_number=1,
            status="waiting",
        )
        db_session.add(orchestrator_execution_a)
        await db_session.commit()

        # Create service
        service = OrchestrationService(db_manager=MagicMock(), tenant_manager=MagicMock(), websocket_manager=MagicMock())
        service._test_session = db_session

        # Act: Tenant B tries to access tenant A's orchestrator
        result = await service.get_orchestrator_instructions(
            job_id=orchestrator_job_a.job_id,
            tenant_key=tenant_b,  # Different tenant
        )

        # Assert: Returns NOT_FOUND error
        assert "error" in result
        assert result["error"] == "NOT_FOUND"


# ============================================================================
# TestCreateSuccessorOrchestrator
# ============================================================================


class TestCreateSuccessorOrchestrator:
    """Tests for create_successor_orchestrator() method."""

    @pytest.mark.asyncio
    async def test_creates_successor_execution(
        self, db_session: AsyncSession, test_project
    ):
        """Test creates new AgentExecution with incremented instance_number."""
        # Setup: Create current orchestrator execution
        current_job = AgentJob(
            job_id=str(uuid4()),
            job_type="orchestrator",
            tenant_key=test_project.tenant_key,
            project_id=test_project.id,
            mission="Original orchestrator mission",
            status="active",  # AgentJob: active, completed, cancelled
        )
        db_session.add(current_job)
        await db_session.commit()

        current_execution = AgentExecution(
            agent_id=str(uuid4()),
            job_id=current_job.job_id,
            tenant_key=test_project.tenant_key,
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            instance_number=1,
            status="waiting",
            context_used=140000,
            context_budget=150000,
        )
        db_session.add(current_execution)
        await db_session.commit()

        # Create service
        service = OrchestrationService(db_manager=MagicMock(), tenant_manager=MagicMock(), websocket_manager=MagicMock())
        service._test_session = db_session

        # Act: Create successor
        result = await service.create_successor_orchestrator(
            current_job_id=current_job.job_id,
            tenant_key=test_project.tenant_key,
            reason="context_limit",
        )

        # Assert: Successor created
        assert result["success"] is True
        assert "successor_id" in result  # New agent_id
        assert result["job_id"] == current_job.job_id  # Same job_id
        assert result["instance_number"] == 2  # Incremented

        # Verify successor execution exists in database
        successor_result = await db_session.execute(
            select(AgentExecution).where(
                AgentExecution.job_id == current_job.job_id,
                AgentExecution.instance_number == 2,
            )
        )
        successor = successor_result.scalar_one_or_none()
        assert successor is not None
        assert successor.status == "waiting"
        assert successor.spawned_by == current_execution.agent_id

    @pytest.mark.asyncio
    async def test_marks_current_decommissioned(
        self, db_session: AsyncSession, test_project
    ):
        """Test marks current execution as 'decommissioned'."""
        # Setup: Create current orchestrator execution
        current_job = AgentJob(
            job_id=str(uuid4()),
            job_type="orchestrator",
            tenant_key=test_project.tenant_key,
            project_id=test_project.id,
            mission="Original orchestrator mission",
            status="active",  # AgentJob: active, completed, cancelled
        )
        db_session.add(current_job)
        await db_session.commit()

        current_agent_id = str(uuid4())
        current_execution = AgentExecution(
            agent_id=current_agent_id,
            job_id=current_job.job_id,
            tenant_key=test_project.tenant_key,
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            instance_number=1,
            status="waiting",
            context_used=140000,
            context_budget=150000,
        )
        db_session.add(current_execution)
        await db_session.commit()

        # Create service
        service = OrchestrationService(db_manager=MagicMock(), tenant_manager=MagicMock(), websocket_manager=MagicMock())
        service._test_session = db_session

        # Act: Create successor
        result = await service.create_successor_orchestrator(
            current_job_id=current_job.job_id,
            tenant_key=test_project.tenant_key,
            reason="context_limit",
        )

        # Assert: Current execution marked decommissioned
        await db_session.refresh(current_execution)
        assert current_execution.status == "decommissioned"
        assert current_execution.succeeded_by == result["successor_id"]
        assert current_execution.completed_at is not None

    @pytest.mark.asyncio
    async def test_preserves_job_id(
        self, db_session: AsyncSession, test_project
    ):
        """Test same job_id, different agent_id."""
        # Setup: Create current orchestrator execution
        current_job = AgentJob(
            job_id=str(uuid4()),
            job_type="orchestrator",
            tenant_key=test_project.tenant_key,
            project_id=test_project.id,
            mission="Original orchestrator mission",
            status="active",  # AgentJob: active, completed, cancelled
        )
        db_session.add(current_job)
        await db_session.commit()

        current_agent_id = str(uuid4())
        current_execution = AgentExecution(
            agent_id=current_agent_id,
            job_id=current_job.job_id,
            tenant_key=test_project.tenant_key,
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            instance_number=1,
            status="waiting",
            context_used=140000,
            context_budget=150000,
        )
        db_session.add(current_execution)
        await db_session.commit()

        # Create service
        service = OrchestrationService(db_manager=MagicMock(), tenant_manager=MagicMock(), websocket_manager=MagicMock())
        service._test_session = db_session

        # Act: Create successor
        result = await service.create_successor_orchestrator(
            current_job_id=current_job.job_id,
            tenant_key=test_project.tenant_key,
            reason="context_limit",
        )

        # Assert: Same job_id, different agent_id
        assert result["success"] is True
        assert result["job_id"] == current_job.job_id
        assert result["successor_id"] != current_agent_id  # Different agent_id

    @pytest.mark.asyncio
    async def test_rejects_already_completed(
        self, db_session: AsyncSession, test_project
    ):
        """Test returns error if job already completed."""
        # Setup: Create completed orchestrator job
        completed_job = AgentJob(
            job_id=str(uuid4()),
            job_type="orchestrator",
            tenant_key=test_project.tenant_key,
            project_id=test_project.id,
            mission="Completed orchestrator mission",
            status="completed",  # Already completed
        )
        db_session.add(completed_job)
        await db_session.commit()

        completed_execution = AgentExecution(
            agent_id=str(uuid4()),
            job_id=completed_job.job_id,
            tenant_key=test_project.tenant_key,
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            instance_number=1,
            status="complete",  # AgentExecution: waiting, working, blocked, complete, failed, cancelled, decommissioned
        )
        db_session.add(completed_execution)
        await db_session.commit()

        # Create service
        service = OrchestrationService(db_manager=MagicMock(), tenant_manager=MagicMock(), websocket_manager=MagicMock())
        service._test_session = db_session

        # Act: Try to create successor
        result = await service.create_successor_orchestrator(
            current_job_id=completed_job.job_id,
            tenant_key=test_project.tenant_key,
            reason="context_limit",
        )

        # Assert: Returns error
        assert result["success"] is False
        assert "already completed" in result["error"]


# ============================================================================
# TestCheckSuccessionStatus
# ============================================================================


@pytest.mark.skip(reason="Test class removed in Handover 0461a - check_succession_status() deleted (manual succession only)")
class TestCheckSuccessionStatus:
    """
    DEPRECATED: This test class tested check_succession_status() which was removed in Handover 0461a.
    Succession is now manual-only via UI or /gil_handover command.
    """

    @pytest.mark.asyncio
    async def test_placeholder(self):
        """Placeholder to prevent pytest collection errors."""
        pass


# NOTE: The following tests were removed in Handover 0461a:
# - test_returns_context_metrics
# - test_returns_recommendation (healthy, monitor, prepare, trigger scenarios)
# - test_should_trigger_at_90_percent
# All tested the deleted check_succession_status() method.

# ============================================================================
# TestUpdateAgentMission
# ============================================================================


class TestUpdateAgentMission:
    """Tests for update_agent_mission() method."""

    @pytest.mark.asyncio
    async def test_updates_job_mission(
        self, db_session: AsyncSession, test_project
    ):
        """Test mission field updated in database."""
        # Setup: Create agent job with original mission
        agent_job = AgentJob(

            job_id=str(uuid4()),
            job_type="orchestrator",
            tenant_key=test_project.tenant_key,
            project_id=test_project.id,
            mission="Original mission",
            status="active",  # AgentJob: active, completed, cancelled
        )
        db_session.add(agent_job)
        await db_session.commit()

        # Create service
        service = OrchestrationService(db_manager=MagicMock(), tenant_manager=MagicMock(), websocket_manager=MagicMock())
        service._test_session = db_session

        # Act: Update mission
        new_mission = "Updated mission with execution plan"
        result = await service.update_agent_mission(
            job_id=agent_job.job_id,
            tenant_key=test_project.tenant_key,
            mission=new_mission,
        )

        # Assert: Mission updated
        assert result["success"] is True
        assert result["mission_updated"] is True

        # Verify in database
        await db_session.refresh(agent_job)
        assert agent_job.mission == new_mission

    @pytest.mark.asyncio
    async def test_returns_not_found_for_invalid_job(
        self, db_session: AsyncSession, test_project
    ):
        """Test returns error for non-existent job."""
        # Create service
        service = OrchestrationService(db_manager=MagicMock(), tenant_manager=MagicMock(), websocket_manager=MagicMock())
        service._test_session = db_session

        # Act: Update mission for non-existent job
        result = await service.update_agent_mission(
            job_id=str(uuid4()),  # Non-existent
            tenant_key=test_project.tenant_key,
            mission="New mission",
        )

        # Assert: Returns NOT_FOUND error
        assert "error" in result
        assert result["error"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_enforces_tenant_isolation(self, db_session: AsyncSession, test_product):
        """Test wrong tenant returns NOT_FOUND."""
        tenant_a = "tenant-a"
        tenant_b = "tenant-b"

        # Setup: Create product in tenant A
        product_a = Product(
            id=str(uuid4()),
            name="Product A",
            tenant_key=tenant_a,
            is_active=True,
            product_memory={},
        )
        db_session.add(product_a)
        await db_session.commit()

        # Setup: Create job in tenant A
        project_a = Project(
            id=str(uuid4()),
            name="Project A",
            description="Project in tenant A",
            mission="Test mission for tenant A",  # Required field
            tenant_key=tenant_a,
            product_id=product_a.id,
        )
        db_session.add(project_a)
        await db_session.commit()

        job_a = AgentJob(
            job_id=str(uuid4()),
            job_type="orchestrator",
            tenant_key=tenant_a,
            project_id=project_a.id,
            mission="Original mission in tenant A",
            status="active",  # AgentJob: active, completed, cancelled
        )
        db_session.add(job_a)
        await db_session.commit()

        # Create service
        service = OrchestrationService(db_manager=MagicMock(), tenant_manager=MagicMock(), websocket_manager=MagicMock())
        service._test_session = db_session

        # Act: Tenant B tries to update tenant A's job
        result = await service.update_agent_mission(
            job_id=job_a.job_id,
            tenant_key=tenant_b,  # Different tenant
            mission="Malicious mission update",
        )

        # Assert: Returns NOT_FOUND error
        assert "error" in result
        assert result["error"] == "NOT_FOUND"

        # Verify original mission unchanged
        await db_session.refresh(job_a)
        assert job_a.mission == "Original mission in tenant A"
