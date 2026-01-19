"""
Concurrent Agent Performance Tests
Tests the system's ability to handle 100+ concurrent agents

PRODUCTION REQUIREMENTS:
- 100+ agents operating concurrently
- Sub-100ms agent creation latency
- Agent lifecycle performance under load
- Context switching efficiency
- Handoff performance at scale
"""

import asyncio
import time
import uuid

import pytest
import pytest_asyncio

from src.giljo_mcp.orchestrator import ProjectOrchestrator
from tests.benchmark_tools import PerformanceBenchmark


class TestConcurrentAgents:
    """Test concurrent agent operations at production scale"""

    @pytest_asyncio.fixture
    async def orchestrator(self, test_db, tenant_manager):
        """Create orchestrator for testing"""
        orchestrator = ProjectOrchestrator(test_db)
        yield orchestrator
        # Cleanup: _stop_context_monitor() was removed in Handover 0422 (dead token budget cleanup)

    @pytest_asyncio.fixture
    async def test_project(self, orchestrator, db_session):
        """Create test project for agent testing"""
        project_id = str(uuid.uuid4())
        tenant_key = str(uuid.uuid4())

        project = await orchestrator.create_project(
            project_id=project_id,
            name="Agent Load Test Project",
            mission="Test 100+ concurrent agents for production validation",
            tenant_key=tenant_key,
        )
        return project

    async def test_single_agent_creation_latency(self, orchestrator, test_project):
        """Test single agent creation meets latency requirements"""
        benchmark = PerformanceBenchmark(target_time_ms=100.0)

        async def create_agent():
            agent_name = f"test_agent_{uuid.uuid4().hex[:8]}"
            return await orchestrator.spawn_agent(project_id=test_project.id, agent_name=agent_name, role="worker")

        # Benchmark single agent creation
        result = await benchmark.benchmark_async("single_agent_creation", create_agent, iterations=50, warmup=5)

        # Validate requirements
        assert result.avg_time < 100.0, f"Agent creation too slow: {result.avg_time:.2f}ms > 100ms"
        assert result.success_rate > 95.0, f"Success rate too low: {result.success_rate:.1f}%"

    async def test_concurrent_agent_spawning_10(self, orchestrator, test_project):
        """Test spawning 10 agents concurrently (baseline)"""
        start_time = time.perf_counter()

        # Create 10 agents concurrently
        tasks = []
        for i in range(10):
            agent_name = f"concurrent_agent_{i}_{uuid.uuid4().hex[:8]}"
            task = orchestrator.spawn_agent(project_id=test_project.id, agent_name=agent_name, role="worker")
            tasks.append(task)

        agents = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = (time.perf_counter() - start_time) * 1000

        # Validate results
        successful_agents = [a for a in agents if not isinstance(a, Exception)]
        success_rate = len(successful_agents) / len(agents) * 100

        assert success_rate > 95.0, f"Too many failures in 10 agent test: {success_rate:.1f}%"
        assert total_time < 2000, f"10 agents took too long: {total_time:.2f}ms"

    async def test_concurrent_agent_spawning_50(self, orchestrator, test_project):
        """Test spawning 50 agents concurrently (mid-scale)"""
        start_time = time.perf_counter()

        # Create 50 agents concurrently
        tasks = []
        for i in range(50):
            agent_name = f"mid_scale_agent_{i}_{uuid.uuid4().hex[:8]}"
            task = orchestrator.spawn_agent(project_id=test_project.id, agent_name=agent_name, role="worker")
            tasks.append(task)

        agents = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = (time.perf_counter() - start_time) * 1000

        # Validate results
        successful_agents = [a for a in agents if not isinstance(a, Exception)]
        success_rate = len(successful_agents) / len(agents) * 100

        assert success_rate > 90.0, f"Too many failures in 50 agent test: {success_rate:.1f}%"
        assert total_time < 10000, f"50 agents took too long: {total_time:.2f}ms"

    @pytest.mark.slow
    async def test_concurrent_agent_spawning_100_production_requirement(self, orchestrator, test_project):
        """
        CRITICAL PRODUCTION TEST: 100+ concurrent agents
        This test validates our core requirement for commercial deployment
        """
        start_time = time.perf_counter()

        # Create exactly 100 agents concurrently (production requirement)
        tasks = []
        for i in range(100):
            agent_name = f"production_agent_{i}_{uuid.uuid4().hex[:8]}"
            task = orchestrator.spawn_agent(project_id=test_project.id, agent_name=agent_name, role="worker")
            tasks.append(task)

        agents = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = (time.perf_counter() - start_time) * 1000

        # Analyze results
        successful_agents = [a for a in agents if not isinstance(a, Exception)]
        failed_agents = [a for a in agents if isinstance(a, Exception)]
        success_rate = len(successful_agents) / len(agents) * 100

        # Log any failures for analysis
        if failed_agents:
            for i, _error in enumerate(failed_agents[:5]):  # Show first 5 errors
                pass

        # PRODUCTION REQUIREMENTS VALIDATION
        assert success_rate >= 95.0, (
            f"PRODUCTION FAILURE: 100 agent spawn success rate {success_rate:.1f}% < 95%\n"
            f"Failed agents: {len(failed_agents)}\n"
            f"This indicates a production scalability issue that must be fixed in the orchestrator."
        )

        assert total_time < 30000, (
            f"PRODUCTION FAILURE: 100 agents took {total_time:.2f}ms > 30s\n"
            f"This indicates a performance bottleneck that must be optimized."
        )

        avg_time_per_agent = total_time / 100
        assert avg_time_per_agent < 300, (
            f"PRODUCTION FAILURE: Average agent creation {avg_time_per_agent:.2f}ms > 300ms\n"
            f"This indicates the system cannot scale to commercial requirements."
        )

    @pytest.mark.stress
    async def test_concurrent_agent_spawning_150_stress_test(self, orchestrator, test_project):
        """
        STRESS TEST: Push beyond requirements to identify breaking points
        This helps us understand system limits and capacity planning
        """
        start_time = time.perf_counter()

        # Create 150 agents (50% over requirement) to test limits
        tasks = []
        for i in range(150):
            agent_name = f"stress_agent_{i}_{uuid.uuid4().hex[:8]}"
            task = orchestrator.spawn_agent(project_id=test_project.id, agent_name=agent_name, role="worker")
            tasks.append(task)

        agents = await asyncio.gather(*tasks, return_exceptions=True)
        (time.perf_counter() - start_time) * 1000

        # Analyze stress test results
        successful_agents = [a for a in agents if not isinstance(a, Exception)]
        [a for a in agents if isinstance(a, Exception)]
        success_rate = len(successful_agents) / len(agents) * 100

        if success_rate < 80:
            pass
        else:
            pass

    async def test_agent_lifecycle_under_load(self, orchestrator, test_project):
        """Test complete agent lifecycle under concurrent load"""
        # Create 20 agents
        agents = []
        for i in range(20):
            agent_name = f"lifecycle_agent_{i}_{uuid.uuid4().hex[:8]}"
            agent = await orchestrator.spawn_agent(project_id=test_project.id, agent_name=agent_name, role="worker")
            agents.append(agent)

        # Test handoff performance
        start_time = time.perf_counter()
        handoff_tasks = []

        for i in range(0, len(agents), 2):
            if i + 1 < len(agents):
                task = orchestrator.handoff(
                    from_agent=agents[i].name,
                    to_agent=agents[i + 1].name,
                    project_id=test_project.id,
                    context={"test": "handoff_data"},
                )
                handoff_tasks.append(task)

        await asyncio.gather(*handoff_tasks, return_exceptions=True)
        handoff_time = (time.perf_counter() - start_time) * 1000

        # Validate handoff performance
        avg_handoff_time = handoff_time / len(handoff_tasks)
        assert avg_handoff_time < 500, f"Handoff too slow: {avg_handoff_time:.2f}ms > 500ms"

    # HANDOVER 0422: Removed test_context_switching_performance
    # This test called get_agent_context_status() which was removed (dead token budget cleanup)


if __name__ == "__main__":
    # Run performance tests directly
    pytest.main([__file__, "-v", "-s", "--tb=short"])
