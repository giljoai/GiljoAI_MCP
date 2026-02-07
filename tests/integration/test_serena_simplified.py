"""
Integration Tests for Simplified Serena MCP (Handover 0277)

Tests the simplified Serena MCP implementation:
1. Serena instructions are ~50 tokens (simple notice)
2. GET /api/serena/settings returns only use_in_prompts
3. POST /api/serena/toggle only accepts boolean
4. Orchestrator includes simple notice when enabled
5. Orchestrator excludes Serena when disabled

Token reduction: 6,000 → 50 tokens (99% reduction)
"""

from unittest.mock import patch
from uuid import uuid4

import pytest
import yaml

from src.giljo_mcp.models import Product, Project
from src.giljo_mcp.models.agent_identity import AgentExecution


@pytest.mark.asyncio
class TestSimplifiedSerenaInstructions:
    """Test suite for simplified Serena instruction generation"""

    async def test_serena_instructions_are_50_tokens(self, tmp_path):
        """Verify Serena instructions are ~50 tokens (simple notice)"""
        config_file = tmp_path / "config.yaml"
        config_data = {"features": {"serena_mcp": {"use_in_prompts": True}}}
        config_file.write_text(yaml.dump(config_data))

        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = tmp_path

            from src.giljo_mcp.prompt_generation.serena_instructions import (
                generate_serena_instructions,
            )

            instructions = generate_serena_instructions(enabled=True)

            # Verify ~50 tokens (rough word count * 1.3)
            word_count = len(instructions.split())
            estimated_tokens = int(word_count * 1.3)

            assert instructions is not None
            assert len(instructions) < 500, "Instructions should be concise"
            assert estimated_tokens < 100, f"Expected ~50 tokens, got ~{estimated_tokens}"
            assert "Serena MCP" in instructions, "Should mention Serena MCP"
            assert "find_symbol" in instructions, "Should mention key tools"
            assert "80-90%" in instructions or "token" in instructions, "Should mention token savings"

    async def test_serena_disabled_returns_empty_string(self, tmp_path):
        """Verify empty string when Serena is disabled"""
        config_file = tmp_path / "config.yaml"
        config_data = {"features": {"serena_mcp": {"use_in_prompts": False}}}
        config_file.write_text(yaml.dump(config_data))

        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = tmp_path

            from src.giljo_mcp.prompt_generation.serena_instructions import (
                generate_serena_instructions,
            )

            instructions = generate_serena_instructions(enabled=False)

            # Should return empty string
            assert instructions == "", "Should return empty string when disabled"

    async def test_serena_instructions_no_advanced_settings(self, tmp_path):
        """Verify no references to advanced settings in instructions"""
        config_file = tmp_path / "config.yaml"
        config_data = {"features": {"serena_mcp": {"use_in_prompts": True}}}
        config_file.write_text(yaml.dump(config_data))

        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = tmp_path

            from src.giljo_mcp.prompt_generation.serena_instructions import (
                generate_serena_instructions,
            )

            instructions = generate_serena_instructions(enabled=True)

            # Should NOT reference advanced settings
            assert "tailor_by_mission" not in instructions
            assert "dynamic_catalog" not in instructions
            assert "prefer_ranges" not in instructions
            assert "max_range_lines" not in instructions
            assert "context_halo" not in instructions


