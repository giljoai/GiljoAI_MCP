"""
Unit tests for ContextService (Handover 0123 - Phase 2)

Tests cover:
- Context index stub functionality
- Vision document stub functionality
- Product settings stub functionality
- Deprecated method responses
- Error handling

Target: >80% line coverage

Note: Most methods are stubs or deprecated, so tests verify correct stub/error responses.
"""

import pytest
from unittest.mock import Mock

from giljo_mcp.services.context_service import ContextService


class TestContextServiceStubs:
    """Test stub functionality"""

    @pytest.mark.asyncio
    async def test_get_context_index_returns_empty_stub(self):
        """Test that get_context_index returns empty index stub"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        service = ContextService(db_manager, tenant_manager)

        # Act
        result = await service.get_context_index(product_id="prod-123")

        # Assert
        assert result["success"] is True
        assert "index" in result
        assert result["index"]["documents"] == []
        assert result["index"]["sections"] == []

    @pytest.mark.asyncio
    async def test_get_context_index_without_product_id(self):
        """Test get_context_index works without product_id"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        service = ContextService(db_manager, tenant_manager)

        # Act
        result = await service.get_context_index()

        # Assert
        assert result["success"] is True
        assert "index" in result

    @pytest.mark.asyncio
    async def test_get_vision_returns_placeholder(self):
        """Test that get_vision returns placeholder content"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        service = ContextService(db_manager, tenant_manager)

        # Act
        result = await service.get_vision(part=1, max_tokens=10000)

        # Assert
        assert result["success"] is True
        assert result["part"] == 1
        assert result["total_parts"] == 1
        assert result["content"] == "Vision document placeholder"
        assert "tokens" in result

    @pytest.mark.asyncio
    async def test_get_vision_with_different_part(self):
        """Test get_vision with different part number"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        service = ContextService(db_manager, tenant_manager)

        # Act
        result = await service.get_vision(part=3, max_tokens=5000)

        # Assert
        assert result["success"] is True
        assert result["part"] == 3

    @pytest.mark.asyncio
    async def test_get_vision_index_returns_empty_stub(self):
        """Test that get_vision_index returns empty index"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        service = ContextService(db_manager, tenant_manager)

        # Act
        result = await service.get_vision_index()

        # Assert
        assert result["success"] is True
        assert "index" in result
        assert result["index"]["files"] == []
        assert result["index"]["chunks"] == []

    @pytest.mark.asyncio
    async def test_get_product_settings_returns_placeholder(self):
        """Test that get_product_settings returns placeholder settings"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        service = ContextService(db_manager, tenant_manager)

        # Act
        result = await service.get_product_settings(product_id="prod-123")

        # Assert
        assert result["success"] is True
        assert "settings" in result
        assert result["settings"]["product_id"] == "prod-123"
        assert "config" in result["settings"]

    @pytest.mark.asyncio
    async def test_get_product_settings_without_product_id(self):
        """Test get_product_settings returns default when no product_id provided"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        service = ContextService(db_manager, tenant_manager)

        # Act
        result = await service.get_product_settings()

        # Assert
        assert result["success"] is True
        assert result["settings"]["product_id"] == "default"


class TestContextServiceDeprecated:
    """Test deprecated method responses"""

    @pytest.mark.asyncio
    async def test_discover_context_returns_deprecated_error(self):
        """Test that discover_context returns deprecation message"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        service = ContextService(db_manager, tenant_manager)

        # Act
        result = await service.discover_context(
            project_id="proj-123",
            path="/some/path",
            agent_role="implementer"
        )

        # Assert
        assert "error" in result
        assert result["error"] == "DEPRECATED"
        assert "message" in result
        assert "replacement" in result
        assert "removal_version" in result
        assert result["removal_version"] == "v3.2.0"

    @pytest.mark.asyncio
    async def test_get_file_context_returns_deprecated_error(self):
        """Test that get_file_context returns deprecation message"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        service = ContextService(db_manager, tenant_manager)

        # Act
        result = await service.get_file_context(file_path="src/main.py")

        # Assert
        assert "error" in result
        assert result["error"] == "DEPRECATED"
        assert "message" in result
        assert "Read tool" in result["reason"]
        assert result["removal_version"] == "v3.2.0"

    @pytest.mark.asyncio
    async def test_search_context_returns_deprecated_error(self):
        """Test that search_context returns deprecation message"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        service = ContextService(db_manager, tenant_manager)

        # Act
        result = await service.search_context(
            query="class MyClass",
            file_types=["*.py", "*.js"]
        )

        # Assert
        assert "error" in result
        assert result["error"] == "DEPRECATED"
        assert "message" in result
        assert "Grep tool" in result["reason"]
        assert result["removal_version"] == "v3.2.0"

    @pytest.mark.asyncio
    async def test_get_context_summary_returns_deprecated_error(self):
        """Test that get_context_summary returns deprecation message"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        service = ContextService(db_manager, tenant_manager)

        # Act
        result = await service.get_context_summary(project_id="proj-123")

        # Assert
        assert "error" in result
        assert result["error"] == "DEPRECATED"
        assert "message" in result
        assert "get_agent_mission" in result["reason"]
        assert result["removal_version"] == "v3.2.0"

    @pytest.mark.asyncio
    async def test_deprecated_methods_return_documentation_links(self):
        """Test that all deprecated methods include documentation references"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        service = ContextService(db_manager, tenant_manager)

        # Act & Assert - discover_context
        result1 = await service.discover_context()
        assert "documentation" in result1
        assert "Comprehensive_MCP_Analysis.md" in result1["documentation"]

        # Act & Assert - get_file_context
        result2 = await service.get_file_context("test.py")
        assert "documentation" in result2
        assert "Comprehensive_MCP_Analysis.md" in result2["documentation"]

        # Act & Assert - search_context
        result3 = await service.search_context("query")
        assert "documentation" in result3
        assert "Comprehensive_MCP_Analysis.md" in result3["documentation"]

        # Act & Assert - get_context_summary
        result4 = await service.get_context_summary()
        assert "documentation" in result4
        assert "Comprehensive_MCP_Analysis.md" in result4["documentation"]


