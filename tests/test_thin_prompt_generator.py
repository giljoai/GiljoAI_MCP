"""
Unit tests for ThinClientPromptGenerator (Handover 0368 - Add Execution Plan Section).

Tests:
- Execution plan section appears in implementation prompt
- get_agent_mission tool call appears in prompt
- Proper formatting and integration with existing sections

TDD Status: GREEN ✅ - Tests verify new execution plan section
"""

import pytest
import pytest_asyncio
from uuid import uuid4
from passlib.hash import bcrypt

from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator
from src.giljo_mcp.models import Product, Project, User
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from src.giljo_mcp.tenant import TenantManager


@pytest_asyncio.fixture
async def test_user(db_manager):
    """
    Create test user for prompt generator tests.

    Returns the User object for assertions and token generation.
    """
    unique_suffix = uuid4().hex[:8]
    # Generate valid tenant key (tk_ + 32 chars)
    tenant_key = TenantManager.generate_tenant_key()

    async with db_manager.get_session_async() as session:
        user = User(
            username=f"test_user_{unique_suffix}",
            email=f"test_{unique_suffix}@example.com",
            password_hash=bcrypt.hash("test_password"),
            tenant_key=tenant_key,
            role="developer",
            is_active=True
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user




@pytest.mark.asyncio
async def test_continuation_prompt_for_instance_greater_than_1(
    db_manager,
    test_user
):
    """
    Test: Instance > 1 should get continuation prompt, not staging prompt.

    Handover 0429 Phase 4: When orchestrator is a successor (instance > 1),
    generate_staging_prompt should return a CONTINUATION prompt that tells
    the orchestrator to check messages and workflow status, NOT to re-stage.

    GIVEN: An orchestrator with instance_number > 1 (successor)
    WHEN: generate_staging_prompt() is called
    THEN: Prompt includes continuation instructions, NOT staging workflow

    TDD Status: RED ❌ - Test created, implementation pending
    """
    product_id = f"test-prod-{uuid4().hex[:12]}"
    project_id = f"test-proj-{uuid4().hex[:12]}"
    orchestrator_job_id = f"test-orch-{uuid4().hex[:12]}"
    agent_id = f"test-agent-{uuid4().hex[:12]}"

    async with db_manager.get_session_async() as session:
        # Create test product
        product = Product(
            id=product_id,
            tenant_key=test_user.tenant_key,
            name="Test Product",
            description="Product for continuation prompt tests",
        )
        session.add(product)

        # Create project
        project = Project(
            id=project_id,
            tenant_key=test_user.tenant_key,
            product_id=product.id,
            name="Test Project",
            mission="Test project mission",
            description="Test project description",
            status="active",
        )
        session.add(project)

        # Create orchestrator job (persistent work order)
        orchestrator_job = AgentJob(
            job_id=orchestrator_job_id,
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            job_type="orchestrator",
            mission="Orchestrate the test project",
            status="active",
        )
        session.add(orchestrator_job)

        # Create instance 1 (first orchestrator) - should get staging prompt
        instance1 = AgentExecution(
            agent_id=f"{agent_id}-inst1",
            job_id=orchestrator_job_id,
            tenant_key=test_user.tenant_key,
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            instance_number=1,
            status="complete",  # Ran out of context
        )
        session.add(instance1)

        # Create instance 2 (successor) - should get continuation prompt
        instance2 = AgentExecution(
            agent_id=f"{agent_id}-inst2",
            job_id=orchestrator_job_id,
            tenant_key=test_user.tenant_key,
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            instance_number=2,
            status="waiting",
        )
        session.add(instance2)

        await session.commit()

    # Test instance 1 (first orchestrator) - should get staging prompt
    async with db_manager.get_session_async() as gen_session:
        generator = ThinClientPromptGenerator(db=gen_session, tenant_key=test_user.tenant_key)

        staging_prompt = await generator.generate_staging_prompt(
            orchestrator_id=orchestrator_job_id,
            project_id=project_id,
            agent_id=f"{agent_id}-inst1"
        )

        # Staging prompt should have staging-specific content
        assert "get_orchestrator_instructions" in staging_prompt.lower(), \
            "Instance 1 should get staging prompt with get_orchestrator_instructions"
        assert "fetch protocol" in staging_prompt.lower() or "orchestrator_protocol" in staging_prompt.lower(), \
            "Instance 1 should be told to fetch protocol"

    # Test instance 2 (successor) - should get continuation prompt
    async with db_manager.get_session_async() as gen_session:
        generator = ThinClientPromptGenerator(db=gen_session, tenant_key=test_user.tenant_key)

        continuation_prompt = await generator.generate_staging_prompt(
            orchestrator_id=orchestrator_job_id,
            project_id=project_id,
            agent_id=f"{agent_id}-inst2"
        )

        # Continuation prompt should have continuation-specific content
        assert "continuation" in continuation_prompt.lower(), \
            "Instance 2 should get continuation prompt"
        assert "do not re-stage" in continuation_prompt.lower() or \
               "do not call get_orchestrator_instructions" in continuation_prompt.lower(), \
            "Instance 2 should be told NOT to re-stage"
        assert "receive_messages" in continuation_prompt.lower(), \
            "Instance 2 should be told to check messages"
        assert "get_workflow_status" in continuation_prompt.lower(), \
            "Instance 2 should be told to check workflow status"
        assert "predecessor" in continuation_prompt.lower(), \
            "Instance 2 should be told about predecessor"

        # Should NOT have staging workflow instructions
        assert continuation_prompt.count("get_orchestrator_instructions") <= 1, \
            "Continuation prompt should not emphasize get_orchestrator_instructions"
