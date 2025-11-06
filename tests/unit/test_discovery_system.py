"""
Test script for the Dynamic Discovery System
Tests PathResolver, DiscoveryManager, and integration with context tools
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
from src.giljo_mcp.models import Project
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

    # Create a test project
    async with db_manager.get_session() as session:
        project = Project(
            name="Test Discovery Project", mission="Test the discovery system", tenant_key="test-tenant-123"
        )
        session.add(project)
        await session.commit()
        project_id = str(project.id)

        # Set current tenant
        tenant_manager.set_current_tenant("test-tenant-123")

    # Test discovery for different roles
    roles = ["orchestrator", "analyzer", "implementer", "tester"]

    for role in roles:
        context = await discovery_manager.discover_context(role, project_id)

        for key in context:
            if key not in ["metadata", "tokens_used"]:
                pass

    # Test change detection
    changes = await discovery_manager.detect_changes(project_id)
    for _path_key, _changed in changes.items():
        pass

    # Test discovery paths
    paths = await discovery_manager.get_discovery_paths(project_id)
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

    # Check if models have DiscoveryConfig

    # Check if context.py imports discovery
    context_path = Path("src/giljo_mcp/tools/context.py")
    if context_path.exists():
        context_path.read_text()


async def test_serena_hooks():
    """Test SerenaHooks placeholder functionality"""

    hooks = SerenaHooks(None, None)  # Placeholder for test

    # Test lazy_load_symbols
    await hooks.lazy_load_symbols("test.py", depth=1)

    # Test search_codebase
    await hooks.search_codebase("test_pattern")

    # Test get_file_overview
    await hooks.get_file_overview("src/")


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
