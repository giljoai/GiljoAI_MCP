"""
Unit Tests for ThinClientPromptGenerator Execution Mode - Handover 0260 Phase 4

Tests mode-specific prompt generation for orchestrator staging prompts:
- Multi-terminal mode: Standard prompt without CLI-specific instructions
- Claude Code CLI mode: Enhanced prompt with strict Task tool requirements

Test Coverage (TDD - RED Phase):
1. Multi-terminal mode excludes CLI-specific instructions
2. Claude Code CLI mode includes strict Task tool requirements
3. CLI mode includes "EXACT AGENT NAMING" section
4. CLI mode includes forbidden examples
5. CLI mode includes agent spawning rules
6. Default behavior (no execution_mode param)
7. Prompt content verification (CRITICAL sections present)

Phase: Test-First Development (RED Phase - Tests FAIL)
Status: Awaiting implementation in generate_staging_prompt()
"""

import pytest
import pytest_asyncio
from uuid import uuid4


# ============================================================================
# FIXTURES
# ============================================================================

@pytest_asyncio.fixture(scope="function")
async def test_product(db_session, test_project):
    """Create test product for prompt generation."""
    from src.giljo_mcp.models import Product

    product = Product(
        id=str(uuid4()),
        name="Test Product",
        description="Test product for mode-specific prompts",
        tenant_key=test_project.tenant_key,
        config_data={
            "tech_stack": {
                "languages": ["Python 3.11+"],
                "frameworks": ["FastAPI", "Vue 3"]
            },
            "architecture": {
                "patterns": ["Service Layer", "Repository Pattern"]
            }
        }
    )

    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    # Link project to product
    test_project.product_id = product.id
    await db_session.commit()

    return product


@pytest_asyncio.fixture(scope="function")
async def generator(db_session, test_project):
    """Create ThinClientPromptGenerator instance."""
    from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator

    return ThinClientPromptGenerator(
        db=db_session,
        tenant_key=test_project.tenant_key
    )


# ============================================================================
# MULTI-TERMINAL MODE TESTS
# ============================================================================

class TestMultiTerminalModePrompts:
    """Test multi-terminal mode prompt generation (default behavior)"""

    @pytest.mark.asyncio
    async def test_multi_terminal_mode_excludes_cli_instructions(
        self, generator, test_project, test_product
    ):
        """Multi-terminal mode prompt should NOT contain Claude Code CLI instructions"""
        prompt = await generator.generate_staging_prompt(
            orchestrator_id=str(uuid4()),
            project_id=test_project.id,
            claude_code_mode=False
        )

        # Should NOT contain CLI-specific sections
        assert 'CLAUDE CODE CLI MODE' not in prompt
        assert 'STRICT TASK TOOL' not in prompt
        assert 'EXACT AGENT NAMING' not in prompt
        assert 'Task tool' not in prompt  # Generic mention might appear, but specific instructions shouldn't

    @pytest.mark.asyncio
    async def test_multi_terminal_excludes_agent_spawning_rules(
        self, generator, test_project, test_product
    ):
        """Multi-terminal mode should not include Task tool agent spawning rules"""
        prompt = await generator.generate_staging_prompt(
            orchestrator_id=str(uuid4()),
            project_id=test_project.id,
            claude_code_mode=False
        )

        # Should NOT contain Task tool specific rules
        assert 'subagent_type parameter' not in prompt
        assert 'FORBIDDEN' not in prompt
        assert 'backend-tester-for-api-validation' not in prompt  # Example forbidden name

    @pytest.mark.asyncio
    async def test_multi_terminal_default_when_param_omitted(
        self, generator, test_project, test_product
    ):
        """Default behavior (no param) should be multi-terminal mode"""
        # Call without claude_code_mode parameter (should default to False)
        prompt = await generator.generate_staging_prompt(
            orchestrator_id=str(uuid4()),
            project_id=test_project.id
            # claude_code_mode omitted - should default to False
        )

        # Verify it's multi-terminal mode (no CLI instructions)
        assert 'CLAUDE CODE CLI MODE' not in prompt
        assert 'STRICT TASK TOOL' not in prompt


# ============================================================================
# CLAUDE CODE CLI MODE TESTS
# ============================================================================

