"""
Test suite for chapter-based orchestrator protocol (Handover 0415).

TDD RED PHASE - These tests MUST fail initially because _build_orchestrator_protocol
doesn't exist yet.

Tests verify:
1. Protocol returns 5 chapters with correct keys
2. CLI mode vs multi-terminal mode content differences
3. Visual box formatting present
4. Navigation hints included
5. Integration with get_orchestrator_instructions()
6. Token count reduction (<150 tokens for staging prompt)
"""

import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Fix import path for giljo_mcp -> src.giljo_mcp in test environment
if "giljo_mcp" not in sys.modules:
    import src.giljo_mcp as giljo_mcp
    sys.modules["giljo_mcp"] = giljo_mcp
    # Map common submodules that get imported
    for submodule in ["config_manager", "database", "mission_planner", "models", "models.agent_identity"]:
        src_key = f"src.giljo_mcp.{submodule}"
        dst_key = f"giljo_mcp.{submodule}"
        if src_key in sys.modules:
            sys.modules[dst_key] = sys.modules[src_key]

# This import will fail - function doesn't exist yet (TDD RED phase)
try:
    from src.giljo_mcp.tools.orchestration import _build_orchestrator_protocol
    PROTOCOL_FUNCTION_EXISTS = True
except ImportError:
    PROTOCOL_FUNCTION_EXISTS = False
    _build_orchestrator_protocol = None

# For integration tests
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator


class TestOrchestratorProtocolChapters:
    """Test chapter-based protocol structure."""

    @pytest.mark.skipif(not PROTOCOL_FUNCTION_EXISTS, reason="Function not implemented yet (TDD RED)")
    def test_build_orchestrator_protocol_returns_5_chapters(self):
        """Verify protocol returns dict with exactly 5 chapter keys."""
        protocol = _build_orchestrator_protocol(
            cli_mode=True,
            context_budget=180000,
            project_id="proj-123",
            orchestrator_id="orch-456",
            tenant_key="tenant-abc"
        )

        assert isinstance(protocol, dict), "Protocol must be a dictionary"

        expected_chapters = {
            "ch1_your_mission",
            "ch2_startup_sequence",
            "ch3_agent_spawning_rules",
            "ch4_error_handling",
            "ch5_reference"
        }

        actual_chapters = set(protocol.keys()) - {"navigation_hint"}
        assert actual_chapters == expected_chapters, (
            f"Expected exactly 5 chapters: {expected_chapters}, "
            f"got: {actual_chapters}"
        )

    @pytest.mark.skipif(not PROTOCOL_FUNCTION_EXISTS, reason="Function not implemented yet (TDD RED)")
    def test_build_orchestrator_protocol_cli_mode_content(self):
        """Verify CH3 contains CLI mode specific instructions when cli_mode=True."""
        protocol = _build_orchestrator_protocol(
            cli_mode=True,
            context_budget=180000,
            project_id="proj-123",
            orchestrator_id="orch-456",
            tenant_key="tenant-abc"
        )

        ch3_content = protocol.get("ch3_agent_spawning_rules", "")

        # CLI mode indicators
        assert "CLI MODE" in ch3_content or "cli_mode=True" in ch3_content, (
            "CH3 must indicate CLI mode when cli_mode=True"
        )
        assert "spawn_agent_job" in ch3_content, (
            "CH3 must mention spawn_agent_job MCP tool for CLI mode"
        )
        assert "thin prompt" in ch3_content.lower(), (
            "CH3 must reference thin prompt approach for CLI mode"
        )

    @pytest.mark.skipif(not PROTOCOL_FUNCTION_EXISTS, reason="Function not implemented yet (TDD RED)")
    def test_build_orchestrator_protocol_multi_terminal_mode_content(self):
        """Verify CH3 contains multi-terminal mode content when cli_mode=False."""
        protocol = _build_orchestrator_protocol(
            cli_mode=False,
            context_budget=180000,
            project_id="proj-123",
            orchestrator_id="orch-456",
            tenant_key="tenant-abc"
        )

        ch3_content = protocol.get("ch3_agent_spawning_rules", "")

        # Multi-terminal mode indicators
        assert "MULTI-TERMINAL" in ch3_content or "cli_mode=False" in ch3_content, (
            "CH3 must indicate multi-terminal mode when cli_mode=False"
        )
        assert "CCW" in ch3_content or "Claude Code Web" in ch3_content, (
            "CH3 must mention CCW for multi-terminal mode"
        )
        assert "spawn_agent_job" in ch3_content, (
            "CH3 must still mention spawn_agent_job tool"
        )

    @pytest.mark.skipif(not PROTOCOL_FUNCTION_EXISTS, reason="Function not implemented yet (TDD RED)")
    def test_chapter_structure_has_visual_boxes(self):
        """Verify chapters use ╔═══╗ box formatting for visual clarity."""
        protocol = _build_orchestrator_protocol(
            cli_mode=True,
            context_budget=180000,
            project_id="proj-123",
            orchestrator_id="orch-456",
            tenant_key="tenant-abc"
        )

        # Check at least one chapter has box formatting
        has_box_formatting = False
        box_chars = ["╔", "═", "╗", "║", "╚", "╝"]

        for chapter_key, chapter_content in protocol.items():
            if chapter_key == "navigation_hint":
                continue

            for char in box_chars:
                if char in str(chapter_content):
                    has_box_formatting = True
                    break

            if has_box_formatting:
                break

        assert has_box_formatting, (
            "At least one chapter must use box formatting (╔═══╗) for visual structure"
        )

    @pytest.mark.skipif(not PROTOCOL_FUNCTION_EXISTS, reason="Function not implemented yet (TDD RED)")
    def test_chapter_navigation_hint_present(self):
        """Verify navigation_hint key exists in protocol."""
        protocol = _build_orchestrator_protocol(
            cli_mode=True,
            context_budget=180000,
            project_id="proj-123",
            orchestrator_id="orch-456",
            tenant_key="tenant-abc"
        )

        assert "navigation_hint" in protocol, "Protocol must include navigation_hint"

        nav_hint = protocol["navigation_hint"]
        assert isinstance(nav_hint, str), "navigation_hint must be a string"
        assert len(nav_hint) > 0, "navigation_hint must not be empty"

        # Should mention chapter navigation
        assert any(word in nav_hint.lower() for word in ["chapter", "ch1", "ch2"]), (
            "navigation_hint should mention chapters"
        )

    @pytest.mark.skipif(not PROTOCOL_FUNCTION_EXISTS, reason="Function not implemented yet (TDD RED)")
    def test_include_implementation_reference_flag(self):
        """Verify include_implementation_reference controls CH5 content."""
        # With implementation reference
        protocol_with_ref = _build_orchestrator_protocol(
            cli_mode=True,
            context_budget=180000,
            project_id="proj-123",
            orchestrator_id="orch-456",
            tenant_key="tenant-abc",
            include_implementation_reference=True
        )

        # Without implementation reference
        protocol_without_ref = _build_orchestrator_protocol(
            cli_mode=True,
            context_budget=180000,
            project_id="proj-123",
            orchestrator_id="orch-456",
            tenant_key="tenant-abc",
            include_implementation_reference=False
        )

        ch5_with = protocol_with_ref.get("ch5_reference", "")
        ch5_without = protocol_without_ref.get("ch5_reference", "")

        # CH5 should exist in both cases but have different content
        assert len(ch5_with) > len(ch5_without), (
            "CH5 with implementation reference should have more content"
        )


