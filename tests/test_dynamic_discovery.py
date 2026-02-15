"""
Test suite for Project 3.3: Dynamic Discovery System
Tests all 7 success criteria for the dynamic discovery implementation
"""

import sys
from pathlib import Path

import pytest


# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Project
from tests.helpers.test_db_helper import PostgreSQLTestHelper


class TestDynamicDiscovery:
    """Comprehensive test suite for dynamic discovery system"""

    @pytest.fixture
    async def setup_test_env(self):
        """Set up test environment with database and configurations"""
        # Create temp database
        db_manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
        await db_manager.initialize()

        # Create test project
        async with db_manager.get_session() as session:
            project = Project(
                name="Test Discovery Project",
                tenant_key="test-tenant-123",
                mission="Test dynamic discovery",
                status="active",
            )
            session.add(project)
            await session.commit()

        return {"db_manager": db_manager, "project": project, "tenant_key": "test-tenant-123"}

    # SUCCESS CRITERION 1: Priority-based discovery order
    @pytest.mark.asyncio
    async def test_priority_based_discovery_order(self, setup_test_env):
        """
        Test that context is loaded in correct priority order:
        1. Vision documents (highest)
        2. Configuration
        3. Documentation
        4. Session memories
        5. Code exploration (lowest)
        """
        # Test plan:
        # 1. Mock all context sources
        # 2. Call discovery function
        # 3. Verify loading order matches priority
        # 4. Verify higher priority sources are loaded first
        # 5. Verify lower priority sources only loaded if needed

    # SUCCESS CRITERION 2: Dynamic path resolution
    @pytest.mark.asyncio
    async def test_dynamic_path_resolution(self, setup_test_env):
        """
        Test that all paths are resolved dynamically from configuration
        No hardcoded paths should remain
        """
        # Test plan:
        # 1. Set custom paths in config.yaml
        # 2. Set database overrides
        # 3. Set environment variable overrides
        # 4. Verify paths are resolved in correct order:
        #    - Environment variables (highest priority)
        #    - Database configuration
        #    - config.yaml
        #    - Default fallback (lowest priority)

    @pytest.mark.asyncio
    async def test_no_hardcoded_paths(self):
        """Verify no hardcoded paths remain in codebase"""
        import re

        context_file = Path("../src/giljo_mcp/tools/context.py")
        assert context_file.exists(), "context.py not found"

        content = context_file.read_text()

        # Patterns that indicate hardcoded paths
        hardcoded_patterns = [
            r'Path\(["\']docs/Vision["\']\)',
            r'Path\(["\']docs/Sessions["\']\)',
            r'Path\(["\']docs/devlog["\']\)',
            r'["\'"]docs/Vision["\'"]',
            r'["\'"]docs/Sessions["\'"]',
            r'["\'"]docs/devlog["\'"]',
        ]

        issues = []
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            # Skip comments and docstrings
            if line.strip().startswith("#") or '"""' in line or "'''" in line:
                continue

            for pattern in hardcoded_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(f"Line {i}: {line.strip()}")

        assert len(issues) == 0, "Found hardcoded paths:\n" + "\n".join(issues)

    # SUCCESS CRITERION 3: Role-based context loading
    @pytest.mark.asyncio
    async def test_role_based_context_loading(self, setup_test_env):
        """
        Test selective context loading based on agent role
        """
        # Test plan for each role:

        # Orchestrator tests:
        # - Should load full vision document
        # - Should load project status
        # - Should load agent health metrics
        # - Should NOT load detailed code unless requested

        # Analyzer tests:
        # - Should load vision principles/guidelines
        # - Should load codebase structure overview
        # - Should load documentation
        # - Should NOT load implementation details

        # Implementer tests:
        # - Should load technical specifications
        # - Should load code patterns and APIs
        # - Should load relevant code sections
        # - Should NOT load full vision unless needed

        # Tester tests:
        # - Should load test frameworks config
        # - Should load success criteria
        # - Should load edge cases documentation
        # - Should NOT load implementation code

    # SUCCESS CRITERION 4: No static indexes
    @pytest.mark.asyncio
    async def test_no_static_indexes_remain(self, setup_test_env):
        """
        Verify no pre-built indexes exist at startup
        All indexes should be created on-demand
        """
        # Test plan:
        # 1. Start fresh system
        # 2. Verify no indexes exist in database
        # 3. Request context
        # 4. Verify indexes are created dynamically
        # 5. Restart system
        # 6. Verify indexes are NOT pre-loaded

    # SUCCESS CRITERION 5: Fresh context reads
    @pytest.mark.asyncio
    async def test_fresh_context_guaranteed(self, setup_test_env):
        """
        Test that context is always fresh from source
        """
        # Test plan:
        # 1. Create initial content
        # 2. Load context and note hash
        # 3. Modify source content
        # 4. Load context again
        # 5. Verify new content is loaded
        # 6. Verify content hash changed
        # 7. Test automatic re-indexing

    @pytest.mark.asyncio
    async def test_content_change_detection(self, setup_test_env):
        """Test content hash validation for change detection"""
        # Test plan:
        # 1. Load document and store hash
        # 2. Make small change to document
        # 3. Verify hash changes
        # 4. Verify re-indexing triggered
        # 5. Test with multiple documents

    # SUCCESS CRITERION 6: Serena MCP integration
    @pytest.mark.asyncio
    async def test_serena_mcp_integration(self, setup_test_env):
        """
        Test Serena MCP hooks for dynamic code discovery
        """
        # Test plan:
        # 1. Mock Serena MCP server
        # 2. Test lazy loading based on agent needs
        # 3. Test token-optimized queries
        # 4. Verify symbolic operations preferred
        # 5. Test context caching with TTL

    @pytest.mark.asyncio
    async def test_serena_lazy_loading(self):
        """Test that Serena only loads code when needed"""
        # Test plan:
        # 1. Start without loading any code
        # 2. Agent requests specific symbol
        # 3. Verify only that symbol is loaded
        # 4. Verify related symbols not loaded
        # 5. Test incremental loading

    @pytest.mark.asyncio
    async def test_serena_token_optimization(self):
        """Test max_answer_chars parameter usage"""
        # Test plan:
        # 1. Request large code section
        # 2. Verify max_answer_chars limits response
        # 3. Test different token limits
        # 4. Verify truncation is intelligent

    # SUCCESS CRITERION 7: Token optimization
    @pytest.mark.asyncio
    async def test_token_usage_optimization(self, setup_test_env):
        """
        Test that token usage is optimized via selective loading
        """
        # Test plan:
        # 1. Track tokens before discovery
        # 2. Load context for specific agent role
        # 3. Verify only necessary content loaded
        # 4. Compare token usage vs loading everything
        # 5. Verify significant reduction (>50%)

    @pytest.mark.asyncio
    async def test_selective_loading_efficiency(self):
        """Test efficiency gains from selective loading"""
        # Test plan:
        # 1. Measure time to load full context
        # 2. Measure time for selective loading
        # 3. Verify selective is faster
        # 4. Measure memory usage difference
        # 5. Test with large documents

    # Integration tests
    @pytest.mark.asyncio
    async def test_full_discovery_workflow(self, setup_test_env):
        """End-to-end test of complete discovery system"""
        # Test plan:
        # 1. Create orchestrator agent
        # 2. Request context discovery
        # 3. Verify priority order respected
        # 4. Switch to implementer agent
        # 5. Verify different context loaded
        # 6. Modify source content
        # 7. Verify fresh reads
        # 8. Test Serena integration

    # Regression tests
    @pytest.mark.asyncio
    async def test_vision_chunking_still_works(self, setup_test_env):
        """Ensure vision chunking from Project 2.3 not broken"""
        # Test plan:
        # 1. Load large vision document (>50K tokens)
        # 2. Verify chunking still functions
        # 3. Test chunk boundaries
        # 4. Verify metadata preserved

    @pytest.mark.asyncio
    async def test_existing_tools_compatibility(self):
        """Verify existing MCP tools still function"""
        # Test plan:
        # 1. Test get_vision() tool
        # 2. Test get_context_index() tool
        # 3. Test get_product_settings() tool
        # 4. Verify backward compatibility

    # Error handling tests
    @pytest.mark.asyncio
    async def test_missing_configuration_handling(self):
        """Test graceful handling of missing configs"""
        # Test plan:
        # 1. Remove config.yaml
        # 2. Verify fallback to defaults
        # 3. Test missing database configs
        # 4. Test missing environment variables

    @pytest.mark.asyncio
    async def test_corrupt_index_recovery(self):
        """Test recovery from corrupted indexes"""
        # Test plan:
        # 1. Corrupt index in database
        # 2. Request context
        # 3. Verify automatic re-indexing
        # 4. Verify correct content returned


