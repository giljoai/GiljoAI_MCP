"""
Database Transaction Performance Benchmarks
Tests database performance for both SQLite and PostgreSQL

PRODUCTION REQUIREMENTS:
- Sub-100ms operation latency for critical operations
- Transaction performance under load
- Query optimization validation
- Connection pool stress testing
- SQLite vs PostgreSQL comparison

TODO(0127a-2): This file needs comprehensive refactoring for MCPAgentJob model.
All Agent references need to be replaced with MCPAgentJob with proper field mappings:
- Agent.name → Not applicable (use mission or job_id)
- Agent.role → AgentExecution.agent_type
- Agent.status → AgentExecution.status (different values: pending, working, completed, failed)
- Add required fields: tenant_key, mission, job_id
See handovers/0127a-2_complete_test_refactoring.md for patterns.
"""

import asyncio
import time
import uuid

import pytest
import pytest_asyncio

from src.giljo_mcp.database import DatabaseManager
# TODO(0127a-2): Comprehensive refactoring needed - Agent → MCPAgentJob throughout
# from src.giljo_mcp.models import Agent, Message, Project, Task
# from src.giljo_mcp.models import AgentExecution, Message, Project, Task  # Use this instead
from tests.benchmark_tools import PerformanceBenchmark

import pytest
pytest.skip("TODO(0127a-2): Performance tests need MCPAgentJob refactoring", allow_module_level=True)