@pytest.mark.asyncio
class TestSerenaAPIEndpoint:
    """Test suite for simplified Serena API endpoint"""

    @pytest.fixture
    async def tenant_context(self, db_manager):
        """Create test tenant"""
        tenant_key = f"test_tenant_{uuid4().hex[:8]}"

        async with db_manager.get_session_async() as session:
            product = Product(
                tenant_key=tenant_key,
                name="Test Product",
                description="Test product for Serena API tests",
                is_active=True,
            )
            session.add(product)
            await session.commit()
            await session.refresh(product)

            return {"tenant_key": tenant_key, "product": product}

    async def test_get_serena_settings_returns_only_use_in_prompts(self, async_client, tenant_context, auth_headers):
        """Verify GET /api/serena/settings returns only use_in_prompts field"""
        response = await async_client.get("/api/serena/settings", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        # Should ONLY have use_in_prompts
        assert "use_in_prompts" in data
        assert isinstance(data["use_in_prompts"], bool)

        # Should NOT have advanced settings
        assert "tailor_by_mission" not in data
        assert "dynamic_catalog" not in data
        assert "prefer_ranges" not in data
        assert "max_range_lines" not in data
        assert "context_halo" not in data

        # Should have exactly 1 key
        assert len(data.keys()) == 1

    async def test_post_serena_toggle_accepts_only_boolean(self, async_client, tenant_context, auth_headers):
        """Verify POST /api/serena/toggle only accepts boolean"""
        # Valid boolean toggle
        response = await async_client.post("/api/serena/toggle", headers=auth_headers, json={"use_in_prompts": True})

        assert response.status_code == 200
        data = response.json()
        assert data["use_in_prompts"] is True

        # Toggle off
        response = await async_client.post("/api/serena/toggle", headers=auth_headers, json={"use_in_prompts": False})

        assert response.status_code == 200
        data = response.json()
        assert data["use_in_prompts"] is False

    async def test_post_serena_rejects_advanced_settings(self, async_client, tenant_context, auth_headers):
        """Verify POST /api/serena/toggle rejects advanced settings"""
        # Attempt to send advanced settings
        response = await async_client.post(
            "/api/serena/toggle",
            headers=auth_headers,
            json={
                "use_in_prompts": True,
                "tailor_by_mission": True,
                "dynamic_catalog": False,
            },
        )

        # Should either reject (422) or ignore extra fields
        # Implementation should only process use_in_prompts
        assert response.status_code in [200, 422]

        if response.status_code == 200:
            data = response.json()
            # Response should only include use_in_prompts
            assert len(data.keys()) == 1
            assert "use_in_prompts" in data


@pytest.mark.asyncio
class TestOrchestratorSerenaIntegration:
    """Test suite for orchestrator Serena integration"""

    @pytest.fixture
    async def orchestrator_context(self, db_manager):
        """Create test orchestrator"""
        tenant_key = f"test_tenant_{uuid4().hex[:8]}"

        async with db_manager.get_session_async() as session:
            product = Product(
                tenant_key=tenant_key,
                name="Test Product",
                description="Test product",
                is_active=True,
            )
            session.add(product)
            await session.flush()

            project = Project(
                tenant_key=tenant_key,
                product_id=product.id,
                name="Test Project",
                description="Test project",
                mission="Test mission",
            )
            session.add(project)
            await session.flush()

            orchestrator = AgentExecution(
                job_id=f"orch_{uuid4().hex[:8]}",
                tenant_key=tenant_key,
                project_id=project.id,
                agent_display_name="orchestrator",
                agent_name="Orchestrator",
                mission="Test mission",
                status="working",
                context_budget=150000,
                context_used=0,
            )
            session.add(orchestrator)
            await session.commit()
            await session.refresh(orchestrator)

            return {
                "tenant_key": tenant_key,
                "orchestrator": orchestrator,
            }

    async def test_orchestrator_includes_serena_when_enabled(self, db_manager, orchestrator_context, tmp_path):
        """Verify orchestrator includes simple Serena notice when enabled"""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "features": {"serena_mcp": {"use_in_prompts": True}},
            "database": {"database_url": "postgresql://test"},
        }
        config_file.write_text(yaml.dump(config_data))

        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = tmp_path

            from src.giljo_mcp.tools.orchestration import get_orchestrator_instructions

            # Get orchestrator instructions
            result = await get_orchestrator_instructions(
                orchestrator_id=orchestrator_context["orchestrator"].job_id,
                tenant_key=orchestrator_context["tenant_key"],
                db_manager=db_manager,
            )

            prompt = result.get("prompt", "")

            # Should include Serena section
            assert "Serena MCP" in prompt or "serena" in prompt.lower()
            assert "find_symbol" in prompt or "symbolic" in prompt.lower()

            # Should NOT include advanced settings references
            assert "tailor_by_mission" not in prompt
            assert "dynamic_catalog" not in prompt
            assert "prefer_ranges" not in prompt

    async def test_orchestrator_excludes_serena_when_disabled(self, db_manager, orchestrator_context, tmp_path):
        """Verify orchestrator excludes Serena when disabled"""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "features": {"serena_mcp": {"use_in_prompts": False}},
            "database": {"database_url": "postgresql://test"},
        }
        config_file.write_text(yaml.dump(config_data))

        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = tmp_path

            from src.giljo_mcp.tools.orchestration import get_orchestrator_instructions

            # Get orchestrator instructions
            result = await get_orchestrator_instructions(
                orchestrator_id=orchestrator_context["orchestrator"].job_id,
                tenant_key=orchestrator_context["tenant_key"],
                db_manager=db_manager,
            )

            prompt = result.get("prompt", "")

            # Should NOT include Serena references
            assert "Serena MCP" not in prompt
            # Basic check - if disabled, shouldn't have extensive tool references
            serena_tool_count = prompt.lower().count("mcp__serena__")
            assert serena_tool_count == 0, "Should not reference Serena MCP tools when disabled"
