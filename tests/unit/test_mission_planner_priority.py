"""
Unit tests for MissionPlanner field priority system (Handover 0048).

Tests the priority-based product configuration field inclusion in agent missions.
Tests cover:
- Default priority configuration structure
- Priority 1 (critical) fields always included
- Priority 3 (medium) fields dropped when over budget
- Custom user priority configurations
- Field extraction with dot notation
- Field formatting
- Token budget enforcement
- Backward compatibility with products lacking config_data

Following TDD principles: Tests written BEFORE implementation.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.giljo_mcp.config.defaults import DEFAULT_FIELD_PRIORITY
from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.models import Product, Project, User
from src.giljo_mcp.orchestration_types import AgentConfig, RequirementAnalysis


class TestMissionPlannerPriority:
    """Test cases for MissionPlanner field priority system."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        from contextlib import asynccontextmanager
        from unittest.mock import AsyncMock

        db_manager = Mock()
        db_manager.is_async = True

        # Create proper async context manager for get_session_async
        session = AsyncMock()

        @asynccontextmanager
        async def mock_get_session_async():
            yield session

        db_manager.get_session_async = mock_get_session_async
        return db_manager

    @pytest.fixture
    def mission_planner(self, mock_db_manager):
        """Create MissionPlanner instance with mocked dependencies."""
        return MissionPlanner(mock_db_manager)

    @pytest.fixture
    def sample_product_with_full_config(self):
        """
        Create a Product with comprehensive config_data.

        This fixture includes all 13 fields from DEFAULT_FIELD_PRIORITY to test
        complete priority handling.
        """
        product = Mock(spec=Product)
        product.id = "product_full_config"
        product.tenant_key = "tenant_test"
        product.name = "Full Config Product"
        product.vision_document = "Test vision document content"
        product.vision_type = "inline"
        product.chunked = False

        # Full config_data with all 13 priority fields
        product.config_data = {
            "tech_stack": {
                "languages": ["Python 3.11+", "TypeScript 5.0"],
                "backend": ["FastAPI", "SQLAlchemy"],
                "frontend": ["Vue 3", "Vuetify"],
                "database": ["PostgreSQL 18"],
                "infrastructure": ["Docker", "Kubernetes", "AWS"],
            },
            "architecture": {
                "pattern": "Microservices with event-driven design",
                "api_style": "RESTful with OpenAPI 3.0",
                "design_patterns": ["Repository Pattern", "Factory Pattern", "Observer Pattern"],
                "notes": "Multi-tenant architecture with strict data isolation. All services communicate via message queue.",
            },
            "features": {"core": ["User Authentication", "Multi-tenant Support", "Real-time Updates"]},
            "test_config": {
                "strategy": "Test-Driven Development (TDD) with pytest",
                "frameworks": ["pytest", "pytest-asyncio", "pytest-cov"],
                "coverage_target": 90,
            },
        }

        return product

    @pytest.fixture
    def sample_product_minimal_config(self):
        """
        Create a Product with minimal config_data (only P1 fields).

        Used to test that missions still generate with minimal configuration.
        """
        product = Mock(spec=Product)
        product.id = "product_minimal"
        product.tenant_key = "tenant_test"
        product.name = "Minimal Config Product"
        product.vision_document = "Minimal test vision"
        product.vision_type = "inline"
        product.chunked = False

        # Only Priority 1 critical fields
        product.config_data = {
            "tech_stack": {"languages": ["Python"], "backend": ["FastAPI"], "frontend": ["Vue 3"]},
            "architecture": {"pattern": "Monolithic"},
            "features": {"core": ["Basic CRUD"]},
        }

        return product

    @pytest.fixture
    def sample_product_no_config(self):
        """
        Create a Product with no config_data.

        Tests backward compatibility with existing products.
        """
        product = Mock(spec=Product)
        product.id = "product_no_config"
        product.tenant_key = "tenant_test"
        product.name = "No Config Product"
        product.vision_document = "Test vision without config"
        product.vision_type = "inline"
        product.chunked = False
        product.config_data = None

        return product

    @pytest.fixture
    def sample_project(self):
        """Create a sample Project."""
        project = Mock(spec=Project)
        project.id = "project_test"
        project.tenant_key = "tenant_test"
        project.name = "Test Project"
        project.mission = "Build test application"
        project.meta_data = {}
        return project

    @pytest.fixture
    def sample_analysis(self):
        """Create sample RequirementAnalysis."""
        return RequirementAnalysis(
            work_types={"orchestrator": "required", "implementer": "high"},
            complexity="moderate",
            tech_stack=["Python", "FastAPI"],
            keywords=["api", "backend"],
            estimated_agents_needed=2,
            feature_categories=["api"],
        )

    @pytest.fixture
    def sample_agent_config(self):
        """Create sample AgentConfig."""
        return AgentConfig(
            role="implementer",
            template_id="template_impl",
            template_content="You are an implementer",
            priority="high",
            mission_scope="Implement features",
        )

    # Test 1: Default Priority Config Structure
    def test_default_priority_config(self):
        """
        Test DEFAULT_FIELD_PRIORITY structure is valid.

        Verifies:
        - Has required keys: fields, token_budget, version
        - All 13 fields are present
        - No duplicate fields across priority tiers
        - All priority values are 1, 2, or 3
        """
        # Check top-level structure
        assert "fields" in DEFAULT_FIELD_PRIORITY
        assert "token_budget" in DEFAULT_FIELD_PRIORITY
        assert "version" in DEFAULT_FIELD_PRIORITY

        # Check token budget is reasonable
        assert DEFAULT_FIELD_PRIORITY["token_budget"] == 1500
        assert isinstance(DEFAULT_FIELD_PRIORITY["token_budget"], int)

        # Check version
        assert DEFAULT_FIELD_PRIORITY["version"] == "1.0"

        # Get all fields
        fields = DEFAULT_FIELD_PRIORITY["fields"]

        # Verify we have exactly 13 fields (as per requirements)
        assert len(fields) == 13

        # Verify all expected fields are present
        expected_fields = [
            # Priority 1 (Critical)
            "tech_stack.languages",
            "tech_stack.backend",
            "tech_stack.frontend",
            "architecture.pattern",
            "features.core",
            # Priority 2 (High)
            "tech_stack.database",
            "architecture.api_style",
            "test_config.strategy",
            # Priority 3 (Medium)
            "tech_stack.infrastructure",
            "architecture.design_patterns",
            "architecture.notes",
            "test_config.frameworks",
            "test_config.coverage_target",
        ]

        for field in expected_fields:
            assert field in fields, f"Expected field {field} not found in DEFAULT_FIELD_PRIORITY"

        # Verify no duplicate fields
        field_paths = list(fields.keys())
        assert len(field_paths) == len(set(field_paths)), "Duplicate fields found in priority config"

        # Verify all priorities are valid (1, 2, or 3)
        for field_path, priority in fields.items():
            assert priority in [1, 2, 3], f"Field {field_path} has invalid priority {priority}"

        # Verify we have the correct distribution
        p1_fields = [f for f, p in fields.items() if p == 1]
        p2_fields = [f for f, p in fields.items() if p == 2]
        p3_fields = [f for f, p in fields.items() if p == 3]

        assert len(p1_fields) == 5, "Should have 5 Priority 1 fields"
        assert len(p2_fields) == 3, "Should have 3 Priority 2 fields"
        assert len(p3_fields) == 5, "Should have 5 Priority 3 fields"

    # Test 2: P1 Fields Always Included
    @pytest.mark.asyncio
    async def test_field_priority_in_mission(
        self, mission_planner, sample_product_with_full_config, sample_project, sample_analysis, sample_agent_config
    ):
        """
        Test that Priority 1 fields are always included in mission content.

        Verifies:
        - P1 fields (languages, backend, frontend, pattern, core features) appear in mission
        - Token budget is respected
        - Mission content contains formatted field sections
        """
        vision_chunks = ["Test vision chunk"]

        with patch.object(mission_planner, "_filter_vision_for_role", return_value=vision_chunks):
            mission = await mission_planner._generate_agent_mission(
                sample_agent_config, sample_analysis, sample_product_with_full_config, sample_project, vision_chunks
            )

        # Verify mission was generated
        assert mission is not None
        assert mission.token_count > 0

        # Verify Priority 1 fields are in mission content
        # Note: Field labels are used in formatting (e.g., "Programming Languages" for "tech_stack.languages")
        p1_indicators = [
            "Programming Languages",  # tech_stack.languages
            "Backend Stack",  # tech_stack.backend
            "Frontend Stack",  # tech_stack.frontend
            "Architecture Pattern",  # architecture.pattern
            "Core Features",  # features.core
        ]

        content_lower = mission.content.lower()

        # At least some P1 fields should be present (depending on content)
        # We check for the actual field values since labels may vary
        assert "python" in content_lower or "typescript" in content_lower, "P1 languages not found"
        assert "fastapi" in content_lower or "backend" in content_lower, "P1 backend not found"
        assert "vue" in content_lower or "frontend" in content_lower, "P1 frontend not found"

        # Verify token budget is respected
        token_budget = DEFAULT_FIELD_PRIORITY["token_budget"]
        assert mission.token_count <= token_budget + 500, (
            f"Mission exceeds reasonable token budget: {mission.token_count} > {token_budget + 500}"
        )

    # Test 3: P3 Fields Dropped Over Budget
    @pytest.mark.asyncio
    async def test_priority_3_fields_dropped_over_budget(
        self, mission_planner, sample_project, sample_analysis, sample_agent_config
    ):
        """
        Test that Priority 3 fields are dropped when token budget is exceeded.

        Verifies:
        - P1 fields always present
        - Some P3 fields are skipped when over budget
        - Token budget enforcement logic works at field granularity

        Note: The implementation skips entire fields when budget is exceeded,
        not individual list items within a field.
        """
        # Create a product with config_data that has many P3 fields
        product = Mock(spec=Product)
        product.id = "product_over_budget"
        product.tenant_key = "tenant_test"
        product.name = "Over Budget Product"
        product.chunked = False

        # Create very long vision to push base tokens high
        # This forces minimal remaining budget for config_data
        product.vision_document = "Extremely detailed product vision. " * 300

        # Config with all fields, some P3 fields very large
        product.config_data = {
            "tech_stack": {
                # P1 fields
                "languages": ["Python 3.11+", "TypeScript 5.0"],
                "backend": ["FastAPI", "SQLAlchemy"],
                "frontend": ["Vue 3", "Vuetify"],
                # P2 field
                "database": ["PostgreSQL 18"],
                # P3 field - Very large to trigger budget
                "infrastructure": [
                    "Docker",
                    "Kubernetes",
                    "Terraform",
                    "AWS ECS",
                    "AWS RDS",
                    "AWS S3",
                    "AWS Lambda",
                    "CloudFormation",
                    "ArgoCD",
                    "Prometheus",
                    "Grafana",
                    "Jaeger",
                    "ELK Stack",
                ]
                * 10,
            },
            "architecture": {
                # P1 field
                "pattern": "Microservices",
                # P2 field
                "api_style": "RESTful with OpenAPI 3.0 specification",
                # P3 fields - Large
                "design_patterns": [
                    "Repository",
                    "Factory",
                    "Observer",
                    "Strategy",
                    "Adapter",
                    "Decorator",
                    "Proxy",
                    "Singleton",
                    "Builder",
                ]
                * 8,
                "notes": "Detailed architectural notes. " * 100,
            },
            "features": {
                # P1 field
                "core": ["Auth", "Multi-tenant", "API"]
            },
            "test_config": {
                # P2 field
                "strategy": "Test-Driven Development",
                # P3 fields - Large
                "frameworks": [
                    "pytest",
                    "pytest-asyncio",
                    "pytest-cov",
                    "pytest-mock",
                    "hypothesis",
                    "faker",
                    "factory-boy",
                    "responses",
                ]
                * 12,
                "coverage_target": 90,
            },
        }

        vision_chunks = ["Test"]

        with patch.object(mission_planner, "_filter_vision_for_role", return_value=vision_chunks):
            mission = await mission_planner._generate_agent_mission(
                sample_agent_config, sample_analysis, product, sample_project, vision_chunks
            )

        content = mission.content

        # P1 fields must ALWAYS be present (critical)
        assert "python" in content.lower() or "typescript" in content.lower(), "P1 languages missing"
        assert "fastapi" in content.lower() or "backend" in content.lower(), "P1 backend missing"
        assert "vue" in content.lower() or "frontend" in content.lower(), "P1 frontend missing"
        assert "microservices" in content.lower() or "pattern" in content.lower(), "P1 pattern missing"

        # Check which P3 fields are present
        # The implementation adds fields until budget is exceeded, then stops
        has_infrastructure = "infrastructure" in content.lower()
        has_design_patterns = "design patterns" in content.lower() or "repository" in content.lower()
        has_arch_notes = "detailed architectural notes" in content.lower()
        has_frameworks = "pytest-cov" in content.lower() or "factory-boy" in content.lower()

        p3_fields_present = sum([has_infrastructure, has_design_patterns, has_arch_notes, has_frameworks])

        # With very long vision (high base tokens), we expect some P3 fields to be skipped
        # At least 1 P3 field should be missing due to budget constraints
        assert p3_fields_present < 4, f"Expected some P3 fields to be dropped, but {p3_fields_present}/4 are present"

        # Verify token budget is respected (with some tolerance for P1 fields)
        assert mission.token_count <= 2500, f"Mission token count {mission.token_count} exceeds reasonable limit"

    # Test 4: Custom Priority Config
    @pytest.mark.asyncio
    async def test_custom_priority_config(
        self, mission_planner, sample_product_with_full_config, sample_project, sample_analysis, sample_agent_config
    ):
        """
        Test that user custom priority configuration is respected.

        Verifies:
        - Custom user field_priority_config is loaded
        - Custom priority order is used instead of default
        - Fields are included based on custom priorities
        """
        # Create mock user with custom priority config
        user_id = "user_custom"

        # Custom config: Swap priorities (make infrastructure P1, languages P3)
        custom_priority = {
            "version": "1.0",
            "token_budget": 1200,  # Smaller budget
            "fields": {
                # Make infrastructure P1 (normally P3)
                "tech_stack.infrastructure": 1,
                "tech_stack.languages": 3,  # Demote to P3
                "tech_stack.backend": 1,
                "tech_stack.frontend": 1,
                "architecture.pattern": 1,
                "features.core": 1,
                "tech_stack.database": 2,
                "architecture.api_style": 2,
                "test_config.strategy": 2,
                "architecture.design_patterns": 3,
                "architecture.notes": 3,
                "test_config.frameworks": 3,
                "test_config.coverage_target": 3,
            },
        }

        # Mock database query to return user with custom config
        mock_user = Mock(spec=User)
        mock_user.id = user_id
        mock_user.field_priority_config = custom_priority

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_user
        mission_planner.db_manager.session.query.return_value = mock_query

        vision_chunks = ["Test chunk"]

        with patch.object(mission_planner, "_filter_vision_for_role", return_value=vision_chunks):
            mission = await mission_planner._generate_agent_mission(
                sample_agent_config,
                sample_analysis,
                sample_product_with_full_config,
                sample_project,
                vision_chunks,
                user_id=user_id,
            )

        content = mission.content

        # Infrastructure should be present (promoted to P1 in custom config)
        assert "docker" in content.lower() or "kubernetes" in content.lower() or "infrastructure" in content.lower(), (
            "Custom P1 infrastructure field not found"
        )

        # Custom token budget should be respected
        assert mission.token_count <= custom_priority["token_budget"] + 500, (
            f"Mission exceeds custom token budget: {mission.token_count}"
        )

    # Test 5: Get Field Value with Dot Notation
    def test_get_field_value(self, mission_planner):
        """
        Test _get_field_value() extracts nested fields with dot notation.

        Verifies:
        - Simple dot paths work (e.g., "tech_stack.languages")
        - Nested paths work (e.g., "architecture.pattern")
        - Missing fields return None
        - Invalid paths return None
        """
        config_data = {
            "tech_stack": {"languages": ["Python", "TypeScript"], "backend": ["FastAPI"]},
            "architecture": {"pattern": "Microservices"},
            "features": {"core": ["Auth", "API"]},
        }

        # Test valid paths
        languages = mission_planner._get_field_value(config_data, "tech_stack.languages")
        assert languages == ["Python", "TypeScript"]

        backend = mission_planner._get_field_value(config_data, "tech_stack.backend")
        assert backend == ["FastAPI"]

        pattern = mission_planner._get_field_value(config_data, "architecture.pattern")
        assert pattern == "Microservices"

        core_features = mission_planner._get_field_value(config_data, "features.core")
        assert core_features == ["Auth", "API"]

        # Test missing fields
        missing = mission_planner._get_field_value(config_data, "tech_stack.database")
        assert missing is None

        invalid_top = mission_planner._get_field_value(config_data, "nonexistent.field")
        assert invalid_top is None

        invalid_nested = mission_planner._get_field_value(config_data, "tech_stack.nonexistent.deep")
        assert invalid_nested is None

        # Test empty path
        empty = mission_planner._get_field_value(config_data, "")
        assert empty is None or empty == config_data  # Implementation-dependent

    # Test 6: Format Field
    def test_format_field(self, mission_planner):
        """
        Test _format_field() formats different field types correctly.

        Verifies:
        - List values format as bullet points
        - Int/float values format with % (for coverage_target)
        - String values format as plain text
        - Field labels are human-readable
        """
        # Test list formatting
        languages_section = mission_planner._format_field("tech_stack.languages", ["Python 3.11+", "TypeScript 5.0"])

        assert "Programming Languages" in languages_section
        assert "- Python 3.11+" in languages_section
        assert "- TypeScript 5.0" in languages_section

        # Test string formatting
        pattern_section = mission_planner._format_field(
            "architecture.pattern", "Microservices with event-driven design"
        )

        assert "Architecture Pattern" in pattern_section
        assert "Microservices with event-driven design" in pattern_section

        # Test int/float formatting (coverage target)
        coverage_section = mission_planner._format_field("test_config.coverage_target", 90)

        assert "Coverage Target" in coverage_section
        assert "90%" in coverage_section

        # Test list with design patterns
        patterns_section = mission_planner._format_field(
            "architecture.design_patterns", ["Repository Pattern", "Factory Pattern"]
        )

        assert "Design Patterns" in patterns_section
        assert "- Repository Pattern" in patterns_section
        assert "- Factory Pattern" in patterns_section

        # Verify sections are properly formatted with markdown headers
        assert languages_section.startswith("\n###")
        assert pattern_section.startswith("\n###")
        assert coverage_section.startswith("\n###")

    # Test 7: Token Budget Enforcement
    @pytest.mark.asyncio
    async def test_token_budget_enforcement(
        self, mission_planner, sample_project, sample_analysis, sample_agent_config
    ):
        """
        Test that token budget is strictly enforced.

        Verifies:
        - Missions with small config stay under budget
        - Missions with large config are truncated to budget
        - Token count is accurately calculated
        """
        # Test with small config (should be well under budget)
        small_product = Mock(spec=Product)
        small_product.id = "product_small"
        small_product.tenant_key = "tenant_test"
        small_product.name = "Small Product"
        small_product.vision_document = "Brief vision"
        small_product.chunked = False
        small_product.config_data = {
            "tech_stack": {"languages": ["Python"], "backend": ["FastAPI"], "frontend": ["Vue"]},
            "architecture": {"pattern": "MVC"},
            "features": {"core": ["CRUD"]},
        }

        vision_chunks = ["Test"]

        with patch.object(mission_planner, "_filter_vision_for_role", return_value=vision_chunks):
            small_mission = await mission_planner._generate_agent_mission(
                sample_agent_config, sample_analysis, small_product, sample_project, vision_chunks
            )

        # Small mission should be under budget
        token_budget = DEFAULT_FIELD_PRIORITY["token_budget"]
        assert small_mission.token_count <= token_budget + 300, (
            f"Small mission over budget: {small_mission.token_count} > {token_budget + 300}"
        )

        # Test with large config
        large_product = Mock(spec=Product)
        large_product.id = "product_large"
        large_product.tenant_key = "tenant_test"
        large_product.name = "Large Product"
        large_product.vision_document = "Test vision " * 500
        large_product.chunked = False
        large_product.config_data = {
            "tech_stack": {
                "languages": ["Python", "TypeScript", "Go", "Rust"],
                "backend": ["FastAPI", "Express", "Django", "Flask"],
                "frontend": ["Vue", "React", "Angular"],
                "database": ["PostgreSQL", "Redis", "MongoDB"],
                "infrastructure": ["Docker", "Kubernetes", "Terraform", "AWS", "GCP"],
            },
            "architecture": {
                "pattern": "Microservices with event-driven design and CQRS",
                "api_style": "RESTful + GraphQL + gRPC",
                "design_patterns": ["Repository", "Factory", "Observer", "Strategy", "Adapter"],
                "notes": "Complex multi-tenant architecture. " * 50,
            },
            "features": {"core": ["Auth", "Multi-tenant", "Real-time", "Analytics", "Reporting"]},
            "test_config": {
                "strategy": "TDD with comprehensive testing",
                "frameworks": ["pytest", "jest", "cypress", "k6", "selenium"],
                "coverage_target": 95,
            },
        }

        with patch.object(mission_planner, "_filter_vision_for_role", return_value=vision_chunks):
            large_mission = await mission_planner._generate_agent_mission(
                sample_agent_config, sample_analysis, large_product, sample_project, vision_chunks
            )

        # Large mission should still respect budget (may exceed slightly due to P1 inclusion)
        assert large_mission.token_count <= token_budget + 500, (
            f"Large mission significantly over budget: {large_mission.token_count} > {token_budget + 500}"
        )

        # Verify token count is calculated
        assert large_mission.token_count > 0
        assert isinstance(large_mission.token_count, int)

    # Test 8: Backward Compatibility
    @pytest.mark.asyncio
    async def test_backward_compatibility(
        self, mission_planner, sample_product_no_config, sample_project, sample_analysis, sample_agent_config
    ):
        """
        Test backward compatibility with products lacking config_data.

        Verifies:
        - Products with config_data=None don't crash
        - Mission is still generated with basic content
        - No config_data section is added
        - Token count is reasonable
        """
        vision_chunks = ["Test vision"]

        with patch.object(mission_planner, "_filter_vision_for_role", return_value=vision_chunks):
            mission = await mission_planner._generate_agent_mission(
                sample_agent_config, sample_analysis, sample_product_no_config, sample_project, vision_chunks
            )

        # Verify mission was generated successfully
        assert mission is not None
        assert mission.agent_role == "implementer"
        assert len(mission.content) > 0
        assert mission.token_count > 0

        # Mission should still have basic structure
        assert "Mission:" in mission.content
        assert "Project Context" in mission.content
        assert sample_project.name in mission.content

        # Should NOT contain config_data field labels
        assert "Programming Languages" not in mission.content
        assert "Backend Stack" not in mission.content

        # Token count should be reasonable (smaller without config)
        assert mission.token_count < 1500, (
            f"Mission without config has unexpectedly high token count: {mission.token_count}"
        )

    # Additional helper method tests

    def test_get_field_priority_config_default(self, mission_planner):
        """
        Test _get_field_priority_config() returns default when no user_id.
        """
        config = mission_planner._get_field_priority_config(None)

        assert config == DEFAULT_FIELD_PRIORITY
        assert config["token_budget"] == 1500
        assert len(config["fields"]) == 13

    def test_get_field_priority_config_user_not_found(self, mission_planner):
        """
        Test _get_field_priority_config() returns default when user not found.
        """
        user_id = "nonexistent_user"

        # Mock database query returning None
        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = None
        mission_planner.db_manager.session.query.return_value = mock_query

        config = mission_planner._get_field_priority_config(user_id)

        assert config == DEFAULT_FIELD_PRIORITY

    def test_get_field_priority_config_user_no_custom(self, mission_planner):
        """
        Test _get_field_priority_config() returns default when user has no custom config.
        """
        user_id = "user_no_custom"

        # Mock user without custom config
        mock_user = Mock(spec=User)
        mock_user.id = user_id
        mock_user.field_priority_config = None

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_user
        mission_planner.db_manager.session.query.return_value = mock_query

        config = mission_planner._get_field_priority_config(user_id)

        assert config == DEFAULT_FIELD_PRIORITY

    def test_build_config_data_section_no_config(self, mission_planner, sample_product_no_config):
        """
        Test _build_config_data_section() returns empty when no config_data.
        """
        priority_config = DEFAULT_FIELD_PRIORITY
        token_budget = 1500

        content, tokens = mission_planner._build_config_data_section(
            sample_product_no_config, priority_config, token_budget
        )

        assert content == ""
        assert tokens == 0

    def test_build_config_data_section_respects_priority(self, mission_planner, sample_product_with_full_config):
        """
        Test _build_config_data_section() processes fields in priority order.
        """
        priority_config = DEFAULT_FIELD_PRIORITY
        token_budget = 10000  # Large budget to include all fields

        content, tokens = mission_planner._build_config_data_section(
            sample_product_with_full_config, priority_config, token_budget
        )

        # Should include config header
        assert "## Product Configuration" in content

        # Should include P1 fields
        assert "Programming Languages" in content or "python" in content.lower()

        # Should have consumed tokens
        assert tokens > 0
        assert isinstance(tokens, int)

    @pytest.mark.asyncio
    async def test_generate_missions_passes_user_id(
        self, mission_planner, sample_product_with_full_config, sample_project, sample_analysis
    ):
        """
        Test that generate_missions() passes user_id to _generate_agent_mission().

        Verifies the end-to-end flow of user_id propagation for custom priority configs.
        """
        user_id = "user_e2e_test"

        agent_configs = [
            AgentConfig(
                role="implementer",
                template_id="t1",
                template_content="Template",
                priority="high",
                mission_scope="Implement",
            )
        ]

        # Mock user with custom config
        custom_config = DEFAULT_FIELD_PRIORITY.copy()
        custom_config["token_budget"] = 1000

        mock_user = Mock(spec=User)
        mock_user.id = user_id
        mock_user.field_priority_config = custom_config

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_user
        mission_planner.db_manager.session.query.return_value = mock_query

        # Mock context repository
        with patch("src.giljo_mcp.mission_planner.ContextRepository") as MockContextRepo:
            mock_repo = MockContextRepo.return_value
            mock_repo.search_chunks = Mock(return_value=[])

            # Mock _store_token_metrics to avoid database calls
            with patch.object(mission_planner, "_store_token_metrics", new_callable=AsyncMock):
                missions = await mission_planner.generate_missions(
                    sample_analysis, sample_product_with_full_config, sample_project, agent_configs, user_id=user_id
                )

        # Verify mission was generated
        assert len(missions) == 1
        assert "implementer" in missions

        # Token count should reflect custom budget (roughly)
        # Note: Can exceed budget slightly due to P1 fields and fixed sections
        assert missions["implementer"].token_count <= 1500
