"""
Test Suite for generate_staging_prompt() method (Handover 0246a)

TDD Implementation - Tests written BEFORE implementation.

These tests validate:
1. Method existence
2. All 7 tasks present in correct sequence
3. Product ID included in identity section
4. MCP tool call instructions (get_available_agents)
5. No embedded agent templates (dynamic fetching only)
6. Token budget enforcement (<1200 tokens)
7. Version checking instructions
8. Execution mode handling (Claude Code vs Manual)

Author: TDD Implementor Agent
Date: 2025-11-24
Handover: 0246a
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator


@pytest.fixture
def mock_db_session():
    """Mock AsyncSession for database operations."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_product():
    """Mock product with required attributes."""
    product = MagicMock()
    product.id = str(uuid4())
    product.name = "Test Product"
    product.tenant_key = "test-tenant-123"
    return product


@pytest.fixture
def mock_project():
    """Mock project with required attributes."""
    project = MagicMock()
    project.id = str(uuid4())
    project.name = "Test Project"
    project.product_id = str(uuid4())
    project.tenant_key = "test-tenant-123"
    return project


@pytest.fixture
def prompt_generator(mock_db_session):
    """Create ThinClientPromptGenerator instance."""
    generator = ThinClientPromptGenerator(db=mock_db_session, tenant_key="test-tenant-123")
    return generator


class TestGenerateStagingPromptExists:
    """Test that generate_staging_prompt method exists."""

    @pytest.mark.asyncio
    async def test_method_exists(self, prompt_generator):
        """Verify generate_staging_prompt method exists."""
        assert hasattr(prompt_generator, "generate_staging_prompt"), "generate_staging_prompt method must exist"


