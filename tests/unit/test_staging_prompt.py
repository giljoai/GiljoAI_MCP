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

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

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
    generator = ThinClientPromptGenerator(
        db=mock_db_session,
        tenant_key="test-tenant-123"
    )
    return generator


class TestGenerateStagingPromptExists:
    """Test that generate_staging_prompt method exists."""

    @pytest.mark.asyncio
    async def test_method_exists(self, prompt_generator):
        """Verify generate_staging_prompt method exists."""
        assert hasattr(prompt_generator, 'generate_staging_prompt'), \
            "generate_staging_prompt method must exist"


class TestStagingPromptStructure:
    """Test that staging prompt contains all required 7 tasks."""

    @pytest.mark.asyncio
    async def test_all_7_tasks_present(self, prompt_generator, mock_project, mock_product):
        """Verify all 7 tasks are present in staging prompt."""
        # Setup mocks
        with patch.object(prompt_generator, '_fetch_project', return_value=mock_project), \
             patch.object(prompt_generator, '_fetch_product', return_value=mock_product):

            orchestrator_id = str(uuid4())
            project_id = mock_project.id

            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=orchestrator_id,
                project_id=project_id
            )

            # All 7 tasks must be present
            assert "TASK 1" in prompt, "Task 1 (Identity & Context Verification) must be present"
            assert "TASK 2" in prompt, "Task 2 (MCP Health Check) must be present"
            assert "TASK 3" in prompt, "Task 3 (Environment Understanding) must be present"
            assert "TASK 4" in prompt, "Task 4 (Agent Discovery & Version Check) must be present"
            assert "TASK 5" in prompt, "Task 5 (Context Prioritization) must be present"
            assert "TASK 6" in prompt, "Task 6 (Agent Job Spawning) must be present"
            assert "TASK 7" in prompt, "Task 7 (Activation) must be present"

    @pytest.mark.asyncio
    async def test_task_1_identity_verification(self, prompt_generator, mock_project, mock_product):
        """Verify Task 1 contains identity verification instructions."""
        with patch.object(prompt_generator, '_fetch_project', return_value=mock_project), \
             patch.object(prompt_generator, '_fetch_product', return_value=mock_product):

            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()),
                project_id=mock_project.id
            )

            assert "IDENTITY" in prompt.upper(), "Task 1 must include identity verification"
            assert "CONTEXT VERIFICATION" in prompt.upper(), "Task 1 must include context verification"

    @pytest.mark.asyncio
    async def test_task_2_mcp_health_check(self, prompt_generator, mock_project, mock_product):
        """Verify Task 2 contains MCP health check instructions."""
        with patch.object(prompt_generator, '_fetch_project', return_value=mock_project), \
             patch.object(prompt_generator, '_fetch_product', return_value=mock_product):

            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()),
                project_id=mock_project.id
            )

            assert "MCP HEALTH CHECK" in prompt.upper(), "Task 2 must include MCP health check"
            assert "health_check()" in prompt, "Task 2 must reference health_check() MCP tool"

    @pytest.mark.asyncio
    async def test_task_3_environment_understanding(self, prompt_generator, mock_project, mock_product):
        """Verify Task 3 contains environment understanding instructions."""
        with patch.object(prompt_generator, '_fetch_project', return_value=mock_project), \
             patch.object(prompt_generator, '_fetch_product', return_value=mock_product):

            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()),
                project_id=mock_project.id
            )

            assert "ENVIRONMENT UNDERSTANDING" in prompt.upper(), "Task 3 must include environment understanding"
            assert "CLAUDE.MD" in prompt.upper(), "Task 3 must reference CLAUDE.md file"

    @pytest.mark.asyncio
    async def test_task_4_agent_discovery(self, prompt_generator, mock_project, mock_product):
        """Verify Task 4 contains agent discovery instructions."""
        with patch.object(prompt_generator, '_fetch_project', return_value=mock_project), \
             patch.object(prompt_generator, '_fetch_product', return_value=mock_product):

            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()),
                project_id=mock_project.id
            )

            assert "AGENT DISCOVERY" in prompt.upper(), "Task 4 must include agent discovery"
            assert "VERSION CHECK" in prompt.upper(), "Task 4 must include version checking"
            assert "get_available_agents()" in prompt, "Task 4 must call get_available_agents() MCP tool"

    @pytest.mark.asyncio
    async def test_task_5_context_prioritization(self, prompt_generator, mock_project, mock_product):
        """Verify Task 5 contains context prioritization instructions."""
        with patch.object(prompt_generator, '_fetch_project', return_value=mock_project), \
             patch.object(prompt_generator, '_fetch_product', return_value=mock_product):

            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()),
                project_id=mock_project.id
            )

            assert "CONTEXT PRIORITIZATION" in prompt.upper(), "Task 5 must include context prioritization"
            assert "MISSION" in prompt.upper(), "Task 5 must reference mission creation"

    @pytest.mark.asyncio
    async def test_task_6_agent_job_spawning(self, prompt_generator, mock_project, mock_product):
        """Verify Task 6 contains agent job spawning instructions."""
        with patch.object(prompt_generator, '_fetch_project', return_value=mock_project), \
             patch.object(prompt_generator, '_fetch_product', return_value=mock_product):

            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()),
                project_id=mock_project.id
            )

            assert "AGENT JOB SPAWNING" in prompt.upper(), "Task 6 must include agent job spawning"
            assert "spawn_agent_job()" in prompt, "Task 6 must reference spawn_agent_job() MCP tool"

    @pytest.mark.asyncio
    async def test_task_7_activation(self, prompt_generator, mock_project, mock_product):
        """Verify Task 7 contains activation instructions."""
        with patch.object(prompt_generator, '_fetch_project', return_value=mock_project), \
             patch.object(prompt_generator, '_fetch_product', return_value=mock_product):

            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()),
                project_id=mock_project.id
            )

            assert "ACTIVATION" in prompt.upper(), "Task 7 must include activation"
            assert "active" in prompt.lower(), "Task 7 must reference 'active' status"


