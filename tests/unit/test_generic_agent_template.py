"""
Tests for Generic Agent Template Feature (Handover 0246b).

Test-driven development: These tests define expected behavior BEFORE implementation.
Tests should initially FAIL until implementation is complete.

Feature Requirements:
1. Create GenericAgentTemplate class with render() method
2. Template accepts 5 parameters: agent_id, job_id, product_id, project_id, tenant_key
3. Template includes all 6 protocol phases
4. Template references all required MCP tools
5. Token budget: 2000-3000 tokens (estimated)
6. MCP tool integration: get_generic_agent_template()
7. Works for all agent types (implementer, tester, reviewer, documenter, analyzer)
"""

from uuid import uuid4

import pytest

# Import will fail initially - expected in RED phase
from src.giljo_mcp.templates.generic_agent_template import GenericAgentTemplate


class TestGenericAgentTemplate:
    """Test suite for generic agent template."""

    def test_template_exists(self):
        """Verify GenericAgentTemplate class exists"""
        # Will FAIL - class doesn't exist yet
        template = GenericAgentTemplate()
        assert template is not None

    def test_template_renders_successfully(self):
        """Template renders without errors"""
        template = GenericAgentTemplate()
        rendered = template.render(
            agent_id=str(uuid4()),
            job_id=str(uuid4()),
            product_id=str(uuid4()),
            project_id=str(uuid4()),
            tenant_key="test_tenant"
        )
        assert rendered is not None
        assert isinstance(rendered, str)
        assert len(rendered) > 0

    def test_all_variables_injected(self):
        """All 5 variables appear in rendered template"""
        template = GenericAgentTemplate()

        agent_id = "test-agent-123"
        job_id = "test-job-456"
        product_id = "test-product-789"
        project_id = "test-project-000"
        tenant_key = "test_tenant_xyz"

        rendered = template.render(
            agent_id=agent_id,
            job_id=job_id,
            product_id=product_id,
            project_id=project_id,
            tenant_key=tenant_key
        )

        assert agent_id in rendered
        assert job_id in rendered
        assert product_id in rendered
        assert project_id in rendered
        assert tenant_key in rendered

    def test_all_6_protocol_phases_present(self):
        """Template includes all 6 protocol phases"""
        template = GenericAgentTemplate()
        rendered = template.render(
            agent_id=str(uuid4()),
            job_id=str(uuid4()),
            product_id=str(uuid4()),
            project_id=str(uuid4()),
            tenant_key="test_tenant"
        )

        assert "Phase 1: Initialization" in rendered
        assert "Phase 2: Mission Fetch" in rendered
        assert "Phase 3: Work Execution" in rendered
        assert "Phase 4: Progress Reporting" in rendered
        assert "Phase 5: Communication" in rendered
        assert "Phase 6: Completion" in rendered

    def test_mcp_tool_references_present(self):
        """Template references all required MCP tools with CORRECT command names"""
        template = GenericAgentTemplate()
        rendered = template.render(
            agent_id=str(uuid4()),
            job_id=str(uuid4()),
            product_id=str(uuid4()),
            project_id=str(uuid4()),
            tenant_key="test_tenant"
        )

        # Phase 1: Initialization - should have acknowledge_job()
        assert "acknowledge_job" in rendered, "Missing acknowledge_job() in Phase 1"

        # Phase 2: Mission Fetch - should have get_agent_mission()
        assert "get_agent_mission" in rendered, "Missing get_agent_mission() in Phase 2"

        # Phase 3: Work Execution - no MCP commands required

        # Phase 4: Progress Reporting - should use report_progress() NOT update_job_progress()
        assert "report_progress" in rendered, "Missing report_progress() in Phase 4"
        assert "update_job_progress" not in rendered, "Found obsolete update_job_progress() - should be report_progress()"

        # Phase 5: Communication - should use get_next_instruction() NOT receive_messages()
        assert "get_next_instruction" in rendered, "Missing get_next_instruction() in Phase 5"
        assert "receive_messages" not in rendered, "Found obsolete receive_messages() - should be get_next_instruction()"
        assert "send_message" in rendered, "Missing send_message() in Phase 5"

        # Phase 6: Completion - should have complete_job()
        assert "complete_job" in rendered, "Missing complete_job() in Phase 6"

        # Obsolete commands that should NOT exist
        assert "acknowledge_message" not in rendered, "Found obsolete acknowledge_message() - this function doesn't exist"

    def test_token_count_in_budget(self):
        """Template stays within reasonable token budget (rough estimate: 2-3K tokens)"""
        template = GenericAgentTemplate()
        rendered = template.render(
            agent_id=str(uuid4()),
            job_id=str(uuid4()),
            product_id=str(uuid4()),
            project_id=str(uuid4()),
            tenant_key="test_tenant"
        )

        estimated_tokens = len(rendered) // 4
        # Allow range of 1200-4000 tokens (rough estimate, ~2-3K target)
        assert 1200 < estimated_tokens < 4000, f"Token count {estimated_tokens} outside range"

    def test_template_properties(self):
        """Template has required properties"""
        template = GenericAgentTemplate()
        assert template.version == "1.0"
        assert template.name == "generic_agent"
        assert template.mode == "generic_legacy"