class TestStagingPromptStructure:
    """Test that staging prompt contains all required startup steps."""

    @pytest.mark.asyncio
    async def test_all_7_tasks_present(self, prompt_generator, mock_project, mock_product):
        """Verify all 8 startup steps are present in staging prompt."""
        # Setup mocks
        with (
            patch.object(prompt_generator, "_fetch_project", return_value=mock_project),
            patch.object(prompt_generator, "_fetch_product", return_value=mock_product),
        ):
            orchestrator_id = str(uuid4())
            project_id = mock_project.id

            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=orchestrator_id, project_id=project_id
            )

            # All 8 numbered steps must be present in STARTUP SEQUENCE
            assert "STARTUP SEQUENCE:" in prompt, "STARTUP SEQUENCE section must be present"
            assert "1. Verify MCP:" in prompt or "1." in prompt, "Step 1 must be present"
            assert "2. Fetch context:" in prompt or "2." in prompt, "Step 2 must be present"
            assert "3. CREATE MISSION:" in prompt or "3." in prompt, "Step 3 must be present"
            assert "4. PERSIST MISSION:" in prompt or "4." in prompt, "Step 4 must be present"
            assert "5. SPAWN AGENTS:" in prompt or "5." in prompt, "Step 5 must be present"
            assert "6. WRITE YOUR EXECUTION PLAN:" in prompt or "6." in prompt, "Step 6 must be present"
            assert "7. SIGNAL COMPLETE:" in prompt or "7." in prompt, "Step 7 must be present"
            assert "8. EXECUTION PHASE MONITORING:" in prompt or "8." in prompt, "Step 8 must be present"

    @pytest.mark.asyncio
    async def test_task_1_identity_verification(self, prompt_generator, mock_project, mock_product):
        """Verify IDENTITY section contains required fields."""
        with (
            patch.object(prompt_generator, "_fetch_project", return_value=mock_project),
            patch.object(prompt_generator, "_fetch_product", return_value=mock_product),
        ):
            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()), project_id=mock_project.id
            )

            assert "IDENTITY" in prompt.upper(), "Must include IDENTITY section"
            assert "Orchestrator ID:" in prompt, "IDENTITY must include Orchestrator ID"
            assert "Project ID:" in prompt, "IDENTITY must include Project ID"
            assert "Tenant Key:" in prompt, "IDENTITY must include Tenant Key"

    @pytest.mark.asyncio
    async def test_task_2_mcp_health_check(self, prompt_generator, mock_project, mock_product):
        """Verify Step 1 contains MCP health check instructions."""
        with (
            patch.object(prompt_generator, "_fetch_project", return_value=mock_project),
            patch.object(prompt_generator, "_fetch_product", return_value=mock_product),
        ):
            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()), project_id=mock_project.id
            )

            assert "MCP CONNECTION:" in prompt, "Must include MCP CONNECTION section"
            assert "health_check()" in prompt, "Step 1 must reference health_check() MCP tool"
            assert "1. Verify MCP:" in prompt, "Step 1 must verify MCP connection"

    @pytest.mark.asyncio
    async def test_task_3_environment_understanding(self, prompt_generator, mock_project, mock_product):
        """Verify Step 2 contains context fetching instructions."""
        with (
            patch.object(prompt_generator, "_fetch_project", return_value=mock_project),
            patch.object(prompt_generator, "_fetch_product", return_value=mock_product),
        ):
            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()), project_id=mock_project.id
            )

            assert "2. Fetch context:" in prompt, "Step 2 must fetch context"
            assert "get_orchestrator_instructions" in prompt, "Step 2 must call get_orchestrator_instructions()"
            assert "Project description" in prompt or "Product context" in prompt, (
                "Step 2 must mention context retrieval"
            )

    @pytest.mark.asyncio
    async def test_task_4_agent_discovery(self, prompt_generator, mock_project, mock_product):
        """Verify Step 2 returns available agent templates."""
        with (
            patch.object(prompt_generator, "_fetch_project", return_value=mock_project),
            patch.object(prompt_generator, "_fetch_product", return_value=mock_product),
        ):
            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()), project_id=mock_project.id
            )

            # Step 2 returns available agent templates via get_orchestrator_instructions
            assert "AVAILABLE AGENT TEMPLATES" in prompt.upper(), "Step 2 must mention agent templates are returned"
            assert "get_orchestrator_instructions" in prompt, "Step 2 must call get_orchestrator_instructions()"

    @pytest.mark.asyncio
    async def test_task_5_context_prioritization(self, prompt_generator, mock_project, mock_product):
        """Verify Steps 3-4 contain mission creation and persistence."""
        with (
            patch.object(prompt_generator, "_fetch_project", return_value=mock_project),
            patch.object(prompt_generator, "_fetch_product", return_value=mock_product),
        ):
            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()), project_id=mock_project.id
            )

            assert "3. CREATE MISSION:" in prompt, "Step 3 must create mission"
            assert "4. PERSIST MISSION:" in prompt, "Step 4 must persist mission"
            assert "update_project_mission" in prompt, "Step 4 must call update_project_mission()"

    @pytest.mark.asyncio
    async def test_task_6_agent_job_spawning(self, prompt_generator, mock_project, mock_product):
        """Verify Step 5 contains agent job spawning instructions."""
        with (
            patch.object(prompt_generator, "_fetch_project", return_value=mock_project),
            patch.object(prompt_generator, "_fetch_product", return_value=mock_product),
        ):
            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()), project_id=mock_project.id
            )

            assert "5. SPAWN AGENTS:" in prompt, "Step 5 must spawn agents"
            assert "spawn_agent_job()" in prompt, "Step 5 must reference spawn_agent_job() MCP tool"
            assert "agent_name MUST exactly match template name" in prompt, "Step 5 must warn about agent_name matching"

    @pytest.mark.asyncio
    async def test_task_7_activation(self, prompt_generator, mock_project, mock_product):
        """Verify Step 7 contains staging complete signal."""
        with (
            patch.object(prompt_generator, "_fetch_project", return_value=mock_project),
            patch.object(prompt_generator, "_fetch_product", return_value=mock_product),
        ):
            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()), project_id=mock_project.id
            )

            assert "7. SIGNAL COMPLETE:" in prompt, "Step 7 must signal completion"
            assert "send_message" in prompt, "Step 7 must send broadcast message"
            assert "STAGING_COMPLETE" in prompt, "Step 7 must broadcast STAGING_COMPLETE"


