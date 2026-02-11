"""
Test suite for SerenaHooks integration.
Tests constructor parameters and initialization.
"""

import sys
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest


# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.discovery import SerenaHooks


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

    def test_cache_ttl_value(self, serena_hooks):
        """Test that cache TTL is set correctly"""
        assert serena_hooks._cache_ttl == timedelta(minutes=10)
        assert serena_hooks._cache_ttl.total_seconds() == 600