class TestClaudeCodeCLIModePrompts:
    """Test Claude Code CLI mode prompt generation"""

    @pytest.mark.asyncio
    async def test_claude_code_cli_mode_includes_strict_instructions(
        self, generator, test_project, test_product
    ):
        """Claude Code CLI mode prompt MUST contain strict Task tool instructions"""
        prompt = await generator.generate_staging_prompt(
            orchestrator_id=str(uuid4()),
            project_id=test_project.id,
            claude_code_mode=True
        )

        # MUST contain CLI mode header
        assert 'CLAUDE CODE CLI MODE' in prompt
        assert 'STRICT TASK TOOL REQUIREMENTS' in prompt

    @pytest.mark.asyncio
    async def test_cli_mode_includes_exact_agent_naming_section(
        self, generator, test_project, test_product
    ):
        """CLI mode prompt must include EXACT AGENT NAMING section"""
        prompt = await generator.generate_staging_prompt(
            orchestrator_id=str(uuid4()),
            project_id=test_project.id,
            claude_code_mode=True
        )

        # Must contain exact naming rules
        assert 'EXACT AGENT NAMING' in prompt
        assert 'NO EXCEPTIONS' in prompt or 'CRITICAL' in prompt  # Emphasis on strictness

    @pytest.mark.asyncio
    async def test_cli_mode_includes_allowed_examples(
        self, generator, test_project, test_product
    ):
        """CLI mode must show ALLOWED agent naming examples"""
        prompt = await generator.generate_staging_prompt(
            orchestrator_id=str(uuid4()),
            project_id=test_project.id,
            claude_code_mode=True
        )

        # Must contain allowed example pattern
        assert 'ALLOWED' in prompt
        assert 'backend-tester' in prompt or 'implementor' in prompt  # Example template names

    @pytest.mark.asyncio
    async def test_cli_mode_includes_forbidden_examples(
        self, generator, test_project, test_product
    ):
        """CLI mode must show FORBIDDEN agent naming examples"""
        prompt = await generator.generate_staging_prompt(
            orchestrator_id=str(uuid4()),
            project_id=test_project.id,
            claude_code_mode=True
        )

        # Must contain forbidden examples
        assert 'FORBIDDEN' in prompt
        # Examples of bad naming patterns
        assert (
            'backend-tester-for-api-validation' in prompt or
            'Backend Tester Agent' in prompt
        ), "Prompt must include at least one forbidden naming example"

    @pytest.mark.asyncio
    async def test_cli_mode_includes_agent_spawning_rules(
        self, generator, test_project, test_product
    ):
        """CLI mode prompt must include agent spawning rules"""
        prompt = await generator.generate_staging_prompt(
            orchestrator_id=str(uuid4()),
            project_id=test_project.id,
            claude_code_mode=True
        )

        # Must explain Task tool parameters
        assert 'subagent_type parameter' in prompt or 'agent_type parameter' in prompt
        assert 'agent_name parameter' in prompt

        # Must mention parameter requirements
        assert 'MUST be EXACTLY' in prompt or 'must match' in prompt

    @pytest.mark.asyncio
    async def test_cli_mode_includes_template_matching_requirement(
        self, generator, test_project, test_product
    ):
        """CLI mode must specify that agent names must match template filenames"""
        prompt = await generator.generate_staging_prompt(
            orchestrator_id=str(uuid4()),
            project_id=test_project.id,
            claude_code_mode=True
        )

        # Must mention template matching
        assert 'template' in prompt.lower()
        assert 'matches' in prompt.lower() or 'match' in prompt.lower()
        assert '.md' in prompt  # Reference to .md template files


# ============================================================================
# MODE COMPARISON TESTS
# ============================================================================

