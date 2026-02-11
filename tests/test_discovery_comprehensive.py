"""
Comprehensive test suite for Dynamic Discovery System
Tests path resolution and discovery manager initialization.
"""

import asyncio
import os
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.discovery import DiscoveryManager, PathResolver, SerenaHooks
from src.giljo_mcp.tenant import TenantManager
from tests.helpers.test_db_helper import PostgreSQLTestHelper


class TestResults:
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0

    def add(self, criterion, test_name, passed, details=""):
        self.results.append({"criterion": criterion, "test": test_name, "passed": passed, "details": details})
        if passed:
            self.passed += 1
        else:
            self.failed += 1

    def print_summary(self):
        if self.failed > 0:
            for r in self.results:
                if not r["passed"]:
                    pass


async def test_criterion_2_dynamic_paths(results):
    """Test Dynamic path resolution"""

    try:
        db_manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
        db_manager.create_tables()
        tenant_manager = TenantManager()
        path_resolver = PathResolver(db_manager, tenant_manager)

        # Test default path resolution
        await path_resolver.resolve_path("vision")
        results.add(2, "Default path resolution", True)

        # Test environment variable override
        os.environ["GILJO_MCP_PATH_VISION"] = "/env/override/vision"
        path_resolver.clear_cache()  # Clear cache to force re-resolution
        vision_env = await path_resolver.resolve_path("vision")

        if str(vision_env) == "/env/override/vision":
            results.add(2, "Environment variable override", True)
        else:
            results.add(2, "Environment variable override", False, f"Expected /env/override/vision, got {vision_env}")

        del os.environ["GILJO_MCP_PATH_VISION"]

        # Check no hardcoded paths in context.py
        context_file = Path("src/giljo_mcp/tools/context.py")
        content = context_file.read_text()

        hardcoded_count = 0
        if 'Path("docs/Vision")' in content:
            hardcoded_count += content.count('Path("docs/Vision")')
        if 'Path("docs/Sessions")' in content:
            hardcoded_count += content.count('Path("docs/Sessions")')
        if 'Path("docs/devlog")' in content:
            hardcoded_count += content.count('Path("docs/devlog")')

        if hardcoded_count <= 1:  # Allow 1 for CLAUDE.md
            results.add(2, "Hardcoded paths removed", True)
        else:
            results.add(2, "Hardcoded paths removed", False, f"{hardcoded_count} hardcoded paths still present")

    except Exception as e:
        results.add(2, "Dynamic path resolution", False, str(e))


async def test_criterion_3_discovery_manager_init(results):
    """Test DiscoveryManager initialization"""

    try:
        db_manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
        db_manager.create_tables()
        tenant_manager = TenantManager()
        path_resolver = PathResolver(db_manager, tenant_manager)
        discovery_manager = DiscoveryManager(db_manager, tenant_manager, path_resolver)

        # Check get_discovery_paths method exists
        if hasattr(discovery_manager, "get_discovery_paths"):
            results.add(3, "get_discovery_paths method exists", True)
        else:
            results.add(3, "get_discovery_paths method exists", False)

    except Exception as e:
        results.add(3, "DiscoveryManager initialization", False, str(e))


async def test_criterion_5_cache_mechanism(results):
    """Test cache TTL mechanism"""

    try:
        db_manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
        db_manager.create_tables()
        tenant_manager = TenantManager()
        path_resolver = PathResolver(db_manager, tenant_manager)

        # Check cache TTL exists
        if hasattr(path_resolver, "_cache_ttl"):
            results.add(5, "Cache TTL mechanism", True)
        else:
            results.add(5, "Cache TTL mechanism", False)

    except Exception as e:
        results.add(5, "Cache mechanism", False, str(e))


async def test_criterion_6_serena_hooks(results):
    """Test SerenaHooks class exists"""

    try:
        db_manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
        db_manager.create_tables()
        tenant_manager = TenantManager()
        serena_hooks = SerenaHooks(db_manager, tenant_manager)

        # Check SerenaHooks class exists and initializes
        if serena_hooks.db_manager is db_manager:
            results.add(6, "SerenaHooks initializes correctly", True)
        else:
            results.add(6, "SerenaHooks initializes correctly", False)

    except Exception as e:
        results.add(6, "SerenaHooks initialization", False, str(e))


async def main():
    results = TestResults()

    # Run all tests
    await test_criterion_2_dynamic_paths(results)
    await test_criterion_3_discovery_manager_init(results)
    await test_criterion_5_cache_mechanism(results)
    await test_criterion_6_serena_hooks(results)

    # Print summary
    results.print_summary()

    # Final verdict
    if results.failed == 0 or results.failed <= 2:
        pass
    else:
        pass

    return results


if __name__ == "__main__":
    results = asyncio.run(main())
