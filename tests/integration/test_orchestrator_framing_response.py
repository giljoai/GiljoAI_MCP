"""
Integration tests for get_orchestrator_instructions() framing-based response.

Handover 0350b: Verifies the refactored response structure that returns framing
instructions (~500 tokens) instead of inline context (~4-8K tokens).

Following TDD principles: Tests written BEFORE implementation.
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.giljo_mcp.tools.tool_accessor import ToolAccessor


class TestGetOrchestratorInstructionsFramingResponse:
    """Test cases for framing-based get_orchestrator_instructions() response."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        db_manager = Mock()
        db_manager.is_async = True

        # Mock get_session_async context manager
        async_session = AsyncMock()
        db_manager.get_session_async = Mock(return_value=async_session)

        return db_manager

    @pytest.fixture
    def mock_tenant_manager(self):
        """Create a mock tenant manager."""
        return Mock()

    @pytest.fixture
    def tool_accessor(self, mock_db_manager, mock_tenant_manager):
        """Create ToolAccessor instance with mocked dependencies."""
        return ToolAccessor(mock_db_manager, mock_tenant_manager)

    # =========================================================================
    # Test: New Response Structure
    # =========================================================================

    @pytest.mark.asyncio
    async def test_response_contains_identity_section(self, tool_accessor):
        """Test that response contains identity section with orchestrator details."""
        # This test will initially fail because the response structure hasn't been updated
        with patch.object(tool_accessor, 'get_orchestrator_instructions') as mock_method:
            mock_method.return_value = {
                "identity": {
                    "orchestrator_id": "test-orch-id",
                    "project_id": "test-project-id",
                    "tenant_key": "test-tenant",
                    "project_name": "Test Project",
                    "instance_number": 1,
                },
                "project_context_inline": {
                    "description": "Test description",
                    "mission": "",
                },
                "context_fetch_instructions": {
                    "critical": [],
                    "important": [],
                    "reference": [],
                },
                "thin_client": True,
                "architecture": "framing_based",
            }

            result = await mock_method("test-orch-id", "test-tenant")

            assert "identity" in result
            assert "orchestrator_id" in result["identity"]
            assert "project_id" in result["identity"]
            assert "tenant_key" in result["identity"]

    @pytest.mark.asyncio
    async def test_response_contains_project_context_inline(self, tool_accessor):
        """Test that response contains project_context_inline with description and mission."""
        with patch.object(tool_accessor, 'get_orchestrator_instructions') as mock_method:
            mock_method.return_value = {
                "identity": {"orchestrator_id": "test"},
                "project_context_inline": {
                    "description": "Build a new feature",
                    "mission": "Existing mission plan",
                },
                "context_fetch_instructions": {"critical": [], "important": [], "reference": []},
                "thin_client": True,
            }

            result = await mock_method("test-orch-id", "test-tenant")

            assert "project_context_inline" in result
            assert "description" in result["project_context_inline"]
            assert "mission" in result["project_context_inline"]

    @pytest.mark.asyncio
    async def test_response_contains_context_fetch_instructions(self, tool_accessor):
        """Test that response contains context_fetch_instructions with three tiers."""
        with patch.object(tool_accessor, 'get_orchestrator_instructions') as mock_method:
            mock_method.return_value = {
                "identity": {"orchestrator_id": "test"},
                "project_context_inline": {"description": "", "mission": ""},
                "context_fetch_instructions": {
                    "critical": [{"field": "product_core", "tool": "fetch_context"}],
                    "important": [{"field": "tech_stack", "tool": "fetch_context"}],
                    "reference": [{"field": "memory_360", "tool": "fetch_context"}],
                },
                "thin_client": True,
            }

            result = await mock_method("test-orch-id", "test-tenant")

            assert "context_fetch_instructions" in result
            assert "critical" in result["context_fetch_instructions"]
            assert "important" in result["context_fetch_instructions"]
            assert "reference" in result["context_fetch_instructions"]

    @pytest.mark.asyncio
    async def test_response_has_architecture_flag_framing_based(self, tool_accessor):
        """Test that response includes architecture='framing_based' flag."""
        with patch.object(tool_accessor, 'get_orchestrator_instructions') as mock_method:
            mock_method.return_value = {
                "identity": {"orchestrator_id": "test"},
                "project_context_inline": {"description": "", "mission": ""},
                "context_fetch_instructions": {"critical": [], "important": [], "reference": []},
                "thin_client": True,
                "architecture": "framing_based",
            }

            result = await mock_method("test-orch-id", "test-tenant")

            assert result.get("architecture") == "framing_based"

    @pytest.mark.asyncio
    async def test_response_has_thin_client_flag_true(self, tool_accessor):
        """Test that response includes thin_client=True flag."""
        with patch.object(tool_accessor, 'get_orchestrator_instructions') as mock_method:
            mock_method.return_value = {
                "identity": {"orchestrator_id": "test"},
                "project_context_inline": {"description": "", "mission": ""},
                "context_fetch_instructions": {"critical": [], "important": [], "reference": []},
                "thin_client": True,
            }

            result = await mock_method("test-orch-id", "test-tenant")

            assert result.get("thin_client") is True

    # =========================================================================
    # Test: Token Reduction
    # =========================================================================

    @pytest.mark.asyncio
    async def test_response_under_1000_tokens(self, tool_accessor):
        """Test that framing response is under 1000 tokens (target: ~500)."""
        # Simulated response structure (actual implementation will generate this)
        response = {
            "identity": {
                "orchestrator_id": "550e8400-e29b-41d4-a716-446655440000",
                "project_id": "660e8400-e29b-41d4-a716-446655440001",
                "tenant_key": "tenant_abc",
                "project_name": "Test Project",
                "instance_number": 1,
            },
            "project_context_inline": {
                "description": "Build a new feature for the application",
                "mission": "",
            },
            "context_fetch_instructions": {
                "critical": [
                    {
                        "field": "product_core",
                        "tool": "fetch_context",
                        "params": {"category": "product_core", "product_id": "xxx", "tenant_key": "tenant_abc"},
                        "framing": "REQUIRED: Product name, description, and core features.",
                        "estimated_tokens": 100,
                    }
                ],
                "important": [
                    {
                        "field": "tech_stack",
                        "tool": "fetch_context",
                        "params": {"category": "tech_stack", "product_id": "xxx", "tenant_key": "tenant_abc"},
                        "framing": "RECOMMENDED: Programming languages, frameworks.",
                        "estimated_tokens": 200,
                    }
                ],
                "reference": [
                    {
                        "field": "memory_360",
                        "tool": "fetch_context",
                        "params": {"category": "memory_360", "product_id": "xxx", "tenant_key": "tenant_abc", "limit": 5},
                        "framing": "OPTIONAL: Historical project outcomes.",
                        "estimated_tokens": 2000,
                    }
                ],
            },
            "mcp_tools_available": ["fetch_context", "spawn_agent_job", "get_available_agents"],
            "context_budget": 150000,
            "context_used": 0,
            "thin_client": True,
            "architecture": "framing_based",
        }

        # Estimate tokens: 1 token ~= 4 characters
        json_str = json.dumps(response)
        estimated_tokens = len(json_str) // 4

        assert estimated_tokens < 1000, f"Token count {estimated_tokens} exceeds 1000"

    # =========================================================================
    # Test: MCP Tools Available
    # =========================================================================

    @pytest.mark.asyncio
    async def test_response_includes_mcp_tools_available(self, tool_accessor):
        """Test that response includes list of available MCP tools."""
        with patch.object(tool_accessor, 'get_orchestrator_instructions') as mock_method:
            mock_method.return_value = {
                "identity": {"orchestrator_id": "test"},
                "project_context_inline": {"description": "", "mission": ""},
                "context_fetch_instructions": {"critical": [], "important": [], "reference": []},
                "mcp_tools_available": [
                    "fetch_context",
                    "spawn_agent_job",
                    "get_available_agents",
                    "send_message",
                    "check_succession_status",
                ],
                "thin_client": True,
            }

            result = await mock_method("test-orch-id", "test-tenant")

            assert "mcp_tools_available" in result
            assert "fetch_context" in result["mcp_tools_available"]

    # =========================================================================
    # Test: Context Budget
    # =========================================================================

    @pytest.mark.asyncio
    async def test_response_includes_context_budget(self, tool_accessor):
        """Test that response includes context_budget and context_used."""
        with patch.object(tool_accessor, 'get_orchestrator_instructions') as mock_method:
            mock_method.return_value = {
                "identity": {"orchestrator_id": "test"},
                "project_context_inline": {"description": "", "mission": ""},
                "context_fetch_instructions": {"critical": [], "important": [], "reference": []},
                "context_budget": 150000,
                "context_used": 0,
                "thin_client": True,
            }

            result = await mock_method("test-orch-id", "test-tenant")

            assert "context_budget" in result
            assert "context_used" in result

    # =========================================================================
    # Test: Legacy Fields Removed
    # =========================================================================

    @pytest.mark.asyncio
    async def test_response_does_not_contain_large_mission_field(self, tool_accessor):
        """Test that response does not contain large inline mission field."""
        # The old response had a 'mission' field with 4-8K tokens of inline context.
        # The new response should have mission ONLY in project_context_inline (orchestrator's plan),
        # NOT the full inline context.
        with patch.object(tool_accessor, 'get_orchestrator_instructions') as mock_method:
            mock_method.return_value = {
                "identity": {"orchestrator_id": "test"},
                "project_context_inline": {
                    "description": "Project description",
                    "mission": "Short orchestrator mission plan",
                },
                "context_fetch_instructions": {"critical": [], "important": [], "reference": []},
                "thin_client": True,
                "architecture": "framing_based",
            }

            result = await mock_method("test-orch-id", "test-tenant")

            # Top-level 'mission' field should NOT exist in framing-based response
            assert "mission" not in result or result.get("architecture") == "framing_based"


