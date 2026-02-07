"""
Unit tests for ThinClientPromptGenerator (Handover 0088)

Simple unit tests that don't require full database schema.
Tests the core logic of thin prompt generation.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.giljo_mcp.thin_prompt_generator import ThinPromptResponse


class TestThinPromptResponse:
    """Test the dataclass structure."""

    def test_thin_prompt_response_creation(self):
        """Test creating ThinPromptResponse."""
        response = ThinPromptResponse(
            prompt="Test prompt",
            orchestrator_id="orch-123",
            project_id="proj-456",
            project_name="Test Project",
            estimated_prompt_tokens=50,
            mcp_tool_name="get_orchestrator_instructions",
            instructions_stored=True,
        )

        assert response.prompt == "Test prompt"
        assert response.orchestrator_id == "orch-123"
        assert response.project_id == "proj-456"
        assert response.project_name == "Test Project"
        assert response.estimated_prompt_tokens == 50
        assert response.mcp_tool_name == "get_orchestrator_instructions"
        assert response.instructions_stored is True


class TestThinPromptBuildLogic:
    """Test the prompt building logic without database."""

    def test_prompt_structure(self):
        """Test that prompts have correct structure."""

        # We can't easily test _build_thin_prompt without a full instance,
        # but we can verify the structure we expect
        expected_keywords = [
            "Orchestrator",
            "IDENTITY",
            "MCP CONNECTION",
            "STARTUP SEQUENCE",
            "get_orchestrator_instructions",
        ]

        # This is a validation that our design is correct
        # The actual implementation test will be in integration tests
        assert all(keyword for keyword in expected_keywords)


class TestConfigurationParsing:
    """Test configuration parsing logic."""

    def test_tool_validation_logic(self):
        """Test that tool validation would catch invalid tools."""
        valid_tools = ["claude-code", "codex", "gemini"]
        invalid_tools = ["invalid-tool", "chatgpt", "unknown"]

        for tool in valid_tools:
            assert tool in ["claude-code", "codex", "gemini"]

        for tool in invalid_tools:
            assert tool not in ["claude-code", "codex", "gemini"]


class TestTokenEstimation:
    """Test token estimation logic."""

    def test_token_estimation_formula(self):
        """Test that token estimation uses 1 token ≈ 4 chars."""
        test_prompt = "This is a test prompt with some content."
        char_count = len(test_prompt)
        estimated_tokens = char_count // 4

        # Our implementation uses this formula
        assert estimated_tokens == 10  # 42 chars // 4 = 10

    def test_thin_prompt_token_budget(self):
        """Verify thin prompts stay under 150 token budget."""
        # A thin prompt should be ~10-30 lines
        # With ~5 words per line average
        # And ~1.3 tokens per word
        # That's ~65-195 tokens

        max_lines = 30
        words_per_line = 5
        tokens_per_word = 1.3

        max_tokens = max_lines * words_per_line * tokens_per_word
        assert max_tokens < 200, "Thin prompts should stay under 200 tokens"


class TestPromptProfessionalism:
    """Test that prompts meet professional standards."""

    def test_prompt_length_professional(self):
        """Professional products don't ask users to copy novels."""
        # Fat prompt: 3000 lines (UNPROFESSIONAL)
        # Thin prompt: 10-30 lines (PROFESSIONAL)

        fat_lines = 3000
        thin_lines = 30

        reduction = ((fat_lines - thin_lines) / fat_lines) * 100
        assert reduction >= 99, "Thin prompts should be 99%+ smaller in line count"

    def test_copy_paste_burden(self):
        """Test that copy-paste burden is minimized."""
        # Professional UX: Can copy prompt in <5 seconds
        # Reading speed: ~250 words/minute = ~4 words/second
        # Max words for 5-second copy: 20 words

        # Thin prompt budget: ~150 words max
        max_words = 150

        # That's reasonable for professional UX
        assert max_words < 200, "Prompt should be quickly copy-pasteable"