class DatabaseBenchmarkRunner:
    """Database performance benchmark runner"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.test_data = {"projects": [], "agents": [], "messages": [], "tasks": []}

    async def setup_test_data(self, num_projects=10, agents_per_project=20):
        """Set up test data for benchmarks"""
        async with self.db_manager.get_session_async() as session:
            # Create projects
            for i in range(num_projects):
                project = Project(
                    id=str(uuid.uuid4()),
                    name=f"Benchmark Project {i}",
                    mission=f"Performance test project {i}",
                    status="active",
                    tenant_key=str(uuid.uuid4()),
                )
                session.add(project)
                self.test_data["projects"].append(project)

                # Create agents for each project
                for j in range(agents_per_project):
                    agent = Agent(
                        id=str(uuid.uuid4()),
                        project_id=project.id,
                        name=f"agent_{i}_{j}",
                        role="worker",
                        status="active",
                    )
                    session.add(agent)
                    self.test_data["agents"].append(agent)

            await session.commit()

    async def cleanup_test_data(self):
        """Clean up test data"""
        async with self.db_manager.get_session_async() as session:
            # Delete in reverse order to respect foreign keys
            for message in self.test_data["messages"]:
                await session.delete(message)
            for task in self.test_data["tasks"]:
                await session.delete(task)
            for agent in self.test_data["agents"]:
                await session.delete(agent)
            for project in self.test_data["projects"]:
                await session.delete(project)

            await session.commit()

        self.test_data = {"projects": [], "agents": [], "messages": [], "tasks": []}


class TestDatabaseBenchmarks:
    """Test database performance at production scale"""

    @pytest_asyncio.fixture
    async def sqlite_db_manager(self):
        """Create SQLite database manager for testing"""

        # PostgreSQL test database used instead of temp file
        # PostgreSQL test database managed by fixtures

        connection_string = fPostgreSQLTestHelper.get_test_db_url()
        db_manager = DatabaseManager(connection_string, is_async=True)
        await db_manager.create_tables_async()

        yield db_manager

        await db_manager.close_async()

        # PostgreSQL test database cleanup handled by fixtures

    @pytest_asyncio.fixture
    async def benchmark_runner(self, sqlite_db_manager):
        """Create benchmark runner with test data"""
        runner = DatabaseBenchmarkRunner(sqlite_db_manager)
        await runner.setup_test_data(num_projects=5, agents_per_project=10)
        yield runner
        await runner.cleanup_test_data()

    async def test_single_record_operations_latency(self, benchmark_runner):
        """Test individual database operation latencies"""
        db_manager = benchmark_runner.db_manager
        benchmark = PerformanceBenchmark(target_time_ms=100.0)

        # Test single project creation
        async def create_project():
            async with db_manager.get_session_async() as session:
                project = Project(
                    id=str(uuid.uuid4()),
                    name="Latency Test Project",
                    mission="Single operation latency test",
                    status="active",
                    tenant_key=str(uuid.uuid4()),
                )
                session.add(project)
                await session.commit()
                return project

        result = await benchmark.benchmark_async("single_project_creation", create_project, iterations=50, warmup=5)

        assert result.avg_time < 100.0, f"Project creation too slow: {result.avg_time:.2f}ms > 100ms"
        assert result.success_rate > 95.0, f"Project creation success rate too low: {result.success_rate:.1f}%"

        # Test single agent creation
        test_project = benchmark_runner.test_data["projects"][0]

        async def create_agent():
            async with db_manager.get_session_async() as session:
                agent = Agent(
                    id=str(uuid.uuid4()),
                    project_id=test_project.id,
                    name=f"latency_agent_{uuid.uuid4().hex[:8]}",
                    role="worker",
                    status="active",
                )
                session.add(agent)
                await session.commit()
                return agent

        result = await benchmark.benchmark_async("single_agent_creation", create_agent, iterations=50, warmup=5)

        assert result.avg_time < 100.0, f"Agent creation too slow: {result.avg_time:.2f}ms > 100ms"

    async def test_bulk_insert_performance(self, benchmark_runner):
        """Test bulk insert performance"""
        db_manager = benchmark_runner.db_manager
        test_project = benchmark_runner.test_data["projects"][0]

        # Test bulk agent creation
        bulk_sizes = [10, 50, 100, 500]

        for bulk_size in bulk_sizes:
            start_time = time.perf_counter()

            async with db_manager.get_session_async() as session:
                agents = []
                for i in range(bulk_size):
                    agent = Agent(
                        id=str(uuid.uuid4()),
                        project_id=test_project.id,
                        name=f"bulk_agent_{i}_{uuid.uuid4().hex[:8]}",
                        role="worker",
                        status="active",
                    )
                    agents.append(agent)
                    session.add(agent)

                await session.commit()

            bulk_time = (time.perf_counter() - start_time) * 1000

            # Validate bulk performance
            if bulk_size <= 100:
                assert bulk_time < 5000, f"Bulk insert of {bulk_size} too slow: {bulk_time:.2f}ms > 5s"
            else:
                assert bulk_time < 30000, f"Large bulk insert of {bulk_size} too slow: {bulk_time:.2f}ms > 30s"

    async def test_query_performance_under_load(self, benchmark_runner):
        """Test query performance with substantial data"""
        db_manager = benchmark_runner.db_manager

        # Add more test data for query testing
        async with db_manager.get_session_async() as session:
            # Add 1000 messages for query testing
            test_project = benchmark_runner.test_data["projects"][0]
            test_agents = benchmark_runner.test_data["agents"][:10]

            messages = []
            for i in range(1000):
                message = Message(
                    id=str(uuid.uuid4()),
                    project_id=test_project.id,
                    from_agent="orchestrator",
                    to_agents=[test_agents[i % len(test_agents)].name],
                    content=f"Query test message {i} with some content for searching",
                    message_type="direct",
                    priority="normal",
                    status="waiting",
                )
                messages.append(message)
                session.add(message)

            await session.commit()
            benchmark_runner.test_data["messages"].extend(messages)

        benchmark = PerformanceBenchmark(target_time_ms=500.0)

        # Test project query
        async def query_project_by_id():
            async with db_manager.get_session_async() as session:
                result = await session.get(Project, test_project.id)
                return result

        result = await benchmark.benchmark_async("query_project_by_id", query_project_by_id, iterations=100, warmup=10)

        assert result.avg_time < 50.0, f"Project query too slow: {result.avg_time:.2f}ms > 50ms"

        # Test agents by project query
        async def query_agents_by_project():
            async with db_manager.get_session_async() as session:
                from sqlalchemy import select

                stmt = select(Agent).where(Agent.project_id == test_project.id)
                result = await session.execute(stmt)
                return result.scalars().all()

        result = await benchmark.benchmark_async(
            "query_agents_by_project", query_agents_by_project, iterations=100, warmup=10
        )

        assert result.avg_time < 200.0, f"Agents query too slow: {result.avg_time:.2f}ms > 200ms"

        # Test messages by project query (larger dataset)
        async def query_messages_by_project():
            async with db_manager.get_session_async() as session:
                from sqlalchemy import select

                stmt = select(Message).where(Message.project_id == test_project.id).limit(50)
                result = await session.execute(stmt)
                return result.scalars().all()

        result = await benchmark.benchmark_async(
            "query_messages_by_project", query_messages_by_project, iterations=100, warmup=10
        )

        assert result.avg_time < 500.0, f"Messages query too slow: {result.avg_time:.2f}ms > 500ms"

    async def test_transaction_performance(self, benchmark_runner):
        """Test transaction performance under load"""
        db_manager = benchmark_runner.db_manager
        test_project = benchmark_runner.test_data["projects"][0]

        # Test complex transaction with multiple operations
        async def complex_transaction():
            async with db_manager.get_session_async() as session:
                # Create agent
                agent = Agent(
                    id=str(uuid.uuid4()),
                    project_id=test_project.id,
                    name=f"trans_agent_{uuid.uuid4().hex[:8]}",
                    role="worker",
                    status="active",
                )
                session.add(agent)

                # Create task for agent
                task = Task(
                    id=str(uuid.uuid4()),
                    project_id=test_project.id,
                    agent_name=agent.name,
                    description="Transaction test task",
                    status="waiting",
                    priority="normal",
                )
                session.add(task)

                # Create message
                message = Message(
                    id=str(uuid.uuid4()),
                    project_id=test_project.id,
                    from_agent="orchestrator",
                    to_agents=[agent.name],
                    content="Transaction test message",
                    message_type="direct",
                    priority="normal",
                    status="waiting",
                )
                session.add(message)

                await session.commit()
                return agent, task, message

        benchmark = PerformanceBenchmark(target_time_ms=1000.0)

        result = await benchmark.benchmark_async("complex_transaction", complex_transaction, iterations=50, warmup=5)

        assert result.avg_time < 1000.0, f"Complex transaction too slow: {result.avg_time:.2f}ms > 1s"
        assert result.success_rate > 95.0, f"Transaction success rate too low: {result.success_rate:.1f}%"

    async def test_concurrent_database_operations(self, benchmark_runner):
        """Test database performance under concurrent load"""
        db_manager = benchmark_runner.db_manager
        test_projects = benchmark_runner.test_data["projects"][:3]

        # Create multiple concurrent operations
        concurrent_operations = []

        for i in range(50):  # 50 concurrent operations
            project = test_projects[i % len(test_projects)]

            async def create_agent_and_message(proj=project, idx=i):
                async with db_manager.get_session_async() as session:
                    # Create agent
                    agent = Agent(
                        id=str(uuid.uuid4()),
                        project_id=proj.id,
                        name=f"concurrent_agent_{idx}_{uuid.uuid4().hex[:8]}",
                        role="worker",
                        status="active",
                    )
                    session.add(agent)

                    # Create message
                    message = Message(
                        id=str(uuid.uuid4()),
                        project_id=proj.id,
                        from_agent="orchestrator",
                        to_agents=[agent.name],
                        content=f"Concurrent test message {idx}",
                        message_type="direct",
                        priority="normal",
                        status="waiting",
                    )
                    session.add(message)

                    await session.commit()
                    return agent, message

            concurrent_operations.append(create_agent_and_message())

        # Execute all operations concurrently
        start_time = time.perf_counter()
        results = await asyncio.gather(*concurrent_operations, return_exceptions=True)
        total_time = (time.perf_counter() - start_time) * 1000

        # Analyze concurrent performance
        successful_ops = [r for r in results if not isinstance(r, Exception)]
        [r for r in results if isinstance(r, Exception)]
        success_rate = len(successful_ops) / len(results) * 100

        assert success_rate > 90.0, f"Concurrent operation success rate too low: {success_rate:.1f}%"
        assert total_time < 30000, f"Concurrent operations too slow: {total_time:.2f}ms > 30s"

    async def test_database_connection_pool_stress(self, benchmark_runner):
        """Test database connection pool under stress"""
        db_manager = benchmark_runner.db_manager

        # Create many short-lived database connections
        connection_tasks = []

        async def quick_database_operation(operation_id):
            async with db_manager.get_session_async() as session:
                # Quick query
                from sqlalchemy import select

                stmt = select(Project).limit(1)
                result = await session.execute(stmt)
                result.scalar()
                return f"operation_{operation_id}_complete"

        # Create 100 concurrent quick operations
        for i in range(100):
            task = quick_database_operation(i)
            connection_tasks.append(task)

        start_time = time.perf_counter()
        results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        total_time = (time.perf_counter() - start_time) * 1000

        successful_connections = [r for r in results if not isinstance(r, Exception)]
        [r for r in results if isinstance(r, Exception)]
        success_rate = len(successful_connections) / len(results) * 100

        assert success_rate > 95.0, f"Connection pool success rate too low: {success_rate:.1f}%"
        assert total_time < 20000, f"Connection pool operations too slow: {total_time:.2f}ms > 20s"

    async def test_database_memory_usage_under_load(self, benchmark_runner):
        """Test database memory usage under sustained load"""
        import psutil

        db_manager = benchmark_runner.db_manager
        process = psutil.Process()

        # Baseline memory
        baseline_memory = process.memory_info().rss / (1024 * 1024)  # MB

        # Create substantial data load
        test_project = benchmark_runner.test_data["projects"][0]

        # Add 2000 records in batches
        batch_size = 100
        total_records = 2000

        for batch_start in range(0, total_records, batch_size):
            async with db_manager.get_session_async() as session:
                for i in range(batch_size):
                    record_id = batch_start + i

                    # Create agent
                    agent = Agent(
                        id=str(uuid.uuid4()),
                        project_id=test_project.id,
                        name=f"memory_agent_{record_id}",
                        role="worker",
                        status="active",
                    )
                    session.add(agent)

                    # Create message
                    message = Message(
                        id=str(uuid.uuid4()),
                        project_id=test_project.id,
                        from_agent="orchestrator",
                        to_agents=[agent.name],
                        content=f"Memory test message {record_id} with substantial content " * 10,
                        message_type="direct",
                        priority="normal",
                        status="waiting",
                    )
                    session.add(message)

                await session.commit()

            # Check memory usage every 5 batches
            if batch_start % (batch_size * 5) == 0:
                current_memory = process.memory_info().rss / (1024 * 1024)
                current_memory - baseline_memory
                batch_start + batch_size

        final_memory = process.memory_info().rss / (1024 * 1024)
        total_memory_growth = final_memory - baseline_memory

        # Validate memory usage is reasonable
        assert total_memory_growth < 1000, (
            f"Excessive memory growth: {total_memory_growth:.1f}MB > 1GB\n"
            f"This indicates memory leaks in database operations."
        )

    async def test_database_cleanup_and_optimization(self, benchmark_runner):
        """Test database cleanup operations and optimization"""
        db_manager = benchmark_runner.db_manager

        # Create data to be cleaned up
        test_project = benchmark_runner.test_data["projects"][0]

        # Add temporary data
        temp_agents = []
        temp_messages = []

        async with db_manager.get_session_async() as session:
            for i in range(100):
                agent = Agent(
                    id=str(uuid.uuid4()),
                    project_id=test_project.id,
                    name=f"temp_agent_{i}",
                    role="worker",
                    status="database_initialized",  # Mark for cleanup
                )
                temp_agents.append(agent)
                session.add(agent)

                message = Message(
                    id=str(uuid.uuid4()),
                    project_id=test_project.id,
                    from_agent="orchestrator",
                    to_agents=[agent.name],
                    content=f"Temporary message {i}",
                    message_type="direct",
                    priority="normal",
                    status="acknowledged",  # Mark for cleanup
                )
                temp_messages.append(message)
                session.add(message)

            await session.commit()

        # Test cleanup performance
        start_time = time.perf_counter()

        async with db_manager.get_session_async() as session:
            # Delete completed agents
            from sqlalchemy import delete

            # Delete messages first (foreign key constraint)
            stmt = delete(Message).where(Message.status == "acknowledged")
            await session.execute(stmt)

            # Delete completed agents
            stmt = delete(Agent).where(Agent.status == "database_initialized")
            await session.execute(stmt)

            await session.commit()

        cleanup_time = (time.perf_counter() - start_time) * 1000

        assert cleanup_time < 5000, f"Database cleanup too slow: {cleanup_time:.2f}ms > 5s"


if __name__ == "__main__":
    # Run performance tests directly
    pytest.main([__file__, "-v", "-s", "--tb=short"])
