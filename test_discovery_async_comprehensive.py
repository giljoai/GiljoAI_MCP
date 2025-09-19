"""
Comprehensive async tests for discovery.py to achieve 95%+ coverage
Tests all uncovered async methods and error scenarios
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

class TestPathResolverAsync:
    """Test PathResolver async methods"""
    
    def __init__(self):
        self.db_path = None
        self.db_manager = None
        self.tenant_manager = None
        self.path_resolver = None
        
    async def setup(self):
        """Setup test environment"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            self.db_path = tmp.name
        
        self.db_manager = DatabaseManager(f'sqlite:///{self.db_path}')
        self.db_manager.create_tables()
        self.tenant_manager = TenantManager()
        self.path_resolver = PathResolver(self.db_manager, self.tenant_manager)
        
    async def cleanup(self):
        """Cleanup test environment"""
        try:
            if self.db_path and os.path.exists(self.db_path):
                os.unlink(self.db_path)
        except (PermissionError, OSError):
            pass
            
    async def test_resolve_path_default(self):
        """Test resolve_path with default values"""
        print("  Testing resolve_path default...")
        result = await self.path_resolver.resolve_path("vision")
        assert result == Path("docs/Vision")
        print("    [OK] Default path resolution")
        
    async def test_resolve_path_with_env_var(self):
        """Test resolve_path with environment variable override"""
        print("  Testing resolve_path with env var...")
        with patch.dict(os.environ, {'GILJO_MCP_PATH_VISION': '/custom/vision/path'}):
            self.path_resolver.clear_cache()  # Force refresh
            result = await self.path_resolver.resolve_path("vision")
            assert result == Path("/custom/vision/path")
        print("    [OK] Environment variable override")
        
    async def test_resolve_path_with_project_id(self):
        """Test resolve_path with project ID"""
        print("  Testing resolve_path with project_id...")
        result = await self.path_resolver.resolve_path("vision", "test-project-123")
        assert isinstance(result, Path)
        print("    [OK] Project-specific path resolution")
        
    async def test_get_all_paths(self):
        """Test get_all_paths async method"""
        print("  Testing get_all_paths...")
        paths = await self.path_resolver.get_all_paths()
        assert isinstance(paths, dict)
        assert "vision" in paths
        assert "docs" in paths
        assert "config" in paths
        print("    [OK] get_all_paths")
        
    async def test_get_all_paths_with_project(self):
        """Test get_all_paths with project ID"""
        print("  Testing get_all_paths with project_id...")
        paths = await self.path_resolver.get_all_paths("test-project-456")
        assert isinstance(paths, dict)
        assert len(paths) >= 8  # Should have all default paths
        print("    [OK] get_all_paths with project")
        
    async def test_get_database_path_not_found(self):
        """Test _get_database_path when no config exists"""
        print("  Testing _get_database_path not found...")
        result = await self.path_resolver._get_database_path("vision", "non-existent-project")
        assert result is None
        print("    [OK] Database path not found")
        
    async def test_get_config_file_path_not_found(self):
        """Test _get_config_file_path when no config file exists"""
        print("  Testing _get_config_file_path not found...")
        # Ensure no config file exists
        with patch('pathlib.Path.exists', return_value=False):
            result = await self.path_resolver._get_config_file_path("vision")
            assert result is None
        print("    [OK] Config file path not found")
        
    async def test_get_config_file_path_found(self):
        """Test _get_config_file_path when config file exists"""
        print("  Testing _get_config_file_path found...")
        config_data = {"paths": {"vision": "/config/vision/path"}}
        config_content = yaml.dump(config_data)
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=config_content)):
                result = await self.path_resolver._get_config_file_path("vision")
                assert result == "/config/vision/path"
        print("    [OK] Config file path found")
        
    async def test_cache_functionality(self):
        """Test cache TTL and validity"""
        print("  Testing cache functionality...")
        
        # Test cache miss
        assert not self.path_resolver._is_cache_valid("non-existent-key")
        
        # Test cache hit
        test_path = Path("/test/cache/path")
        self.path_resolver._update_cache("test-key", test_path)
        assert self.path_resolver._is_cache_valid("test-key")
        assert self.path_resolver._cache["test-key"] == test_path
        print("    [OK] Cache functionality")


