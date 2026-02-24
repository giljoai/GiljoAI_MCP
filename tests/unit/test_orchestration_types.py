"""
Unit tests for orchestration data structures.

Tests data structures used in the orchestration workflow:
- Mission
- RequirementAnalysis
- AgentConfig
"""

from src.giljo_mcp.orchestration_types import (
    AgentConfig,
    Mission,
    RequirementAnalysis,
)


class TestMission:
    """Test cases for Mission dataclass."""

    def test_mission_creation_minimal(self):
        """Test creating a mission with required fields only."""
        mission = Mission(
            agent_role="architect",
            content="Design the system architecture",
            token_count=150,
            context_chunk_ids=["chunk_1", "chunk_2"],
            priority="required",
        )

        assert mission.agent_role == "architect"
        assert mission.content == "Design the system architecture"
        assert mission.token_count == 150
        assert mission.context_chunk_ids == ["chunk_1", "chunk_2"]
        assert mission.priority == "required"
        assert mission.scope_boundary is None
        assert mission.success_criteria is None
        assert mission.dependencies is None

    def test_mission_creation_full(self):
        """Test creating a mission with all fields."""
        mission = Mission(
            agent_role="implementor",
            content="Implement the authentication system",
            token_count=800,
            context_chunk_ids=["chunk_3", "chunk_4", "chunk_5"],
            priority="high",
            scope_boundary="Focus on OAuth2 implementation only",
            success_criteria="All tests pass, code coverage > 90%",
            dependencies=["architect_mission_1", "analyst_mission_2"],
        )

        assert mission.agent_role == "implementor"
        assert mission.scope_boundary == "Focus on OAuth2 implementation only"
        assert mission.success_criteria == "All tests pass, code coverage > 90%"
        assert mission.dependencies == ["architect_mission_1", "analyst_mission_2"]

    def test_mission_to_dict(self):
        """Test Mission to_dict method."""
        mission = Mission(
            agent_role="analyst",
            content="Analyze requirements",
            token_count=500,
            context_chunk_ids=["chunk_1"],
            priority="medium",
            scope_boundary="User authentication only",
            success_criteria="Requirements documented",
            dependencies=["initial_analysis"],
        )

        result = mission.to_dict()

        assert isinstance(result, dict)
        assert result["agent_role"] == "analyst"
        assert result["content"] == "Analyze requirements"
        assert result["token_count"] == 500
        assert result["context_chunk_ids"] == ["chunk_1"]
        assert result["priority"] == "medium"
        assert result["scope_boundary"] == "User authentication only"
        assert result["success_criteria"] == "Requirements documented"
        assert result["dependencies"] == ["initial_analysis"]

    def test_mission_to_dict_with_none_values(self):
        """Test to_dict with None optional values."""
        mission = Mission(
            agent_role="tester",
            content="Create test suite",
            token_count=300,
            context_chunk_ids=[],
            priority="low",
        )

        result = mission.to_dict()

        assert result["scope_boundary"] is None
        assert result["success_criteria"] is None
        assert result["dependencies"] is None

    def test_mission_empty_context_chunks(self):
        """Test mission with empty context chunks list."""
        mission = Mission(
            agent_role="architect",
            content="High-level design",
            token_count=200,
            context_chunk_ids=[],
            priority="required",
        )

        assert mission.context_chunk_ids == []


