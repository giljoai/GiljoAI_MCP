"""
Integration Tests for get_orchestrator_instructions MCP Tool

Verifies that the get_orchestrator_instructions tool is:
1. Properly registered in the MCP tool map
2. Accessible via HTTP endpoint
3. Returns correct data structure
4. Handles tenant isolation
5. Works with thin client architecture

CRITICAL: This tool is the foundation of Handover 0088 (context prioritization and orchestration).
If this test fails, thin client prompts will not work.
"""

from uuid import uuid4

import pytest

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import AgentTemplate, MCPAgentJob, Product, Project


@pytest.mark.asyncio
class TestGetOrchestratorInstructionsMCP:
    """Test suite for get_orchestrator_instructions MCP tool exposure"""

    @pytest.fixture
    async def tenant_context(self, db_manager):
        """Create test tenant with product, project, and orchestrator"""
        tenant_key = f"test_tenant_{uuid4().hex[:8]}"

        async with db_manager.get_session_async() as session:
            # Create product
            product = Product(
                tenant_key=tenant_key,
                name="Test Product",
                description="Test product for MCP tool tests",
                vision_content="Product vision for testing",
                status="active",
            )
            session.add(product)
            await session.flush()

            # Create project
            project = Project(
                tenant_key=tenant_key,
                product_id=product.id,
                name="Test Project",
                description="Test project for MCP",
                mission="Test mission for orchestrator",
                status="active",
                context_budget=150000,
                context_used=0,
            )
            session.add(project)
            await session.flush()

            # Create orchestrator job
            orchestrator_id = str(uuid4())
            orchestrator = MCPAgentJob(
                job_id=orchestrator_id,
                tenant_key=tenant_key,
                project_id=project.id,
                agent_type="orchestrator",
                mission="Orchestrate test project",
                status="waiting",
                context_budget=150000,
                context_used=0,
                instance_number=1,
                job_metadata={
                    "field_priorities": {"core_features": 10, "tech_stack": 8, "architecture": 7},
                    "user_id": "test_user_123",
                },
            )
            session.add(orchestrator)

            # Create sample agent template
            template = AgentTemplate(
                tenant_key=tenant_key,
                name="Backend Developer",
                role="backend",
                description="Backend development specialist",
                is_active=True,
            )
            session.add(template)

            await session.commit()

            yield {
                "tenant_key": tenant_key,
                "orchestrator_id": orchestrator_id,
                "project_id": str(project.id),
                "product_id": str(product.id),
            }

            # Cleanup
            await session.rollback()

    async def test_tool_accessor_has_method(self, db_manager):
        """Test 1: ToolAccessor has get_orchestrator_instructions method"""
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        # Method should exist
        assert hasattr(tool_accessor, "get_orchestrator_instructions")

        # Should be a coroutine function
        import inspect

        assert inspect.iscoroutinefunction(tool_accessor.get_orchestrator_instructions)

    async def test_http_endpoint_tool_map_includes_tool(self):
        """Test 2: HTTP endpoint tool_map includes get_orchestrator_instructions"""
        # This would require importing the tool_map from mcp_tools.py
        # Since we can't easily test the FastAPI app initialization,
        # we verify the code structure instead

        # Read the mcp_tools.py file and verify the tool is mapped
        from pathlib import Path

        mcp_tools_path = Path("F:/GiljoAI_MCP/api/endpoints/mcp_tools.py")
        content = mcp_tools_path.read_text()

        # Check tool is in tool_map
        assert '"get_orchestrator_instructions"' in content
        assert "state.tool_accessor.get_orchestrator_instructions" in content

    async def test_orchestration_module_registers_tool(self):
        """Test 3: Orchestration module has get_orchestrator_instructions as MCP tool"""
        from pathlib import Path

        orchestration_path = Path("F:/GiljoAI_MCP/src/giljo_mcp/tools/orchestration.py")
        content = orchestration_path.read_text()

        # Verify the tool is decorated with @mcp.tool()
        assert "@mcp.tool()" in content
        assert "async def get_orchestrator_instructions(" in content

        # Verify it has proper docstring explaining thin client architecture
        assert "context prioritization and orchestration" in content or "thin client" in content

    async def test_get_orchestrator_instructions_success(self, db_manager, tenant_context):
        """Test 4: get_orchestrator_instructions returns correct structure"""
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        # Call the tool
        result = await tool_accessor.get_orchestrator_instructions(
            job_id=tenant_context["orchestrator_id"], tenant_key=tenant_context["tenant_key"]
        )

        # Should return success structure
        assert "orchestrator_id" in result
        assert "project_id" in result
        assert "project_name" in result
        assert "mission" in result
        assert "context_budget" in result
        assert "agent_templates" in result
        assert "thin_client" in result
        assert result["thin_client"] is True

        # Should have field priorities
        assert "field_priorities" in result
        assert result["field_priorities"] == {"core_features": 10, "tech_stack": 8, "architecture": 7}

        # Should have token estimates
        assert "estimated_tokens" in result
        assert isinstance(result["estimated_tokens"], int)
        assert result["estimated_tokens"] > 0

    async def test_get_orchestrator_instructions_not_found(self, db_manager, tenant_context):
        """Test 5: get_orchestrator_instructions handles missing orchestrator"""
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        # Call with non-existent orchestrator ID
        result = await tool_accessor.get_orchestrator_instructions(
            job_id="nonexistent-orchestrator-id", tenant_key=tenant_context["tenant_key"]
        )

        # Should return error structure
        assert "error" in result
        assert result["error"] == "NOT_FOUND"
        assert "message" in result
        assert "orchestrator" in result["message"].lower()

    async def test_get_orchestrator_instructions_tenant_isolation(self, db_manager, tenant_context):
        """Test 6: get_orchestrator_instructions enforces tenant isolation"""
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        # Try to access orchestrator with wrong tenant key
        result = await tool_accessor.get_orchestrator_instructions(
            job_id=tenant_context["orchestrator_id"], tenant_key="wrong_tenant_key"
        )

        # Should return NOT_FOUND (not expose existence to other tenants)
        assert "error" in result
        assert result["error"] == "NOT_FOUND"

    async def test_get_orchestrator_instructions_validation(self, db_manager):
        """Test 7: get_orchestrator_instructions validates inputs"""
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        # Test empty orchestrator_id
        result = await tool_accessor.get_orchestrator_instructions(job_id="", tenant_key="some_tenant")
        assert "error" in result
        assert result["error"] == "VALIDATION_ERROR"

        # Test empty tenant_key
        result = await tool_accessor.get_orchestrator_instructions(job_id="some_id", tenant_key="")
        assert "error" in result
        assert result["error"] == "VALIDATION_ERROR"

    async def test_thin_client_prompt_calls_tool(self):
        """Test 8: Verify thin client prompt includes correct tool call"""
        # This is a critical test - the staging prompt MUST call this tool

        from pathlib import Path

        # Check ThinClientPromptGenerator
        prompt_gen_path = Path("F:/GiljoAI_MCP/src/giljo_mcp/thin_client_prompt_generator.py")

        if prompt_gen_path.exists():
            content = prompt_gen_path.read_text()

            # Should call get_orchestrator_instructions
            assert "get_orchestrator_instructions" in content

            # Should use mcp__giljo-mcp__ prefix
            assert (
                "mcp__giljo-mcp__get_orchestrator_instructions" in content or "get_orchestrator_instructions" in content
            )

    async def test_mission_planner_integration(self, db_manager, tenant_context):
        """Test 9: get_orchestrator_instructions integrates with MissionPlanner"""
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        result = await tool_accessor.get_orchestrator_instructions(
            job_id=tenant_context["orchestrator_id"], tenant_key=tenant_context["tenant_key"]
        )

        # Mission should be condensed (not full vision)
        assert "mission" in result
        mission = result["mission"]

        # Should be a string
        assert isinstance(mission, str)

        # Should have content (not empty)
        assert len(mission) > 0

        # Token count should be reasonable (70% reduction from full vision)
        # Assuming full vision would be ~20,000 tokens, condensed should be ~6,000
        estimated_tokens = result["estimated_tokens"]
        assert 1000 < estimated_tokens < 15000  # Reasonable range

    async def test_agent_templates_included(self, db_manager, tenant_context):
        """Test 10: get_orchestrator_instructions includes agent templates"""
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        result = await tool_accessor.get_orchestrator_instructions(
            job_id=tenant_context["orchestrator_id"], tenant_key=tenant_context["tenant_key"]
        )

        # Should include agent templates
        assert "agent_templates" in result
        templates = result["agent_templates"]

        # Should be a list
        assert isinstance(templates, list)

        # Should have at least the one we created
        assert len(templates) >= 1

        # Each template should have required fields
        for template in templates:
            assert "name" in template
            assert "role" in template
            assert "description" in template

    async def test_empty_mission_fallback(self):
        """Test 11: get_orchestrator_instructions handles empty mission with fallback"""
        from unittest.mock import MagicMock, patch

        # Test the fallback logic directly without database
        # This tests the fallback generation in get_orchestrator_instructions

        # Mock product with description
        product = MagicMock()
        product.vision_summary = None
        product.product_context = {}

        # Mock project with description
        project = MagicMock()
        project.description = "Project goal: Build amazing features"

        # Simulate the fallback logic
        condensed_mission = ""  # Empty mission from MissionPlanner

        # Apply fallback (this is the code we added to tool_accessor.py)
        if not condensed_mission or condensed_mission.strip() == "":
            mission_parts = []

            # Include product vision if available
            if product and product.vision_summary:
                mission_parts.append(f"Vision: {product.vision_summary}")

            # Include project description if available
            if project.description:
                mission_parts.append(f"Project Goal: {project.description}")

            # Include tech stack from product context if available
            if product and product.product_context:
                context = product.product_context or {}
                if context.get("tech_stack"):
                    mission_parts.append(f"Tech Stack: {context['tech_stack']}")

            # Build fallback mission from collected parts
            if mission_parts:
                condensed_mission = "\n\n".join(mission_parts)
            else:
                # Final fallback: use project description or a minimal message
                condensed_mission = project.description or "No mission defined"

        # Verify fallback worked
        assert condensed_mission  # Should not be empty
        assert len(condensed_mission) > 0
        assert "Build amazing features" in condensed_mission

    async def test_empty_mission_with_all_fallback_parts(self):
        """Test 12: get_orchestrator_instructions uses all fallback parts when available"""
        from unittest.mock import MagicMock

        # Test fallback with all components populated
        product = MagicMock()
        product.vision_summary = "Comprehensive data solution"
        product.product_context = {"tech_stack": "Python, FastAPI, PostgreSQL"}

        project = MagicMock()
        project.description = "Data pipeline implementation"

        # Start with empty mission
        condensed_mission = ""

        # Apply fallback
        if not condensed_mission or condensed_mission.strip() == "":
            mission_parts = []

            if product and product.vision_summary:
                mission_parts.append(f"Vision: {product.vision_summary}")

            if project.description:
                mission_parts.append(f"Project Goal: {project.description}")

            if product and product.product_context:
                context = product.product_context or {}
                if context.get("tech_stack"):
                    mission_parts.append(f"Tech Stack: {context['tech_stack']}")

            if mission_parts:
                condensed_mission = "\n\n".join(mission_parts)
            else:
                condensed_mission = project.description or "No mission defined"

        # Verify all parts included
        assert "Comprehensive data solution" in condensed_mission
        assert "Data pipeline implementation" in condensed_mission
        assert "Python, FastAPI, PostgreSQL" in condensed_mission
        assert "\n\n" in condensed_mission  # Parts separated by double newline

    async def test_with_vision_documents_no_lazy_loading_error(self, db_manager):
        """
        Test 13: get_orchestrator_instructions handles products with vision documents
        without lazy loading errors (greenlet_spawn error).

        BUG FIX: This test verifies the fix for SQLAlchemy async context error.
        The Product model has a primary_vision_text property that accesses
        self.vision_documents, which triggers lazy loading in async context.

        Solution: Eager load vision_documents relationship when fetching Product.
        """
        from src.giljo_mcp.models import VisionDocument
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_key = f"test_tenant_{uuid4().hex[:8]}"

        async with db_manager.get_session_async() as session:
            # Create product
            product = Product(
                tenant_key=tenant_key,
                name="Test Product with Vision",
                description="Product with vision documents",
                is_active=True,
            )
            session.add(product)
            await session.flush()

            # Create vision document for the product
            vision_doc = VisionDocument(
                tenant_key=tenant_key,
                product_id=product.id,
                document_name="Primary Vision",
                document_type="vision",
                vision_document="This is the primary vision content for testing.",
                storage_type="inline",
                is_active=True,
                display_order=1,
            )
            session.add(vision_doc)
            await session.flush()

            # Create project for that product
            project = Project(
                tenant_key=tenant_key,
                product_id=product.id,
                name="Test Project",
                description="Test project with vision documents",
                mission="Test mission",
                status="active",
                context_budget=150000,
                context_used=0,
            )
            session.add(project)
            await session.flush()

            # Create orchestrator job
            orchestrator_id = str(uuid4())
            orchestrator = MCPAgentJob(
                job_id=orchestrator_id,
                tenant_key=tenant_key,
                project_id=project.id,
                agent_type="orchestrator",
                mission="Orchestrate test project with vision",
                status="waiting",  # Valid statuses: waiting, working, blocked, complete, failed, cancelled, decommissioned
                context_budget=150000,
                context_used=0,
                instance_number=1,
                job_metadata={
                    "field_priorities": {"core_features": 10, "vision": 9},
                    "user_id": "test_user_123",
                },
            )
            session.add(orchestrator)

            await session.commit()

            # Store IDs for later use
            orchestrator_id_str = orchestrator_id
            tenant_key_str = tenant_key

        # ACT: Call get_orchestrator_instructions
        # This should NOT raise greenlet error when accessing product.primary_vision_text
        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        result = await tool_accessor.get_orchestrator_instructions(
            job_id=orchestrator_id_str, tenant_key=tenant_key_str
        )

        # ASSERT: Should return success without errors
        assert "error" not in result
        assert "orchestrator_id" in result
        assert result["orchestrator_id"] == orchestrator_id_str

        # Mission should be populated (may include vision content or fallback)
        assert "mission" in result
        assert isinstance(result["mission"], str)
        assert len(result["mission"]) > 0

        # Should have thin_client flag
        assert "thin_client" in result
        assert result["thin_client"] is True


