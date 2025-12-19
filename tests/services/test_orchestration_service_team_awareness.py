"""
Test suite for team-aware missions (Handover 0353).

Tests cover:
- Mission text includes team context headers when multiple agents exist
- YOUR IDENTITY section with role + job_id
- YOUR TEAM section with roster of all agents on the project
- YOUR DEPENDENCIES section listing upstream/downstream relationships
- COORDINATION section with messaging guidance

TDD Approach:
- RED: Write failing tests first (this file)
- GREEN: Implement minimal code to pass
- REFACTOR: Clean up while keeping tests green
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.giljo_mcp.services.orchestration_service import OrchestrationService
from src.giljo_mcp.models.agents import MCPAgentJob


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
    db_manager.get_session_async = MagicMock(return_value=session)
    return db_manager, session


@pytest.fixture
def mock_tenant_manager():
    """Mock tenant manager."""
    tenant_manager = MagicMock()
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
def multi_agent_project_jobs():
    """
    Create a list of agent jobs representing a multi-agent project.

    This simulates a staged project with:
    - analyzer: Responsible for folder structure design
    - documenter: Responsible for documentation

    Analyzer should list documenter as a downstream dependency.
    Documenter should list analyzer as an upstream dependency.
    """
    project_id = str(uuid4())
    tenant_key = "tenant-test"

    analyzer_job = MCPAgentJob(
        job_id=str(uuid4()),
        tenant_key=tenant_key,
        project_id=project_id,
        agent_type="analyzer",
        agent_name="analyzer",
        mission="Analyze and design the folder structure for the project.",
        status="waiting",
        mission_acknowledged_at=None,
        started_at=None,
    )

    documenter_job = MCPAgentJob(
        job_id=str(uuid4()),
        tenant_key=tenant_key,
        project_id=project_id,
        agent_type="documenter",
        agent_name="documenter",
        mission="Write documentation including README.md and docs/index.md.",
        status="waiting",
        mission_acknowledged_at=None,
        started_at=None,
    )

    return {
        "project_id": project_id,
        "tenant_key": tenant_key,
        "analyzer": analyzer_job,
        "documenter": documenter_job,
        "all_jobs": [analyzer_job, documenter_job],
    }


class TestTeamAwareMissions:
    """Test suite for team-aware mission content (Handover 0353)."""

    @pytest.mark.asyncio
    async def test_get_agent_mission_includes_your_identity_header(
        self, orchestration_service, mock_db_manager, multi_agent_project_jobs
    ):
        """
        Test that get_agent_mission returns mission with YOUR IDENTITY header.

        The YOUR IDENTITY section should contain:
        - Role name (e.g., "ANALYZER")
        - Job ID for MCP tool calls
        """
        db_manager, session = mock_db_manager
        analyzer_job = multi_agent_project_jobs["analyzer"]
        all_jobs = multi_agent_project_jobs["all_jobs"]

        # Mock database queries
        # First query returns the specific agent job
        result_job = MagicMock()
        result_job.scalar_one_or_none = MagicMock(return_value=analyzer_job)

        # Second query returns all jobs for the project (for team context)
        result_all_jobs = MagicMock()
        result_all_jobs.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=all_jobs)))

        session.execute = AsyncMock(side_effect=[result_job, result_all_jobs])

        with patch("httpx.AsyncClient") as MockHttpxClient:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            MockHttpxClient.return_value = mock_client

            response = await orchestration_service.get_agent_mission(
                agent_job_id=analyzer_job.job_id,
                tenant_key=multi_agent_project_jobs["tenant_key"]
            )

        assert response.get("success") is True
        mission = response.get("mission", "")

        # Verify YOUR IDENTITY section exists
        assert "## YOUR IDENTITY" in mission, "Mission must include YOUR IDENTITY header"
        assert "analyzer" in mission.lower(), "YOUR IDENTITY must mention role"
        assert analyzer_job.job_id in mission, "YOUR IDENTITY must include job_id"

    @pytest.mark.asyncio
    async def test_get_agent_mission_includes_your_team_header(
        self, orchestration_service, mock_db_manager, multi_agent_project_jobs
    ):
        """
        Test that get_agent_mission returns mission with YOUR TEAM header.

        The YOUR TEAM section should contain:
        - Count of agents on the project
        - Table/list of all agents with roles and deliverables
        """
        db_manager, session = mock_db_manager
        analyzer_job = multi_agent_project_jobs["analyzer"]
        all_jobs = multi_agent_project_jobs["all_jobs"]

        result_job = MagicMock()
        result_job.scalar_one_or_none = MagicMock(return_value=analyzer_job)

        result_all_jobs = MagicMock()
        result_all_jobs.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=all_jobs)))

        session.execute = AsyncMock(side_effect=[result_job, result_all_jobs])

        with patch("httpx.AsyncClient") as MockHttpxClient:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            MockHttpxClient.return_value = mock_client

            response = await orchestration_service.get_agent_mission(
                agent_job_id=analyzer_job.job_id,
                tenant_key=multi_agent_project_jobs["tenant_key"]
            )

        assert response.get("success") is True
        mission = response.get("mission", "")

        # Verify YOUR TEAM section exists
        assert "## YOUR TEAM" in mission, "Mission must include YOUR TEAM header"
        # Should mention both agents
        assert "analyzer" in mission.lower(), "YOUR TEAM must list analyzer"
        assert "documenter" in mission.lower(), "YOUR TEAM must list documenter"

    @pytest.mark.asyncio
    async def test_get_agent_mission_includes_your_dependencies_header(
        self, orchestration_service, mock_db_manager, multi_agent_project_jobs
    ):
        """
        Test that get_agent_mission returns mission with YOUR DEPENDENCIES header.

        The YOUR DEPENDENCIES section should describe:
        - Upstream dependencies (what this agent depends on)
        - Downstream dependencies (who depends on this agent)
        """
        db_manager, session = mock_db_manager
        documenter_job = multi_agent_project_jobs["documenter"]
        all_jobs = multi_agent_project_jobs["all_jobs"]

        result_job = MagicMock()
        result_job.scalar_one_or_none = MagicMock(return_value=documenter_job)

        result_all_jobs = MagicMock()
        result_all_jobs.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=all_jobs)))

        session.execute = AsyncMock(side_effect=[result_job, result_all_jobs])

        with patch("httpx.AsyncClient") as MockHttpxClient:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            MockHttpxClient.return_value = mock_client

            response = await orchestration_service.get_agent_mission(
                agent_job_id=documenter_job.job_id,
                tenant_key=multi_agent_project_jobs["tenant_key"]
            )

        assert response.get("success") is True
        mission = response.get("mission", "")

        # Verify YOUR DEPENDENCIES section exists
        assert "## YOUR DEPENDENCIES" in mission, "Mission must include YOUR DEPENDENCIES header"

    @pytest.mark.asyncio
    async def test_get_agent_mission_includes_coordination_header(
        self, orchestration_service, mock_db_manager, multi_agent_project_jobs
    ):
        """
        Test that get_agent_mission returns mission with COORDINATION header.

        The COORDINATION section should include:
        - Guidance on when/who to message
        - Reference to MCP messaging tools
        """
        db_manager, session = mock_db_manager
        analyzer_job = multi_agent_project_jobs["analyzer"]
        all_jobs = multi_agent_project_jobs["all_jobs"]

        result_job = MagicMock()
        result_job.scalar_one_or_none = MagicMock(return_value=analyzer_job)

        result_all_jobs = MagicMock()
        result_all_jobs.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=all_jobs)))

        session.execute = AsyncMock(side_effect=[result_job, result_all_jobs])

        with patch("httpx.AsyncClient") as MockHttpxClient:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            MockHttpxClient.return_value = mock_client

            response = await orchestration_service.get_agent_mission(
                agent_job_id=analyzer_job.job_id,
                tenant_key=multi_agent_project_jobs["tenant_key"]
            )

        assert response.get("success") is True
        mission = response.get("mission", "")

        # Verify COORDINATION section exists
        assert "## COORDINATION" in mission, "Mission must include COORDINATION header"
        # Should reference messaging tools
        assert "send_message" in mission.lower() or "receive_messages" in mission.lower(), \
            "COORDINATION must reference MCP messaging tools"

    @pytest.mark.asyncio
    async def test_get_agent_mission_team_header_lists_all_project_agents(
        self, orchestration_service, mock_db_manager, multi_agent_project_jobs
    ):
        """
        Test that YOUR TEAM lists all agents on the project with their roles.
        """
        db_manager, session = mock_db_manager
        analyzer_job = multi_agent_project_jobs["analyzer"]
        all_jobs = multi_agent_project_jobs["all_jobs"]

        result_job = MagicMock()
        result_job.scalar_one_or_none = MagicMock(return_value=analyzer_job)

        result_all_jobs = MagicMock()
        result_all_jobs.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=all_jobs)))

        session.execute = AsyncMock(side_effect=[result_job, result_all_jobs])

        with patch("httpx.AsyncClient") as MockHttpxClient:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            MockHttpxClient.return_value = mock_client

            response = await orchestration_service.get_agent_mission(
                agent_job_id=analyzer_job.job_id,
                tenant_key=multi_agent_project_jobs["tenant_key"]
            )

        assert response.get("success") is True
        mission = response.get("mission", "")

        # Count agents mentioned
        team_section_start = mission.find("## YOUR TEAM")
        assert team_section_start != -1, "YOUR TEAM section must exist"

        # Both agent types should appear in the mission
        assert "analyzer" in mission.lower()
        assert "documenter" in mission.lower()

    @pytest.mark.asyncio
    async def test_single_agent_project_still_gets_team_context(
        self, orchestration_service, mock_db_manager
    ):
        """
        Test that even a single-agent project gets team context headers.

        The headers should still exist, with the team section indicating
        this is the only agent on the project.
        """
        db_manager, session = mock_db_manager
        project_id = str(uuid4())
        tenant_key = "tenant-solo"

        solo_job = MCPAgentJob(
            job_id=str(uuid4()),
            tenant_key=tenant_key,
            project_id=project_id,
            agent_type="implementer",
            agent_name="implementer",
            mission="Implement the complete feature.",
            status="waiting",
            mission_acknowledged_at=None,
            started_at=None,
        )

        result_job = MagicMock()
        result_job.scalar_one_or_none = MagicMock(return_value=solo_job)

        result_all_jobs = MagicMock()
        result_all_jobs.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[solo_job])))

        session.execute = AsyncMock(side_effect=[result_job, result_all_jobs])

        with patch("httpx.AsyncClient") as MockHttpxClient:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            MockHttpxClient.return_value = mock_client

            response = await orchestration_service.get_agent_mission(
                agent_job_id=solo_job.job_id,
                tenant_key=tenant_key
            )

        assert response.get("success") is True
        mission = response.get("mission", "")

        # All headers should still exist
        assert "## YOUR IDENTITY" in mission
        assert "## YOUR TEAM" in mission
        # For single agent, team section might indicate "1 agent" or similar
        assert "1 agent" in mission.lower() or "only agent" in mission.lower() or "implementer" in mission.lower()


class TestTeamContextIdClarification:
    """Test ID usage clarification per Handover 0353."""

    @pytest.mark.asyncio
    async def test_mission_uses_job_id_for_mcp_tools(
        self, orchestration_service, mock_db_manager, multi_agent_project_jobs
    ):
        """
        Test that mission/protocol uses job_id (UUID) for MCP tool calls.

        Per 0353: Clarify that job_id / agent_job_id = UUID for MCP tools.
        """
        db_manager, session = mock_db_manager
        analyzer_job = multi_agent_project_jobs["analyzer"]
        all_jobs = multi_agent_project_jobs["all_jobs"]

        result_job = MagicMock()
        result_job.scalar_one_or_none = MagicMock(return_value=analyzer_job)

        result_all_jobs = MagicMock()
        result_all_jobs.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=all_jobs)))

        session.execute = AsyncMock(side_effect=[result_job, result_all_jobs])

        with patch("httpx.AsyncClient") as MockHttpxClient:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            MockHttpxClient.return_value = mock_client

            response = await orchestration_service.get_agent_mission(
                agent_job_id=analyzer_job.job_id,
                tenant_key=multi_agent_project_jobs["tenant_key"]
            )

        assert response.get("success") is True

        # Check that the actual job_id (UUID) appears in mission or protocol
        mission = response.get("mission", "")
        protocol = response.get("full_protocol", "")
        combined = mission + protocol

        # The job_id UUID should appear (for MCP tool calls)
        assert analyzer_job.job_id in combined, \
            "Mission/protocol must include job_id UUID for MCP tool calls"

    @pytest.mark.asyncio
    async def test_mission_uses_agent_name_for_display(
        self, orchestration_service, mock_db_manager, multi_agent_project_jobs
    ):
        """
        Test that mission uses agent_name for display/identity.

        Per 0353: agent_name = template role (implementer/tester/etc.)
        """
        db_manager, session = mock_db_manager
        analyzer_job = multi_agent_project_jobs["analyzer"]
        all_jobs = multi_agent_project_jobs["all_jobs"]

        result_job = MagicMock()
        result_job.scalar_one_or_none = MagicMock(return_value=analyzer_job)

        result_all_jobs = MagicMock()
        result_all_jobs.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=all_jobs)))

        session.execute = AsyncMock(side_effect=[result_job, result_all_jobs])

        with patch("httpx.AsyncClient") as MockHttpxClient:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            MockHttpxClient.return_value = mock_client

            response = await orchestration_service.get_agent_mission(
                agent_job_id=analyzer_job.job_id,
                tenant_key=multi_agent_project_jobs["tenant_key"]
            )

        assert response.get("success") is True
        mission = response.get("mission", "")

        # Identity section should show the role name prominently
        assert "analyzer" in mission.lower(), \
            "YOUR IDENTITY must include the agent_name/role for display"
