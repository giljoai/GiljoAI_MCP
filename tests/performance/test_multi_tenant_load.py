"""
Multi-Tenant Isolation Performance Tests
Tests tenant isolation and performance under concurrent multi-tenant load

PRODUCTION REQUIREMENTS:
- Multiple tenants with 50+ agents each
- Complete tenant isolation under load
- Cross-tenant security validation
- Resource allocation fairness
- Performance isolation (one tenant can't impact others)
"""

import asyncio
import time
import uuid
from statistics import mean

import pytest
import pytest_asyncio

from src.giljo_mcp.orchestrator import ProjectOrchestrator
from src.giljo_mcp.tenant import TenantManager


# TODO: MessageTools class doesn't exist yet - commenting out for test collection
# from src.giljo_mcp.tools.message import MessageTools


class TenantTestEnvironment:
    """Test environment for a single tenant"""

    def __init__(self, tenant_id, tenant_key, num_agents=50):
        self.tenant_id = tenant_id
        self.tenant_key = tenant_key
        self.num_agents = num_agents
        self.project_id = None
        self.agents = []
        self.messages_sent = 0
        self.messages_received = 0
        self.performance_metrics = {}

    async def setup(self, orchestrator, db_session):
        """Set up tenant environment with project and agents"""
        # Create project for this tenant
        self.project_id = str(uuid.uuid4())

        await orchestrator.create_project(
            project_id=self.project_id,
            name=f"Tenant {self.tenant_id} Load Test",
            mission=f"Multi-tenant performance test for tenant {self.tenant_id}",
            tenant_key=self.tenant_key,
        )

        # Create agents for this tenant
        start_time = time.perf_counter()
        agent_tasks = []

        for i in range(self.num_agents):
            agent_name = f"tenant_{self.tenant_id}_agent_{i}"
            task = orchestrator.spawn_agent(project_id=self.project_id, agent_name=agent_name, role="worker")
            agent_tasks.append(task)

        self.agents = await asyncio.gather(*agent_tasks, return_exceptions=True)
        setup_time = (time.perf_counter() - start_time) * 1000

        # Filter successful agents
        self.agents = [a for a in self.agents if not isinstance(a, Exception)]

        self.performance_metrics["setup_time_ms"] = setup_time
        self.performance_metrics["agents_created"] = len(self.agents)
        self.performance_metrics["agents_requested"] = self.num_agents

        return len(self.agents) == self.num_agents

    async def simulate_workload(self, message_tools, duration_seconds=30):
        """Simulate realistic tenant workload"""
        start_time = time.time()
        end_time = start_time + duration_seconds

        workload_tasks = []

        # Each agent sends messages periodically
        for agent in self.agents:
            task = self._agent_message_workload(message_tools, agent, start_time, end_time)
            workload_tasks.append(task)

        # Execute workload
        await asyncio.gather(*workload_tasks, return_exceptions=True)

        self.performance_metrics["workload_duration_s"] = duration_seconds
        self.performance_metrics["messages_sent"] = self.messages_sent
        self.performance_metrics["messages_per_second"] = self.messages_sent / duration_seconds

    async def _agent_message_workload(self, message_tools, agent, start_time, end_time):
        """Individual agent message workload"""
        agent_messages = 0

        while time.time() < end_time:
            try:
                # Send message to another random agent in the same tenant
                if len(self.agents) > 1:
                    target_agent = self.agents[(self.agents.index(agent) + 1) % len(self.agents)]

                    await message_tools.send_message(
                        project_id=self.project_id,
                        from_agent=agent.name,
                        to_agents=[target_agent.name],
                        content=f"Workload message {agent_messages} from {agent.name}",
                        message_type="direct",
                        priority="normal",
                    )

                    agent_messages += 1
                    self.messages_sent += 1

                # Wait before next message
                await asyncio.sleep(1.0)  # 1 message per second per agent

            except Exception:
                break