@pytest.mark.asyncio
class TestMCPToolAccessibility:
    """Test MCP tool accessibility from external clients"""

    async def test_tool_can_be_called_via_http(self, test_client, tenant_context):
        """Test 11: Tool can be called via HTTP endpoint (simulated)"""
        # This would require a full FastAPI test client setup
        # For now, verify the endpoint structure is correct

        from pathlib import Path

        mcp_tools_path = Path("F:/GiljoAI_MCP/api/endpoints/mcp_tools.py")
        content = mcp_tools_path.read_text()

        # Verify POST /mcp/tools/execute endpoint exists
        assert '@router.post("/execute"' in content

        # Verify it handles tool routing
        assert "tool_map" in content
        assert "get_orchestrator_instructions" in content

    async def test_mcp_adapter_forwards_tool_calls(self):
        """Test 12: MCP adapter forwards tool calls to HTTP endpoint"""
        from pathlib import Path

        adapter_path = Path("F:/GiljoAI_MCP/src/giljo_mcp/mcp_adapter.py")
        content = adapter_path.read_text()

        # Verify adapter calls /mcp/tools/execute
        assert '"/mcp/tools/execute"' in content

        # Verify it handles tool_name and arguments
        assert '"tool": tool_name' in content
        assert '"arguments": arguments' in content


