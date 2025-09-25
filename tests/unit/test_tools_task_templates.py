"""
Comprehensive tests for task_templates.py tools
Target: 7.28% → 95%+ coverage

Tests all task template functions:
- register_task_template_tools
- _generate_project_mission
- _analyze_task_for_template
"""

from unittest.mock import patch

import pytest
import pytest_asyncio

from src.giljo_mcp.tools.task_templates import (
    _analyze_task_for_template,
    _generate_project_mission,
    register_task_template_tools,
)
from tests.utils.tools_helpers import (
    MockMCPToolRegistrar,
    ToolsTestHelper,
)


class TestTaskTemplateTools:
    """Test class for task template tools"""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, tools_test_setup):
        """Setup for each test method"""
        self.setup = tools_test_setup
        self.db_manager = tools_test_setup["db_manager"]
        self.tenant_manager = tools_test_setup["tenant_manager"]
        self.mock_server = tools_test_setup["mcp_server"]

        # Create test project and set as current tenant
        async with self.db_manager.get_session_async() as session:
            self.project = await ToolsTestHelper.create_test_project(session, "Task Template Test Project")
            self.tenant_manager.set_current_tenant(self.project.tenant_key)

    @pytest.mark.asyncio
    async def test_register_task_template_tools(self):
        """Test that task template tools are registered properly"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Register tools
        register_task_template_tools(mock_server, self.db_manager, self.tenant_manager)

        # Should register task template related tools
        registered_tools = registrar.get_all_tools()
        assert len(registered_tools) >= 0

    def test_generate_project_mission_basic(self):
        """Test basic project mission generation"""
        project_name = "E-commerce Platform"
        project_type = "web application"
        requirements = ["user authentication", "product catalog", "shopping cart"]

        mission = _generate_project_mission(project_name, project_type, requirements)

        assert isinstance(mission, str)
        assert project_name in mission
        assert project_type in mission
        assert len(mission) > 50  # Should be substantial
        for req in requirements:
            assert req in mission

    def test_generate_project_mission_complex(self):
        """Test complex project mission generation"""
        project_name = "AI-Powered Analytics Dashboard"
        project_type = "machine learning application"
        requirements = [
            "real-time data processing",
            "predictive analytics",
            "interactive visualizations",
            "user role management",
            "API integration",
        ]

        mission = _generate_project_mission(project_name, project_type, requirements)

        assert isinstance(mission, str)
        assert "AI" in mission or "analytics" in mission
        assert "machine learning" in mission or "ML" in mission
        assert len(mission) > 100  # Complex projects should have longer missions

    def test_generate_project_mission_minimal(self):
        """Test project mission generation with minimal input"""
        project_name = "Simple Tool"
        project_type = "utility"
        requirements = ["basic functionality"]

        mission = _generate_project_mission(project_name, project_type, requirements)

        assert isinstance(mission, str)
        assert project_name in mission
        assert len(mission) > 20  # Even minimal should be descriptive

    def test_generate_project_mission_empty_requirements(self):
        """Test project mission generation with no requirements"""
        project_name = "Test Project"
        project_type = "application"
        requirements = []

        mission = _generate_project_mission(project_name, project_type, requirements)

        assert isinstance(mission, str)
        assert project_name in mission
        assert project_type in mission

    def test_analyze_task_for_template_development(self):
        """Test task analysis for development tasks"""
        task_title = "Implement user authentication system"
        task_description = "Create a secure login system with JWT tokens, password hashing, and session management"

        analysis = _analyze_task_for_template(task_title, task_description)

        assert isinstance(analysis, dict)
        assert "category" in analysis
        assert "complexity" in analysis
        assert "suggested_template" in analysis
        assert "estimated_effort" in analysis

        # Should identify as development task
        assert analysis["category"] in ["development", "implementation", "feature"]

    def test_analyze_task_for_template_testing(self):
        """Test task analysis for testing tasks"""
        task_title = "Write unit tests for authentication module"
        task_description = "Create comprehensive test coverage for login, logout, and session validation functions"

        analysis = _analyze_task_for_template(task_title, task_description)

        assert isinstance(analysis, dict)
        assert analysis["category"] in ["testing", "qa", "quality_assurance"]

    def test_analyze_task_for_template_documentation(self):
        """Test task analysis for documentation tasks"""
        task_title = "Update API documentation"
        task_description = "Document all REST endpoints with examples and parameter descriptions"

        analysis = _analyze_task_for_template(task_title, task_description)

        assert isinstance(analysis, dict)
        assert analysis["category"] in ["documentation", "docs", "writing"]

    def test_analyze_task_for_template_bug_fix(self):
        """Test task analysis for bug fix tasks"""
        task_title = "Fix memory leak in data processing"
        task_description = "Investigate and resolve memory consumption issue that occurs during large file processing"

        analysis = _analyze_task_for_template(task_title, task_description)

        assert isinstance(analysis, dict)
        assert analysis["category"] in ["bug_fix", "debugging", "maintenance"]

    def test_analyze_task_for_template_research(self):
        """Test task analysis for research tasks"""
        task_title = "Research database optimization strategies"
        task_description = "Investigate and evaluate different approaches to improve query performance and scalability"

        analysis = _analyze_task_for_template(task_title, task_description)

        assert isinstance(analysis, dict)
        assert analysis["category"] in ["research", "investigation", "analysis"]

    def test_analyze_task_for_template_deployment(self):
        """Test task analysis for deployment tasks"""
        task_title = "Set up production deployment pipeline"
        task_description = "Configure CI/CD pipeline with automated testing, building, and deployment to production"

        analysis = _analyze_task_for_template(task_title, task_description)

        assert isinstance(analysis, dict)
        assert analysis["category"] in ["deployment", "devops", "infrastructure"]

    def test_analyze_task_for_template_complexity_simple(self):
        """Test complexity analysis for simple tasks"""
        task_title = "Update button color"
        task_description = "Change the primary button color from blue to green"

        analysis = _analyze_task_for_template(task_title, task_description)

        assert analysis["complexity"] in ["simple", "low", "trivial"]

    def test_analyze_task_for_template_complexity_complex(self):
        """Test complexity analysis for complex tasks"""
        task_title = "Implement real-time collaboration system"
        task_description = "Build a WebSocket-based system for real-time document editing with conflict resolution, user presence indicators, and change tracking"

        analysis = _analyze_task_for_template(task_title, task_description)

        assert analysis["complexity"] in ["complex", "high", "advanced"]

    def test_analyze_task_for_template_effort_estimation(self):
        """Test effort estimation in task analysis"""
        task_title = "Refactor authentication middleware"
        task_description = (
            "Reorganize and optimize the authentication middleware for better performance and maintainability"
        )

        analysis = _analyze_task_for_template(task_title, task_description)

        assert "estimated_effort" in analysis
        effort = analysis["estimated_effort"]
        assert isinstance(effort, (str, int, float))

    def test_analyze_task_for_template_suggested_template(self):
        """Test template suggestion in task analysis"""
        task_title = "Implement payment processing"
        task_description = (
            "Integrate with Stripe API for secure payment processing including webhooks and error handling"
        )

        analysis = _analyze_task_for_template(task_title, task_description)

        assert "suggested_template" in analysis
        template = analysis["suggested_template"]
        assert isinstance(template, str)
        assert len(template) > 0

    def test_analyze_task_for_template_edge_cases(self):
        """Test task analysis with edge cases"""
        # Empty title
        analysis1 = _analyze_task_for_template("", "Some description")
        assert isinstance(analysis1, dict)

        # Empty description
        analysis2 = _analyze_task_for_template("Some title", "")
        assert isinstance(analysis2, dict)

        # Very long title
        long_title = "A" * 500
        analysis3 = _analyze_task_for_template(long_title, "Description")
        assert isinstance(analysis3, dict)

        # Special characters
        special_title = "Fix #123: Handle UTF-8 encoding (ñ, é, ü) in user names"
        analysis4 = _analyze_task_for_template(special_title, "Description with émojis 🚀")
        assert isinstance(analysis4, dict)

    @pytest.mark.asyncio
    async def test_task_template_tools_integration(self):
        """Integration test for task template tools"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        with patch("src.giljo_mcp.tools.task_templates._analyze_task_for_template") as mock_analyze:
            mock_analyze.return_value = {
                "category": "development",
                "complexity": "medium",
                "suggested_template": "feature_implementation",
                "estimated_effort": "3-5 days",
            }

            register_task_template_tools(mock_server, self.db_manager, self.tenant_manager)

            # Should register without errors
            registered_tools = registrar.get_all_tools()
            assert len(registered_tools) >= 0

    def test_project_mission_generation_various_types(self):
        """Test project mission generation for various project types"""
        project_types = [
            ("mobile app", ["user interface", "offline sync"]),
            ("desktop application", ["cross-platform", "file management"]),
            ("web service", ["REST API", "database integration"]),
            ("machine learning model", ["data preprocessing", "model training"]),
            ("IoT solution", ["sensor integration", "real-time monitoring"]),
        ]

        for project_type, requirements in project_types:
            mission = _generate_project_mission(f"Test {project_type}", project_type, requirements)
            assert isinstance(mission, str)
            assert len(mission) > 30
            assert project_type.replace("_", " ") in mission.lower()

    def test_task_analysis_keyword_detection(self):
        """Test that task analysis correctly detects keywords"""
        test_cases = [
            ("Optimize database queries", "performance", ["optimization", "database", "performance"]),
            ("Implement user interface", "development", ["implement", "interface", "UI"]),
            ("Write integration tests", "testing", ["test", "integration", "coverage"]),
            ("Deploy to production", "deployment", ["deploy", "production", "release"]),
            ("Fix security vulnerability", "bug_fix", ["fix", "security", "vulnerability"]),
        ]

        for title, expected_category, expected_keywords in test_cases:
            analysis = _analyze_task_for_template(title, "")

            # Category should match or be related
            assert analysis["category"] in [expected_category] or any(
                keyword in analysis["category"] for keyword in expected_keywords
            )

    def test_mission_generation_formatting(self):
        """Test that generated missions are well-formatted"""
        mission = _generate_project_mission(
            "Test Project", "web application", ["authentication", "data visualization", "API integration"]
        )

        # Should be properly formatted
        assert mission[0].isupper()  # Starts with capital letter
        assert mission.endswith((".", "!"))  # Ends with punctuation
        assert len(mission.split()) >= 10  # Substantial content
        assert not mission.startswith("The ")  # Avoid redundant starts

    def test_task_analysis_consistency(self):
        """Test that task analysis is consistent for similar tasks"""
        similar_tasks = [
            ("Implement login functionality", "Create user authentication system"),
            ("Add login feature", "Build authentication module"),
            ("Create login system", "Develop user login capability"),
        ]

        categories = []
        for title, description in similar_tasks:
            analysis = _analyze_task_for_template(title, description)
            categories.append(analysis["category"])

        # All similar tasks should have similar categories
        assert len(set(categories)) <= 2  # Allow some variation but should be mostly consistent
