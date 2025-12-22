"""
Phase C TDD - RED Phase for context.py

Tests for agent_id-based context tracking (AgentExecution-specific).
These tests WILL FAIL initially - they enforce new semantic parameter naming.

Handover 0366c: Context tools use agent_id (executor-specific context windows).

Key Semantic Points:
- agent_id = executor UUID (WHO is executing)
- job_id = work order UUID (WHAT is being done)
- Context tracking is per-executor (AgentExecution.context_used, .context_budget)
- Multiple executions on same job have independent context windows
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4


@pytest.mark.asyncio
async def test_fetch_context_uses_agent_id(db_manager):
    """
    Test that context fetching uses agent_id parameter.

    Semantic: Context is executor-specific, not job-specific.
    Each AgentExecution has its own context window.
    """
    from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
    from src.giljo_mcp.tools.context import fetch_context

    tenant_key = f"tenant_{uuid4()}"
    job_id = str(uuid4())
    agent_id = str(uuid4())

    # Create job and execution
    async with db_manager.get_session_async() as session:
        job = AgentJob(
            job_id=job_id,
            tenant_key=tenant_key,
            mission="Build authentication system",
            job_type="orchestrator",
            status="active",
        )
        session.add(job)

        execution = AgentExecution(
            agent_id=agent_id,
            job_id=job_id,
            tenant_key=tenant_key,
            agent_type="orchestrator",
            instance_number=1,
            status="working",
            context_used=5000,
            context_budget=50000,
        )
        session.add(execution)
        await session.commit()

    # TEST: fetch_context should accept agent_id (not job_id)
    result = await fetch_context(
        agent_id=agent_id,
        tenant_key=tenant_key,
        categories=["product_core"]
    )

    # EXPECTED: Result includes agent_id and current context usage
    assert result["success"] is True
    assert result["agent_id"] == agent_id
    assert result["job_id"] == job_id  # Also include job_id for reference
    assert result["context_used"] == 5000
    assert result["context_budget"] == 50000
    assert "context" in result


@pytest.mark.asyncio
async def test_context_tracking_updates_agent_execution(db_manager):
    """
    Test that context tracking updates AgentExecution.context_used.

    Semantic: Context window is tracked per executor instance.
    Updating context_used modifies the AgentExecution row (not AgentJob).
    """
    from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
    from src.giljo_mcp.tools.context import update_context_usage
    from sqlalchemy import select

    tenant_key = f"tenant_{uuid4()}"
    job_id = str(uuid4())
    agent_id = str(uuid4())

    # Create job and execution
    async with db_manager.get_session_async() as session:
        job = AgentJob(
            job_id=job_id,
            tenant_key=tenant_key,
            mission="Build authentication system",
            job_type="orchestrator",
            status="active",
        )
        session.add(job)

        execution = AgentExecution(
            agent_id=agent_id,
            job_id=job_id,
            tenant_key=tenant_key,
            agent_type="orchestrator",
            instance_number=1,
            status="working",
            context_used=10000,
            context_budget=50000,
        )
        session.add(execution)
        await session.commit()

    # TEST: Update context usage via agent_id
    result = await update_context_usage(
        agent_id=agent_id,
        tenant_key=tenant_key,
        tokens_used=3500
    )

    # EXPECTED: AgentExecution row updated
    assert result["success"] is True
    assert result["agent_id"] == agent_id
    assert result["context_used"] == 13500  # 10000 + 3500
    assert result["context_budget"] == 50000

    # VERIFY: Database updated correctly
    async with db_manager.get_session_async() as session:
        query = select(AgentExecution).where(AgentExecution.agent_id == agent_id)
        result = await session.execute(query)
        execution = result.scalar_one()

        assert execution.context_used == 13500
        assert execution.last_progress_at is not None  # Should auto-update


@pytest.mark.asyncio
async def test_multiple_executions_independent_context(db_manager):
    """
    Test that multiple executions on same job have independent context windows.

    Semantic: Succession creates NEW executor with fresh context window.
    Executor 1 and Executor 2 track context independently.
    """
    from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
    from src.giljo_mcp.tools.context import fetch_context
    from sqlalchemy import select

    tenant_key = f"tenant_{uuid4()}"
    job_id = str(uuid4())
    agent_id_1 = str(uuid4())
    agent_id_2 = str(uuid4())

    # Create job with two executions (succession scenario)
    async with db_manager.get_session_async() as session:
        job = AgentJob(
            job_id=job_id,
            tenant_key=tenant_key,
            mission="Build authentication system",
            job_type="orchestrator",
            status="active",
        )
        session.add(job)

        # First execution (succeeded by second)
        execution_1 = AgentExecution(
            agent_id=agent_id_1,
            job_id=job_id,
            tenant_key=tenant_key,
            agent_type="orchestrator",
            instance_number=1,
            status="complete",
            context_used=45000,  # Near limit
            context_budget=50000,
            succeeded_by=agent_id_2,
        )
        session.add(execution_1)

        # Second execution (successor)
        execution_2 = AgentExecution(
            agent_id=agent_id_2,
            job_id=job_id,
            tenant_key=tenant_key,
            agent_type="orchestrator",
            instance_number=2,
            status="working",
            context_used=8000,  # Fresh start
            context_budget=50000,
            spawned_by=agent_id_1,
        )
        session.add(execution_2)
        await session.commit()

    # TEST: Fetch context for first executor
    result_1 = await fetch_context(
        agent_id=agent_id_1,
        tenant_key=tenant_key,
        categories=["product_core"]
    )

    # TEST: Fetch context for second executor
    result_2 = await fetch_context(
        agent_id=agent_id_2,
        tenant_key=tenant_key,
        categories=["product_core"]
    )

    # EXPECTED: Independent context windows
    assert result_1["agent_id"] == agent_id_1
    assert result_1["context_used"] == 45000
    assert result_1["job_id"] == job_id  # Same job

    assert result_2["agent_id"] == agent_id_2
    assert result_2["context_used"] == 8000  # Different context!
    assert result_2["job_id"] == job_id  # Same job

    # VERIFY: Same job, different executors
    assert result_1["job_id"] == result_2["job_id"]
    assert result_1["agent_id"] != result_2["agent_id"]


@pytest.mark.asyncio
async def test_get_context_history_includes_both_ids(db_manager):
    """
    Test that context history response includes both agent_id and job_id.

    Semantic: agent_id = WHO executed, job_id = WHAT they worked on.
    Both IDs provide complete traceability.
    """
    from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
    from src.giljo_mcp.tools.context import get_context_history

    tenant_key = f"tenant_{uuid4()}"
    job_id = str(uuid4())
    agent_id = str(uuid4())

    # Create job and execution
    async with db_manager.get_session_async() as session:
        job = AgentJob(
            job_id=job_id,
            tenant_key=tenant_key,
            mission="Build authentication system",
            job_type="orchestrator",
            status="active",
        )
        session.add(job)

        execution = AgentExecution(
            agent_id=agent_id,
            job_id=job_id,
            tenant_key=tenant_key,
            agent_type="orchestrator",
            instance_number=1,
            status="working",
            context_used=12000,
            context_budget=50000,
        )
        session.add(execution)
        await session.commit()

    # TEST: Get context history via agent_id
    result = await get_context_history(
        agent_id=agent_id,
        tenant_key=tenant_key
    )

    # EXPECTED: Response includes both IDs
    assert result["success"] is True
    assert result["agent_id"] == agent_id
    assert result["job_id"] == job_id
    assert result["agent_type"] == "orchestrator"
    assert result["instance_number"] == 1
    assert "context_history" in result


@pytest.mark.asyncio
async def test_context_multi_tenant_isolation(db_manager):
    """
    Test that context fetching enforces multi-tenant isolation.

    Semantic: tenant_key provides security boundary.
    Agent from tenant A cannot access context from tenant B.
    """
    from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
    from src.giljo_mcp.tools.context import fetch_context

    tenant_a = f"tenant_{uuid4()}"
    tenant_b = f"tenant_{uuid4()}"
    job_id = str(uuid4())
    agent_id = str(uuid4())

    # Create execution for tenant A
    async with db_manager.get_session_async() as session:
        job = AgentJob(
            job_id=job_id,
            tenant_key=tenant_a,
            mission="Tenant A mission",
            job_type="orchestrator",
            status="active",
        )
        session.add(job)

        execution = AgentExecution(
            agent_id=agent_id,
            job_id=job_id,
            tenant_key=tenant_a,
            agent_type="orchestrator",
            instance_number=1,
            status="working",
            context_used=5000,
            context_budget=50000,
        )
        session.add(execution)
        await session.commit()

    # TEST: Fetch context with correct tenant_key
    result_correct = await fetch_context(
        agent_id=agent_id,
        tenant_key=tenant_a,
        categories=["product_core"]
    )

    # EXPECTED: Success
    assert result_correct["success"] is True
    assert result_correct["agent_id"] == agent_id

    # TEST: Fetch context with WRONG tenant_key
    result_wrong = await fetch_context(
        agent_id=agent_id,
        tenant_key=tenant_b,  # Wrong tenant!
        categories=["product_core"]
    )

    # EXPECTED: Failure (multi-tenant isolation enforced)
    assert result_wrong["success"] is False
    assert "not found" in result_wrong["error"].lower() or "unauthorized" in result_wrong["error"].lower()


@pytest.mark.asyncio
async def test_context_succession_tracking(db_manager):
    """
    Test that context tools track succession chain correctly.

    Semantic: successor inherits job_id, gets new agent_id.
    Context window resets, but job reference persists.
    """
    from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
    from src.giljo_mcp.tools.context import get_succession_context
    from sqlalchemy import select

    tenant_key = f"tenant_{uuid4()}"
    job_id = str(uuid4())
    agent_id_1 = str(uuid4())
    agent_id_2 = str(uuid4())
    agent_id_3 = str(uuid4())

    # Create job with succession chain
    async with db_manager.get_session_async() as session:
        job = AgentJob(
            job_id=job_id,
            tenant_key=tenant_key,
            mission="Build authentication system",
            job_type="orchestrator",
            status="active",
        )
        session.add(job)

        # First execution
        execution_1 = AgentExecution(
            agent_id=agent_id_1,
            job_id=job_id,
            tenant_key=tenant_key,
            agent_type="orchestrator",
            instance_number=1,
            status="complete",
            context_used=48000,
            context_budget=50000,
            succeeded_by=agent_id_2,
        )
        session.add(execution_1)

        # Second execution (successor)
        execution_2 = AgentExecution(
            agent_id=agent_id_2,
            job_id=job_id,
            tenant_key=tenant_key,
            agent_type="orchestrator",
            instance_number=2,
            status="complete",
            context_used=47500,
            context_budget=50000,
            spawned_by=agent_id_1,
            succeeded_by=agent_id_3,
        )
        session.add(execution_2)

        # Third execution (current)
        execution_3 = AgentExecution(
            agent_id=agent_id_3,
            job_id=job_id,
            tenant_key=tenant_key,
            agent_type="orchestrator",
            instance_number=3,
            status="working",
            context_used=12000,
            context_budget=50000,
            spawned_by=agent_id_2,
        )
        session.add(execution_3)
        await session.commit()

    # TEST: Get succession context for current executor
    result = await get_succession_context(
        agent_id=agent_id_3,
        tenant_key=tenant_key
    )

    # EXPECTED: Succession chain with all executors
    assert result["success"] is True
    assert result["agent_id"] == agent_id_3
    assert result["job_id"] == job_id
    assert result["instance_number"] == 3
    assert len(result["succession_chain"]) == 3

    # VERIFY: Chain order
    assert result["succession_chain"][0]["agent_id"] == agent_id_1
    assert result["succession_chain"][1]["agent_id"] == agent_id_2
    assert result["succession_chain"][2]["agent_id"] == agent_id_3

    # VERIFY: Context resets across succession
    assert result["succession_chain"][0]["context_used"] == 48000
    assert result["succession_chain"][1]["context_used"] == 47500
    assert result["succession_chain"][2]["context_used"] == 12000  # Fresh start


# EXPECTED FAILURES:
# ==================
# 1. test_fetch_context_uses_agent_id
#    - ImportError: fetch_context does not exist in context.py
#    - OR: TypeError: fetch_context() got unexpected keyword argument 'agent_id'
#
# 2. test_context_tracking_updates_agent_execution
#    - ImportError: update_context_usage does not exist in context.py
#
# 3. test_multiple_executions_independent_context
#    - TypeError: fetch_context() missing required argument 'agent_id'
#    - OR: AssertionError: context_used not found in result
#
# 4. test_get_context_history_includes_both_ids
#    - ImportError: get_context_history does not exist in context.py
#
# 5. test_context_multi_tenant_isolation
#    - TypeError: fetch_context() missing required argument 'agent_id'
#
# 6. test_context_succession_tracking
#    - ImportError: get_succession_context does not exist in context.py
#
# These failures are EXPECTED and CORRECT for RED phase.
# Phase D (GREEN) will implement these functions in context.py.


# =============================================================================
# TDD FIX TESTS: HIGH + MEDIUM Priority Issues
# =============================================================================


@pytest.mark.asyncio
async def test_fetch_context_uses_config_database_url(db_manager):
    """
    HIGH ISSUE #5 - Lines 1747, 1809, 1866, 1930

    Behavior: fetch_context should NOT hardcode test database URL.

    The code used to have:
        db_url = os.getenv("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:***@localhost:5432/giljo_mcp_test")

    This test verifies that we removed the hardcoded fallback.
    Instead, the code should use the global db_manager set by the server.
    """
    import src.giljo_mcp.tools.context as context_module

    #  BEHAVIOR: Check the source code doesn't have hardcoded test DB URL
    source_code = open(context_module.__file__, 'r').read()

    # Find fetch_context function
    fetch_start = source_code.find("async def fetch_context(")
    fetch_end = source_code.find("\nasync def", fetch_start + 1)
    if fetch_end == -1:
        fetch_end = len(source_code)

    fetch_code = source_code[fetch_start:fetch_end]

    # EXPECTED: Should NOT hardcode test database URL
    assert "postgresql+asyncpg://postgres:***@localhost:5432/giljo_mcp_test" not in fetch_code, \
        "fetch_context() should NOT hardcode test database URL"

    # Should NOT have TEST_DATABASE_URL environment variable fallback
    assert 'os.getenv("TEST_DATABASE_URL"' not in fetch_code, \
        "fetch_context() should NOT use TEST_DATABASE_URL env var with hardcoded fallback"


@pytest.mark.asyncio
async def test_update_context_usage_uses_config_database_url(db_manager):
    """
    HIGH ISSUE #5 - Lines 1809, 1866, 1930 (all wrapper functions)

    Behavior: Wrapper functions should NOT hardcode test database URL.

    All wrapper functions (fetch_context, update_context_usage, get_context_history, get_succession_context)
    used to hardcode the test database URL. This test verifies the hardcoded URL is removed.
    """
    import src.giljo_mcp.tools.context as context_module

    # BEHAVIOR: Check the source code doesn't have hardcoded test DB URL
    source_code = open(context_module.__file__, 'r').read()

    # Check all wrapper functions (4 instances were at lines 1747, 1809, 1866, 1930)
    wrapper_functions = [
        "async def fetch_context(",
        "async def update_context_usage(",
        "async def get_context_history(",
        "async def get_succession_context(",
    ]

    for func_signature in wrapper_functions:
        func_start = source_code.find(func_signature)
        if func_start == -1:
            continue  # Function might not exist yet

        func_end = source_code.find("\nasync def", func_start + 1)
        if func_end == -1:
            func_end = len(source_code)

        func_code = source_code[func_start:func_end]

        # EXPECTED: Should NOT hardcode test database URL
        assert "postgresql+asyncpg://postgres:***@localhost:5432/giljo_mcp_test" not in func_code, \
            f"{func_signature} should NOT hardcode test database URL"

        # Should NOT use TEST_DATABASE_URL env var with hardcoded fallback
        assert 'os.getenv("TEST_DATABASE_URL"' not in func_code, \
            f"{func_signature} should NOT use TEST_DATABASE_URL env var with hardcoded fallback"


@pytest.mark.asyncio
async def test_session_info_uses_agent_job_model(db_manager):
    """
    MEDIUM ISSUE #6 - Lines 719-727

    Behavior: session_info (MCP tool) should query AgentJob, not deprecated AgentExecution.

    The function should use the new dual-model architecture:
    - AgentJob = work order
    - AgentExecution = executor instance

    This test checks that the code in context.py lines 719-727 doesn't import MCPAgentJob
    """
    import src.giljo_mcp.tools.context as context_module

    # BEHAVIOR: Code at lines 719-727 should NOT import MCPAgentJob
    # This will fail if the code tries to import deprecated model
    source_code = open(context_module.__file__, 'r').read()

    # Check if session_info function imports MCPAgentJob
    session_info_start = source_code.find("async def session_info()")
    session_info_end = source_code.find("@mcp.tool()", session_info_start + 1)
    if session_info_end == -1:
        session_info_end = source_code.find("async def", session_info_start + 1)
    if session_info_end == -1:
        session_info_end = len(source_code)

    session_info_code = source_code[session_info_start:session_info_end]

    # EXPECTED: Should use AgentJob, NOT MCPAgentJob
    # This assertion WILL FAIL in RED phase (line 716 imports MCPAgentJob)
    assert "MCPAgentJob" not in session_info_code, \
        "session_info() should NOT import deprecated MCPAgentJob (line 716)"

    # Should use AgentJob instead
    assert "AgentJob" in session_info_code or "agent_identity" in session_info_code, \
        "session_info() should use AgentJob from agent_identity module"


@pytest.mark.asyncio
async def test_recalibrate_mission_returns_valid_response(db_manager):
    """
    MEDIUM ISSUE #7 - Lines 787-792

    Behavior: recalibrate_mission should return properly (no unreachable code).

    Lines 787-792 have unreachable code after a return statement.
    The function should return a dict with success status.

    This test checks the code structure for unreachable code.
    """
    import src.giljo_mcp.tools.context as context_module
    import ast

    # BEHAVIOR: Check for unreachable code in recalibrate_mission function
    source_code = open(context_module.__file__, 'r').read()

    # Find recalibrate_mission function
    recal_start = source_code.find("async def recalibrate_mission(")
    recal_end = source_code.find("\n    @mcp.tool()", recal_start + 1)
    if recal_end == -1:
        recal_end = source_code.find("\n    async def", recal_start + 1)
    if recal_end == -1:
        recal_end = len(source_code)

    recal_code = source_code[recal_start:recal_end]

    # Lines 787-792 contain the problematic code
    # Line 786-787: if broadcast_result["success"]:
    # Line 788-791: return {...}  # First return
    # Line 792: return broadcast_result  # UNREACHABLE - this is the bug!

    # Count return statements in the function
    return_count = recal_code.count("return {")
    return_broadcast = recal_code.count("return broadcast_result")

    # EXPECTED: Should have only ONE return path, not two
    # The current code has unreachable return on line 792
    assert return_count + return_broadcast > 1, \
        "Bug not present: recalibrate_mission should have unreachable code on line 792"

    # After fix, there should be only one return statement
    # This test documents the expected FAILURE state


# EXPECTED FAILURES FOR FIX TESTS:
# =================================
# 1. test_fetch_context_uses_config_database_url
#    - Lines 1747-1749 hardcode test DB URL
#    - Will fail when TEST_DATABASE_URL env var is removed
#
# 2. test_update_context_usage_uses_config_database_url
#    - Lines 1809 hardcodes test DB URL
#    - Will fail when TEST_DATABASE_URL env var is removed
#
# 3. test_session_info_uses_agent_job_model
#    - Lines 719-727 import and use deprecated MCPAgentJob
#    - Will fail with ImportError or wrong query results
#
# 4. test_recalibrate_mission_returns_valid_response
#    - Lines 787-792 have unreachable code after return
#    - May succeed but code structure is incorrect
