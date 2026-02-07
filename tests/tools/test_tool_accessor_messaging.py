"""
Tests for ToolAccessor message methods to verify tenant_key parameter handling.

Handover 0378 Bug 1: Fix receive_messages and list_messages to pass tenant_key.
"""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio

from src.giljo_mcp.tools.tool_accessor import ToolAccessor


@pytest_asyncio.fixture
async def tenant_key():
    """Generate test tenant key."""
    return f"tk_test_{uuid4().hex[:16]}"


@pytest_asyncio.fixture
async def tool_accessor(db_manager, db_session, tenant_key):
    """Create ToolAccessor instance with test session."""
    from src.giljo_mcp.tenant import TenantManager

    tenant_manager = TenantManager()
    tenant_manager.get_current_tenant = lambda: tenant_key

    accessor = ToolAccessor(db_manager, tenant_manager, test_session=db_session)

    # Mock the MessageService to verify calls
    accessor._message_service = AsyncMock()
    accessor._message_service.receive_messages = AsyncMock(return_value={"messages": []})
    accessor._message_service.list_messages = AsyncMock(return_value={"messages": []})

    return accessor


@pytest.mark.asyncio
async def test_receive_messages_with_tenant_key(tool_accessor):
    """
    Test that receive_messages accepts tenant_key and passes it to MessageService.

    Handover 0378 Bug 1: MCP tool schema declares tenant_key parameter,
    but ToolAccessor doesn't pass it through.
    """
    # Arrange
    agent_id = "agent-123"
    tenant_key = "tenant-abc"

    # Act
    result = await tool_accessor.receive_messages(agent_id=agent_id, tenant_key=tenant_key, limit=10)

    # Assert
    tool_accessor._message_service.receive_messages.assert_called_once_with(
        agent_id=agent_id, tenant_key=tenant_key, limit=10, exclude_self=True, exclude_progress=True, message_types=None
    )
    assert result == {"messages": []}


@pytest.mark.asyncio
async def test_list_messages_with_tenant_key(tool_accessor):
    """
    Test that list_messages accepts tenant_key and passes it to MessageService.

    Handover 0378 Bug 1: MCP tool schema declares tenant_key parameter,
    but ToolAccessor doesn't pass it through.
    """
    # Arrange
    project_id = "project-123"
    tenant_key = "tenant-abc"

    # Act
    result = await tool_accessor.list_messages(project_id=project_id, tenant_key=tenant_key, limit=20)

    # Assert
    tool_accessor._message_service.list_messages.assert_called_once_with(
        project_id=project_id, tenant_key=tenant_key, status=None, agent_id=None, limit=20
    )
    assert result == {"messages": []}