class TestProductIdentityInclusion:
    """Test that Product ID is included in identity section."""

    @pytest.mark.asyncio
    async def test_product_id_in_prompt(self, prompt_generator, mock_project, mock_product):
        """Verify Product ID is in identity section."""
        with patch.object(prompt_generator, '_fetch_project', return_value=mock_project), \
             patch.object(prompt_generator, '_fetch_product', return_value=mock_product):

            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()),
                project_id=mock_project.id
            )

            assert "Product ID" in prompt or "PRODUCT ID" in prompt, \
                "Prompt must include Product ID label"
            assert mock_product.id in prompt, \
                f"Prompt must include actual product ID: {mock_product.id}"

    @pytest.mark.asyncio
    async def test_project_id_in_prompt(self, prompt_generator, mock_project, mock_product):
        """Verify Project ID is in identity section."""
        with patch.object(prompt_generator, '_fetch_project', return_value=mock_project), \
             patch.object(prompt_generator, '_fetch_product', return_value=mock_product):

            project_id = mock_project.id
            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()),
                project_id=project_id
            )

            assert "Project ID" in prompt or "PROJECT ID" in prompt, \
                "Prompt must include Project ID label"
            assert project_id in prompt, \
                f"Prompt must include actual project ID: {project_id}"

    @pytest.mark.asyncio
    async def test_tenant_key_in_prompt(self, prompt_generator, mock_project, mock_product):
        """Verify Tenant Key is in identity section."""
        with patch.object(prompt_generator, '_fetch_project', return_value=mock_project), \
             patch.object(prompt_generator, '_fetch_product', return_value=mock_product):

            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()),
                project_id=mock_project.id
            )

            assert "Tenant" in prompt or "TENANT" in prompt, \
                "Prompt must include Tenant Key label"
            assert prompt_generator.tenant_key in prompt, \
                f"Prompt must include tenant key: {prompt_generator.tenant_key}"


class TestMCPToolCalls:
    """Test that MCP tool calls are explicitly instructed."""

    @pytest.mark.asyncio
    async def test_get_available_agents_call_instruction(self, prompt_generator, mock_project, mock_product):
        """Verify instructions call get_available_agents() MCP tool."""
        with patch.object(prompt_generator, '_fetch_project', return_value=mock_project), \
             patch.object(prompt_generator, '_fetch_product', return_value=mock_product):

            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()),
                project_id=mock_project.id
            )

            assert "get_available_agents()" in prompt, \
                "Prompt must include get_available_agents() MCP tool call"
            # Check for imperative language (Call, call, invoke, etc.)
            prompt_lower = prompt.lower()
            assert any(word in prompt_lower for word in ["call", "invoke", "use", "execute"]), \
                "Prompt must include imperative instruction to call the tool"


class TestNoEmbeddedAgentTemplates:
    """Test that agent templates are NOT embedded in prompt."""

    @pytest.mark.asyncio
    async def test_no_embedded_templates(self, prompt_generator, mock_project, mock_product):
        """Verify agent templates are NOT embedded in prompt."""
        with patch.object(prompt_generator, '_fetch_project', return_value=mock_project), \
             patch.object(prompt_generator, '_fetch_product', return_value=mock_product):

            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()),
                project_id=mock_project.id
            )

            # Should NOT contain hardcoded agent template section
            assert "AGENT_TEMPLATES" not in prompt, \
                "Prompt must NOT contain embedded AGENT_TEMPLATES section"

            # Should NOT list multiple agents inline (would inflate token count)
            # Allow a few mentions (in instructions) but not extensive listings
            agent_keywords = ["implementer", "tester", "architect", "reviewer"]
            for keyword in agent_keywords:
                count = prompt.lower().count(keyword)
                assert count < 5, \
                    f"Prompt should not extensively list '{keyword}' agent (found {count} times)"


