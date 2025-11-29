"""
Tests for ThinClientPromptGenerator Layer 1 (Orchestrator Spawn Prompt).

This test focuses on verifying that the orchestrator spawn prompt uses
CORRECT MCP command names when reminding sub-agents of their protocol.

Handover 0252: Three-Layer Instruction Architecture Cleanup
Layer 1: Orchestrator Spawn Prompt
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator


class TestOrchestratorSpawnPromptMCPCommands:
    """Test that orchestrator spawn prompt uses correct MCP commands."""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        from src.giljo_mcp.models import Project, Product

        session = AsyncMock()

        # Mock project fetch
        mock_project = MagicMock(spec=Project)
        mock_project.id = str(uuid4())
        mock_project.product_id = str(uuid4())
        mock_project.tenant_key = "test_tenant"

        # Mock product fetch
        mock_product = MagicMock(spec=Product)
        mock_product.id = mock_project.product_id
        mock_product.product_name = "Test Product"

        async def mock_execute(query):
            result = MagicMock()
            result.scalar_one_or_none.return_value = mock_project if "project" in str(query).lower() else mock_product
            return result

        session.execute = mock_execute
        return session

    @pytest.fixture
    def prompt_generator(self, mock_db_session):
        """Create ThinClientPromptGenerator instance."""
        return ThinClientPromptGenerator(
            db=mock_db_session,
            tenant_key="test_tenant"
        )

    @pytest.mark.asyncio
    async def test_spawn_prompt_uses_correct_mcp_commands(self, prompt_generator):
        """Orchestrator spawn prompt should use get_next_instruction() NOT receive_messages()"""
        # Generate the staging prompt (includes spawn instructions)
        prompt = await prompt_generator.generate_staging_prompt(
            orchestrator_id=str(uuid4()),
            project_id=str(uuid4())
        )

        # Verify CORRECT command is used
        assert "get_next_instruction()" in prompt, "Missing get_next_instruction() in spawn instructions"

        # Verify INCORRECT command is NOT used
        assert "receive_messages()" not in prompt, "Found obsolete receive_messages() - should be get_next_instruction()"

    @pytest.mark.asyncio
    async def test_spawn_prompt_has_all_required_commands(self, prompt_generator):
        """Verify all required MCP commands are mentioned in spawn prompt"""
        prompt = await prompt_generator.generate_staging_prompt(
            orchestrator_id=str(uuid4()),
            project_id=str(uuid4())
        )

        # Commands agents should be reminded of
        assert "acknowledge_job(" in prompt, "Missing acknowledge_job() in spawn instructions"
        assert "report_progress()" in prompt, "Missing report_progress() in spawn instructions"
        assert "get_next_instruction()" in prompt, "Missing get_next_instruction() in spawn instructions"
        assert "complete_job()" in prompt, "Missing complete_job() in spawn instructions"

        # Obsolete commands should NOT be present
        assert "update_job_progress" not in prompt, "Found obsolete update_job_progress() - should be report_progress()"
        assert "acknowledge_message" not in prompt, "Found obsolete acknowledge_message() - this function doesn't exist"