class TestMultiTenantLoad:
    """Test multi-tenant performance and isolation"""

    @pytest_asyncio.fixture
    async def orchestrator(self, test_db):
        """Create orchestrator for testing"""
        orchestrator = ProjectOrchestrator(test_db)
        yield orchestrator
        # Cleanup: _stop_context_monitor() was removed in Handover 0422 (dead token budget cleanup)

    @pytest_asyncio.fixture
    async def message_tools(self, test_db):
        """Create message tools for testing"""
        return MessageTools(test_db)

    @pytest_asyncio.fixture
    async def tenant_manager(self, test_db):
        """Create tenant manager for testing"""
        return TenantManager(test_db)

    async def test_single_tenant_baseline_performance(self, orchestrator, message_tools, db_session):
        """Establish baseline performance for single tenant with 50 agents"""
        tenant_key = str(uuid.uuid4())
        tenant_env = TenantTestEnvironment("baseline", tenant_key, num_agents=50)

        # Setup tenant environment
        setup_success = await tenant_env.setup(orchestrator, db_session)
        assert setup_success, "Failed to set up baseline tenant environment"

        # Run workload for 10 seconds
        await tenant_env.simulate_workload(message_tools, duration_seconds=10)

        metrics = tenant_env.performance_metrics

        # Baseline validation
        assert metrics["setup_time_ms"] < 30000, f"Baseline setup too slow: {metrics['setup_time_ms']:.2f}ms"
        assert metrics["agents_created"] >= 45, f"Too few agents created: {metrics['agents_created']}/50"
        assert metrics["messages_per_second"] >= 40, (
            f"Baseline throughput too low: {metrics['messages_per_second']:.1f}/s"
        )

    async def test_dual_tenant_isolation_performance(self, orchestrator, message_tools, db_session):
        """Test performance with 2 tenants running concurrently"""
        # Create two tenant environments
        tenant1_key = str(uuid.uuid4())
        tenant2_key = str(uuid.uuid4())

        tenant1 = TenantTestEnvironment("tenant1", tenant1_key, num_agents=30)
        tenant2 = TenantTestEnvironment("tenant2", tenant2_key, num_agents=30)

        # Setup both tenants concurrently
        setup_start = time.perf_counter()
        setup_tasks = [tenant1.setup(orchestrator, db_session), tenant2.setup(orchestrator, db_session)]
        setup_results = await asyncio.gather(*setup_tasks, return_exceptions=True)
        (time.perf_counter() - setup_start) * 1000

        assert all(setup_results), "Failed to set up dual tenant environments"

        # Run concurrent workloads
        workload_tasks = [
            tenant1.simulate_workload(message_tools, duration_seconds=15),
            tenant2.simulate_workload(message_tools, duration_seconds=15),
        ]
        await asyncio.gather(*workload_tasks, return_exceptions=True)

        # Analyze isolation and performance

        # Validate tenant isolation doesn't impact performance significantly
        combined_throughput = (
            tenant1.performance_metrics["messages_per_second"] + tenant2.performance_metrics["messages_per_second"]
        )

        assert combined_throughput >= 50, (
            f"Dual tenant throughput too low: {combined_throughput:.1f} messages/s\n"
            f"This indicates tenant isolation is impacting performance."
        )

        # Validate tenant keys are different (isolation)
        assert tenant1.tenant_key != tenant2.tenant_key, "Tenant keys are not isolated"
        assert tenant1.project_id != tenant2.project_id, "Project IDs are not isolated"

    @pytest.mark.slow
    async def test_five_tenant_concurrent_load(self, orchestrator, message_tools, db_session):
        """Test 5 tenants running concurrently with 20 agents each"""
        tenants = []

        # Create 5 tenant environments
        for i in range(5):
            tenant_key = str(uuid.uuid4())
            tenant = TenantTestEnvironment(f"multi_{i}", tenant_key, num_agents=20)
            tenants.append(tenant)

        # Setup all tenants concurrently
        setup_start = time.perf_counter()
        setup_tasks = [tenant.setup(orchestrator, db_session) for tenant in tenants]
        setup_results = await asyncio.gather(*setup_tasks, return_exceptions=True)
        (time.perf_counter() - setup_start) * 1000

        successful_setups = sum(1 for r in setup_results if r is True)

        assert successful_setups >= 4, f"Too many tenant setup failures: {successful_setups}/5"

        # Run concurrent workloads for all tenants
        workload_tasks = [
            tenant.simulate_workload(message_tools, duration_seconds=20)
            for tenant in tenants
            if tenant.performance_metrics.get("agents_created", 0) > 0
        ]

        await asyncio.gather(*workload_tasks, return_exceptions=True)

        # Analyze multi-tenant performance
        total_agents = sum(t.performance_metrics.get("agents_created", 0) for t in tenants)
        total_throughput = sum(t.performance_metrics.get("messages_per_second", 0) for t in tenants)

        for i, tenant in enumerate(tenants):
            pass

        # PRODUCTION REQUIREMENTS VALIDATION
        assert total_agents >= 80, (
            f"PRODUCTION FAILURE: Total agents {total_agents} < 80 (4 tenants × 20 agents)\n"
            f"This indicates multi-tenant scalability issues."
        )

        assert total_throughput >= 60, (
            f"PRODUCTION FAILURE: Multi-tenant throughput {total_throughput:.1f}/s < 60/s\n"
            f"This indicates performance degradation under multi-tenant load."
        )

    async def test_tenant_data_isolation_verification(self, orchestrator, message_tools, db_session):
        """Verify complete data isolation between tenants"""
        # Create two tenants with similar data
        tenant1_key = str(uuid.uuid4())
        tenant2_key = str(uuid.uuid4())

        tenant1 = TenantTestEnvironment("isolation1", tenant1_key, num_agents=10)
        tenant2 = TenantTestEnvironment("isolation2", tenant2_key, num_agents=10)

        # Setup both tenants
        await tenant1.setup(orchestrator, db_session)
        await tenant2.setup(orchestrator, db_session)

        # Send messages within each tenant
        for i in range(5):
            # Tenant 1 messages
            await message_tools.send_message(
                project_id=tenant1.project_id,
                from_agent="orchestrator",
                to_agents=[tenant1.agents[0].name],
                content=f"Tenant 1 secret message {i}",
                message_type="direct",
                priority="normal",
            )

            # Tenant 2 messages
            await message_tools.send_message(
                project_id=tenant2.project_id,
                from_agent="orchestrator",
                to_agents=[tenant2.agents[0].name],
                content=f"Tenant 2 secret message {i}",
                message_type="direct",
                priority="normal",
            )

        # Verify tenant 1 cannot access tenant 2's messages and vice versa
        tenant1_messages = await message_tools.get_messages(
            agent_name=tenant1.agents[0].name, project_id=tenant1.project_id
        )

        tenant2_messages = await message_tools.get_messages(
            agent_name=tenant2.agents[0].name, project_id=tenant2.project_id
        )

        # Verify isolation
        assert len(tenant1_messages) >= 5, "Tenant 1 missing its own messages"
        assert len(tenant2_messages) >= 5, "Tenant 2 missing its own messages"

        # Check that messages contain only tenant-specific content
        tenant1_content = [m.get("content", "") for m in tenant1_messages]
        tenant2_content = [m.get("content", "") for m in tenant2_messages]

        tenant1_has_own_data = any("Tenant 1 secret" in content for content in tenant1_content)
        tenant1_has_other_data = any("Tenant 2 secret" in content for content in tenant1_content)

        tenant2_has_own_data = any("Tenant 2 secret" in content for content in tenant2_content)
        tenant2_has_other_data = any("Tenant 1 secret" in content for content in tenant2_content)

        assert tenant1_has_own_data, "Tenant 1 doesn't have access to its own data"
        assert not tenant1_has_other_data, "Tenant 1 has access to Tenant 2's data - SECURITY BREACH"

        assert tenant2_has_own_data, "Tenant 2 doesn't have access to its own data"
        assert not tenant2_has_other_data, "Tenant 2 has access to Tenant 1's data - SECURITY BREACH"

    async def test_tenant_performance_isolation(self, orchestrator, message_tools, db_session):
        """Test that one tenant's heavy load doesn't impact another tenant's performance"""
        # Create two tenants: one for heavy load, one for normal load
        heavy_tenant_key = str(uuid.uuid4())
        normal_tenant_key = str(uuid.uuid4())

        heavy_tenant = TenantTestEnvironment("heavy_load", heavy_tenant_key, num_agents=40)
        normal_tenant = TenantTestEnvironment("normal_load", normal_tenant_key, num_agents=10)

        # Setup both tenants
        await heavy_tenant.setup(orchestrator, db_session)
        await normal_tenant.setup(orchestrator, db_session)

        # Measure normal tenant baseline performance (alone)
        baseline_start = time.perf_counter()
        await normal_tenant.simulate_workload(message_tools, duration_seconds=10)
        baseline_performance = normal_tenant.performance_metrics["messages_per_second"]
        (time.perf_counter() - baseline_start) * 1000

        # Reset normal tenant metrics
        normal_tenant.messages_sent = 0
        normal_tenant.performance_metrics = {}

        # Now run both tenants concurrently (heavy load + normal load)
        concurrent_start = time.perf_counter()
        concurrent_tasks = [
            heavy_tenant.simulate_workload(message_tools, duration_seconds=15),
            normal_tenant.simulate_workload(message_tools, duration_seconds=15),
        ]
        await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        (time.perf_counter() - concurrent_start) * 1000

        concurrent_performance = normal_tenant.performance_metrics["messages_per_second"]
        heavy_tenant.performance_metrics["messages_per_second"]

        # Calculate performance impact
        performance_degradation = (baseline_performance - concurrent_performance) / baseline_performance * 100

        # PRODUCTION ISOLATION REQUIREMENTS
        assert performance_degradation < 25.0, (
            f"PRODUCTION FAILURE: Performance degradation {performance_degradation:.1f}% > 25%\n"
            f"Heavy tenant load is significantly impacting other tenants.\n"
            f"This indicates insufficient tenant performance isolation."
        )

        assert concurrent_performance > baseline_performance * 0.8, (
            f"PRODUCTION FAILURE: Concurrent performance {concurrent_performance:.1f} "
            f"< 80% of baseline {baseline_performance:.1f}\n"
            f"This indicates severe performance isolation issues."
        )

    async def test_tenant_resource_allocation_fairness(self, orchestrator, message_tools, db_session):
        """Test fair resource allocation across multiple tenants"""
        num_tenants = 4
        agents_per_tenant = 15
        tenants = []

        # Create equal tenant environments
        for i in range(num_tenants):
            tenant_key = str(uuid.uuid4())
            tenant = TenantTestEnvironment(f"fair_{i}", tenant_key, agents_per_tenant)
            tenants.append(tenant)

        # Setup all tenants concurrently
        setup_tasks = [tenant.setup(orchestrator, db_session) for tenant in tenants]
        await asyncio.gather(*setup_tasks, return_exceptions=True)

        # Run equal workloads on all tenants
        workload_tasks = [tenant.simulate_workload(message_tools, duration_seconds=20) for tenant in tenants]
        await asyncio.gather(*workload_tasks, return_exceptions=True)

        # Analyze resource allocation fairness
        performances = [t.performance_metrics.get("messages_per_second", 0) for t in tenants]
        agent_counts = [t.performance_metrics.get("agents_created", 0) for t in tenants]

        avg_performance = mean(performances)
        avg_agents = mean(agent_counts)

        for i, tenant in enumerate(tenants):
            metrics = tenant.performance_metrics
            perf = metrics.get("messages_per_second", 0)
            agents = metrics.get("agents_created", 0)
            abs(perf - avg_performance) / avg_performance * 100
            abs(agents - avg_agents) / avg_agents * 100

        # Check fairness - no tenant should have significantly different performance
        max_perf_variance = max(abs(p - avg_performance) / avg_performance * 100 for p in performances)
        max_agent_variance = max(abs(a - avg_agents) / avg_agents * 100 for a in agent_counts)

        assert max_perf_variance < 30.0, (
            f"PRODUCTION FAILURE: Performance variance {max_perf_variance:.1f}% > 30%\n"
            f"Resource allocation is not fair across tenants."
        )

        assert max_agent_variance < 20.0, (
            f"PRODUCTION FAILURE: Agent allocation variance {max_agent_variance:.1f}% > 20%\n"
            f"Agent creation is not fair across tenants."
        )


if __name__ == "__main__":
    # Run performance tests directly
    pytest.main([__file__, "-v", "-s", "--tb=short"])
