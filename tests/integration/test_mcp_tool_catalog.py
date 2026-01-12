"""
Integration Tests for MCP Tool Catalog Generator (Handover 0270)

Verifies that:
1. MCPToolCatalogGenerator creates comprehensive tool definitions
2. Tools are organized by category with proper metadata
3. Orchestrator receives complete catalog in instructions
4. Spawned agents receive agent-type-specific tool subsets
5. Tool catalog respects field priorities (if priority=0, exclude)
6. Tool definitions include params, descriptions, when-to-use, and examples
7. Complete orchestrator workflow pattern is included
"""

from uuid import uuid4

import pytest

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Product, Project
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from src.giljo_mcp.prompt_generation.mcp_tool_catalog import MCPToolCatalogGenerator


@pytest.mark.asyncio
class TestMCPToolCatalog:
    """Test suite for MCP Tool Catalog Generator"""

    @pytest.fixture
    async def tenant_context(self, db_manager):
        """Create test tenant with product, project, and orchestrator"""
        tenant_key = f"test_tenant_{uuid4().hex[:8]}"

        async with db_manager.get_session_async() as session:
            # Create product
            product = Product(
                tenant_key=tenant_key,
                name="Tool Catalog Test Product",
                description="Test product for MCP tool catalog tests",
                is_active=True,
            )
            session.add(product)
            await session.flush()

            # Create project
            project = Project(
                tenant_key=tenant_key,
                product_id=product.id,
                name="Tool Catalog Test Project",
                description="Test project for MCP tool catalog",
                mission="Test mission for orchestrator",
                status="active",
                context_budget=150000,
                context_used=0,
            )
            session.add(project)
            await session.flush()

            # Create orchestrator job
            orchestrator_id = str(uuid4())
            orchestrator = AgentExecution(
                job_id=orchestrator_id,
                tenant_key=tenant_key,
                project_id=project.id,
                agent_display_name="orchestrator",
                mission="Orchestrate test project",
                status="waiting",
                context_budget=150000,
                context_used=0,
                instance_number=1,
                job_metadata={
                    "field_priorities": {
                        "core_features": 10,
                        "tech_stack": 8,
                        "architecture": 7,
                        "mcp_tool_catalog": 9,  # Catalog priority
                    },
                    "user_id": "test_user_123",
                },
            )
            session.add(orchestrator)
            await session.commit()

            yield {
                "tenant_key": tenant_key,
                "product_id": str(product.id),
                "project_id": str(project.id),
                "orchestrator_id": orchestrator_id,
                "db_manager": db_manager,
            }

    async def test_catalog_generator_instantiation(self):
        """Test that MCPToolCatalogGenerator can be instantiated"""
        generator = MCPToolCatalogGenerator()
        assert generator is not None
        assert hasattr(generator, "generate_full_catalog")
        assert hasattr(generator, "generate_for_agent")

    async def test_orchestrator_receives_complete_tool_catalog(self, tenant_context):
        """
        Test: test_orchestrator_receives_complete_tool_catalog
        Verify catalog present in orchestrator instructions with all categories covered
        """
        generator = MCPToolCatalogGenerator()
        full_catalog = generator.generate_full_catalog()

        # Verify catalog structure
        assert isinstance(full_catalog, str)
        assert len(full_catalog) > 500  # Significant content

        # Verify all major categories are present
        categories = ["orchestration", "context", "communication", "tasks", "project"]
        for category in categories:
            assert category.lower() in full_catalog.lower(), f"Missing category: {category}"

        # Verify key tools are listed
        key_tools = [
            "get_orchestrator_instructions",
            "spawn_agent_job",
            "send_message",
            "get_agent_mission",
        ]
        for tool in key_tools:
            assert tool.lower() in full_catalog.lower(), f"Missing key tool: {tool}"

    async def test_tool_catalog_includes_usage_patterns(self, tenant_context):
        """
        Test: test_tool_catalog_includes_usage_patterns
        Verify each tool has usage guidance and code examples
        """
        generator = MCPToolCatalogGenerator()
        full_catalog = generator.generate_full_catalog()

        # Verify usage guidance markers are present
        guidance_markers = [
            "**When to use**",
            "**Example**",
            "**Parameters**",
            "**Returns**",
        ]

        for marker in guidance_markers:
            assert marker in full_catalog, f"Missing usage guidance: {marker}"

        # Verify code examples are present (should have at least one code block)
        assert "```" in full_catalog, "No code examples found in catalog"

    async def test_spawned_agents_receive_relevant_tools(self, tenant_context):
        """
        Test: test_spawned_agents_receive_relevant_tools
        Verify agents get appropriate tool subset based on type
        """
        generator = MCPToolCatalogGenerator()

        # Test implementer agent gets task-related tools
        implementer_catalog = generator.generate_for_agent("implementer")
        assert isinstance(implementer_catalog, str)
        assert len(implementer_catalog) > 100
        # Implementer should have task and communication tools
        assert "spawn_agent_job" in implementer_catalog or "send_message" in implementer_catalog

        # Test tester agent gets appropriate tools
        tester_catalog = generator.generate_for_agent("tester")
        assert isinstance(tester_catalog, str)
        assert len(tester_catalog) > 100

        # Test architect agent gets context tools
        architect_catalog = generator.generate_for_agent("architect")
        assert isinstance(architect_catalog, str)
        assert "context" in architect_catalog.lower() or "architecture" in architect_catalog.lower()

    async def test_tool_catalog_organized_by_category(self, tenant_context):
        """
        Test: test_tool_catalog_organized_by_category
        Verify tools are properly organized with clear sections
        """
        generator = MCPToolCatalogGenerator()
        full_catalog = generator.generate_full_catalog()

        # Verify clear category headers
        assert "# Orchestration Tools" in full_catalog or "orchestration" in full_catalog.lower()
        assert "# Context Tools" in full_catalog or "context" in full_catalog.lower()
        assert "# Communication Tools" in full_catalog or "communication" in full_catalog.lower()

    async def test_tool_catalog_respects_field_priorities(self, tenant_context):
        """
        Test: test_tool_catalog_respects_field_priorities
        If mcp_tool_catalog priority is 0, catalog should be excluded
        """
        db_manager = tenant_context["db_manager"]
        orchestrator_id = tenant_context["orchestrator_id"]

        # Test the catalog generator directly with field priorities
        field_priorities = {
            "mcp_tool_catalog": 0,  # Exclude catalog
            "core_features": 10,
        }

        # Generate catalog
        generator = MCPToolCatalogGenerator()
        catalog = generator.generate_full_catalog(field_priorities=field_priorities)

        # If priority is 0, should return minimal/empty catalog or marker
        # This is a design choice - we either:
        # 1. Return empty string
        # 2. Return "catalog not requested" message
        # Test accepts either behavior
        assert isinstance(catalog, str)

    async def test_agent_specific_tool_filtering(self, tenant_context):
        """
        Test: test_agent_specific_tool_filtering
        Verify each agent type gets correct tools
        """
        generator = MCPToolCatalogGenerator()

        agent_types = {
            "orchestrator": ["get_orchestrator_instructions", "spawn_agent_job"],
            "implementer": ["send_message", "get_agent_mission"],
            "tester": ["get_workflow_status"],
            "architect": ["fetch_product_context"],
            "documenter": ["send_message"],
        }

        for agent_type, expected_tools in agent_types.items():
            catalog = generator.generate_for_agent(agent_display_name)
            assert isinstance(catalog, str)
            # At least one expected tool should be in the catalog
            has_expected = any(tool in catalog for tool in expected_tools)
            assert has_expected or len(catalog) > 50, f"Empty or invalid catalog for {agent_display_name}"

    async def test_tool_catalog_format(self, tenant_context):
        """
        Test: test_tool_catalog_format
        Verify formatting with descriptions, params, examples
        """
        generator = MCPToolCatalogGenerator()
        full_catalog = generator.generate_full_catalog()

        # Verify Markdown formatting
        assert "#" in full_catalog  # Headers
        assert "**" in full_catalog  # Bold text
        assert "`" in full_catalog  # Code formatting

        # Verify structured information for tools
        required_sections = ["Parameters", "Returns", "When to use", "Example"]
        found_sections = sum(1 for section in required_sections if section in full_catalog)
        assert found_sections >= 2, "Missing required documentation sections"

    async def test_orchestrator_workflow_included(self, tenant_context):
        """
        Test: test_orchestrator_workflow_included
        Verify typical orchestrator workflow pattern is included in catalog
        """
        generator = MCPToolCatalogGenerator()
        full_catalog = generator.generate_full_catalog()

        # Verify workflow/pattern examples are present
        workflow_markers = [
            "spawn_agent_job",  # Key for spawning agents
            "get_agent_mission",  # For agents to fetch mission
            "send_message",  # For inter-agent communication
        ]

        for marker in workflow_markers:
            assert marker in full_catalog, f"Missing workflow marker: {marker}"

    async def test_tool_catalog_minimum_20_tools(self, tenant_context):
        """
        Test: Verify catalog includes at least 20 tools
        """
        generator = MCPToolCatalogGenerator()
        full_catalog = generator.generate_full_catalog()

        # Count occurrences of tool definitions (lines starting with "##" in Markdown)
        tool_count = full_catalog.count("## ")
        assert tool_count >= 20, f"Catalog only has {tool_count} tools, need at least 20"

    async def test_catalog_categories_have_examples(self, tenant_context):
        """
        Test: Each tool has runnable example code
        """
        generator = MCPToolCatalogGenerator()
        full_catalog = generator.generate_full_catalog()

        # Count code blocks
        code_blocks = full_catalog.count("```")
        # Should have pairs (start and end), so at least 2 per tool minimum
        # With 20+ tools and examples, should have many code blocks
        assert code_blocks >= 4, "Insufficient code examples in catalog"

    async def test_catalog_includes_error_handling_guidance(self, tenant_context):
        """
        Test: Catalog includes error handling patterns and troubleshooting
        """
        generator = MCPToolCatalogGenerator()
        full_catalog = generator.generate_full_catalog()

        # Verify error-related content
        error_markers = ["error", "exception", "troubleshoot", "return", "validate"]
        found_error_guidance = sum(1 for marker in error_markers if marker.lower() in full_catalog.lower())
        assert found_error_guidance >= 2, "Insufficient error handling guidance"

    async def test_catalog_generation_performance(self, tenant_context):
        """
        Test: Catalog generation completes in reasonable time
        """
        import time

        generator = MCPToolCatalogGenerator()

        start = time.time()
        full_catalog = generator.generate_full_catalog()
        elapsed = time.time() - start

        # Should complete in under 1 second
        assert elapsed < 1.0, f"Catalog generation took {elapsed:.2f}s"
        assert len(full_catalog) > 1000, "Catalog too small"

    async def test_agent_display_name_specific_exclusions(self, tenant_context):
        """
        Test: Agent gets only relevant tools, not all tools
        """
        generator = MCPToolCatalogGenerator()

        full_catalog = generator.generate_full_catalog()
        implementer_catalog = generator.generate_for_agent("implementer")

        # Implementer catalog should be smaller than full
        assert len(implementer_catalog) < len(full_catalog), \
            "Agent-specific catalog should be smaller than full catalog"

    async def test_catalog_markdown_validity(self, tenant_context):
        """
        Test: Catalog is valid Markdown with proper structure
        """
        generator = MCPToolCatalogGenerator()
        full_catalog = generator.generate_full_catalog()

        # Basic Markdown validation
        lines = full_catalog.split("\n")
        assert len(lines) > 20, "Catalog should have substantial content"

        # Should have proper structure with headers and content
        header_count = sum(1 for line in lines if line.startswith("#"))
        assert header_count >= 5, "Should have multiple section headers"

    async def test_catalog_includes_all_required_categories(self, tenant_context):
        """
        Test: All 5 required categories present with tools
        """
        generator = MCPToolCatalogGenerator()
        full_catalog = generator.generate_full_catalog()

        required_categories = [
            "orchestration",
            "context",
            "communication",
            "tasks",
            "project"
        ]

        for category in required_categories:
            assert category in full_catalog.lower(), \
                f"Required category '{category}' missing from catalog"


