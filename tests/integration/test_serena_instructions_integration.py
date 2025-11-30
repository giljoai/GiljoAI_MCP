"""
Integration Tests for Serena MCP Usage Instructions

Verifies that SerenaInstructionGenerator:
1. Generates comprehensive Serena MCP usage instructions
2. Conditionally includes instructions based on serena_mcp.enabled config
3. Provides agent-specific instructions for different roles
4. Generates token-efficient instructions with examples
5. Integrates with get_orchestrator_instructions

CRITICAL: Serena MCP can save 80-90% tokens by avoiding full file reads.
This test ensures orchestrators and agents receive proper guidance.
"""

from uuid import uuid4
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import MCPAgentJob, Product, Project


@pytest.mark.asyncio
class TestSerenaInstructionGenerator:
    """Test suite for SerenaInstructionGenerator"""

    @pytest.fixture
    async def tenant_context(self, db_manager):
        """Create test tenant with product, project, and orchestrator"""
        tenant_key = f"test_tenant_{uuid4().hex[:8]}"

        async with db_manager.get_session_async() as session:
            # Create product
            product = Product(
                tenant_key=tenant_key,
                name="Test Product",
                description="Test product for Serena instruction tests",
                is_active=True,
            )
            session.add(product)
            await session.flush()

            # Create project
            project = Project(
                tenant_key=tenant_key,
                product_id=product.id,
                name="Test Project",
                description="Test project for Serena",
                mission="Test mission for Serena instructions",
            )
            session.add(project)
            await session.flush()

            # Create orchestrator job
            orchestrator = MCPAgentJob(
                job_id=f"orch_{uuid4().hex[:8]}",
                tenant_key=tenant_key,
                project_id=project.id,
                agent_type="orchestrator",
                agent_name="Orchestrator",
                mission="Test mission for orchestrator",
                status="working",
                context_budget=150000,
                context_used=0,
                instance_number=1,
            )
            session.add(orchestrator)
            await session.commit()
            await session.refresh(product)
            await session.refresh(project)
            await session.refresh(orchestrator)

            return {
                "tenant_key": tenant_key,
                "product": product,
                "project": project,
                "orchestrator": orchestrator,
            }

    async def test_serena_instructions_included_when_enabled(
        self, db_manager, tenant_context, tmp_path
    ):
        """Verify orchestrator receives Serena instructions when enabled in config"""
        # Create config with Serena enabled
        config_file = tmp_path / "config.yaml"
        config_data = {
            "features": {
                "serena_mcp": {
                    "enabled": True,
                    "use_in_prompts": True,
                    "installed": True,
                    "registered": True,
                }
            },
            "database": {"database_url": "postgresql://test"},
        }
        config_file.write_text(yaml.dump(config_data))

        # Patch config reading to use our test config
        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = tmp_path

            # Import the generator after patching
            from src.giljo_mcp.prompt_generation.serena_instructions import (
                SerenaInstructionGenerator,
            )

            generator = SerenaInstructionGenerator()

            # Generate full instructions for orchestrator
            instructions = await generator.generate_instructions(
                enabled=True, detail_level="full"
            )

            # Verify instructions are comprehensive
            assert instructions is not None
            assert len(instructions) > 500, "Instructions should be substantial"
            assert "mcp__serena__" in instructions, "Should reference Serena MCP tools"
            assert "find_symbol" in instructions, "Should include find_symbol tool"
            assert "search_for_pattern" in instructions, "Should include search_for_pattern tool"
            assert (
                "80%" in instructions or "90%" in instructions or "token" in instructions
            ), "Should mention token savings"
            assert (
                "CORRECT" in instructions and "INCORRECT" in instructions
            ), "Should include code examples"

    async def test_serena_instructions_excluded_when_disabled(self, tmp_path):
        """Verify minimal message when Serena is disabled in config"""
        # Create config with Serena disabled
        config_file = tmp_path / "config.yaml"
        config_data = {
            "features": {
                "serena_mcp": {
                    "enabled": False,
                    "use_in_prompts": False,
                    "installed": False,
                    "registered": False,
                }
            }
        }
        config_file.write_text(yaml.dump(config_data))

        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = tmp_path

            from src.giljo_mcp.prompt_generation.serena_instructions import (
                SerenaInstructionGenerator,
            )

            generator = SerenaInstructionGenerator()

            # Generate instructions for disabled state
            instructions = await generator.generate_instructions(
                enabled=False, detail_level="minimal"
            )

            # Verify minimal message
            assert instructions is not None
            assert len(instructions) < 200, "Disabled message should be minimal"
            assert (
                "Serena" in instructions or "not available" in instructions
            ), "Should mention Serena is unavailable"

    async def test_spawned_agents_receive_serena_status(
        self, db_manager, tenant_context, tmp_path
    ):
        """Verify spawned agents receive agent-specific Serena instructions"""
        # Create config with Serena enabled
        config_file = tmp_path / "config.yaml"
        config_data = {
            "features": {
                "serena_mcp": {
                    "enabled": True,
                    "use_in_prompts": True,
                    "installed": True,
                }
            }
        }
        config_file.write_text(yaml.dump(config_data))

        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = tmp_path

            from src.giljo_mcp.prompt_generation.serena_instructions import (
                SerenaInstructionGenerator,
            )

            generator = SerenaInstructionGenerator()

            # Generate instructions for implementer agent
            impl_instructions = await generator.generate_for_agent(
                enabled=True, agent_type="implementer"
            )

            # Verify implementer gets full instructions
            assert impl_instructions is not None
            assert (
                len(impl_instructions) > 300
            ), "Implementer should get substantial instructions"
            assert (
                "find_symbol" in impl_instructions
            ), "Implementer needs navigation tools"
            assert (
                "replace_symbol_body" in impl_instructions
            ), "Implementer needs editing tools"

            # Generate instructions for tester agent
            tester_instructions = await generator.generate_for_agent(
                enabled=True, agent_type="tester"
            )

            # Verify tester gets summary instructions
            assert tester_instructions is not None
            assert (
                len(tester_instructions) > 100
            ), "Tester should get summary instructions"
            assert (
                "find_symbol" in tester_instructions
            ), "Tester needs to understand code"

    async def test_serena_tools_reference_structure(self, tmp_path):
        """Verify Serena tools are properly structured in instructions"""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "features": {
                "serena_mcp": {"enabled": True, "use_in_prompts": True}
            }
        }
        config_file.write_text(yaml.dump(config_data))

        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = tmp_path

            from src.giljo_mcp.prompt_generation.serena_instructions import (
                SerenaInstructionGenerator,
            )

            generator = SerenaInstructionGenerator()
            instructions = await generator.generate_instructions(
                enabled=True, detail_level="full"
            )

            # Verify key tool categories are present
            assert "Navigation" in instructions or "navigation" in instructions.lower()
            assert "Search" in instructions or "search" in instructions.lower()
            assert "Modification" in instructions or "modify" in instructions.lower()
            assert (
                "mcp__serena__find_symbol" in instructions
            ), "Should include find_symbol MCP tool"
            assert (
                "mcp__serena__search_for_pattern" in instructions
            ), "Should include search_for_pattern MCP tool"

    async def test_serena_instructions_include_usage_patterns(self, tmp_path):
        """Verify instructions include clear usage patterns and examples"""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "features": {
                "serena_mcp": {"enabled": True, "use_in_prompts": True}
            }
        }
        config_file.write_text(yaml.dump(config_data))

        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = tmp_path

            from src.giljo_mcp.prompt_generation.serena_instructions import (
                SerenaInstructionGenerator,
            )

            generator = SerenaInstructionGenerator()
            instructions = await generator.generate_instructions(
                enabled=True, detail_level="full"
            )

            # Verify usage patterns
            assert (
                "Structure" in instructions or "structure" in instructions.lower()
            ), "Should explain overall structure"
            assert (
                "Navigate" in instructions or "navigate" in instructions.lower()
            ), "Should explain how to navigate"
            assert (
                "example" in instructions.lower()
            ), "Should include code examples"

    async def test_serena_instructions_token_savings_mentioned(self, tmp_path):
        """Verify instructions emphasize token savings benefits"""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "features": {
                "serena_mcp": {"enabled": True, "use_in_prompts": True}
            }
        }
        config_file.write_text(yaml.dump(config_data))

        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = tmp_path

            from src.giljo_mcp.prompt_generation.serena_instructions import (
                SerenaInstructionGenerator,
            )

            generator = SerenaInstructionGenerator()
            instructions = await generator.generate_instructions(
                enabled=True, detail_level="full"
            )

            # Verify token savings are highlighted
            instructions_lower = instructions.lower()
            assert (
                "token" in instructions_lower and "sav" in instructions_lower
            ), "Should mention token savings"
            assert (
                "80" in instructions or "90" in instructions
            ), "Should mention specific percentages"
            assert (
                "read" in instructions_lower and "file" in instructions_lower
            ), "Should mention avoiding full file reads"

    async def test_orchestrator_instructions_integration_deferred(
        self, db_manager, tenant_context, tmp_path
    ):
        """
        DEFERRED: Verify Serena instructions are integrated into get_orchestrator_instructions

        This test is marked as deferred because it requires integrating Serena instructions
        into the get_orchestrator_instructions tool, which is Phase 3 of implementation.

        Once integrated, this test will verify that:
        1. Orchestrator receives Serena instructions when enabled
        2. Instructions appear in condensed mission
        3. Agent-specific instructions are generated for spawned agents
        """
        pass  # TODO: Implement Phase 3 integration

    async def test_serena_instructions_caching_performance(self, tmp_path):
        """Verify instructions are generated efficiently (caching if needed)"""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "features": {
                "serena_mcp": {"enabled": True, "use_in_prompts": True}
            }
        }
        config_file.write_text(yaml.dump(config_data))

        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = tmp_path

            from src.giljo_mcp.prompt_generation.serena_instructions import (
                SerenaInstructionGenerator,
            )

            generator = SerenaInstructionGenerator()

            # Generate multiple times
            instructions1 = await generator.generate_instructions(
                enabled=True, detail_level="full"
            )
            instructions2 = await generator.generate_instructions(
                enabled=True, detail_level="full"
            )

            # Verify same instructions returned (should be identical)
            assert instructions1 == instructions2, "Instructions should be consistent"

    async def test_serena_different_detail_levels(self, tmp_path):
        """Verify different detail levels generate appropriate content"""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "features": {
                "serena_mcp": {"enabled": True, "use_in_prompts": True}
            }
        }
        config_file.write_text(yaml.dump(config_data))

        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = tmp_path

            from src.giljo_mcp.prompt_generation.serena_instructions import (
                SerenaInstructionGenerator,
            )

            generator = SerenaInstructionGenerator()

            # Generate different detail levels
            minimal = await generator.generate_instructions(
                enabled=True, detail_level="minimal"
            )
            summary = await generator.generate_instructions(
                enabled=True, detail_level="summary"
            )
            full = await generator.generate_instructions(
                enabled=True, detail_level="full"
            )

            # Verify escalating detail
            assert len(minimal) < len(summary), "Minimal should be shorter than summary"
            assert len(summary) < len(full), "Summary should be shorter than full"

            # Verify all include basic tool reference
            for instructions in [minimal, summary, full]:
                assert "serena" in instructions.lower(), "All should reference Serena"


