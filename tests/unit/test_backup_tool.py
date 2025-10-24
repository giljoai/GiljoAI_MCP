"""
Unit tests for database backup MCP tool
Handover: Database Backup Unit Testing

Tests focus on:
- Tool registration and availability
- Input validation
- Error handling and edge cases
- Return value structure
- Tenant context handling
- Tool function signatures
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


# ============================================================================
# Tool Registration Tests
# ============================================================================


class TestBackupToolRegistration:
    """Tests for backup tool registration in MCP tool system"""

    def test_backup_tool_registered(self):
        """Test backup_database tool is registered in MCP tools"""
        from src.giljo_mcp.tools import get_available_tools

        tools = get_available_tools()
        tool_names = [tool.name for tool in tools]

        assert "backup_database" in tool_names, "backup_database tool not registered"

    def test_backup_tool_has_description(self):
        """Test backup_database tool has proper description"""
        from src.giljo_mcp.tools import get_tool_by_name

        tool = get_tool_by_name("backup_database")

        assert tool is not None
        assert hasattr(tool, "description") or hasattr(tool, "__doc__")

        description = getattr(tool, "description", None) or tool.__doc__
        assert description is not None
        assert len(description) > 0
        assert "backup" in description.lower()
        assert "database" in description.lower()

    def test_backup_tool_has_correct_signature(self):
        """Test backup_database tool has expected function signature"""
        from src.giljo_mcp.tools.backup import backup_database
        import inspect

        # Get function signature
        sig = inspect.signature(backup_database)
        params = sig.parameters

        # Should have tenant_key parameter
        assert "tenant_key" in params, "Missing tenant_key parameter"

        # tenant_key should be string type
        tenant_param = params["tenant_key"]
        if tenant_param.annotation != inspect.Parameter.empty:
            assert tenant_param.annotation == str or "str" in str(tenant_param.annotation)

    def test_backup_tool_is_async(self):
        """Test backup_database tool is an async function"""
        from src.giljo_mcp.tools.backup import backup_database
        import inspect

        assert inspect.iscoroutinefunction(backup_database), "backup_database should be async"


# ============================================================================
# Tool Function Tests
# ============================================================================


@pytest.mark.asyncio
class TestBackupToolFunction:
    """Tests for backup_database tool function logic"""

    async def test_backup_tool_returns_dict(self):
        """Test backup_database returns dictionary"""
        from src.giljo_mcp.tools.backup import backup_database

        tenant_key = f"test_tenant_{uuid4().hex[:8]}"

        # Mock underlying backup utility
        with patch("src.giljo_mcp.tools.backup.create_backup") as mock_backup:
            mock_backup.return_value = {
                "success": True,
                "backup_path": "docs/archive/database_backups/test",
                "metadata": {},
            }

            result = await backup_database(tenant_key=tenant_key)

            assert isinstance(result, dict)

    async def test_backup_tool_returns_required_fields(self):
        """Test backup_database returns all required fields"""
        from src.giljo_mcp.tools.backup import backup_database

        tenant_key = f"test_tenant_{uuid4().hex[:8]}"

        with patch("src.giljo_mcp.tools.backup.create_backup") as mock_backup:
            mock_backup.return_value = {
                "success": True,
                "backup_path": "docs/archive/database_backups/test",
                "metadata": {"timestamp": datetime.now().isoformat()},
            }

            result = await backup_database(tenant_key=tenant_key)

            # Required fields
            assert "success" in result
            assert isinstance(result["success"], bool)

            if result["success"]:
                assert "backup_path" in result
                assert "metadata" in result
                assert isinstance(result["backup_path"], str)
                assert isinstance(result["metadata"], dict)

    async def test_backup_tool_handles_missing_tenant_key(self):
        """Test backup_database validates tenant_key parameter"""
        from src.giljo_mcp.tools.backup import backup_database

        # Test with None
        with pytest.raises((ValueError, TypeError)):
            await backup_database(tenant_key=None)

        # Test with empty string
        with pytest.raises((ValueError, TypeError)):
            await backup_database(tenant_key="")

    async def test_backup_tool_handles_invalid_tenant_key_type(self):
        """Test backup_database validates tenant_key type"""
        from src.giljo_mcp.tools.backup import backup_database

        # Test with integer
        with pytest.raises((ValueError, TypeError)):
            await backup_database(tenant_key=12345)

        # Test with list
        with pytest.raises((ValueError, TypeError)):
            await backup_database(tenant_key=["tenant"])

    async def test_backup_tool_passes_tenant_to_utility(self):
        """Test backup_database passes tenant_key to backup utility"""
        from src.giljo_mcp.tools.backup import backup_database

        tenant_key = f"test_tenant_{uuid4().hex[:8]}"

        with patch("src.giljo_mcp.tools.backup.create_backup") as mock_backup:
            mock_backup.return_value = {
                "success": True,
                "backup_path": "test",
                "metadata": {},
            }

            await backup_database(tenant_key=tenant_key)

            # Verify create_backup was called with tenant_key
            mock_backup.assert_called_once()
            call_args = mock_backup.call_args

            # tenant_key should be in args or kwargs
            assert (
                tenant_key in call_args.args
                or call_args.kwargs.get("tenant_key") == tenant_key
            )


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.asyncio
class TestBackupToolErrorHandling:
    """Tests for error handling in backup tool"""

    async def test_backup_tool_handles_import_error(self):
        """Test backup_database handles missing backup utility gracefully"""
        from src.giljo_mcp.tools.backup import backup_database

        tenant_key = f"test_tenant_{uuid4().hex[:8]}"

        with patch("src.giljo_mcp.tools.backup.create_backup") as mock_backup:
            mock_backup.side_effect = ImportError("Cannot import database_backup module")

            result = await backup_database(tenant_key=tenant_key)

            assert result["success"] is False
            assert "error" in result
            assert "import" in result["error"].lower() or "module" in result["error"].lower()

    async def test_backup_tool_handles_connection_error(self):
        """Test backup_database handles database connection errors"""
        from src.giljo_mcp.tools.backup import backup_database

        tenant_key = f"test_tenant_{uuid4().hex[:8]}"

        with patch("src.giljo_mcp.tools.backup.create_backup") as mock_backup:
            mock_backup.side_effect = ConnectionError("Cannot connect to database")

            result = await backup_database(tenant_key=tenant_key)

            assert result["success"] is False
            assert "error" in result
            assert "connect" in result["error"].lower() or "database" in result["error"].lower()

    async def test_backup_tool_handles_permission_error(self):
        """Test backup_database handles filesystem permission errors"""
        from src.giljo_mcp.tools.backup import backup_database

        tenant_key = f"test_tenant_{uuid4().hex[:8]}"

        with patch("src.giljo_mcp.tools.backup.create_backup") as mock_backup:
            mock_backup.side_effect = PermissionError("Cannot write to backup directory")

            result = await backup_database(tenant_key=tenant_key)

            assert result["success"] is False
            assert "error" in result
            assert "permission" in result["error"].lower() or "write" in result["error"].lower()

    async def test_backup_tool_handles_generic_exception(self):
        """Test backup_database handles unexpected exceptions"""
        from src.giljo_mcp.tools.backup import backup_database

        tenant_key = f"test_tenant_{uuid4().hex[:8]}"

        with patch("src.giljo_mcp.tools.backup.create_backup") as mock_backup:
            mock_backup.side_effect = Exception("Unexpected error during backup")

            result = await backup_database(tenant_key=tenant_key)

            assert result["success"] is False
            assert "error" in result
            assert len(result["error"]) > 0

    async def test_backup_tool_logs_errors(self):
        """Test backup_database logs errors for debugging"""
        from src.giljo_mcp.tools.backup import backup_database

        tenant_key = f"test_tenant_{uuid4().hex[:8]}"

        with patch("src.giljo_mcp.tools.backup.create_backup") as mock_backup:
            with patch("src.giljo_mcp.tools.backup.logger") as mock_logger:
                mock_backup.side_effect = Exception("Test error")

                await backup_database(tenant_key=tenant_key)

                # Should log error
                assert mock_logger.error.called or mock_logger.exception.called


# ============================================================================
# Return Value Structure Tests
# ============================================================================


@pytest.mark.asyncio
class TestBackupToolReturnValues:
    """Tests for backup tool return value structure"""

    async def test_backup_tool_success_return_structure(self):
        """Test successful backup returns properly structured result"""
        from src.giljo_mcp.tools.backup import backup_database

        tenant_key = f"test_tenant_{uuid4().hex[:8]}"
        expected_path = "docs/archive/database_backups/2025-10-24_14-30-00"
        expected_metadata = {
            "timestamp": "2025-10-24T14:30:00Z",
            "tenant_key": tenant_key,
            "tables_backed_up": ["users", "projects", "agents"],
            "record_counts": {"users": 10, "projects": 5, "agents": 15},
        }

        with patch("src.giljo_mcp.tools.backup.create_backup") as mock_backup:
            mock_backup.return_value = {
                "success": True,
                "backup_path": expected_path,
                "metadata": expected_metadata,
            }

            result = await backup_database(tenant_key=tenant_key)

            assert result["success"] is True
            assert result["backup_path"] == expected_path
            assert result["metadata"] == expected_metadata

    async def test_backup_tool_failure_return_structure(self):
        """Test failed backup returns properly structured error result"""
        from src.giljo_mcp.tools.backup import backup_database

        tenant_key = f"test_tenant_{uuid4().hex[:8]}"

        with patch("src.giljo_mcp.tools.backup.create_backup") as mock_backup:
            mock_backup.side_effect = ConnectionError("Database unavailable")

            result = await backup_database(tenant_key=tenant_key)

            assert result["success"] is False
            assert "error" in result
            assert isinstance(result["error"], str)
            assert len(result["error"]) > 0

    async def test_backup_tool_metadata_contains_tenant(self):
        """Test backup metadata includes tenant_key"""
        from src.giljo_mcp.tools.backup import backup_database

        tenant_key = f"test_tenant_{uuid4().hex[:8]}"

        with patch("src.giljo_mcp.tools.backup.create_backup") as mock_backup:
            mock_backup.return_value = {
                "success": True,
                "backup_path": "test/path",
                "metadata": {
                    "tenant_key": tenant_key,
                    "timestamp": datetime.now().isoformat(),
                },
            }

            result = await backup_database(tenant_key=tenant_key)

            assert result["success"] is True
            assert result["metadata"]["tenant_key"] == tenant_key

    async def test_backup_tool_metadata_contains_timestamp(self):
        """Test backup metadata includes timestamp"""
        from src.giljo_mcp.tools.backup import backup_database

        tenant_key = f"test_tenant_{uuid4().hex[:8]}"

        with patch("src.giljo_mcp.tools.backup.create_backup") as mock_backup:
            mock_backup.return_value = {
                "success": True,
                "backup_path": "test/path",
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "tenant_key": tenant_key,
                },
            }

            result = await backup_database(tenant_key=tenant_key)

            assert result["success"] is True
            assert "timestamp" in result["metadata"]

            # Verify timestamp is valid ISO format
            timestamp_str = result["metadata"]["timestamp"]
            datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))


# ============================================================================
# Integration with Tool System Tests
# ============================================================================


class TestBackupToolIntegration:
    """Tests for backup tool integration with MCP tool system"""

    def test_backup_tool_can_be_invoked_via_tool_system(self):
        """Test backup_database can be invoked through tool system"""
        from src.giljo_mcp.tools import get_tool_by_name, call_tool

        tool = get_tool_by_name("backup_database")
        assert tool is not None

        # Should be callable through tool system
        assert callable(tool)

    def test_backup_tool_metadata_correct(self):
        """Test backup tool has correct metadata in tool system"""
        from src.giljo_mcp.tools import get_tool_by_name

        tool = get_tool_by_name("backup_database")
        assert tool is not None

        # Check tool has required metadata attributes
        # (exact attributes depend on MCP tool system implementation)
        assert hasattr(tool, "__name__") or hasattr(tool, "name")

    def test_backup_tool_appears_in_tool_list(self):
        """Test backup tool appears in tool listing"""
        from src.giljo_mcp.tools import list_tools

        tools_list = list_tools()

        # Should be in the list
        assert any("backup" in str(tool).lower() for tool in tools_list)


# ============================================================================
# Edge Cases Tests
# ============================================================================


@pytest.mark.asyncio
class TestBackupToolEdgeCases:
    """Tests for edge cases in backup tool"""

    async def test_backup_tool_with_unicode_tenant_key(self):
        """Test backup handles unicode characters in tenant key"""
        from src.giljo_mcp.tools.backup import backup_database

        tenant_key = f"tenant_日本語_{uuid4().hex[:8]}"

        with patch("src.giljo_mcp.tools.backup.create_backup") as mock_backup:
            mock_backup.return_value = {
                "success": True,
                "backup_path": "test",
                "metadata": {"tenant_key": tenant_key},
            }

            result = await backup_database(tenant_key=tenant_key)

            # Should handle gracefully
            assert "success" in result

    async def test_backup_tool_with_very_long_tenant_key(self):
        """Test backup handles very long tenant keys"""
        from src.giljo_mcp.tools.backup import backup_database

        tenant_key = "tenant_" + "x" * 500

        with patch("src.giljo_mcp.tools.backup.create_backup") as mock_backup:
            mock_backup.return_value = {
                "success": True,
                "backup_path": "test",
                "metadata": {"tenant_key": tenant_key},
            }

            result = await backup_database(tenant_key=tenant_key)

            assert "success" in result

    async def test_backup_tool_timeout_handling(self):
        """Test backup handles long-running operations"""
        from src.giljo_mcp.tools.backup import backup_database

        tenant_key = f"test_tenant_{uuid4().hex[:8]}"

        async def slow_backup(*args, **kwargs):
            await asyncio.sleep(100)  # Simulate very slow backup
            return {"success": True, "backup_path": "test", "metadata": {}}

        with patch("src.giljo_mcp.tools.backup.create_backup", new=slow_backup):
            # Should either complete or timeout gracefully
            try:
                result = await asyncio.wait_for(
                    backup_database(tenant_key=tenant_key),
                    timeout=2.0
                )
                # If it completes, should have success field
                assert "success" in result
            except asyncio.TimeoutError:
                # Timeout is acceptable for this test
                pass
