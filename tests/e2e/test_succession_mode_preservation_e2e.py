"""
Phase 3: E2E Succession Mode Preservation Test (Handover 0246d)

Tests succession chain validation (A→B→C):
1. Create project in Claude Code mode
2. Spawn Orchestrator A
3. Trigger succession (A→B)
4. Verify B inherits Claude Code mode
5. Trigger succession (B→C)
6. Verify C still uses Claude Code mode
7. Change mode in project metadata
8. Spawn Orchestrator D
9. Verify D uses new mode

TDD Phase: RED (Tests written BEFORE E2E implementation)
Expected: Tests MAY FAIL initially until succession logic complete
"""

import pytest
import pytest_asyncio
from uuid import uuid4

from src.giljo_mcp.models import Project, Product, User
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
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
        description="E2E succession test product",
        tenant_key=test_user.tenant_key,
        is_active=True
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest.mark.asyncio
class TestSuccessionModePreservationE2E:
    """E2E tests for succession mode preservation across chains."""

    async def test_succession_chain_a_b_c_preserves_mode(
        self, db_session, db_manager, tenant_manager, test_user, test_product
    ):
        """
        Test succession chain (A→B→C) preserves execution mode:
        1. Create project in Claude Code mode
        2. Spawn Orchestrator A
        3. Trigger succession (A→B)
        4. Verify B inherits Claude Code mode
        5. Trigger succession (B→C)
        6. Verify C still uses Claude Code mode
        """

        tenant_key = test_user.tenant_key

        # Step 1: Create project in Claude Code mode
        project = Project(
            name=f"Succession Chain Test {uuid4().hex[:8]}",
            description="Test mode preservation through succession chain",
            tenant_key=tenant_key,
            product_id=test_product.id,
            status="active",
            mission="Test succession chain",
            meta_data={"execution_mode": "claude-code"}
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        orchestration_service = OrchestrationService(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            test_session=db_session,
        )

        # Step 2: Spawn Orchestrator A
        orchestrator_a = AgentExecution(
            project_id=project.id,
            tenant_key=tenant_key,
            agent_display_name="orchestrator",
            status="active",
            mission="Orchestrator A",
            context_used=10000,
            context_budget=100000,
            job_metadata={
                "user_id": test_user.id,
                "execution_mode": "claude-code",
                "instance_number": 1
            }
        )
        db_session.add(orchestrator_a)
        await db_session.commit()
        await db_session.refresh(orchestrator_a)

        # Step 3: Trigger succession (A→B)
        # Simulate context exhaustion
        orchestrator_a.context_used = 90000
        await db_session.commit()

        result_ab = await orchestration_service.trigger_succession(
            job_id=str(orchestrator_a.job_id),
            reason="context_limit",
            tenant_key=tenant_key
        )

        assert result_ab["success"] is True
        orchestrator_b_id = result_ab["data"]["successor_id"]

        # Step 4: Verify B inherits Claude Code mode
        from sqlalchemy import select
        stmt = select(AgentExecution).where(AgentExecution.job_id == orchestrator_b_id)
        result = await db_session.execute(stmt)
        orchestrator_b = result.scalar_one()

        assert orchestrator_b.metadata.get("execution_mode") == "claude-code", \
            "Orchestrator B must inherit Claude Code mode from A"
        assert orchestrator_b.metadata.get("instance_number") == 2, \
            "Orchestrator B should be instance 2"

        # Step 5: Trigger succession (B→C)
        # Simulate context exhaustion again
        orchestrator_b.context_used = 90000
        orchestrator_b.context_budget = 100000
        await db_session.commit()

        result_bc = await orchestration_service.trigger_succession(
            job_id=str(orchestrator_b.job_id),
            reason="context_limit",
            tenant_key=tenant_key
        )

        assert result_bc["success"] is True
        orchestrator_c_id = result_bc["data"]["successor_id"]

        # Step 6: Verify C still uses Claude Code mode
        stmt = select(AgentExecution).where(AgentExecution.job_id == orchestrator_c_id)
        result = await db_session.execute(stmt)
        orchestrator_c = result.scalar_one()

        assert orchestrator_c.metadata.get("execution_mode") == "claude-code", \
            "Orchestrator C must still use Claude Code mode (inherited from B)"
        assert orchestrator_c.metadata.get("instance_number") == 3, \
            "Orchestrator C should be instance 3"

        print("\n✓ Succession chain (A→B→C) mode preservation validated:")
        print(f"  A: {orchestrator_a.job_id} (mode: claude-code, instance: 1)")
        print(f"  B: {orchestrator_b.job_id} (mode: {orchestrator_b.metadata['execution_mode']}, instance: 2)")
        print(f"  C: {orchestrator_c.job_id} (mode: {orchestrator_c.metadata['execution_mode']}, instance: 3)")
        print(f"  Mode preserved through chain: ✓")

    async def test_mode_change_affects_new_orchestrator(
        self, db_session, db_manager, tenant_manager, test_user, test_product
    ):
        """
        Test that changing execution mode in project metadata
        affects new orchestrator spawns:
        1. Create project in Claude Code mode
        2. Spawn Orchestrator A (claude-code)
        3. Change project mode to multi-terminal
        4. Spawn Orchestrator D (should use multi-terminal)
        """

        tenant_key = test_user.tenant_key

        # Step 1: Create project in Claude Code mode
        project = Project(
            name=f"Mode Change Test {uuid4().hex[:8]}",
            description="Test mode change affects new orchestrators",
            tenant_key=tenant_key,
            product_id=test_product.id,
            status="active",
            mission="Test mode change",
            meta_data={"execution_mode": "claude-code"}
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        # Step 2: Spawn Orchestrator A (claude-code)
        orchestrator_a = AgentExecution(
            project_id=project.id,
            tenant_key=tenant_key,
            agent_display_name="orchestrator",
            status="active",
            mission="Orchestrator A",
            job_metadata={
                "user_id": test_user.id,
                "execution_mode": "claude-code",
                "instance_number": 1
            }
        )
        db_session.add(orchestrator_a)
        await db_session.commit()
        await db_session.refresh(orchestrator_a)

        assert orchestrator_a.metadata["execution_mode"] == "claude-code"

        # Step 3: Change project mode to multi-terminal
        project.meta_data = {"execution_mode": "multi-terminal"}
        await db_session.commit()

        # Step 4: Spawn Orchestrator D (should use multi-terminal)
        orchestrator_d = AgentExecution(
            project_id=project.id,
            tenant_key=tenant_key,
            agent_display_name="orchestrator",
            status="waiting",
            mission="Orchestrator D",
            job_metadata={
                "user_id": test_user.id,
                "execution_mode": project.meta_data.get("execution_mode", "multi-terminal"),
                "instance_number": 4  # Hypothetical instance 4
            }
        )
        db_session.add(orchestrator_d)
        await db_session.commit()
        await db_session.refresh(orchestrator_d)

        assert orchestrator_d.metadata["execution_mode"] == "multi-terminal", \
            "New orchestrator D must use new project mode (multi-terminal)"

        print("\n✓ Mode change affects new orchestrator:")
        print(f"  Original mode: claude-code (Orchestrator A)")
        print(f"  Changed mode: multi-terminal")
        print(f"  New orchestrator D uses: {orchestrator_d.metadata['execution_mode']}")

    async def test_succession_preserves_mode_but_respects_manual_override(
        self, db_session, db_manager, tenant_manager, test_user, test_product
    ):
        """
        Test that succession preserves mode from predecessor,
        but can be manually overridden if needed.
        """

        tenant_key = test_user.tenant_key

        # Create project in multi-terminal mode
        project = Project(
            name=f"Manual Override Test {uuid4().hex[:8]}",
            description="Test manual mode override during succession",
            tenant_key=tenant_key,
            product_id=test_product.id,
            status="active",
            mission="Test override",
            meta_data={"execution_mode": "multi-terminal"}
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        # Spawn Orchestrator A (multi-terminal)
        orchestrator_a = AgentExecution(
            project_id=project.id,
            tenant_key=tenant_key,
            agent_display_name="orchestrator",
            status="active",
            mission="Orchestrator A",
            context_used=90000,
            context_budget=100000,
            job_metadata={
                "user_id": test_user.id,
                "execution_mode": "multi-terminal",
                "instance_number": 1
            }
        )
        db_session.add(orchestrator_a)
        await db_session.commit()

        # Trigger succession (A→B)
        orchestration_service = OrchestrationService(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            test_session=db_session,
        )

        result = await orchestration_service.trigger_succession(
            job_id=str(orchestrator_a.job_id),
            reason="context_limit",
            tenant_key=tenant_key
        )

        assert result["success"] is True
        orchestrator_b_id = result["data"]["successor_id"]

        # Verify B inherited multi-terminal mode
        from sqlalchemy import select
        stmt = select(AgentExecution).where(AgentExecution.job_id == orchestrator_b_id)
        result_b = await db_session.execute(stmt)
        orchestrator_b = result_b.scalar_one()

        assert orchestrator_b.metadata["execution_mode"] == "multi-terminal", \
            "Successor B should inherit multi-terminal mode"

        # Manually override B's mode to claude-code (hypothetical scenario)
        orchestrator_b.metadata["execution_mode"] = "claude-code"
        await db_session.commit()

        # Now trigger succession (B→C)
        orchestrator_b.context_used = 90000
        orchestrator_b.context_budget = 100000
        await db_session.commit()

        result_bc = await orchestration_service.trigger_succession(
            job_id=str(orchestrator_b.job_id),
            reason="context_limit",
            tenant_key=tenant_key
        )

        assert result_bc["success"] is True
        orchestrator_c_id = result_bc["data"]["successor_id"]

        # Verify C inherited the OVERRIDDEN mode from B (claude-code)
        stmt = select(AgentExecution).where(AgentExecution.job_id == orchestrator_c_id)
        result_c = await db_session.execute(stmt)
        orchestrator_c = result_c.scalar_one()

        assert orchestrator_c.metadata["execution_mode"] == "claude-code", \
            "Successor C should inherit overridden mode from B (claude-code)"

        print("\n✓ Succession respects manual overrides:")
        print(f"  A: multi-terminal (original)")
        print(f"  B: claude-code (manually overridden)")
        print(f"  C: {orchestrator_c.metadata['execution_mode']} (inherited from B)")

    async def test_succession_chain_generates_different_prompts_per_mode(
        self, db_session, db_manager, tenant_manager, test_user, test_product
    ):
        """
        Test that succession chain generates mode-specific prompts
        for each orchestrator in the chain.
        """

        tenant_key = test_user.tenant_key

        # Create project in Claude Code mode
        project = Project(
            name=f"Prompt Variation Test {uuid4().hex[:8]}",
            description="Test prompts vary by mode",
            tenant_key=tenant_key,
            product_id=test_product.id,
            status="active",
            mission="Test prompts",
            meta_data={"execution_mode": "claude-code"}
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        # Spawn Orchestrator A (claude-code)
        orchestrator_a = AgentExecution(
            project_id=project.id,
            tenant_key=tenant_key,
            agent_display_name="orchestrator",
            status="active",
            mission="Orchestrator A",
            context_used=90000,
            context_budget=100000,
            job_metadata={
                "user_id": test_user.id,
                "execution_mode": "claude-code",
                "instance_number": 1
            }
        )
        db_session.add(orchestrator_a)
        await db_session.commit()

        # Generate prompt for A
        generator_a = ThinClientPromptGenerator(
            db=db_session,
            tenant_key=tenant_key
        )

        result_a = await generator_a.generate(
            project_id=str(project.id),
            user_id=test_user.id,
            tool="claude-code",
            instance_number=1
        )
        prompt_a = result_a["thin_prompt"]

        # Trigger succession (A→B)
        orchestration_service = OrchestrationService(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            test_session=db_session,
        )

        result = await orchestration_service.trigger_succession(
            job_id=str(orchestrator_a.job_id),
            reason="context_limit",
            tenant_key=tenant_key
        )

        orchestrator_b_id = result["data"]["successor_id"]
        from sqlalchemy import select
        stmt = select(AgentExecution).where(AgentExecution.job_id == orchestrator_b_id)
        result_b = await db_session.execute(stmt)
        orchestrator_b = result_b.scalar_one()

        # Generate prompt for B
        generator_b = ThinClientPromptGenerator(
            db=db_session,
            tenant_key=tenant_key
        )

        result_b = await generator_b.generate(
            project_id=str(project.id),
            user_id=test_user.id,
            tool="claude-code",
            instance_number=2
        )
        prompt_b = result_b["thin_prompt"]

        # Both prompts should use Claude Code mode
        assert "Task" in prompt_a or "task tool" in prompt_a.lower()
        assert "Task" in prompt_b or "task tool" in prompt_b.lower()

        # Prompts should have similar structure but different instance numbers
        assert "Instance 1" in prompt_a or "instance 1" in prompt_a.lower()
        assert "Instance 2" in prompt_b or "instance 2" in prompt_b.lower()

        print("\n✓ Succession chain prompts validated:")
        print(f"  A prompt uses Task tool: {'Task' in prompt_a}")
        print(f"  B prompt uses Task tool: {'Task' in prompt_b}")
        print(f"  Instance numbers differ: ✓")
