"""
Test suite for team-aware missions (Handover 0353, updated 0453).

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

This test file directly unit tests _generate_team_context_header() as a pure function.
No mocking of database queries needed - we just create mock AgentExecution objects
and test the function output.
"""

from unittest.mock import MagicMock
from uuid import uuid4

from src.giljo_mcp.services.orchestration_service import _generate_team_context_header


def create_mock_agent_execution(
    agent_display_name: str,
    agent_name: str | None = None,
    agent_id: str | None = None,
    job_id: str | None = None,
    status: str = "waiting",
    mission: str | None = None,
) -> MagicMock:
    """
    Create a mock AgentExecution object for testing.

    Args:
        agent_display_name: Display name like "analyzer", "implementer"
        agent_name: Template name (defaults to agent_display_name)
        agent_id: Unique agent ID (defaults to new UUID)
        job_id: Job ID (defaults to new UUID)
        status: Job status (defaults to "waiting")
        mission: Mission text (optional)

    Returns:
        MagicMock configured with required attributes
    """
    mock_execution = MagicMock()
    mock_execution.agent_display_name = agent_display_name
    mock_execution.agent_name = agent_name or agent_display_name
    mock_execution.agent_id = agent_id or str(uuid4())
    mock_execution.job_id = job_id or str(uuid4())
    mock_execution.status = status
    mock_execution.mission = mission
    return mock_execution


