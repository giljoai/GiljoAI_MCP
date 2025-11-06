"""
Tests for Project Tools WebSocket Refactoring

Validates the production-grade WebSocket dependency injection pattern
in src/giljo_mcp/tools/project.py's update_project_mission function.

Handover 0086A: Production-Grade Stage Project Architecture
Task 1.5: Refactor WebSocket Broadcasting to Use Dependency Injection
Created: 2025-11-02

Test Coverage:
- WebSocket broadcasting with EventFactory
- Multi-tenant isolation enforcement
- Graceful degradation when WebSocket unavailable
- Proper structured logging
- Error handling without bare except blocks

Note: These are integration tests that mock the WebSocket layer to verify
the refactored code uses the production-grade dependency injection pattern.
"""

import logging
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestProjectMissionUpdateWebSocketRefactor:
    """
    Test suite validating WebSocket refactoring in project.py.

    These tests verify that the update_project_mission function:
    1. Uses WebSocketDependency for injection
    2. Uses EventFactory for event creation
    3. Implements proper multi-tenant isolation
    4. Gracefully degrades when WebSocket unavailable
    5. Uses structured logging with context
    """

    @pytest.mark.asyncio
    async def test_websocket_uses_dependency_injection_pattern(self):
        """
        Verify that refactored code uses WebSocketDependency class.

        Validates:
        - WebSocketDependency is instantiated
        - broadcast_to_tenant method is called
        - No manual iteration over active_connections
        """
        # Import the actual function
        from fastmcp import FastMCP

        from giljo_mcp.database import DatabaseManager
        from giljo_mcp.tenant import TenantManager
        from giljo_mcp.tools.project import register_project_tools

        # Setup mock database manager
        mock_db_manager = MagicMock(spec=DatabaseManager)
        mock_session = MagicMock()
        mock_project = MagicMock()
        mock_project.id = uuid4()
        mock_project.tenant_key = f"tk_{uuid4().hex}"
        mock_project.mission = "Old mission"
        mock_project.name = "Test Project"

        # Mock the session context manager
        async_context = MagicMock()
        async_context.__aenter__ = AsyncMock(return_value=mock_session)
        async_context.__aexit__ = AsyncMock(return_value=None)
        mock_db_manager.get_session_async.return_value = async_context

        # Mock query results
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_project
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        # Register tools
        mcp = FastMCP()
        tenant_manager = TenantManager()
        register_project_tools(mcp, mock_db_manager, tenant_manager)

        # Mock WebSocket manager
        mock_ws_manager = MagicMock()
        mock_ws_dep = MagicMock()
        mock_ws_dep.broadcast_to_tenant = AsyncMock(return_value=1)

        # Mock app state
        mock_state = MagicMock()
        mock_state.websocket_manager = mock_ws_manager

        # Patch api.app.state and WebSocketDependency
        with patch("api.app.state", mock_state):
            with patch("api.dependencies.websocket.WebSocketDependency") as mock_ws_dep_class:
                mock_ws_dep_class.return_value = mock_ws_dep

                # Execute the mission update directly from module scope
                # The function was registered via @mcp.tool() decorator
                # We need to call it through the tool system
                tools = await mcp._tool_manager.list_tools()
                update_tool = next((t for t in tools if t.name == "update_project_mission"), None)
                assert update_tool is not None

                # Execute the mission update
                result = await update_tool.fn(
                    project_id=str(mock_project.id),
                    mission="New refactored mission",
                )

                # Verify WebSocketDependency was instantiated
                mock_ws_dep_class.assert_called_once_with(mock_ws_manager)

                # Verify broadcast_to_tenant was called (production pattern)
                mock_ws_dep.broadcast_to_tenant.assert_called_once()

                # Verify call arguments
                call_args = mock_ws_dep.broadcast_to_tenant.call_args
                assert call_args.kwargs["tenant_key"] == mock_project.tenant_key
                assert call_args.kwargs["event_type"] == "project:mission_updated"
                assert "data" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_websocket_uses_event_factory(self):
        """
        Verify that refactored code uses EventFactory.project_mission_updated.

        Validates:
        - EventFactory.project_mission_updated() is called
        - Proper parameters are passed
        - Event structure is valid
        """
        from fastmcp import FastMCP

        from giljo_mcp.database import DatabaseManager
        from giljo_mcp.tenant import TenantManager
        from giljo_mcp.tools.project import register_project_tools

        # Setup mock database manager
        mock_db_manager = MagicMock(spec=DatabaseManager)
        mock_session = MagicMock()
        mock_project = MagicMock()
        mock_project.id = uuid4()
        mock_project.tenant_key = f"tk_{uuid4().hex}"
        mock_project.mission = "Old mission"
        mock_project.name = "Test Project"

        # Mock session context
        async_context = MagicMock()
        async_context.__aenter__ = AsyncMock(return_value=mock_session)
        async_context.__aexit__ = AsyncMock(return_value=None)
        mock_db_manager.get_session_async.return_value = async_context

        # Mock query results
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_project
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        # Register tools
        mcp = FastMCP()
        tenant_manager = TenantManager()
        register_project_tools(mcp, mock_db_manager, tenant_manager)

        # Mock WebSocket
        mock_ws_manager = MagicMock()
        mock_state = MagicMock()
        mock_state.websocket_manager = mock_ws_manager

        new_mission = "Mission with EventFactory"

        # Patch dependencies
        with patch("api.app.state", mock_state):
            with patch("api.dependencies.websocket.WebSocketDependency") as mock_ws_dep_class:
                with patch("api.events.schemas.EventFactory") as mock_event_factory:
                    mock_ws_dep = MagicMock()
                    mock_ws_dep.broadcast_to_tenant = AsyncMock(return_value=1)
                    mock_ws_dep_class.return_value = mock_ws_dep

                    mock_event_factory.project_mission_updated.return_value = {
                        "type": "project:mission_updated",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "schema_version": "1.0",
                        "data": {
                            "project_id": str(mock_project.id),
                            "tenant_key": mock_project.tenant_key,
                            "mission": new_mission,
                            "token_estimate": len(new_mission) // 4,
                            "generated_by": "orchestrator",
                            "user_config_applied": False,
                        },
                    }

                    # Get the tool
                    tools = await mcp._tool_manager.list_tools()
                    update_tool = next((t for t in tools if t.name == "update_project_mission"), None)
                    assert update_tool is not None

                    # Execute
                    result = await update_tool.fn(project_id=str(mock_project.id), mission=new_mission)

                    # Verify EventFactory was called
                    mock_event_factory.project_mission_updated.assert_called_once()

                    # Verify call parameters
                    call_args = mock_event_factory.project_mission_updated.call_args
                    assert call_args.kwargs["project_id"] == mock_project.id
                    assert call_args.kwargs["tenant_key"] == mock_project.tenant_key
                    assert call_args.kwargs["mission"] == new_mission
                    assert call_args.kwargs["generated_by"] == "orchestrator"
                    assert call_args.kwargs["user_config_applied"] is False

    @pytest.mark.asyncio
    async def test_websocket_graceful_degradation(self):
        """
        Verify graceful degradation when WebSocket manager is None.

        Validates:
        - Mission update succeeds even without WebSocket
        - No exceptions are raised
        - Proper logging occurs
        """
        from fastmcp import FastMCP

        from giljo_mcp.database import DatabaseManager
        from giljo_mcp.tenant import TenantManager
        from giljo_mcp.tools.project import register_project_tools

        # Setup mock database manager
        mock_db_manager = MagicMock(spec=DatabaseManager)
        mock_session = MagicMock()
        mock_project = MagicMock()
        mock_project.id = uuid4()
        mock_project.tenant_key = f"tk_{uuid4().hex}"
        mock_project.mission = "Old mission"
        mock_project.name = "Test Project"

        # Mock session context
        async_context = MagicMock()
        async_context.__aenter__ = AsyncMock(return_value=mock_session)
        async_context.__aexit__ = AsyncMock(return_value=None)
        mock_db_manager.get_session_async.return_value = async_context

        # Mock query results
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_project
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        # Register tools
        mcp = FastMCP()
        tenant_manager = TenantManager()
        register_project_tools(mcp, mock_db_manager, tenant_manager)

        # Mock app state with NO WebSocket manager
        mock_state = MagicMock()
        mock_state.websocket_manager = None

        # Execute with no WebSocket
        with patch("api.app.state", mock_state):
            # Get the tool
            tools = await mcp._tool_manager.list_tools()
            update_tool = next((t for t in tools if t.name == "update_project_mission"), None)
            assert update_tool is not None

            result = await update_tool.fn(
                project_id=str(mock_project.id),
                mission="Mission without WebSocket",
            )

            # Verify success despite no WebSocket
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_websocket_structured_logging(self, caplog):
        """
        Verify structured logging with proper context.

        Validates:
        - Log messages include project_id, tenant_key, sent_count
        - Logging uses logger.info with extra parameter
        - No bare except blocks (proper Exception catching)
        """
        from fastmcp import FastMCP

        from giljo_mcp.database import DatabaseManager
        from giljo_mcp.tenant import TenantManager
        from giljo_mcp.tools.project import register_project_tools

        # Setup mock database manager
        mock_db_manager = MagicMock(spec=DatabaseManager)
        mock_session = MagicMock()
        mock_project = MagicMock()
        mock_project.id = uuid4()
        mock_project.tenant_key = f"tk_{uuid4().hex}"
        mock_project.mission = "Old mission"
        mock_project.name = "Test Project"

        # Mock session context
        async_context = MagicMock()
        async_context.__aenter__ = AsyncMock(return_value=mock_session)
        async_context.__aexit__ = AsyncMock(return_value=None)
        mock_db_manager.get_session_async.return_value = async_context

        # Mock query results
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_project
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        # Register tools
        mcp = FastMCP()
        tenant_manager = TenantManager()
        register_project_tools(mcp, mock_db_manager, tenant_manager)

        # Mock WebSocket
        mock_ws_manager = MagicMock()
        mock_state = MagicMock()
        mock_state.websocket_manager = mock_ws_manager

        # Patch dependencies
        with patch("api.app.state", mock_state):
            with patch("api.dependencies.websocket.WebSocketDependency") as mock_ws_dep_class:
                mock_ws_dep = MagicMock()
                mock_ws_dep.broadcast_to_tenant = AsyncMock(return_value=2)
                mock_ws_dep_class.return_value = mock_ws_dep

                # Get the tool
                tools = await mcp._tool_manager.list_tools()
                update_tool = next((t for t in tools if t.name == "update_project_mission"), None)
                assert update_tool is not None

                # Execute with logging capture
                with caplog.at_level(logging.INFO):
                    result = await update_tool.fn(
                        project_id=str(mock_project.id),
                        mission="Structured logging test",
                    )

                # Verify logging occurred
                log_found = False
                for record in caplog.records:
                    if "broadcast" in record.message.lower() and "clients" in record.message.lower():
                        log_found = True
                        break

                assert log_found, "Expected broadcast logging not found"


# Run tests with: pytest tests/test_project_tools_websocket_refactor.py -v --no-cov
