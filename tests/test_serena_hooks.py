"""
Test suite for SerenaHooks integration.
Tests constructor parameters, placeholder methods, and caching functionality.
"""

import asyncio
import sys
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest


# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.discovery import SerenaHooks
from tests.helpers.test_db_helper import PostgreSQLTestHelper


class TestSerenaHooks:
    """Test suite for SerenaHooks class"""

    @pytest.fixture
    def mock_db_manager(self):
        """Create mock DatabaseManager"""
        mock = Mock()
        mock.get_session = AsyncMock()
        mock.close = AsyncMock()
        return mock

    @pytest.fixture
    def mock_tenant_manager(self):
        """Create mock TenantManager"""
        mock = Mock()
        mock.get_tenant_key = Mock(return_value="test-tenant-key")
        mock.validate_tenant = AsyncMock(return_value=True)
        return mock

    @pytest.fixture
    def serena_hooks(self, mock_db_manager, mock_tenant_manager):
        """Create SerenaHooks instance with mocks"""
        return SerenaHooks(mock_db_manager, mock_tenant_manager)

    def test_constructor_parameters(self, mock_db_manager, mock_tenant_manager):
        """Test that constructor properly accepts db_manager and tenant_manager"""
        hooks = SerenaHooks(mock_db_manager, mock_tenant_manager)

        assert hooks.db_manager is mock_db_manager
        assert hooks.tenant_manager is mock_tenant_manager
        assert hooks._symbol_cache == {}
        assert hooks._cache_ttl == timedelta(minutes=10)

    def test_constructor_without_parameters(self):
        """Test that constructor fails without required parameters"""
        with pytest.raises(TypeError) as exc_info:
            SerenaHooks()

        assert "missing 2 required positional arguments" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_lazy_load_symbols(self, serena_hooks):
        """Test lazy_load_symbols placeholder method"""
        result = await serena_hooks.lazy_load_symbols(file_path="test.py", depth=2, max_chars=5000)

        assert result["file"] == "test.py"
        assert result["symbols"] == []
        assert "mcp__serena-mcp__get_symbols_overview" in result["message"]

    @pytest.mark.asyncio
    async def test_search_codebase(self, serena_hooks):
        """Test search_codebase placeholder method"""
        result = await serena_hooks.search_codebase(pattern="test_pattern", max_chars=3000, paths_include="*.py")

        assert result["pattern"] == "test_pattern"
        assert result["results"] == []
        assert "mcp__serena-mcp__search_for_pattern" in result["message"]

    @pytest.mark.asyncio
    async def test_get_file_overview(self, serena_hooks):
        """Test get_file_overview placeholder method"""
        result = await serena_hooks.get_file_overview(path="/test/path")

        assert result["path"] == "/test/path"
        assert result["structure"] == {}
        assert "mcp__serena-mcp__list_dir" in result["message"]

    def test_clear_cache(self, serena_hooks):
        """Test cache clearing functionality"""
        # Add some items to cache
        serena_hooks._symbol_cache = {"file1.py": {"symbols": []}, "file2.py": {"symbols": []}}

        # Clear cache
        serena_hooks.clear_cache()

        assert serena_hooks._symbol_cache == {}

    def test_cache_ttl_value(self, serena_hooks):
        """Test that cache TTL is set correctly"""
        assert serena_hooks._cache_ttl == timedelta(minutes=10)
        assert serena_hooks._cache_ttl.total_seconds() == 600


class TestSerenaHooksIntegration:
    """Integration tests for SerenaHooks with actual database/tenant managers"""

    @pytest.mark.asyncio
    async def test_with_real_managers(self):
        """Test SerenaHooks with actual manager instances (if available)"""
        try:
            from src.giljo_mcp.database import DatabaseManager
            from src.giljo_mcp.tenant_manager import TenantManager

            # Create real instances
            db_manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
            tenant_manager = TenantManager(db_manager)

            # Create SerenaHooks with real managers
            hooks = SerenaHooks(db_manager, tenant_manager)

            # Test basic functionality
            result = await hooks.lazy_load_symbols("test.py")
            assert "message" in result

            # Cleanup
            await db_manager.close()

        except ImportError:
            pytest.skip("DatabaseManager or TenantManager not available")


def run_tests():
    """Run all tests and print results"""

    # Run with pytest if available
    try:
        import pytest

        exit_code = pytest.main([__file__, "-v", "--tb=short"])
        return exit_code == 0
    except ImportError:
        # Fallback to manual test execution

        # Create mock objects
        db_manager = Mock()
        db_manager.get_session = AsyncMock()
        tenant_manager = Mock()
        tenant_manager.get_tenant_key = Mock(return_value="test-key")

        # Test constructor
        try:
            hooks = SerenaHooks(db_manager, tenant_manager)
        except Exception:
            return False

        # Test async methods
        async def run_async_tests():
            results = []

            # Test lazy_load_symbols
            result = await hooks.lazy_load_symbols("test.py")
            if result["file"] == "test.py":
                results.append(True)
            else:
                results.append(False)

            # Test search_codebase
            result = await hooks.search_codebase("pattern")
            if result["pattern"] == "pattern":
                results.append(True)
            else:
                results.append(False)

            # Test get_file_overview
            result = await hooks.get_file_overview("/path")
            if result["path"] == "/path":
                results.append(True)
            else:
                results.append(False)

            return all(results)

        # Run async tests
        success = asyncio.run(run_async_tests())

        # Test clear_cache
        hooks._symbol_cache = {"test": "data"}
        hooks.clear_cache()
        if hooks._symbol_cache == {}:
            pass
        else:
            success = False

        if success:
            pass
        else:
            pass

        return success


if __name__ == "__main__":
    success = run_tests()
    # sys.exit(0 if success else 1)  # Commented for pytest