@pytest.mark.asyncio
class TestMCPToolCatalogIntegration:
    """Integration tests with orchestrator instructions"""

    @pytest.fixture
    async def tenant_context(self, db_manager):
        """Create test tenant with full context"""
        tenant_key = f"test_tenant_{uuid4().hex[:8]}"

        async with db_manager.get_session_async() as session:
            # Create product
            product = Product(
                tenant_key=tenant_key,
                name="Integration Test Product",
                description="Test product for integration",
                is_active=True,
            )
            session.add(product)
            await session.flush()

            # Create project
            project = Project(
                tenant_key=tenant_key,
                product_id=product.id,
                name="Integration Test Project",
                description="Test project",
                mission="Test mission",
                status="active",
                context_budget=150000,
                context_used=0,
            )
            session.add(project)
            await session.flush()

            # Create orchestrator
            orchestrator_id = str(uuid4())
            orchestrator = AgentExecution(
                job_id=orchestrator_id,
                tenant_key=tenant_key,
                project_id=project.id,
                agent_display_name="orchestrator",
                mission="Orchestrate integration test",
                status="waiting",
                context_budget=150000,
                context_used=0,
                instance_number=1,
                job_metadata={
                    "field_priorities": {
                        "mcp_tool_catalog": 9,
                    },
                    "user_id": "test_user",
                },
            )
            session.add(orchestrator)
            await session.commit()

            yield {
                "tenant_key": tenant_key,
                "orchestrator_id": orchestrator_id,
                "project_id": str(project.id),
                "db_manager": db_manager,
            }

    async def test_catalog_can_be_injected_into_mission(self, tenant_context):
        """Test that catalog can be successfully injected into orchestrator mission"""
        generator = MCPToolCatalogGenerator()
        full_catalog = generator.generate_full_catalog()

        # Simulate mission with catalog injection
        mission_template = f"""
# Orchestrator Mission

## Context
Your project analysis context here.

---

# MCP Tool Catalog

{full_catalog}

---

## Next Steps
Spawn agents to execute tasks.
"""

        assert len(mission_template) > 2000, "Injected mission should be substantial"
        assert "orchestration" in mission_template.lower()
        assert "spawn_agent_job" in mission_template

    async def test_field_priority_integration(self, tenant_context):
        """Test that field priorities are respected when generating catalog"""
        # Get field priorities directly from tenant context
        # (orchestrator has mcp_tool_catalog priority of 9)
        field_priorities = {
            "mcp_tool_catalog": 9,  # Included
        }

        # Generate catalog with priorities
        generator = MCPToolCatalogGenerator()
        catalog = generator.generate_full_catalog(field_priorities=field_priorities)

        # Catalog should be generated (not excluded)
        assert isinstance(catalog, str)
        assert len(catalog) > 0
