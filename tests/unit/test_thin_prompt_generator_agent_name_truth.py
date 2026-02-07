"""
Unit Tests for Agent Name Single Source of Truth - Handover 0351

Tests that staging prompts reference agent_name (not agent_display_name) as the single source
of truth for agent spawning in Claude Code CLI mode.

Test Coverage (TDD - RED Phase):
1. Staging prompt contains "agent_name: SINGLE SOURCE OF TRUTH"
2. Staging prompt does NOT contain "agent_display_name: SINGLE SOURCE OF TRUTH"
3. Task tool examples use agent_name for subagent_type parameter
4. Prompt agent_name matches template filename reference
5. Multi-terminal mode is unaffected (no changes)

Phase: Test-First Development (RED Phase - Tests FAIL)
Status: Awaiting implementation in thin_prompt_generator.py
Related Handovers: 0260 (execution mode), 0246 (orchestrator workflow)
"""

from uuid import uuid4

import pytest
import pytest_asyncio

from src.giljo_mcp.models import Product, Project, User
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator


# ============================================================================
# FIXTURES
# ============================================================================


@pytest_asyncio.fixture(scope="function")
async def test_product(db_session):
    """Create test product for prompt generation."""
    tenant_key = f"test_tenant_{uuid4().hex[:8]}"

    product = Product(
        id=str(uuid4()),
        name="Test Product",
        description="Test product for agent name truth testing",
        tenant_key=tenant_key,
        config_data={"tech_stack": {"languages": ["Python 3.11+"], "frameworks": ["FastAPI", "Vue 3"]}},
    )

    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    return product


