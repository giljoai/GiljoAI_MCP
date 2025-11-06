"""
Test suite for list_templates() bug fix in tool_accessor.py

Bug: list_templates() returns hardcoded empty array
Fix: Implement actual database query to AgentTemplate table with multi-tenant isolation

Tests:
- Empty template list (no templates in tenant)
- Single template returned correctly
- Multiple templates returned with correct structure
- Multi-tenant isolation (only tenant's templates returned)
- Database error handling
"""

import pytest
import pytest_asyncio
from sqlalchemy import select

from src.giljo_mcp.models import AgentTemplate
from src.giljo_mcp.tools.tool_accessor import ToolAccessor
from tests.utils.tools_helpers import ToolsTestHelper


class TestListTemplates:
    """Test suite for list_templates() method"""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, tools_test_setup):
        """Setup for each test method"""
        self.setup = tools_test_setup
        self.db_manager = tools_test_setup["db_manager"]
        self.tenant_manager = tools_test_setup["tenant_manager"]

        # Create test project and set as current tenant
        async with self.db_manager.get_session_async() as session:
            self.project = await ToolsTestHelper.create_test_project(
                session, "ListTemplates Test Project"
            )
            self.tenant_key = self.project.tenant_key
            self.tenant_manager.set_current_tenant(self.tenant_key)

    @pytest.mark.asyncio
    async def test_list_templates_empty(self):
        """Test list_templates returns empty array when no templates exist"""
        accessor = ToolAccessor(self.db_manager, self.tenant_manager)

        result = await accessor.list_templates()

        assert result["success"] is True
        assert "templates" in result
        assert isinstance(result["templates"], list)
        assert len(result["templates"]) == 0

    @pytest.mark.asyncio
    async def test_list_templates_single_template(self):
        """Test list_templates returns single template with correct structure"""
        # Create a test template
        async with self.db_manager.get_session_async() as session:
            template = AgentTemplate(
                id="test-template-1",
                tenant_key=self.tenant_key,
                name="test_orchestrator",
                category="role",
                role="orchestrator",
                template_content="Test mission for orchestrator",
                cli_tool="claude",
                background_color="#FF5733",
                tool="claude",
            )
            session.add(template)
            await session.commit()

        accessor = ToolAccessor(self.db_manager, self.tenant_manager)
        result = await accessor.list_templates()

        assert result["success"] is True
        assert len(result["templates"]) == 1
        template_dict = result["templates"][0]

        # Verify template structure
        assert template_dict["id"] == "test-template-1"
        assert template_dict["name"] == "test_orchestrator"
        assert template_dict["role"] == "orchestrator"
        assert template_dict["content"] == "Test mission for orchestrator"
        assert template_dict["cli_tool"] == "claude"
        assert template_dict["background_color"] == "#FF5733"

    @pytest.mark.asyncio
    async def test_list_templates_multiple_templates(self):
        """Test list_templates returns multiple templates in correct order"""
        # Create multiple test templates
        async with self.db_manager.get_session_async() as session:
            templates = [
                AgentTemplate(
                    id="test-template-1",
                    tenant_key=self.tenant_key,
                    name="orchestrator",
                    category="role",
                    role="orchestrator",
                    template_content="Orchestrator mission",
                    cli_tool="claude",
                    background_color="#FF5733",
                    tool="claude",
                ),
                AgentTemplate(
                    id="test-template-2",
                    tenant_key=self.tenant_key,
                    name="analyzer",
                    category="role",
                    role="analyzer",
                    template_content="Analyzer mission",
                    cli_tool="codex",
                    background_color="#00FF00",
                    tool="claude",
                ),
                AgentTemplate(
                    id="test-template-3",
                    tenant_key=self.tenant_key,
                    name="developer",
                    category="role",
                    role="developer",
                    template_content="Developer mission",
                    cli_tool="gemini",
                    background_color="#0000FF",
                    tool="claude",
                ),
            ]
            for template in templates:
                session.add(template)
            await session.commit()

        accessor = ToolAccessor(self.db_manager, self.tenant_manager)
        result = await accessor.list_templates()

        assert result["success"] is True
        assert len(result["templates"]) == 3

        # Verify all templates are present with correct data
        template_ids = [t["id"] for t in result["templates"]]
        assert "test-template-1" in template_ids
        assert "test-template-2" in template_ids
        assert "test-template-3" in template_ids

        # Verify correct roles
        roles = {t["id"]: t["role"] for t in result["templates"]}
        assert roles["test-template-1"] == "orchestrator"
        assert roles["test-template-2"] == "analyzer"
        assert roles["test-template-3"] == "developer"

    @pytest.mark.asyncio
    async def test_list_templates_multi_tenant_isolation(self):
        """Test list_templates returns only current tenant's templates"""
        # Create templates for current tenant
        async with self.db_manager.get_session_async() as session:
            template1 = AgentTemplate(
                id="tenant1-template-1",
                tenant_key=self.tenant_key,
                name="orchestrator",
                category="role",
                role="orchestrator",
                template_content="Tenant 1 mission",
                cli_tool="claude",
                background_color="#FF5733",
                tool="claude",
            )
            session.add(template1)
            await session.commit()

        # Create second tenant and its templates
        async with self.db_manager.get_session_async() as session:
            tenant2_project = await ToolsTestHelper.create_test_project(
                session, "Tenant 2 Project"
            )
            tenant2_key = tenant2_project.tenant_key

            template2 = AgentTemplate(
                id="tenant2-template-1",
                tenant_key=tenant2_key,
                name="analyzer",
                category="role",
                role="analyzer",
                template_content="Tenant 2 mission",
                cli_tool="codex",
                background_color="#00FF00",
                tool="claude",
            )
            session.add(template2)
            await session.commit()

        # Query as tenant 1 - should only see tenant 1's template
        accessor = ToolAccessor(self.db_manager, self.tenant_manager)
        result = await accessor.list_templates()

        assert result["success"] is True
        assert len(result["templates"]) == 1

        template_dict = result["templates"][0]
        assert template_dict["id"] == "tenant1-template-1"
        assert template_dict["name"] == "orchestrator"

    @pytest.mark.asyncio
    async def test_list_templates_no_tenant_context(self):
        """Test list_templates handles missing tenant context gracefully"""
        # Clear tenant context
        self.tenant_manager.set_current_tenant(None)

        accessor = ToolAccessor(self.db_manager, self.tenant_manager)
        result = await accessor.list_templates()

        # Should handle gracefully - either return empty list or error
        assert "success" in result
        if not result["success"]:
            assert "error" in result
        else:
            # If successful, should be empty list (no tenant context = no templates)
            assert isinstance(result["templates"], list)

    @pytest.mark.asyncio
    async def test_list_templates_structure_validation(self):
        """Test list_templates returns properly structured template objects"""
        # Create a template with all optional fields
        async with self.db_manager.get_session_async() as session:
            template = AgentTemplate(
                id="full-template",
                tenant_key=self.tenant_key,
                name="complete_template",
                category="role",
                role="orchestrator",
                template_content="Complete template content",
                cli_tool="claude",
                background_color="#ABCDEF",
                tool="claude",
            )
            session.add(template)
            await session.commit()

        accessor = ToolAccessor(self.db_manager, self.tenant_manager)
        result = await accessor.list_templates()

        assert result["success"] is True
        assert len(result["templates"]) == 1

        template_dict = result["templates"][0]

        # Verify all required fields are present
        required_fields = ["id", "name", "role", "content", "cli_tool", "background_color"]
        for field in required_fields:
            assert field in template_dict, f"Missing required field: {field}"
            assert template_dict[field] is not None, f"Field {field} is None"

    @pytest.mark.asyncio
    async def test_list_templates_database_error_handling(self):
        """Test list_templates handles database errors gracefully"""
        accessor = ToolAccessor(self.db_manager, self.tenant_manager)

        # Mock a database error
        original_get_session = self.db_manager.get_session_async

        async def broken_get_session(*args, **kwargs):
            raise RuntimeError("Database connection failed")

        self.db_manager.get_session_async = broken_get_session

        try:
            result = await accessor.list_templates()

            # Should return error response, not crash
            assert result["success"] is False
            assert "error" in result
        finally:
            # Restore original method
            self.db_manager.get_session_async = original_get_session

    @pytest.mark.asyncio
    async def test_list_templates_null_fields_handled(self):
        """Test list_templates handles null/optional fields correctly"""
        # Create a template with minimal fields
        async with self.db_manager.get_session_async() as session:
            template = AgentTemplate(
                id="minimal-template",
                tenant_key=self.tenant_key,
                name="minimal",
                category="role",
                role="developer",
                template_content="Minimal content",
                cli_tool="claude",
                background_color=None,  # Optional field
                tool="claude",
            )
            session.add(template)
            await session.commit()

        accessor = ToolAccessor(self.db_manager, self.tenant_manager)
        result = await accessor.list_templates()

        assert result["success"] is True
        assert len(result["templates"]) == 1

        template_dict = result["templates"][0]
        # Should handle None gracefully
        assert "background_color" in template_dict
        assert template_dict["background_color"] is None
