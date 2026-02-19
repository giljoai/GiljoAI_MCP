"""
Phase 3: E2E Claude Code Mode Workflow Test (Handover 0246d)

Tests complete user workflow for Claude Code execution mode:
1. Create project
2. Toggle execution mode to "claude-code"
3. Stage project (spawn orchestrator)
4. Verify orchestrator prompt uses Task tool
5. Trigger succession
6. Verify successor uses Task tool

TDD Phase: RED (Tests written BEFORE E2E implementation)
Expected: Tests MAY FAIL initially until E2E workflow complete
"""

from uuid import uuid4

import pytest
import pytest_asyncio

from src.giljo_mcp.models import Product, Project, User
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator


@pytest_asyncio.fixture
async def test_user(db_session):
    """Create test user"""
    user = User(
        username=f"testuser_{uuid4().hex[:8]}",
        email=f"test_{uuid4().hex[:8]}@example.com",
        tenant_key=f"tenant_{uuid4().hex[:8]}",
        role="developer",
        password_hash="hashed_password",
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
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest.mark.asyncio
class TestClaudeCodeModeWorkflow:
    """E2E tests for Claude Code execution mode workflow."""

    # HANDOVER 0422: Removed test_complete_claude_code_workflow
    # This test called trigger_succession() which was removed (dead token budget cleanup)

    async def test_claude_code_mode_agent_spawning(
        self, db_session, db_manager, tenant_manager, test_user, test_product
    ):
        """
        Test that Claude Code mode spawns agents via Task tool
        (not message passing).
        """

        tenant_key = test_user.tenant_key

        # Create project in Claude Code mode
        project = Project(
            name=f"Claude Code Agent Spawn Test {uuid4().hex[:8]}",
            description="Test agent spawning in Claude Code mode",
            tenant_key=tenant_key,
            product_id=test_product.id,
            status="active",
            mission="Test agent spawning",
            meta_data={"execution_mode": "claude-code"},
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        # Create AgentJob first (AgentExecution requires job_id FK)
        job = AgentJob(
            job_id=str(uuid4()),
            tenant_key=tenant_key,
            project_id=project.id,
            job_type="orchestrator",
            mission="Test agent spawning",
            status="active",
            job_metadata={"user_id": test_user.id, "execution_mode": "claude-code"},
        )
        db_session.add(job)
        await db_session.flush()

        # Create orchestrator execution
        orchestrator = AgentExecution(
            job_id=job.job_id,
            tenant_key=tenant_key,
            agent_display_name="orchestrator",
            status="working",
        )
        db_session.add(orchestrator)
        await db_session.commit()

        # Generate prompt
        generator = ThinClientPromptGenerator(db=db_session, tenant_key=tenant_key)

        result = await generator.generate(project_id=str(project.id), user_id=test_user.id, tool="claude-code")
        prompt = result["thin_prompt"]

        # Verify Task tool instructions present
        assert "Task" in prompt, "Prompt must reference Task tool for agent spawning"

        # Verify agent discovery instructions
        assert "get_available_agents" in prompt.lower(), (
            "Prompt must reference get_available_agents() for dynamic discovery"
        )

        # Claude Code mode should spawn agents like this:
        # Task(description="...", prompt="...", subagent_type="implementer")
        assert "subagent" in prompt.lower() or "spawn" in prompt.lower(), (
            "Prompt should include agent spawning instructions"
        )

        print("\n- Claude Code mode agent spawning validated:")
        print("  - Uses Task tool: yes")
        print("  - Discovers agents dynamically: yes")
        print("  - Includes spawning instructions: yes")

    async def test_claude_code_mode_token_efficiency(
        self, db_session, db_manager, tenant_manager, test_user, test_product
    ):
        """
        Test that Claude Code mode achieves token reduction target
        (<600 tokens, ideal ~450).
        """

        tenant_key = test_user.tenant_key

        # Create project in Claude Code mode
        project = Project(
            name=f"Token Efficiency Test {uuid4().hex[:8]}",
            description="Test token reduction in Claude Code mode",
            tenant_key=tenant_key,
            product_id=test_product.id,
            status="active",
            mission="Test tokens",
            meta_data={"execution_mode": "claude-code"},
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        # Create AgentJob first (AgentExecution requires job_id FK)
        job = AgentJob(
            job_id=str(uuid4()),
            tenant_key=tenant_key,
            project_id=project.id,
            job_type="orchestrator",
            mission="Test",
            status="active",
            job_metadata={"user_id": test_user.id, "execution_mode": "claude-code"},
        )
        db_session.add(job)
        await db_session.flush()

        # Create orchestrator execution
        orchestrator = AgentExecution(
            job_id=job.job_id,
            tenant_key=tenant_key,
            agent_display_name="orchestrator",
            status="waiting",
        )
        db_session.add(orchestrator)
        await db_session.commit()

        # Generate prompt
        generator = ThinClientPromptGenerator(db=db_session, tenant_key=tenant_key)

        result = await generator.generate(project_id=str(project.id), user_id=test_user.id, tool="claude-code")
        prompt = result["thin_prompt"]

        # Token estimation
        token_count = len(prompt) // 4
        reduction_from_old = ((880 - token_count) / 880) * 100  # Old: ~880 tokens

        assert token_count < 600, f"Token count {token_count} exceeds target (<600)"

        # Ideally should be around 450 tokens
        is_ideal = 400 <= token_count <= 500

        print("\n- Claude Code mode token efficiency:")
        print(f"  - Token count: ~{token_count} tokens")
        print("  - Target: <600 tokens")
        print(f"  - Ideal range (400-500): {is_ideal}")
        print(f"  - Reduction from old (880): {reduction_from_old:.1f}%")
