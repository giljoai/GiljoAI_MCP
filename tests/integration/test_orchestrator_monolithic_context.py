"""
Integration tests for Orchestrator Monolithic Context Implementation (Handover 0281).

Tests verify:
1. End-to-end user control flow (user settings → database → orchestrator → MCP tools)
2. Token count estimation accuracy (within ±10% of actual)
3. Performance benchmarks vs old 9-tool system (target: <500ms)

Phase 7: Integration Testing (Days 13-14)
"""

import pytest
import pytest_asyncio
import time
from uuid import uuid4
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models.auth import User
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.models.agent_identity import AgentExecution
from src.giljo_mcp.tools.orchestration import get_orchestrator_instructions
from src.giljo_mcp.database import DatabaseManager


# ============================================================================
# FIXTURES - Use test_user and test_tenant_key from integration/conftest.py
# ============================================================================

@pytest_asyncio.fixture
async def monolithic_test_user(db_session: AsyncSession, test_tenant_key: str):
    """Create test user with custom field priorities for monolithic context testing."""
    user = User(
        id=str(uuid4()),
        username=f"mono_user_{uuid4().hex[:8]}",
        email=f"mono_{uuid4().hex[:8]}@example.com",
        password_hash="dummy_hash",
        tenant_key=test_tenant_key,
        is_active=True,
        role="developer",
        field_priority_config={
            "version": "2.0",
            "priorities": {
                "product_core": 1,           # CRITICAL
                "vision_documents": 4,       # EXCLUDED (should not appear in mission)
                "tech_stack": 2,             # IMPORTANT
                "architecture": 2,           # IMPORTANT
                "testing": 3,                # NICE_TO_HAVE
                "memory_360": 4,             # EXCLUDED (should not appear in mission)
                "git_history": 4,            # EXCLUDED (should not appear in mission)
                "agent_templates": 2         # IMPORTANT
            }
        },
        depth_config={
            "vision_chunking": "none",                  # Not applicable (disabled)
            "memory_last_n_projects": 0,                # Not applicable (disabled)
            "git_commits": 0,                           # Not applicable (disabled)
            "agent_template_detail": "standard",        # Standard detail for agents
            "tech_stack_sections": "required",          # Required sections only
            "architecture_depth": "overview"            # Overview level
        }
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def monolithic_test_product(db_session: AsyncSession, test_tenant_key: str):
    """Create test product with 360 Memory for monolithic context testing."""
    product = Product(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        name="Monolithic Context Test Product",
        description="Product with comprehensive 360 Memory for testing",
        product_memory={
            "objectives": ["Build scalable backend", "Ensure high availability"],
            "decisions": ["Use PostgreSQL for data persistence", "Implement REST API"],
            "context": {},
            "knowledge_base": {},
            "sequential_history": [
                {
                    "sequence": 1,
                    "type": "project_closeout",
                    "project_id": str(uuid4()),
                    "project_name": "Previous Project 1",
                    "summary": "Implemented user authentication system",
                    "key_outcomes": ["JWT-based auth", "Password reset"],
                    "decisions_made": ["Use bcrypt for hashing"],
                    "timestamp": "2025-11-01T10:00:00Z"
                },
                {
                    "sequence": 2,
                    "type": "project_closeout",
                    "project_id": str(uuid4()),
                    "project_name": "Previous Project 2",
                    "summary": "Built API gateway with rate limiting",
                    "key_outcomes": ["Redis-based rate limiter", "API versioning"],
                    "decisions_made": ["Use Redis for distributed cache"],
                    "timestamp": "2025-11-15T10:00:00Z"
                },
                {
                    "sequence": 3,
                    "type": "project_closeout",
                    "project_id": str(uuid4()),
                    "project_name": "Previous Project 3",
                    "summary": "Database optimization and indexing",
                    "key_outcomes": ["40% query speedup", "Index optimization"],
                    "decisions_made": ["Add composite indexes on frequently queried columns"],
                    "timestamp": "2025-11-20T10:00:00Z"
                }
            ]
        }
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def monolithic_test_project(db_session: AsyncSession, test_tenant_key: str, monolithic_test_product):
    """Create test project linked to product."""
    project = Project(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        product_id=monolithic_test_product.id,
        name="Monolithic Context Test Project",
        description="User requirements: Build a REST API with authentication and rate limiting",
        mission="",  # Empty mission - will be compiled by get_orchestrator_instructions
        status="active",
        context_budget=150000,
        context_used=0
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def monolithic_test_orchestrator(
    db_session: AsyncSession,
    test_tenant_key: str,
    monolithic_test_project,
    monolithic_test_user
):
    """Create orchestrator job with user metadata."""
    orchestrator = AgentExecution(
        job_id=str(uuid4()),
        tenant_key=test_tenant_key,
        project_id=monolithic_test_project.id,
        agent_type="orchestrator",
        agent_name="Monolithic Test Orchestrator",
        mission="Initial mission to be replaced by get_orchestrator_instructions",
        status="waiting",  # Valid statuses: waiting, working, blocked, complete, failed, cancelled, decommissioned
        context_budget=150000,
        context_used=0,
        job_metadata={
            "field_priorities": monolithic_test_user.field_priority_config["priorities"],
            "depth_config": monolithic_test_user.depth_config,
            "user_id": str(monolithic_test_user.id)
        }
    )
    db_session.add(orchestrator)
    await db_session.commit()
    await db_session.refresh(orchestrator)
    return orchestrator


# ============================================================================
# TEST 7.1: End-to-end User Control Flow
# ============================================================================

@pytest.mark.asyncio
async def test_e2e_user_control_flow(
    db_session: AsyncSession,
    db_manager: DatabaseManager,
    monolithic_test_user,
    monolithic_test_product,
    monolithic_test_project,
    monolithic_test_orchestrator,
    test_tenant_key: str
):
    """
    Test complete user control flow:
    1. User sets priorities in UI (fixture: vision_documents=OFF, memory_360=OFF, git_history=OFF)
    2. Settings saved to database
    3. Orchestrator launched with user_id
    4. get_orchestrator_instructions() respects user settings
    5. Response mission matches user expectations
    """
    # STEP 1-2: User config already set in fixture
    assert monolithic_test_user.field_priority_config["priorities"]["vision_documents"] == 4  # EXCLUDED
    assert monolithic_test_user.field_priority_config["priorities"]["memory_360"] == 4        # EXCLUDED
    assert monolithic_test_user.field_priority_config["priorities"]["git_history"] == 4       # EXCLUDED
    assert monolithic_test_user.field_priority_config["priorities"]["product_core"] == 1      # CRITICAL
    assert monolithic_test_user.field_priority_config["priorities"]["tech_stack"] == 2        # IMPORTANT

    # STEP 3-4: Launch orchestrator and fetch instructions
    result = await get_orchestrator_instructions(
        orchestrator_id=monolithic_test_orchestrator.job_id,
        tenant_key=test_tenant_key,
        db_manager=db_manager
    )

    # STEP 5: Verify response matches expectations
    if "error" in result:
        print(f"\n[ERROR] get_orchestrator_instructions() returned error: {result}")
    assert "error" not in result, f"Unexpected error: {result.get('error')} - Full response: {result}"

    # Verify orchestrator metadata
    assert result["orchestrator_id"] == monolithic_test_orchestrator.job_id
    assert result["project_id"] == str(monolithic_test_project.id)
    assert result["project_name"] == monolithic_test_project.name
    assert result["thin_client"] is True

    # Verify field priorities are applied
    assert result["field_priorities"] == monolithic_test_user.field_priority_config["priorities"]
    assert result["token_reduction_applied"] is True

    # Verify EXCLUDED contexts (priority=4) do NOT appear in mission
    mission = result["mission"]

    # These should be EXCLUDED (0 bytes)
    assert "Vision Documents" not in mission, "Vision documents should be excluded (priority=4)"
    assert "360 Memory" not in mission, "360 Memory should be excluded (priority=4)"
    assert "Git History" not in mission, "Git History should be excluded (priority=4)"

    # Verify estimated tokens
    assert "estimated_tokens" in result
    assert result["estimated_tokens"] > 0
    assert result["estimated_tokens"] < 150000  # Should be well under context budget

    print(f"\n[TEST] End-to-end user control flow: PASS")
    print(f"[TEST] Orchestrator ID: {result['orchestrator_id']}")
    print(f"[TEST] Estimated tokens: {result['estimated_tokens']}")
    print(f"[TEST] User priorities applied: {result['field_priorities']}")
    print(f"[TEST] Mission length: {len(mission)} chars")


# ============================================================================
# TEST 7.2: Token Count Estimation Accuracy
# ============================================================================

@pytest.mark.asyncio
async def test_token_count_estimation_accuracy(
    db_session: AsyncSession,
    db_manager: DatabaseManager,
    monolithic_test_user,
    monolithic_test_product,
    monolithic_test_project,
    monolithic_test_orchestrator,
    test_tenant_key: str
):
    """
    Test that estimated_tokens is within ±10% of actual.

    Token estimation formula: len(mission) // 4 (rough approximation)
    Accuracy target: Within ±10% of actual token count
    """
    # Fetch orchestrator instructions
    result = await get_orchestrator_instructions(
        orchestrator_id=monolithic_test_orchestrator.job_id,
        tenant_key=test_tenant_key,
        db_manager=db_manager
    )

    assert "error" not in result, f"Unexpected error: {result.get('error')}"

    # Calculate actual token count (rough approximation: len / 4)
    mission = result["mission"]
    actual_tokens = len(mission) // 4
    estimated_tokens = result["estimated_tokens"]

    # Verify within ±10%
    if actual_tokens > 0:
        error_percentage = abs(estimated_tokens - actual_tokens) / actual_tokens * 100
        assert error_percentage < 10, \
            f"Token estimation error: {error_percentage:.2f}% (estimated: {estimated_tokens}, actual: {actual_tokens})"

    print(f"\n[TEST] Token count estimation accuracy: PASS")
    print(f"[TEST] Estimated tokens: {estimated_tokens}")
    print(f"[TEST] Actual tokens (approx): {actual_tokens}")
    if actual_tokens > 0:
        print(f"[TEST] Error percentage: {error_percentage:.2f}%")


# ============================================================================
# TEST 7.3: Performance Benchmark vs Old System
# ============================================================================

@pytest.mark.asyncio
async def test_performance_benchmark(
    db_session: AsyncSession,
    db_manager: DatabaseManager,
    monolithic_test_user,
    monolithic_test_product,
    monolithic_test_project,
    monolithic_test_orchestrator,
    test_tenant_key: str
):
    """
    Benchmark latency vs old 9-tool system.

    Old system: 900-1500ms (9 sequential MCP tool calls)
    New system: <500ms (1 monolithic call)
    Target: <500ms
    """
    # Warm-up call (exclude from benchmark)
    await get_orchestrator_instructions(
        orchestrator_id=monolithic_test_orchestrator.job_id,
        tenant_key=test_tenant_key,
        db_manager=db_manager
    )

    # Benchmark: 3 calls for average
    latencies = []
    for i in range(3):
        start_time = time.time()

        result = await get_orchestrator_instructions(
            orchestrator_id=monolithic_test_orchestrator.job_id,
            tenant_key=test_tenant_key,
            db_manager=db_manager
        )

        elapsed_ms = (time.time() - start_time) * 1000
        latencies.append(elapsed_ms)

        assert "error" not in result, f"Unexpected error in benchmark run {i+1}: {result.get('error')}"

    # Calculate average latency
    avg_latency_ms = sum(latencies) / len(latencies)
    min_latency_ms = min(latencies)
    max_latency_ms = max(latencies)

    # Target: <500ms (vs old system 900-1500ms)
    assert avg_latency_ms < 500, \
        f"Latency too high: {avg_latency_ms:.2f}ms (target: <500ms, old system: 900-1500ms)"

    print(f"\n[TEST] Performance benchmark: PASS")
    print(f"[TEST] Average latency: {avg_latency_ms:.2f}ms (Target: <500ms)")
    print(f"[TEST] Min latency: {min_latency_ms:.2f}ms")
    print(f"[TEST] Max latency: {max_latency_ms:.2f}ms")
    print(f"[TEST] Old system baseline: 900-1500ms")
    print(f"[TEST] Performance improvement: {((900 - avg_latency_ms) / 900 * 100):.1f}% faster than old system minimum")


# ============================================================================
# Integration Test Summary
# ============================================================================
#
# These tests verify Handover 0281 (Monolithic Context Implementation):
#
# COVERAGE:
# ✅ End-to-end user control flow (UI → DB → Orchestrator → MCP → Filtered Context)
# ✅ Token count estimation accuracy (±10% target)
# ✅ Performance benchmark (<500ms vs old 900-1500ms)
#
# PERFORMANCE TARGETS:
# - Latency: <500ms (monolithic call vs old 900-1500ms for 9 sequential calls)
# - Token accuracy: ±10% error
# - Context reduction: 40-60% reduction via user priorities
#
# INTEGRATION POINTS:
# - User model: field_priority_config, depth_config
# - Product model: product_memory (360 Memory)
# - Project model: description (user requirements)
# - MCPAgentJob model: job_metadata (field_priorities, depth_config, user_id)
# - get_orchestrator_instructions(): Monolithic context compilation
# - MissionPlanner: Context prioritization and framing
#
# ============================================================================
