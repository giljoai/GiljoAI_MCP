"""
Test orchestration.py tools with agent_id parameter (Phase C - TDD RED).

Handover 0366c: Agent Identity Refactor - Tool Signature Changes

These tests are EXPECTED TO FAIL initially (TDD RED phase).
They test the NEW signatures that will be implemented in Phase D.

Semantic Contract:
- agent_id = executor UUID (the WHO - specific agent instance)
- job_id = work order UUID (the WHAT - persistent across succession)

Tools Under Test:
1. get_orchestrator_instructions(agent_id, tenant_key) - NEW signature
2. get_agent_mission(agent_id, tenant_key) - NEW signature

Phase A+B Complete:
- AgentJob model exists (job_id PK, mission, job_type, status)
- AgentExecution model exists (agent_id PK, job_id FK, instance_number, status)
- Database schema migration complete

Phase C (this file):
- Write failing tests for NEW tool signatures
- Tests expect agent_id parameter (not orchestrator_id/job_id)
- Tests verify tools return BOTH agent_id and job_id in response

Phase D (next):
- Update orchestration.py to use NEW signatures
- Make tests pass (TDD GREEN)
"""
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Product, Project, AgentTemplate
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from src.giljo_mcp.tools.orchestration import get_orchestrator_instructions, get_agent_mission


@pytest.mark.asyncio
async def test_get_orchestrator_instructions_by_agent_id(db_manager: DatabaseManager):
    """
    Test get_orchestrator_instructions() with NEW signature using agent_id.

    Expected to FAIL until Phase D implementation.

    Verifies:
    - Tool accepts agent_id parameter (not orchestrator_id)
    - Tool returns BOTH agent_id and job_id in response
    - Tool retrieves orchestrator execution via agent_id
    - Tool fetches mission from parent AgentJob
    - Multi-tenant isolation enforced
    """
    tenant_key = str(uuid.uuid4())

    async with db_manager.get_session_async() as session:
        # Create product
        product = Product(
            id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            name="Test Product",
            description="Test product for agent_id testing",
            is_active=True
        )
        session.add(product)
        await session.flush()

        # Create project
        project = Project(
            id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name="Test Project [TEST01]",
            description="Test project requirements for agent_id testing",
            mission="Test project mission",
            status="active"
        )
        session.add(project)
        await session.flush()

        # Create AgentJob (work order - the WHAT)
        agent_job = AgentJob(
            job_id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            project_id=project.id,
            mission="Build authentication system with OAuth2 support",
            job_type="orchestrator",
            status="active",
            job_metadata={
                "field_priorities": {},
                "depth_config": {},
                "user_id": str(uuid.uuid4())
            }
        )
        session.add(agent_job)
        await session.flush()

        # Create AgentExecution (executor - the WHO)
        agent_execution = AgentExecution(
            agent_id=str(uuid.uuid4()),
            job_id=agent_job.job_id,
            tenant_key=tenant_key,
            agent_type="orchestrator",
            instance_number=1,
            status="waiting",
            context_budget=150000,
            context_used=0
        )
        session.add(agent_execution)
        await session.commit()

        agent_id = agent_execution.agent_id
        job_id = agent_job.job_id

    # Call tool with NEW signature (agent_id parameter)
    # Expected to FAIL until Phase D implements this signature
    result = await get_orchestrator_instructions(
        agent_id=agent_id,  # NEW: Use agent_id (executor UUID)
        tenant_key=tenant_key,
        db_manager=db_manager
    )

    # Verify response structure
    assert "error" not in result, f"Tool returned error: {result.get('message', 'Unknown error')}"

    # Verify BOTH IDs returned in response (Phase C requirement)
    assert "agent_id" in result, "Response should include agent_id (WHO is executing)"
    assert "job_id" in result, "Response should include job_id (WHAT work order)"

    # Verify correct IDs
    assert result["agent_id"] == agent_id, "agent_id should match executor UUID"
    assert result["job_id"] == job_id, "job_id should match work order UUID"

    # Verify mission fetched from AgentJob
    assert "mission" in result, "Response should include mission content"
    assert "Build authentication system" in result["mission"], "Mission should be from AgentJob"

    # Verify project context included
    assert result["project_id"] == str(project.id), "Project ID should match"
    assert result["project_name"] == project.name, "Project name should match"

    # Verify context tracking fields
    assert result["context_budget"] == 150000, "Context budget should match execution"
    assert result["context_used"] == 0, "Context used should be zero initially"

    # Verify thin client flag
    assert result["thin_client"] is True, "Should be thin client architecture"


