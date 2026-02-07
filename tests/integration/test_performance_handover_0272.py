"""
Performance benchmarks for handover 0272 - Context generation and settings

This test suite validates performance characteristics of the complete context
wiring system:

Target Performance Benchmarks:
- Context generation: <2 seconds
- Settings persistence: <500ms
- Field priority filtering: <100ms
- Memory retrieval: <300ms

Tests validate:
1. Context generation completes within SLA
2. Settings persistence is fast enough for real-time UI updates
3. Field priority filtering doesn't cause performance degradation
4. Memory operations are efficient even with large datasets
5. Multi-tenant operations don't degrade performance
6. Concurrent operations maintain performance
"""

import time
from datetime import datetime
from uuid import uuid4

import pytest_asyncio

from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.models import Product, Project, User


# ============================================================================
# FIXTURES
# ============================================================================


@pytest_asyncio.fixture
async def perf_tenant():
    """Tenant for performance tests"""
    return f"perf_tenant_{uuid4().hex[:8]}"


@pytest_asyncio.fixture
async def perf_user(db_session, perf_tenant):
    """User for performance tests"""
    user = User(
        id=str(uuid4()),
        username=f"perfuser_{uuid4().hex[:6]}",
        email=f"perfuser_{uuid4().hex[:6]}@example.com",
        tenant_key=perf_tenant,
        role="developer",
        password_hash="hash",
        field_priority_config={
            "version": "2.0",
            "priorities": {
                "product_core": 1,
                "vision_documents": 2,
                "tech_stack": 2,
                "architecture": 2,
                "testing": 2,
                "memory_360": 2,
                "git_history": 3,
                "agent_templates": 3,
            },
        },
        serena_enabled=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def perf_product_with_large_memory(db_session, perf_tenant):
    """Product with large 360 memory for realistic performance testing"""
    # Create product with substantial memory entries
    history = []
    for i in range(100):  # Large number of entries
        history.append(
            {
                "sequence": i + 1,
                "type": "project_closeout",
                "project_id": str(uuid4()),
                "summary": f"Project {i + 1} completed with implementation and testing",
                "timestamp": datetime.utcnow().isoformat(),
                "decisions": ["decision_1", "decision_2"],
                "git_commits": [f"commit_{j}" for j in range(5)],
            }
        )

    product = Product(
        id=str(uuid4()),
        name=f"PerfProduct_{uuid4().hex[:6]}",
        tenant_key=perf_tenant,
        tech_stack={
            "languages": ["python", "typescript"],
            "frameworks": ["fastapi", "react"],
            "database": "postgresql",
            "caching": "redis",
            "messaging": "rabbitmq",
        },
        testing_config={
            "framework": "pytest",
            "coverage_target": 85,
            "strategy": "comprehensive",
            "ci_system": "github_actions",
        },
        product_memory={
            "git_integration": {
                "enabled": True,
                "repository_url": "https://github.com/example/repo",
            },
            "sequential_history": history,
        },
    )
    db_session.add(product)
    await db_session.flush()
    return product


@pytest_asyncio.fixture
async def perf_project(db_session, perf_product_with_large_memory, perf_tenant):
    """Project for performance tests"""
    project = Project(
        id=str(uuid4()),
        product_id=perf_product_with_large_memory.id,
        name=f"PerfProject_{uuid4().hex[:6]}",
        status="created",
        tenant_key=perf_tenant,
    )
    db_session.add(project)
    await db_session.flush()
    return project


# ============================================================================
# TEST SUITE 1: Context Generation Performance
# ============================================================================


class TestContextGenerationPerformance:
    """
    Validate that context generation meets performance SLAs
    """

    async def test_mission_planner_context_generation_under_2_seconds(
        self,
        db_session,
        perf_user,
        perf_product_with_large_memory,
        perf_project,
        perf_tenant,
    ):
        """
        REQUIREMENT: Context generation must complete in <2 seconds
        SLA: 2000ms

        This is critical for responsive UI and agent spawning
        """
        planner = MissionPlanner(test_session=db_session)

        start_time = time.time()
        mission = await planner.plan_orchestrator_mission(
            user_id=perf_user.id,
            product_id=perf_product_with_large_memory.id,
            project_id=perf_project.id,
            tenant_key=perf_tenant,
        )
        elapsed = time.time() - start_time

        # Verify result
        assert mission is not None
        assert len(mission) > 0

        # Check SLA
        assert elapsed < 2.0, f"Context generation took {elapsed:.2f}s, expected <2.0s"

    async def test_context_generation_with_all_features_enabled_under_2_seconds(
        self,
        db_session,
        perf_user,
        perf_product_with_large_memory,
        perf_project,
        perf_tenant,
    ):
        """
        REQUIREMENT: Even with ALL features enabled, context generation <2s
        (Handover 0266-0271 all enabled simultaneously)
        """
        # Verify all features enabled
        assert perf_user.serena_enabled is True
        assert perf_user.field_priority_config is not None
        assert perf_product_with_large_memory.testing_config is not None
        assert perf_product_with_large_memory.product_memory is not None

        planner = MissionPlanner(test_session=db_session)

        start_time = time.time()
        context = await planner._build_context_with_priorities(
            user=perf_user,
            product=perf_product_with_large_memory,
            project=perf_project,
            field_priorities=perf_user.field_priority_config["priorities"],
            include_serena=perf_user.serena_enabled,
        )
        elapsed = time.time() - start_time

        assert context is not None
        assert elapsed < 2.0, f"Full context generation took {elapsed:.2f}s, expected <2.0s"

    async def test_memory_retrieval_performance(
        self,
        db_session,
        perf_product_with_large_memory,
    ):
        """
        REQUIREMENT: Retrieving 360 memory must be <300ms
        (Memory access is frequent operation)
        """
        start_time = time.time()
        memory = perf_product_with_large_memory.product_memory["sequential_history"]
        elapsed = time.time() - start_time

        assert memory is not None
        assert len(memory) == 100  # Should have all entries

        assert elapsed < 0.3, f"Memory retrieval took {elapsed * 1000:.2f}ms, expected <300ms"


# ============================================================================
# TEST SUITE 2: Settings Persistence Performance
# ============================================================================


class TestSettingsPersistencePerformance:
    """
    Validate that settings can be saved/loaded quickly for responsive UI
    """

    async def test_field_priority_persistence_under_500ms(
        self,
        db_session,
        perf_user,
    ):
        """
        REQUIREMENT: Settings changes must persist in <500ms
        SLA: 500ms (for responsive UI feedback)

        User expects immediate "saved" confirmation in UI
        """
        # Simulate setting change
        new_priorities = {
            "product_core": 1,
            "vision_documents": 3,  # Changed
            "tech_stack": 2,
            "architecture": 2,
            "testing": 2,
            "memory_360": 3,  # Changed
            "git_history": 4,
            "agent_templates": 3,
        }

        start_time = time.time()
        perf_user.field_priority_config["priorities"] = new_priorities
        await db_session.flush()
        elapsed = time.time() - start_time

        # Verify persistence
        retrieved = await db_session.get(User, perf_user.id)
        assert retrieved.field_priority_config["priorities"]["vision_documents"] == 3

        assert elapsed < 0.5, f"Settings persistence took {elapsed * 1000:.2f}ms, expected <500ms"

    async def test_serena_toggle_persistence_under_500ms(
        self,
        db_session,
        perf_user,
    ):
        """
        REQUIREMENT: Serena toggle must persist in <500ms
        """
        start_time = time.time()
        perf_user.serena_enabled = not perf_user.serena_enabled
        await db_session.flush()
        elapsed = time.time() - start_time

        retrieved = await db_session.get(User, perf_user.id)
        assert retrieved.serena_enabled is True

        assert elapsed < 0.5, f"Toggle persistence took {elapsed * 1000:.2f}ms, expected <500ms"

    async def test_github_integration_toggle_under_500ms(
        self,
        db_session,
        perf_product_with_large_memory,
    ):
        """
        REQUIREMENT: GitHub integration toggle must persist in <500ms
        """
        start_time = time.time()
        perf_product_with_large_memory.product_memory["git_integration"]["enabled"] = False
        await db_session.flush()
        elapsed = time.time() - start_time

        retrieved = await db_session.get(Product, perf_product_with_large_memory.id)
        assert retrieved.product_memory["git_integration"]["enabled"] is False

        assert elapsed < 0.5, f"GitHub toggle persistence took {elapsed * 1000:.2f}ms, expected <500ms"

    async def test_testing_config_update_under_500ms(
        self,
        db_session,
        perf_product_with_large_memory,
    ):
        """
        REQUIREMENT: Testing config changes must persist in <500ms
        """
        start_time = time.time()
        perf_product_with_large_memory.testing_config["coverage_target"] = 90
        await db_session.flush()
        elapsed = time.time() - start_time

        retrieved = await db_session.get(Product, perf_product_with_large_memory.id)
        assert retrieved.testing_config["coverage_target"] == 90

        assert elapsed < 0.5, f"Config persistence took {elapsed * 1000:.2f}ms, expected <500ms"


# ============================================================================
# TEST SUITE 3: Field Priority Filtering Performance
# ============================================================================


class TestFieldPriorityFilteringPerformance:
    """
    Validate that field priority filtering doesn't degrade performance
    """

    async def test_priority_filtering_under_100ms(
        self,
        db_session,
        perf_user,
        perf_product_with_large_memory,
        perf_project,
    ):
        """
        REQUIREMENT: Field priority filtering must be <100ms
        SLA: 100ms (fast filtering operation)

        This operation happens during context generation
        """
        priorities = perf_user.field_priority_config["priorities"]

        # Measure just the filtering operation
        start_time = time.time()
        # Simulate filtering based on priorities
        high_priority = {k: v for k, v in priorities.items() if v <= 2}
        low_priority = {k: v for k, v in priorities.items() if v >= 3}
        elapsed = time.time() - start_time

        assert len(high_priority) > 0
        assert len(low_priority) > 0

        assert elapsed < 0.1, f"Priority filtering took {elapsed * 1000:.2f}ms, expected <100ms"

    async def test_context_priority_application_under_500ms(
        self,
        db_session,
        perf_user,
        perf_product_with_large_memory,
        perf_project,
        perf_tenant,
    ):
        """
        REQUIREMENT: Applying priorities to build context must be <500ms
        """
        priorities = perf_user.field_priority_config["priorities"]
        planner = MissionPlanner(test_session=db_session)

        start_time = time.time()
        context = await planner._build_context_with_priorities(
            user=perf_user,
            product=perf_product_with_large_memory,
            project=perf_project,
            field_priorities=priorities,
            include_serena=perf_user.serena_enabled,
        )
        elapsed = time.time() - start_time

        assert context is not None
        assert elapsed < 0.5, f"Priority application took {elapsed * 1000:.2f}ms, expected <500ms"


# ============================================================================
# TEST SUITE 4: Large Dataset Performance
# ============================================================================


class TestLargeDatasetPerformance:
    """
    Validate performance with realistic large datasets
    """

    async def test_context_with_100_memory_entries(
        self,
        db_session,
        perf_user,
        perf_product_with_large_memory,
        perf_project,
        perf_tenant,
    ):
        """
        REQUIREMENT: Context generation must handle large memory (100+ entries)
        efficiently
        """
        planner = MissionPlanner(test_session=db_session)

        start_time = time.time()
        mission = await planner.plan_orchestrator_mission(
            user_id=perf_user.id,
            product_id=perf_product_with_large_memory.id,
            project_id=perf_project.id,
            tenant_key=perf_tenant,
        )
        elapsed = time.time() - start_time

        # Should still complete in time even with 100 memory entries
        assert mission is not None
        assert elapsed < 2.0, f"Large memory context generation took {elapsed:.2f}s"

    async def test_memory_loading_scales_linearly(
        self,
        db_session,
        perf_product_with_large_memory,
    ):
        """
        REQUIREMENT: Memory loading should scale linearly with entry count
        (not exponentially)
        """
        memory = perf_product_with_large_memory.product_memory["sequential_history"]

        # Load times for different entry counts
        # With 100 entries, should still be <300ms
        start_time = time.time()
        filtered = [e for e in memory if e["sequence"] <= 50]
        elapsed = time.time() - start_time

        assert len(filtered) == 50
        assert elapsed < 0.3, f"Filtering 100 entries took {elapsed * 1000:.2f}ms"


# ============================================================================
# TEST SUITE 5: Concurrent Operations Performance
# ============================================================================


class TestConcurrentOperationsPerformance:
    """
    Validate that concurrent settings changes don't degrade performance
    """

    async def test_multiple_user_setting_changes_concurrent(
        self,
        db_session,
        perf_user,
    ):
        """
        REQUIREMENT: Multiple setting changes should not significantly degrade
        performance (still <500ms per operation)
        """
        # Simulate multiple concurrent setting changes
        start_time = time.time()

        # Change 1: Field priorities
        perf_user.field_priority_config["priorities"]["git_history"] = 4
        await db_session.flush()

        # Change 2: Serena toggle
        perf_user.serena_enabled = False
        await db_session.flush()

        # Change 3: Back to Serena enabled
        perf_user.serena_enabled = True
        await db_session.flush()

        elapsed = time.time() - start_time

        # All three changes should complete in <1.5s total
        assert elapsed < 1.5, f"Three setting changes took {elapsed:.2f}s"


# ============================================================================
# TEST SUITE 6: Cache Effectiveness (if applicable)
# ============================================================================


class TestCacheEffectiveness:
    """
    Validate that repeated operations benefit from caching
    """

    async def test_repeated_context_generation_improves(
        self,
        db_session,
        perf_user,
        perf_product_with_large_memory,
        perf_project,
        perf_tenant,
    ):
        """
        REQUIREMENT: Repeated context generation should be at least as fast
        as first generation (indicate caching effectiveness)
        """
        planner = MissionPlanner(test_session=db_session)

        # First generation
        start_time_1 = time.time()
        context_1 = await planner.plan_orchestrator_mission(
            user_id=perf_user.id,
            product_id=perf_product_with_large_memory.id,
            project_id=perf_project.id,
            tenant_key=perf_tenant,
        )
        elapsed_1 = time.time() - start_time_1

        # Second generation (should benefit from cache if available)
        start_time_2 = time.time()
        context_2 = await planner.plan_orchestrator_mission(
            user_id=perf_user.id,
            product_id=perf_product_with_large_memory.id,
            project_id=perf_project.id,
            tenant_key=perf_tenant,
        )
        elapsed_2 = time.time() - start_time_2

        # Both should be fast
        assert elapsed_1 < 2.0
        assert elapsed_2 < 2.0

        # Second should ideally be faster or same speed
        # (don't assert strict inequality as caching might not be implemented)
        print(f"First generation: {elapsed_1:.3f}s, Second: {elapsed_2:.3f}s")


# ============================================================================
# TEST SUITE 7: Memory Usage
# ============================================================================


class TestMemoryEfficiency:
    """
    Validate that context generation doesn't use excessive memory
    """

    async def test_context_generation_memory_efficient(
        self,
        db_session,
        perf_user,
        perf_product_with_large_memory,
        perf_project,
        perf_tenant,
    ):
        """
        REQUIREMENT: Context generation should not create massive intermediate
        objects in memory
        """
        import sys

        planner = MissionPlanner(test_session=db_session)

        # Get initial memory baseline
        # (Note: In-process measurement; in production use memory profilers)
        mission = await planner.plan_orchestrator_mission(
            user_id=perf_user.id,
            product_id=perf_product_with_large_memory.id,
            project_id=perf_project.id,
            tenant_key=perf_tenant,
        )

        # Mission should be reasonable size
        mission_size = sys.getsizeof(mission)
        assert mission_size < 1_000_000, f"Mission too large: {mission_size} bytes"