class TestDiscoveryManagerAsync:
    """Test DiscoveryManager async methods"""
    
    def __init__(self):
        self.db_path = None
        self.db_manager = None
        self.tenant_manager = None
        self.path_resolver = None
        self.discovery_manager = None
        
    async def setup(self):
        """Setup test environment"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            self.db_path = tmp.name
        
        self.db_manager = DatabaseManager(f'sqlite:///{self.db_path}')
        self.db_manager.create_tables()
        self.tenant_manager = TenantManager()
        self.path_resolver = PathResolver(self.db_manager, self.tenant_manager)
        self.discovery_manager = DiscoveryManager(self.db_manager, self.tenant_manager, self.path_resolver)
        
    async def cleanup(self):
        """Cleanup test environment"""
        try:
            if self.db_path and os.path.exists(self.db_path):
                os.unlink(self.db_path)
        except (PermissionError, OSError):
            pass
            
    async def test_discover_context_orchestrator(self):
        """Test discover_context for orchestrator role"""
        print("  Testing discover_context orchestrator...")
        context = await self.discovery_manager.discover_context("orchestrator", "test-project-1")
        assert isinstance(context, dict)
        assert "metadata" in context
        assert context["metadata"]["agent_role"] == "orchestrator"
        assert "tokens_used" in context
        print("    [OK] Orchestrator context discovery")
        
    async def test_discover_context_analyzer(self):
        """Test discover_context for analyzer role"""
        print("  Testing discover_context analyzer...")
        context = await self.discovery_manager.discover_context("analyzer", "test-project-2")
        assert isinstance(context, dict)
        assert context["metadata"]["agent_role"] == "analyzer"
        print("    [OK] Analyzer context discovery")
        
    async def test_discover_context_with_force_refresh(self):
        """Test discover_context with force refresh"""
        print("  Testing discover_context force refresh...")
        context = await self.discovery_manager.discover_context("implementer", "test-project-3", force_refresh=True)
        assert isinstance(context, dict)
        assert context["metadata"]["agent_role"] == "implementer"
        print("    [OK] Force refresh context discovery")
        
    async def test_load_by_priority_token_limit(self):
        """Test load_by_priority with token limits"""
        print("  Testing load_by_priority token limits...")
        priorities = ["config", "docs"]
        context = await self.discovery_manager.load_by_priority(priorities, "test-project-4", 1000)
        assert isinstance(context, dict)
        assert "tokens_used" in context
        assert context["tokens_used"] <= 1000
        print("    [OK] Token limited loading")
        
    async def test_load_vision_no_db_no_files(self):
        """Test _load_vision when no database or files exist"""
        print("  Testing _load_vision no data...")
        result = await self.discovery_manager._load_vision("non-existent-project", 5000)
        assert result is None
        print("    [OK] Vision loading with no data")
        
    async def test_load_config_empty(self):
        """Test _load_config with empty configuration"""
        print("  Testing _load_config empty...")
        result = await self.discovery_manager._load_config("test-project-5", 5000)
        assert isinstance(result, dict)
        assert "content" in result
        print("    [OK] Config loading empty")
        
    async def test_load_docs_no_files(self):
        """Test _load_docs when no doc files exist"""
        print("  Testing _load_docs no files...")
        with patch('pathlib.Path.exists', return_value=False):
            result = await self.discovery_manager._load_docs("test-project-6", 5000)
            assert isinstance(result, dict)
            assert result["content"] == {}
        print("    [OK] Docs loading no files")
        
    async def test_load_docs_with_files(self):
        """Test _load_docs when files exist"""
        print("  Testing _load_docs with files...")
        mock_content = "# Test CLAUDE.md content\nThis is test documentation."
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.read_text', return_value=mock_content):
                result = await self.discovery_manager._load_docs("test-project-7", 5000)
                assert isinstance(result, dict)
                assert "content" in result
                assert len(result["content"]) > 0
        print("    [OK] Docs loading with files")
        
    async def test_load_memories_no_dirs(self):
        """Test _load_memories when directories don't exist"""
        print("  Testing _load_memories no dirs...")
        with patch('pathlib.Path.exists', return_value=False):
            result = await self.discovery_manager._load_memories("test-project-8", 5000)
            assert isinstance(result, dict)
            assert result["content"] == {}
        print("    [OK] Memories loading no dirs")
        
    async def test_load_memories_with_sessions(self):
        """Test _load_memories with session files"""
        print("  Testing _load_memories with sessions...")
        
        # Mock session files
        mock_files = [Path("session1.md"), Path("session2.md")]
        mock_content = "# Session Memory\nTest session content"
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.is_dir', return_value=True):
                with patch('pathlib.Path.glob', return_value=mock_files):
                    with patch('pathlib.Path.read_text', return_value=mock_content):
                        # Mock file stats for sorting
                        with patch('pathlib.Path.stat') as mock_stat:
                            mock_stat.return_value.st_mtime = 1234567890
                            result = await self.discovery_manager._load_memories("test-project-9", 5000)
                            assert isinstance(result, dict)
                            assert "content" in result
        print("    [OK] Memories loading with sessions")
        
    async def test_load_code_placeholder(self):
        """Test _load_code placeholder implementation"""
        print("  Testing _load_code placeholder...")
        result = await self.discovery_manager._load_code("test-project-10", 5000)
        assert isinstance(result, dict)
        assert "content" in result
        assert "available_tools" in result["content"]
        print("    [OK] Code loading placeholder")
        
    async def test_detect_changes_no_paths(self):
        """Test detect_changes when no paths exist"""
        print("  Testing detect_changes no paths...")
        with patch.object(self.discovery_manager, 'get_discovery_paths', return_value={}):
            changes = await self.discovery_manager.detect_changes("test-project-11")
            assert isinstance(changes, dict)
        print("    [OK] Change detection no paths")
        
    async def test_detect_changes_with_files(self):
        """Test detect_changes with existing files"""
        print("  Testing detect_changes with files...")
        mock_paths = {"docs": Path("test_docs.md")}
        
        with patch.object(self.discovery_manager, 'get_discovery_paths', return_value=mock_paths):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('pathlib.Path.is_file', return_value=True):
                    with patch('pathlib.Path.read_text', return_value="test content"):
                        changes = await self.discovery_manager.detect_changes("test-project-12")
                        assert isinstance(changes, dict)
                        assert "docs" in changes
        print("    [OK] Change detection with files")
        
    async def test_get_discovery_paths(self):
        """Test get_discovery_paths async method"""
        print("  Testing get_discovery_paths...")
        paths = await self.discovery_manager.get_discovery_paths("test-project-13")
        assert isinstance(paths, dict)
        print("    [OK] Discovery paths retrieval")