class TestRequirementAnalysis:
    """Test cases for RequirementAnalysis dataclass."""

    def test_requirement_analysis_creation(self):
        """Test creating RequirementAnalysis with required fields."""
        analysis = RequirementAnalysis(
            work_types={"architecture": "system_design", "implementation": "backend"},
            complexity="moderate",
            tech_stack=["Python", "FastAPI", "PostgreSQL"],
            keywords=["authentication", "API", "database"],
            estimated_agents_needed=3,
        )

        assert analysis.work_types == {"architecture": "system_design", "implementation": "backend"}
        assert analysis.complexity == "medium"
        assert analysis.tech_stack == ["Python", "FastAPI", "PostgreSQL"]
        assert analysis.keywords == ["authentication", "API", "database"]
        assert analysis.estimated_agents_needed == 3
        assert analysis.feature_categories is None

    def test_requirement_analysis_with_feature_categories(self):
        """Test RequirementAnalysis with optional feature_categories."""
        analysis = RequirementAnalysis(
            work_types={"testing": "unit_tests"},
            complexity="simple",
            tech_stack=["pytest"],
            keywords=["testing", "coverage"],
            estimated_agents_needed=1,
            feature_categories=["authentication", "authorization"],
        )

        assert analysis.feature_categories == ["authentication", "authorization"]

    def test_get_agent_priority_exists(self):
        """Test get_agent_priority when agent type exists in work_types."""
        analysis = RequirementAnalysis(
            work_types={"architect": "high", "implementor": "medium", "tester": "low"},
            complexity="complex",
            tech_stack=["Python"],
            keywords=["test"],
            estimated_agents_needed=3,
        )

        assert analysis.get_agent_priority("architect") == "high"
        assert analysis.get_agent_priority("implementor") == "medium"
        assert analysis.get_agent_priority("tester") == "low"

    def test_get_agent_priority_not_exists(self):
        """Test get_agent_priority when agent type doesn't exist."""
        analysis = RequirementAnalysis(
            work_types={"architect": "high"},
            complexity="simple",
            tech_stack=["Python"],
            keywords=["test"],
            estimated_agents_needed=1,
        )

        assert analysis.get_agent_priority("unknown_agent") == "low"

    def test_get_agent_priority_empty_work_types(self):
        """Test get_agent_priority with empty work_types."""
        analysis = RequirementAnalysis(
            work_types={},
            complexity="simple",
            tech_stack=[],
            keywords=[],
            estimated_agents_needed=0,
        )

        assert analysis.get_agent_priority("any_agent") == "low"

    def test_complexity_validation_simple(self):
        """Test complexity field with 'simple' value."""
        analysis = RequirementAnalysis(
            work_types={},
            complexity="simple",
            tech_stack=[],
            keywords=[],
            estimated_agents_needed=1,
        )

        assert analysis.complexity == "simple"

    def test_complexity_validation_moderate(self):
        """Test complexity field with 'moderate' value."""
        analysis = RequirementAnalysis(
            work_types={},
            complexity="moderate",
            tech_stack=[],
            keywords=[],
            estimated_agents_needed=2,
        )

        assert analysis.complexity == "medium"

    def test_complexity_validation_complex(self):
        """Test complexity field with 'complex' value."""
        analysis = RequirementAnalysis(
            work_types={},
            complexity="complex",
            tech_stack=[],
            keywords=[],
            estimated_agents_needed=5,
        )

        assert analysis.complexity == "complex"


class TestAgentConfig:
    """Test cases for AgentConfig dataclass."""

    def test_agent_config_creation_minimal(self):
        """Test creating AgentConfig with required fields."""
        config = AgentConfig(
            role="architect",
            template_id="arch_001",
            system_instructions="You are an expert architect...",
            priority="high",
            mission_scope="Design authentication system",
        )

        assert config.role == "architect"
        assert config.template_id == "arch_001"
        assert config.system_instructions == "You are an expert architect..."
        assert config.priority == "high"
        assert config.mission_scope == "Design authentication system"
        assert config.mission is None
        assert config.context_chunks is None

    def test_agent_config_creation_with_mission(self):
        """Test creating AgentConfig with Mission object."""
        mission = Mission(
            agent_role="implementor",
            content="Implement OAuth2",
            token_count=600,
            context_chunk_ids=["chunk_1"],
            priority="required",
        )

        config = AgentConfig(
            role="implementor",
            template_id="impl_001",
            system_instructions="You are an expert implementor...",
            priority="required",
            mission_scope="OAuth2 implementation",
            mission=mission,
            context_chunks=["context data 1", "context data 2"],
        )

        assert config.mission == mission
        assert config.context_chunks == ["context data 1", "context data 2"]

    def test_agent_config_to_job_params_minimal(self):
        """Test to_job_params with minimal config."""
        config = AgentConfig(
            role="analyst",
            template_id="anal_001",
            system_instructions="You are an analyst...",
            priority="medium",
            mission_scope="Analyze requirements",
        )

        params = config.to_job_params()

        assert isinstance(params, dict)
        assert params["agent_role"] == "analyst"
        assert params["template_id"] == "anal_001"
        assert params["system_instructions"] == "You are an analyst..."
        assert params["priority"] == "medium"
        assert params["mission_scope"] == "Analyze requirements"
        assert params["mission"] is None
        assert params["context_chunks"] is None

    def test_agent_config_to_job_params_with_mission(self):
        """Test to_job_params with mission and context."""
        mission = Mission(
            agent_role="tester",
            content="Create test suite",
            token_count=400,
            context_chunk_ids=["chunk_2"],
            priority="high",
        )

        config = AgentConfig(
            role="tester",
            template_id="test_001",
            system_instructions="You are a tester...",
            priority="high",
            mission_scope="Testing scope",
            mission=mission,
            context_chunks=["context A", "context B"],
        )

        params = config.to_job_params()

        assert params["mission"] == mission.to_dict()
        assert params["context_chunks"] == ["context A", "context B"]

    def test_agent_config_to_job_params_none_mission(self):
        """Test to_job_params when mission is None."""
        config = AgentConfig(
            role="reviewer",
            template_id="rev_001",
            system_instructions="You are a reviewer...",
            priority="low",
            mission_scope="Review code",
        )

        params = config.to_job_params()

        assert params["mission"] is None
