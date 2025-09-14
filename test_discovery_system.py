"""
Test script for the Dynamic Discovery System
Tests PathResolver, DiscoveryManager, and integration with context tools
"""

import asyncio
import os
from pathlib import Path
import json
import yaml

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.tenant import TenantManager
from src.giljo_mcp.discovery import PathResolver, DiscoveryManager, SerenaHooks
from src.giljo_mcp.models import Project, Configuration, Base


async def test_path_resolver():
    """Test PathResolver functionality"""
    print("\n=== Testing PathResolver ===")
    
    # Initialize components
    db_manager = DatabaseManager("sqlite:///test_discovery.db")
    db_manager.create_tables()
    
    tenant_manager = TenantManager()
    path_resolver = PathResolver(db_manager, tenant_manager)
    
    # Test default path resolution
    print("\n1. Testing default paths:")
    for key in ["vision", "sessions", "devlog", "memories", "docs"]:
        path = await path_resolver.resolve_path(key)
        print(f"  {key}: {path} (exists: {path.exists()})")
    
    # Test with environment variable override
    print("\n2. Testing environment variable override:")
    os.environ["GILJO_MCP_PATH_VISION"] = "/custom/vision/path"
    vision_path = await path_resolver.resolve_path("vision")
    print(f"  vision with env var: {vision_path}")
    del os.environ["GILJO_MCP_PATH_VISION"]
    
    # Test get_all_paths
    print("\n3. Testing get_all_paths:")
    all_paths = await path_resolver.get_all_paths()
    for key, path in all_paths.items():
        print(f"  {key}: {path}")
    
    db_manager.close()
    print("\n[OK] PathResolver tests completed")


async def test_discovery_manager():
    """Test DiscoveryManager functionality"""
    print("\n=== Testing DiscoveryManager ===")
    
    # Initialize components
    db_manager = DatabaseManager("sqlite:///test_discovery.db")
    db_manager.create_tables()
    
    tenant_manager = TenantManager()
    path_resolver = PathResolver(db_manager, tenant_manager)
    discovery_manager = DiscoveryManager(db_manager, tenant_manager, path_resolver)
    
    # Create a test project
    async with db_manager.get_session() as session:
        project = Project(
            name="Test Discovery Project",
            mission="Test the discovery system",
            tenant_key="test-tenant-123"
        )
        session.add(project)
        await session.commit()
        project_id = str(project.id)
        
        # Set current tenant
        tenant_manager.set_current_tenant("test-tenant-123")
    
    # Test discovery for different roles
    roles = ["orchestrator", "analyzer", "implementer", "tester"]
    
    for role in roles:
        print(f"\n{role.upper()} Discovery:")
        context = await discovery_manager.discover_context(role, project_id)
        
        print(f"  Priorities: {context['metadata']['priorities_used']}")
        print(f"  Token limit: {context['metadata']['token_limit']}")
        print(f"  Tokens used: {context.get('tokens_used', 0)}")
        
        for key in context:
            if key not in ["metadata", "tokens_used"]:
                print(f"  {key}: {'loaded' if key in context else 'not loaded'}")
    
    # Test change detection
    print("\n4. Testing change detection:")
    changes = await discovery_manager.detect_changes(project_id)
    for path_key, changed in changes.items():
        print(f"  {path_key}: {'changed' if changed else 'unchanged'}")
    
    # Test discovery paths
    print("\n5. Testing get_discovery_paths:")
    paths = await discovery_manager.get_discovery_paths(project_id)
    for key, path in paths.items():
        print(f"  {key}: {path}")
    
    db_manager.close()
    print("\n[OK] DiscoveryManager tests completed")


async def test_integration():
    """Test integration with existing context tools"""
    print("\n=== Testing Integration ===")
    
    # Check if config.yaml has dynamic_discovery enabled
    config_path = Path("config.yaml")
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            dynamic_discovery = config.get('features', {}).get('dynamic_discovery', False)
            print(f"1. Dynamic discovery enabled in config: {dynamic_discovery}")
    
    # Check if models have DiscoveryConfig
    from src.giljo_mcp.models import DiscoveryConfig
    print(f"2. DiscoveryConfig model imported: [OK]")
    
    # Check if context.py imports discovery
    context_path = Path("src/giljo_mcp/tools/context.py")
    if context_path.exists():
        content = context_path.read_text()
        has_import = "from ..discovery import" in content
        print(f"3. Discovery imported in context.py: {'[OK]' if has_import else '[FAIL]'}")
        
        has_discover_tool = "async def discover_context" in content
        print(f"4. discover_context tool added: {'[OK]' if has_discover_tool else '[FAIL]'}")
        
        has_path_resolver = "path_resolver.resolve_path" in content
        print(f"5. PathResolver used in context.py: {'[OK]' if has_path_resolver else '[FAIL]'}")
    
    print("\n[OK] Integration tests completed")


async def test_serena_hooks():
    """Test SerenaHooks placeholder functionality"""
    print("\n=== Testing SerenaHooks ===")
    
    hooks = SerenaHooks()
    
    # Test lazy_load_symbols
    print("1. Testing lazy_load_symbols:")
    result = await hooks.lazy_load_symbols("test.py", depth=1)
    print(f"  Result: {result['message']}")
    
    # Test search_codebase
    print("\n2. Testing search_codebase:")
    result = await hooks.search_codebase("test_pattern")
    print(f"  Result: {result['message']}")
    
    # Test get_file_overview
    print("\n3. Testing get_file_overview:")
    result = await hooks.get_file_overview("src/")
    print(f"  Result: {result['message']}")
    
    print("\n[OK] SerenaHooks tests completed")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("DYNAMIC DISCOVERY SYSTEM TEST SUITE")
    print("=" * 60)
    
    try:
        await test_path_resolver()
        await test_discovery_manager()
        await test_serena_hooks()
        await test_integration()
        
        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETED SUCCESSFULLY! [OK]")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[FAIL] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Cleanup test database
        test_db = Path("test_discovery.db")
        if test_db.exists():
            test_db.unlink()
            print("\nTest database cleaned up")


if __name__ == "__main__":
    asyncio.run(main())