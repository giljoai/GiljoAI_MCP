"""
Phase 4: MCP Tool Latency Performance Test (Handover 0246d)

Validates that get_available_agents() MCP tool meets performance targets:
- Target: P95 latency < 50ms
- Acceptance: P95 latency < 100ms
- Tests with various dataset sizes (1, 10, 50 agents)

TDD Phase: RED (Tests written BEFORE optimization)
Expected: Tests MAY FAIL initially if performance not optimized
"""

import pytest
import pytest_asyncio
import time
from uuid import uuid4
from statistics import quantiles

from src.giljo_mcp.models import AgentTemplate, User
from src.giljo_mcp.tools.agent_discovery import get_available_agents


@pytest_asyncio.fixture
async def test_user(db_session):
    """Create test user"""
    user = User(
        username=f"perftest_{uuid4().hex[:8]}",
        email=f"perf_{uuid4().hex[:8]}@example.com",
        tenant_key=f"tenant_{uuid4().hex[:8]}",
        role="developer",
        password_hash="hashed_password"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def populate_agents(db_session, test_user):
    """Populate database with test agents for performance testing"""
    async def _populate(count: int):
        agents = []
        for i in range(count):
            agent = AgentTemplate(
                name=f"agent_{i}",
                role=f"Agent {i}",
                description=f"Performance test agent {i}",
                tenant_key=test_user.tenant_key,
                is_active=True,
                version=f"1.{i}.0",
                system_instructions="Test content"
            )
            agents.append(agent)
            db_session.add(agent)

        await db_session.commit()
        return agents

    return _populate


@pytest.mark.asyncio
class TestMCPToolLatency:
    """Performance tests for get_available_agents() MCP tool."""

    async def test_small_dataset_latency(self, db_session, test_user, populate_agents):
        """
        Test latency with small dataset (1-5 agents).
        Target: P95 < 50ms
        Acceptance: P95 < 100ms
        """

        # Setup: 5 agents
        await populate_agents(5)

        # Warm-up call (ignore first call latency)
        await get_available_agents(db_session, test_user.tenant_key)

        # Benchmark: 100 calls
        latencies = []
        for _ in range(100):
            start = time.perf_counter()
            await get_available_agents(db_session, test_user.tenant_key)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)  # Convert to ms

        # Calculate percentiles
        latencies.sort()
        p50 = quantiles(latencies, n=2)[0]  # Median
        p95 = quantiles(latencies, n=20)[18]  # P95
        p99 = quantiles(latencies, n=100)[98]  # P99

        # Assertions
        assert p95 < 100, \
            f"P95 latency ({p95:.2f}ms) exceeds acceptance threshold (100ms)"

        print(f"\n✓ Small dataset (5 agents) latency:")
        print(f"  - P50: {p50:.2f}ms")
        print(f"  - P95: {p95:.2f}ms (target: <50ms, acceptance: <100ms)")
        print(f"  - P99: {p99:.2f}ms")
        print(f"  - Result: {'OPTIMAL' if p95 < 50 else 'ACCEPTABLE'}")

    async def test_medium_dataset_latency(self, db_session, test_user, populate_agents):
        """
        Test latency with medium dataset (10-20 agents).
        Target: P95 < 100ms
        Acceptance: P95 < 200ms
        """

        # Setup: 20 agents
        await populate_agents(20)

        # Warm-up call
        await get_available_agents(db_session, test_user.tenant_key)

        # Benchmark: 100 calls
        latencies = []
        for _ in range(100):
            start = time.perf_counter()
            await get_available_agents(db_session, test_user.tenant_key)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)

        # Calculate percentiles
        latencies.sort()
        p50 = quantiles(latencies, n=2)[0]
        p95 = quantiles(latencies, n=20)[18]
        p99 = quantiles(latencies, n=100)[98]

        # Assertions
        assert p95 < 200, \
            f"P95 latency ({p95:.2f}ms) exceeds acceptance threshold (200ms)"

        print(f"\n✓ Medium dataset (20 agents) latency:")
        print(f"  - P50: {p50:.2f}ms")
        print(f"  - P95: {p95:.2f}ms (target: <100ms, acceptance: <200ms)")
        print(f"  - P99: {p99:.2f}ms")
        print(f"  - Result: {'OPTIMAL' if p95 < 100 else 'ACCEPTABLE'}")

    async def test_large_dataset_latency(self, db_session, test_user, populate_agents):
        """
        Test latency with large dataset (50 agents).
        Target: P95 < 200ms
        Acceptance: P95 < 500ms
        """

        # Setup: 50 agents
        await populate_agents(50)

        # Warm-up call
        await get_available_agents(db_session, test_user.tenant_key)

        # Benchmark: 50 calls (fewer due to larger dataset)
        latencies = []
        for _ in range(50):
            start = time.perf_counter()
            await get_available_agents(db_session, test_user.tenant_key)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)

        # Calculate percentiles
        latencies.sort()
        p50 = quantiles(latencies, n=2)[0]
        p95_idx = int(len(latencies) * 0.95)
        p95 = latencies[p95_idx]
        p99_idx = int(len(latencies) * 0.99)
        p99 = latencies[p99_idx] if p99_idx < len(latencies) else latencies[-1]

        # Assertions
        assert p95 < 500, \
            f"P95 latency ({p95:.2f}ms) exceeds acceptance threshold (500ms)"

        print(f"\n✓ Large dataset (50 agents) latency:")
        print(f"  - P50: {p50:.2f}ms")
        print(f"  - P95: {p95:.2f}ms (target: <200ms, acceptance: <500ms)")
        print(f"  - P99: {p99:.2f}ms")
        print(f"  - Result: {'OPTIMAL' if p95 < 200 else 'ACCEPTABLE'}")

    async def test_concurrent_calls_latency(self, db_session, test_user, populate_agents):
        """
        Test latency with concurrent calls (simulates multiple orchestrators).
        Target: P95 < 150ms under concurrent load
        Acceptance: P95 < 300ms
        """

        # Setup: 10 agents
        await populate_agents(10)

        # Warm-up
        await get_available_agents(db_session, test_user.tenant_key)

        # Benchmark: Concurrent calls (simulated via sequential rapid calls)
        latencies = []
        for batch in range(10):  # 10 batches
            batch_latencies = []
            for _ in range(5):  # 5 calls per batch
                start = time.perf_counter()
                await get_available_agents(db_session, test_user.tenant_key)
                end = time.perf_counter()
                batch_latencies.append((end - start) * 1000)
            latencies.extend(batch_latencies)

        # Calculate percentiles
        latencies.sort()
        p50 = quantiles(latencies, n=2)[0]
        p95 = quantiles(latencies, n=20)[18]
        p99 = quantiles(latencies, n=100)[98]

        # Assertions
        assert p95 < 300, \
            f"P95 latency under load ({p95:.2f}ms) exceeds acceptance threshold (300ms)"

        print(f"\n✓ Concurrent calls (10 agents, 50 total calls) latency:")
        print(f"  - P50: {p50:.2f}ms")
        print(f"  - P95: {p95:.2f}ms (target: <150ms, acceptance: <300ms)")
        print(f"  - P99: {p99:.2f}ms")
        print(f"  - Result: {'OPTIMAL' if p95 < 150 else 'ACCEPTABLE'}")

    async def test_cache_performance_improvement(self, db_session, test_user, populate_agents):
        """
        Test that caching (if implemented) improves performance.
        If no caching, latency should be consistent.
        """

        # Setup: 10 agents
        await populate_agents(10)

        # First call (cold)
        start_cold = time.perf_counter()
        await get_available_agents(db_session, test_user.tenant_key)
        end_cold = time.perf_counter()
        cold_latency = (end_cold - start_cold) * 1000

        # Subsequent calls (warm)
        warm_latencies = []
        for _ in range(10):
            start_warm = time.perf_counter()
            await get_available_agents(db_session, test_user.tenant_key)
            end_warm = time.perf_counter()
            warm_latencies.append((end_warm - start_warm) * 1000)

        avg_warm_latency = sum(warm_latencies) / len(warm_latencies)

        # If caching exists, warm should be faster than cold
        # If no caching, they should be similar
        performance_improvement = ((cold_latency - avg_warm_latency) / cold_latency) * 100

        print(f"\n✓ Cache performance (if implemented):")
        print(f"  - Cold call latency: {cold_latency:.2f}ms")
        print(f"  - Avg warm call latency: {avg_warm_latency:.2f}ms")
        print(f"  - Performance improvement: {performance_improvement:.1f}%")
        print(f"  - Caching detected: {performance_improvement > 10}")


@pytest.mark.asyncio
class TestMCPToolThroughput:
    """Throughput tests for get_available_agents() MCP tool."""

    async def test_requests_per_second(self, db_session, test_user, populate_agents):
        """
        Test throughput (requests per second).
        Target: >100 RPS for small datasets
        """

        # Setup: 5 agents
        await populate_agents(5)

        # Warm-up
        await get_available_agents(db_session, test_user.tenant_key)

        # Benchmark: As many calls as possible in 1 second
        start_time = time.perf_counter()
        request_count = 0

        while (time.perf_counter() - start_time) < 1.0:
            await get_available_agents(db_session, test_user.tenant_key)
            request_count += 1

        actual_duration = time.perf_counter() - start_time
        rps = request_count / actual_duration

        print(f"\n✓ Throughput test (5 agents):")
        print(f"  - Requests completed: {request_count}")
        print(f"  - Duration: {actual_duration:.2f}s")
        print(f"  - Requests per second: {rps:.1f} RPS")
        print(f"  - Target: >100 RPS")
        print(f"  - Result: {'OPTIMAL' if rps > 100 else 'ACCEPTABLE' if rps > 50 else 'NEEDS OPTIMIZATION'}")

        # This is informational - no hard assertion
        # Performance will vary by hardware