@pytest.mark.asyncio
async def test_get_agent_mission_by_agent_id(db_manager: DatabaseManager):
    """
    Test get_agent_mission() with NEW signature using agent_id.

    Expected to FAIL until Phase D implementation.

    Verifies:
    - Tool accepts agent_id parameter (not job_id)
    - Tool returns BOTH agent_id and job_id in response
    - Tool retrieves agent execution via agent_id
    - Tool fetches mission from parent AgentJob
    - Multi-tenant isolation enforced
    """
    tenant_key = str(uuid.uuid4())

    async with db_manager.get_session_async() as session:
        # Create product and project (minimal setup)
        product = Product(
            id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            name="Test Product",
            description="Test product",
            is_active=True
        )
        session.add(product)
        await session.flush()

        project = Project(
            id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name="Test Project [TEST02]",
            description="Test project",
            mission="Test mission",
            status="active"
        )
        session.add(project)
        await session.flush()

        # Create AgentJob (work order)
        agent_job = AgentJob(
            job_id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            project_id=project.id,
            mission="Implement user registration with email verification",
            job_type="implementer",
            status="active",
            job_metadata={}
        )
        session.add(agent_job)
        await session.flush()

        # Create AgentExecution (executor)
        agent_execution = AgentExecution(
            agent_id=str(uuid.uuid4()),
            job_id=agent_job.job_id,
            tenant_key=tenant_key,
            agent_type="implementer",
            agent_name="Backend Implementer",
            instance_number=1,
            status="waiting"
        )
        session.add(agent_execution)
        await session.commit()

        agent_id = agent_execution.agent_id
        job_id = agent_job.job_id

    # Call tool with NEW signature (agent_id parameter)
    # Expected to FAIL until Phase D implements this signature
    result = await get_agent_mission(
        agent_id=agent_id,  # NEW: Use agent_id (executor UUID)
        tenant_key=tenant_key,
        db_manager=db_manager
    )

    # Verify response structure
    assert "error" not in result, f"Tool returned error: {result.get('message', 'Unknown error')}"

    # Verify BOTH IDs returned in response (Phase C requirement)
    assert "agent_id" in result, "Response should include agent_id (WHO is executing)"
    assert "job_id" in result, "Response should include job_id (WHAT work order)"

    # Verify correct IDs
    assert result["agent_id"] == agent_id, "agent_id should match executor UUID"
    assert result["job_id"] == job_id, "job_id should match work order UUID"

    # Verify mission fetched from AgentJob
    assert "mission" in result, "Response should include mission content"
    assert "Implement user registration" in result["mission"], "Mission should be from AgentJob"

    # Verify agent metadata
    assert result["agent_name"] == "Backend Implementer", "Agent name should match execution"
    assert result["agent_type"] == "implementer", "Agent type should match execution"

    # Verify thin client flag
    assert result["thin_client"] is True, "Should be thin client architecture"


