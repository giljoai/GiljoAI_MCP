"""
Final async tests for discovery.py to achieve 95%+ coverage
Tests with proper async database initialization
"""
import sys
import tempfile
import os
import asyncio
import yaml
from pathlib import Path
from unittest.mock import patch, mock_open

# Add src to path  
sys.path.insert(0, 'src')

from giljo_mcp.discovery import DiscoveryManager, PathResolver, SerenaHooks
from giljo_mcp.database import DatabaseManager
from giljo_mcp.tenant import TenantManager

async def test_discovery_with_real_async_database():
    """Test discovery methods with real async database"""
    print("Testing discovery with real async database...")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # CRITICAL: Initialize with is_async=True
        db_manager = DatabaseManager(f'sqlite:///{db_path}', is_async=True)
        await db_manager.create_tables_async()
        tenant_manager = TenantManager()
        path_resolver = PathResolver(db_manager, tenant_manager)
        discovery_manager = DiscoveryManager(db_manager, tenant_manager, path_resolver)
        
        # Test _get_database_path with real async database
        result = await path_resolver._get_database_path("vision", "test-project")
        assert result is None  # No config should exist
        print("  [OK] _get_database_path async")
        
        # Test _load_vision with real async database (no vision data)
        result = await discovery_manager._load_vision("test-project", 5000)
        # Could be None or dict depending on filesystem - both are valid
        assert result is None or isinstance(result, dict)
        print("  [OK] _load_vision async no data")
        
        # Test _load_config with real async database (no config data)
        result = await discovery_manager._load_config("test-project", 5000)
        assert isinstance(result, dict)
        assert "content" in result
        print("  [OK] _load_config async no data")
        
        # Test discover_context with real async workflow
        context = await discovery_manager.discover_context("orchestrator", "test-project")
        assert isinstance(context, dict)
        assert "metadata" in context
        print("  [OK] discover_context full async workflow")
        
        # Test load_by_priority with vision and config (real async)
        result = await discovery_manager.load_by_priority(["vision", "config"], "test-project", 5000)
        assert isinstance(result, dict)
        assert "tokens_used" in result
        print("  [OK] load_by_priority async workflow")
        
    finally:
        try:
            if os.path.exists(db_path):
                os.unlink(db_path)
        except (PermissionError, OSError):
            pass

async def test_vision_with_existing_database_data():
    """Test vision loading with database data"""
    print("Testing vision with database data...")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        db_manager = DatabaseManager(f'sqlite:///{db_path}', is_async=True)
        await db_manager.create_tables_async()
        tenant_manager = TenantManager()
        path_resolver = PathResolver(db_manager, tenant_manager)
        discovery_manager = DiscoveryManager(db_manager, tenant_manager, path_resolver)
        
        # Create a vision record in the database first
        from giljo_mcp.models import Vision
        async with db_manager.get_session_async() as session:
            vision = Vision(
                tenant_key="test-tenant",
                project_id="test-project",
                document_name="vision.md",
                chunk_number=1,
                total_chunks=1,
                content="# Test Vision\nThis is test vision content.",
                tokens=100
            )
            session.add(vision)
            await session.commit()
        
        # Now test loading it
        result = await discovery_manager._load_vision("test-project", 5000)
        assert isinstance(result, dict)
        assert "content" in result
        assert result["content"]["source"] == "database"
        print("  [OK] _load_vision with database data")
        
    finally:
        try:
            if os.path.exists(db_path):
                os.unlink(db_path)
        except (PermissionError, OSError):
            pass

async def test_config_with_database_data():
    """Test config loading with database configuration"""
    print("Testing config with database data...")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        db_manager = DatabaseManager(f'sqlite:///{db_path}', is_async=True)
        await db_manager.create_tables_async()
        tenant_manager = TenantManager()
        path_resolver = PathResolver(db_manager, tenant_manager)
        discovery_manager = DiscoveryManager(db_manager, tenant_manager, path_resolver)
        
        # Create configuration records
        from giljo_mcp.models import Configuration
        async with db_manager.get_session_async() as session:
            config1 = Configuration(
                tenant_key="test-tenant",
                project_id="test-project",
                key="test.setting",
                value="test_value",
                category="general"
            )
            config2 = Configuration(
                tenant_key="test-tenant",
                project_id="test-project", 
                key="path.vision",
                value="/custom/vision/path",
                category="paths"
            )
            session.add(config1)
            session.add(config2)
            await session.commit()
        
        # Test path resolution with database config
        result = await path_resolver._get_database_path("vision", "test-project")
        assert result == "/custom/vision/path"
        print("  [OK] _get_database_path with data")
        
        # Test config loading with database data
        result = await discovery_manager._load_config("test-project", 5000)
        assert isinstance(result, dict)
        assert "content" in result
        assert "database" in result["content"]
        assert len(result["content"]["database"]) >= 2
        print("  [OK] _load_config with database data")
        
    finally:
        try:
            if os.path.exists(db_path):
                os.unlink(db_path)
        except (PermissionError, OSError):
            pass