class TestTeamContextHeader:
    """Test suite for _generate_team_context_header() function."""

    def test_your_identity_section_contains_role_and_ids(self):
        """
        Test that YOUR IDENTITY section contains agent role, agent_id, and job_id.

        The YOUR IDENTITY section should clearly state the agent's role
        and provide both agent_id and job_id for MCP tool calls.
        """
        agent_id = str(uuid4())
        job_id = str(uuid4())
        current_agent = create_mock_agent_execution(
            agent_display_name="analyzer",
            agent_name="analyzer",
            agent_id=agent_id,
            job_id=job_id,
        )

        header = _generate_team_context_header(
            current_job=current_agent,
            all_project_jobs=[current_agent],
            mission_lookup=None,
        )

        # Verify YOUR IDENTITY section exists
        assert "## YOUR IDENTITY" in header, "Header must include YOUR IDENTITY section"

        # Verify role is capitalized and prominent
        assert "ANALYZER" in header, "YOUR IDENTITY must include capitalized role name"

        # Verify agent_id is present
        assert agent_id in header, "YOUR IDENTITY must include agent_id"

        # Verify job_id is present
        assert job_id in header, "YOUR IDENTITY must include job_id"

        # Verify agent_display_name is mentioned
        assert "analyzer" in header.lower(), "YOUR IDENTITY must mention agent_display_name"

    def test_your_team_section_lists_all_agents(self):
        """
        Test that YOUR TEAM section lists all agents on the project.

        The YOUR TEAM section should contain:
        - Count of agents on the project
        - Table with all agents and their roles
        - Deliverables preview for each agent
        """
        analyzer = create_mock_agent_execution(
            agent_display_name="analyzer", mission="Analyze folder structure and design architecture"
        )
        implementer = create_mock_agent_execution(
            agent_display_name="implementer", mission="Implement backend API endpoints based on architecture"
        )

        all_agents = [analyzer, implementer]

        header = _generate_team_context_header(
            current_job=analyzer,
            all_project_jobs=all_agents,
            mission_lookup=None,
        )

        # Verify YOUR TEAM section exists
        assert "## YOUR TEAM" in header, "Header must include YOUR TEAM section"

        # Verify agent count
        assert "2 agent(s)" in header, "YOUR TEAM must show correct agent count"

        # Verify table exists
        assert "| Agent |" in header, "YOUR TEAM must include table header"
        assert "| agent_id |" in header, "YOUR TEAM table must have agent_id column"
        assert "| Role |" in header, "YOUR TEAM table must have Role column"
        assert "| Deliverables |" in header, "YOUR TEAM table must have Deliverables column"

        # Verify both agents are listed
        assert "analyzer" in header.lower(), "YOUR TEAM must list analyzer"
        assert "implementer" in header.lower(), "YOUR TEAM must list implementer"

        # Verify deliverable previews appear
        assert "Analyze folder structure" in header or "architecture" in header.lower(), (
            "YOUR TEAM should show deliverable preview"
        )

    def test_your_dependencies_section_analyzer_has_downstream(self):
        """
        Test that YOUR DEPENDENCIES section correctly identifies downstream dependencies.

        Analyzer should have downstream dependencies on implementer and documenter
        when they are present in the team.
        """
        analyzer = create_mock_agent_execution(agent_display_name="analyzer")
        implementer = create_mock_agent_execution(agent_display_name="implementer")
        documenter = create_mock_agent_execution(agent_display_name="documenter")

        all_agents = [analyzer, implementer, documenter]

        header = _generate_team_context_header(
            current_job=analyzer,
            all_project_jobs=all_agents,
            mission_lookup=None,
        )

        # Verify YOUR DEPENDENCIES section exists
        assert "## YOUR DEPENDENCIES" in header, "Header must include YOUR DEPENDENCIES section"

        # Analyzer has no upstream dependencies
        assert "You depend on: None" in header, "Analyzer should have no upstream dependencies"

        # Analyzer has downstream dependencies
        assert "Others depend on you:" in header, "YOUR DEPENDENCIES must list downstream dependencies"
        assert "implementer" in header.lower(), "Analyzer should list implementer as downstream"
        assert "documenter" in header.lower(), "Analyzer should list documenter as downstream"

    def test_your_dependencies_section_documenter_has_upstream(self):
        """
        Test that YOUR DEPENDENCIES section correctly identifies upstream dependencies.

        Documenter should have upstream dependencies on analyzer and implementer
        when they are present in the team.
        """
        analyzer = create_mock_agent_execution(agent_display_name="analyzer")
        implementer = create_mock_agent_execution(agent_display_name="implementer")
        documenter = create_mock_agent_execution(agent_display_name="documenter")

        all_agents = [analyzer, implementer, documenter]

        header = _generate_team_context_header(
            current_job=documenter,
            all_project_jobs=all_agents,
            mission_lookup=None,
        )

        # Verify YOUR DEPENDENCIES section exists
        assert "## YOUR DEPENDENCIES" in header, "Header must include YOUR DEPENDENCIES section"

        # Documenter has upstream dependencies
        assert "You depend on:" in header, "YOUR DEPENDENCIES must list upstream dependencies"
        assert "analyzer" in header.lower(), "Documenter should list analyzer as upstream"
        assert "implementer" in header.lower(), "Documenter should list implementer as upstream"

        # Documenter has no downstream dependencies
        assert "Others depend on you: None" in header, "Documenter should have no downstream dependencies"

    def test_your_dependencies_section_implementer_has_both(self):
        """
        Test that YOUR DEPENDENCIES section handles both upstream and downstream.

        Implementer should have:
        - Upstream: analyzer
        - Downstream: tester, documenter
        """
        analyzer = create_mock_agent_execution(agent_display_name="analyzer")
        implementer = create_mock_agent_execution(agent_display_name="implementer")
        tester = create_mock_agent_execution(agent_display_name="tester")
        documenter = create_mock_agent_execution(agent_display_name="documenter")

        all_agents = [analyzer, implementer, tester, documenter]

        header = _generate_team_context_header(
            current_job=implementer,
            all_project_jobs=all_agents,
            mission_lookup=None,
        )

        # Verify YOUR DEPENDENCIES section exists
        assert "## YOUR DEPENDENCIES" in header, "Header must include YOUR DEPENDENCIES section"

        # Implementer has upstream dependency on analyzer
        assert "You depend on:" in header and "analyzer" in header.lower(), (
            "Implementer should list analyzer as upstream"
        )

        # Implementer has downstream dependencies on tester and documenter
        assert "Others depend on you:" in header, "Implementer should have downstream dependencies"
        assert "tester" in header.lower(), "Implementer should list tester as downstream"
        assert "documenter" in header.lower(), "Implementer should list documenter as downstream"

    def test_coordination_section_mentions_messaging_tools(self):
        """
        Test that COORDINATION section provides messaging guidance.

        The COORDINATION section should:
        - Reference send_message and receive_messages tools
        - Provide guidance on when to message teammates
        - Reference full_protocol for detailed instructions
        """
        current_agent = create_mock_agent_execution(agent_display_name="analyzer")

        header = _generate_team_context_header(
            current_job=current_agent,
            all_project_jobs=[current_agent],
            mission_lookup=None,
        )

        # Verify COORDINATION section exists
        assert "## COORDINATION" in header, "Header must include COORDINATION section"

        # Verify messaging tools are mentioned
        assert "send_message" in header, "COORDINATION must reference send_message tool"
        assert "receive_messages" in header, "COORDINATION must reference receive_messages tool"

        # Verify guidance is provided
        assert "notify teammates" in header.lower() or "status message" in header.lower(), (
            "COORDINATION must provide messaging guidance"
        )

        # Verify reference to full_protocol
        assert "full_protocol" in header, "COORDINATION must reference full_protocol for detailed instructions"

    def test_single_agent_project_still_gets_all_sections(self):
        """
        Test that single-agent project still gets all team context sections.

        Even with only one agent, the header should include all sections
        with appropriate messaging (e.g., "1 agent(s)", "None" dependencies).
        """
        solo_agent = create_mock_agent_execution(agent_display_name="implementer")

        header = _generate_team_context_header(
            current_job=solo_agent,
            all_project_jobs=[solo_agent],
            mission_lookup=None,
        )

        # All sections should exist
        assert "## YOUR IDENTITY" in header, "Single-agent must have YOUR IDENTITY"
        assert "## YOUR TEAM" in header, "Single-agent must have YOUR TEAM"
        assert "## YOUR DEPENDENCIES" in header, "Single-agent must have YOUR DEPENDENCIES"
        assert "## COORDINATION" in header, "Single-agent must have COORDINATION"

        # Team section should show 1 agent
        assert "1 agent(s)" in header, "YOUR TEAM should show '1 agent(s)'"

        # Dependencies should be None
        assert "None" in header, "Single-agent should have None dependencies"

    def test_mission_lookup_dict_used_when_provided(self):
        """
        Test that mission_lookup dict is used instead of mission attribute.

        When mission_lookup is provided, it should be used to get mission text
        for the deliverables preview instead of accessing the mission attribute
        (which could cause SQLAlchemy lazy load errors).
        """
        job_id_1 = str(uuid4())
        job_id_2 = str(uuid4())

        agent_1 = create_mock_agent_execution(
            agent_display_name="analyzer",
            job_id=job_id_1,
            mission="Should not appear",  # This should be ignored
        )
        agent_2 = create_mock_agent_execution(
            agent_display_name="implementer",
            job_id=job_id_2,
            mission="Should not appear",  # This should be ignored
        )

        mission_lookup = {
            job_id_1: "Analyze architecture using mission_lookup dict",
            job_id_2: "Implement features using mission_lookup dict",
        }

        all_agents = [agent_1, agent_2]

        header = _generate_team_context_header(
            current_job=agent_1,
            all_project_jobs=all_agents,
            mission_lookup=mission_lookup,
        )

        # Verify mission_lookup text appears in deliverables
        assert "mission_lookup dict" in header, "Deliverables should use mission_lookup text when provided"

        # Verify original mission attribute text does NOT appear
        assert "Should not appear" not in header, (
            "Deliverables should NOT use mission attribute when mission_lookup provided"
        )

    def test_multi_agent_team_roster_completeness(self):
        """
        Test that YOUR TEAM section includes all agents in a large team.

        Verify that a 5-agent team has all agents listed with their IDs.
        """
        agents = [
            create_mock_agent_execution(agent_display_name="analyzer"),
            create_mock_agent_execution(agent_display_name="implementer"),
            create_mock_agent_execution(agent_display_name="tester"),
            create_mock_agent_execution(agent_display_name="reviewer"),
            create_mock_agent_execution(agent_display_name="documenter"),
        ]

        header = _generate_team_context_header(
            current_job=agents[0],
            all_project_jobs=agents,
            mission_lookup=None,
        )

        # Verify team count
        assert "5 agent(s)" in header, "YOUR TEAM must show '5 agent(s)'"

        # Verify all agents are listed
        assert "analyzer" in header.lower()
        assert "implementer" in header.lower()
        assert "tester" in header.lower()
        assert "reviewer" in header.lower()
        assert "documenter" in header.lower()

        # Verify all agent_ids appear
        for agent in agents:
            assert agent.agent_id in header, f"YOUR TEAM must include agent_id for {agent.agent_display_name}"

    def test_dependency_inference_tester_depends_on_implementer(self):
        """
        Test that tester has upstream dependency on implementer.

        When both implementer and tester are present, tester should
        list implementer as an upstream dependency.
        """
        implementer = create_mock_agent_execution(agent_display_name="implementer")
        tester = create_mock_agent_execution(agent_display_name="tester")

        all_agents = [implementer, tester]

        header = _generate_team_context_header(
            current_job=tester,
            all_project_jobs=all_agents,
            mission_lookup=None,
        )

        # Tester depends on implementer
        assert "You depend on:" in header and "implementer" in header.lower(), (
            "Tester should list implementer as upstream dependency"
        )

    def test_unknown_role_has_no_dependencies(self):
        """
        Test that unknown/custom roles have no inferred dependencies.

        Roles not in the dependency_rules dict should have no
        upstream or downstream dependencies inferred.
        """
        custom_agent = create_mock_agent_execution(agent_display_name="custom-role")
        implementer = create_mock_agent_execution(agent_display_name="implementer")

        all_agents = [custom_agent, implementer]

        header = _generate_team_context_header(
            current_job=custom_agent,
            all_project_jobs=all_agents,
            mission_lookup=None,
        )

        # Custom role should have no dependencies
        assert "You depend on: None" in header, "Unknown roles should have no upstream dependencies"
        assert "Others depend on you: None" in header, "Unknown roles should have no downstream dependencies"
