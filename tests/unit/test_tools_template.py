"""
Comprehensive tests for template.py tools
Target: 4.05% → 95%+ coverage

Tests all template tool functions:
- register_template_tools
- list_agent_templates
- get_agent_template
- create_agent_template
- update_agent_template
- archive_template
- create_template_augmentation
- restore_template_version
- suggest_template
- get_template_stats
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
import pytest_asyncio

from src.giljo_mcp.models import AgentTemplate, TemplateArchive, TemplateUsageStats
from src.giljo_mcp.tools.template import register_template_tools
from tests.utils.tools_helpers import (
    AssertionHelpers,
    MockMCPToolRegistrar,
    ToolsTestHelper,
)


class TestTemplateTools:
    """Test class for template tools"""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, tools_test_setup):
        """Setup for each test method"""
        self.setup = tools_test_setup
        self.db_manager = tools_test_setup["db_manager"]
        self.tenant_manager = tools_test_setup["tenant_manager"]
        self.mock_server = tools_test_setup["mcp_server"]

        # Create test project and set as current tenant
        async with self.db_manager.get_session_async() as session:
            self.project = await ToolsTestHelper.create_test_project(session, "Template Test Project")
            self.tenant_manager.set_current_tenant(self.project.tenant_key)

    async def create_test_template(
        self, session, name: str = "test_template", role: str = "analyzer", category: str = "role"
    ) -> AgentTemplate:
        """Helper to create test template"""
        template = AgentTemplate(
            id=str(uuid.uuid4()),
            name=name,
            category=category,
            role=role,
            project_type="test",
            description="Test template description",
            mission_template="Analyze {component} for {project_name}",
            version="1.0.0",
            is_default=False,
            is_active=True,
            usage_count=0,
            variables=["component", "project_name"],
            tags=["test", "analysis"],
            tenant_key=self.project.tenant_key,
            product_id=self.project.id,
            created_at=datetime.now(timezone.utc),
        )
        session.add(template)
        await session.commit()
        await session.refresh(template)
        return template

    @pytest.mark.asyncio
    async def test_register_template_tools(self):
        """Test that all template tools are registered properly"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Register tools
        register_template_tools(mock_server, self.db_manager, self.tenant_manager)

        # Verify all expected tools are registered
        expected_tools = [
            "list_agent_templates",
            "get_agent_template",
            "create_agent_template",
            "update_agent_template",
            "archive_template",
            "create_template_augmentation",
            "restore_template_version",
            "suggest_template",
            "get_template_stats",
        ]

        registered_tools = registrar.get_all_tools()
        for tool in expected_tools:
            AssertionHelpers.assert_tool_registered(registrar, tool)

        assert len(registered_tools) >= len(expected_tools)

    # list_agent_templates tests
    @pytest.mark.asyncio
    async def test_list_agent_templates_all(self):
        """Test listing all agent templates"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create test templates
        async with self.db_manager.get_session_async() as session:
            await self.create_test_template(session, "template1", "analyzer", "role")
            await self.create_test_template(session, "template2", "orchestrator", "role")
            await self.create_test_template(session, "template3", "implementer", "custom")

        register_template_tools(mock_server, self.db_manager, self.tenant_manager)
        list_templates = registrar.get_registered_tool("list_agent_templates")

        result = await list_templates()

        AssertionHelpers.assert_success_response(result, ["count", "templates"])
        assert result["count"] == 3
        assert len(result["templates"]) == 3

    @pytest.mark.asyncio
    async def test_list_agent_templates_with_filters(self):
        """Test listing templates with various filters"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create test templates with different attributes
        async with self.db_manager.get_session_async() as session:
            await self.create_test_template(session, "analyzer1", "analyzer", "role")
            await self.create_test_template(session, "analyzer2", "analyzer", "role")
            await self.create_test_template(session, "orchestrator1", "orchestrator", "role")

        register_template_tools(mock_server, self.db_manager, self.tenant_manager)
        list_templates = registrar.get_registered_tool("list_agent_templates")

        # Test role filter
        result = await list_templates(role="analyzer")
        AssertionHelpers.assert_success_response(result)
        assert result["count"] == 2
        assert all(template["role"] == "analyzer" for template in result["templates"])

        # Test category filter
        result2 = await list_templates(category="role")
        AssertionHelpers.assert_success_response(result2)
        assert result2["count"] == 3

    @pytest.mark.asyncio
    async def test_list_agent_templates_inactive(self):
        """Test listing inactive templates"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create active and inactive templates
        async with self.db_manager.get_session_async() as session:
            await self.create_test_template(session, "active", "analyzer", "role")

            inactive_template = AgentTemplate(
                id=str(uuid.uuid4()),
                name="inactive",
                category="role",
                role="analyzer",
                project_type="test",
                description="Inactive template",
                mission_template="Inactive mission",
                version="1.0.0",
                is_default=False,
                is_active=False,  # Inactive
                usage_count=0,
                tenant_key=self.project.tenant_key,
                product_id=self.project.id,
                created_at=datetime.now(timezone.utc),
            )
            session.add(inactive_template)
            await session.commit()

        register_template_tools(mock_server, self.db_manager, self.tenant_manager)
        list_templates = registrar.get_registered_tool("list_agent_templates")

        # Test active templates (default)
        result = await list_templates()
        AssertionHelpers.assert_success_response(result)
        assert result["count"] == 1

        # Test inactive templates
        result2 = await list_templates(is_active=False)
        AssertionHelpers.assert_success_response(result2)
        assert result2["count"] == 1
        assert result2["templates"][0]["name"] == "inactive"

    # get_agent_template tests
    @pytest.mark.asyncio
    async def test_get_agent_template_by_id(self):
        """Test getting template by ID"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create test template
        async with self.db_manager.get_session_async() as session:
            template = await self.create_test_template(session, "test_template")

        register_template_tools(mock_server, self.db_manager, self.tenant_manager)
        get_template = registrar.get_registered_tool("get_agent_template")

        result = await get_template(template_id=template.id)

        AssertionHelpers.assert_success_response(result, ["template"])
        assert result["template"]["name"] == "test_template"
        assert result["template"]["role"] == "analyzer"

    @pytest.mark.asyncio
    async def test_get_agent_template_by_name(self):
        """Test getting template by name"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create test template
        async with self.db_manager.get_session_async() as session:
            await self.create_test_template(session, "unique_template")

        register_template_tools(mock_server, self.db_manager, self.tenant_manager)
        get_template = registrar.get_registered_tool("get_agent_template")

        result = await get_template(name="unique_template")

        AssertionHelpers.assert_success_response(result, ["template"])
        assert result["template"]["name"] == "unique_template"

    @pytest.mark.asyncio
    async def test_get_agent_template_not_found(self):
        """Test getting non-existent template"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_template_tools(mock_server, self.db_manager, self.tenant_manager)
        get_template = registrar.get_registered_tool("get_agent_template")

        result = await get_template(template_id=str(uuid.uuid4()))

        AssertionHelpers.assert_error_response(result, "Template not found")

    @pytest.mark.asyncio
    async def test_get_agent_template_with_processing(self):
        """Test getting template with variable processing"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create test template with variables
        async with self.db_manager.get_session_async() as session:
            await self.create_test_template(session, "parameterized_template")

        register_template_tools(mock_server, self.db_manager, self.tenant_manager)
        get_template = registrar.get_registered_tool("get_agent_template")

        with patch("src.giljo_mcp.tools.template.process_template") as mock_process:
            mock_process.return_value = "Processed mission template"

            result = await get_template(
                name="parameterized_template", variables={"component": "authentication", "project_name": "TestProject"}
            )

        AssertionHelpers.assert_success_response(result, ["template", "processed_mission"])
        assert "processed_mission" in result

    # create_agent_template tests
    @pytest.mark.asyncio
    async def test_create_agent_template_success(self):
        """Test successful template creation"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_template_tools(mock_server, self.db_manager, self.tenant_manager)
        create_template = registrar.get_registered_tool("create_agent_template")

        result = await create_template(
            name="new_template",
            category="role",
            role="tester",
            project_type="web",
            description="Template for testing",
            mission_template="Test {component} thoroughly",
            variables=["component"],
            tags=["testing", "qa"],
        )

        AssertionHelpers.assert_success_response(result, ["template_id", "created"])
        assert result["template"]["name"] == "new_template"
        assert result["template"]["role"] == "tester"

    @pytest.mark.asyncio
    async def test_create_agent_template_duplicate_name(self):
        """Test creating template with duplicate name"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create existing template
        async with self.db_manager.get_session_async() as session:
            await self.create_test_template(session, "duplicate_name")

        register_template_tools(mock_server, self.db_manager, self.tenant_manager)
        create_template = registrar.get_registered_tool("create_agent_template")

        result = await create_template(
            name="duplicate_name", category="role", role="analyzer", mission_template="Test mission"
        )

        AssertionHelpers.assert_error_response(result, "already exists")

    @pytest.mark.asyncio
    async def test_create_agent_template_missing_required_fields(self):
        """Test creating template with missing required fields"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_template_tools(mock_server, self.db_manager, self.tenant_manager)
        create_template = registrar.get_registered_tool("create_agent_template")

        result = await create_template(
            category="role",
            role="analyzer",
            # Missing name and mission_template
        )

        AssertionHelpers.assert_error_response(result, "required")

    # update_agent_template tests
    @pytest.mark.asyncio
    async def test_update_agent_template_success(self):
        """Test successful template update"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create test template
        async with self.db_manager.get_session_async() as session:
            template = await self.create_test_template(session, "updateable_template")

        register_template_tools(mock_server, self.db_manager, self.tenant_manager)
        update_template = registrar.get_registered_tool("update_agent_template")

        result = await update_template(
            template_id=template.id,
            description="Updated description",
            mission_template="Updated mission for {component}",
            tags=["updated", "modified"],
        )

        AssertionHelpers.assert_success_response(result, ["template", "updated"])
        assert result["template"]["description"] == "Updated description"

    @pytest.mark.asyncio
    async def test_update_agent_template_not_found(self):
        """Test updating non-existent template"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_template_tools(mock_server, self.db_manager, self.tenant_manager)
        update_template = registrar.get_registered_tool("update_agent_template")

        result = await update_template(template_id=str(uuid.uuid4()), description="New description")

        AssertionHelpers.assert_error_response(result, "Template not found")

    @pytest.mark.asyncio
    async def test_update_agent_template_version_increment(self):
        """Test that template update increments version"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create test template
        async with self.db_manager.get_session_async() as session:
            template = await self.create_test_template(session, "versioned_template")
            original_version = template.version

        register_template_tools(mock_server, self.db_manager, self.tenant_manager)
        update_template = registrar.get_registered_tool("update_agent_template")

        result = await update_template(template_id=template.id, mission_template="Updated mission template")

        AssertionHelpers.assert_success_response(result)
        assert result["template"]["version"] != original_version

    # archive_template tests
    @pytest.mark.asyncio
    async def test_archive_template_success(self):
        """Test successful template archival"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create test template
        async with self.db_manager.get_session_async() as session:
            template = await self.create_test_template(session, "archivable_template")

        register_template_tools(mock_server, self.db_manager, self.tenant_manager)
        archive_template = registrar.get_registered_tool("archive_template")

        result = await archive_template(template_id=template.id, reason="No longer needed")

        AssertionHelpers.assert_success_response(result, ["archived", "archive_id"])
        assert result["archived"] is True

    @pytest.mark.asyncio
    async def test_archive_template_not_found(self):
        """Test archiving non-existent template"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_template_tools(mock_server, self.db_manager, self.tenant_manager)
        archive_template = registrar.get_registered_tool("archive_template")

        result = await archive_template(template_id=str(uuid.uuid4()))

        AssertionHelpers.assert_error_response(result, "Template not found")

    # create_template_augmentation tests
    @pytest.mark.asyncio
    async def test_create_template_augmentation_success(self):
        """Test successful template augmentation creation"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create test template
        async with self.db_manager.get_session_async() as session:
            template = await self.create_test_template(session, "augmentable_template")

        register_template_tools(mock_server, self.db_manager, self.tenant_manager)
        create_augmentation = registrar.get_registered_tool("create_template_augmentation")

        result = await create_augmentation(
            template_id=template.id,
            augmentation_name="security_focus",
            augmentation_content="Focus particularly on security aspects",
            context="security review",
        )

        AssertionHelpers.assert_success_response(result, ["augmentation_id", "created"])
        assert result["augmentation"]["name"] == "security_focus"

    @pytest.mark.asyncio
    async def test_create_template_augmentation_invalid_template(self):
        """Test creating augmentation for non-existent template"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_template_tools(mock_server, self.db_manager, self.tenant_manager)
        create_augmentation = registrar.get_registered_tool("create_template_augmentation")

        result = await create_augmentation(
            template_id=str(uuid.uuid4()), augmentation_name="test_aug", augmentation_content="Test content"
        )

        AssertionHelpers.assert_error_response(result, "Template not found")

    # restore_template_version tests
    @pytest.mark.asyncio
    async def test_restore_template_version_success(self):
        """Test successful template version restoration"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create template and archive
        async with self.db_manager.get_session_async() as session:
            template = await self.create_test_template(session, "restorable_template")

            # Create archive entry
            archive = TemplateArchive(
                id=str(uuid.uuid4()),
                template_id=template.id,
                version_archived="1.0.0",
                archived_data={
                    "name": template.name,
                    "mission_template": template.mission_template,
                    "description": template.description,
                },
                reason="backup",
                tenant_key=self.project.tenant_key,
                archived_at=datetime.now(timezone.utc),
            )
            session.add(archive)
            await session.commit()

        register_template_tools(mock_server, self.db_manager, self.tenant_manager)
        restore_version = registrar.get_registered_tool("restore_template_version")

        result = await restore_version(template_id=template.id, archive_id=archive.id)

        AssertionHelpers.assert_success_response(result, ["restored", "template"])
        assert result["restored"] is True

    @pytest.mark.asyncio
    async def test_restore_template_version_not_found(self):
        """Test restoring non-existent archive"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_template_tools(mock_server, self.db_manager, self.tenant_manager)
        restore_version = registrar.get_registered_tool("restore_template_version")

        result = await restore_version(template_id=str(uuid.uuid4()), archive_id=str(uuid.uuid4()))

        AssertionHelpers.assert_error_response(result, "not found")

    # suggest_template tests
    @pytest.mark.asyncio
    async def test_suggest_template_success(self):
        """Test template suggestion based on context"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create test templates with different roles
        async with self.db_manager.get_session_async() as session:
            analyzer_template = await self.create_test_template(session, "analyzer_template", "analyzer")
            orchestrator_template = await self.create_test_template(session, "orchestrator_template", "orchestrator")

            # Update usage counts
            analyzer_template.usage_count = 10
            orchestrator_template.usage_count = 5
            await session.commit()

        register_template_tools(mock_server, self.db_manager, self.tenant_manager)
        suggest_template = registrar.get_registered_tool("suggest_template")

        result = await suggest_template(role="analyzer", project_type="test", context="code analysis needed")

        AssertionHelpers.assert_success_response(result, ["suggestions", "criteria"])
        assert len(result["suggestions"]) > 0
        assert result["suggestions"][0]["role"] == "analyzer"

    @pytest.mark.asyncio
    async def test_suggest_template_no_matches(self):
        """Test template suggestion with no matches"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_template_tools(mock_server, self.db_manager, self.tenant_manager)
        suggest_template = registrar.get_registered_tool("suggest_template")

        result = await suggest_template(role="nonexistent_role", project_type="unknown")

        AssertionHelpers.assert_success_response(result, ["suggestions"])
        assert len(result["suggestions"]) == 0

    # get_template_stats tests
    @pytest.mark.asyncio
    async def test_get_template_stats_success(self):
        """Test getting template usage statistics"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create test templates and usage stats
        async with self.db_manager.get_session_async() as session:
            template1 = await self.create_test_template(session, "popular_template", "analyzer")
            await self.create_test_template(session, "unused_template", "orchestrator")

            # Create usage stats
            stats = TemplateUsageStats(
                id=str(uuid.uuid4()),
                template_id=template1.id,
                usage_count=50,
                last_used=datetime.now(timezone.utc),
                avg_performance_score=8.5,
                tenant_key=self.project.tenant_key,
                created_at=datetime.now(timezone.utc),
            )
            session.add(stats)
            await session.commit()

        register_template_tools(mock_server, self.db_manager, self.tenant_manager)
        get_stats = registrar.get_registered_tool("get_template_stats")

        result = await get_stats()

        AssertionHelpers.assert_success_response(result, ["stats", "summary"])
        assert "total_templates" in result["summary"]
        assert "most_used" in result["summary"]

    @pytest.mark.asyncio
    async def test_get_template_stats_specific_template(self):
        """Test getting stats for specific template"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create test template
        async with self.db_manager.get_session_async() as session:
            template = await self.create_test_template(session, "stats_template")

        register_template_tools(mock_server, self.db_manager, self.tenant_manager)
        get_stats = registrar.get_registered_tool("get_template_stats")

        result = await get_stats(template_id=template.id)

        AssertionHelpers.assert_success_response(result, ["template_id", "stats"])
        assert result["template_id"] == template.id

    # Error handling and edge cases
    @pytest.mark.asyncio
    async def test_template_tools_database_error_handling(self):
        """Test that template tools handle database errors gracefully"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Mock database to raise exception
        with patch.object(self.db_manager, "get_session_async") as mock_get_session:
            mock_get_session.side_effect = Exception("Database connection failed")

            register_template_tools(mock_server, self.db_manager, self.tenant_manager)
            list_templates = registrar.get_registered_tool("list_agent_templates")

            result = await list_templates()

        AssertionHelpers.assert_error_response(result, "Database connection failed")

    @pytest.mark.asyncio
    async def test_template_variable_extraction(self):
        """Test template variable extraction from mission templates"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_template_tools(mock_server, self.db_manager, self.tenant_manager)
        create_template = registrar.get_registered_tool("create_agent_template")

        with patch("src.giljo_mcp.tools.template.extract_variables") as mock_extract:
            mock_extract.return_value = ["project_name", "component", "deadline"]

            result = await create_template(
                name="variable_template",
                category="role",
                role="analyzer",
                mission_template="Analyze {component} for {project_name} by {deadline}",
            )

        AssertionHelpers.assert_success_response(result)
        mock_extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_template_performance_metrics(self):
        """Test template performance tracking"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create template with performance metrics
        async with self.db_manager.get_session_async() as session:
            template = await self.create_test_template(session, "performance_template")
            template.usage_count = 100

            # Create performance stats
            stats = TemplateUsageStats(
                id=str(uuid.uuid4()),
                template_id=template.id,
                usage_count=100,
                last_used=datetime.now(timezone.utc),
                avg_performance_score=9.2,
                success_rate=0.95,
                tenant_key=self.project.tenant_key,
                created_at=datetime.now(timezone.utc),
            )
            session.add(stats)
            await session.commit()

        register_template_tools(mock_server, self.db_manager, self.tenant_manager)
        get_stats = registrar.get_registered_tool("get_template_stats")

        result = await get_stats(template_id=template.id)

        AssertionHelpers.assert_success_response(result)
        assert result["stats"]["avg_performance_score"] == 9.2
        assert result["stats"]["success_rate"] == 0.95

    @pytest.mark.asyncio
    async def test_template_versioning_workflow(self):
        """Test complete template versioning workflow"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_template_tools(mock_server, self.db_manager, self.tenant_manager)
        create_template = registrar.get_registered_tool("create_agent_template")
        update_template = registrar.get_registered_tool("update_agent_template")
        archive_template = registrar.get_registered_tool("archive_template")
        registrar.get_registered_tool("restore_template_version")

        # Create template
        create_result = await create_template(
            name="versioned_template", category="role", role="analyzer", mission_template="Original mission v1.0"
        )
        AssertionHelpers.assert_success_response(create_result)
        template_id = create_result["template_id"]

        # Update template (creates new version)
        update_result = await update_template(template_id=template_id, mission_template="Updated mission v2.0")
        AssertionHelpers.assert_success_response(update_result)

        # Archive current version
        archive_result = await archive_template(template_id=template_id, reason="Testing versioning")
        AssertionHelpers.assert_success_response(archive_result)

        # The complete workflow demonstrates versioning capabilities
        assert create_result["template"]["version"] != update_result["template"]["version"]

    @pytest.mark.asyncio
    async def test_template_augmentation_workflow(self):
        """Test template augmentation workflow"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create template
        async with self.db_manager.get_session_async() as session:
            template = await self.create_test_template(session, "augmentable_template")

        register_template_tools(mock_server, self.db_manager, self.tenant_manager)
        create_augmentation = registrar.get_registered_tool("create_template_augmentation")
        get_template = registrar.get_registered_tool("get_agent_template")

        # Create augmentation
        aug_result = await create_augmentation(
            template_id=template.id,
            augmentation_name="security_focus",
            augmentation_content="Pay special attention to security vulnerabilities",
        )
        AssertionHelpers.assert_success_response(aug_result)

        # Get template with augmentation
        template_result = await get_template(template_id=template.id, augmentations=["security_focus"])
        AssertionHelpers.assert_success_response(template_result)

    @pytest.mark.asyncio
    async def test_template_search_and_filtering_advanced(self):
        """Test advanced template search and filtering"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create templates with various attributes
        async with self.db_manager.get_session_async() as session:
            # High usage template
            popular_template = await self.create_test_template(session, "popular_analyzer", "analyzer", "role")
            popular_template.usage_count = 100
            popular_template.tags = ["popular", "reliable"]

            # New template
            new_template = await self.create_test_template(session, "new_orchestrator", "orchestrator", "role")
            new_template.usage_count = 2
            new_template.tags = ["new", "experimental"]

            await session.commit()

        register_template_tools(mock_server, self.db_manager, self.tenant_manager)
        list_templates = registrar.get_registered_tool("list_agent_templates")

        # Test multiple filters
        result = await list_templates(category="role", role="analyzer")
        AssertionHelpers.assert_success_response(result)
        assert result["count"] == 1
        assert result["templates"][0]["name"] == "popular_analyzer"