@pytest.mark.asyncio
async def test_agent_id_multi_tenant_isolation(db_manager: DatabaseManager):
    """
    Test that agent_id lookups enforce multi-tenant isolation.

    Expected to FAIL until Phase D implementation.

    Verifies:
    - Agent in tenant A cannot be accessed with tenant B's key
    - Proper error handling for cross-tenant access attempts
    - No data leakage between tenants
    """
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())

    async with db_manager.get_session_async() as session:
        # Create resources for Tenant A
        product_a = Product(
            id=str(uuid.uuid4()),
            tenant_key=tenant_a,
            name="Product A",
            description="Product A",
            is_active=True
        )
        session.add(product_a)
        await session.flush()

        project_a = Project(
            id=str(uuid.uuid4()),
            tenant_key=tenant_a,
            product_id=product_a.id,
            name="Project A [TESTA]",
            description="Project A",
            mission="Mission A",
            status="active"
        )
        session.add(project_a)
        await session.flush()

        job_a = AgentJob(
            job_id=str(uuid.uuid4()),
            tenant_key=tenant_a,
            project_id=project_a.id,
            mission="Mission for Tenant A",
            job_type="orchestrator",
            status="active",
            job_metadata={"field_priorities": {}}
        )
        session.add(job_a)
        await session.flush()

        execution_a = AgentExecution(
            agent_id=str(uuid.uuid4()),
            job_id=job_a.job_id,
            tenant_key=tenant_a,
            agent_type="orchestrator",
            instance_number=1,
            status="waiting"
        )
        session.add(execution_a)
        await session.commit()

        agent_id_a = execution_a.agent_id

    # Attempt to access Tenant A's agent with Tenant B's key
    # Expected to FAIL until Phase D implements proper tenant isolation
    result = await get_orchestrator_instructions(
        agent_id=agent_id_a,  # Tenant A's agent
        tenant_key=tenant_b,  # Tenant B's key
        db_manager=db_manager
    )

    # Verify access is denied (multi-tenant isolation)
    assert "error" in result, "Should return error for cross-tenant access attempt"
    assert result["error"] == "NOT_FOUND", "Error type should be NOT_FOUND (not revealing existence)"
    assert "not found" in result["message"].lower(), "Error message should indicate resource not found"


@pytest.mark.asyncio
async def test_agent_succession_preserves_job_id(db_manager: DatabaseManager):
    """
    Test that agent succession creates NEW agent_id but preserves job_id.

    Expected to FAIL until Phase D implementation.

    Verifies:
    - Successor execution has NEW agent_id (different executor)
    - Successor execution has SAME job_id (same work order)
    - Both executions retrieve the same mission content
    - Instance numbers increment correctly
    """
    tenant_key = str(uuid.uuid4())

    async with db_manager.get_session_async() as session:
        # Create product and project
        product = Product(
            id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            name="Test Product",
            description="Test product",
            is_active=True
        )
        session.add(product)
        await session.flush()

        project = Project(
            id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name="Test Project [TEST03]",
            description="Test project",
            mission="Test mission",
            status="active"
        )
        session.add(project)
        await session.flush()

        # Create AgentJob (persistent work order)
        agent_job = AgentJob(
            job_id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            project_id=project.id,
            mission="Build feature X with tests and documentation",
            job_type="orchestrator",
            status="active",
            job_metadata={"field_priorities": {}}
        )
        session.add(agent_job)
        await session.flush()

        # Create FIRST execution (instance 1)
        execution_1 = AgentExecution(
            agent_id=str(uuid.uuid4()),
            job_id=agent_job.job_id,
            tenant_key=tenant_key,
            agent_type="orchestrator",
            instance_number=1,
            status="decommissioned",  # Handed over
            context_budget=150000,
            context_used=120000  # Near capacity
        )
        session.add(execution_1)
        await session.flush()

        # Create SECOND execution (instance 2 - successor)
        execution_2 = AgentExecution(
            agent_id=str(uuid.uuid4()),
            job_id=agent_job.job_id,  # SAME job_id
            tenant_key=tenant_key,
            agent_type="orchestrator",
            instance_number=2,  # Incremented
            status="working",
            spawned_by=execution_1.agent_id,  # Points to predecessor's agent_id
            context_budget=150000,
            context_used=0  # Fresh context
        )
        session.add(execution_2)

        # Link executions via succession chain
        execution_1.succeeded_by = execution_2.agent_id
        await session.commit()

        agent_id_1 = execution_1.agent_id
        agent_id_2 = execution_2.agent_id
        job_id = agent_job.job_id

    # Fetch mission via FIRST execution (decommissioned)
    result_1 = await get_orchestrator_instructions(
        agent_id=agent_id_1,
        tenant_key=tenant_key,
        db_manager=db_manager
    )

    # Fetch mission via SECOND execution (current)
    result_2 = await get_orchestrator_instructions(
        agent_id=agent_id_2,
        tenant_key=tenant_key,
        db_manager=db_manager
    )

    # Verify DIFFERENT agent_ids (different executors)
    assert result_1["agent_id"] == agent_id_1, "First result should have first agent_id"
    assert result_2["agent_id"] == agent_id_2, "Second result should have second agent_id"
    assert result_1["agent_id"] != result_2["agent_id"], "Agent IDs should be different (different executors)"

    # Verify SAME job_id (same work order)
    assert result_1["job_id"] == job_id, "First result should have correct job_id"
    assert result_2["job_id"] == job_id, "Second result should have correct job_id"
    assert result_1["job_id"] == result_2["job_id"], "Job IDs should be identical (same work order)"

    # Verify SAME mission content (retrieved from AgentJob)
    assert result_1["mission"] == result_2["mission"], "Mission should be identical (same job)"
    assert "Build feature X" in result_1["mission"], "Mission content should match job"

    # Verify instance numbers differ
    assert result_1.get("instance_number") == 1, "First execution should be instance 1"
    assert result_2.get("instance_number") == 2, "Second execution should be instance 2"

    # Verify context tracking differs (execution-specific)
    assert result_1["context_used"] == 120000, "First execution context used should match"
    assert result_2["context_used"] == 0, "Second execution context used should be fresh"