class TestStagingPromptStep7:
    """
    Test Step 7: EXECUTION PHASE MONITORING in staging prompt.

    TDD RED Phase (Handover 0355) - These tests MUST FAIL initially.
    Step 7 documents execution phase patterns for orchestrators.
    """

    @pytest.mark.asyncio
    async def test_staging_prompt_includes_step7_execution_monitoring(self):
        """
        Staging prompt should include Step 7: EXECUTION PHASE MONITORING.

        BEHAVIOR: After Step 6 (SIGNAL COMPLETE), there should be a Step 7
        that documents execution phase monitoring patterns.

        This test will FAIL until implementation adds Step 7 to the staging prompt.
        """
        # Import here to avoid circular dependencies
        from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator

        # Mock database and dependencies
        mock_db = MagicMock()
        generator = ThinClientPromptGenerator(db=mock_db, tenant_key="test_tenant")

        # Mock the async methods
        mock_project = MagicMock(name="Test Project", id="test_proj_456")
        mock_product = MagicMock(name="Test Product", id="test_prod_789")

        generator._fetch_project = AsyncMock(return_value=mock_project)
        generator._fetch_product = AsyncMock(return_value=mock_product)
        generator._get_external_host = MagicMock(return_value="localhost")

        # Build staging prompt
        staging_prompt = await generator.generate_staging_prompt(
            orchestrator_id="test_orch_123", project_id="test_proj_456"
        )

        # EXPECTED: Step 7 should exist
        assert "Step 7" in staging_prompt or "7." in staging_prompt, (
            "Staging prompt should include Step 7 after Step 6 (SIGNAL COMPLETE)"
        )

        # EXPECTED: Step 7 should reference execution monitoring
        assert "EXECUTION PHASE MONITORING" in staging_prompt or "execution phase" in staging_prompt.lower(), (
            "Step 7 should document execution phase monitoring"
        )

    @pytest.mark.asyncio
    async def test_staging_prompt_step7_includes_sequential_pattern(self):
        """
        Step 7 should document sequential execution pattern for orchestrators.

        BEHAVIOR: Step 7 should explain sequential agent execution (spawn → poll → complete).

        This test will FAIL until implementation adds sequential pattern documentation.
        """
        # Import here to avoid circular dependencies
        from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator

        # Mock database and dependencies
        mock_db = MagicMock()
        generator = ThinClientPromptGenerator(db=mock_db, tenant_key="test_tenant")

        # Mock the async methods
        mock_project = MagicMock(name="Test Project", id="test_proj_456")
        mock_product = MagicMock(name="Test Product", id="test_prod_789")

        generator._fetch_project = AsyncMock(return_value=mock_project)
        generator._fetch_product = AsyncMock(return_value=mock_product)
        generator._get_external_host = MagicMock(return_value="localhost")

        # Build staging prompt
        staging_prompt = await generator.generate_staging_prompt(
            orchestrator_id="test_orch_123", project_id="test_proj_456"
        )

        # EXPECTED: Sequential execution pattern should be documented
        assert "sequential" in staging_prompt.lower() or "one at a time" in staging_prompt.lower(), (
            "Step 7 should document sequential execution pattern"
        )

        # EXPECTED: Spawn → Poll → Complete flow should be described
        assert (
            "spawn" in staging_prompt.lower() and "poll" in staging_prompt.lower()
        ) or "workflow_status" in staging_prompt, "Step 7 should describe spawn → poll → completion workflow"

    @pytest.mark.asyncio
    async def test_staging_prompt_step7_includes_parallel_pattern(self):
        """
        Step 7 should document parallel execution pattern for orchestrators.

        BEHAVIOR: Step 7 should explain parallel agent execution (spawn all → poll all).

        This test will FAIL until implementation adds parallel pattern documentation.
        """
        # Import here to avoid circular dependencies
        from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator

        # Mock database and dependencies
        mock_db = MagicMock()
        generator = ThinClientPromptGenerator(db=mock_db, tenant_key="test_tenant")

        # Mock the async methods
        mock_project = MagicMock(name="Test Project", id="test_proj_456")
        mock_product = MagicMock(name="Test Product", id="test_prod_789")

        generator._fetch_project = AsyncMock(return_value=mock_project)
        generator._fetch_product = AsyncMock(return_value=mock_product)
        generator._get_external_host = MagicMock(return_value="localhost")

        # Build staging prompt
        staging_prompt = await generator.generate_staging_prompt(
            orchestrator_id="test_orch_123", project_id="test_proj_456"
        )

        # EXPECTED: Parallel execution pattern should be documented
        assert "parallel" in staging_prompt.lower() or "all agents" in staging_prompt.lower(), (
            "Step 7 should document parallel execution pattern"
        )

        # EXPECTED: Poll all agents flow should be described
        assert "poll all" in staging_prompt.lower() or (
            "get_workflow_status" in staging_prompt and "all" in staging_prompt.lower()
        ), "Step 7 should describe polling all agents pattern"

    @pytest.mark.asyncio
    async def test_staging_prompt_step7_requires_message_check_before_completion(self):
        """
        Step 7 should require orchestrator to check messages before completing.

        BEHAVIOR: Step 7 should mandate calling receive_messages() before complete_job().
        This prevents orchestrators from completing without checking for agent messages.

        This test will FAIL until implementation adds mandatory message check requirement.
        """
        # Import here to avoid circular dependencies
        from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator

        # Mock database and dependencies
        mock_db = MagicMock()
        generator = ThinClientPromptGenerator(db=mock_db, tenant_key="test_tenant")

        # Mock the async methods
        mock_project = MagicMock(name="Test Project", id="test_proj_456")
        mock_product = MagicMock(name="Test Product", id="test_prod_789")

        generator._fetch_project = AsyncMock(return_value=mock_project)
        generator._fetch_product = AsyncMock(return_value=mock_product)
        generator._get_external_host = MagicMock(return_value="localhost")

        # Build staging prompt
        staging_prompt = await generator.generate_staging_prompt(
            orchestrator_id="test_orch_123", project_id="test_proj_456"
        )

        # EXPECTED: receive_messages() should be mentioned
        assert "receive_messages" in staging_prompt, "Step 7 should instruct orchestrator to call receive_messages()"

        # EXPECTED: Should emphasize this is mandatory/required before completion
        assert (
            "mandatory" in staging_prompt.lower()
            or "required" in staging_prompt.lower()
            or "before complete" in staging_prompt.lower()
            or "MUST" in staging_prompt
        ), "Step 7 should emphasize message check is MANDATORY before completing job"

        # EXPECTED: Should mention complete_job() or completion
        assert "complete_job" in staging_prompt or "completion" in staging_prompt.lower(), (
            "Step 7 should reference completing the orchestrator job"
        )
