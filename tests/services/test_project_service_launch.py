"""
TDD Tests for ProjectService.launch_project() migration to AgentJob + AgentExecution.

Handover 0358a: Migrate launch_project() from creating MCPAgentJob directly
to using the dual-model architecture (AgentJob + AgentExecution).

Phase 1: RED - These tests should FAIL initially because launch_project()
still creates MCPAgentJob instead of AgentJob + AgentExecution.
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import func, select

from src.giljo_mcp.models import Project
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.services.project_service import ProjectService


@pytest_asyncio.fixture
async def project_service_for_test(db_session, db_manager, tenant_manager, test_project):
    """Create ProjectService with tenant_key matching test_project."""
    tenant_manager.set_current_tenant(test_project.tenant_key)
    return ProjectService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        test_session=db_session,
    )


class TestLaunchProjectCreatesAgentJobAndExecution:
    """Test that launch_project() creates AgentJob + AgentExecution pair (not MCPAgentJob)."""

    @pytest.mark.asyncio
    async def test_launch_creates_agent_job(
        self, db_session, project_service_for_test, test_project
    ):
        """Verify AgentJob record exists with correct fields after launch."""
        # Act
        result = await project_service_for_test.launch_project(
            project_id=test_project.id,
            user_id=None,
            launch_config=None,
        )

        # Assert - launch succeeded
        assert result["success"] is True, f"Launch failed: {result.get('error')}"
        orchestrator_job_id = result["data"]["orchestrator_job_id"]

        # Assert - AgentJob was created with correct fields
        stmt = select(AgentJob).where(
            AgentJob.job_id == orchestrator_job_id,
            AgentJob.tenant_key == test_project.tenant_key,
        )
        agent_job_result = await db_session.execute(stmt)
        agent_job = agent_job_result.scalar_one_or_none()

        assert agent_job is not None, "AgentJob should be created by launch_project()"
        assert agent_job.job_id == orchestrator_job_id
        assert agent_job.tenant_key == test_project.tenant_key
        assert agent_job.project_id == test_project.id
        assert agent_job.job_type == "orchestrator"
        assert agent_job.status == "active"
        assert agent_job.mission is not None

    @pytest.mark.asyncio
    async def test_launch_creates_agent_execution(
        self, db_session, project_service_for_test, test_project
    ):
        """Verify AgentExecution record exists with instance_number=1 after launch."""
        # Act
        result = await project_service_for_test.launch_project(
            project_id=test_project.id,
            user_id=None,
            launch_config=None,
        )

        # Assert - launch succeeded
        assert result["success"] is True, f"Launch failed: {result.get('error')}"
        orchestrator_job_id = result["data"]["orchestrator_job_id"]

        # Assert - AgentExecution was created with correct fields
        stmt = select(AgentExecution).where(
            AgentExecution.job_id == orchestrator_job_id,
            AgentExecution.tenant_key == test_project.tenant_key,
        )
        execution_result = await db_session.execute(stmt)
        execution = execution_result.scalar_one_or_none()

        assert execution is not None, "AgentExecution should be created by launch_project()"
        assert execution.job_id == orchestrator_job_id
        assert execution.tenant_key == test_project.tenant_key
        assert execution.agent_type == "orchestrator"
        assert execution.instance_number == 1
        assert execution.status == "waiting"
        assert execution.context_used == 0
        assert execution.context_budget == (test_project.context_budget or 150000)

    @pytest.mark.asyncio
    async def test_launch_returns_orchestrator_job_id(
        self, db_session, project_service_for_test, test_project
    ):
        """Response contains orchestrator_job_id which is the AgentJob.job_id."""
        # Act
        result = await project_service_for_test.launch_project(
            project_id=test_project.id,
            user_id=None,
            launch_config=None,
        )

        # Assert
        assert result["success"] is True, f"Launch failed: {result.get('error')}"
        assert "orchestrator_job_id" in result["data"]
        assert result["data"]["orchestrator_job_id"] is not None

        # Verify it's a valid UUID
        job_id = result["data"]["orchestrator_job_id"]
        uuid.UUID(job_id)  # Will raise if invalid

    @pytest.mark.asyncio
    async def test_launch_stores_depth_config_in_job_metadata(
        self, db_session, db_manager, tenant_manager, test_project
    ):
        """job_metadata should contain depth_config and user_id."""
        # Arrange - Create user with depth_config
        from src.giljo_mcp.models import User

        user = User(
            id=str(uuid.uuid4()),
            tenant_key=test_project.tenant_key,
            username=f"test_user_{uuid.uuid4().hex[:8]}",
            email=f"test_{uuid.uuid4().hex[:8]}@example.com",
            password_hash="hashed_password",
            depth_config={
                "vision_documents": "full",
                "memory_last_n_projects": 5,
            },
            field_priority_config={
                "priorities": {
                    "vision_documents": 1,
                    "tech_stack": 2,
                }
            },
        )
        db_session.add(user)
        await db_session.commit()

        # Create service with same tenant
        tenant_manager.set_current_tenant(test_project.tenant_key)
        service = ProjectService(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            test_session=db_session,
        )

        # Act
        result = await service.launch_project(
            project_id=test_project.id,
            user_id=user.id,
            launch_config=None,
        )

        # Assert
        assert result["success"] is True, f"Launch failed: {result.get('error')}"
        orchestrator_job_id = result["data"]["orchestrator_job_id"]

        # Fetch AgentJob and check job_metadata
        stmt = select(AgentJob).where(AgentJob.job_id == orchestrator_job_id)
        agent_job_result = await db_session.execute(stmt)
        agent_job = agent_job_result.scalar_one_or_none()

        assert agent_job is not None
        assert agent_job.job_metadata is not None
        assert "depth_config" in agent_job.job_metadata
        assert "user_id" in agent_job.job_metadata
        assert agent_job.job_metadata["user_id"] == user.id
        assert agent_job.job_metadata["depth_config"]["vision_documents"] == "full"

    @pytest.mark.asyncio
    async def test_launch_increments_instance_number_on_subsequent_launches(
        self, db_session, project_service_for_test, test_project
    ):
        """Second launch for same project should have instance_number=2."""
        # Act - First launch
        result1 = await project_service_for_test.launch_project(
            project_id=test_project.id,
            user_id=None,
            launch_config=None,
        )
        assert result1["success"] is True, f"Launch 1 failed: {result1.get('error')}"
        job_id_1 = result1["data"]["orchestrator_job_id"]

        # Get first execution
        stmt1 = select(AgentExecution).where(AgentExecution.job_id == job_id_1)
        exec_result1 = await db_session.execute(stmt1)
        execution1 = exec_result1.scalar_one_or_none()
        assert execution1.instance_number == 1

        # Act - Second launch (creates new job and execution)
        result2 = await project_service_for_test.launch_project(
            project_id=test_project.id,
            user_id=None,
            launch_config=None,
        )
        assert result2["success"] is True, f"Launch 2 failed: {result2.get('error')}"
        job_id_2 = result2["data"]["orchestrator_job_id"]

        # Get second execution
        stmt2 = select(AgentExecution).where(AgentExecution.job_id == job_id_2)
        exec_result2 = await db_session.execute(stmt2)
        execution2 = exec_result2.scalar_one_or_none()

        # Assert - instance_number should be 2
        assert execution2.instance_number == 2


class TestLaunchProjectDoesNotCreateMCPAgentJob:
    """Verify that launch_project() no longer creates MCPAgentJob records."""

    @pytest.mark.asyncio
    async def test_no_mcp_agent_job_created(
        self, db_session, project_service_for_test, test_project
    ):
        """MCPAgentJob count should remain unchanged after launch_project()."""
        # Arrange - Count existing MCPAgentJob records for this project
        count_before_stmt = select(func.count()).select_from(MCPAgentJob).where(
            AgentExecution.project_id == test_project.id,
            AgentExecution.tenant_key == test_project.tenant_key,
        )
        count_before_result = await db_session.execute(count_before_stmt)
        count_before = count_before_result.scalar()

        # Act
        result = await project_service_for_test.launch_project(
            project_id=test_project.id,
            user_id=None,
            launch_config=None,
        )

        # Assert - launch succeeded
        assert result["success"] is True, f"Launch failed: {result.get('error')}"

        # Assert - MCPAgentJob count unchanged
        count_after_result = await db_session.execute(count_before_stmt)
        count_after = count_after_result.scalar()

        assert count_after == count_before, (
            f"MCPAgentJob count changed from {count_before} to {count_after}. "
            "launch_project() should NOT create MCPAgentJob records."
        )


class TestLaunchProjectAgentExecutionFields:
    """Test that AgentExecution has all expected fields populated correctly."""

    @pytest.mark.asyncio
    async def test_execution_has_agent_name(
        self, db_session, project_service_for_test, test_project
    ):
        """AgentExecution should have agent_name like 'Orchestrator #1'."""
        # Act
        result = await project_service_for_test.launch_project(
            project_id=test_project.id,
            user_id=None,
            launch_config=None,
        )

        # Assert
        assert result["success"] is True, f"Launch failed: {result.get('error')}"
        orchestrator_job_id = result["data"]["orchestrator_job_id"]

        stmt = select(AgentExecution).where(AgentExecution.job_id == orchestrator_job_id)
        exec_result = await db_session.execute(stmt)
        execution = exec_result.scalar_one_or_none()

        assert execution is not None
        assert execution.agent_name is not None
        assert "Orchestrator" in execution.agent_name
        assert "#1" in execution.agent_name

    @pytest.mark.asyncio
    async def test_execution_has_health_status_unknown(
        self, db_session, project_service_for_test, test_project
    ):
        """AgentExecution should start with health_status='unknown'."""
        # Act
        result = await project_service_for_test.launch_project(
            project_id=test_project.id,
            user_id=None,
            launch_config=None,
        )

        # Assert
        assert result["success"] is True, f"Launch failed: {result.get('error')}"
        orchestrator_job_id = result["data"]["orchestrator_job_id"]

        stmt = select(AgentExecution).where(AgentExecution.job_id == orchestrator_job_id)
        exec_result = await db_session.execute(stmt)
        execution = exec_result.scalar_one_or_none()

        assert execution.health_status == "unknown"

    @pytest.mark.asyncio
    async def test_execution_has_progress_zero(
        self, db_session, project_service_for_test, test_project
    ):
        """AgentExecution should start with progress=0."""
        # Act
        result = await project_service_for_test.launch_project(
            project_id=test_project.id,
            user_id=None,
            launch_config=None,
        )

        # Assert
        assert result["success"] is True, f"Launch failed: {result.get('error')}"
        orchestrator_job_id = result["data"]["orchestrator_job_id"]

        stmt = select(AgentExecution).where(AgentExecution.job_id == orchestrator_job_id)
        exec_result = await db_session.execute(stmt)
        execution = exec_result.scalar_one_or_none()

        assert execution.progress == 0
