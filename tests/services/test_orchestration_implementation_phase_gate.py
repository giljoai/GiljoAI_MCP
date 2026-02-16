"""
Test suite for implementation phase gate (Handover 0709).

Tests cover:
- get_agent_mission blocked when implementation_launched_at is None
- get_agent_mission succeeds when implementation_launched_at is set
- acknowledge_job blocked when implementation_launched_at is None (raises ProjectStateError)
- acknowledge_job succeeds when implementation_launched_at is set

Updated for exception-based error handling (Handover 0730).
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.giljo_mcp.exceptions import DatabaseError, ProjectStateError
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.services.orchestration_service import OrchestrationService


@pytest.fixture
def mock_db_manager():
    """Mock database manager with async session support."""
    db_manager = MagicMock()
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.get = AsyncMock()
    db_manager.get_session_async = MagicMock(return_value=session)
    return db_manager, session


@pytest.fixture
def mock_tenant_manager():
    """Mock tenant manager."""
    tenant_manager = MagicMock()
    tenant_manager.get_current_tenant = MagicMock(return_value="tenant-test")
    return tenant_manager


@pytest.fixture
def orchestration_service(mock_db_manager, mock_tenant_manager):
    """Create OrchestrationService with mocked dependencies."""
    db_manager, _ = mock_db_manager
    service = OrchestrationService(db_manager=db_manager, tenant_manager=mock_tenant_manager)
    return service


@pytest.fixture
def mock_project_not_launched():
    """Create mock project with implementation_launched_at = None."""
    project = Project(
        id=str(uuid4()),
        tenant_key="tenant-test",
        name="Test Project",
        description="Test description",
        mission="Test mission",
        status="active",
        implementation_launched_at=None,  # BLOCKED - not launched yet
    )
    return project


@pytest.fixture
def mock_project_launched():
    """Create mock project with implementation_launched_at set."""
    project = Project(
        id=str(uuid4()),
        tenant_key="tenant-test",
        name="Test Project",
        description="Test description",
        mission="Test mission",
        status="active",
        implementation_launched_at=datetime.now(timezone.utc),  # LAUNCHED
    )
    return project


@pytest.fixture
def mock_agent_job_and_execution():
    """Create mock agent job and execution."""
    job_id = str(uuid4())
    project_id = str(uuid4())

    # Create AgentJob (work order)
    job = AgentJob(
        job_id=job_id,
        tenant_key="tenant-test",
        project_id=project_id,
        mission="Test mission for implementation",
        job_type="implementer",
        status="active",
        created_at=datetime.now(timezone.utc),
    )

    # Create AgentExecution (executor instance)
    execution = AgentExecution(
        job_id=job_id,
        agent_id=str(uuid4()),
        tenant_key="tenant-test",
        agent_display_name="implementer",
        agent_name="implementer-1",
        status="waiting",
        mission_acknowledged_at=None,
        started_at=None,
    )

    return job, execution, project_id


class TestGetAgentMissionImplementationGate:
    """Test suite for implementation phase gate in get_agent_mission."""

    @pytest.mark.asyncio
    async def test_get_agent_mission_blocked_when_not_launched(
        self, orchestration_service, mock_db_manager, mock_agent_job_and_execution, mock_project_not_launched
    ):
        """Test that get_agent_mission is blocked when implementation_launched_at is None."""
        db_manager, session = mock_db_manager
        job, execution, project_id = mock_agent_job_and_execution
        project = mock_project_not_launched
        project.id = project_id  # Link project to job

        # Setup database mocks
        job_result = MagicMock()
        job_result.scalar_one_or_none = MagicMock(return_value=job)

        exec_result = MagicMock()
        exec_result.scalar_one_or_none = MagicMock(return_value=execution)

        # Mock project lookup via session.execute (tenant-scoped query)
        project_result = MagicMock()
        project_result.scalar_one_or_none = MagicMock(return_value=project)

        # Mock session.execute for job, execution, and project lookups
        session.execute = AsyncMock(side_effect=[job_result, exec_result, project_result])

        # Call get_agent_mission
        response = await orchestration_service.get_agent_mission(job_id=job.job_id, tenant_key="tenant-test")

        # Handover 0731c: Returns MissionResponse typed model
        # Verify blocked response
        assert response.blocked is True, "Mission should be blocked when implementation not launched"
        assert response.mission is None, "Mission should be None when blocked"
        assert response.full_protocol is None, "Protocol should be None when blocked"
        assert "BLOCKED" in (response.error or ""), "Error message should indicate blocked status"
        assert response.user_instruction is not None, "Response should include user instruction"
        assert "Implement" in (response.user_instruction or ""), "User instruction should mention Implement button"

    @pytest.mark.asyncio
    async def test_get_agent_mission_succeeds_when_launched(
        self, orchestration_service, mock_db_manager, mock_agent_job_and_execution, mock_project_launched
    ):
        """Test that get_agent_mission succeeds when implementation_launched_at is set.

        Updated for exception-based error handling (Handover 0730b).
        Success is indicated by presence of job_id in response, not a 'success' wrapper.
        """
        db_manager, session = mock_db_manager
        job, execution, project_id = mock_agent_job_and_execution
        project = mock_project_launched
        project.id = project_id  # Link project to job

        # Setup database mocks
        job_result = MagicMock()
        job_result.scalar_one_or_none = MagicMock(return_value=job)

        exec_result = MagicMock()
        exec_result.scalar_one_or_none = MagicMock(return_value=execution)

        # Mock project lookup via session.execute (tenant-scoped query)
        project_result = MagicMock()
        project_result.scalar_one_or_none = MagicMock(return_value=project)

        all_exec_result = MagicMock()
        all_exec_result.all = MagicMock(return_value=[(execution, job)])

        # Mock session.execute for job, execution, project, and project executions
        session.execute = AsyncMock(side_effect=[job_result, exec_result, project_result, all_exec_result])

        # Stub httpx to avoid real WebSocket bridge calls
        with patch("httpx.AsyncClient") as MockHttpxClient:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            MockHttpxClient.return_value = mock_client

            # Call get_agent_mission
            response = await orchestration_service.get_agent_mission(job_id=job.job_id, tenant_key="tenant-test")

        # Handover 0731c: Returns MissionResponse typed model
        # Verify successful response (not blocked)
        assert response.blocked is not True, "Mission should not be blocked when implementation launched"
        assert response.mission is not None, "Mission should be present when not blocked"
        assert response.full_protocol is not None, "Protocol should be present when not blocked"
        assert response.job_id == job.job_id, "Response should include job_id (indicates success)"


class TestAcknowledgeJobImplementationGate:
    """Test suite for implementation phase gate in acknowledge_job."""

    @pytest.mark.asyncio
    async def test_acknowledge_job_blocked_when_not_launched(
        self, orchestration_service, mock_db_manager, mock_agent_job_and_execution, mock_project_not_launched
    ):
        """Test that acknowledge_job raises DatabaseError (wrapping ProjectStateError) when implementation_launched_at is None.

        Updated for exception-based error handling (Handover 0730).
        Note: ProjectStateError is wrapped in DatabaseError by the generic exception handler.
        """
        db_manager, session = mock_db_manager
        job, execution, project_id = mock_agent_job_and_execution
        project = mock_project_not_launched
        project.id = project_id  # Link project to job

        # Setup database mocks
        exec_result = MagicMock()
        exec_result.scalar_one_or_none = MagicMock(return_value=execution)

        job_result = MagicMock()
        job_result.scalar_one_or_none = MagicMock(return_value=job)

        # Mock project lookup via session.execute (tenant-scoped query)
        project_result = MagicMock()
        project_result.scalar_one_or_none = MagicMock(return_value=project)

        # Mock session.execute for execution, job, and project lookups
        session.execute = AsyncMock(side_effect=[exec_result, job_result, project_result])

        # Call acknowledge_job - should raise DatabaseError wrapping ProjectStateError
        with pytest.raises(DatabaseError) as exc_info:
            await orchestration_service.acknowledge_job(job_id=job.job_id, tenant_key="tenant-test")

        # Verify exception details - the wrapped ProjectStateError message is in the DatabaseError message
        assert "Implementation not launched" in str(exc_info.value), "Error should indicate implementation not launched"
        assert "Implement" in str(exc_info.value), "Error should mention Implement button"

        # Verify the original cause is ProjectStateError
        assert isinstance(exc_info.value.__cause__, ProjectStateError), "Cause should be ProjectStateError"

    @pytest.mark.asyncio
    async def test_acknowledge_job_succeeds_when_launched(
        self, orchestration_service, mock_db_manager, mock_agent_job_and_execution, mock_project_launched
    ):
        """Test that acknowledge_job succeeds when implementation_launched_at is set."""
        db_manager, session = mock_db_manager
        job, execution, project_id = mock_agent_job_and_execution
        project = mock_project_launched
        project.id = project_id  # Link project to job

        # Setup database mocks
        exec_result = MagicMock()
        exec_result.scalar_one_or_none = MagicMock(return_value=execution)

        job_result = MagicMock()
        job_result.scalar_one_or_none = MagicMock(return_value=job)

        # Mock project lookup via session.execute (tenant-scoped query)
        project_result = MagicMock()
        project_result.scalar_one_or_none = MagicMock(return_value=project)

        # Mock session.execute for execution, job, and project lookups
        session.execute = AsyncMock(side_effect=[exec_result, job_result, project_result])

        # Stub httpx to avoid real WebSocket bridge calls
        with patch("httpx.AsyncClient") as MockHttpxClient:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            MockHttpxClient.return_value = mock_client

            # Call acknowledge_job
            response = await orchestration_service.acknowledge_job(job_id=job.job_id, tenant_key="tenant-test")

        # Handover 0731c: Returns AcknowledgeJobResult typed model
        # Verify successful response (not blocked)
        assert response.job, "Response should include job details"
        assert response.job.get("status") == "working", "Job status should be working after acknowledgment"
