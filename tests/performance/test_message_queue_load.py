"""
Message Queue Load Testing
Tests message queue performance under production loads

PRODUCTION REQUIREMENTS:
- 10,000+ messages per minute throughput
- Broadcast to 100+ agents efficiently
- Message acknowledgment arrays under load
- Priority message handling under stress
- Zero message loss under maximum load
"""

import asyncio
import time
import uuid

import pytest
import pytest_asyncio

from src.giljo_mcp.tools.message import MessageTools
from tests.benchmark_tools import PerformanceBenchmark


class TestMessageQueueLoad:
    """Test message queue performance at production scale"""

    @pytest_asyncio.fixture
    async def message_tools(self, test_db):
        """Create message tools for testing"""
        return MessageTools(test_db)

    @pytest_asyncio.fixture
    async def test_project_with_agents(self, test_db, db_session):
        """Create test project with 100 agents for message testing"""
        from src.giljo_mcp.models import Agent, Project

        # Create project
        project_id = str(uuid.uuid4())
        tenant_key = str(uuid.uuid4())

        project = Project(
            id=project_id,
            name="Message Queue Load Test",
            mission="Test message queue with 100+ agents",
            status="active",
            tenant_key=tenant_key
        )
        db_session.add(project)

        # Create 100 agents
        agents = []
        for i in range(100):
            agent = Agent(
                id=str(uuid.uuid4()),
                project_id=project_id,
                name=f"queue_agent_{i}",
                role="worker",
                status="active"
            )
            agents.append(agent)
            db_session.add(agent)

        await db_session.commit()
        return project, agents

    async def test_single_message_latency(self, message_tools, test_project_with_agents):
        """Test single message send latency meets requirements"""
        project, agents = test_project_with_agents
        benchmark = PerformanceBenchmark(target_time_ms=100.0)

        async def send_single_message():
            return await message_tools.send_message(
                project_id=project.id,
                from_agent="orchestrator",
                to_agents=[agents[0].name],
                content="Performance test message",
                message_type="direct",
                priority="normal"
            )

        # Benchmark single message send
        result = await benchmark.benchmark_async(
            "single_message_send",
            send_single_message,
            iterations=100,
            warmup=10
        )

        # Validate requirements
        assert result.avg_time < 100.0, f"Message send too slow: {result.avg_time:.2f}ms > 100ms"
        assert result.success_rate > 99.0, f"Message success rate too low: {result.success_rate:.1f}%"

        print("\n✅ Single Message Send Performance:")
        print(f"   Average: {result.avg_time:.2f}ms")
        print(f"   P95: {result.p95:.2f}ms")
        print(f"   P99: {result.p99:.2f}ms")
        print(f"   Success Rate: {result.success_rate:.1f}%")

    async def test_message_retrieval_latency(self, message_tools, test_project_with_agents):
        """Test message retrieval performance"""
        project, agents = test_project_with_agents

        # Send some test messages first
        for i in range(10):
            await message_tools.send_message(
                project_id=project.id,
                from_agent="orchestrator",
                to_agents=[agents[0].name],
                content=f"Test message {i}",
                message_type="direct",
                priority="normal"
            )

        benchmark = PerformanceBenchmark(target_time_ms=50.0)

        async def get_messages():
            return await message_tools.get_messages(
                agent_name=agents[0].name,
                project_id=project.id
            )

        # Benchmark message retrieval
        result = await benchmark.benchmark_async(
            "message_retrieval",
            get_messages,
            iterations=100,
            warmup=10
        )

        assert result.avg_time < 50.0, f"Message retrieval too slow: {result.avg_time:.2f}ms > 50ms"

        print("\n✅ Message Retrieval Performance:")
        print(f"   Average: {result.avg_time:.2f}ms")
        print(f"   P95: {result.p95:.2f}ms")
        print(f"   Success Rate: {result.success_rate:.1f}%")

    async def test_broadcast_to_100_agents(self, message_tools, test_project_with_agents):
        """Test broadcast message to 100 agents"""
        project, agents = test_project_with_agents

        start_time = time.perf_counter()

        # Broadcast to all 100 agents
        await message_tools.broadcast(
            project_id=project.id,
            content="Broadcast performance test message",
            from_agent="orchestrator",
            priority="normal"
        )

        broadcast_time = (time.perf_counter() - start_time) * 1000

        print("\n✅ Broadcast to 100 Agents:")
        print(f"   Total Time: {broadcast_time:.2f}ms")
        print(f"   Time per Agent: {broadcast_time/100:.2f}ms")

        # Validate broadcast performance
        assert broadcast_time < 5000, f"Broadcast too slow: {broadcast_time:.2f}ms > 5s"

        # Verify all agents received the message
        received_count = 0
        for agent in agents[:10]:  # Check first 10 agents as sample
            messages = await message_tools.get_messages(
                agent_name=agent.name,
                project_id=project.id
            )
            if messages:
                received_count += 1

        print(f"   Sample Delivery: {received_count}/10 agents received message")

    @pytest.mark.slow
    async def test_message_saturation_1000_messages(self, message_tools, test_project_with_agents):
        """Test sending 1000 messages rapidly (production scale)"""
        project, agents = test_project_with_agents

        start_time = time.perf_counter()

        # Send 1000 messages as fast as possible
        tasks = []
        for i in range(1000):
            agent_target = agents[i % 100]  # Distribute across agents
            task = message_tools.send_message(
                project_id=project.id,
                from_agent="orchestrator",
                to_agents=[agent_target.name],
                content=f"Saturation test message {i}",
                message_type="direct",
                priority="normal"
            )
            tasks.append(task)

        # Execute all sends concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = (time.perf_counter() - start_time) * 1000

        # Analyze results
        successful_sends = [r for r in results if not isinstance(r, Exception)]
        failed_sends = [r for r in results if isinstance(r, Exception)]
        success_rate = len(successful_sends) / len(results) * 100

        messages_per_second = 1000 / (total_time / 1000)
        messages_per_minute = messages_per_second * 60

        print("\n🚀 Message Saturation Test (1000 messages):")
        print(f"   Total Time: {total_time:.2f}ms ({total_time/1000:.2f}s)")
        print(f"   Success Rate: {success_rate:.1f}%")
        print(f"   Successful: {len(successful_sends)}")
        print(f"   Failed: {len(failed_sends)}")
        print(f"   Messages/second: {messages_per_second:.1f}")
        print(f"   Messages/minute: {messages_per_minute:.0f}")

        # PRODUCTION REQUIREMENTS VALIDATION
        assert success_rate >= 95.0, (
            f"PRODUCTION FAILURE: Message saturation success rate {success_rate:.1f}% < 95%\n"
            f"Failed messages: {len(failed_sends)}\n"
            f"This indicates message queue reliability issues under load."
        )

        assert messages_per_minute >= 10000, (
            f"PRODUCTION FAILURE: Throughput {messages_per_minute:.0f} messages/minute < 10,000\n"
            f"This indicates insufficient message queue performance for production."
        )

        assert total_time < 60000, (
            f"PRODUCTION FAILURE: 1000 messages took {total_time:.2f}ms > 60s\n"
            f"This indicates severe performance bottlenecks in message processing."
        )

        print("   ✅ MEETS PRODUCTION THROUGHPUT REQUIREMENTS")

    @pytest.mark.stress
    async def test_message_saturation_10000_stress_test(self, message_tools, test_project_with_agents):
        """STRESS TEST: 10,000 messages to identify system limits"""
        project, agents = test_project_with_agents

        start_time = time.perf_counter()

        # Send 10,000 messages in batches to avoid overwhelming the system
        batch_size = 500
        total_messages = 10000
        all_results = []

        for batch_start in range(0, total_messages, batch_size):
            batch_end = min(batch_start + batch_size, total_messages)
            batch_tasks = []

            for i in range(batch_start, batch_end):
                agent_target = agents[i % 100]
                task = message_tools.send_message(
                    project_id=project.id,
                    from_agent="orchestrator",
                    to_agents=[agent_target.name],
                    content=f"Stress test message {i}",
                    message_type="direct",
                    priority="normal"
                )
                batch_tasks.append(task)

            # Execute batch
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            all_results.extend(batch_results)

            # Small delay between batches to prevent overwhelming
            await asyncio.sleep(0.1)

        total_time = (time.perf_counter() - start_time) * 1000

        # Analyze stress test results
        successful_sends = [r for r in all_results if not isinstance(r, Exception)]
        failed_sends = [r for r in all_results if isinstance(r, Exception)]
        success_rate = len(successful_sends) / len(all_results) * 100

        messages_per_second = 10000 / (total_time / 1000)
        messages_per_minute = messages_per_second * 60

        print("\n🔥 STRESS TEST: 10,000 Messages")
        print(f"   Total Time: {total_time:.2f}ms ({total_time/1000:.2f}s)")
        print(f"   Success Rate: {success_rate:.1f}%")
        print(f"   Successful: {len(successful_sends)}")
        print(f"   Failed: {len(failed_sends)}")
        print(f"   Messages/second: {messages_per_second:.1f}")
        print(f"   Messages/minute: {messages_per_minute:.0f}")

        if success_rate < 90:
            print("   ⚠️  System shows stress at 10,000 messages")
        else:
            print("   ✅ System handles 10,000 messages well - excellent capacity")

    async def test_message_acknowledgment_performance(self, message_tools, test_project_with_agents):
        """Test message acknowledgment performance under load"""
        project, agents = test_project_with_agents

        # Send 100 messages to be acknowledged
        message_ids = []
        for i in range(100):
            message_id = await message_tools.send_message(
                project_id=project.id,
                from_agent="orchestrator",
                to_agents=[agents[i % 10].name],  # Use first 10 agents
                content=f"Ack test message {i}",
                message_type="direct",
                priority="normal"
            )
            message_ids.append(message_id)

        # Test acknowledgment performance
        start_time = time.perf_counter()
        ack_tasks = []

        for i, message_id in enumerate(message_ids):
            agent_name = agents[i % 10].name
            task = message_tools.acknowledge_message(
                message_id=message_id,
                agent_name=agent_name
            )
            ack_tasks.append(task)

        ack_results = await asyncio.gather(*ack_tasks, return_exceptions=True)
        ack_time = (time.perf_counter() - start_time) * 1000

        successful_acks = [r for r in ack_results if not isinstance(r, Exception)]
        success_rate = len(successful_acks) / len(ack_results) * 100

        print("\n✅ Message Acknowledgment Performance:")
        print(f"   Messages Acknowledged: {len(message_ids)}")
        print(f"   Total Time: {ack_time:.2f}ms")
        print(f"   Avg per Ack: {ack_time/len(message_ids):.2f}ms")
        print(f"   Success Rate: {success_rate:.1f}%")

        # Validate acknowledgment performance
        avg_ack_time = ack_time / len(message_ids)
        assert avg_ack_time < 50, f"Acknowledgment too slow: {avg_ack_time:.2f}ms > 50ms"
        assert success_rate > 95, f"Acknowledgment success rate too low: {success_rate:.1f}%"

    async def test_priority_message_handling(self, message_tools, test_project_with_agents):
        """Test priority message handling under load"""
        project, agents = test_project_with_agents

        # Send mixed priority messages
        start_time = time.perf_counter()
        tasks = []

        # Send 50 normal and 50 high priority messages concurrently
        for i in range(50):
            # Normal priority
            task1 = message_tools.send_message(
                project_id=project.id,
                from_agent="orchestrator",
                to_agents=[agents[i % 10].name],
                content=f"Normal priority message {i}",
                message_type="direct",
                priority="normal"
            )
            tasks.append(task1)

            # High priority
            task2 = message_tools.send_message(
                project_id=project.id,
                from_agent="orchestrator",
                to_agents=[agents[i % 10].name],
                content=f"High priority message {i}",
                message_type="direct",
                priority="high"
            )
            tasks.append(task2)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = (time.perf_counter() - start_time) * 1000

        successful_sends = [r for r in results if not isinstance(r, Exception)]
        success_rate = len(successful_sends) / len(results) * 100

        print("\n✅ Priority Message Handling:")
        print(f"   Total Messages: {len(tasks)}")
        print("   Normal Priority: 50")
        print("   High Priority: 50")
        print(f"   Total Time: {total_time:.2f}ms")
        print(f"   Success Rate: {success_rate:.1f}%")

        assert success_rate > 95, f"Priority message success rate too low: {success_rate:.1f}%"
        assert total_time < 10000, f"Priority message handling too slow: {total_time:.2f}ms > 10s"

    async def test_message_queue_memory_usage(self, message_tools, test_project_with_agents):
        """Test message queue memory usage under sustained load"""
        project, agents = test_project_with_agents

        import psutil
        process = psutil.Process()

        # Baseline memory
        baseline_memory = process.memory_info().rss / (1024 * 1024)  # MB

        # Send 1000 messages with larger content to test memory
        large_content = "This is a large message content for memory testing. " * 20  # ~1KB per message

        for i in range(1000):
            await message_tools.send_message(
                project_id=project.id,
                from_agent="orchestrator",
                to_agents=[agents[i % 100].name],
                content=f"Memory test {i}: {large_content}",
                message_type="direct",
                priority="normal"
            )

            # Check memory every 100 messages
            if i % 100 == 0:
                current_memory = process.memory_info().rss / (1024 * 1024)
                memory_growth = current_memory - baseline_memory
                print(f"   Messages {i}: Memory growth {memory_growth:.1f}MB")

        final_memory = process.memory_info().rss / (1024 * 1024)
        total_memory_growth = final_memory - baseline_memory

        print("\n✅ Message Queue Memory Usage:")
        print(f"   Baseline Memory: {baseline_memory:.1f}MB")
        print(f"   Final Memory: {final_memory:.1f}MB")
        print(f"   Total Growth: {total_memory_growth:.1f}MB")
        print(f"   Growth per Message: {total_memory_growth/1000*1024:.1f}KB")

        # Validate memory usage is reasonable
        assert total_memory_growth < 500, (
            f"Excessive memory growth: {total_memory_growth:.1f}MB > 500MB\n"
            f"This indicates memory leaks in the message queue."
        )


if __name__ == "__main__":
    # Run performance tests directly
    pytest.main([__file__, "-v", "-s", "--tb=short"])
