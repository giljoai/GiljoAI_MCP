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
async def test_execution_plan_section_in_implementation_prompt(
    db_manager,
    test_user
):
    """
    Test 1: Execution plan section appears in implementation prompt.

    GIVEN: A CLI project with active orchestrator and spawned agents
    WHEN: _build_claude_code_execution_prompt() is called
    THEN: Prompt includes "Your Execution Plan (from Staging)" section

    TDD Status: GREEN ✅ - Implementation complete
    """
    # Store IDs for later use
    product_id = f"test-prod-{uuid4().hex[:12]}"
    project_id = f"test-proj-{uuid4().hex[:12]}"
    orchestrator_job_id = f"test-orch-{uuid4().hex[:12]}"
    job_id = f"test-agent-{uuid4().hex[:12]}"

    async with db_manager.get_session_async() as session:
        # Create test product
        product = Product(
            id=product_id,
            tenant_key=test_user.tenant_key,
            name="Test Product",
            description="Product for execution plan tests",
        )
        session.add(product)

        # Create CLI mode project
        project = Project(
            id=project_id,
            tenant_key=test_user.tenant_key,
            product_id=product.id,
            name="Test Project",
            mission="Test project mission",
            description="Test project description",
            status="active",
            execution_mode="claude_code_cli",
        )
        session.add(project)

        # Create orchestrator job and execution
        orchestrator_job = AgentJob(
            job_id=orchestrator_job_id,
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            job_type="orchestrator",
            mission="Orchestrate the test project",
            status="active",
        )
        session.add(orchestrator_job)

        orchestrator = AgentExecution(
            job_id=orchestrator_job_id,
            tenant_key=test_user.tenant_key,
            agent_display_name="orchestrator",
            agent_name="Test Orchestrator",
            status="working",
        )
        session.add(orchestrator)

        # Create spawned agent job and execution
        agent_job = AgentJob(
            job_id=job_id,
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            job_type="implementer",
            mission="Implement test feature",
            status="active",
        )
        session.add(agent_job)

        agent = AgentExecution(
            job_id=job_id,
            tenant_key=test_user.tenant_key,
            agent_display_name="implementer",
            agent_name="Test Implementer",
            status="waiting",
            spawned_by=orchestrator.agent_id,
        )
        session.add(agent)

        await session.commit()

    # Create prompt generator and build prompt (in new session with fresh objects)
    async with db_manager.get_session_async() as gen_session:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        # Fetch project and agents with eager loading
        project = await gen_session.get(Project, project_id)
        agent_result = await gen_session.execute(
            select(AgentExecution)
            .options(selectinload(AgentExecution.job))
            .where(AgentExecution.job_id == job_id)
        )
        agent = agent_result.scalar_one()

        generator = ThinClientPromptGenerator(db=gen_session, tenant_key=test_user.tenant_key)

        # Build implementation prompt (uses orchestrator's job_id as orchestrator_id)
        prompt = generator._build_claude_code_execution_prompt(
            orchestrator_id=orchestrator_job_id,
            project=project,
            agent_jobs=[agent]
        )

        # Verify execution plan section exists
        assert "Your Execution Plan (from Staging)" in prompt, \
            "Prompt should include execution plan section"

        # Verify get_agent_mission call is present
        assert "get_agent_mission" in prompt, \
            "Prompt should include get_agent_mission tool call"

        # Verify orchestrator_job_id and tenant_key are in the call
        assert orchestrator_job_id in prompt, \
            "Prompt should include orchestrator job_id"
        assert test_user.tenant_key in prompt, \
            "Prompt should include tenant_key"

        # Verify section explains what is returned
        assert "Agent execution order" in prompt or "execution order" in prompt, \
            "Prompt should explain execution order is returned"
        assert "Dependency graph" in prompt or "dependency" in prompt.lower(), \
            "Prompt should explain dependency graph is returned"

        # Verify section appears before "What You've Already Done"
        plan_index = prompt.find("Your Execution Plan")
        done_index = prompt.find("What You've Already Done")
        assert plan_index < done_index, \
            "Execution plan section should appear before 'What You've Already Done'"


@pytest.mark.asyncio
async def test_execution_plan_section_formatting(
    db_manager,
    test_user
):
    """
    Test 2: Execution plan section has proper formatting.

    GIVEN: A CLI project with active orchestrator
    WHEN: _build_claude_code_execution_prompt() is called
    THEN: Prompt includes properly formatted code block with MCP tool call

    TDD Status: GREEN ✅ - Implementation complete
    """
    async with db_manager.get_session_async() as session:
        # Create minimal test setup
        product = Product(
            id=f"test-prod-{uuid4().hex[:12]}",
            tenant_key=test_user.tenant_key,
            name="Test Product",
            description="Product for formatting tests",
        )
        session.add(product)

        project = Project(
            id=f"test-proj-{uuid4().hex[:12]}",
            tenant_key=test_user.tenant_key,
            product_id=product.id,
            name="Test Project",
            mission="Test project mission",
            description="Test project description",
            status="active",
            execution_mode="claude_code_cli",
        )
        session.add(project)

        # Create orchestrator job and execution
        orchestrator_job_id = f"test-orch-{uuid4().hex[:12]}"
        orchestrator_job = AgentJob(
            job_id=orchestrator_job_id,
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            job_type="orchestrator",
            mission="Orchestrate the test project",
            status="active",
        )
        session.add(orchestrator_job)

        orchestrator = AgentExecution(
            job_id=orchestrator_job_id,
            tenant_key=test_user.tenant_key,
            agent_display_name="orchestrator",
            agent_name="Test Orchestrator",
            status="working",
        )
        session.add(orchestrator)

        await session.commit()
        await session.refresh(project)

    # Create prompt generator (outside session context)
    async with db_manager.get_session_async() as gen_session:
        generator = ThinClientPromptGenerator(db=gen_session, tenant_key=test_user.tenant_key)

        # Build implementation prompt
        prompt = generator._build_claude_code_execution_prompt(
            orchestrator_id=orchestrator_job_id,
            project=project,
            agent_jobs=[]
        )

        # Verify code block formatting
        assert "```python" in prompt, \
            "Prompt should include Python code block"

        # Verify proper MCP tool call syntax
        expected_call = f'get_agent_mission(job_id="{orchestrator_job_id}", tenant_key="{test_user.tenant_key}")'
        assert expected_call in prompt, \
            f"Prompt should include properly formatted MCP tool call: {expected_call}"

        # Verify closing code block
        code_block_start = prompt.find("```python")
        code_block_end = prompt.find("```", code_block_start + 9)
        assert code_block_end > code_block_start, \
            "Code block should be properly closed"


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
