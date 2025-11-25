"""
Phase 2: Full Stack Integration Test (Handover 0246d)

Tests complete flow across all 3 components:
1. Set execution mode via toggle (0246a)
2. Verify mode persisted (0246a)
3. Fetch agents via MCP tool (0246b)
4. Validate token reduction in prompt (0246b)
5. Trigger succession (0246c)
6. Verify successor mode preserved (0246c)

TDD Phase: RED (Tests written BEFORE full integration)
Expected: Tests FAIL initially until all components integrated
"""

import pytest
import pytest_asyncio
from uuid import uuid4

from src.giljo_mcp.models import Project, MCPAgentJob, Product, User
from src.giljo_mcp.services.orchestration_service import OrchestrationService
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator


@pytest_asyncio.fixture
async def test_user(db_session):
    """Create test user with tenant"""
    user = User(
        username=f"testuser_{uuid4().hex[:8]}",
        email=f"test_{uuid4().hex[:8]}@example.com",
        tenant_key=f"tenant_{uuid4().hex[:8]}",
        role="developer",
        password_hash="hashed_password"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_tenant(test_user):
    """Get tenant key from test user"""
    return test_user.tenant_key


@pytest_asyncio.fixture
async def test_product(db_session, test_tenant):
    """Create test product"""
    product = Product(
        name=f"Test Product {uuid4().hex[:8]}",
        description="Full stack test product",
        tenant_key=test_tenant,
        is_active=True
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def test_project(db_session, test_tenant, test_product):
    """Create test project"""
    project = Project(
        name=f"Test Project {uuid4().hex[:8]}",
        description="Full stack test project",
        tenant_key=test_tenant,
        product_id=test_product.id,
        status="active",
        mission="Test full stack flow",
        meta_data={}  # Will be populated with execution_mode
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.mark.asyncio
class TestFullStackModeFlow:
    """Full stack integration test for execution mode flow."""

    async def test_complete_flow_toggle_discovery_succession(
        self, db_session, db_manager, tenant_manager,
        test_project, test_tenant, test_user
    ):
        """
        Test complete flow across all 3 components:
        1. Set execution mode via toggle (0246a)
        2. Verify mode persisted (0246a)
        3. Fetch agents via MCP tool (0246b)
        4. Validate token reduction in prompt (0246b)
        5. Trigger succession (0246c)
        6. Verify successor mode preserved (0246c)
        """

        # STEP 1-2: Set and verify execution mode
        # Simulate toggle setting execution mode to "claude-code"
        test_project.meta_data = {"execution_mode": "claude-code"}
        await db_session.commit()
        await db_session.refresh(test_project)

        # Verify persisted
        from sqlalchemy import select
        stmt = select(Project).where(Project.id == test_project.id)
        result = await db_session.execute(stmt)
        project = result.scalar_one()
        assert project.meta_data.get("execution_mode") == "claude-code", \
            "Execution mode must be persisted in project metadata"

        # STEP 3: Fetch agents dynamically via MCP tool
        from src.giljo_mcp.tools.agent_discovery import get_available_agents

        agents_result = await get_available_agents(
            session=db_session,
            tenant_key=test_tenant
        )

        assert agents_result["success"] is True, \
            "get_available_agents() must return success"
        assert "data" in agents_result, \
            "get_available_agents() must return data"
        assert "agents" in agents_result["data"], \
            "get_available_agents() must return agents list"

        # STEP 4: Generate prompt and validate token reduction
        orchestrator = MCPAgentJob(
            project_id=test_project.id,
            tenant_key=test_tenant,
            agent_type="orchestrator",
            status="waiting",
            mission="Test mission for full stack flow",
            job_metadata={
                "user_id": test_user.id,
                "execution_mode": "claude-code",
                "field_priorities": {
                    "product_core": 1,
                    "agent_templates": 2,
                    "project_context": 1
                }
            }
        )
        db_session.add(orchestrator)
        await db_session.commit()
        await db_session.refresh(orchestrator)

        generator = ThinClientPromptGenerator(
            db=db_session,
            tenant_key=test_tenant
        )

        result = await generator.generate(
            project_id=str(test_project.id),
            user_id=test_user.id,
            tool="claude-code",
            instance_number=1,
            field_priorities={
                "product_core": 1,
                "agent_templates": 2,
                "project_context": 1
            }
        )
        prompt = result["thin_prompt"]

        # Verify dynamic discovery used (not embedded templates)
        assert "get_available_agents" in prompt.lower(), \
            "Prompt must reference get_available_agents() for dynamic discovery"

        # Embedded template check - should NOT have inline templates
        assert "### Implementer" not in prompt, \
            "Prompt should not embed Implementer template inline"
        assert "### Tester" not in prompt, \
            "Prompt should not embed Tester template inline"

        # Verify token reduction (vs fat prompts at ~3500 tokens)
        token_count = len(prompt) // 4  # Rough estimate
        assert token_count <= 1200, \
            f"Token count {token_count} too high (target: <1200, fat prompt was ~3500)"

        # STEP 5-6: Trigger succession and verify mode preserved
        # Simulate context exhaustion (90% capacity)
        orchestrator.context_used = 90000
        orchestrator.context_budget = 100000
        orchestrator.metadata = {
            "execution_mode": "claude-code",  # Original mode
            "instance_number": 1
        }
        await db_session.commit()

        service = OrchestrationService(
            db_manager=db_manager,
            tenant_manager=tenant_manager
        )

        result = await service.trigger_succession(
            job_id=str(orchestrator.job_id),
            reason="context_limit",
            tenant_key=test_tenant
        )

        assert result["success"] is True, \
            "Succession must succeed"

        # Verify successor created
        successor_id = result["successor_job_id"]
        stmt = select(MCPAgentJob).where(MCPAgentJob.job_id == successor_id)
        result_successor = await db_session.execute(stmt)
        successor = result_successor.scalar_one()

        # Verify mode preserved through succession
        assert successor.metadata.get("execution_mode") == "claude-code", \
            "Successor must inherit execution mode from predecessor"

        print("\n✓ Full stack flow validated:")
        print(f"  - Execution mode toggled: claude-code")
        print(f"  - Mode persisted in project metadata")
        print(f"  - Agents discovered dynamically: {agents_result['data']['count']} agents")
        print(f"  - Token count reduced: ~{token_count} tokens (target: <600)")
        print(f"  - Succession triggered with mode preservation")
        print(f"  - Successor inherited mode: {successor.metadata.get('execution_mode')}")

    async def test_mode_affects_agent_spawning_strategy(
        self, db_session, test_project, test_tenant, test_user
    ):
        """
        Test that execution mode affects how agents are spawned:
        - Claude Code mode: Uses Task tool for agent spawning
        - Multi-Terminal mode: Uses message passing
        """

        # Test Claude Code mode
        test_project.meta_data = {"execution_mode": "claude-code"}
        await db_session.commit()

        orchestrator_cc = MCPAgentJob(
            project_id=test_project.id,
            tenant_key=test_tenant,
            agent_type="orchestrator",
            status="waiting",
            mission="Test Claude Code mode",
            job_metadata={
                "user_id": test_user.id,
                "execution_mode": "claude-code"
            }
        )
        db_session.add(orchestrator_cc)
        await db_session.commit()
        await db_session.refresh(orchestrator_cc)

        generator_cc = ThinClientPromptGenerator(
            db=db_session,
            tenant_key=test_tenant
        )

        result_cc = await generator_cc.generate(
            project_id=str(test_project.id),
            user_id=test_user.id,
            tool="claude-code",
            instance_number=1
        )
        prompt_cc = result_cc["thin_prompt"]

        # Claude Code mode should mention Task tool
        assert "Task" in prompt_cc or "task tool" in prompt_cc.lower(), \
            "Claude Code mode should reference Task tool for agent spawning"

        # Test Multi-Terminal mode
        test_project.meta_data = {"execution_mode": "multi-terminal"}
        await db_session.commit()

        orchestrator_mt = MCPAgentJob(
            project_id=test_project.id,
            tenant_key=test_tenant,
            agent_type="orchestrator",
            status="waiting",
            mission="Test Multi-Terminal mode",
            job_metadata={
                "user_id": test_user.id,
                "execution_mode": "multi-terminal"
            }
        )
        db_session.add(orchestrator_mt)
        await db_session.commit()
        await db_session.refresh(orchestrator_mt)

        generator_mt = ThinClientPromptGenerator(
            db=db_session,
            tenant_key=test_tenant
        )

        result_mt = await generator_mt.generate(
            project_id=str(test_project.id),
            user_id=test_user.id,
            tool="multi-terminal",
            instance_number=1
        )
        prompt_mt = result_mt["thin_prompt"]

        # Multi-Terminal mode should mention message passing
        assert "message" in prompt_mt.lower() or "terminal" in prompt_mt.lower(), \
            "Multi-Terminal mode should reference message passing"

        # Prompts should be different based on mode
        assert prompt_cc != prompt_mt, \
            "Execution mode should produce different prompts"

        print("\n✓ Mode affects agent spawning strategy:")
        print(f"  - Claude Code mode mentions Task tool: {'Task' in prompt_cc}")
        print(f"  - Multi-Terminal mode mentions messaging: {'message' in prompt_mt.lower()}")
        print(f"  - Prompts are mode-specific: {prompt_cc != prompt_mt}")

    async def test_token_reduction_achieved_across_all_modes(
        self, db_session, test_project, test_tenant, test_user
    ):
        """
        Test that token reduction is achieved in both execution modes:
        - Target: <600 tokens (was ~594-880 tokens with embedded templates)
        - Ideal: ~450 tokens
        """

        modes = ["claude-code", "multi-terminal"]
        token_counts = {}

        for mode in modes:
            test_project.meta_data = {"execution_mode": mode}
            await db_session.commit()

            orchestrator = MCPAgentJob(
                project_id=test_project.id,
                tenant_key=test_tenant,
                agent_type="orchestrator",
                status="waiting",
                mission=f"Test {mode} mode",
                job_metadata={
                    "user_id": test_user.id,
                    "execution_mode": mode
                }
            )
            db_session.add(orchestrator)
            await db_session.commit()
            await db_session.refresh(orchestrator)

            generator = ThinClientPromptGenerator(
                db=db_session,
                tenant_key=test_tenant
            )

            result = await generator.generate(
                project_id=str(test_project.id),
                user_id=test_user.id,
                tool=mode,
                instance_number=1,
                field_priorities={
                    "product_core": 1,
                    "agent_templates": 2,
                    "project_context": 1
                }
            )
            prompt = result["thin_prompt"]

            token_count = len(prompt) // 4  # Rough estimate
            token_counts[mode] = token_count

            assert token_count < 600, \
                f"{mode} mode token count {token_count} exceeds target (<600)"

        print("\n✓ Token reduction achieved across all modes:")
        for mode, count in token_counts.items():
            reduction_pct = ((880 - count) / 880) * 100  # 880 was old max
            print(f"  - {mode}: ~{count} tokens ({reduction_pct:.1f}% reduction from 880)")
        print(f"  - Target: <600 tokens")
        print(f"  - Ideal: ~450 tokens")
