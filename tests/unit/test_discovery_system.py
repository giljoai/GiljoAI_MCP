# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Test script for the Dynamic Discovery System
Tests PathResolver and DiscoveryManager initialization.
"""

import asyncio
import os

# Add project root to path
import sys
from pathlib import Path

import yaml


sys.path.insert(0, str(Path(__file__).parent))

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.discovery import DiscoveryManager, PathResolver, SerenaHooks
from src.giljo_mcp.tenant import TenantManager
from tests.helpers.test_db_helper import PostgreSQLTestHelper


async def test_path_resolver():
    """Test PathResolver functionality"""

    # Initialize components
    db_manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
    db_manager.create_tables()

    tenant_manager = TenantManager()
    path_resolver = PathResolver(db_manager, tenant_manager)

    # Test default path resolution
    for key in ["vision", "sessions", "devlog", "memories", "docs"]:
        await path_resolver.resolve_path(key)

    # Test with environment variable override
    os.environ["GILJO_MCP_PATH_VISION"] = "/custom/vision/path"
    await path_resolver.resolve_path("vision")
    del os.environ["GILJO_MCP_PATH_VISION"]

    # Test get_all_paths
    all_paths = await path_resolver.get_all_paths()
    for key in all_paths:
        pass

    db_manager.close()


async def test_discovery_manager():
    """Test DiscoveryManager functionality"""

    # Initialize components
    db_manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
    db_manager.create_tables()

    tenant_manager = TenantManager()
    path_resolver = PathResolver(db_manager, tenant_manager)
    discovery_manager = DiscoveryManager(db_manager, tenant_manager, path_resolver)

    # Test discovery paths
    paths = await discovery_manager.get_discovery_paths()
    for key in paths:
        pass

    db_manager.close()


async def test_integration():
    """Test integration with existing context tools"""

    # Check if config.yaml has dynamic_discovery enabled
    config_path = Path("config.yaml")
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)
            config.get("features", {}).get("dynamic_discovery", False)

    # Check if context.py imports discovery
    context_path = Path("src/giljo_mcp/tools/context.py")
    if context_path.exists():
        context_path.read_text()


async def test_serena_hooks():
    """Test SerenaHooks initialization"""

    hooks = SerenaHooks(None, None)  # Placeholder for test
    assert hooks._symbol_cache == {}


async def main():
    """Run all tests"""

    try:
        await test_path_resolver()
        await test_discovery_manager()
        await test_serena_hooks()
        await test_integration()

    except Exception:
        import traceback

        traceback.print_exc()

    finally:
        # Cleanup test database
        test_db = Path("test_discovery.db")
        if test_db.exists():
            test_db.unlink()


if __name__ == "__main__":
    asyncio.run(main())