@pytest.mark.asyncio
async def test_spawn_agent_job_creates_execution_record(db_manager: DatabaseManager):
    """
    spawn_agent_job must create BOTH AgentJob AND AgentExecution (dual-model).

    Expected to FAIL until HIGH #3 is fixed.

    Verifies:
    - spawn_agent_job creates AgentJob record (work order)
    - spawn_agent_job creates AgentExecution record (executor)
    - Response includes BOTH job_id and agent_id
    - AgentExecution.instance_number defaults to 1
    - AgentExecution.status defaults to "waiting"
    - Both records share same tenant_key, agent_type
    """
    tenant_key = str(uuid.uuid4())

    async with db_manager.get_session_async() as session:
        # Create product and project
        product = Product(
            id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            name="Test Product",
            description="Test product",
            is_active=True
        )
        session.add(product)
        await session.flush()

        project = Project(
            id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name="Test Project [SPAWN01]",
            description="Test project for spawn_agent_job",
            mission="Build authentication system",
            status="active"
        )
        session.add(project)
        await session.flush()

        # Create agent template (required for spawn validation)
        template = AgentTemplate(
            id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name="analyzer",
            template_content="Analyze code for security issues",
            system_instructions="MCP system instructions",
            is_active=True
        )
        session.add(template)
        await session.commit()

        project_id = project.id

    # Import spawn_agent_job
    from src.giljo_mcp.tools.orchestration import spawn_agent_job

    # Call spawn_agent_job
    result = await spawn_agent_job(
        agent_type="analyzer",
        agent_name="analyzer",  # Must match template name
        mission="Analyze codebase for security vulnerabilities",
        project_id=str(project_id),
        tenant_key=tenant_key,
        db_manager=db_manager
    )

    # Behavior: Returns both job_id AND agent_id
    assert result["success"] is True, f"spawn_agent_job should succeed: {result}"
    assert "job_id" in result, "Response must include job_id (work order UUID)"
    assert "agent_job_id" in result, "Response must include agent_job_id (backwards compat)"
    assert "agent_id" in result, "Response must include agent_id (executor UUID) - THIS IS THE KEY ASSERTION"

    job_id = result["job_id"]
    agent_id = result["agent_id"]

    # Verify job_id and agent_job_id are the same (backwards compat)
    assert result["agent_job_id"] == job_id, "agent_job_id should match job_id for backwards compatibility"

    # Verify database state: AgentJob exists
    async with db_manager.get_session_async() as session:
        job = await session.execute(
            select(AgentJob).where(AgentJob.job_id == job_id)
        )
        job = job.scalar_one_or_none()
        assert job is not None, "AgentJob record must exist in database"
        assert job.tenant_key == tenant_key, "AgentJob tenant_key must match"
        assert job.job_type == "analyzer", "AgentJob job_type must match"
        assert job.mission == "Analyze codebase for security vulnerabilities", "AgentJob mission must match"
        assert job.status == "active", "AgentJob status should be active"

        # Verify database state: AgentExecution exists
        execution = await session.execute(
            select(AgentExecution).where(AgentExecution.agent_id == agent_id)
        )
        execution = execution.scalar_one_or_none()
        assert execution is not None, "AgentExecution record must exist in database"
        assert execution.job_id == job_id, "AgentExecution job_id must reference AgentJob"
        assert execution.tenant_key == tenant_key, "AgentExecution tenant_key must match"
        assert execution.agent_type == "analyzer", "AgentExecution agent_type must match"
        assert execution.instance_number == 1, "AgentExecution instance_number should default to 1"
        assert execution.status == "waiting", "AgentExecution status should default to 'waiting'"
        assert execution.agent_name == "analyzer", "AgentExecution agent_name should match"