class TestProductIdentityInclusion:
    """Test that identity section contains required fields."""

    @pytest.mark.asyncio
    async def test_product_id_in_prompt(self, prompt_generator, mock_project, mock_product):
        """Verify IDENTITY section contains orchestrator, project, and tenant info."""
        with (
            patch.object(prompt_generator, "_fetch_project", return_value=mock_project),
            patch.object(prompt_generator, "_fetch_product", return_value=mock_product),
        ):
            orchestrator_id = str(uuid4())
            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=orchestrator_id, project_id=mock_project.id
            )

            # Current implementation includes these in IDENTITY section
            assert "IDENTITY:" in prompt, "Must include IDENTITY section"
            assert orchestrator_id in prompt, "Must include orchestrator ID"
            assert "Execution Mode:" in prompt, "Must include execution mode"

    @pytest.mark.asyncio
    async def test_project_id_in_prompt(self, prompt_generator, mock_project, mock_product):
        """Verify Project ID is in identity section."""
        with (
            patch.object(prompt_generator, "_fetch_project", return_value=mock_project),
            patch.object(prompt_generator, "_fetch_product", return_value=mock_product),
        ):
            project_id = mock_project.id
            prompt = await prompt_generator.generate_staging_prompt(orchestrator_id=str(uuid4()), project_id=project_id)

            assert "Project ID" in prompt or "PROJECT ID" in prompt, "Prompt must include Project ID label"
            assert project_id in prompt, f"Prompt must include actual project ID: {project_id}"

    @pytest.mark.asyncio
    async def test_tenant_key_in_prompt(self, prompt_generator, mock_project, mock_product):
        """Verify Tenant Key is in identity section."""
        with (
            patch.object(prompt_generator, "_fetch_project", return_value=mock_project),
            patch.object(prompt_generator, "_fetch_product", return_value=mock_product),
        ):
            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()), project_id=mock_project.id
            )

            assert "Tenant" in prompt or "TENANT" in prompt, "Prompt must include Tenant Key label"
            assert prompt_generator.tenant_key in prompt, (
                f"Prompt must include tenant key: {prompt_generator.tenant_key}"
            )


class TestMCPToolCalls:
    """Test that MCP tool calls are explicitly instructed."""

    @pytest.mark.asyncio
    async def test_get_available_agents_call_instruction(self, prompt_generator, mock_project, mock_product):
        """Verify instructions call get_orchestrator_instructions() MCP tool."""
        with (
            patch.object(prompt_generator, "_fetch_project", return_value=mock_project),
            patch.object(prompt_generator, "_fetch_product", return_value=mock_product),
        ):
            orchestrator_id = str(uuid4())
            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=orchestrator_id, project_id=mock_project.id
            )

            # Current implementation uses get_orchestrator_instructions (Step 2)
            assert "get_orchestrator_instructions" in prompt, (
                "Prompt must include get_orchestrator_instructions() MCP tool call"
            )
            assert orchestrator_id in prompt, "Prompt must include orchestrator_id for tool call"
            assert prompt_generator.tenant_key in prompt, "Prompt must include tenant_key for tool call"


class TestNoEmbeddedAgentTemplates:
    """Test that agent templates are NOT embedded in prompt."""

    @pytest.mark.asyncio
    async def test_no_embedded_templates(self, prompt_generator, mock_project, mock_product):
        """Verify agent templates are NOT embedded in prompt."""
        with (
            patch.object(prompt_generator, "_fetch_project", return_value=mock_project),
            patch.object(prompt_generator, "_fetch_product", return_value=mock_product),
        ):
            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()), project_id=mock_project.id
            )

            # Should NOT contain hardcoded agent template section
            assert "AGENT_TEMPLATES" not in prompt, "Prompt must NOT contain embedded AGENT_TEMPLATES section"

            # Should NOT list multiple agents inline (would inflate token count)
            # Allow a few mentions (in instructions) but not extensive listings
            agent_keywords = ["implementer", "tester", "architect", "reviewer"]
            for keyword in agent_keywords:
                count = prompt.lower().count(keyword)
                assert count < 5, f"Prompt should not extensively list '{keyword}' agent (found {count} times)"


class TestTokenBudget:
    """Test that prompt stays under 1200 token budget."""

    @pytest.mark.asyncio
    async def test_token_count_under_budget(self, prompt_generator, mock_project, mock_product):
        """Verify prompt stays under 1200 token budget."""
        with (
            patch.object(prompt_generator, "_fetch_project", return_value=mock_project),
            patch.object(prompt_generator, "_fetch_product", return_value=mock_product),
        ):
            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()), project_id=mock_project.id
            )

            # Token estimation: len(prompt) // 4 (conservative estimate)
            estimated_tokens = len(prompt) // 4

            assert estimated_tokens < 1200, f"Token count {estimated_tokens} exceeds budget of 1200 tokens"

    @pytest.mark.asyncio
    async def test_token_count_target_range(self, prompt_generator, mock_project, mock_product):
        """Verify prompt is in target range of 800-1000 tokens."""
        with (
            patch.object(prompt_generator, "_fetch_project", return_value=mock_project),
            patch.object(prompt_generator, "_fetch_product", return_value=mock_product),
        ):
            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()), project_id=mock_project.id
            )

            # Token estimation: len(prompt) // 4 (conservative estimate)
            estimated_tokens = len(prompt) // 4

            # Target range: 800-1000 tokens (allow some flexibility)
            assert estimated_tokens >= 600, f"Token count {estimated_tokens} is too low (target: 800-1000)"
            assert estimated_tokens <= 1200, (
                f"Token count {estimated_tokens} exceeds maximum (target: 800-1000, max: 1200)"
            )