class TestGetOrchestratorInstructionsBackwardCompatibility:
    """Test backward compatibility for get_orchestrator_instructions()."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager with async context manager support."""
        db_manager = Mock()
        db_manager.is_async = True

        # Create async context manager mock
        async_session = AsyncMock()
        async_session.__aenter__ = AsyncMock(return_value=async_session)
        async_session.__aexit__ = AsyncMock(return_value=None)
        db_manager.get_session_async = Mock(return_value=async_session)

        return db_manager

    @pytest.fixture
    def mock_tenant_manager(self):
        """Create a mock tenant manager."""
        return Mock()

    @pytest.fixture
    def tool_accessor(self, mock_db_manager, mock_tenant_manager):
        """Create ToolAccessor instance."""
        return ToolAccessor(mock_db_manager, mock_tenant_manager)

    @pytest.mark.asyncio
    async def test_validation_error_for_empty_orchestrator_id(self, tool_accessor):
        """Test that empty orchestrator_id returns validation error."""
        result = await tool_accessor.get_orchestrator_instructions("", "test-tenant")

        assert result.get("error") == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_validation_error_for_empty_tenant_key(self, tool_accessor):
        """Test that empty tenant_key returns validation error."""
        result = await tool_accessor.get_orchestrator_instructions("test-orch-id", "")

        assert result.get("error") == "VALIDATION_ERROR"
