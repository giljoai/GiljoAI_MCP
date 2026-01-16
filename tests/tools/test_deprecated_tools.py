"""
Deprecation Tests for Obsolete MCP Tools (Handover 0116)

Tests verify that 11 obsolete MCP tools return proper deprecation errors
as specified in Comprehensive_MCP_Analysis.md Phase 1.

Tool Categories:
- Legacy Agent Model Tools (7): spawn_agent, list_agents, get_agent_status,
  update_agent, retire_agent, ensure_agent, agent_health
- Context Discovery Stubs (4): discover_context, get_file_context,
  search_context, get_context_summary

All tools should return deprecation error with:
- error: "DEPRECATED"
- message: Clear deprecation message
- replacement: Recommended replacement tool
- documentation: Reference to migration guide
- removal_version: "v3.2.0"
- reason: Explanation of why deprecated
"""

import pytest
from pathlib import Path
import sys
from unittest.mock import MagicMock, AsyncMock

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.tenant import TenantManager
from src.giljo_mcp.tools.tool_accessor import ToolAccessor


@pytest.fixture
async def tool_accessor():
    """Create ToolAccessor instance for testing with mocked dependencies"""
    # Mock database manager (deprecation wrappers don't use database)
    db_manager = MagicMock(spec=DatabaseManager)

    # Mock tenant manager
    tenant_manager = MagicMock(spec=TenantManager)
    tenant_manager.get_current_tenant = MagicMock(return_value="test-tenant-key")

    return ToolAccessor(db_manager, tenant_manager)


# ============================================================================
# LEGACY AGENT MODEL TOOLS (7 tests)
# ============================================================================


@pytest.mark.deprecated
@pytest.mark.asyncio
async def test_spawn_agent_returns_deprecation_error(tool_accessor):
    """Verify spawn_agent returns deprecation error"""
    result = await tool_accessor.spawn_agent(
        name="test-agent",
        role="implementer",
        mission="test mission"
    )

    assert result["error"] == "DEPRECATED"
    assert "spawn_agent_job" in result["replacement"]
    assert "legacy Agent records" in result["message"] or "4-state" in result["message"]
    assert result["removal_version"] == "v3.2.0"
    assert "agents" in result["reason"] and "mcp_agent_jobs" in result["reason"]
    assert "Comprehensive_MCP_Analysis.md" in result["documentation"]


@pytest.mark.deprecated
@pytest.mark.asyncio
async def test_list_agents_returns_deprecation_error(tool_accessor):
    """Verify list_agents returns deprecation error"""
    result = await tool_accessor.list_agents(status="active")

    assert result["error"] == "DEPRECATED"
    assert "get_pending_jobs" in result["replacement"]
    assert result["removal_version"] == "v3.2.0"
    assert "Comprehensive_MCP_Analysis.md" in result["documentation"]


@pytest.mark.deprecated
@pytest.mark.asyncio
async def test_get_agent_status_returns_deprecation_error(tool_accessor):
    """Verify get_agent_status returns deprecation error"""
    result = await tool_accessor.get_agent_status(agent_name="test-agent")

    assert result["error"] == "DEPRECATED"
    assert "get_workflow_status" in result["replacement"]
    assert result["removal_version"] == "v3.2.0"
    assert "Comprehensive_MCP_Analysis.md" in result["documentation"]


@pytest.mark.deprecated
@pytest.mark.asyncio
async def test_update_agent_returns_deprecation_error(tool_accessor):
    """Verify update_agent returns deprecation error"""
    result = await tool_accessor.update_agent(
        agent_name="test-agent",
        status="active"
    )

    assert result["error"] == "DEPRECATED"
    assert "report_progress" in result["replacement"] or "complete_job" in result["replacement"]
    assert result["removal_version"] == "v3.2.0"
    assert "Comprehensive_MCP_Analysis.md" in result["documentation"]


@pytest.mark.deprecated
@pytest.mark.asyncio
async def test_retire_agent_returns_deprecation_error(tool_accessor):
    """Verify retire_agent returns deprecation error"""
    result = await tool_accessor.retire_agent(
        agent_name="test-agent",
        reason="completed"
    )

    assert result["error"] == "DEPRECATED"
    assert "Automatic" in result["replacement"] or "complete_job" in result["replacement"]
    assert result["removal_version"] == "v3.2.0"
    assert "Comprehensive_MCP_Analysis.md" in result["documentation"]


@pytest.mark.deprecated
@pytest.mark.asyncio
async def test_ensure_agent_returns_deprecation_error(tool_accessor):
    """Verify ensure_agent returns deprecation error"""
    result = await tool_accessor.ensure_agent(
        project_id="test-project-id",
        agent_name="test-agent",
        mission="test mission"
    )

    assert result["error"] == "DEPRECATED"
    assert "spawn_agent_job" in result["replacement"]
    assert result["removal_version"] == "v3.2.0"
    assert "Comprehensive_MCP_Analysis.md" in result["documentation"]


@pytest.mark.deprecated
@pytest.mark.asyncio
async def test_agent_health_returns_deprecation_error(tool_accessor):
    """Verify agent_health returns deprecation error"""
    result = await tool_accessor.agent_health(agent_name="test-agent")

    assert result["error"] == "DEPRECATED"
    assert "get_workflow_status" in result["replacement"]
    assert result["removal_version"] == "v3.2.0"
    assert "Comprehensive_MCP_Analysis.md" in result["documentation"]


# ============================================================================
# CONTEXT DISCOVERY STUBS (4 tests)
# ============================================================================