@pytest.mark.asyncio
async def test_thin_prompt_uses_agent_id_parameter(db_manager: DatabaseManager):
    """
    Generated thin prompt should use 'agent_id' not 'agent_job_id'.

    Expected to FAIL until HIGH #4 is fixed.

    Verifies:
    - Thin prompt references agent_id in get_agent_mission call
    - Thin prompt does NOT use deprecated agent_job_id parameter
    - Thin prompt uses correct MCP tool signature
    """
    tenant_key = str(uuid.uuid4())

    async with db_manager.get_session_async() as session:
        # Create product and project
        product = Product(
            id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            name="Test Product",
            description="Test product",
            is_active=True
        )
        session.add(product)
        await session.flush()

        project = Project(
            id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name="Test Project [PROMPT01]",
            description="Test project for thin prompt",
            mission="Build feature",
            status="active"
        )
        session.add(project)
        await session.flush()

        # Create agent template (required for spawn validation)
        template = AgentTemplate(
            id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name="implementer",
            template_content="Implement features",
            system_instructions="MCP system instructions",
            is_active=True
        )
        session.add(template)
        await session.commit()

        project_id = project.id

    # Import spawn_agent_job
    from src.giljo_mcp.tools.orchestration import spawn_agent_job

    # Spawn agent to get thin prompt
    result = await spawn_agent_job(
        agent_type="implementer",
        agent_name="implementer",  # Must match template name
        mission="Implement user authentication",
        project_id=str(project_id),
        tenant_key=tenant_key,
        db_manager=db_manager
    )

    assert result["success"] is True, f"spawn_agent_job should succeed: {result}"
    assert "agent_prompt" in result, "Response should include thin prompt"

    prompt = result["agent_prompt"]

    # Behavior: Prompt should reference agent_id correctly
    # The get_agent_mission tool expects: get_agent_mission(agent_id, tenant_key)
    # NOT: get_agent_mission(agent_job_id, tenant_key)

    # Check for correct parameter name in prompt
    assert "agent_id" in prompt or result.get("agent_id") in prompt, \
        "Prompt should reference 'agent_id' parameter or include the actual agent_id value"

    # Check that deprecated parameter name is NOT used
    assert "agent_job_id" not in prompt.replace("mcp__giljo-mcp__", ""), \
        "Prompt should NOT use deprecated 'agent_job_id' parameter name (except in tool name)"

    # Verify the prompt includes the correct tool call format
    assert "mcp__giljo-mcp__get_agent_mission" in prompt, \
        "Prompt should include correct MCP tool name"