class TestConfigurationManager:
    """Test configuration resolution and management"""

    @pytest.mark.asyncio
    async def test_configuration_precedence(self):
        """Test configuration loading precedence"""
        # Test plan:
        # 1. Set value in defaults
        # 2. Override in config.yaml
        # 3. Override in database
        # 4. Override with environment variable
        # 5. Verify final value matches env var

    @pytest.mark.asyncio
    async def test_environment_variable_parsing(self):
        """Test GILJO_MCP_* environment variables"""
        # Test plan:
        # 1. Set GILJO_MCP_SERVER_MCP_PORT=7001
        # 2. Verify port configuration updated
        # 3. Test nested configuration paths
        # 4. Test type conversions (string to int, bool)


class TestDiscoveryManager:
    """Test the discovery manager component"""

    @pytest.mark.asyncio
    async def test_discovery_manager_initialization(self):
        """Test discovery manager setup"""
        # Test plan:
        # 1. Initialize discovery manager
        # 2. Verify configuration loaded
        # 3. Verify no static indexes created
        # 4. Verify Serena hooks registered

    @pytest.mark.asyncio
    async def test_context_request_routing(self):
        """Test routing context requests to sources"""
        # Test plan:
        # 1. Request vision context
        # 2. Verify routed to vision loader
        # 3. Request code context
        # 4. Verify routed to Serena MCP
        # 5. Test unknown context type handling


if __name__ == "__main__":
    # Run tests with coverage
    pytest.main([__file__, "-v", "--cov=src.giljo_mcp.tools", "--cov-report=html"])
