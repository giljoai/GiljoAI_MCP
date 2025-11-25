"""
Test Suite for Handover 0247 Integration Gaps

This test suite validates the 4 integration gaps completed in Handover 0247:
1. Version checking comparison logic in staging prompt (Task 4)
2. CLAUDE.md reading instruction in staging prompt (Task 3)
3. Product ID in execution prompts identity section
4. Execution mode preservation in succession chain

Author: System Architect Agent
Date: 2025-11-25
Handover: 0247
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator
from src.giljo_mcp.orchestrator_succession import OrchestratorSuccessionManager
from src.giljo_mcp.models import MCPAgentJob


# Fixtures
@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    return session


@pytest.fixture
def mock_sync_session():
    session = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.refresh = MagicMock()
    return session


@pytest.fixture
def mock_product():
    product = MagicMock()
    product.id = str(uuid4())
    product.name = "Test Product"
    product.tenant_key = "test-tenant-123"
    return product


@pytest.fixture
def mock_project():
    project = MagicMock()
    project.id = str(uuid4())
    project.name = "Test Project"
    project.product_id = str(uuid4())
    project.tenant_key = "test-tenant-123"
    project.context_budget = 200000
    return project


@pytest.fixture
def prompt_generator(mock_db_session):
    generator = ThinClientPromptGenerator(
        db=mock_db_session,
        tenant_key="test-tenant-123"
    )
    return generator


@pytest.fixture
def succession_manager(mock_sync_session):
    manager = OrchestratorSuccessionManager(
        db_session=mock_sync_session,
        tenant_key="test-tenant-123"
    )
    return manager


@pytest.fixture
def mock_orchestrator():
    orch = MagicMock(spec=MCPAgentJob)
    orch.job_id = str(uuid4())
    orch.tenant_key = "test-tenant-123"
    orch.project_id = str(uuid4())
    orch.instance_number = 1
    orch.context_budget = 200000
    orch.mission = "Test orchestrator mission"
    orch.job_metadata = {
        "execution_mode": "claude_code",
        "field_priorities": {"vision": 1, "architecture": 2},
        "depth_config": {"vision_chunking": "moderate"},
        "user_id": str(uuid4()),
        "tool": "claude-code",
        "created_via": "thin_client_generator"
    }
    return orch


# Gap 1: Version Checking
class TestGap1VersionCheckingLogic:
    @pytest.mark.asyncio
    async def test_version_comparison_instructions_present(
        self, prompt_generator, mock_project, mock_product
    ):
        with patch.object(prompt_generator, '_fetch_project', return_value=mock_project), patch.object(prompt_generator, '_fetch_product', return_value=mock_product):
            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()),
                project_id=mock_project.id
            )
            assert "TASK 4: AGENT DISCOVERY & VERSION CHECK" in prompt
            assert "get_available_agents(" in prompt
            assert "version" in prompt.lower()


# Gap 2: CLAUDE.md Reading
class TestGap2ClaudeMdReading:
    @pytest.mark.asyncio
    async def test_claude_md_reading_instruction_present(
        self, prompt_generator, mock_project, mock_product
    ):
        with patch.object(prompt_generator, '_fetch_project', return_value=mock_project), patch.object(prompt_generator, '_fetch_product', return_value=mock_product):
            prompt = await prompt_generator.generate_staging_prompt(
                orchestrator_id=str(uuid4()),
                project_id=mock_project.id
            )
            assert "TASK 3: ENVIRONMENT UNDERSTANDING" in prompt
            assert "CLAUDE.md" in prompt or "CLAUDE.MD" in prompt


# Gap 3: Product ID in Execution Prompts
class TestGap3ProductIdInExecutionPrompts:
    def test_product_id_in_multi_terminal_prompt(
        self, prompt_generator, mock_project
    ):
        prompt = prompt_generator._build_multi_terminal_execution_prompt(
            orchestrator_id=str(uuid4()),
            project=mock_project,
            agent_jobs=[]
        )
        assert "Product ID" in prompt or "PRODUCT ID" in prompt
        assert mock_project.product_id in prompt

    def test_product_id_in_claude_code_prompt(
        self, prompt_generator, mock_project
    ):
        prompt = prompt_generator._build_claude_code_execution_prompt(
            orchestrator_id=str(uuid4()),
            project=mock_project,
            agent_jobs=[]
        )
        assert "Product ID" in prompt or "PRODUCT ID" in prompt
        assert mock_project.product_id in prompt


# Gap 4: Execution Mode Preservation
class TestGap4ExecutionModePreservation:
    def test_successor_preserves_execution_mode_claude_code(
        self, succession_manager, mock_orchestrator
    ):
        mock_orchestrator.job_metadata["execution_mode"] = "claude_code"
        successor = succession_manager.create_successor(
            orchestrator=mock_orchestrator,
            reason="context_limit"
        )
        assert successor.job_metadata["execution_mode"] == "claude_code"

    def test_successor_defaults_to_multi_terminal_if_missing(
        self, succession_manager, mock_orchestrator
    ):
        mock_orchestrator.job_metadata = {"field_priorities": {}}
        successor = succession_manager.create_successor(
            orchestrator=mock_orchestrator,
            reason="manual"
        )
        assert successor.job_metadata["execution_mode"] == "multi-terminal"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
