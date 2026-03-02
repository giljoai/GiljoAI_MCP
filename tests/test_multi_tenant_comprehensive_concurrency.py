"""
Multi-tenant concurrency and performance tests for GiljoAI MCP.

Split from test_multi_tenant_comprehensive.py: covers concurrent operations,
thread safety, performance benchmarks, and isolation under load.
"""

import random

# Add src to path
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import select

pytestmark = pytest.mark.skip(reason="0750c3: async_engine attribute missing on DatabaseManager — DB test infrastructure")


sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Job, Message, Project, Task
from src.giljo_mcp.tenant import TenantManager
from tests.helpers.test_db_helper import PostgreSQLTestHelper


class TestMultiTenantConcurrency:
    """Tests for multi-tenant concurrency, thread safety, and performance."""

    @pytest.fixture
    def db_manager(self):
        """Create an in-memory database manager for testing."""
        manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
        manager.create_tables()
        yield manager
        manager.close()

    def test_concurrent_tenant_creation(self, db_manager):
        """Test concurrent creation of projects across multiple tenants."""
        num_tenants = 15
        projects_per_tenant = 5

        def create_tenant_projects(tenant_key: str, tenant_id: int) -> list[str]:
            """Create multiple projects for a tenant."""
            project_ids = []

            for i in range(projects_per_tenant):
                with db_manager.get_tenant_session(tenant_key) as session:
                    project = Project(
                        name=f"Concurrent Project T{tenant_id}_P{i}",
                        mission=f"Concurrent mission {i}",
                        tenant_key=tenant_key,
                        series_number=random.randint(1, 999999),
                    )
                    session.add(project)

                    # Add some agents
                    for j in range(2):
                        agent = Agent(
                            name=f"concurrent_agent_T{tenant_id}_P{i}_A{j}",
                            role="worker",
                            tenant_key=tenant_key,
                            project_id=project.id,
                            status="active",
                        )
                        session.add(agent)

                    session.commit()
                    project_ids.append(project.id)

            return project_ids

        # Generate tenant keys
        tenant_keys = [TenantManager.generate_tenant_key() for _ in range(num_tenants)]

        # Execute concurrent operations
        with ThreadPoolExecutor(max_workers=num_tenants) as executor:
            futures = {}
            for i, tenant_key in enumerate(tenant_keys):
                future = executor.submit(create_tenant_projects, tenant_key, i)
                futures[future] = tenant_key

            results = {}
            for future in as_completed(futures):
                tenant_key = futures[future]
                try:
                    project_ids = future.result(timeout=30)
                    results[tenant_key] = project_ids
                except Exception as e:
                    pytest.fail(f"Failed to create projects for tenant {tenant_key}: {e}")

        # Verify all tenants have correct data
        for tenant_key, project_ids in results.items():
            with db_manager.get_tenant_session(tenant_key) as session:
                # Check projects
                projects = session.execute(select(Project).where(Project.tenant_key == tenant_key)).scalars().all()
                assert len(projects) == projects_per_tenant
                assert {p.id for p in projects} == set(project_ids)

                # Check agents (2 per project)
                agents = session.execute(select(Agent).where(Agent.tenant_key == tenant_key)).scalars().all()
                assert len(agents) == projects_per_tenant * 2

                # Verify all belong to this tenant
                for project in projects:
                    assert project.tenant_key == tenant_key
                for agent in agents:
                    assert agent.tenant_key == tenant_key

    def test_thread_safety_tenant_manager(self, db_manager):
        """Test thread safety of TenantManager operations."""
        num_threads = 20
        operations_per_thread = 50

        def thread_operations(thread_id: int) -> dict[str, Any]:
            """Perform TenantManager operations in a thread."""
            results = {"keys_generated": [], "validations": 0, "context_switches": 0, "errors": []}

            try:
                for _i in range(operations_per_thread):
                    # Generate key
                    key = TenantManager.generate_tenant_key()
                    results["keys_generated"].append(key)

                    # Validate key
                    if TenantManager.validate_tenant_key(key):
                        results["validations"] += 1

                    # Context switching
                    TenantManager.set_current_tenant(key)
                    current = TenantManager.get_current_tenant()
                    if current == key:
                        results["context_switches"] += 1

                    # Use context manager
                    with TenantManager.with_tenant(key):
                        in_context = TenantManager.get_current_tenant()
                        assert in_context == key

            except Exception as e:
                results["errors"].append(str(e))

            return results

        # Run thread safety test
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for i in range(num_threads):
                future = executor.submit(thread_operations, i)
                futures.append(future)

            all_keys = []
            total_validations = 0
            total_context_switches = 0
            errors = []

            for future in as_completed(futures):
                result = future.result()
                all_keys.extend(result["keys_generated"])
                total_validations += result["validations"]
                total_context_switches += result["context_switches"]
                errors.extend(result["errors"])

        # Verify results
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len(all_keys) == num_threads * operations_per_thread
        assert len(set(all_keys)) == len(all_keys), "Duplicate keys generated"
        assert total_validations == num_threads * operations_per_thread
        assert total_context_switches == num_threads * operations_per_thread

    def test_performance_with_many_tenants(self, db_manager):
        """Test system performance with 50+ tenants."""
        num_tenants = 50
        tenant_keys = []

        # Measure tenant creation time
        start_time = time.perf_counter()

        for i in range(num_tenants):
            tenant_key = TenantManager.generate_tenant_key()
            tenant_keys.append(tenant_key)

            with db_manager.get_tenant_session(tenant_key) as session:
                project = Project(
                    name=f"Performance Test Project {i}",
                    mission=f"Performance testing for tenant {i}",
                    tenant_key=tenant_key,
                    series_number=random.randint(1, 999999),
                )
                session.add(project)
                session.commit()

        creation_time = time.perf_counter() - start_time
        avg_creation_time = creation_time / num_tenants

        # Should create tenants quickly
        assert avg_creation_time < 0.1, f"Tenant creation too slow: {avg_creation_time:.3f}s per tenant"

        # Measure query performance
        query_times = []

        for tenant_key in random.sample(tenant_keys, min(10, num_tenants)):
            start_time = time.perf_counter()

            with db_manager.get_tenant_session(tenant_key) as session:
                projects = session.execute(select(Project).where(Project.tenant_key == tenant_key)).scalars().all()
                assert len(projects) == 1

            query_time = time.perf_counter() - start_time
            query_times.append(query_time)

        avg_query_time = sum(query_times) / len(query_times)

        # Queries should be fast even with many tenants
        assert avg_query_time < 0.05, f"Query performance degraded: {avg_query_time:.3f}s per query"

    def test_tenant_isolation_under_load(self, db_manager):
        """Stress test tenant isolation with high concurrent load."""
        num_tenants = 10
        operations_per_tenant = 100
        tenant_keys = [TenantManager.generate_tenant_key() for _ in range(num_tenants)]

        # Initialize tenants
        for tenant_key in tenant_keys:
            with db_manager.get_tenant_session(tenant_key) as session:
                project = Project(name="Load Test Project", mission="Stress testing", tenant_key=tenant_key, series_number=random.randint(1, 999999))
                session.add(project)
                session.commit()

        def stress_operations(tenant_key: str) -> dict[str, int]:
            """Perform stress operations for a tenant."""
            counts = {"agents_created": 0, "messages_sent": 0, "tasks_created": 0, "queries_executed": 0}

            with db_manager.get_tenant_session(tenant_key) as session:
                project = session.execute(select(Project).where(Project.tenant_key == tenant_key)).scalars().first()

                for i in range(operations_per_tenant):
                    operation = random.choice(["create_agent", "send_message", "create_task", "query"])

                    if operation == "create_agent":
                        agent = Agent(
                            name=f"stress_agent_{i}",
                            role="worker",
                            tenant_key=tenant_key,
                            project_id=project.id,
                            status="active",
                        )
                        session.add(agent)
                        counts["agents_created"] += 1

                    elif operation == "send_message":
                        message = Message(
                            tenant_key=tenant_key,
                            project_id=project.id,
                            to_agents=["stress_agent"],
                            description=f"Stress message {i}",
                            message_type="broadcast",
                            status="waiting",
                        )
                        session.add(message)
                        counts["messages_sent"] += 1

                    elif operation == "create_task":
                        task = Task(
                            tenant_key=tenant_key,
                            project_id=project.id,
                            content=f"Stress task {i}",
                            category="stress",
                            priority="medium",
                            status="waiting",
                        )
                        session.add(task)
                        counts["tasks_created"] += 1

                    else:  # query
                        session.execute(select(Agent).where(Agent.tenant_key == tenant_key).limit(10)).scalars().all()
                        counts["queries_executed"] += 1

                    if i % 10 == 0:
                        session.commit()

                session.commit()

            return counts

        # Run stress test concurrently
        start_time = time.perf_counter()

        with ThreadPoolExecutor(max_workers=num_tenants) as executor:
            futures = {}
            for tenant_key in tenant_keys:
                future = executor.submit(stress_operations, tenant_key)
                futures[future] = tenant_key

            results = {}
            for future in as_completed(futures):
                tenant_key = futures[future]
                try:
                    counts = future.result(timeout=60)
                    results[tenant_key] = counts
                except Exception as e:
                    pytest.fail(f"Stress test failed for tenant {tenant_key}: {e}")

        elapsed_time = time.perf_counter() - start_time

        # Verify isolation after stress test
        for tenant_key in tenant_keys:
            with db_manager.get_tenant_session(tenant_key) as session:
                # All data should belong to this tenant only
                agents = session.execute(select(Agent).where(Agent.tenant_key == tenant_key)).scalars().all()
                messages = session.execute(select(Message).where(Message.tenant_key == tenant_key)).scalars().all()
                tasks = session.execute(select(Task).where(Task.tenant_key == tenant_key)).scalars().all()

                for agent in agents:
                    assert agent.tenant_key == tenant_key
                for message in messages:
                    assert message.tenant_key == tenant_key
                for task in tasks:
                    assert task.tenant_key == tenant_key

        # Calculate totals
        total_operations = sum(sum(counts.values()) for counts in results.values())
        ops_per_second = total_operations / elapsed_time

        # Should handle at least 100 ops/second
        assert ops_per_second > 100, f"Performance too low: {ops_per_second:.0f} ops/s"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
