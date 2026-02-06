"""
Test suite for implementation phase gate (Handover 0709).

Tests cover:
- get_agent_mission blocked when implementation_launched_at is None
- get_agent_mission succeeds when implementation_launched_at is set
- acknowledge_job blocked when implementation_launched_at is None
- acknowledge_job succeeds when implementation_launched_at is set
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.giljo_mcp.services.orchestration_service import OrchestrationService
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.projects import Project


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
    service = OrchestrationService(
        db_manager=db_manager,
        tenant_manager=mock_tenant_manager
    )
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
        status="waiting",        mission_acknowledged_at=None,
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

        # Mock project lookup via session.get
        session.get = AsyncMock(return_value=project)

        # Mock session.execute for job and execution lookups
        session.execute = AsyncMock(side_effect=[job_result, exec_result])

        # Call get_agent_mission
        response = await orchestration_service.get_agent_mission(
            job_id=job.job_id,
            tenant_key="tenant-test"
        )

        # Verify blocked response
        assert response.get("blocked") is True, "Mission should be blocked when implementation not launched"
        assert response.get("mission") is None, "Mission should be None when blocked"
        assert response.get("full_protocol") is None, "Protocol should be None when blocked"
        assert "BLOCKED" in response.get("error", ""), "Error message should indicate blocked status"
        assert "user_instruction" in response, "Response should include user instruction"
        assert "Implement" in response.get("user_instruction", ""), "User instruction should mention Implement button"

    @pytest.mark.asyncio
    async def test_get_agent_mission_succeeds_when_launched(
        self, orchestration_service, mock_db_manager, mock_agent_job_and_execution, mock_project_launched
    ):
        """Test that get_agent_mission succeeds when implementation_launched_at is set."""
        db_manager, session = mock_db_manager
        job, execution, project_id = mock_agent_job_and_execution
        project = mock_project_launched
        project.id = project_id  # Link project to job

        # Setup database mocks
        job_result = MagicMock()
        job_result.scalar_one_or_none = MagicMock(return_value=job)

        exec_result = MagicMock()
        exec_result.scalar_one_or_none = MagicMock(return_value=execution)

        all_exec_result = MagicMock()
        all_exec_result.all = MagicMock(return_value=[(execution, job)])

        # Mock project lookup via session.get
        session.get = AsyncMock(return_value=project)

        # Mock session.execute for job, execution, and project executions
        session.execute = AsyncMock(side_effect=[job_result, exec_result, all_exec_result])

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
            response = await orchestration_service.get_agent_mission(
                job_id=job.job_id,
                tenant_key="tenant-test"
            )

        # Verify successful response (not blocked)
        assert response.get("blocked") is not True, "Mission should not be blocked when implementation launched"
        assert response.get("mission") is not None, "Mission should be present when not blocked"
        assert response.get("full_protocol") is not None, "Protocol should be present when not blocked"
        assert response.get("success") is True, "Response should indicate success"
        assert response.get("job_id") == job.job_id, "Response should include job_id"


class TestAcknowledgeJobImplementationGate:
    """Test suite for implementation phase gate in acknowledge_job."""

    @pytest.mark.asyncio
    async def test_acknowledge_job_blocked_when_not_launched(
        self, orchestration_service, mock_db_manager, mock_agent_job_and_execution, mock_project_not_launched
    ):
        """Test that acknowledge_job is blocked when implementation_launched_at is None."""
        db_manager, session = mock_db_manager
        job, execution, project_id = mock_agent_job_and_execution
        project = mock_project_not_launched
        project.id = project_id  # Link project to job

        # Setup database mocks
        exec_result = MagicMock()
        exec_result.scalar_one_or_none = MagicMock(return_value=execution)

        job_result = MagicMock()
        job_result.scalar_one_or_none = MagicMock(return_value=job)

        # Mock project lookup via session.get
        session.get = AsyncMock(return_value=project)

        # Mock session.execute for execution and job lookups
        session.execute = AsyncMock(side_effect=[exec_result, job_result])

        # Call acknowledge_job
        response = await orchestration_service.acknowledge_job(
            job_id=job.job_id,
            tenant_key="tenant-test"
        )

        # Verify blocked response
        assert response.get("success") is False, "Acknowledge should fail when implementation not launched"
        assert "BLOCKED" in response.get("error", ""), "Error should indicate blocked status"
        assert "action_required" in response, "Response should include action_required field"
        assert "Implement" in response.get("action_required", ""), "Action required should mention Implement button"

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

        # Mock project lookup via session.get
        session.get = AsyncMock(return_value=project)

        # Mock session.execute for execution and job lookups
        session.execute = AsyncMock(side_effect=[exec_result, job_result])

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
            response = await orchestration_service.acknowledge_job(
                job_id=job.job_id,
                tenant_key="tenant-test"
            )

        # Verify successful response (not blocked)
        assert response.get("success") is not False, "Acknowledge should succeed when implementation launched"
        assert "job" in response, "Response should include job details"
        assert response["job"].get("status") == "working", "Job status should be working after acknowledgment"