class TestTokenBudget:
    """Test that prompt stays under 1200 token budget."""

    @pytest.mark.asyncio
    async def test_token_count_under_budget(self, prompt_generator, mock_project, mock_product):
        """Verify prompt stays under 1200 token budget."""
        with patch.object(prompt_generator, '_fetch_project', return_value=mock_project), \
             patch.object(prompt_generator, '_fetch_product', return_value=mock_product):

            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()),
                project_id=mock_project.id
            )

            # Token estimation: len(prompt) // 4 (conservative estimate)
            estimated_tokens = len(prompt) // 4

            assert estimated_tokens < 1200, \
                f"Token count {estimated_tokens} exceeds budget of 1200 tokens"

    @pytest.mark.asyncio
    async def test_token_count_target_range(self, prompt_generator, mock_project, mock_product):
        """Verify prompt is in target range of 800-1000 tokens."""
        with patch.object(prompt_generator, '_fetch_project', return_value=mock_project), \
             patch.object(prompt_generator, '_fetch_product', return_value=mock_product):

            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()),
                project_id=mock_project.id
            )

            # Token estimation: len(prompt) // 4 (conservative estimate)
            estimated_tokens = len(prompt) // 4

            # Target range: 800-1000 tokens (allow some flexibility)
            assert estimated_tokens >= 600, \
                f"Token count {estimated_tokens} is too low (target: 800-1000)"
            assert estimated_tokens <= 1200, \
                f"Token count {estimated_tokens} exceeds maximum (target: 800-1000, max: 1200)"


class TestVersionChecking:
    """Test that version checking instructions are included."""

    @pytest.mark.asyncio
    async def test_version_checking_instructions(self, prompt_generator, mock_project, mock_product):
        """Verify version checking instructions are included."""
        with patch.object(prompt_generator, '_fetch_project', return_value=mock_project), \
             patch.object(prompt_generator, '_fetch_product', return_value=mock_product):

            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()),
                project_id=mock_project.id
            )

            prompt_lower = prompt.lower()
            assert "version" in prompt_lower, \
                "Prompt must include version checking instructions"
            assert "compatibility" in prompt_lower, \
                "Prompt must include compatibility verification instructions"


class TestExecutionModeHandling:
    """Test that execution mode is properly handled."""

    @pytest.mark.asyncio
    async def test_claude_code_mode_flag(self, prompt_generator, mock_project, mock_product):
        """Verify claude_code_mode parameter affects prompt."""
        with patch.object(prompt_generator, '_fetch_project', return_value=mock_project), \
             patch.object(prompt_generator, '_fetch_product', return_value=mock_product):

            # Test with claude_code_mode=True
            prompt_claude_code = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()),
                project_id=mock_project.id,
                claude_code_mode=True
            )

            # Test with claude_code_mode=False (default)
            prompt_manual = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()),
                project_id=mock_project.id,
                claude_code_mode=False
            )

            # Both should reference mode (using "Mode:" label for conciseness)
            assert "Mode:" in prompt_claude_code or "MODE:" in prompt_claude_code.upper(), \
                "Claude Code mode prompt must reference mode"
            assert "Mode:" in prompt_manual or "MODE:" in prompt_manual.upper(), \
                "Manual mode prompt must reference mode"

            # Claude Code mode should mention "Claude Code"
            assert "Claude Code" in prompt_claude_code, \
                "Claude Code mode prompt must mention 'Claude Code'"

            # Manual mode should NOT heavily emphasize Claude Code
            # (may mention it as an option, but shouldn't be primary mode)
            assert prompt_claude_code != prompt_manual, \
                "Execution mode should affect prompt content"


class TestWebSocketStatus:
    """Test that WebSocket status is included."""

    @pytest.mark.asyncio
    async def test_websocket_status_in_prompt(self, prompt_generator, mock_project, mock_product):
        """Verify WebSocket status is mentioned in prompt."""
        with patch.object(prompt_generator, '_fetch_project', return_value=mock_project), \
             patch.object(prompt_generator, '_fetch_product', return_value=mock_product):

            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()),
                project_id=mock_project.id
            )

            prompt_lower = prompt.lower()
            assert "websocket" in prompt_lower, \
                "Prompt must include WebSocket status reference"