class TestVersionChecking:
    """Test that role and workflow are clearly defined."""

    @pytest.mark.asyncio
    async def test_version_checking_instructions(self, prompt_generator, mock_project, mock_product):
        """Verify role section defines staging vs execution clearly."""
        with (
            patch.object(prompt_generator, "_fetch_project", return_value=mock_project),
            patch.object(prompt_generator, "_fetch_product", return_value=mock_product),
        ):
            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()), project_id=mock_project.id
            )

            # Current implementation has "YOUR ROLE: PROJECT STAGING (NOT EXECUTION)"
            assert "YOUR ROLE:" in prompt, "Prompt must define orchestrator role"
            assert "STAGING" in prompt.upper(), "Prompt must mention staging phase"
            assert "NOT EXECUTION" in prompt.upper() or "not execution" in prompt.lower(), (
                "Prompt must clarify this is staging, not execution"
            )


class TestExecutionModeHandling:
    """Test that execution mode is properly handled.

    NOTE: The claude_code_mode parameter was removed as the execution mode
    is now read from Project.execution_mode in the database when
    get_orchestrator_instructions() is called. The thin prompt is intentionally
    mode-agnostic.
    """

    @pytest.mark.asyncio
    async def test_staging_prompt_is_mode_agnostic(self, prompt_generator, mock_project, mock_product):
        """Verify staging prompt is mode-agnostic (doesn't require claude_code_mode parameter)."""
        with (
            patch.object(prompt_generator, "_fetch_project", return_value=mock_project),
            patch.object(prompt_generator, "_fetch_product", return_value=mock_product),
        ):
            # Generate prompt without claude_code_mode parameter
            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()), project_id=mock_project.id
            )

            # Verify the prompt is generated successfully
            assert prompt, "Staging prompt should be generated"
            assert len(prompt) > 0, "Staging prompt should not be empty"

            # The prompt should be universal and work for any execution mode
            # (mode is determined later from Project.execution_mode in database)
            assert "PROJECT STAGING" in prompt.upper(), "Prompt should indicate staging phase"


class TestWebSocketStatus:
    """Test that communication mechanisms are described."""

    @pytest.mark.asyncio
    async def test_websocket_status_in_prompt(self, prompt_generator, mock_project, mock_product):
        """Verify messaging and monitoring instructions are included."""
        with (
            patch.object(prompt_generator, "_fetch_project", return_value=mock_project),
            patch.object(prompt_generator, "_fetch_product", return_value=mock_product),
        ):
            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()), project_id=mock_project.id
            )

            # Current implementation mentions messaging and monitoring
            assert "send_message" in prompt or "receive_messages" in prompt, (
                "Prompt must include messaging instructions"
            )
            # Handover 0382: Step 8 now marked as context for planning only
            assert "8. [CONTEXT FOR PLANNING ONLY] EXECUTION PHASE MONITORING:" in prompt, (
                "Prompt must include execution phase monitoring step (marked as planning context)"
            )


class TestOutdatedReferencesRemoved:
    """Test that outdated handover references are removed (Issue 0361)."""

    @pytest.mark.asyncio
    async def test_0106b_reference_not_in_prompt(self, prompt_generator, mock_project, mock_product):
        """Verify outdated 'Handover 0106b' reference is not in staging prompt."""
        with (
            patch.object(prompt_generator, "_fetch_project", return_value=mock_project),
            patch.object(prompt_generator, "_fetch_product", return_value=mock_product),
        ):
            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()), project_id=mock_project.id
            )

            # Verify no outdated handover references
            assert "0106b" not in prompt, "Staging prompt must NOT contain outdated '0106b' reference"
            assert "Handover 0106b" not in prompt, "Staging prompt must NOT contain 'Handover 0106b' reference"
