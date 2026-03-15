"""
Tests for CLI mode rules in get_orchestrator_instructions (Handover 0335).

Test BEHAVIOR:
- CLI mode response includes cli_mode_rules object
- CLI mode response includes spawning_examples
- Multi-terminal mode response does NOT include cli_mode_rules
- cli_mode_rules contains required fields

Split from test_orchestration_service_cli_rules.py -- core CLI mode rule tests.
"""

import random
import uuid

import pytest

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import AgentExecution, AgentJob, AgentTemplate, Product, Project


@pytest.mark.asyncio
class TestCLIModeRules:
    """Test suite for CLI mode rules in get_orchestrator_instructions (Handover 0335)."""

    @pytest.fixture
    async def cli_mode_context(self, db_manager: DatabaseManager):
        """Create CLI mode orchestrator context using db_manager directly.

        This pattern follows test_mcp_get_orchestrator_instructions.py for
        proper session handling with db_manager-based functions.
        """
        tenant_key = f"test_tenant_{uuid.uuid4().hex[:8]}"

        async with db_manager.get_session_async() as session:
            # Create product
            product = Product(
                tenant_key=tenant_key,
                name="Test Product for CLI Rules",
                description="Product for testing CLI mode rules",
                is_active=True,  # Product uses is_active, not status
            )
            session.add(product)
            await session.flush()

            # Create project with CLI mode execution
            project = Project(
                tenant_key=tenant_key,
                product_id=product.id,
                name="Test Project for CLI Rules",
                description="Project for testing CLI mode rules",
                mission="Test mission for CLI mode validation",
                status="active",
                execution_mode="claude_code_cli",  # Required for cli_mode_rules to be included
                series_number=random.randint(1, 999999),
            )
            session.add(project)
            await session.flush()

            # Create CLI mode orchestrator job
            orchestrator_id = str(uuid.uuid4())

            # Create AgentJob first (required for FK constraint)
            job = AgentJob(
                job_id=orchestrator_id,
                tenant_key=tenant_key,
                project_id=str(project.id),
                mission="CLI mode orchestrator mission for testing",
                job_type="orchestrator",
                status="active",
                job_metadata={
                    "execution_mode": "claude_code_cli",
                    "field_toggles": {},
                    "depth_config": {},
                },
            )
            session.add(job)
            await session.flush()

            # Create AgentExecution
            orchestrator = AgentExecution(
                job_id=orchestrator_id,
                tenant_key=tenant_key,
                agent_display_name="orchestrator",
                agent_name="CLI Mode Orchestrator",
                status="waiting",
            )
            session.add(orchestrator)

            # Create agent template (for allowed_agent_display_names query)
            template = AgentTemplate(
                tenant_key=tenant_key,
                name="implementer",
                role="implementer",
                description="Implementation specialist",
                system_instructions="# Implementer\nAn implementation specialist agent.",  # Required field
                is_active=True,
            )
            session.add(template)

            await session.commit()

            yield {
                "tenant_key": tenant_key,
                "orchestrator_id": orchestrator_id,
                "project_id": str(project.id),
                "product_id": str(product.id),
            }

            # Cleanup handled by test isolation

    @pytest.fixture
    async def multi_terminal_context(self, db_manager: DatabaseManager):
        """Create multi-terminal mode orchestrator context."""
        tenant_key = f"test_tenant_{uuid.uuid4().hex[:8]}"

        async with db_manager.get_session_async() as session:
            # Create product
            product = Product(
                tenant_key=tenant_key,
                name="Test Product for Multi-Terminal",
                description="Product for testing multi-terminal mode",
                is_active=True,  # Product uses is_active, not status
            )
            session.add(product)
            await session.flush()

            # Create project
            project = Project(
                tenant_key=tenant_key,
                product_id=product.id,
                name="Test Project for Multi-Terminal",
                description="Project for testing multi-terminal mode",
                mission="Test mission for multi-terminal mode",
                status="active",
                series_number=random.randint(1, 999999),
            )
            session.add(project)
            await session.flush()

            # Create multi-terminal mode orchestrator job
            orchestrator_id = str(uuid.uuid4())

            # Create AgentJob first (required for FK constraint)
            job = AgentJob(
                job_id=orchestrator_id,
                tenant_key=tenant_key,
                project_id=str(project.id),
                mission="Multi-terminal orchestrator mission for testing",
                job_type="orchestrator",
                status="active",
                job_metadata={
                    "execution_mode": "multi_terminal",
                    "field_toggles": {},
                    "depth_config": {},
                },
            )
            session.add(job)
            await session.flush()

            # Create AgentExecution
            orchestrator = AgentExecution(
                job_id=orchestrator_id,
                tenant_key=tenant_key,
                agent_display_name="orchestrator",
                agent_name="Multi-Terminal Orchestrator",
                status="waiting",
            )
            session.add(orchestrator)

            await session.commit()

            yield {
                "tenant_key": tenant_key,
                "orchestrator_id": orchestrator_id,
                "project_id": str(project.id),
                "product_id": str(product.id),
            }

    async def test_cli_mode_response_includes_cli_mode_rules(
        self,
        db_manager: DatabaseManager,
        cli_mode_context: dict,
    ):
        """
        CLI mode response includes cli_mode_rules object.

        Verifies that when execution_mode == 'claude_code_cli', the response
        contains a cli_mode_rules dict with agent_display_name/agent_name usage instructions.
        """
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        result = await tool_accessor.get_orchestrator_instructions(
            job_id=cli_mode_context["orchestrator_id"],
            tenant_key=cli_mode_context["tenant_key"],
        )

        # Should not have error
        assert "error" not in result, f"Unexpected error: {result.get('message')}"

        # BEHAVIOR: CLI mode response includes cli_mode_rules
        assert "cli_mode_rules" in result, "CLI mode response should include cli_mode_rules"

        cli_rules = result["cli_mode_rules"]
        assert isinstance(cli_rules, dict), "cli_mode_rules should be a dict"

    async def test_cli_mode_rules_contains_required_fields(
        self,
        db_manager: DatabaseManager,
        cli_mode_context: dict,
    ):
        """
        Verify cli_mode_rules contains all required fields.

        Required fields per Handover 0335:
        - agent_display_name_usage: Instructions for agent_display_name parameter
        - agent_name_usage: Instructions for agent_name parameter
        - task_tool_mapping: How Task tool maps to templates
        - validation: "soft" (warn but don't block)
        - template_locations: Where to find templates
        """
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        result = await tool_accessor.get_orchestrator_instructions(
            job_id=cli_mode_context["orchestrator_id"],
            tenant_key=cli_mode_context["tenant_key"],
        )

        assert "cli_mode_rules" in result
        cli_rules = result["cli_mode_rules"]

        # Required fields per Handover 0335
        required_fields = [
            "agent_display_name_usage",
            "agent_name_usage",
            "task_tool_mapping",
            "validation",
            "template_locations",
        ]

        for field in required_fields:
            assert field in cli_rules, f"cli_mode_rules missing required field: {field}"

        # Verify validation is "soft"
        assert cli_rules["validation"] == "soft", "validation should be 'soft'"

        # Verify template_locations is a list
        assert isinstance(cli_rules["template_locations"], list), "template_locations should be a list"
        assert len(cli_rules["template_locations"]) >= 2, "template_locations should have at least 2 entries"

    async def test_cli_mode_response_includes_spawning_examples(
        self,
        db_manager: DatabaseManager,
        cli_mode_context: dict,
    ):
        """
        CLI mode response includes spawning_examples.

        spawning_examples shows correct usage of agent_display_name vs agent_name.

        NOTE: This feature was redesigned. Spawning examples are now in
        cli_mode_rules.multi_agent_example instead of a top-level spawning_examples field.
        """
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        result = await tool_accessor.get_orchestrator_instructions(
            job_id=cli_mode_context["orchestrator_id"],
            tenant_key=cli_mode_context["tenant_key"],
        )

        assert "error" not in result

        # Check for the new structure instead
        assert "cli_mode_rules" in result
        assert "multi_agent_example" in result["cli_mode_rules"]
        example = result["cli_mode_rules"]["multi_agent_example"]
        assert "scenario" in example
        assert "agent_1" in example
        assert "agent_2" in example

    async def test_multi_terminal_mode_excludes_cli_mode_rules(
        self,
        db_manager: DatabaseManager,
        multi_terminal_context: dict,
    ):
        """
        Multi-terminal mode response does NOT include cli_mode_rules.

        cli_mode_rules is CLI-specific and should not appear in multi-terminal mode.
        """
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        result = await tool_accessor.get_orchestrator_instructions(
            job_id=multi_terminal_context["orchestrator_id"],
            tenant_key=multi_terminal_context["tenant_key"],
        )

        assert "error" not in result, f"Unexpected error: {result.get('message')}"

        # BEHAVIOR: Multi-terminal mode does NOT include cli_mode_rules
        assert "cli_mode_rules" not in result, "Multi-terminal mode should NOT include cli_mode_rules"
        assert "spawning_examples" not in result, "Multi-terminal mode should NOT include spawning_examples"

    async def test_cli_mode_rules_agent_display_name_usage_mentions_template_name(
        self,
        db_manager: DatabaseManager,
        cli_mode_context: dict,
    ):
        """
        agent_display_name_usage explains that agent_display_name is a dashboard label
        and must be unique per agent instance when spawning multiple agents of same template.
        """
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        result = await tool_accessor.get_orchestrator_instructions(
            job_id=cli_mode_context["orchestrator_id"],
            tenant_key=cli_mode_context["tenant_key"],
        )

        cli_rules = result.get("cli_mode_rules", {})
        agent_display_name_usage = cli_rules.get("agent_display_name_usage", "")

        # Should mention template and uniqueness requirement
        assert "template" in agent_display_name_usage.lower(), "agent_display_name_usage should mention template"
        assert "unique" in agent_display_name_usage.lower(), (
            "agent_display_name_usage should emphasize uniqueness per agent instance"
        )

    async def test_cli_mode_rules_task_tool_mapping_mentions_subagent_type(
        self,
        db_manager: DatabaseManager,
        cli_mode_context: dict,
    ):
        """
        task_tool_mapping explains the Task(subagent_type=X) pattern.
        """
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        result = await tool_accessor.get_orchestrator_instructions(
            job_id=cli_mode_context["orchestrator_id"],
            tenant_key=cli_mode_context["tenant_key"],
        )

        cli_rules = result.get("cli_mode_rules", {})
        task_mapping = cli_rules.get("task_tool_mapping", "")

        # Should mention subagent_type
        assert "subagent_type" in task_mapping or "Task" in task_mapping, (
            "task_tool_mapping should mention Task tool or subagent_type"
        )
