"""
Integration Test for Handover 0408: Serena MCP Injection in get_orchestrator_instructions

Tests that the Serena MCP toggle check and injection work correctly when:
1. Serena is enabled in config.yaml
2. Serena is disabled in config.yaml
3. Config file doesn't exist or has errors
"""

from pathlib import Path
from uuid import uuid4
import yaml
import pytest

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Product, Project
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution


@pytest.mark.asyncio
class TestSerenaInjection0408:
    """Test Serena MCP injection in get_orchestrator_instructions"""

    @pytest.fixture
    async def tenant_context(self, db_manager):
        """Create test tenant with product, project, and orchestrator"""
        tenant_key = f"test_tenant_{uuid4().hex[:8]}"

        async with db_manager.get_session_async() as session:
            # Create product
            product = Product(
                tenant_key=tenant_key,
                name="Test Product",
                description="Test product for Serena injection",
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
                description="Test project",
                mission="Test mission",
                status="active",
                context_budget=150000,
                context_used=0,
            )
            session.add(project)
            await session.flush()

            # Create orchestrator job
            orchestrator_job_id = str(uuid4())
            orchestrator_job = AgentJob(
                job_id=orchestrator_job_id,
                tenant_key=tenant_key,
                project_id=project.id,
                agent_type="orchestrator",
                agent_name="Orchestrator",
                mission="Orchestrate test project",
                status="pending",
                job_metadata={
                    "field_priorities": {"core_features": 10},
                },
            )
            session.add(orchestrator_job)
            await session.flush()

            # Create orchestrator execution
            orchestrator_agent_id = str(uuid4())
            orchestrator_exec = AgentExecution(
                agent_id=orchestrator_agent_id,
                job_id=orchestrator_job_id,
                tenant_key=tenant_key,
                project_id=project.id,
                agent_type="orchestrator",
                status="waiting",
                context_budget=150000,
                context_used=0,
                instance_number=1,
            )
            session.add(orchestrator_exec)

            await session.commit()

            yield {
                "tenant_key": tenant_key,
                "agent_id": orchestrator_agent_id,
                "job_id": orchestrator_job_id,
                "project_id": str(project.id),
                "product_id": str(product.id),
            }

    async def test_serena_injection_when_enabled(self, db_manager, tenant_context, tmp_path):
        """Test 1: Serena notice is injected when enabled in config"""
        from src.giljo_mcp.tools.orchestration import get_orchestrator_instructions

        # Create temporary config with Serena enabled
        config_path = Path.cwd() / "config.yaml"
        original_exists = config_path.exists()
        original_content = None

        if original_exists:
            original_content = config_path.read_text()

        try:
            # Write config with Serena enabled
            config_data = {
                "features": {
                    "serena_mcp": {
                        "use_in_prompts": True
                    }
                }
            }
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(config_data, f)

            # Call get_orchestrator_instructions
            result = await get_orchestrator_instructions(
                agent_id=tenant_context["agent_id"],
                tenant_key=tenant_context["tenant_key"],
                db_manager=db_manager,
            )

            # Verify no error
            assert "error" not in result

            # Verify integrations field exists with serena_mcp_enabled=True
            assert "integrations" in result
            assert result["integrations"]["serena_mcp_enabled"] is True

            # Verify mission contains Serena notice
            mission = result["mission"]
            assert "Serena MCP Available" in mission
            assert "find_symbol" in mission or "get_symbols_overview" in mission

        finally:
            # Restore original config
            if original_exists and original_content:
                config_path.write_text(original_content)
            elif not original_exists and config_path.exists():
                config_path.unlink()

    async def test_serena_injection_when_disabled(self, db_manager, tenant_context):
        """Test 2: Serena notice is NOT injected when disabled in config"""
        from src.giljo_mcp.tools.orchestration import get_orchestrator_instructions

        # Create temporary config with Serena disabled
        config_path = Path.cwd() / "config.yaml"
        original_exists = config_path.exists()
        original_content = None

        if original_exists:
            original_content = config_path.read_text()

        try:
            # Write config with Serena disabled
            config_data = {
                "features": {
                    "serena_mcp": {
                        "use_in_prompts": False
                    }
                }
            }
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(config_data, f)

            # Call get_orchestrator_instructions
            result = await get_orchestrator_instructions(
                agent_id=tenant_context["agent_id"],
                tenant_key=tenant_context["tenant_key"],
                db_manager=db_manager,
            )

            # Verify no error
            assert "error" not in result

            # Verify integrations field exists with serena_mcp_enabled=False
            assert "integrations" in result
            assert result["integrations"]["serena_mcp_enabled"] is False

            # Verify mission does NOT contain Serena notice
            mission = result["mission"]
            assert "Serena MCP Available" not in mission

        finally:
            # Restore original config
            if original_exists and original_content:
                config_path.write_text(original_content)
            elif not original_exists and config_path.exists():
                config_path.unlink()

    async def test_serena_injection_with_missing_config(self, db_manager, tenant_context):
        """Test 3: Gracefully handles missing config file"""
        from src.giljo_mcp.tools.orchestration import get_orchestrator_instructions

        # Temporarily remove config if it exists
        config_path = Path.cwd() / "config.yaml"
        original_exists = config_path.exists()
        original_content = None

        if original_exists:
            original_content = config_path.read_text()
            config_path.unlink()

        try:
            # Call get_orchestrator_instructions with no config file
            result = await get_orchestrator_instructions(
                agent_id=tenant_context["agent_id"],
                tenant_key=tenant_context["tenant_key"],
                db_manager=db_manager,
            )

            # Should not error, should default to disabled
            assert "error" not in result
            assert "integrations" in result
            assert result["integrations"]["serena_mcp_enabled"] is False

        finally:
            # Restore original config
            if original_exists and original_content:
                config_path.write_text(original_content)

    async def test_integrations_field_structure(self, db_manager, tenant_context):
        """Test 4: Verify integrations field has correct structure"""
        from src.giljo_mcp.tools.orchestration import get_orchestrator_instructions

        result = await get_orchestrator_instructions(
            agent_id=tenant_context["agent_id"],
            tenant_key=tenant_context["tenant_key"],
            db_manager=db_manager,
        )

        # Verify integrations field structure
        assert "integrations" in result
        assert isinstance(result["integrations"], dict)
        assert "serena_mcp_enabled" in result["integrations"]
        assert isinstance(result["integrations"]["serena_mcp_enabled"], bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
