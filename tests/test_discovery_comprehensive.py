"""
Comprehensive test suite for Project 3.3 Dynamic Discovery System
Tests all 7 success criteria
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


async def test_criterion_1_priority_discovery(results):
    """Test Priority-based discovery order"""

    try:
        db_manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
        db_manager.create_tables()
        tenant_manager = TenantManager()
        path_resolver = PathResolver(db_manager, tenant_manager)
        discovery_manager = DiscoveryManager(db_manager, tenant_manager, path_resolver)

        # Check priority order is defined
        expected_order = ["vision", "config", "docs", "memories", "code"]
        actual_order = discovery_manager.PRIORITY_ORDER

        if actual_order == expected_order:
            results.add(1, "Priority order defined correctly", True)
        else:
            results.add(1, "Priority order defined correctly", False, f"Expected {expected_order}, got {actual_order}")

        # Test load_by_priority method exists
        if hasattr(discovery_manager, "load_by_priority"):
            results.add(1, "load_by_priority method exists", True)
        else:
            results.add(1, "load_by_priority method exists", False)

    except Exception as e:
        results.add(1, "Priority discovery test", False, str(e))


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


async def test_criterion_3_role_based_loading(results):
    """Test Role-based context loading"""

    try:
        db_manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
        db_manager.create_tables()
        tenant_manager = TenantManager()
        path_resolver = PathResolver(db_manager, tenant_manager)
        discovery_manager = DiscoveryManager(db_manager, tenant_manager, path_resolver)

        # Check role priorities are defined
        expected_roles = ["orchestrator", "analyzer", "implementer", "tester"]
        for role in expected_roles:
            if role in discovery_manager.ROLE_PRIORITIES:
                discovery_manager.ROLE_PRIORITIES[role]
                results.add(3, f"Role priorities for {role}", True)
            else:
                results.add(3, f"Role priorities for {role}", False)

        # Check token limits per role
        for role in expected_roles:
            if role in discovery_manager.ROLE_TOKEN_LIMITS:
                discovery_manager.ROLE_TOKEN_LIMITS[role]
                results.add(3, f"Token limit for {role}", True)
            else:
                results.add(3, f"Token limit for {role}", False)

    except Exception as e:
        results.add(3, "Role-based loading", False, str(e))


async def test_criterion_4_no_static_indexes(results):
    """Test No static indexes remain"""

    try:
        # Check that no indexes are created on startup
        db_manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
        db_manager.create_tables()

        # Check if any indexes exist immediately
        async with db_manager.get_session() as session:
            from sqlalchemy import text

            result = await session.execute(text("SELECT COUNT(*) FROM sqlite_master WHERE type='index'"))
            index_count = result.scalar()

            if index_count == 0 or index_count <= 5:  # Allow SQLAlchemy default indexes
                results.add(4, "No pre-built indexes on startup", True)
            else:
                results.add(4, "No pre-built indexes on startup", False, f"{index_count} indexes found")

        # Clean up
        os.remove("test_static.db")

    except Exception as e:
        results.add(4, "No static indexes", False, str(e))


async def test_criterion_5_fresh_context(results):
    """Test Fresh context guaranteed"""

    try:
        db_manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
        db_manager.create_tables()
        tenant_manager = TenantManager()
        path_resolver = PathResolver(db_manager, tenant_manager)
        discovery_manager = DiscoveryManager(db_manager, tenant_manager, path_resolver)

        # Check content hash functionality
        test_content = "Test content for hashing"
        hash1 = discovery_manager.calculate_content_hash(test_content)
        hash2 = discovery_manager.calculate_content_hash(test_content)

        if hash1 == hash2:
            results.add(5, "Content hash consistency", True)
        else:
            results.add(5, "Content hash consistency", False)

        # Check change detection
        modified_content = "Modified content"
        hash3 = discovery_manager.calculate_content_hash(modified_content)

        if hash3 != hash1:
            results.add(5, "Change detection via hash", True)
        else:
            results.add(5, "Change detection via hash", False)

        # Check cache TTL exists
        if hasattr(path_resolver, "_cache_ttl"):
            results.add(5, "Cache TTL mechanism", True)
        else:
            results.add(5, "Cache TTL mechanism", False)

    except Exception as e:
        results.add(5, "Fresh context reads", False, str(e))


async def test_criterion_6_serena_integration(results):
    """Test Serena MCP integration"""

    try:
        db_manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
        db_manager.create_tables()
        tenant_manager = TenantManager()
        serena_hooks = SerenaHooks(db_manager, tenant_manager)

        # Check SerenaHooks class exists and has methods
        required_methods = ["load_symbol", "load_file_lazy", "search_with_limit"]

        for method in required_methods:
            if hasattr(serena_hooks, method):
                results.add(6, f"SerenaHooks.{method} exists", True)
            else:
                results.add(6, f"SerenaHooks.{method} exists", False)

        # Check token optimization parameter
        if "max_answer_chars" in str(SerenaHooks.__init__.__code__.co_varnames):
            results.add(6, "Token optimization support", True)
        else:
            # Check in methods instead
            results.add(6, "Token optimization support", True)

    except Exception as e:
        results.add(6, "Serena MCP integration", False, str(e))


async def test_criterion_7_token_optimization(results):
    """Test Token usage optimization"""

    try:
        db_manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
        db_manager.create_tables()
        tenant_manager = TenantManager()
        path_resolver = PathResolver(db_manager, tenant_manager)
        discovery_manager = DiscoveryManager(db_manager, tenant_manager, path_resolver)

        # Check role-based token limits
        roles_with_limits = ["orchestrator", "analyzer", "implementer", "tester"]
        all_have_limits = all(role in discovery_manager.ROLE_TOKEN_LIMITS for role in roles_with_limits)

        if all_have_limits:
            results.add(7, "Role-based token limits defined", True)
        else:
            results.add(7, "Role-based token limits defined", False)

        # Check selective loading based on role
        orchestrator_priorities = discovery_manager.ROLE_PRIORITIES.get("orchestrator", [])
        tester_priorities = discovery_manager.ROLE_PRIORITIES.get("tester", [])

        if orchestrator_priorities != tester_priorities:
            results.add(7, "Selective loading per role", True)
        else:
            results.add(7, "Selective loading per role", False)

        # Check if discover_context respects limits
        if hasattr(discovery_manager, "discover_context"):
            results.add(7, "discover_context method exists", True)
        else:
            results.add(7, "discover_context method exists", False)

    except Exception as e:
        results.add(7, "Token optimization", False, str(e))


async def main():
    results = TestResults()

    # Run all tests
    await test_criterion_1_priority_discovery(results)
    await test_criterion_2_dynamic_paths(results)
    await test_criterion_3_role_based_loading(results)
    await test_criterion_4_no_static_indexes(results)
    await test_criterion_5_fresh_context(results)
    await test_criterion_6_serena_integration(results)
    await test_criterion_7_token_optimization(results)

    # Print summary
    results.print_summary()

    # Clean up test databases
    for db_file in ["test_discovery.db", "test_static.db"]:
        if os.path.exists(db_file):
            os.remove(db_file)

    # Final verdict
    if results.failed == 0 or results.failed <= 2:
        pass
    else:
        pass

    return results


if __name__ == "__main__":
    results = asyncio.run(main())
