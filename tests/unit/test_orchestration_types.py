"""
Unit tests for orchestration data structures.

Tests all data structures used in the orchestration workflow:
- Mission
- RequirementAnalysis
- AgentConfig
- WorkflowStage
- StageResult
- WorkflowResult
"""

from src.giljo_mcp.orchestration_types import (
    AgentConfig,
    Mission,
    RequirementAnalysis,
    StageResult,
    WorkflowResult,
    WorkflowStage,
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


class TestWorkflowStage:
    """Test cases for WorkflowStage dataclass."""

    def test_workflow_stage_creation_minimal(self):
        """Test creating WorkflowStage with required fields."""
        agent_config = AgentConfig(
            role="architect",
            template_id="arch_001",
            system_instructions="Template",
            priority="high",
            mission_scope="Design",
        )

        stage = WorkflowStage(
            name="architecture",
            agents=[agent_config],
        )

        assert stage.name == "architecture"
        assert stage.agents == [agent_config]
        assert stage.depends_on is None
        assert stage.critical is True
        assert stage.timeout_seconds == 3600
        assert stage.max_retries == 1
        assert stage.retry_count == 0

    def test_workflow_stage_creation_full(self):
        """Test creating WorkflowStage with all fields."""
        agent1 = AgentConfig(
            role="implementor",
            template_id="impl_001",
            system_instructions="Template 1",
            priority="high",
            mission_scope="Scope 1",
        )
        agent2 = AgentConfig(
            role="tester",
            template_id="test_001",
            system_instructions="Template 2",
            priority="medium",
            mission_scope="Scope 2",
        )

        stage = WorkflowStage(
            name="implementation",
            agents=[agent1, agent2],
            depends_on=["architecture"],
            critical=False,
            timeout_seconds=7200,
            max_retries=3,
            retry_count=1,
        )

        assert stage.name == "implementation"
        assert stage.agents == [agent1, agent2]
        assert stage.depends_on == ["architecture"]
        assert stage.critical is False
        assert stage.timeout_seconds == 7200
        assert stage.max_retries == 3
        assert stage.retry_count == 1

    def test_is_ready_no_dependencies(self):
        """Test is_ready when stage has no dependencies."""
        stage = WorkflowStage(
            name="initial_stage",
            agents=[],
        )

        assert stage.is_ready([]) is True
        assert stage.is_ready(["some_stage"]) is True

    def test_is_ready_dependencies_met(self):
        """Test is_ready when all dependencies are met."""
        stage = WorkflowStage(
            name="testing",
            agents=[],
            depends_on=["architecture", "implementation"],
        )

        completed = ["architecture", "implementation", "other_stage"]
        assert stage.is_ready(completed) is True

    def test_is_ready_dependencies_not_met(self):
        """Test is_ready when dependencies are not met."""
        stage = WorkflowStage(
            name="testing",
            agents=[],
            depends_on=["architecture", "implementation"],
        )

        completed = ["architecture"]
        assert stage.is_ready(completed) is False

    def test_is_ready_dependencies_partially_met(self):
        """Test is_ready when some dependencies are met."""
        stage = WorkflowStage(
            name="deployment",
            agents=[],
            depends_on=["testing", "documentation"],
        )

        completed = ["testing"]
        assert stage.is_ready(completed) is False

    def test_is_ready_empty_dependencies_list(self):
        """Test is_ready with empty depends_on list."""
        stage = WorkflowStage(
            name="stage",
            agents=[],
            depends_on=[],
        )

        assert stage.is_ready([]) is True

    def test_workflow_stage_defaults(self):
        """Test WorkflowStage default values are correct."""
        stage = WorkflowStage(
            name="test_stage",
            agents=[],
        )

        assert stage.critical is True
        assert stage.timeout_seconds == 3600
        assert stage.max_retries == 1
        assert stage.retry_count == 0


class TestStageResult:
    """Test cases for StageResult dataclass."""

    def test_stage_result_creation(self):
        """Test creating StageResult."""
        result = StageResult(
            stage_name="architecture",
            job_ids=["job_001", "job_002"],
            results={"architect_1": "success", "architect_2": "success"},
            duration=125.5,
            status="completed",
        )

        assert result.stage_name == "architecture"
        assert result.job_ids == ["job_001", "job_002"]
        assert result.results == {"architect_1": "success", "architect_2": "success"}
        assert result.duration == 125.5
        assert result.status == "completed"

    def test_stage_result_empty_results(self):
        """Test StageResult with empty results."""
        result = StageResult(
            stage_name="empty_stage",
            job_ids=[],
            results={},
            duration=0.0,
            status="skipped",
        )

        assert result.job_ids == []
        assert result.results == {}
        assert result.duration == 0.0

    def test_stage_result_failed_status(self):
        """Test StageResult with failed status."""
        result = StageResult(
            stage_name="implementation",
            job_ids=["job_003"],
            results={"implementor_1": "failed"},
            duration=45.2,
            status="failed",
        )

        assert result.status == "failed"


class TestWorkflowResult:
    """Test cases for WorkflowResult dataclass."""

    def test_workflow_result_creation(self):
        """Test creating WorkflowResult."""
        stage1 = StageResult(
            stage_name="architecture",
            job_ids=["job_001"],
            results={"result": "success"},
            duration=100.0,
            status="completed",
        )
        stage2 = StageResult(
            stage_name="implementation",
            job_ids=["job_002"],
            results={"result": "success"},
            duration=200.0,
            status="completed",
        )

        workflow = WorkflowResult(
            completed=[stage1, stage2],
            failed=[],
            status="completed",
            duration_seconds=300.0,
            token_reduction_achieved=0.72,
        )

        assert workflow.completed == [stage1, stage2]
        assert workflow.failed == []
        assert workflow.status == "completed"
        assert workflow.duration_seconds == 300.0
        assert workflow.token_reduction_achieved == 0.72

    def test_workflow_result_with_failures(self):
        """Test WorkflowResult with failed stages."""
        stage1 = StageResult(
            stage_name="architecture",
            job_ids=["job_001"],
            results={"result": "success"},
            duration=100.0,
            status="completed",
        )

        workflow = WorkflowResult(
            completed=[stage1],
            failed=["implementation", "testing"],
            status="partial",
            duration_seconds=150.0,
        )

        assert workflow.completed == [stage1]
        assert workflow.failed == ["implementation", "testing"]
        assert workflow.status == "partial"

    def test_success_rate_all_completed(self):
        """Test success_rate property with all stages completed."""
        stage1 = StageResult(
            stage_name="s1",
            job_ids=["j1"],
            results={},
            duration=10.0,
            status="completed",
        )
        stage2 = StageResult(
            stage_name="s2",
            job_ids=["j2"],
            results={},
            duration=20.0,
            status="completed",
        )
        stage3 = StageResult(
            stage_name="s3",
            job_ids=["j3"],
            results={},
            duration=30.0,
            status="completed",
        )

        workflow = WorkflowResult(
            completed=[stage1, stage2, stage3],
            failed=[],
            status="completed",
            duration_seconds=60.0,
        )

        assert workflow.success_rate == 1.0

    def test_success_rate_partial_completion(self):
        """Test success_rate property with partial completion."""
        stage1 = StageResult(
            stage_name="s1",
            job_ids=["j1"],
            results={},
            duration=10.0,
            status="completed",
        )
        stage2 = StageResult(
            stage_name="s2",
            job_ids=["j2"],
            results={},
            duration=20.0,
            status="completed",
        )

        workflow = WorkflowResult(
            completed=[stage1, stage2],
            failed=["s3", "s4"],
            status="partial",
            duration_seconds=30.0,
        )

        assert workflow.success_rate == 0.5

    def test_success_rate_all_failed(self):
        """Test success_rate property with all stages failed."""
        workflow = WorkflowResult(
            completed=[],
            failed=["s1", "s2", "s3"],
            status="failed",
            duration_seconds=10.0,
        )

        assert workflow.success_rate == 0.0

    def test_success_rate_no_stages(self):
        """Test success_rate property with no stages."""
        workflow = WorkflowResult(
            completed=[],
            failed=[],
            status="completed",
            duration_seconds=0.0,
        )

        assert workflow.success_rate == 0.0

    def test_workflow_result_none_token_reduction(self):
        """Test WorkflowResult with None token_reduction_achieved."""
        workflow = WorkflowResult(
            completed=[],
            failed=[],
            status="completed",
            duration_seconds=0.0,
            token_reduction_achieved=None,
        )

        assert workflow.token_reduction_achieved is None

    def test_workflow_result_status_completed(self):
        """Test WorkflowResult with completed status."""
        workflow = WorkflowResult(
            completed=[],
            failed=[],
            status="completed",
            duration_seconds=100.0,
        )

        assert workflow.status == "completed"

    def test_workflow_result_status_partial(self):
        """Test WorkflowResult with partial status."""
        workflow = WorkflowResult(
            completed=[],
            failed=["s1"],
            status="partial",
            duration_seconds=50.0,
        )

        assert workflow.status == "partial"

    def test_workflow_result_status_failed(self):
        """Test WorkflowResult with failed status."""
        workflow = WorkflowResult(
            completed=[],
            failed=["s1", "s2"],
            status="failed",
            duration_seconds=25.0,
        )

        assert workflow.status == "failed"
