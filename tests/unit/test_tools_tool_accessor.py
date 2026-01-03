"""
Unit tests for ToolAccessor (public MCP-facing surface).

This suite intentionally tests behavior that should remain stable:
- ToolAccessor wiring (db_manager / tenant_manager)
- Download helpers require `_api_key` (MCP HTTP injects it)
- Legacy download flow tools are not present anymore
"""

import pytest

from src.giljo_mcp.tools.tool_accessor import ToolAccessor


def test_tool_accessor_initialization(mock_db_manager, mock_tenant_manager):
    db_manager, _session = mock_db_manager
    accessor = ToolAccessor(db_manager=db_manager, tenant_manager=mock_tenant_manager)

    assert accessor.db_manager is db_manager
    assert accessor.tenant_manager is mock_tenant_manager


def test_legacy_download_flow_tools_removed(mock_db_manager, mock_tenant_manager):
    db_manager, _session = mock_db_manager
    accessor = ToolAccessor(db_manager=db_manager, tenant_manager=mock_tenant_manager)

    assert not hasattr(accessor, "gil_fetch")
    assert not hasattr(accessor, "gil_import_productagents")
    assert not hasattr(accessor, "gil_import_personalagents")
    assert not hasattr(accessor, "gil_update_agents")


@pytest.mark.asyncio
async def test_setup_slash_commands_requires_api_key(mock_db_manager, mock_tenant_manager):
    db_manager, _session = mock_db_manager
    mock_tenant_manager.get_current_tenant.return_value = "tk_" + ("A" * 32)

    accessor = ToolAccessor(db_manager=db_manager, tenant_manager=mock_tenant_manager)
    result = await accessor.setup_slash_commands(_api_key=None, _server_url="http://localhost:7272")

    assert result["success"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_get_agent_download_url_requires_api_key(mock_db_manager, mock_tenant_manager):
    db_manager, _session = mock_db_manager
    mock_tenant_manager.get_current_tenant.return_value = "tk_" + ("A" * 32)

    accessor = ToolAccessor(db_manager=db_manager, tenant_manager=mock_tenant_manager)
    result = await accessor.get_agent_download_url(_api_key=None, _server_url="http://localhost:7272")

    assert result["success"] is False
    assert "error" in result
