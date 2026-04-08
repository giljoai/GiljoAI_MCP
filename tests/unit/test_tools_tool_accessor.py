# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Unit tests for ToolAccessor (public MCP-facing surface).

This suite intentionally tests behavior that should remain stable:
- ToolAccessor wiring (db_manager / tenant_manager)
- Legacy download flow tools are not present anymore
"""

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
    # Verify removed MCP tools (deprecated)
    assert not hasattr(accessor, "setup_slash_commands")
    assert not hasattr(accessor, "get_agent_download_url")