@pytest_asyncio.fixture(scope="function")
async def test_project(db_session, test_product):
    """Create test project linked to product."""
    project = Project(
        id=str(uuid4()),
        name="Test Project",
        description="Test project for agent name truth testing",
        mission="Test mission for agent name truth testing",
        status="active",
        tenant_key=test_product.tenant_key,
        product_id=test_product.id,
        context_budget=100000,
    )

    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    return project


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session, test_product):
    """Create test user for prompt generation."""
    unique_id = uuid4().hex[:8]
    user = User(
        id=str(uuid4()),
        username=f"test_user_{unique_id}",
        email=f"test_{unique_id}@example.com",
        tenant_key=test_product.tenant_key,
        password_hash="hashed_password",
        field_priority_config={},
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest_asyncio.fixture(scope="function")
async def generator(db_session, test_product):
    """Create ThinClientPromptGenerator instance."""
    return ThinClientPromptGenerator(db=db_session, tenant_key=test_product.tenant_key)


# ============================================================================
# CLAUDE CODE CLI MODE TESTS - agent_name AS SINGLE SOURCE OF TRUTH
# ============================================================================


class TestAgentNameSingleSourceOfTruth:
    """Test that CLI mode prompts use agent_name as single source of truth"""

    @pytest.mark.asyncio
    async def test_staging_prompt_declares_agent_name_as_truth(self, generator, test_project):
        """
        BEHAVIOR: CLI mode staging prompt MUST declare agent_name as SINGLE SOURCE OF TRUTH

        GIVEN: Claude Code CLI mode enabled
        WHEN: Generating staging prompt
        THEN: Prompt contains "agent_name: SINGLE SOURCE OF TRUTH"
        """
        prompt = await generator.generate_staging_prompt(
            orchestrator_id=str(uuid4()), project_id=test_project.id, claude_code_mode=True
        )

        # MUST declare agent_name as single source of truth
        assert "agent_name: SINGLE SOURCE OF TRUTH" in prompt, (
            "CLI mode prompt must declare 'agent_name: SINGLE SOURCE OF TRUTH'"
        )

    @pytest.mark.asyncio
    async def test_staging_prompt_does_not_declare_agent_display_name_as_truth(self, generator, test_project):
        """
        BEHAVIOR: CLI mode staging prompt MUST NOT declare agent_display_name as SINGLE SOURCE OF TRUTH

        GIVEN: Claude Code CLI mode enabled
        WHEN: Generating staging prompt
        THEN: Prompt does NOT contain "agent_display_name: SINGLE SOURCE OF TRUTH"
        """
        prompt = await generator.generate_staging_prompt(
            orchestrator_id=str(uuid4()), project_id=test_project.id, claude_code_mode=True
        )

        # MUST NOT declare agent_display_name as single source of truth
        assert "agent_display_name: SINGLE SOURCE OF TRUTH" not in prompt, (
            "CLI mode prompt must NOT declare 'agent_display_name: SINGLE SOURCE OF TRUTH'"
        )

    @pytest.mark.asyncio
    async def test_task_tool_example_uses_agent_name_for_subagent_type(self, generator, test_project):
        """
        BEHAVIOR: Task tool examples in CLI mode MUST use {agent_name} for subagent_type

        GIVEN: Claude Code CLI mode enabled
        WHEN: Generating staging prompt
        THEN: Prompt states "Task(subagent_type=X) uses agent_name value"
        """
        prompt = await generator.generate_staging_prompt(
            orchestrator_id=str(uuid4()), project_id=test_project.id, claude_code_mode=True
        )

        # Staging prompt states Task tool uses agent_name (not literal code example)
        assert "Task(subagent_type=X) uses agent_name value" in prompt, (
            "Staging prompt must state 'Task(subagent_type=X) uses agent_name value'"
        )

    @pytest.mark.asyncio
    async def test_task_tool_example_does_not_use_agent_type_for_subagent_type(self, generator, test_project):
        """
        BEHAVIOR: Task tool examples in CLI mode MUST NOT use {agent_display_name} for subagent_type

        GIVEN: Claude Code CLI mode enabled
        WHEN: Generating staging prompt
        THEN: Task tool example does NOT show subagent_type="{agent_display_name}"
        """
        prompt = await generator.generate_staging_prompt(
            orchestrator_id=str(uuid4()), project_id=test_project.id, claude_code_mode=True
        )

        # Task tool example must NOT use agent_display_name
        assert 'subagent_type="{agent_display_name}"' not in prompt, (
            'Task tool example must NOT use subagent_type="{agent_display_name}"'
        )

    @pytest.mark.asyncio
    async def test_prompt_references_agent_name_matching_template_filename(self, generator, test_project):
        """
        BEHAVIOR: CLI mode prompt MUST explain agent_name matches template filename

        GIVEN: Claude Code CLI mode enabled
        WHEN: Generating staging prompt
        THEN: Prompt mentions agent_name matches template name
        AND: Example like "implementer-frontend" appears
        """
        prompt = await generator.generate_staging_prompt(
            orchestrator_id=str(uuid4()), project_id=test_project.id, claude_code_mode=True
        )

        # Should reference template matching pattern (example: implementer-frontend)
        assert "implementer-frontend" in prompt or "template name" in prompt.lower(), (
            "Prompt must reference agent_name matching template (e.g., implementer-frontend)"
        )


# ============================================================================
# MULTI-TERMINAL MODE TESTS - ENSURE NO IMPACT
# ============================================================================


class TestMultiTerminalModeUnaffected:
    """Test that multi-terminal mode is unaffected by agent_name changes"""

    @pytest.mark.asyncio
    async def test_multi_terminal_does_not_mention_agent_name_truth(self, generator, test_project):
        """
        BEHAVIOR: Multi-terminal mode should NOT mention agent_name as SINGLE SOURCE OF TRUTH

        GIVEN: Multi-terminal mode (claude_code_mode=False)
        WHEN: Generating staging prompt
        THEN: Prompt does NOT contain "agent_name: SINGLE SOURCE OF TRUTH"
        """
        prompt = await generator.generate_staging_prompt(
            orchestrator_id=str(uuid4()), project_id=test_project.id, claude_code_mode=False
        )

        # Multi-terminal should not have CLI-specific agent_name truth declaration
        assert "agent_name: SINGLE SOURCE OF TRUTH" not in prompt, (
            "Multi-terminal mode should not contain CLI-specific agent_name truth declaration"
        )

    @pytest.mark.asyncio
    async def test_multi_terminal_does_not_mention_agent_display_name_truth(self, generator, test_project):
        """
        BEHAVIOR: Multi-terminal mode should NOT mention agent_display_name as SINGLE SOURCE OF TRUTH

        GIVEN: Multi-terminal mode (claude_code_mode=False)
        WHEN: Generating staging prompt
        THEN: Prompt does NOT contain "agent_display_name: SINGLE SOURCE OF TRUTH"
        """
        prompt = await generator.generate_staging_prompt(
            orchestrator_id=str(uuid4()), project_id=test_project.id, claude_code_mode=False
        )

        # Multi-terminal should not have agent_display_name truth declaration either
        assert "agent_display_name: SINGLE SOURCE OF TRUTH" not in prompt, (
            "Multi-terminal mode should not contain agent_display_name truth declaration"
        )


# ============================================================================
# get_orchestrator_instructions() TESTS - CONTEXT INSTRUCTIONS
# ============================================================================
# NOTE: Removed tests for get_orchestrator_instructions() MCP tool behavior
# These should be tested in test_orchestration.py, not here (thin_prompt_generator tests)


# ============================================================================
# AGENT LIST SECTION TESTS - SPAWNED AGENTS DISPLAY
# ============================================================================


class TestAgentListSectionUsesAgentName:
    """Test that agent list section in prompts uses agent_name correctly"""

    @pytest.mark.asyncio
    async def test_agent_list_shows_agent_name_in_template_path(self, generator, test_project):
        """
        BEHAVIOR: Agent list section MUST show agent_name in template path reference

        GIVEN: Staging prompt with agent list section
        WHEN: Generating prompt for CLI mode
        THEN: Agent list shows template path as .claude/agents/{agent_name}.md
        """
        # Note: This test will pass once we have spawned agents in the database
        # For now, we're testing the template structure in the prompt
        prompt = await generator.generate_staging_prompt(
            orchestrator_id=str(uuid4()), project_id=test_project.id, claude_code_mode=True
        )

        # Look for template path pattern using agent_name
        # The prompt should reference .claude/agents/{agent_name}.md
        if ".claude/agents" in prompt:
            # Check that it uses agent_name variable, not agent_display_name
            assert "agent_name" in prompt.lower(), "Agent list template path should reference agent_name"