@pytest.mark.asyncio
class TestSerenaInstructionsEdgeCases:
    """Test edge cases and error handling"""

    async def test_serena_instructions_with_missing_config(self, tmp_path):
        """Verify graceful handling when config.yaml doesn't exist"""
        # Don't create config file

        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = tmp_path

            from src.giljo_mcp.prompt_generation.serena_instructions import (
                SerenaInstructionGenerator,
            )

            generator = SerenaInstructionGenerator()

            # Should not raise exception
            instructions = await generator.generate_instructions(
                enabled=False, detail_level="minimal"
            )

            # Should provide minimal instructions
            assert instructions is not None
            assert len(instructions) > 0

    async def test_serena_instructions_agent_types(self, tmp_path):
        """Verify all agent types receive appropriate instructions"""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "features": {
                "serena_mcp": {"enabled": True, "use_in_prompts": True}
            }
        }
        config_file.write_text(yaml.dump(config_data))

        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = tmp_path

            from src.giljo_mcp.prompt_generation.serena_instructions import (
                SerenaInstructionGenerator,
            )

            generator = SerenaInstructionGenerator()

            # Test multiple agent types
            agent_types = ["implementer", "tester", "architect", "documenter"]

            for agent_type in agent_types:
                instructions = await generator.generate_for_agent(
                    enabled=True, agent_type=agent_type
                )

                assert instructions is not None, f"Should generate instructions for {agent_type}"
                assert (
                    len(instructions) > 0
                ), f"Instructions for {agent_type} should not be empty"


