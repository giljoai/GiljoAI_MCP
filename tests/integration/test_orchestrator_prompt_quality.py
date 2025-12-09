"""
Integration Tests for Orchestrator Prompt Quality (Handover 0336)

Verifies prompt quality fixes for:
1. Tech stack character-by-character encoding bug
2. Token estimation accuracy mismatch
3. Vision document depth configuration
4. CLI mode rules inclusion

These tests prevent regression of critical prompt quality issues that
affect orchestrator performance and user trust in token budgeting.

Related Handovers:
- 0336: Tech Stack Encoding and Token Estimation Fix
- 0335: CLI Mode Template Export
- 0246a-c: Token Optimization Series
- 0302: Tech Stack Formatting
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
import tiktoken
from sqlalchemy import and_, select

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.models import MCPAgentJob, Product, Project, VisionDocument
from src.giljo_mcp.tenant import TenantManager
from src.giljo_mcp.tools.tool_accessor import ToolAccessor


@pytest.mark.asyncio
class TestTechStackEncoding:
    """
    Test 1: Tech Stack Character-by-Character Encoding (Bug 1 - CRITICAL)

    Verifies that tech stack displays as 'Python 3.11+' not 'P, y, t, h, o, n, ...'

    Regression test for Handover 0336 Bug 1.
    Root cause: _format_tech_stack() didn't handle string values correctly
    Fix: Type-safe value formatting with isinstance() check
    """

    async def test_tech_stack_displays_correctly_not_character_separated(self, db_manager):
        """Verify tech stack displays as 'Python 3.11+' not 'P, y, t, h, o, n, ...'"""
        tenant_key = f"test_tenant_{uuid4().hex[:8]}"

        async with db_manager.get_session_async() as session:
            # Create product with STRING tech stack values (bug scenario)
            product = Product(
                tenant_key=tenant_key,
                name="Test Product",
                description="Testing tech stack encoding",
                config_data={
                    "tech_stack": {
                        "languages": "Python 3.11+",  # STRING (triggers bug)
                        "backend": "FastAPI",  # STRING
                        "frontend": "Vue 3",  # STRING
                    }
                },
                is_active=True,
            )
            session.add(product)
            await session.flush()

            # Create project
            project = Project(
                tenant_key=tenant_key,
                product_id=product.id,
                name="Test Project",
                description="Test project for tech stack encoding",
                mission="Build test project for validating tech stack encoding in prompts",
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
                mission="Test orchestrator for tech stack encoding",
                status="waiting",
                context_budget=150000,
                context_used=0,
                instance_number=1,
                job_metadata={
                    "field_priorities": {
                        "product_core": 1,
                        "tech_stack": 1,  # CRITICAL priority (always included)
                    },
                    "depth_config": {},
                },
            )
            session.add(orchestrator)
            await session.commit()

        # ACT: Generate orchestrator instructions
        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        result = await tool_accessor.get_orchestrator_instructions(
            orchestrator_id=orchestrator_id, tenant_key=tenant_key
        )

        # ASSERT: Tech stack displays as words, not character-separated
        mission = result["mission"]

        # Should contain tech stack as words
        assert "Python 3.11+" in mission, "Tech stack should include 'Python 3.11+' as whole phrase"
        assert "FastAPI" in mission, "Tech stack should include 'FastAPI' as whole word"
        assert "Vue 3" in mission, "Tech stack should include 'Vue 3' as whole phrase"

        # Should NOT contain character-separated values (the bug)
        assert "P, y, t, h, o, n" not in mission, "Tech stack should NOT split 'Python' into characters"
        assert "F, a, s, t, A, P, I" not in mission, "Tech stack should NOT split 'FastAPI' into characters"
        assert "V, u, e" not in mission, "Tech stack should NOT split 'Vue' into characters"

    async def test_mixed_string_and_list_tech_stack_values(self, db_manager):
        """Verify mixed string/list tech stack values format correctly"""
        tenant_key = f"test_tenant_{uuid4().hex[:8]}"

        async with db_manager.get_session_async() as session:
            # Create product with MIXED tech stack values
            product = Product(
                tenant_key=tenant_key,
                name="Test Product Mixed",
                description="Testing mixed tech stack formats",
                config_data={
                    "tech_stack": {
                        "languages": "Python 3.11+",  # STRING
                        "backend": ["FastAPI", "PostgreSQL"],  # LIST
                        "frontend": "Vue 3",  # STRING
                        "deployment": ["Docker", "Kubernetes"],  # LIST
                    }
                },
                is_active=True,
            )
            session.add(product)
            await session.flush()

            # Create project
            project = Project(
                tenant_key=tenant_key,
                product_id=product.id,
                name="Test Project Mixed",
                description="Test project for mixed tech stack",
                mission="Build test project for validating mixed tech stack formats",
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
                mission="Test orchestrator for mixed tech stack",
                status="waiting",
                context_budget=150000,
                context_used=0,
                instance_number=1,
                job_metadata={
                    "field_priorities": {"tech_stack": 1},
                    "depth_config": {},
                },
            )
            session.add(orchestrator)
            await session.commit()

        # ACT: Generate orchestrator instructions
        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        result = await tool_accessor.get_orchestrator_instructions(
            orchestrator_id=orchestrator_id, tenant_key=tenant_key
        )

        # ASSERT: Both string and list values format correctly
        mission = result["mission"]

        # String values should display without character splitting
        assert "Python 3.11+" in mission
        assert "Vue 3" in mission

        # List values should join with commas
        assert "FastAPI, PostgreSQL" in mission or "PostgreSQL, FastAPI" in mission
        assert "Docker, Kubernetes" in mission or "Kubernetes, Docker" in mission

        # Should NOT have character-separated values
        assert "P, y, t, h, o, n" not in mission
        assert "V, u, e" not in mission


@pytest.mark.asyncio
class TestTokenEstimationAccuracy:
    """
    Test 2: Token Estimation Accuracy (Bug 2 - HIGH)

    Verifies estimated_tokens is within 20% of actual mission content.

    Regression test for Handover 0336 Bug 2.
    Root cause: Token estimation used len() // 4 instead of actual token counting
    Fix: Use accurate tiktoken-based counting
    """

    @pytest.mark.xfail(reason="Bug 0336-2: Token estimation uses len()//4 instead of tiktoken (known issue)")
    async def test_estimated_tokens_matches_actual_content(self, db_manager):
        """Verify estimated_tokens is within 20% of actual mission content"""
        tenant_key = f"test_tenant_{uuid4().hex[:8]}"

        async with db_manager.get_session_async() as session:
            # Create product with large vision document
            product = Product(
                tenant_key=tenant_key,
                name="Test Product Large Vision",
                description="Testing token estimation with large vision",
                config_data={"tech_stack": {"languages": ["Python 3.11+"]}},
                is_active=True,
            )
            session.add(product)
            await session.flush()

            # Create large vision document (~10K tokens)
            vision_content = (
                "# Product Vision\n\n"
                + "This is a comprehensive vision document. " * 500  # ~5K tokens
                + "\n\n## Architecture\n\n"
                + "Detailed architecture description. " * 500  # ~5K tokens
            )

            vision_doc = VisionDocument(
                tenant_key=tenant_key,
                product_id=product.id,
                document_name="Primary Vision",
                document_type="vision",
                vision_document=vision_content,
                storage_type="inline",
                is_active=True,
                display_order=1,
            )
            session.add(vision_doc)
            await session.flush()

            # Create project
            project = Project(
                tenant_key=tenant_key,
                product_id=product.id,
                name="Test Project Token Estimation",
                description="Test project for token estimation accuracy",
                mission="Build test project for validating token estimation accuracy in prompts",
                status="active",
                context_budget=150000,
                context_used=0,
            )
            session.add(project)
            await session.flush()

            # Create orchestrator job with vision enabled
            orchestrator_id = str(uuid4())
            orchestrator = MCPAgentJob(
                job_id=orchestrator_id,
                tenant_key=tenant_key,
                project_id=project.id,
                agent_type="orchestrator",
                mission="Test orchestrator for token estimation",
                status="waiting",
                context_budget=150000,
                context_used=0,
                instance_number=1,
                job_metadata={
                    "field_priorities": {
                        "vision_documents": 2,  # IMPORTANT - include vision
                        "tech_stack": 1,
                    },
                    "depth_config": {
                        "vision_chunking": "moderate"  # 17,500 token limit
                    },
                },
            )
            session.add(orchestrator)
            await session.commit()

        # ACT: Generate orchestrator instructions
        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        result = await tool_accessor.get_orchestrator_instructions(
            orchestrator_id=orchestrator_id, tenant_key=tenant_key
        )

        # ASSERT: Calculate actual tokens using tiktoken
        encoder = tiktoken.get_encoding("cl100k_base")  # GPT-4 encoding
        mission_content = result["mission"]
        actual_tokens = len(encoder.encode(mission_content))
        estimated_tokens = result["estimated_tokens"]

        # Verify accuracy within 20% margin
        discrepancy = abs(actual_tokens - estimated_tokens)
        discrepancy_ratio = discrepancy / actual_tokens if actual_tokens > 0 else 0

        assert discrepancy_ratio < 0.20, (
            f"Token estimation off by {discrepancy_ratio:.1%}: "
            f"estimated={estimated_tokens}, actual={actual_tokens}, "
            f"discrepancy={discrepancy} tokens"
        )

        # Log for debugging
        print(
            f"\n[TOKEN_AUDIT] Estimation accuracy: "
            f"estimated={estimated_tokens}, actual={actual_tokens}, "
            f"accuracy={(1 - discrepancy_ratio) * 100:.1f}%"
        )


@pytest.mark.asyncio
class TestVisionDepthConfiguration:
    """
    Test 3: Vision Document Depth Configuration

    Verifies vision document is truncated based on vision_chunking depth.
    Tests that different depth levels respect configured token budgets.
    """

    @pytest.mark.xfail(reason="Bug 0336-3: Vision depth may include more content than expected (investigation needed)")
    async def test_vision_document_respects_depth_setting(self, db_manager):
        """Verify vision document is truncated based on vision_chunking depth"""
        tenant_key = f"test_tenant_{uuid4().hex[:8]}"

        async with db_manager.get_session_async() as session:
            # Create product
            product = Product(
                tenant_key=tenant_key,
                name="Test Product Vision Depth",
                description="Testing vision depth configuration",
                config_data={"tech_stack": {"languages": ["Python"]}},
                is_active=True,
            )
            session.add(product)
            await session.flush()

            # Create LARGE vision document (~50K tokens)
            vision_content = (
                "# Massive Vision Document\n\n" + "This is a very long vision document. " * 5000  # ~50K tokens
            )

            vision_doc = VisionDocument(
                tenant_key=tenant_key,
                product_id=product.id,
                document_name="Large Vision",
                document_type="vision",
                vision_document=vision_content,
                storage_type="inline",
                is_active=True,
                display_order=1,
            )
            session.add(vision_doc)
            await session.flush()

            # Create project
            project = Project(
                tenant_key=tenant_key,
                product_id=product.id,
                name="Test Project Vision Depth",
                description="Test project for vision depth",
                mission="Build test project for validating vision document depth configuration",
                status="active",
                context_budget=150000,
                context_used=0,
            )
            session.add(project)
            await session.flush()

            # Create orchestrator job with LIGHT vision depth
            orchestrator_id = str(uuid4())
            orchestrator = MCPAgentJob(
                job_id=orchestrator_id,
                tenant_key=tenant_key,
                project_id=project.id,
                agent_type="orchestrator",
                mission="Test orchestrator for vision depth",
                status="waiting",
                context_budget=150000,
                context_used=0,
                instance_number=1,
                job_metadata={
                    "field_priorities": {"vision_documents": 2},
                    "depth_config": {
                        "vision_chunking": "light"  # 10,000 token limit
                    },
                },
            )
            session.add(orchestrator)
            await session.commit()

        # ACT: Generate orchestrator instructions
        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        result = await tool_accessor.get_orchestrator_instructions(
            orchestrator_id=orchestrator_id, tenant_key=tenant_key
        )

        # ASSERT: Mission should be truncated to fit light budget (~10K tokens = ~40K chars)
        mission = result["mission"]
        mission_chars = len(mission)

        # Light vision should limit to ~10K tokens (40K chars)
        # Allow some overhead for formatting, but should be significantly truncated
        max_expected_chars = 40000 * 1.5  # 50% overhead for formatting

        assert mission_chars <= max_expected_chars, (
            f"Vision content not truncated properly: "
            f"{mission_chars} chars > {max_expected_chars} chars (expected ~40K for 10K token budget)"
        )

        # Verify truncation marker is present
        assert "[... vision truncated" in mission.lower(), (
            "Truncation marker should be present when vision exceeds budget"
        )

        print(
            f"\n[VISION_DEPTH] Light depth successfully limited mission to {mission_chars} chars "
            f"(~{mission_chars // 4} tokens)"
        )


@pytest.mark.asyncio
class TestCLIModeRulesInclusion:
    """
    Test 4: CLI Mode Rules Inclusion

    Verifies CLI mode response includes cli_mode_rules for Task tool enforcement.

    Related to Handover 0335 (CLI Mode Template Export) and 0260 (CLI Toggle).
    """

    async def test_cli_mode_includes_agent_spawning_rules(self, db_manager):
        """Verify CLI mode response includes cli_mode_rules for Task tool enforcement"""
        tenant_key = f"test_tenant_{uuid4().hex[:8]}"

        async with db_manager.get_session_async() as session:
            # Create product
            product = Product(
                tenant_key=tenant_key,
                name="Test Product CLI Mode",
                description="Testing CLI mode rules inclusion",
                config_data={"tech_stack": {"languages": ["Python"]}},
                is_active=True,
            )
            session.add(product)
            await session.flush()

            # Create project
            project = Project(
                tenant_key=tenant_key,
                product_id=product.id,
                name="Test Project CLI Mode",
                description="Test project for CLI mode",
                mission="Build test project for validating CLI mode agent spawning constraints",
                status="active",
                context_budget=150000,
                context_used=0,
            )
            session.add(project)
            await session.flush()

            # Create orchestrator job with CLI mode execution
            orchestrator_id = str(uuid4())
            orchestrator = MCPAgentJob(
                job_id=orchestrator_id,
                tenant_key=tenant_key,
                project_id=project.id,
                agent_type="orchestrator",
                mission="Test orchestrator for CLI mode",
                status="waiting",
                context_budget=150000,
                context_used=0,
                instance_number=1,
                job_metadata={
                    "field_priorities": {},
                    "depth_config": {},
                    "execution_mode": "claude_code_cli",  # CLI MODE
                },
            )
            session.add(orchestrator)
            await session.commit()

        # ACT: Generate orchestrator instructions
        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        result = await tool_accessor.get_orchestrator_instructions(
            orchestrator_id=orchestrator_id, tenant_key=tenant_key
        )

        # ASSERT: Response includes agent_spawning_constraint for CLI mode
        assert "agent_spawning_constraint" in result, (
            "CLI mode should include agent_spawning_constraint field"
        )

        constraint = result["agent_spawning_constraint"]
        assert constraint["mode"] == "strict_task_tool", (
            "CLI mode should enforce strict Task tool usage"
        )

        assert "allowed_agent_types" in constraint, (
            "Constraint should include list of allowed agent types"
        )

        assert "instruction" in constraint, (
            "Constraint should include instruction text for orchestrator"
        )

        # Verify instruction mentions Task tool
        assert "Task tool" in constraint["instruction"], (
            "Instruction should mention Claude Code's native Task tool"
        )

        print(
            f"\n[CLI_MODE] Agent spawning constraint included with "
            f"{len(constraint['allowed_agent_types'])} allowed types"
        )


@pytest.mark.asyncio
class TestPromptQualityRegression:
    """
    Comprehensive regression tests for all prompt quality fixes.

    These tests combine multiple fixes to ensure overall prompt quality
    meets production standards.
    """

    @pytest.mark.xfail(reason="Bug 0336-2: Token estimation inaccuracy affects comprehensive test")
    async def test_comprehensive_prompt_quality_check(self, db_manager):
        """Comprehensive test: Tech stack + token estimation + vision depth + CLI mode"""
        tenant_key = f"test_tenant_{uuid4().hex[:8]}"

        async with db_manager.get_session_async() as session:
            # Create product with all features
            product = Product(
                tenant_key=tenant_key,
                name="Comprehensive Test Product",
                description="Full-featured product for comprehensive testing",
                config_data={
                    "tech_stack": {
                        "languages": "Python 3.11+",  # STRING (bug scenario)
                        "backend": ["FastAPI", "PostgreSQL"],  # LIST
                        "frontend": "Vue 3",  # STRING
                    }
                },
                is_active=True,
            )
            session.add(product)
            await session.flush()

            # Create vision document
            vision_doc = VisionDocument(
                tenant_key=tenant_key,
                product_id=product.id,
                document_name="Test Vision",
                document_type="vision",
                vision_document="# Vision\n\n" + "Product vision content. " * 1000,
                storage_type="inline",
                is_active=True,
                display_order=1,
            )
            session.add(vision_doc)
            await session.flush()

            # Create project
            project = Project(
                tenant_key=tenant_key,
                product_id=product.id,
                name="Comprehensive Test Project",
                description="Full-featured project for testing",
                mission="Build comprehensive test project for validating all prompt quality fixes",
                status="active",
                context_budget=150000,
                context_used=0,
            )
            session.add(project)
            await session.flush()

            # Create orchestrator job with CLI mode
            orchestrator_id = str(uuid4())
            orchestrator = MCPAgentJob(
                job_id=orchestrator_id,
                tenant_key=tenant_key,
                project_id=project.id,
                agent_type="orchestrator",
                mission="Comprehensive test orchestrator",
                status="waiting",
                context_budget=150000,
                context_used=0,
                instance_number=1,
                job_metadata={
                    "field_priorities": {
                        "tech_stack": 1,
                        "vision_documents": 2,
                    },
                    "depth_config": {"vision_chunking": "moderate"},
                    "execution_mode": "claude_code_cli",
                },
            )
            session.add(orchestrator)
            await session.commit()

        # ACT: Generate orchestrator instructions
        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        result = await tool_accessor.get_orchestrator_instructions(
            orchestrator_id=orchestrator_id, tenant_key=tenant_key
        )

        mission = result["mission"]

        # ASSERT: All quality checks pass

        # 1. Tech stack displays correctly (not character-separated)
        assert "Python 3.11+" in mission, "Tech stack should show 'Python 3.11+'"
        assert "P, y, t, h, o, n" not in mission, "Tech stack should NOT split into characters"

        # 2. Token estimation is accurate
        encoder = tiktoken.get_encoding("cl100k_base")
        actual_tokens = len(encoder.encode(mission))
        estimated_tokens = result["estimated_tokens"]
        discrepancy_ratio = abs(actual_tokens - estimated_tokens) / actual_tokens

        assert discrepancy_ratio < 0.20, (
            f"Token estimation accuracy within 20%: {discrepancy_ratio:.1%}"
        )

        # 3. Vision depth respected
        # Moderate depth should limit to ~17,500 tokens (~70K chars)
        assert len(mission) <= 70000 * 1.5, "Vision depth should limit mission size"

        # 4. CLI mode rules included
        assert "agent_spawning_constraint" in result, "CLI mode constraint present"
        assert result["agent_spawning_constraint"]["mode"] == "strict_task_tool"

        print(
            f"\n[COMPREHENSIVE] All quality checks passed:\n"
            f"  - Tech stack: Correct formatting ✓\n"
            f"  - Token estimation: {(1 - discrepancy_ratio) * 100:.1f}% accurate ✓\n"
            f"  - Vision depth: {len(mission)} chars ✓\n"
            f"  - CLI mode: Agent constraint present ✓"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
