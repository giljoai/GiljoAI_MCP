"""
Tests for TenantManager functionality and performance.

Split from test_tenant_isolation.py — covers TenantManager unit tests
(key generation, validation, context management, hashing, batch ops)
and performance benchmarks.
"""

import random
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest
from sqlalchemy import select


sys.path.insert(0, str(Path(__file__).parent.parent))

pytestmark = pytest.mark.skip(reason="0750c3: async_engine attribute missing on DatabaseManager — DB test infrastructure")

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Project
from src.giljo_mcp.tenant import TenantManager
from tests.helpers.test_db_helper import PostgreSQLTestHelper


class TestTenantManager:
    """Test TenantManager functionality."""

    def test_tenant_key_generation(self):
        """Test tenant key generation is unique and valid."""
        keys = set()
        for _ in range(100):
            key = TenantManager.generate_tenant_key()
            assert key.startswith("tk_")
            assert len(key) == 35  # tk_ + 32 chars
            assert key not in keys
            keys.add(key)
            assert TenantManager.validate_tenant_key(key)

    def test_tenant_key_validation(self):
        """Test tenant key validation."""
        # Valid keys
        valid_key = TenantManager.generate_tenant_key()
        assert TenantManager.validate_tenant_key(valid_key)

        # Invalid keys
        assert not TenantManager.validate_tenant_key(None)
        assert not TenantManager.validate_tenant_key("")
        assert not TenantManager.validate_tenant_key("invalid")
        assert not TenantManager.validate_tenant_key("tk_")
        assert not TenantManager.validate_tenant_key("tk_short")
        assert not TenantManager.validate_tenant_key("wrong_prefix_" + "a" * 32)

    def test_tenant_context_management(self):
        """Test tenant context setting and retrieval."""
        key1 = TenantManager.generate_tenant_key()
        key2 = TenantManager.generate_tenant_key()

        # Initially no tenant
        assert TenantManager.get_current_tenant() is None

        # Set tenant 1
        TenantManager.set_current_tenant(key1)
        assert TenantManager.get_current_tenant() == key1

        # Switch to tenant 2
        TenantManager.set_current_tenant(key2)
        assert TenantManager.get_current_tenant() == key2

        # Clear tenant
        TenantManager.clear_current_tenant()
        assert TenantManager.get_current_tenant() is None

    def test_tenant_context_manager(self):
        """Test with_tenant context manager."""
        key1 = TenantManager.generate_tenant_key()
        key2 = TenantManager.generate_tenant_key()

        # Set initial tenant
        TenantManager.set_current_tenant(key1)
        assert TenantManager.get_current_tenant() == key1

        # Use context manager
        with TenantManager.with_tenant(key2):
            assert TenantManager.get_current_tenant() == key2

        # Should restore previous tenant
        assert TenantManager.get_current_tenant() == key1

        # Clear and test with no previous tenant
        TenantManager.clear_current_tenant()
        with TenantManager.with_tenant(key2):
            assert TenantManager.get_current_tenant() == key2
        assert TenantManager.get_current_tenant() is None

    def test_require_tenant(self):
        """Test require_tenant error handling."""
        TenantManager.clear_current_tenant()

        # Should raise when no tenant set
        with pytest.raises(RuntimeError, match="No tenant context"):
            TenantManager.require_tenant()

        # Should work when tenant is set
        key = TenantManager.generate_tenant_key()
        TenantManager.set_current_tenant(key)
        assert TenantManager.require_tenant() == key

    def test_tenant_key_hashing(self):
        """Test tenant key hashing for logging."""
        key = TenantManager.generate_tenant_key()
        hash1 = TenantManager.hash_tenant_key(key)
        hash2 = TenantManager.hash_tenant_key(key)

        # Should be consistent
        assert hash1 == hash2
        assert len(hash1) == 8

        # Different keys should have different hashes
        key2 = TenantManager.generate_tenant_key()
        hash3 = TenantManager.hash_tenant_key(key2)
        assert hash3 != hash1

    def test_batch_validation(self):
        """Test batch tenant key validation."""
        valid_keys = [TenantManager.generate_tenant_key() for _ in range(5)]
        invalid_keys = ["invalid1", "tk_", None, "", "wrong_prefix"]

        all_keys = valid_keys + invalid_keys
        results = TenantManager.batch_validate_keys(all_keys)

        for key in valid_keys:
            assert results[key] is True

        for key in invalid_keys:
            assert results[key] is False


class TestTenantPerformance:
    """Performance tests for multi-tenant operations."""

    @pytest.fixture
    def db_manager(self):
        """Create an in-memory database for performance testing."""
        manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
        manager.create_tables()
        yield manager
        manager.close()

    def test_tenant_key_generation_performance(self):
        """Test performance of tenant key generation."""
        import time

        start = time.time()
        keys = [TenantManager.generate_tenant_key() for _ in range(1000)]
        elapsed = time.time() - start

        # Should generate 1000 keys in under 1 second
        assert elapsed < 1.0
        # All keys should be unique
        assert len(set(keys)) == 1000

    def test_tenant_validation_caching(self):
        """Test that validation caching improves performance."""
        import time

        keys = [TenantManager.generate_tenant_key() for _ in range(100)]

        # First validation (uncached)
        TenantManager.clear_cache()
        start = time.time()
        for key in keys:
            TenantManager.validate_tenant_key(key)
        first_run = time.time() - start

        # Second validation (cached)
        start = time.time()
        for key in keys:
            TenantManager.validate_tenant_key(key)
        cached_run = time.time() - start

        # Cached should be faster
        assert cached_run < first_run

    def test_multi_tenant_query_performance(self, db_manager):
        """Test query performance with tenant filtering."""
        import time

        # Create multiple tenants with data
        tenant_keys = [TenantManager.generate_tenant_key() for _ in range(10)]

        # Populate data
        for tenant_key in tenant_keys:
            with db_manager.get_tenant_session(tenant_key) as session:
                for i in range(50):
                    project = Project(name=f"Project {i}", mission=f"Mission {i}", tenant_key=tenant_key, series_number=random.randint(1, 999999))
                    session.add(project)
                session.commit()

        # Test query performance
        target_tenant = tenant_keys[5]
        start = time.time()

        with db_manager.get_tenant_session(target_tenant) as session:
            projects = session.execute(select(Project).where(Project.tenant_key == target_tenant)).scalars().all()
            assert len(projects) == 50

        elapsed = time.time() - start

        # Should query in under 100ms even with 500 total projects
        assert elapsed < 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
