"""
Tests for extended CLI mode rule fields and backward compatibility (Handover 0335/0336).

Test BEHAVIOR:
- cli_mode_rules extended fields (new fields, UI label structure, forbidden patterns, lifecycle flow)
- Backward compatibility: existing functionality preserved with CLI mode rules

Split from test_orchestration_service_cli_rules.py -- extended fields and backward compat tests.
"""

import random
import uuid

import pytest

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import AgentExecution, AgentJob, AgentTemplate, Product, Project


@pytest.mark.asyncio
class TestCLIModeRulesExtendedFields:
    """Tests for extended CLI mode rule fields from Handover 0336.

    NOTE: All tests in this class are skipped because the fields were never implemented
    or were replaced by different structures.
    """

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
                    "field_priorities": {},
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

    @pytest.mark.skip(reason="Fields agent_display_name_is_ui_label, forbidden_patterns, lifecycle_flow don't exist")
    async def test_cli_mode_rules_contains_new_fields(
        self,
        db_manager: DatabaseManager,
        cli_mode_context: dict,
    ):
        """
        Verify cli_mode_rules contains new fields from Handover 0336.

        New fields:
        - agent_display_name_is_ui_label: Dict with SSOT explanation
        - forbidden_patterns: List of forbidden pattern dicts
        - lifecycle_flow: List of 4-phase lifecycle dicts
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

        # New fields from Handover 0336
        new_fields = [
            "agent_display_name_is_ui_label",
            "forbidden_patterns",
            "lifecycle_flow",
        ]

        for field in new_fields:
            assert field in cli_rules, f"cli_mode_rules missing new field: {field}"

        # Verify field types
        assert isinstance(cli_rules["agent_display_name_is_ui_label"], dict), (
            "agent_display_name_is_ui_label should be a dict"
        )
        assert isinstance(cli_rules["forbidden_patterns"], list), "forbidden_patterns should be a list"
        assert isinstance(cli_rules["lifecycle_flow"], list), "lifecycle_flow should be a list"

    @pytest.mark.skip(
        reason="Field agent_display_name_is_ui_label doesn't exist - replaced with agent_display_name_usage"
    )
    async def test_cli_mode_rules_agent_display_name_is_ui_label_structure(
        self,
        db_manager: DatabaseManager,
        cli_mode_context: dict,
    ):
        """
        Verify agent_display_name_is_ui_label field contains required sub-fields.
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
        agent_display_name_is_ui_label = cli_rules.get("agent_display_name_is_ui_label", {})

        # Should have required sub-fields
        required_sub_fields = ["statement", "usage", "agent_name_purpose"]
        for field in required_sub_fields:
            assert field in agent_display_name_is_ui_label, f"agent_display_name_is_ui_label missing sub-field: {field}"

        # Verify statement content
        statement = agent_display_name_is_ui_label["statement"]
        assert "SINGLE SOURCE OF TRUTH" in statement, "statement should mention 'SINGLE SOURCE OF TRUTH'"

    @pytest.mark.skip(reason="forbidden_patterns field was never implemented")
    async def test_cli_mode_rules_forbidden_patterns_structure(
        self,
        db_manager: DatabaseManager,
        cli_mode_context: dict,
    ):
        """
        Verify forbidden_patterns contains list of pattern dicts.
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
        forbidden_patterns = cli_rules.get("forbidden_patterns", [])

        # Should have at least 5 forbidden patterns
        assert len(forbidden_patterns) >= 5, (
            f"forbidden_patterns should have at least 5 patterns, found {len(forbidden_patterns)}"
        )

        # Each pattern should have pattern and reason
        for pattern_obj in forbidden_patterns:
            assert "pattern" in pattern_obj, "Forbidden pattern missing 'pattern' field"
            assert "reason" in pattern_obj, "Forbidden pattern missing 'reason' field"

    @pytest.mark.skip(reason="lifecycle_flow field was never implemented")
    async def test_cli_mode_rules_lifecycle_flow_structure(
        self,
        db_manager: DatabaseManager,
        cli_mode_context: dict,
    ):
        """
        Verify lifecycle_flow contains 4-phase lifecycle table.
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
        lifecycle_flow = cli_rules.get("lifecycle_flow", [])

        # Should have exactly 4 phases
        assert len(lifecycle_flow) == 4, f"lifecycle_flow should have exactly 4 phases, found {len(lifecycle_flow)}"

        # Each phase should have required fields
        required_phase_fields = ["phase", "name", "operation", "param"]
        for phase_obj in lifecycle_flow:
            for field in required_phase_fields:
                assert field in phase_obj, f"Lifecycle phase missing field: {field}"

        # Verify phase numbers are 1-4
        phase_numbers = [phase["phase"] for phase in lifecycle_flow]
        assert phase_numbers == [1, 2, 3, 4], f"Lifecycle phases should be numbered 1-4, got {phase_numbers}"


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
                    "field_priorities": {},
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

            # Create agent template
            template = AgentTemplate(
                tenant_key=tenant_key,
                name="analyzer",
                role="analyzer",
                description="Analysis specialist",
                system_instructions="# Analyzer\nAn analysis specialist agent.",  # Required field
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

    @pytest.mark.skip(reason="agent_spawning_constraint removed — contradicted staging phase, Task tool instructions now in thin_prompt_generator")
    async def test_existing_agent_spawning_constraint_preserved(
        self,
        db_manager: DatabaseManager,
        cli_mode_context: dict,
    ):
        """
        OBSOLETE: agent_spawning_constraint removed from staging response.

        It contradicted CH1/CH3 ("do NOT call Task() during staging").
        Task tool instructions now live in thin_prompt_generator's
        _build_claude_code_execution_prompt() for implementation phase.
        cli_mode_rules remains (multi_agent_example, display_name_usage are useful during staging).
        """
        pass

    @pytest.mark.skip(reason="Field structure changed in implementation")
    async def test_core_response_fields_unchanged(
        self,
        db_manager: DatabaseManager,
        cli_mode_context: dict,
    ):
        """
        Core response fields should remain unchanged regardless of mode.
        """
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        result = await tool_accessor.get_orchestrator_instructions(
            job_id=cli_mode_context["orchestrator_id"],
            tenant_key=cli_mode_context["tenant_key"],
        )

        # Core fields should always be present
        core_fields = [
            "orchestrator_id",
            "project_id",
            "project_name",
            "project_description",
            "mission",
            "agent_discovery_tool",
            "thin_client",
        ]

        for field in core_fields:
            assert field in result, f"Core field '{field}' should be present"