class TestSerenaHooksAsync:
    """Test SerenaHooks async methods"""
    
    def __init__(self):
        self.db_path = None
        self.db_manager = None
        self.tenant_manager = None
        self.serena_hooks = None
        
    async def setup(self):
        """Setup test environment"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            self.db_path = tmp.name
        
        self.db_manager = DatabaseManager(f'sqlite:///{self.db_path}')
        self.db_manager.create_tables()
        self.tenant_manager = TenantManager()
        self.serena_hooks = SerenaHooks(self.db_manager, self.tenant_manager)
        
    async def cleanup(self):
        """Cleanup test environment"""
        try:
            if self.db_path and os.path.exists(self.db_path):
                os.unlink(self.db_path)
        except (PermissionError, OSError):
            pass
            
    async def test_lazy_load_symbols(self):
        """Test lazy_load_symbols async method"""
        print("  Testing lazy_load_symbols...")
        result = await self.serena_hooks.lazy_load_symbols("test_file.py", depth=1, max_chars=1000)
        assert isinstance(result, dict)
        assert "file" in result
        assert result["file"] == "test_file.py"
        print("    [OK] Lazy load symbols")
        
    async def test_search_codebase(self):
        """Test search_codebase async method"""
        print("  Testing search_codebase...")
        result = await self.serena_hooks.search_codebase("test_pattern", max_chars=2000)
        assert isinstance(result, dict)
        assert "pattern" in result
        assert result["pattern"] == "test_pattern"
        print("    [OK] Search codebase")
        
    async def test_search_codebase_with_include(self):
        """Test search_codebase with paths_include"""
        print("  Testing search_codebase with include...")
        result = await self.serena_hooks.search_codebase("test", max_chars=1000, paths_include="*.py")
        assert isinstance(result, dict)
        print("    [OK] Search codebase with include")
        
    async def test_get_file_overview(self):
        """Test get_file_overview async method"""
        print("  Testing get_file_overview...")
        result = await self.serena_hooks.get_file_overview("src/")
        assert isinstance(result, dict)
        assert "path" in result
        assert result["path"] == "src/"
        print("    [OK] File overview")


async def test_error_scenarios():
    """Test error handling scenarios"""
    print("Testing error scenarios...")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        db_manager = DatabaseManager(f'sqlite:///{db_path}')
        db_manager.create_tables()
        tenant_manager = TenantManager()
        path_resolver = PathResolver(db_manager, tenant_manager)
        discovery_manager = DiscoveryManager(db_manager, tenant_manager, path_resolver)
        
        # Test load_by_priority with unknown priority
        context = await discovery_manager.load_by_priority(["unknown_priority"], "test-project", 1000)
        assert isinstance(context, dict)
        print("  [OK] Unknown priority handling")
        
        # Test _get_config_file_path with YAML error
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', side_effect=IOError("File error")):
                result = await path_resolver._get_config_file_path("vision")
                assert result is None
        print("  [OK] Config file YAML error handling")
        
        # Test _load_vision with database error
        with patch.object(db_manager, 'get_session', side_effect=Exception("DB Error")):
            result = await discovery_manager._load_vision("test-project", 1000)
            assert result is None
        print("  [OK] Vision loading DB error handling")
        
        # Test _load_config with exception
        with patch.object(db_manager, 'get_session', side_effect=Exception("Config DB Error")):
            result = await discovery_manager._load_config("test-project", 1000)
            assert result is None
        print("  [OK] Config loading error handling")
        
        # Test _load_docs with exception
        with patch('pathlib.Path.read_text', side_effect=IOError("File read error")):
            result = await discovery_manager._load_docs("test-project", 1000)
            assert isinstance(result, dict)
        print("  [OK] Docs loading error handling")
        
        # Test _load_memories with exception
        with patch.object(path_resolver, 'resolve_path', side_effect=Exception("Path error")):
            result = await discovery_manager._load_memories("test-project", 1000)
            assert result is None
        print("  [OK] Memories loading error handling")
        
        # Test detect_changes with exception
        with patch.object(discovery_manager, 'get_discovery_paths', side_effect=Exception("Path error")):
            changes = await discovery_manager.detect_changes("test-project")
            assert isinstance(changes, dict)
        print("  [OK] Change detection error handling")
        
    finally:
        try:
            if os.path.exists(db_path):
                os.unlink(db_path)
        except (PermissionError, OSError):
            pass


async def run_all_tests():
    """Run all comprehensive async tests"""
    print("Starting comprehensive async discovery.py tests...")
    
    # Test PathResolver
    print("\n=== PathResolver Async Tests ===")
    path_tests = TestPathResolverAsync()
    await path_tests.setup()
    try:
        await path_tests.test_resolve_path_default()
        await path_tests.test_resolve_path_with_env_var()
        await path_tests.test_resolve_path_with_project_id()
        await path_tests.test_get_all_paths()
        await path_tests.test_get_all_paths_with_project()
        await path_tests.test_get_database_path_not_found()
        await path_tests.test_get_config_file_path_not_found()
        await path_tests.test_get_config_file_path_found()
        await path_tests.test_cache_functionality()
    finally:
        await path_tests.cleanup()
    
    # Test DiscoveryManager
    print("\n=== DiscoveryManager Async Tests ===")
    discovery_tests = TestDiscoveryManagerAsync()
    await discovery_tests.setup()
    try:
        await discovery_tests.test_discover_context_orchestrator()
        await discovery_tests.test_discover_context_analyzer()
        await discovery_tests.test_discover_context_with_force_refresh()
        await discovery_tests.test_load_by_priority_token_limit()
        await discovery_tests.test_load_vision_no_db_no_files()
        await discovery_tests.test_load_config_empty()
        await discovery_tests.test_load_docs_no_files()
        await discovery_tests.test_load_docs_with_files()
        await discovery_tests.test_load_memories_no_dirs()
        await discovery_tests.test_load_memories_with_sessions()
        await discovery_tests.test_load_code_placeholder()
        await discovery_tests.test_detect_changes_no_paths()
        await discovery_tests.test_detect_changes_with_files()
        await discovery_tests.test_get_discovery_paths()
    finally:
        await discovery_tests.cleanup()
    
    # Test SerenaHooks
    print("\n=== SerenaHooks Async Tests ===")
    serena_tests = TestSerenaHooksAsync()
    await serena_tests.setup()
    try:
        await serena_tests.test_lazy_load_symbols()
        await serena_tests.test_search_codebase()
        await serena_tests.test_search_codebase_with_include()
        await serena_tests.test_get_file_overview()
    finally:
        await serena_tests.cleanup()
    
    # Test error scenarios
    print("\n=== Error Handling Tests ===")
    await test_error_scenarios()
    
    print("\n[SUCCESS] All comprehensive async tests passed!")
    print("[INFO] This should achieve 95%+ coverage for discovery.py")


if __name__ == "__main__":
    asyncio.run(run_all_tests())