@pytest.mark.asyncio
class TestGenericAgentTemplateMCPTool:
    """Test MCP tool integration."""

    @pytest.fixture
    def test_tenant(self):
        """Generate test tenant key"""
        return f"test-tenant-{uuid4()}"

    async def test_mcp_tool_exists(self, db_session, test_tenant):
        """MCP tool function exists in standalone functions section"""
        from src.giljo_mcp.tools.orchestration import get_generic_agent_template

        assert callable(get_generic_agent_template)

    async def test_mcp_tool_returns_success(self, db_session, test_tenant):
        """MCP tool returns success response"""
        from src.giljo_mcp.tools.orchestration import get_generic_agent_template

        result = await get_generic_agent_template(
            session=db_session,
            agent_id=str(uuid4()),
            job_id=str(uuid4()),
            product_id=str(uuid4()),
            project_id=str(uuid4()),
            tenant_key=test_tenant
        )

        assert result["success"] is True
        assert "template" in result
        assert "variables_injected" in result
        assert "protocol_version" in result
        assert "estimated_tokens" in result

    async def test_variables_injected_match_input(self, db_session, test_tenant):
        """Variables in response match input parameters"""
        from src.giljo_mcp.tools.orchestration import get_generic_agent_template

        agent_id = str(uuid4())
        job_id = str(uuid4())
        product_id = str(uuid4())
        project_id = str(uuid4())

        result = await get_generic_agent_template(
            session=db_session,
            agent_id=agent_id,
            job_id=job_id,
            product_id=product_id,
            project_id=project_id,
            tenant_key=test_tenant
        )

        assert result["variables_injected"]["agent_id"] == agent_id
        assert result["variables_injected"]["job_id"] == job_id
        assert result["variables_injected"]["product_id"] == product_id
        assert result["variables_injected"]["project_id"] == project_id
        assert result["variables_injected"]["tenant_key"] == test_tenant

    async def test_works_for_multiple_agent_types(self, db_session, test_tenant):
        """Same template works for all agent types"""
        from src.giljo_mcp.tools.orchestration import get_generic_agent_template

        agent_types = ["implementer", "tester", "reviewer", "documenter", "analyzer"]

        for agent_type in agent_types:
            result = await get_generic_agent_template(
                session=db_session,
                agent_id=f"{agent_type}-{str(uuid4())}",
                job_id=str(uuid4()),
                product_id=str(uuid4()),
                project_id=str(uuid4()),
                tenant_key=test_tenant
            )

            assert result["success"] is True, f"Failed for {agent_type}"
            assert len(result["template"]) > 0