async def test_memories_with_real_files():
    """Test memories loading with actual files"""
    print("Testing memories with real files...")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    # Create temporary memory files
    with tempfile.TemporaryDirectory() as temp_dir:
        sessions_dir = Path(temp_dir) / "sessions"
        sessions_dir.mkdir()
        
        serena_dir = Path(temp_dir) / "serena"
        serena_dir.mkdir()
        
        # Create session files
        (sessions_dir / "session1.md").write_text("# Session 1\nTest session content")
        (sessions_dir / "session2.md").write_text("# Session 2\nAnother session")
        
        # Create serena memory files  
        (serena_dir / "memory1.md").write_text("# Memory 1\nTest memory content")
        
        try:
            db_manager = DatabaseManager(f'sqlite:///{db_path}', is_async=True)
            await db_manager.create_tables_async()
            tenant_manager = TenantManager()
            path_resolver = PathResolver(db_manager, tenant_manager)
            discovery_manager = DiscoveryManager(db_manager, tenant_manager, path_resolver)
            
            # Mock path resolution to use our temp directories
            async def mock_resolve_path(path_type, project_id=None):
                if path_type == "sessions":
                    return sessions_dir
                elif path_type == "memories":
                    return serena_dir
                return Path("default")
            
            with patch.object(path_resolver, 'resolve_path', side_effect=mock_resolve_path):
                result = await discovery_manager._load_memories("test-project", 5000)
                assert isinstance(result, dict)
                assert "content" in result
                assert len(result["content"]) > 0
                print("  [OK] _load_memories with real files")
        
        finally:
            try:
                if os.path.exists(db_path):
                    os.unlink(db_path)
            except (PermissionError, OSError):
                pass

async def test_error_handling_async():
    """Test error handling with async operations"""
    print("Testing async error handling...")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        db_manager = DatabaseManager(f'sqlite:///{db_path}', is_async=True)
        await db_manager.create_tables_async()
        tenant_manager = TenantManager()
        path_resolver = PathResolver(db_manager, tenant_manager)
        discovery_manager = DiscoveryManager(db_manager, tenant_manager, path_resolver)
        
        # Test database error in _get_database_path
        with patch.object(db_manager, 'get_session_async', side_effect=Exception("DB Async Error")):
            result = await path_resolver._get_database_path("vision", "test-project")
            assert result is None
            print("  [OK] Database error handling in path resolution")
        
        # Test database error in _load_vision  
        with patch.object(db_manager, 'get_session_async', side_effect=Exception("Vision DB Error")):
            result = await discovery_manager._load_vision("test-project", 1000)
            assert result is None
            print("  [OK] Database error handling in vision loading")
        
        # Test database error in _load_config
        with patch.object(db_manager, 'get_session_async', side_effect=Exception("Config DB Error")):
            result = await discovery_manager._load_config("test-project", 1000)
            assert result is None
            print("  [OK] Database error handling in config loading")
        
    finally:
        try:
            if os.path.exists(db_path):
                os.unlink(db_path)
        except (PermissionError, OSError):
            pass

async def test_docs_with_truncation():
    """Test docs loading with content truncation"""
    print("Testing docs with truncation...")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        db_manager = DatabaseManager(f'sqlite:///{db_path}', is_async=True)  
        await db_manager.create_tables_async()
        tenant_manager = TenantManager()
        path_resolver = PathResolver(db_manager, tenant_manager)
        discovery_manager = DiscoveryManager(db_manager, tenant_manager, path_resolver)
        
        # Create large content that will need truncation
        large_content = "x" * 10000  # 10KB content
        
        mock_docs_path = Path("mock_docs")
        with patch.object(path_resolver, 'resolve_path', return_value=mock_docs_path):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('pathlib.Path.read_text', return_value=large_content):
                    # Test with small token limit to force truncation
                    result = await discovery_manager._load_docs("test-project", 100)
                    assert isinstance(result, dict)
                    assert "content" in result
                    assert "CLAUDE.md" in result["content"]
                    # Should have truncated content
                    assert "[truncated]" in result["content"]["CLAUDE.md"]
                    print("  [OK] Docs loading with truncation")
        
    finally:
        try:
            if os.path.exists(db_path):
                os.unlink(db_path)
        except (PermissionError, OSError):
            pass

async def run_final_tests():
    """Run all final async tests"""
    print("Starting final async discovery.py tests for 95%+ coverage...\n")
    
    await test_discovery_with_real_async_database()
    print()
    
    await test_vision_with_existing_database_data()
    print()
    
    await test_config_with_database_data()
    print()
    
    await test_memories_with_real_files()
    print()
    
    await test_error_handling_async()
    print()
    
    await test_docs_with_truncation()
    print()
    
    print("[SUCCESS] All final async tests passed!")
    print("[INFO] These tests should achieve 95%+ coverage for discovery.py")

if __name__ == "__main__":
    asyncio.run(run_final_tests())