class TestExecutionModeComparison:
    """Test differences between multi-terminal and CLI modes"""

    @pytest.mark.asyncio
    async def test_cli_mode_longer_than_multi_terminal(
        self, generator, test_project, test_product
    ):
        """CLI mode prompt should be longer due to additional instructions"""
        orchestrator_id = str(uuid4())

        # Generate both prompts
        multi_terminal_prompt = await generator.generate_staging_prompt(
            orchestrator_id=orchestrator_id,
            project_id=test_project.id,
            claude_code_mode=False
        )

        cli_mode_prompt = await generator.generate_staging_prompt(
            orchestrator_id=orchestrator_id,
            project_id=test_project.id,
            claude_code_mode=True
        )

        # CLI mode should be longer (includes additional instructions)
        assert len(cli_mode_prompt) > len(multi_terminal_prompt), \
            "CLI mode prompt should be longer due to Task tool instructions"

    @pytest.mark.asyncio
    async def test_both_modes_contain_core_sections(
        self, generator, test_project, test_product
    ):
        """Both modes should contain core staging workflow sections"""
        orchestrator_id = str(uuid4())

        # Generate both prompts
        multi_terminal_prompt = await generator.generate_staging_prompt(
            orchestrator_id=orchestrator_id,
            project_id=test_project.id,
            claude_code_mode=False
        )

        cli_mode_prompt = await generator.generate_staging_prompt(
            orchestrator_id=orchestrator_id,
            project_id=test_project.id,
            claude_code_mode=True
        )

        # Both should contain core sections
        core_sections = [
            'STAGING WORKFLOW',
            'IDENTITY',
            'TASK 1',
            'TASK 2',
            'MCP HEALTH CHECK',
            'TASK 4',  # Agent discovery
            'TASK 5',  # Context prioritization
            'TASK 6',  # Job spawning
            'TASK 7',  # Activation
        ]

        for section in core_sections:
            assert section in multi_terminal_prompt, \
                f"Multi-terminal prompt missing core section: {section}"
            assert section in cli_mode_prompt, \
                f"CLI mode prompt missing core section: {section}"

    @pytest.mark.asyncio
    async def test_cli_mode_unique_sections_absent_in_multi_terminal(
        self, generator, test_project, test_product
    ):
        """Verify CLI-specific sections only appear in CLI mode"""
        orchestrator_id = str(uuid4())

        # Generate both prompts
        multi_terminal_prompt = await generator.generate_staging_prompt(
            orchestrator_id=orchestrator_id,
            project_id=test_project.id,
            claude_code_mode=False
        )

        cli_mode_prompt = await generator.generate_staging_prompt(
            orchestrator_id=orchestrator_id,
            project_id=test_project.id,
            claude_code_mode=True
        )

        # CLI-specific sections
        cli_specific_sections = [
            'CLAUDE CODE CLI MODE',
            'STRICT TASK TOOL',
            'EXACT AGENT NAMING',
            'FORBIDDEN'
        ]

        for section in cli_specific_sections:
            # Must be in CLI mode
            assert section in cli_mode_prompt, \
                f"CLI mode missing required section: {section}"

            # Must NOT be in multi-terminal mode
            assert section not in multi_terminal_prompt, \
                f"Multi-terminal mode should not contain CLI-specific section: {section}"


# ============================================================================
# PROMPT CONTENT VALIDATION
# ============================================================================

class TestPromptContentValidation:
    """Test specific content requirements in prompts"""

    @pytest.mark.asyncio
    async def test_cli_mode_mentions_single_terminal_constraint(
        self, generator, test_project, test_product
    ):
        """CLI mode prompt should mention single-terminal constraint"""
        prompt = await generator.generate_staging_prompt(
            orchestrator_id=str(uuid4()),
            project_id=test_project.id,
            claude_code_mode=True
        )

        # Should mention single-terminal or CLI constraint
        assert (
            'single-terminal' in prompt.lower() or
            'single terminal' in prompt.lower() or
            'CLI mode' in prompt or
            'Claude Code CLI' in prompt
        )

    @pytest.mark.asyncio
    async def test_cli_mode_explains_why_exact_naming_required(
        self, generator, test_project, test_product
    ):
        """CLI mode should explain WHY exact naming is required"""
        prompt = await generator.generate_staging_prompt(
            orchestrator_id=str(uuid4()),
            project_id=test_project.id,
            claude_code_mode=True
        )

        # Should explain the constraint (matches template files)
        assert 'template' in prompt.lower()
        assert '.md' in prompt  # References .md template files

    @pytest.mark.asyncio
    async def test_both_modes_include_execution_mode_label(
        self, generator, test_project, test_product
    ):
        """Both prompts should clearly label their execution mode"""
        orchestrator_id = str(uuid4())

        multi_terminal_prompt = await generator.generate_staging_prompt(
            orchestrator_id=orchestrator_id,
            project_id=test_project.id,
            claude_code_mode=False
        )

        cli_mode_prompt = await generator.generate_staging_prompt(
            orchestrator_id=orchestrator_id,
            project_id=test_project.id,
            claude_code_mode=True
        )

        # Multi-terminal should say "Manual Multi-Terminal"
        assert 'Manual Multi-Terminal' in multi_terminal_prompt or \
               'Multi-Terminal' in multi_terminal_prompt

        # CLI mode should say "Claude Code CLI"
        assert 'Claude Code CLI' in cli_mode_prompt


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestExecutionModeErrorHandling:
    """Test error handling for execution mode parameter"""

    @pytest.mark.asyncio
    async def test_invalid_project_id_raises_error(
        self, generator
    ):
        """Invalid project_id should raise ValueError"""
        with pytest.raises(ValueError, match="not found"):
            await generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()),
                project_id=str(uuid4()),  # Non-existent project
                claude_code_mode=True
            )

    @pytest.mark.asyncio
    async def test_none_claude_code_mode_treated_as_false(
        self, generator, test_project, test_product
    ):
        """None value for claude_code_mode should behave like False"""
        prompt = await generator.generate_staging_prompt(
            orchestrator_id=str(uuid4()),
            project_id=test_project.id,
            claude_code_mode=None  # Explicitly None
        )

        # Should behave like multi-terminal mode (no CLI instructions)
        assert 'CLAUDE CODE CLI MODE' not in prompt