class TestContextServiceBehavior:
    """Test service behavior and initialization"""

    def test_service_initializes_correctly(self):
        """Test that service initializes with required dependencies"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()

        # Act
        service = ContextService(db_manager, tenant_manager)

        # Assert
        assert service.db_manager == db_manager
        assert service.tenant_manager == tenant_manager
        assert service._logger is not None

    @pytest.mark.asyncio
    async def test_stub_methods_are_synchronous_safe(self):
        """Test that stub methods don't require database access"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        service = ContextService(db_manager, tenant_manager)

        # Act - Call all stub methods without database
        result1 = await service.get_context_index()
        result2 = await service.get_vision()
        result3 = await service.get_vision_index()
        result4 = await service.get_product_settings()

        # Assert - All should succeed without database calls
        assert result1["success"] is True
        assert result2["success"] is True
        assert result3["success"] is True
        assert result4["success"] is True

        # Verify no database calls were made
        db_manager.get_session_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_deprecated_methods_dont_require_database(self):
        """Test that deprecated methods don't access database"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        service = ContextService(db_manager, tenant_manager)

        # Act - Call all deprecated methods
        await service.discover_context()
        await service.get_file_context("test.py")
        await service.search_context("query")
        await service.get_context_summary()

        # Assert - No database calls should be made
        db_manager.get_session_async.assert_not_called()


class TestContextServiceConsistency:
    """Test consistency of responses"""

    @pytest.mark.asyncio
    async def test_all_stub_methods_return_success_true(self):
        """Test that all stub methods return success: true"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        service = ContextService(db_manager, tenant_manager)

        # Act
        results = [
            await service.get_context_index(),
            await service.get_vision(),
            await service.get_vision_index(),
            await service.get_product_settings(),
        ]

        # Assert
        for result in results:
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_all_deprecated_methods_return_consistent_format(self):
        """Test that all deprecated methods return consistent error format"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        service = ContextService(db_manager, tenant_manager)

        # Act
        results = [
            await service.discover_context(),
            await service.get_file_context("test.py"),
            await service.search_context("query"),
            await service.get_context_summary(),
        ]

        # Assert - All should have same structure
        for result in results:
            assert "error" in result
            assert result["error"] == "DEPRECATED"
            assert "message" in result
            assert "replacement" in result
            assert "documentation" in result
            assert "removal_version" in result
            assert "reason" in result