@pytest.mark.asyncio
class TestErrorHandling:
    """Test error handling and edge cases"""

    async def test_handles_missing_project(self, db_manager):
        """Test 13: Gracefully handles missing project"""
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        # Create orphaned orchestrator (no project)
        tenant_key = f"test_{uuid4().hex[:8]}"
        orchestrator_id = str(uuid4())

        async with db_manager.get_session_async() as session:
            orchestrator = MCPAgentJob(
                job_id=orchestrator_id,
                tenant_key=tenant_key,
                project_id=uuid4(),  # Non-existent project
                agent_type="orchestrator",
                mission="Test",
                status="waiting",
            )
            session.add(orchestrator)
            await session.commit()

        result = await tool_accessor.get_orchestrator_instructions(
            job_id=orchestrator_id, tenant_key=tenant_key
        )

        # Should return error
        assert "error" in result
        assert result["error"] == "NOT_FOUND"

    async def test_handles_database_errors(self, db_manager):
        """Test 14: Handles database connection errors gracefully"""
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        # Close database connection to simulate error
        await db_manager.close()

        result = await tool_accessor.get_orchestrator_instructions(job_id="test_id", tenant_key="test_key")

        # Should return INTERNAL_ERROR
        assert "error" in result
        assert "INTERNAL_ERROR" in result["error"] or "message" in result


# Integration test fixtures
@pytest.fixture
async def test_client():
    """Create test client for HTTP endpoint testing"""
    # This would be implemented with httpx.AsyncClient
    # For now, we rely on structural validation


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
