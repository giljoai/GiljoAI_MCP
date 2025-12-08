"""
Tests for CLI mode validation section in staging prompt (Handover 0335).

Test BEHAVIOR:
- CLI mode staging prompt includes agent spawning rules table
- CLI mode staging prompt includes Task tool mapping explanation
- CLI mode staging prompt includes template validation section
- CLI mode staging prompt includes resolution priority
- CLI mode staging prompt includes soft validation guidance
- Multi-terminal mode staging prompt does NOT include CLI validation section

TDD Phase: Test file created to verify Task 2 implementation.
"""
import uuid

import pytest

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models import Product, Project
from giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator


@pytest.mark.asyncio
class TestCLIValidationSection:
    """Test suite for CLI validation section in staging prompt (Handover 0335)."""

    async def _generate_staging_prompt(
        self, db_manager: DatabaseManager, tenant_key: str, project_id: str, orchestrator_id: str, claude_code_mode: bool
    ) -> str:
        """Helper to generate staging prompt within a session context."""
        async with db_manager.get_session_async() as session:
            generator = ThinClientPromptGenerator(
                db=session,
                tenant_key=tenant_key,
            )
            return await generator.generate_staging_prompt(
                orchestrator_id=orchestrator_id,
                project_id=project_id,
                claude_code_mode=claude_code_mode,
            )

    @pytest.fixture
    async def staging_context(self, db_manager: DatabaseManager):
        """Create staging context using db_manager directly."""
        tenant_key = f"test_tenant_{uuid.uuid4().hex[:8]}"

        async with db_manager.get_session_async() as session:
            # Create product
            product = Product(
                tenant_key=tenant_key,
                name="Test Product for CLI Validation",
                description="Product for testing CLI validation section",
                is_active=True,
            )
            session.add(product)
            await session.flush()

            # Create project
            project = Project(
                tenant_key=tenant_key,
                product_id=product.id,
                name="Test Project for CLI Validation",
                description="Project for testing CLI validation section",
                mission="Test mission for CLI validation",
                status="active",
            )
            session.add(project)
            await session.flush()

            orchestrator_id = str(uuid.uuid4())

            await session.commit()

            yield {
                "tenant_key": tenant_key,
                "orchestrator_id": orchestrator_id,
                "project_id": str(project.id),
                "product_id": str(product.id),
            }

    async def test_cli_mode_prompt_includes_spawning_rules_table(
        self,
        db_manager: DatabaseManager,
        staging_context: dict,
    ):
        """
        CLI mode staging prompt includes agent spawning rules table.

        The table explains agent_type vs agent_name distinction.
        """
        prompt = await self._generate_staging_prompt(
            db_manager=db_manager,
            tenant_key=staging_context["tenant_key"],
            project_id=staging_context["project_id"],
            orchestrator_id=staging_context["orchestrator_id"],
            claude_code_mode=True,
        )

        # Should contain the spawning rules table with key columns
        assert "| Parameter" in prompt, "Should include parameter table header"
        assert "agent_type" in prompt, "Should mention agent_type parameter"
        assert "agent_name" in prompt, "Should mention agent_name parameter"
        assert "Template name" in prompt or "template" in prompt.lower(), "Should explain template name purpose"

    async def test_cli_mode_prompt_includes_task_tool_mapping(
        self,
        db_manager: DatabaseManager,
        staging_context: dict,
    ):
        """
        CLI mode staging prompt explains Task(subagent_type=X) pattern.
        """
        prompt = await self._generate_staging_prompt(
            db_manager=db_manager,
            tenant_key=staging_context["tenant_key"],
            project_id=staging_context["project_id"],
            orchestrator_id=staging_context["orchestrator_id"],
            claude_code_mode=True,
        )

        # Should explain the Task tool mapping
        assert "Task" in prompt, "Should mention Task tool"
        assert "subagent_type" in prompt, "Should mention subagent_type parameter"

    async def test_cli_mode_prompt_includes_template_validation_section(
        self,
        db_manager: DatabaseManager,
        staging_context: dict,
    ):
        """
        CLI mode staging prompt includes template validation section.
        """
        prompt = await self._generate_staging_prompt(
            db_manager=db_manager,
            tenant_key=staging_context["tenant_key"],
            project_id=staging_context["project_id"],
            orchestrator_id=staging_context["orchestrator_id"],
            claude_code_mode=True,
        )

        # Should include template validation header
        assert "TEMPLATE VALIDATION" in prompt or "Template Validation" in prompt.lower(), \
            "Should include template validation section"

    async def test_cli_mode_prompt_includes_resolution_priority(
        self,
        db_manager: DatabaseManager,
        staging_context: dict,
    ):
        """
        CLI mode staging prompt includes resolution priority (project → user → built-in).
        """
        prompt = await self._generate_staging_prompt(
            db_manager=db_manager,
            tenant_key=staging_context["tenant_key"],
            project_id=staging_context["project_id"],
            orchestrator_id=staging_context["orchestrator_id"],
            claude_code_mode=True,
        )

        # Should explain template resolution priority
        assert "Resolution Priority" in prompt or "priority" in prompt.lower(), \
            "Should explain resolution priority"
        assert ".claude/agents/" in prompt, "Should mention .claude/agents/ path"
        assert "project" in prompt.lower(), "Should mention project-level templates"

    async def test_cli_mode_prompt_includes_soft_validation_guidance(
        self,
        db_manager: DatabaseManager,
        staging_context: dict,
    ):
        """
        CLI mode staging prompt includes soft validation guidance (warn but proceed).
        """
        prompt = await self._generate_staging_prompt(
            db_manager=db_manager,
            tenant_key=staging_context["tenant_key"],
            project_id=staging_context["project_id"],
            orchestrator_id=staging_context["orchestrator_id"],
            claude_code_mode=True,
        )

        # Should explain soft validation approach
        assert "WARN" in prompt or "warn" in prompt.lower(), "Should mention warning"
        assert "PROCEED" in prompt or "proceed" in prompt.lower(), "Should mention proceeding anyway"

    async def test_multi_terminal_mode_excludes_cli_validation(
        self,
        db_manager: DatabaseManager,
        staging_context: dict,
    ):
        """
        Multi-terminal mode staging prompt does NOT include CLI validation section.
        """
        prompt = await self._generate_staging_prompt(
            db_manager=db_manager,
            tenant_key=staging_context["tenant_key"],
            project_id=staging_context["project_id"],
            orchestrator_id=staging_context["orchestrator_id"],
            claude_code_mode=False,  # Multi-terminal mode
        )

        # Should NOT include CLI-specific validation content
        assert "AGENT SPAWNING RULES" not in prompt, \
            "Multi-terminal mode should NOT include CLI spawning rules section"
        assert "AGENT TEMPLATE VALIDATION" not in prompt, \
            "Multi-terminal mode should NOT include CLI template validation section"
        assert "Resolution Priority" not in prompt, \
            "Multi-terminal mode should NOT include resolution priority"

    async def test_cli_mode_prompt_includes_example_spawn_calls(
        self,
        db_manager: DatabaseManager,
        staging_context: dict,
    ):
        """
        CLI mode staging prompt includes example spawn_agent_job calls.
        """
        prompt = await self._generate_staging_prompt(
            db_manager=db_manager,
            tenant_key=staging_context["tenant_key"],
            project_id=staging_context["project_id"],
            orchestrator_id=staging_context["orchestrator_id"],
            claude_code_mode=True,
        )

        # Should include spawn example
        assert "spawn_agent_job" in prompt, "Should include spawn_agent_job example"
        assert "implementer" in prompt.lower(), "Should include implementer as example agent_type"

    async def test_cli_mode_prompt_explains_file_not_found_risk(
        self,
        db_manager: DatabaseManager,
        staging_context: dict,
    ):
        """
        CLI mode staging prompt explains FILE NOT FOUND risk for wrong agent_type.
        """
        prompt = await self._generate_staging_prompt(
            db_manager=db_manager,
            tenant_key=staging_context["tenant_key"],
            project_id=staging_context["project_id"],
            orchestrator_id=staging_context["orchestrator_id"],
            claude_code_mode=True,
        )

        # Should explain the FILE NOT FOUND risk
        assert "FILE NOT FOUND" in prompt or "not found" in prompt.lower(), \
            "Should explain FILE NOT FOUND risk for wrong agent_type"
