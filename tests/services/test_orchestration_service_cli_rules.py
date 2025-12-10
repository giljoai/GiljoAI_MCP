"""
Tests for CLI mode rules in get_orchestrator_instructions (Handover 0335).

Test BEHAVIOR:
- CLI mode response includes cli_mode_rules object
- CLI mode response includes spawning_examples
- Multi-terminal mode response does NOT include cli_mode_rules
- cli_mode_rules contains required fields

TDD Phase: RED - These tests should FAIL initially.
"""
import uuid

import pytest

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models import AgentTemplate, MCPAgentJob, Product, Project


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

            # Create project
            project = Project(
                tenant_key=tenant_key,
                product_id=product.id,
                name="Test Project for CLI Rules",
                description="Project for testing CLI mode rules",
                mission="Test mission for CLI mode validation",
                status="active",
            )
            session.add(project)
            await session.flush()

            # Create CLI mode orchestrator job
            orchestrator_id = str(uuid.uuid4())
            orchestrator = MCPAgentJob(
                job_id=orchestrator_id,
                tenant_key=tenant_key,
                project_id=project.id,
                agent_type="orchestrator",
                agent_name="CLI Mode Orchestrator",
                mission="CLI mode orchestrator mission for testing",
                status="waiting",
                context_budget=150000,
                job_metadata={
                    "execution_mode": "claude_code_cli",  # CLI mode enabled
                    "field_priorities": {},
                    "depth_config": {},
                },
            )
            session.add(orchestrator)

            # Create agent template (for allowed_agent_types query)
            template = AgentTemplate(
                tenant_key=tenant_key,
                name="implementer",
                role="implementer",
                description="Implementation specialist",
                template_content="# Implementer\nAn implementation specialist agent.",  # Required field
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
            )
            session.add(project)
            await session.flush()

            # Create multi-terminal mode orchestrator job
            orchestrator_id = str(uuid.uuid4())
            orchestrator = MCPAgentJob(
                job_id=orchestrator_id,
                tenant_key=tenant_key,
                project_id=project.id,
                agent_type="orchestrator",
                agent_name="Multi-Terminal Orchestrator",
                mission="Multi-terminal orchestrator mission for testing",
                status="waiting",
                context_budget=150000,
                job_metadata={
                    "execution_mode": "multi_terminal",  # Multi-terminal mode (default)
                    "field_priorities": {},
                    "depth_config": {},
                },
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
        contains a cli_mode_rules dict with agent_type/agent_name usage instructions.
        """
        from giljo_mcp.tenant import TenantManager
        from giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        result = await tool_accessor.get_orchestrator_instructions(
            orchestrator_id=cli_mode_context["orchestrator_id"],
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
        - agent_type_usage: Instructions for agent_type parameter
        - agent_name_usage: Instructions for agent_name parameter
        - task_tool_mapping: How Task tool maps to templates
        - validation: "soft" (warn but don't block)
        - template_locations: Where to find templates
        """
        from giljo_mcp.tenant import TenantManager
        from giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        result = await tool_accessor.get_orchestrator_instructions(
            orchestrator_id=cli_mode_context["orchestrator_id"],
            tenant_key=cli_mode_context["tenant_key"],
        )

        assert "cli_mode_rules" in result
        cli_rules = result["cli_mode_rules"]

        # Required fields per Handover 0335
        required_fields = [
            "agent_type_usage",
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

        spawning_examples shows correct usage of agent_type vs agent_name.
        """
        from giljo_mcp.tenant import TenantManager
        from giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        result = await tool_accessor.get_orchestrator_instructions(
            orchestrator_id=cli_mode_context["orchestrator_id"],
            tenant_key=cli_mode_context["tenant_key"],
        )

        assert "error" not in result

        # BEHAVIOR: CLI mode includes spawning examples
        assert "spawning_examples" in result, "CLI mode response should include spawning_examples"

        examples = result["spawning_examples"]
        assert isinstance(examples, list), "spawning_examples should be a list"
        assert len(examples) >= 1, "spawning_examples should have at least one example"

        # Verify example structure
        example = examples[0]
        assert "scenario" in example, "Example should have scenario"
        assert "calls" in example, "Example should have calls"

    async def test_multi_terminal_mode_excludes_cli_mode_rules(
        self,
        db_manager: DatabaseManager,
        multi_terminal_context: dict,
    ):
        """
        Multi-terminal mode response does NOT include cli_mode_rules.

        cli_mode_rules is CLI-specific and should not appear in multi-terminal mode.
        """
        from giljo_mcp.tenant import TenantManager
        from giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        result = await tool_accessor.get_orchestrator_instructions(
            orchestrator_id=multi_terminal_context["orchestrator_id"],
            tenant_key=multi_terminal_context["tenant_key"],
        )

        assert "error" not in result, f"Unexpected error: {result.get('message')}"

        # BEHAVIOR: Multi-terminal mode does NOT include cli_mode_rules
        assert "cli_mode_rules" not in result, "Multi-terminal mode should NOT include cli_mode_rules"
        assert "spawning_examples" not in result, "Multi-terminal mode should NOT include spawning_examples"

    async def test_cli_mode_rules_agent_type_usage_mentions_template_name(
        self,
        db_manager: DatabaseManager,
        cli_mode_context: dict,
    ):
        """
        agent_type_usage explains that agent_type must match template name.
        """
        from giljo_mcp.tenant import TenantManager
        from giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        result = await tool_accessor.get_orchestrator_instructions(
            orchestrator_id=cli_mode_context["orchestrator_id"],
            tenant_key=cli_mode_context["tenant_key"],
        )

        cli_rules = result.get("cli_mode_rules", {})
        agent_type_usage = cli_rules.get("agent_type_usage", "")

        # Should mention template name requirement
        assert "template" in agent_type_usage.lower(), "agent_type_usage should mention template"
        assert "exact" in agent_type_usage.lower() or "match" in agent_type_usage.lower(), \
            "agent_type_usage should emphasize exact matching"

    async def test_cli_mode_rules_task_tool_mapping_mentions_subagent_type(
        self,
        db_manager: DatabaseManager,
        cli_mode_context: dict,
    ):
        """
        task_tool_mapping explains the Task(subagent_type=X) pattern.
        """
        from giljo_mcp.tenant import TenantManager
        from giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        result = await tool_accessor.get_orchestrator_instructions(
            orchestrator_id=cli_mode_context["orchestrator_id"],
            tenant_key=cli_mode_context["tenant_key"],
        )

        cli_rules = result.get("cli_mode_rules", {})
        task_mapping = cli_rules.get("task_tool_mapping", "")

        # Should mention subagent_type
        assert "subagent_type" in task_mapping or "Task" in task_mapping, \
            "task_tool_mapping should mention Task tool or subagent_type"

    async def test_cli_mode_rules_contains_new_fields(
        self,
        db_manager: DatabaseManager,
        cli_mode_context: dict,
    ):
        """
        Verify cli_mode_rules contains new fields from Handover 0336.

        New fields:
        - agent_type_is_truth: Dict with SSOT explanation
        - forbidden_patterns: List of forbidden pattern dicts
        - lifecycle_flow: List of 4-phase lifecycle dicts
        """
        from giljo_mcp.tenant import TenantManager
        from giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        result = await tool_accessor.get_orchestrator_instructions(
            orchestrator_id=cli_mode_context["orchestrator_id"],
            tenant_key=cli_mode_context["tenant_key"],
        )

        assert "cli_mode_rules" in result
        cli_rules = result["cli_mode_rules"]

        # New fields from Handover 0336
        new_fields = [
            "agent_type_is_truth",
            "forbidden_patterns",
            "lifecycle_flow",
        ]

        for field in new_fields:
            assert field in cli_rules, f"cli_mode_rules missing new field: {field}"

        # Verify field types
        assert isinstance(cli_rules["agent_type_is_truth"], dict), \
            "agent_type_is_truth should be a dict"
        assert isinstance(cli_rules["forbidden_patterns"], list), \
            "forbidden_patterns should be a list"
        assert isinstance(cli_rules["lifecycle_flow"], list), \
            "lifecycle_flow should be a list"

    async def test_cli_mode_rules_agent_type_is_truth_structure(
        self,
        db_manager: DatabaseManager,
        cli_mode_context: dict,
    ):
        """
        Verify agent_type_is_truth field contains required sub-fields.
        """
        from giljo_mcp.tenant import TenantManager
        from giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        result = await tool_accessor.get_orchestrator_instructions(
            orchestrator_id=cli_mode_context["orchestrator_id"],
            tenant_key=cli_mode_context["tenant_key"],
        )

        cli_rules = result.get("cli_mode_rules", {})
        agent_type_is_truth = cli_rules.get("agent_type_is_truth", {})

        # Should have required sub-fields
        required_sub_fields = ["statement", "usage", "agent_name_purpose"]
        for field in required_sub_fields:
            assert field in agent_type_is_truth, \
                f"agent_type_is_truth missing sub-field: {field}"

        # Verify statement content
        statement = agent_type_is_truth["statement"]
        assert "SINGLE SOURCE OF TRUTH" in statement, \
            "statement should mention 'SINGLE SOURCE OF TRUTH'"

    async def test_cli_mode_rules_forbidden_patterns_structure(
        self,
        db_manager: DatabaseManager,
        cli_mode_context: dict,
    ):
        """
        Verify forbidden_patterns contains list of pattern dicts.
        """
        from giljo_mcp.tenant import TenantManager
        from giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        result = await tool_accessor.get_orchestrator_instructions(
            orchestrator_id=cli_mode_context["orchestrator_id"],
            tenant_key=cli_mode_context["tenant_key"],
        )

        cli_rules = result.get("cli_mode_rules", {})
        forbidden_patterns = cli_rules.get("forbidden_patterns", [])

        # Should have at least 5 forbidden patterns
        assert len(forbidden_patterns) >= 5, \
            f"forbidden_patterns should have at least 5 patterns, found {len(forbidden_patterns)}"

        # Each pattern should have pattern and reason
        for pattern_obj in forbidden_patterns:
            assert "pattern" in pattern_obj, "Forbidden pattern missing 'pattern' field"
            assert "reason" in pattern_obj, "Forbidden pattern missing 'reason' field"

    async def test_cli_mode_rules_lifecycle_flow_structure(
        self,
        db_manager: DatabaseManager,
        cli_mode_context: dict,
    ):
        """
        Verify lifecycle_flow contains 4-phase lifecycle table.
        """
        from giljo_mcp.tenant import TenantManager
        from giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        result = await tool_accessor.get_orchestrator_instructions(
            orchestrator_id=cli_mode_context["orchestrator_id"],
            tenant_key=cli_mode_context["tenant_key"],
        )

        cli_rules = result.get("cli_mode_rules", {})
        lifecycle_flow = cli_rules.get("lifecycle_flow", [])

        # Should have exactly 4 phases
        assert len(lifecycle_flow) == 4, \
            f"lifecycle_flow should have exactly 4 phases, found {len(lifecycle_flow)}"

        # Each phase should have required fields
        required_phase_fields = ["phase", "name", "operation", "param"]
        for phase_obj in lifecycle_flow:
            for field in required_phase_fields:
                assert field in phase_obj, \
                    f"Lifecycle phase missing field: {field}"

        # Verify phase numbers are 1-4
        phase_numbers = [phase["phase"] for phase in lifecycle_flow]
        assert phase_numbers == [1, 2, 3, 4], \
            f"Lifecycle phases should be numbered 1-4, got {phase_numbers}"


@pytest.mark.asyncio
class TestCLIModeRulesBackwardCompatibility:
    """Verify CLI mode rules don't break existing functionality."""

    @pytest.fixture
    async def cli_mode_context(self, db_manager: DatabaseManager):
        """Create CLI mode orchestrator context using db_manager directly."""
        tenant_key = f"test_tenant_{uuid.uuid4().hex[:8]}"

        async with db_manager.get_session_async() as session:
            # Create product
            product = Product(
                tenant_key=tenant_key,
                name="Test Product for Backward Compat",
                description="Product for backward compatibility tests",
                is_active=True,  # Product uses is_active, not status
            )
            session.add(product)
            await session.flush()

            # Create project
            project = Project(
                tenant_key=tenant_key,
                product_id=product.id,
                name="Test Project for Backward Compat",
                description="Project for backward compatibility tests",
                mission="Test mission for backward compatibility",
                status="active",
            )
            session.add(project)
            await session.flush()

            # Create CLI mode orchestrator job
            orchestrator_id = str(uuid.uuid4())
            orchestrator = MCPAgentJob(
                job_id=orchestrator_id,
                tenant_key=tenant_key,
                project_id=project.id,
                agent_type="orchestrator",
                agent_name="CLI Mode Orchestrator",
                mission="CLI mode orchestrator mission",
                status="waiting",
                context_budget=150000,
                job_metadata={
                    "execution_mode": "claude_code_cli",
                    "field_priorities": {},
                    "depth_config": {},
                },
            )
            session.add(orchestrator)

            # Create agent template
            template = AgentTemplate(
                tenant_key=tenant_key,
                name="analyzer",
                role="analyzer",
                description="Analysis specialist",
                template_content="# Analyzer\nAn analysis specialist agent.",  # Required field
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

    async def test_existing_agent_spawning_constraint_preserved(
        self,
        db_manager: DatabaseManager,
        cli_mode_context: dict,
    ):
        """
        Existing agent_spawning_constraint from Handover 0260 should still be present.

        cli_mode_rules supplements (not replaces) agent_spawning_constraint.
        """
        from giljo_mcp.tenant import TenantManager
        from giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        result = await tool_accessor.get_orchestrator_instructions(
            orchestrator_id=cli_mode_context["orchestrator_id"],
            tenant_key=cli_mode_context["tenant_key"],
        )

        # Both should be present for CLI mode
        assert "agent_spawning_constraint" in result, \
            "CLI mode should still include agent_spawning_constraint (Handover 0260)"
        assert "cli_mode_rules" in result, \
            "CLI mode should also include cli_mode_rules (Handover 0335)"

    async def test_core_response_fields_unchanged(
        self,
        db_manager: DatabaseManager,
        cli_mode_context: dict,
    ):
        """
        Core response fields should remain unchanged regardless of mode.
        """
        from giljo_mcp.tenant import TenantManager
        from giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        result = await tool_accessor.get_orchestrator_instructions(
            orchestrator_id=cli_mode_context["orchestrator_id"],
            tenant_key=cli_mode_context["tenant_key"],
        )

        # Core fields should always be present
        core_fields = [
            "orchestrator_id",
            "project_id",
            "project_name",
            "project_description",
            "mission",
            "context_budget",
            "context_used",
            "agent_discovery_tool",
            "thin_client",
        ]

        for field in core_fields:
            assert field in result, f"Core field '{field}' should be present"