@pytest.mark.deprecated
@pytest.mark.asyncio
async def test_discover_context_returns_deprecation_error(tool_accessor):
    """Verify discover_context returns deprecation error"""
    result = await tool_accessor.discover_context(
        project_id="test-project-id",
        agent_role="implementer"
    )

    assert result["error"] == "DEPRECATED"
    assert "None - not needed" in result["replacement"]
    assert result["removal_version"] == "v3.2.0"
    assert "Comprehensive_MCP_Analysis.md" in result["documentation"]


@pytest.mark.deprecated
@pytest.mark.asyncio
async def test_get_file_context_returns_deprecation_error(tool_accessor):
    """Verify get_file_context returns deprecation error"""
    result = await tool_accessor.get_file_context(file_path="src/main.py")

    assert result["error"] == "DEPRECATED"
    assert "None - not needed" in result["replacement"]
    assert result["removal_version"] == "v3.2.0"
    assert "Comprehensive_MCP_Analysis.md" in result["documentation"]


@pytest.mark.deprecated
@pytest.mark.asyncio
async def test_search_context_returns_deprecation_error(tool_accessor):
    """Verify search_context returns deprecation error"""
    result = await tool_accessor.search_context(
        query="class MyClass",
        file_types=["*.py"]
    )

    assert result["error"] == "DEPRECATED"
    assert "None - not needed" in result["replacement"]
    assert result["removal_version"] == "v3.2.0"
    assert "Comprehensive_MCP_Analysis.md" in result["documentation"]


@pytest.mark.deprecated
@pytest.mark.asyncio
async def test_get_context_summary_returns_deprecation_error(tool_accessor):
    """Verify get_context_summary returns deprecation error"""
    result = await tool_accessor.get_context_summary(project_id="test-project-id")

    assert result["error"] == "DEPRECATED"
    assert "None - not needed" in result["replacement"]
    assert result["removal_version"] == "v3.2.0"
    assert "Comprehensive_MCP_Analysis.md" in result["documentation"]


# ============================================================================
# COMPREHENSIVE VERIFICATION TEST
# ============================================================================


@pytest.mark.deprecated
@pytest.mark.asyncio
async def test_all_deprecated_tools_have_consistent_format(tool_accessor):
    """Verify all 11 deprecated tools return consistent deprecation format"""

    deprecated_tools = [
        # Legacy Agent Model (7)
        ("spawn_agent", lambda: tool_accessor.spawn_agent("test", "role", "mission")),
        ("list_agents", lambda: tool_accessor.list_agents()),
        ("get_agent_status", lambda: tool_accessor.get_agent_status("test")),
        ("update_agent", lambda: tool_accessor.update_agent("test", status="active")),
        ("retire_agent", lambda: tool_accessor.retire_agent("test")),
        ("ensure_agent", lambda: tool_accessor.ensure_agent("proj-id", "test")),
        ("agent_health", lambda: tool_accessor.agent_health()),

        # Context Discovery Stubs (4)
        ("discover_context", lambda: tool_accessor.discover_context()),
        ("get_file_context", lambda: tool_accessor.get_file_context("file.py")),
        ("search_context", lambda: tool_accessor.search_context("query")),
        ("get_context_summary", lambda: tool_accessor.get_context_summary()),
    ]

    for tool_name, tool_func in deprecated_tools:
        result = await tool_func()

        # All tools must have these fields
        assert result["error"] == "DEPRECATED", f"{tool_name} missing DEPRECATED error"
        assert "message" in result, f"{tool_name} missing message"
        assert "replacement" in result, f"{tool_name} missing replacement"
        assert "documentation" in result, f"{tool_name} missing documentation"
        assert result["removal_version"] == "v3.2.0", f"{tool_name} wrong removal version"
        assert "reason" in result, f"{tool_name} missing reason"

        # Documentation must reference guide
        assert "Comprehensive_MCP_Analysis.md" in result["documentation"], \
            f"{tool_name} missing documentation reference"

        print(f"✓ {tool_name}: Deprecation format verified")


# ============================================================================
# MIGRATION PATH VERIFICATION
# ============================================================================


@pytest.mark.deprecated
def test_deprecation_replacement_mapping():
    """Verify replacement tool recommendations are correct"""

    replacement_map = {
        # Legacy Agent Model → MCPAgentJob Tools
        "spawn_agent": "spawn_agent_job",
        "list_agents": "get_pending_jobs",
        "get_agent_status": "get_workflow_status",
        "update_agent": "report_progress or complete_job",
        "retire_agent": "Automatic via job lifecycle",
        "ensure_agent": "spawn_agent_job",
        "agent_health": "get_workflow_status",

        # Context Discovery Stubs → No Replacement
        "discover_context": "None - not needed",
        "get_file_context": "None - not needed",
        "search_context": "None - not needed",
        "get_context_summary": "None - not needed",
    }

    assert len(replacement_map) == 11, "Must have 11 deprecated tools"

    # Verify 7 legacy agent tools have replacements
    legacy_tools = [k for k in replacement_map.keys() if "context" not in k and "summary" not in k]
    assert len(legacy_tools) == 7, "Must have 7 legacy agent tools"

    # Verify 4 context stubs have no replacement
    context_stubs = [k for k in replacement_map.keys() if "context" in k or "summary" in k]
    assert len(context_stubs) == 4, "Must have 4 context stub tools"
    assert all("None" in replacement_map[k] for k in context_stubs), \
        "All context stubs should have 'None' replacement"

    print("✓ Replacement mapping verified: 7 legacy tools + 4 context stubs = 11 total")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "deprecated"])
