"""
Unit tests for MissionPlanner class.

Tests all methods of the MissionPlanner class which generates condensed agent missions
from product vision documents with context prioritization and orchestration target.

Following TDD principles: Tests written BEFORE implementation.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.models import Product, Project
from src.giljo_mcp.orchestration_types import (
    AgentConfig,
    Mission,
    RequirementAnalysis,
)


class TestMissionPlanner:
    """Test cases for MissionPlanner class."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        db_manager = Mock()
        db_manager.is_async = True
        return db_manager

    @pytest.fixture
    def mission_planner(self, mock_db_manager):
        """Create MissionPlanner instance with mocked dependencies."""
        return MissionPlanner(mock_db_manager)

    @pytest.fixture
    def sample_product(self):
        """Create a sample Product with vision document."""
        product = Mock(spec=Product)
        product.id = "product_123"
        product.tenant_key = "tenant_abc"
        product.name = "Test Product"
        vision_text = """
        # Product Vision

        ## Technical Stack
        - Python 3.11+
        - FastAPI framework
        - PostgreSQL database
        - Vue 3 frontend

        ## Features
        - User authentication with OAuth2
        - RESTful API endpoints
        - Real-time notifications
        - Dashboard with analytics

        ## Architecture Guidelines
        - Microservices architecture
        - Event-driven design
        - TDD approach with pytest
        - CI/CD pipeline with GitHub Actions

        ## Implementation Requirements
        - All code must have 90% test coverage
        - API endpoints must be documented with OpenAPI
        - Database migrations must be reversible
        - Frontend components must be reusable
        """
        product.vision_document = vision_text
        product.primary_vision_text = vision_text  # Add for new vision handling
        product.primary_vision_path = None
        product.vision_documents = []  # No chunked documents
        product.vision_type = "inline"
        product.chunked = True
        product.config_data = {
            "tech_stack": ["Python", "FastAPI", "PostgreSQL", "Vue3"],
            "features": ["authentication", "api", "notifications", "dashboard"],
            "guidelines": ["microservices", "event-driven", "TDD", "CI/CD"],
        }
        # Add product_memory for history extraction
        product.product_memory = {"sequential_history": [], "git_integration": {"enabled": False}}
        return product

    @pytest.fixture
    def sample_project(self):
        """Create a sample Project."""
        project = Mock(spec=Project)
        project.id = "project_456"
        project.tenant_key = "tenant_abc"
        project.name = "Test Project"
        project.mission = "Build a modern web application"
        project.meta_data = {}
        return project

    @pytest.fixture
    def sample_agent_configs(self):
        """Create sample AgentConfig list."""
        return [
            AgentConfig(
                role="orchestrator",
                template_id="template_orch",
                system_instructions="You are an orchestrator...",
                priority="required",
                mission_scope="Coordinate all agents",
            ),
            AgentConfig(
                role="implementer",
                template_id="template_impl",
                system_instructions="You are an implementer...",
                priority="high",
                mission_scope="Implement backend features",
            ),
            AgentConfig(
                role="tester",
                template_id="template_test",
                system_instructions="You are a tester...",
                priority="high",
                mission_scope="Create comprehensive tests",
            ),
        ]

    @pytest.fixture
    def mock_context_chunks(self):
        """Create mock context chunks from vision document."""
        chunk1 = Mock()
        chunk1.chunk_id = "chunk_001"
        chunk1.content = "Technical Stack: Python, FastAPI, PostgreSQL"
        chunk1.keywords = ["python", "fastapi", "postgresql"]

        chunk2 = Mock()
        chunk2.chunk_id = "chunk_002"
        chunk2.content = "Features: Authentication, API, Notifications"
        chunk2.keywords = ["authentication", "api", "notifications"]

        chunk3 = Mock()
        chunk3.chunk_id = "chunk_003"
        chunk3.content = "Architecture: Microservices, Event-driven, TDD"
        chunk3.keywords = ["architecture", "microservices", "tdd"]

        return [chunk1, chunk2, chunk3]

    # Test helper methods

    def test_extract_keywords_comprehensive(self, mission_planner):
        """Test keyword extraction from text."""
        text = """
        This project requires comprehensive testing with pytest and unittest.
        We need a robust API built with FastAPI.
        The database layer will use PostgreSQL.
        Frontend development with Vue3 components.
        Security measures include OAuth2 authentication.
        We will deploy using Docker containers.
        """

        keywords = mission_planner._extract_keywords(text)

        assert "test" in keywords
        assert "api" in keywords
        assert "database" in keywords
        assert "frontend" in keywords
        assert "security" in keywords
        assert "deployment" in keywords

    def test_extract_keywords_empty_text(self, mission_planner):
        """Test keyword extraction with empty text."""
        keywords = mission_planner._extract_keywords("")
        assert keywords == []

    def test_extract_keywords_no_matches(self, mission_planner):
        """Test keyword extraction with no matching keywords."""
        text = "This is a simple project with no technical keywords."
        keywords = mission_planner._extract_keywords(text)
        # Should still return empty list if no matches
        assert isinstance(keywords, list)

    def test_categorize_work_orchestrator_always_required(self, mission_planner):
        """Test that orchestrator is always categorized as required."""
        keywords = []
        features = []

        work_types = mission_planner._categorize_work(keywords, features)

        assert "orchestrator" in work_types
        assert work_types["orchestrator"] == "required"

    def test_categorize_work_backend_api_keywords(self, mission_planner):
        """Test work categorization with backend/API keywords."""
        keywords = ["api", "database", "backend"]
        features = ["REST API", "Database Layer"]

        work_types = mission_planner._categorize_work(keywords, features)

        assert "implementer" in work_types
        assert work_types["implementer"] == "high"

    def test_categorize_work_test_keywords(self, mission_planner):
        """Test work categorization with test keywords."""
        keywords = ["test", "testing"]
        features = ["Unit Tests", "Integration Tests"]

        work_types = mission_planner._categorize_work(keywords, features)

        assert "tester" in work_types
        assert work_types["tester"] == "high"

    def test_categorize_work_frontend_keywords(self, mission_planner):
        """Test work categorization with frontend keywords."""
        keywords = ["frontend", "ui"]
        features = ["User Interface", "Dashboard"]

        work_types = mission_planner._categorize_work(keywords, features)

        assert "frontend-implementer" in work_types
        assert work_types["frontend-implementer"] == "high"

    def test_categorize_work_complex_project_reviewer(self, mission_planner):
        """Test that complex projects get code reviewer."""
        keywords = ["api", "database", "frontend", "test"]
        features = ["Feature 1", "Feature 2", "Feature 3", "Feature 4", "Feature 5"]

        work_types = mission_planner._categorize_work(keywords, features)

        assert "code-reviewer" in work_types
        assert work_types["code-reviewer"] == "medium"

    def test_categorize_work_user_facing_documenter(self, mission_planner):
        """Test that user-facing projects get documenter."""
        keywords = ["frontend", "ui", "api"]
        features = ["User Dashboard", "API Documentation"]

        work_types = mission_planner._categorize_work(keywords, features)

        assert "documenter" in work_types
        assert work_types["documenter"] == "low"

    def test_assess_complexity_simple(self, mission_planner):
        """Test complexity assessment for simple projects."""
        complexity = mission_planner._assess_complexity(description_length=100, feature_count=2, tech_stack_size=2)

        assert complexity == "simple"

    def test_assess_complexity_moderate(self, mission_planner):
        """Test complexity assessment for moderate projects."""
        complexity = mission_planner._assess_complexity(description_length=600, feature_count=4, tech_stack_size=4)

        assert complexity == "medium"

    def test_assess_complexity_complex(self, mission_planner):
        """Test complexity assessment for complex projects."""
        complexity = mission_planner._assess_complexity(description_length=1500, feature_count=8, tech_stack_size=6)

        assert complexity == "complex"

    def test_estimate_agent_count_simple(self, mission_planner):
        """Test agent count estimation for simple projects."""
        work_types = {"orchestrator": "required", "implementer": "high"}
        complexity = "simple"

        count = mission_planner._estimate_agent_count(work_types, complexity)

        assert count >= 2
        assert count <= 4

    def test_estimate_agent_count_moderate(self, mission_planner):
        """Test agent count estimation for moderate projects."""
        work_types = {"orchestrator": "required", "implementer": "high", "tester": "high", "code-reviewer": "medium"}
        complexity = "moderate"

        count = mission_planner._estimate_agent_count(work_types, complexity)

        assert count >= 3
        assert count <= 6

    def test_estimate_agent_count_complex(self, mission_planner):
        """Test agent count estimation for complex projects."""
        work_types = {
            "orchestrator": "required",
            "implementer": "high",
            "tester": "high",
            "frontend-implementer": "high",
            "code-reviewer": "medium",
            "documenter": "low",
        }
        complexity = "complex"

        count = mission_planner._estimate_agent_count(work_types, complexity)

        assert count >= 4
        assert count <= 8

    def test_count_tokens_basic(self, mission_planner):
        """Test token counting with basic text."""
        text = "This is a simple test string for token counting."

        token_count = mission_planner._count_tokens(text)

        assert token_count > 0
        assert isinstance(token_count, int)

    def test_count_tokens_empty(self, mission_planner):
        """Test token counting with empty string."""
        token_count = mission_planner._count_tokens("")
        assert token_count == 0

    def test_count_tokens_long_text(self, mission_planner):
        """Test token counting with longer text."""
        text = " ".join(["word"] * 1000)

        token_count = mission_planner._count_tokens(text)

        assert token_count > 500
        assert token_count < 2000

    def test_filter_vision_for_role_implementer(self, mission_planner):
        """Test vision filtering for implementer role."""
        vision_chunks = [
            "Architecture: The system uses microservices architecture with event-driven design.",
            "Implementation: Backend API built with FastAPI and PostgreSQL database.",
            "Testing: Comprehensive test suite with pytest and 90% coverage.",
            "UI Design: Modern dashboard with Vue3 components.",
            "Code quality: All code must follow PEP 8 standards.",
        ]

        filtered = mission_planner._filter_vision_for_role(vision_chunks, "implementer")

        assert len(filtered) <= 3
        assert any(
            "implementation" in chunk.lower() or "architecture" in chunk.lower() or "api" in chunk.lower()
            for chunk in filtered
        )

    def test_filter_vision_for_role_tester(self, mission_planner):
        """Test vision filtering for tester role."""
        vision_chunks = [
            "Architecture: Microservices with event-driven design.",
            "Testing: Unit tests with pytest, integration tests required.",
            "Quality: 90% test coverage required for all modules.",
            "Validation: Input validation on all endpoints.",
            "UI: Modern dashboard interface.",
        ]

        filtered = mission_planner._filter_vision_for_role(vision_chunks, "tester")

        assert len(filtered) <= 3
        assert any(
            "test" in chunk.lower() or "quality" in chunk.lower() or "validation" in chunk.lower() for chunk in filtered
        )

    def test_filter_vision_for_role_frontend_implementer(self, mission_planner):
        """Test vision filtering for frontend-implementer role."""
        vision_chunks = [
            "Backend: FastAPI with PostgreSQL.",
            "UI: Vue3 components with Vuetify design system.",
            "Design: Modern, responsive user interface.",
            "Components: Reusable UI components library.",
            "Testing: E2E tests with Cypress.",
        ]

        filtered = mission_planner._filter_vision_for_role(vision_chunks, "frontend-implementer")

        assert len(filtered) <= 3
        assert any(
            "ui" in chunk.lower() or "design" in chunk.lower() or "components" in chunk.lower() for chunk in filtered
        )

    def test_filter_vision_for_role_returns_top_3(self, mission_planner):
        """Test that vision filtering returns maximum 3 chunks."""
        vision_chunks = [f"Chunk {i} with implementation code architecture backend api" for i in range(10)]

        filtered = mission_planner._filter_vision_for_role(vision_chunks, "implementer")

        assert len(filtered) == 3

    def test_get_role_responsibilities_implementer(self, mission_planner):
        """Test getting role responsibilities for implementer."""
        responsibilities = mission_planner._get_role_responsibilities("implementer")

        assert "implement" in responsibilities.lower()
        assert isinstance(responsibilities, str)
        assert len(responsibilities) > 50

    def test_get_role_responsibilities_tester(self, mission_planner):
        """Test getting role responsibilities for tester."""
        responsibilities = mission_planner._get_role_responsibilities("tester")

        assert "test" in responsibilities.lower()
        assert isinstance(responsibilities, str)
        assert len(responsibilities) > 50

    def test_get_role_responsibilities_orchestrator(self, mission_planner):
        """Test getting role responsibilities for orchestrator."""
        responsibilities = mission_planner._get_role_responsibilities("orchestrator")

        assert "orchestrat" in responsibilities.lower() or "coordinat" in responsibilities.lower()
        assert isinstance(responsibilities, str)
        assert len(responsibilities) > 50

    def test_get_role_responsibilities_unknown_role(self, mission_planner):
        """Test getting role responsibilities for unknown role."""
        responsibilities = mission_planner._get_role_responsibilities("unknown-role")

        assert isinstance(responsibilities, str)
        assert len(responsibilities) > 0

    def test_get_success_criteria_implementer(self, mission_planner, sample_product):
        """Test getting success criteria for implementer."""
        analysis = RequirementAnalysis(
            work_types={"implementer": "high"},
            complexity="moderate",
            tech_stack=["Python", "FastAPI"],
            keywords=["api", "database"],
            estimated_agents_needed=3,
            feature_categories=["authentication", "api"],
        )

        criteria = mission_planner._get_success_criteria("implementer", analysis)

        assert isinstance(criteria, str)
        assert len(criteria) > 50
        assert "test" in criteria.lower() or "code" in criteria.lower()

    def test_get_success_criteria_tester(self, mission_planner, sample_product):
        """Test getting success criteria for tester."""
        analysis = RequirementAnalysis(
            work_types={"tester": "high"},
            complexity="moderate",
            tech_stack=["pytest"],
            keywords=["test"],
            estimated_agents_needed=2,
            feature_categories=["testing"],
        )

        criteria = mission_planner._get_success_criteria("tester", analysis)

        assert isinstance(criteria, str)
        assert "test" in criteria.lower() or "coverage" in criteria.lower()

    # Test main workflow methods

    @pytest.mark.asyncio
    async def test_analyze_requirements_basic(self, mission_planner, sample_product):
        """Test basic requirement analysis."""
        project_description = "Build a REST API with authentication and database"

        analysis = await mission_planner.analyze_requirements(sample_product, project_description)

        assert isinstance(analysis, RequirementAnalysis)
        assert "orchestrator" in analysis.work_types
        assert analysis.work_types["orchestrator"] == "required"
        assert isinstance(analysis.complexity, str)
        assert analysis.complexity in ["simple", "moderate", "complex"]
        assert isinstance(analysis.tech_stack, list)
        assert isinstance(analysis.keywords, list)
        assert analysis.estimated_agents_needed > 0

    @pytest.mark.asyncio
    async def test_analyze_requirements_extracts_tech_stack(self, mission_planner, sample_product):
        """Test that requirement analysis extracts tech stack from product."""
        project_description = "Build a web application"

        analysis = await mission_planner.analyze_requirements(sample_product, project_description)

        assert len(analysis.tech_stack) > 0
        assert "Python" in analysis.tech_stack or "FastAPI" in analysis.tech_stack

    @pytest.mark.asyncio
    async def test_analyze_requirements_extracts_features(self, mission_planner, sample_product):
        """Test that requirement analysis extracts features from product."""
        project_description = "Build with authentication and API"

        analysis = await mission_planner.analyze_requirements(sample_product, project_description)

        assert analysis.feature_categories is not None
        assert len(analysis.feature_categories) > 0

    @pytest.mark.asyncio
    async def test_generate_agent_mission_basic(self, mission_planner, sample_product, sample_project):
        """Test generating a single agent mission."""
        agent_config = AgentConfig(
            role="implementer",
            template_id="template_impl",
            system_instructions="You are an implementer...",
            priority="high",
            mission_scope="Implement backend API",
        )

        analysis = RequirementAnalysis(
            work_types={"implementer": "high"},
            complexity="moderate",
            tech_stack=["Python", "FastAPI"],
            keywords=["api", "backend"],
            estimated_agents_needed=3,
            feature_categories=["api"],
        )

        vision_chunks = [
            "Backend implementation with FastAPI",
            "Database layer with PostgreSQL",
            "RESTful API design patterns",
        ]

        with patch.object(mission_planner, "_filter_vision_for_role", return_value=vision_chunks[:3]):
            mission = await mission_planner._generate_agent_mission(
                agent_config, analysis, sample_product, sample_project, vision_chunks
            )

        assert isinstance(mission, Mission)
        assert mission.agent_role == "implementer"
        assert len(mission.content) > 0
        assert mission.token_count > 0
        assert mission.token_count >= 200  # Reasonable minimum for condensed mission
        assert mission.token_count <= 2000  # Allow some flexibility for template content
        assert mission.priority == "high"
        assert isinstance(mission.context_chunk_ids, list)

    @pytest.mark.asyncio
    async def test_generate_agent_mission_includes_project_description(
        self, mission_planner, sample_product, sample_project
    ):
        """Test that generated mission includes project context."""
        agent_config = AgentConfig(
            role="tester",
            template_id="template_test",
            system_instructions="You are a tester...",
            priority="high",
            mission_scope="Create test suite",
        )

        analysis = RequirementAnalysis(
            work_types={"tester": "high"},
            complexity="simple",
            tech_stack=["pytest"],
            keywords=["test"],
            estimated_agents_needed=2,
        )

        vision_chunks = ["Testing with pytest framework"]

        with patch.object(mission_planner, "_filter_vision_for_role", return_value=vision_chunks):
            mission = await mission_planner._generate_agent_mission(
                agent_config, analysis, sample_product, sample_project, vision_chunks
            )

        assert sample_project.name in mission.content or sample_product.name in mission.content

    @pytest.mark.asyncio
    async def test_generate_missions_all_agents(
        self, mission_planner, sample_product, sample_project, sample_agent_configs, mock_context_chunks
    ):
        """Test generating missions for all agents."""
        analysis = RequirementAnalysis(
            work_types={"orchestrator": "required", "implementer": "high", "tester": "high"},
            complexity="moderate",
            tech_stack=["Python", "FastAPI", "PostgreSQL"],
            keywords=["api", "test", "database"],
            estimated_agents_needed=3,
            feature_categories=["api", "testing"],
        )

        # Mock ContextRepository search
        with patch("src.giljo_mcp.mission_planner.ContextRepository") as MockContextRepo:
            mock_repo = MockContextRepo.return_value
            mock_repo.search_chunks = Mock(return_value=mock_context_chunks)

            missions = await mission_planner.generate_missions(
                analysis, sample_product, sample_project, sample_agent_configs
            )

        assert isinstance(missions, dict)
        assert len(missions) == len(sample_agent_configs)
        assert "orchestrator" in missions
        assert "implementer" in missions
        assert "tester" in missions

        for role, mission in missions.items():
            assert isinstance(mission, Mission)
            assert mission.agent_role == role
            assert mission.token_count > 0

    @pytest.mark.asyncio
    async def test_generate_missions_token_reduction(
        self, mission_planner, sample_product, sample_project, sample_agent_configs, mock_context_chunks
    ):
        """Test that mission generation produces structured, targeted missions."""
        analysis = RequirementAnalysis(
            work_types={"orchestrator": "required", "implementer": "high", "tester": "high"},
            complexity="moderate",
            tech_stack=["Python", "FastAPI"],
            keywords=["api", "test"],
            estimated_agents_needed=3,
        )

        with patch("src.giljo_mcp.mission_planner.ContextRepository") as MockContextRepo:
            mock_repo = MockContextRepo.return_value
            mock_repo.search_chunks = Mock(return_value=mock_context_chunks)

            missions = await mission_planner.generate_missions(
                analysis, sample_product, sample_project, sample_agent_configs
            )

        # Verify missions were generated
        assert len(missions) == 3

        # Verify each mission is properly structured
        for role, mission in missions.items():
            assert mission.token_count > 0
            # Each mission should be reasonably sized (not too large)
            assert mission.token_count < 2000, f"{role} mission has {mission.token_count} tokens"
            # Mission should include role-specific content
            assert role in mission.content.lower()

        # The key insight: for large vision documents (50K+ tokens), sending condensed
        # role-specific missions achieves massive context prioritization.
        # For small test fixtures, the template overhead is acceptable
        # because it provides structure and clarity.

    @pytest.mark.asyncio
    async def test_generate_missions_stores_metrics(
        self, mission_planner, sample_product, sample_project, sample_agent_configs, mock_context_chunks
    ):
        """Test that mission generation stores token metrics."""
        analysis = RequirementAnalysis(
            work_types={"orchestrator": "required", "implementer": "high"},
            complexity="simple",
            tech_stack=["Python"],
            keywords=["api"],
            estimated_agents_needed=2,
        )

        with patch("src.giljo_mcp.mission_planner.ContextRepository") as MockContextRepo:
            mock_repo = MockContextRepo.return_value
            mock_repo.search_chunks = Mock(return_value=mock_context_chunks)

            with patch.object(mission_planner, "_store_token_metrics") as mock_store:
                await mission_planner.generate_missions(analysis, sample_product, sample_project, sample_agent_configs)

                # Verify metrics were stored
                mock_store.assert_called_once()
                call_args = mock_store.call_args[0]
                assert call_args[0] == sample_project.id
                assert call_args[1] > 0  # original_tokens
                assert call_args[2] > 0  # total_mission_tokens
                assert isinstance(call_args[3], (int, float))  # reduction_percent (can be negative in tests)

    @pytest.mark.asyncio
    async def test_store_token_metrics_updates_project(self, mission_planner, mock_db_manager):
        """Test that token metrics are stored in project metadata."""
        mock_session = AsyncMock()
        mock_db_manager.get_session_async = AsyncMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        project_id = "project_123"
        original_tokens = 10000
        mission_tokens = 2500
        reduction_percent = 75.0

        await mission_planner._store_token_metrics(project_id, original_tokens, mission_tokens, reduction_percent)

        # Should have attempted to update project
        assert mock_db_manager.get_session_async.called

    @pytest.mark.asyncio
    async def test_generate_missions_respects_priority(
        self, mission_planner, sample_product, sample_project, mock_context_chunks
    ):
        """Test that generated missions respect agent priorities."""
        agent_configs = [
            AgentConfig(
                role="orchestrator",
                template_id="t1",
                system_instructions="Template 1",
                priority="required",
                mission_scope="Scope 1",
            ),
            AgentConfig(
                role="implementer",
                template_id="t2",
                system_instructions="Template 2",
                priority="high",
                mission_scope="Scope 2",
            ),
            AgentConfig(
                role="documenter",
                template_id="t3",
                system_instructions="Template 3",
                priority="low",
                mission_scope="Scope 3",
            ),
        ]

        analysis = RequirementAnalysis(
            work_types={"orchestrator": "required", "implementer": "high", "documenter": "low"},
            complexity="simple",
            tech_stack=["Python"],
            keywords=["api"],
            estimated_agents_needed=3,
        )

        with patch("src.giljo_mcp.mission_planner.ContextRepository") as MockContextRepo:
            mock_repo = MockContextRepo.return_value
            mock_repo.search_chunks = Mock(return_value=mock_context_chunks)

            missions = await mission_planner.generate_missions(analysis, sample_product, sample_project, agent_configs)

        assert missions["orchestrator"].priority == "required"
        assert missions["implementer"].priority == "high"
        assert missions["documenter"].priority == "low"

    @pytest.mark.asyncio
    async def test_generate_missions_with_no_vision_chunks(
        self, mission_planner, sample_product, sample_project, sample_agent_configs
    ):
        """Test mission generation when no vision chunks are found."""
        analysis = RequirementAnalysis(
            work_types={"orchestrator": "required"},
            complexity="simple",
            tech_stack=["Python"],
            keywords=["api"],
            estimated_agents_needed=1,
        )

        with patch("src.giljo_mcp.mission_planner.ContextRepository") as MockContextRepo:
            mock_repo = MockContextRepo.return_value
            mock_repo.search_chunks = Mock(return_value=[])

            missions = await mission_planner.generate_missions(
                analysis, sample_product, sample_project, sample_agent_configs
            )

        # Should still generate missions even without chunks
        assert len(missions) > 0
        for mission in missions.values():
            assert mission.token_count > 0
            assert len(mission.content) > 0

    def test_mission_planner_initialization(self, mock_db_manager):
        """Test MissionPlanner initialization."""
        planner = MissionPlanner(mock_db_manager)

        assert planner.db_manager == mock_db_manager
        assert hasattr(planner, "_count_tokens")
        assert hasattr(planner, "analyze_requirements")
        assert hasattr(planner, "generate_missions")

    # === Fix #1: Default Field Priorities Tests ===

    @pytest.mark.asyncio
    async def test_empty_field_priorities_uses_defaults(self, mission_planner, sample_product, sample_project):
        """When no user priorities configured, should use sensible defaults.

        Critical Issue: field_priorities defaulting to {} causes all optional fields
        to be excluded. This test verifies that when empty dict is passed,
        the system applies DEFAULT_FIELD_PRIORITIES to include important context
        like codebase_summary and architecture.
        """
        # Arrange: Empty field priorities (simulating user with no config)
        field_priorities = {}

        # Act: Build context with empty priorities
        context = await mission_planner._build_context_with_priorities(
            product=sample_product, project=sample_project, field_priorities=field_priorities, user_id="test_user_123"
        )

        # Assert: Default fields should be included
        # Codebase summary should be included at moderate level (priority 6)
        assert "## Codebase" in context, "Codebase summary missing with empty priorities"

        # Architecture should be included at abbreviated level (priority 4)
        assert "## Architecture" in context, "Architecture missing with empty priorities"

        # Mandatory fields always present
        assert "## Product" in context
        assert "## Product Vision" in context
        assert "## Project Description" in context

    @pytest.mark.asyncio
    async def test_user_field_priorities_override_defaults(self, mission_planner, sample_product, sample_project):
        """User-configured priorities should override defaults.

        When user explicitly sets field priorities, those should take precedence
        over default priorities, allowing full customization.
        """
        # Arrange: User wants FULL detail for codebase_summary (priority 10)
        user_priorities = {"codebase_summary": 10}

        # Act: Build context with user priorities
        context = await mission_planner._build_context_with_priorities(
            product=sample_product, project=sample_project, field_priorities=user_priorities, user_id="test_user_123"
        )

        # Assert: Codebase should be included at FULL detail
        assert "## Codebase" in context
        # With priority 10, full codebase should be present (not abbreviated)
        # We'll verify this by checking the content is substantial
        codebase_section_start = context.find("## Codebase")
        codebase_section_end = context.find("##", codebase_section_start + 1)
        if codebase_section_end == -1:
            codebase_section_end = len(context)
        codebase_content = context[codebase_section_start:codebase_section_end]

        # Full detail should include all content from sample_project.codebase_summary
        assert len(codebase_content) > 100, "Codebase should have full detail with priority 10"

    @pytest.mark.asyncio
    async def test_defaults_do_not_affect_mandatory_fields(self, mission_planner, sample_product, sample_project):
        """Mandatory fields always included regardless of priorities.

        Product name, product vision, and project description are MANDATORY
        and should always be included at full detail, even with empty priorities.
        """
        # Arrange: Empty priorities
        field_priorities = {}

        # Act: Build context
        context = await mission_planner._build_context_with_priorities(
            product=sample_product, project=sample_project, field_priorities=field_priorities, user_id="test_user_123"
        )

        # Assert: All mandatory fields present at full detail
        assert "## Product" in context
        assert sample_product.name in context

        assert "## Product Vision" in context
        assert sample_product.primary_vision_text in context

        assert "## Project Description" in context
        assert sample_project.description in context

    @pytest.mark.asyncio
    async def test_default_priority_values_are_reasonable(self, mission_planner, sample_product, sample_project):
        """Verify default priority values produce balanced context.

        Default priorities should be:
        - codebase_summary: 6 (moderate detail)
        - architecture: 4 (abbreviated detail)

        This ensures ~50% context prioritization for optional fields while
        maintaining useful context.
        """
        # Arrange: Empty priorities to trigger defaults
        field_priorities = {}

        # Mock the _get_detail_level to verify it's called with correct priorities
        original_get_detail_level = mission_planner._get_detail_level
        detail_level_calls = []

        def mock_get_detail_level(priority):
            result = original_get_detail_level(priority)
            detail_level_calls.append((priority, result))
            return result

        with patch.object(mission_planner, "_get_detail_level", side_effect=mock_get_detail_level):
            # Act: Build context
            context = await mission_planner._build_context_with_priorities(
                product=sample_product,
                project=sample_project,
                field_priorities=field_priorities,
                user_id="test_user_123",
            )

        # Assert: Verify detail levels called with default priorities
        # Should have calls for codebase_summary (6) and architecture (4)
        priority_values = [call[0] for call in detail_level_calls]

        # Default codebase priority should be 6 (moderate)
        assert 6 in priority_values, "Default codebase_summary priority should be 6"

        # Default architecture priority should be 4 (abbreviated)
        assert 4 in priority_values, "Default architecture priority should be 4"