class TestOrchestratorProtocolIntegration:
    """Integration tests for protocol in get_orchestrator_instructions()."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(not PROTOCOL_FUNCTION_EXISTS, reason="Function not implemented yet (TDD RED)")
    async def test_orchestrator_protocol_in_instructions_response(self):
        """Verify get_orchestrator_instructions() returns orchestrator_protocol field."""
        from src.giljo_mcp.tools.orchestration import get_orchestrator_instructions, _build_orchestrator_protocol

        # Simply verify that _build_orchestrator_protocol is being called and its result
        # is included in the response. We don't need to mock the entire database stack.

        # Mock the database manager and all database-related operations
        mock_db = AsyncMock()

        # Mock AgentExecution and AgentJob lookups with spec_set to ensure attributes are strings
        mock_agent_execution = MagicMock()
        mock_agent_execution.agent_id = "agent-123"
        mock_agent_execution.job_id = "orch-123"
        mock_agent_execution.tenant_key = "tenant-abc"
        mock_agent_execution.context_budget = 180000
        mock_agent_execution.context_used = 0

        mock_agent_job = MagicMock()
        mock_agent_job.id = "orch-123"
        mock_agent_job.project_id = "proj-456"
        mock_agent_job.tenant_key = "tenant-abc"
        mock_agent_job.tool_type = "claude-code"

        mock_project = MagicMock()
        mock_project.id = "proj-456"
        mock_project.name = "Test Project"
        mock_project.description = "Test description"
        mock_project.product_id = "prod-789"
        mock_project.tenant_key = "tenant-abc"

        mock_product = MagicMock()
        mock_product.id = "prod-789"
        mock_product.name = "Test Product"
        mock_product.tenant_key = "tenant-abc"

        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.tenant_key = "tenant-abc"
        mock_user.field_priority_config = None
        mock_user.depth_config = None

        # Setup query results
        async def mock_execute(query):
            result = MagicMock()
            result.scalar_one_or_none = MagicMock()
            result.scalars = MagicMock(return_value=MagicMock(
                first=MagicMock(return_value=None),
                all=MagicMock(return_value=[])
            ))

            # Return appropriate mock based on query type
            query_str = str(query)
            if "AgentExecution" in query_str or "agent_executions" in query_str:
                result.scalar_one_or_none.return_value = mock_agent_execution
            elif "AgentJob" in query_str or "agent_jobs" in query_str:
                result.scalar_one_or_none.return_value = mock_agent_job
            elif "Project" in query_str or "projects" in query_str:
                result.scalar_one_or_none.return_value = mock_project
            elif "Product" in query_str or "products" in query_str:
                result.scalar_one_or_none.return_value = mock_product
            elif "User" in query_str or "users" in query_str:
                result.scalar_one_or_none.return_value = mock_user

            return result

        mock_db.execute = mock_execute

        # Create a mock DatabaseManager instance
        mock_db_manager = MagicMock()
        mock_db_manager.get_session_async = MagicMock(
            return_value=MagicMock(
                __aenter__=AsyncMock(return_value=mock_db),
                __aexit__=AsyncMock()
            )
        )

        # Call function with db_manager
        result = await get_orchestrator_instructions(
            agent_id="agent-123",
            tenant_key="tenant-abc",
            db_manager=mock_db_manager
        )

        # Verify orchestrator_protocol exists in response
        assert "orchestrator_protocol" in result, (
            "get_orchestrator_instructions() must return orchestrator_protocol field"
        )

        protocol = result["orchestrator_protocol"]
        assert isinstance(protocol, dict), "orchestrator_protocol must be a dict"

        # Verify chapter keys present
        expected_chapters = {
            "ch1_your_mission",
            "ch2_startup_sequence",
            "ch3_agent_spawning_rules",
            "ch4_error_handling",
            "ch5_reference"
        }

        actual_chapters = set(protocol.keys()) - {"navigation_hint"}
        assert actual_chapters == expected_chapters, (
            f"orchestrator_protocol must contain all 5 chapters: {expected_chapters}"
        )


class TestStagingPromptTokenReduction:
    """Test token count reduction in staging prompt."""

    @pytest.mark.asyncio
    async def test_staging_prompt_token_count_under_150(self):
        """Verify generate_staging_prompt() produces <150 tokens."""
        # Mock database session with proper async behavior
        mock_db = AsyncMock()

        # Mock the db.execute call for AgentExecution query
        mock_execution = MagicMock(agent_id="agent-123")
        mock_exec_result = MagicMock()
        mock_exec_result.scalars.return_value.first.return_value = mock_execution
        mock_db.execute = AsyncMock(return_value=mock_exec_result)

        generator = ThinClientPromptGenerator(db=mock_db, tenant_key="tenant-abc")

        # Mock _fetch_project to return a project object
        mock_project = MagicMock(
            id="proj-456",
            product_id="prod-789",
            tenant_key="tenant-abc"
        )

        # Mock _fetch_product to return a product object
        mock_product = MagicMock(
            id="prod-789",
            tenant_key="tenant-abc"
        )

        # Mock get_config to return a mock config
        mock_config = MagicMock()
        mock_config.api.host = "localhost"
        mock_config.api.port = 7272

        with patch.object(generator, "_fetch_project", return_value=mock_project), \
             patch.object(generator, "_fetch_product", return_value=mock_product), \
             patch("src.giljo_mcp.thin_prompt_generator.get_config", return_value=mock_config):

            # Generate staging prompt
            staging_prompt = await generator.generate_staging_prompt(
                orchestrator_id="orch-123",
                project_id="proj-456",
                claude_code_mode=True
            )

            # Rough token estimate: 1 token ≈ 4 characters
            char_count = len(staging_prompt)
            estimated_tokens = char_count / 4

            assert estimated_tokens < 150, (
                f"Staging prompt should be <150 tokens, "
                f"estimated {estimated_tokens:.0f} tokens ({char_count} chars)"
            )

            # Verify key thin-client elements present
            assert "get_orchestrator_instructions" in staging_prompt, (
                "Staging prompt must reference get_orchestrator_instructions MCP tool"
            )
            assert "orchestrator_protocol" in staging_prompt.lower() or "chapter" in staging_prompt.lower(), (
                "Staging prompt must mention orchestrator_protocol or chapters"
            )

    @pytest.mark.asyncio
    async def test_staging_prompt_removes_inline_tasks(self):
        """Verify staging prompt no longer contains inline task list."""
        # Mock database session with proper async behavior
        mock_db = AsyncMock()

        # Mock the db.execute call for AgentExecution query
        mock_execution = MagicMock(agent_id="agent-123")
        mock_exec_result = MagicMock()
        mock_exec_result.scalars.return_value.first.return_value = mock_execution
        mock_db.execute = AsyncMock(return_value=mock_exec_result)

        generator = ThinClientPromptGenerator(db=mock_db, tenant_key="tenant-abc")

        # Mock _fetch_project to return a project object
        mock_project = MagicMock(
            id="proj-456",
            product_id="prod-789",
            tenant_key="tenant-abc"
        )

        # Mock _fetch_product to return a product object
        mock_product = MagicMock(
            id="prod-789",
            tenant_key="tenant-abc"
        )

        # Mock get_config to return a mock config
        mock_config = MagicMock()
        mock_config.api.host = "localhost"
        mock_config.api.port = 7272

        with patch.object(generator, "_fetch_project", return_value=mock_project), \
             patch.object(generator, "_fetch_product", return_value=mock_product), \
             patch("src.giljo_mcp.thin_prompt_generator.get_config", return_value=mock_config):

            staging_prompt = await generator.generate_staging_prompt(
                orchestrator_id="orch-123",
                project_id="proj-456",
                claude_code_mode=True
            )

            # These should NOT appear in thin-client staging prompt
            inline_task_indicators = [
                "TASK 1:",
                "TASK 2:",
                "TASK 3:",
                "Verify identity",
                "Health check",
                "Environment understanding",
                "[ ] Mark complete"
            ]

            for indicator in inline_task_indicators:
                assert indicator not in staging_prompt, (
                    f"Staging prompt should not contain inline task '{indicator}' - "
                    f"tasks should be in orchestrator_protocol chapters"
                )


class TestChapterContentQuality:
    """Test content quality and completeness of chapters."""

    @pytest.mark.skipif(not PROTOCOL_FUNCTION_EXISTS, reason="Function not implemented yet (TDD RED)")
    def test_ch1_contains_mission_clarity(self):
        """Verify CH1 (Your Mission) provides clear purpose."""
        protocol = _build_orchestrator_protocol(
            cli_mode=True,
            context_budget=180000,
            project_id="proj-123",
            orchestrator_id="orch-456",
            tenant_key="tenant-abc"
        )

        ch1 = protocol.get("ch1_your_mission", "")

        # Should mention orchestrator role
        assert any(word in ch1.lower() for word in ["orchestrator", "coordinate", "manage"]), (
            "CH1 should clarify orchestrator role"
        )

    @pytest.mark.skipif(not PROTOCOL_FUNCTION_EXISTS, reason="Function not implemented yet (TDD RED)")
    def test_ch2_contains_startup_sequence(self):
        """Verify CH2 (Startup Sequence) lists initialization steps."""
        protocol = _build_orchestrator_protocol(
            cli_mode=True,
            context_budget=180000,
            project_id="proj-123",
            orchestrator_id="orch-456",
            tenant_key="tenant-abc"
        )

        ch2 = protocol.get("ch2_startup_sequence", "")

        # Should mention key startup actions
        startup_keywords = ["identity", "health", "context", "agent"]
        matches = sum(1 for keyword in startup_keywords if keyword in ch2.lower())

        assert matches >= 3, (
            f"CH2 should mention at least 3 startup concepts, found {matches}"
        )

    @pytest.mark.skipif(not PROTOCOL_FUNCTION_EXISTS, reason="Function not implemented yet (TDD RED)")
    def test_ch4_contains_error_handling(self):
        """Verify CH4 (Error Handling) provides guidance."""
        protocol = _build_orchestrator_protocol(
            cli_mode=True,
            context_budget=180000,
            project_id="proj-123",
            orchestrator_id="orch-456",
            tenant_key="tenant-abc"
        )

        ch4 = protocol.get("ch4_error_handling", "")

        # Should mention error handling concepts
        assert any(word in ch4.lower() for word in ["error", "fail", "retry", "recover"]), (
            "CH4 should contain error handling guidance"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
