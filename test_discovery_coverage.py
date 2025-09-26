"""
Test script to establish discovery.py coverage baseline
"""

import os
import sys
import tempfile
from pathlib import Path


# Add src to path
sys.path.insert(0, "src")

from giljo_mcp.database import DatabaseManager
from giljo_mcp.discovery import DiscoveryManager, PathResolver, SerenaHooks
from giljo_mcp.tenant import TenantManager


def test_basic_instantiation():
    """Test basic class instantiation"""
    print("Testing basic instantiation...")

    # Create temp db
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        db_manager = DatabaseManager(f"sqlite:///{db_path}")
        db_manager.create_tables()
        tenant_manager = TenantManager()

        # Test PathResolver
        path_resolver = PathResolver(db_manager, tenant_manager)
        assert path_resolver.DEFAULT_PATHS
        print("  [OK] PathResolver instantiated")

        # Test DiscoveryManager
        discovery_manager = DiscoveryManager(db_manager, tenant_manager, path_resolver)
        assert discovery_manager.PRIORITY_ORDER
        assert discovery_manager.ROLE_PRIORITIES
        assert discovery_manager.ROLE_TOKEN_LIMITS
        print("  [OK] DiscoveryManager instantiated")

        # Test SerenaHooks
        serena_hooks = SerenaHooks(db_manager, tenant_manager)
        print("  [OK] SerenaHooks instantiated")

    finally:
        try:
            if os.path.exists(db_path):
                os.unlink(db_path)
        except (PermissionError, OSError):
            pass  # Ignore cleanup errors


def test_path_resolver():
    """Test PathResolver methods"""
    print("Testing PathResolver methods...")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        db_manager = DatabaseManager(f"sqlite:///{db_path}")
        db_manager.create_tables()
        tenant_manager = TenantManager()
        path_resolver = PathResolver(db_manager, tenant_manager)

        # Test cache methods
        path_resolver.clear_cache()
        print("  [OK] clear_cache")

        # Test cache validity (sync method)
        valid = path_resolver._is_cache_valid("test_key")
        assert not valid  # Should be False for non-existent key
        print("  [OK] _is_cache_valid")

        # Test cache update
        test_path = Path("test/path")
        path_resolver._update_cache("test_key", test_path)
        print("  [OK] _update_cache")

    finally:
        try:
            if os.path.exists(db_path):
                os.unlink(db_path)
        except (PermissionError, OSError):
            pass  # Ignore cleanup errors


def test_discovery_manager():
    """Test DiscoveryManager methods"""
    print("Testing DiscoveryManager methods...")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        db_manager = DatabaseManager(f"sqlite:///{db_path}")
        db_manager.create_tables()
        tenant_manager = TenantManager()
        path_resolver = PathResolver(db_manager, tenant_manager)
        discovery_manager = DiscoveryManager(db_manager, tenant_manager, path_resolver)

        # Test hash calculation
        test_content = "test content for hashing"
        hash1 = discovery_manager.calculate_content_hash(test_content)
        hash2 = discovery_manager.calculate_content_hash(test_content)
        assert hash1 == hash2
        print("  [OK] calculate_content_hash")

        # Test different content produces different hash
        hash3 = discovery_manager.calculate_content_hash("different content")
        assert hash3 != hash1
        print("  [OK] hash consistency verification")

    finally:
        try:
            if os.path.exists(db_path):
                os.unlink(db_path)
        except (PermissionError, OSError):
            pass  # Ignore cleanup errors


def test_serena_hooks():
    """Test SerenaHooks methods"""
    print("Testing SerenaHooks methods...")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        db_manager = DatabaseManager(f"sqlite:///{db_path}")
        db_manager.create_tables()
        tenant_manager = TenantManager()
        serena_hooks = SerenaHooks(db_manager, tenant_manager)

        # Test cache clear
        serena_hooks.clear_cache()
        print("  [OK] clear_cache")

    finally:
        try:
            if os.path.exists(db_path):
                os.unlink(db_path)
        except (PermissionError, OSError):
            pass  # Ignore cleanup errors


if __name__ == "__main__":
    print("Starting discovery.py coverage baseline tests...")

    test_basic_instantiation()
    test_path_resolver()
    test_discovery_manager()
    test_serena_hooks()

    print("\n[SUCCESS] All basic tests passed!")
    print("[INFO] This covers basic instantiation and some sync methods")
    print("[TODO] Next: Need to test async methods and complex workflows")
