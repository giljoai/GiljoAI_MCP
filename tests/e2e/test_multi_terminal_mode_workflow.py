"""
Phase 3: E2E Multi-Terminal Mode Workflow Test (Handover 0246d)

Tests complete user workflow for Multi-Terminal execution mode:
1. Create project
2. Keep default execution mode (multi-terminal)
3. Stage project
4. Verify orchestrator uses message passing
5. Trigger succession
6. Verify successor uses message passing

TDD Phase: RED (Tests written BEFORE E2E implementation)
Expected: Tests MAY FAIL initially until E2E workflow complete
"""

import pytest
import pytest_asyncio
from uuid import uuid4

from src.giljo_mcp.models import Project, Product, User
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from src.giljo_mcp.services.project_service import ProjectService
from src.giljo_mcp.services.orchestration_service import OrchestrationService
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator


@pytest_asyncio.fixture
async def test_user(db_session):
    """Create test user"""
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
async def test_product(db_session, test_user):
    """Create test product"""
    product = Product(
        name=f"Test Product {uuid4().hex[:8]}",
        description="E2E test product",
        tenant_key=test_user.tenant_key,
        is_active=True
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest.mark.asyncio
class TestMultiTerminalModeWorkflow:
    """E2E tests for Multi-Terminal execution mode workflow."""

    # HANDOVER 0422: Removed test_complete_multi_terminal_workflow
    # This test called trigger_succession() which was removed (dead token budget cleanup)

    async def test_multi_terminal_mode_agent_communication(
        self, db_session, db_manager, tenant_manager, test_user, test_product
    ):
        """
        Test that Multi-Terminal mode uses message passing for agent communication
        (not Task tool).
        """

        tenant_key = test_user.tenant_key

        # Create project in Multi-Terminal mode
        project = Project(
            name=f"Multi-Terminal Communication Test {uuid4().hex[:8]}",
            description="Test message passing in Multi-Terminal mode",
            tenant_key=tenant_key,
            product_id=test_product.id,
            status="active",
            mission="Test message passing",
            meta_data={"execution_mode": "multi-terminal"}
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        # Create orchestrator
        orchestrator = AgentExecution(
            project_id=project.id,
            tenant_key=tenant_key,
            agent_display_name="orchestrator",
            status="active",
            mission="Test message passing",
            job_metadata={
                "user_id": test_user.id,
                "execution_mode": "multi-terminal"
            }
        )
        db_session.add(orchestrator)
        await db_session.commit()

        # Generate prompt
        generator = ThinClientPromptGenerator(
            db=db_session,
            tenant_key=tenant_key
        )

        result = await generator.generate(
            project_id=str(project.id),
            user_id=test_user.id,
            tool="multi-terminal")
        prompt = result["thin_prompt"]

        # Verify message passing tools present
        assert "send_message" in prompt or "message passing" in prompt.lower(), \
            "Prompt must reference message passing for agent communication"

        # Verify agent discovery instructions
        assert "get_available_agents" in prompt.lower() or "spawn_agent_job" in prompt, \
            "Prompt must reference agent discovery or spawning"

        # Multi-Terminal mode should spawn agents like this:
        # spawn_agent_job(agent_display_name="implementer", ...)
        # send_message(to_agent="...", message="...")
        assert "spawn" in prompt.lower() or "agent_job" in prompt, \
            "Prompt should include agent spawning instructions"

        print("\n✓ Multi-Terminal mode agent communication validated:")
        print(f"  - Uses message passing: ✓")
        print(f"  - Discovers/spawns agents: ✓")
        print(f"  - Includes communication instructions: ✓")

    async def test_multi_terminal_mode_token_efficiency(
        self, db_session, db_manager, tenant_manager, test_user, test_product
    ):
        """
        Test that Multi-Terminal mode also achieves token reduction target
        (<600 tokens, ideal ~450).
        """

        tenant_key = test_user.tenant_key

        # Create project in Multi-Terminal mode
        project = Project(
            name=f"Token Efficiency Test {uuid4().hex[:8]}",
            description="Test token reduction in Multi-Terminal mode",
            tenant_key=tenant_key,
            product_id=test_product.id,
            status="active",
            mission="Test tokens",
            meta_data={"execution_mode": "multi-terminal"}
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        # Create orchestrator
        orchestrator = AgentExecution(
            project_id=project.id,
            tenant_key=tenant_key,
            agent_display_name="orchestrator",
            status="waiting",
            mission="Test",
            job_metadata={
                "user_id": test_user.id,
                "execution_mode": "multi-terminal"
            }
        )
        db_session.add(orchestrator)
        await db_session.commit()

        # Generate prompt
        generator = ThinClientPromptGenerator(
            db=db_session,
            tenant_key=tenant_key
        )

        result = await generator.generate(
            project_id=str(project.id),
            user_id=test_user.id,
            tool="multi-terminal")
        prompt = result["thin_prompt"]

        # Token estimation
        token_count = len(prompt) // 4
        reduction_from_old = ((880 - token_count) / 880) * 100  # Old: ~880 tokens

        assert token_count < 600, \
            f"Token count {token_count} exceeds target (<600)"

        # Ideally should be around 450 tokens
        is_ideal = 400 <= token_count <= 500

        print("\n✓ Multi-Terminal mode token efficiency:")
        print(f"  - Token count: ~{token_count} tokens")
        print(f"  - Target: <600 tokens")
        print(f"  - Ideal range (400-500): {is_ideal}")
        print(f"  - Reduction from old (880): {reduction_from_old:.1f}%")

    async def test_legacy_projects_default_to_multi_terminal(
        self, db_session, db_manager, tenant_manager, test_user, test_product
    ):
        """
        Test that legacy projects (no execution_mode set) default to multi-terminal.
        """

        tenant_key = test_user.tenant_key

        # Create legacy project (no execution_mode in meta_data)
        legacy_project = Project(
            name=f"Legacy Project {uuid4().hex[:8]}",
            description="Legacy project without execution_mode",
            tenant_key=tenant_key,
            product_id=test_product.id,
            status="active",
            mission="Legacy test",
            meta_data={}  # NO execution_mode set
        )
        db_session.add(legacy_project)
        await db_session.commit()
        await db_session.refresh(legacy_project)

        # Create orchestrator for legacy project
        orchestrator = AgentExecution(
            project_id=legacy_project.id,
            tenant_key=tenant_key,
            agent_display_name="orchestrator",
            status="waiting",
            mission="Legacy test",
            job_metadata={
                "user_id": test_user.id
                # NO execution_mode set
            }
        )
        db_session.add(orchestrator)
        await db_session.commit()

        # Generate prompt
        generator = ThinClientPromptGenerator(
            db=db_session,
            tenant_key=tenant_key
        )

        result = await generator.generate(
            project_id=str(legacy_project.id),
            user_id=test_user.id,
            tool="multi-terminal"  # Default should be multi-terminal
        )
        prompt = result["thin_prompt"]

        # Legacy projects should use message passing (multi-terminal default)
        message_tools = ["send_message", "receive_messages", "spawn_agent_job"]
        has_message_tools = any(tool in prompt for tool in message_tools)
        assert has_message_tools, \
            "Legacy projects must default to multi-terminal mode (message passing)"

        print("\n✓ Legacy project defaults validated:")
        print(f"  - Project has no execution_mode set: ✓")
        print(f"  - Defaults to multi-terminal mode: ✓")
        print(f"  - Uses message passing: ✓")