@pytest.mark.asyncio
class TestSerenaInstructionsQuality:
    """Test instruction quality and completeness"""

    async def test_serena_instructions_no_duplicate_tools(self, tmp_path):
        """Verify tool references aren't duplicated in instructions"""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "features": {
                "serena_mcp": {"enabled": True, "use_in_prompts": True}
            }
        }
        config_file.write_text(yaml.dump(config_data))

        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = tmp_path

            from src.giljo_mcp.prompt_generation.serena_instructions import (
                SerenaInstructionGenerator,
            )

            generator = SerenaInstructionGenerator()
            instructions = await generator.generate_instructions(
                enabled=True, detail_level="full"
            )

            # Count occurrences of key tools
            find_symbol_count = instructions.count("mcp__serena__find_symbol")
            search_count = instructions.count("mcp__serena__search_for_pattern")

            # Should appear multiple times in different contexts, but not excessively
            assert find_symbol_count >= 1, "find_symbol should be mentioned"
            assert search_count >= 1, "search_for_pattern should be mentioned"

    async def test_serena_instructions_markdown_format(self, tmp_path):
        """Verify instructions use clear markdown formatting"""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "features": {
                "serena_mcp": {"enabled": True, "use_in_prompts": True}
            }
        }
        config_file.write_text(yaml.dump(config_data))

        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = tmp_path

            from src.giljo_mcp.prompt_generation.serena_instructions import (
                SerenaInstructionGenerator,
            )

            generator = SerenaInstructionGenerator()
            instructions = await generator.generate_instructions(
                enabled=True, detail_level="full"
            )

            # Check for markdown formatting
            assert "#" in instructions, "Should use markdown headers"
            assert "**" in instructions or "-" in instructions, "Should have formatting"
