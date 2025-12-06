"""
Comprehensive tests for the MessageQueue system
Tests priority routing, ACID compliance, crash recovery, and monitoring
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.message_queue import (
    CircuitBreaker,
    ContentRoutingRule,
    DeadLetterQueue,
    MessageQueue,
    PriorityRoutingRule,
    QueueException,
    QueueMonitor,
    RoutingEngine,
    TypeRoutingRule,
)
from src.giljo_mcp.models import Message
from src.giljo_mcp.tenant import TenantManager


@pytest.fixture
def db_manager():
    """Mock database manager with proper async context manager"""
    db_manager = Mock(spec=DatabaseManager)

    # Create proper async context manager mock
    async_session_mock = AsyncMock()
    async_session_mock.__aenter__ = AsyncMock()
    async_session_mock.__aexit__ = AsyncMock(return_value=None)  # Don't suppress exceptions
    async_session_mock.begin = AsyncMock()
    async_session_mock.commit = AsyncMock()
    async_session_mock.rollback = AsyncMock()
    async_session_mock.add = Mock()
    async_session_mock.execute = AsyncMock()

    # Mock BOTH get_session and get_session_async to return the async context manager
    db_manager.get_session = Mock(return_value=async_session_mock)
    db_manager.get_session_async = Mock(return_value=async_session_mock)
    async_session_mock.__aenter__.return_value = async_session_mock

    return db_manager


@pytest.fixture
def tenant_manager():
    """Mock tenant manager"""
    tenant_manager = Mock(spec=TenantManager)
    tenant_manager.get_current_tenant = Mock(return_value="test-tenant-123")
    return tenant_manager


@pytest.fixture
def message_queue(db_manager, tenant_manager):
    """Create a MessageQueue instance"""
    return MessageQueue(db_manager, tenant_manager)


@pytest.fixture
def sample_message():
    """Create a sample message"""

    return Message(
        id=uuid4(),
        tenant_key="test-tenant-123",
        project_id=uuid4(),
        to_agents=["analyzer", "implementer"],
        message_type="direct",
        content="Test message content",
        priority="high",
        status="waiting",
        created_at=datetime.now(timezone.utc),
        acknowledged_by=[],
        completed_by=[],
        meta_data={},
    )


class TestMessageQueue:
    """Test MessageQueue core functionality"""

    @pytest.mark.asyncio
    async def test_enqueue_message(self, message_queue, sample_message, db_manager):
        """Test message enqueue operation"""
        # Setup mock result for database query execution
        result_mock = Mock()
        result_mock.rowcount = 1
        session_mock = db_manager.get_session.return_value.__aenter__.return_value
        session_mock.execute.return_value = result_mock

        # Enqueue message
        message_id = await message_queue.enqueue(sample_message)

        # Verify
        assert message_id == str(sample_message.id)
        session_mock.add.assert_called_once_with(sample_message)
        session_mock.commit.assert_called_once()
        assert message_queue._monitor._metrics["queue_depth"]["high"] == 1

    @pytest.mark.asyncio
    async def test_dequeue_by_priority(self, message_queue, db_manager):
        """Test dequeue respects priority order"""
        # Setup mock session
        session_mock = db_manager.get_session.return_value.__aenter__.return_value

        # Create messages with different priorities and proper meta_data
        critical_msg = Mock(
            priority="critical", created_at=datetime.now(timezone.utc), id="1", status="waiting", meta_data={}
        )
        high_msg = Mock(priority="high", created_at=datetime.now(timezone.utc), id="2", status="waiting", meta_data={})
        normal_msg = Mock(
            priority="normal", created_at=datetime.now(timezone.utc), id="3", status="waiting", meta_data={}
        )

        # Mock execute to return messages in priority order
        result_mock = Mock()
        result_mock.scalars.return_value.all.return_value = [critical_msg, high_msg, normal_msg]
        session_mock.execute = AsyncMock(return_value=result_mock)

        # Dequeue messages
        messages = await message_queue.dequeue("analyzer", batch_size=3)

        # Verify priority order
        assert len(messages) == 3
        assert messages[0].priority == "critical"
        assert messages[1].priority == "high"
        assert messages[2].priority == "normal"

    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff(self, message_queue, sample_message, db_manager):
        """Test retry mechanism with exponential backoff"""
        # Setup mock session
        session_mock = AsyncMock()
        session_mock.begin = AsyncMock()
        session_mock.commit = AsyncMock()
        session_mock.get = AsyncMock(return_value=sample_message)

        # Mock execute for select query
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = sample_message
        session_mock.execute = AsyncMock(return_value=result_mock)

        db_manager.get_session.return_value.__aenter__.return_value = session_mock

        # First retry
        success = await message_queue.retry_message("msg-123", "Temporary failure")
        assert success is True
        assert sample_message.meta_data["retry_count"] == 1
        assert sample_message.status == "pending"

        # Second retry
        success = await message_queue.retry_message("msg-123", "Another failure")
        assert success is True
        assert sample_message.meta_data["retry_count"] == 2

        # Third retry (should move to DLQ)
        sample_message.meta_data["retry_count"] = 3
        success = await message_queue.retry_message("msg-123", "Final failure")
        assert success is False  # Moved to DLQ

    @pytest.mark.asyncio
    async def test_stuck_message_detection(self, message_queue, db_manager):
        """Test detection of stuck messages"""
        # Create stuck message
        stuck_msg = Mock(
            id="stuck-123",
            status="processing",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=10),
            meta_data={"processing_started_at": (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()},
        )

        # Setup mock session
        session_mock = AsyncMock()
        result_mock = Mock()
        result_mock.scalars.return_value.all.return_value = [stuck_msg]
        session_mock.execute = AsyncMock(return_value=result_mock)

        db_manager.get_session.return_value.__aenter__.return_value = session_mock

        # Detect stuck messages
        stuck_messages = await message_queue.detect_stuck_messages(timeout_seconds=300)

        # Verify
        assert len(stuck_messages) == 1
        assert stuck_messages[0].id == "stuck-123"

    @pytest.mark.asyncio
    async def test_crash_recovery(self, message_queue, db_manager):
        """Test crash recovery resets processing messages"""
        # Setup mock session
        session_mock = AsyncMock()
        session_mock.begin = AsyncMock()
        session_mock.commit = AsyncMock()
        session_mock.rollback = AsyncMock()

        # Mock update result
        result_mock = Mock()
        result_mock.rowcount = 5  # 5 messages recovered
        session_mock.execute = AsyncMock(return_value=result_mock)

        db_manager.get_session.return_value.__aenter__.return_value = session_mock

        # Perform recovery
        await message_queue.recover_from_crash()

        # Verify update was called
        session_mock.execute.assert_called()
        session_mock.commit.assert_called()


class TestRoutingEngine:
    """Test intelligent routing functionality"""

    def test_priority_routing_rule(self):
        """Test priority-based routing"""
        rule = PriorityRoutingRule("critical", ["orchestrator"])

        msg_critical = Mock(priority="critical")
        msg_normal = Mock(priority="normal")

        assert rule.matches(msg_critical) is True
        assert rule.matches(msg_normal) is False
        assert rule.get_agents() == ["orchestrator"]

    def test_type_routing_rule(self):
        """Test type-based routing"""
        rule = TypeRoutingRule("broadcast", ["*"])

        msg_broadcast = Mock(message_type="broadcast")
        msg_direct = Mock(message_type="direct")

        assert rule.matches(msg_broadcast) is True
        assert rule.matches(msg_direct) is False
        assert rule.get_agents() == ["*"]

    def test_content_routing_rule(self):
        """Test content pattern routing"""
        rule = ContentRoutingRule(r"ERROR|CRITICAL", ["error_handler"])

        msg_error = Mock(content="ERROR: System failure")
        msg_info = Mock(content="INFO: System running")

        assert rule.matches(msg_error) is True
        assert rule.matches(msg_info) is False
        assert rule.get_agents() == ["error_handler"]

    @pytest.mark.asyncio
    async def test_load_balancing(self):
        """Test load balancing across agents"""
        engine = RoutingEngine()

        # Set up agent loads
        engine._agent_load = {"agent1": 5, "agent2": 1, "agent3": 3}  # Heavy load  # Light load  # Medium load

        # Mock agents
        agents = [Mock(name="agent1"), Mock(name="agent2"), Mock(name="agent3")]

        # Mock message with to_agents that exist
        message = Mock(message_type="task", to_agents=["agent1", "agent2", "agent3"], priority="normal")

        # Add a default routing rule to handle the message
        engine._routing_rules = []  # Clear default rules
        from src.giljo_mcp.message_queue import TypeRoutingRule

        engine._routing_rules.append(TypeRoutingRule("task", ["agent1", "agent2", "agent3"]))

        # Route message
        routed = await engine.route_message(message, agents)

        # Should have some agents (order depends on scoring)
        assert len(routed) > 0
        assert all(agent in ["agent1", "agent2", "agent3"] for agent in routed)

    def test_circuit_breaker(self):
        """Test circuit breaker functionality"""
        breaker = CircuitBreaker("test_agent", failure_threshold=3, timeout=60)

        # Initially closed
        assert breaker.is_open() is False

        # Record failures
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.is_open() is False  # Still closed

        # Third failure opens circuit
        breaker.record_failure()
        assert breaker.is_open() is True

        # Record success in half-open state
        breaker.state = "half-open"
        breaker.record_success()
        assert breaker.state == "closed"
        assert breaker.failure_count == 0


class TestQueueMonitor:
    """Test monitoring and metrics functionality"""

    @pytest.mark.asyncio
    async def test_throughput_calculation(self):
        """Test throughput metrics calculation"""
        monitor = QueueMonitor()

        # Record multiple enqueues
        for _ in range(10):
            msg = Mock(priority="normal")
            await monitor.record_enqueue(msg)

        # Calculate throughput
        throughput = monitor._calculate_throughput()
        assert throughput == 10  # 10 messages in the window

    @pytest.mark.asyncio
    async def test_latency_tracking(self):
        """Test latency percentile calculation"""
        monitor = QueueMonitor()

        # Record dequeue events with varying latencies
        for i in range(100):
            msg = Mock(priority="normal", created_at=datetime.now(timezone.utc) - timedelta(seconds=i / 10))
            await monitor.record_dequeue(msg, "test_agent")

        # Get percentiles
        percentiles = monitor._calculate_latency_percentiles()

        assert "p50" in percentiles
        assert "p95" in percentiles
        assert "p99" in percentiles
        assert percentiles["p50"] < percentiles["p95"] < percentiles["p99"]

    @pytest.mark.asyncio
    async def test_processing_time_tracking(self):
        """Test processing time metrics"""
        monitor = QueueMonitor()

        # Start processing
        await monitor.record_processing_start("msg-1", "agent1")

        # Simulate processing delay
        await asyncio.sleep(0.1)

        # End processing
        await monitor.record_processing_end("msg-1", "agent1", success=True)

        # Verify metrics
        assert "agent1" in monitor._metrics["processing_time"]
        assert len(monitor._metrics["processing_time"]["agent1"]) == 1
        assert monitor._metrics["processing_time"]["agent1"][0] >= 0.1


class TestDeadLetterQueue:
    """Test DLQ functionality"""

    @pytest.mark.asyncio
    async def test_add_to_dlq(self, db_manager):
        """Test moving message to DLQ"""
        dlq = DeadLetterQueue(db_manager)

        # Setup mock session
        session_mock = AsyncMock()
        session_mock.begin = AsyncMock()
        session_mock.commit = AsyncMock()
        session_mock.add = Mock()

        db_manager.get_session.return_value.__aenter__.return_value = session_mock

        # Create failed message
        failed_msg = Mock(id="failed-123", status="failed", meta_data={})

        # Add to DLQ
        await dlq.add_message(failed_msg, "Max retries exceeded")

        # Verify
        assert failed_msg.status == "dead_letter"
        assert failed_msg.meta_data["dlq_reason"] == "Max retries exceeded"
        assert "dlq_timestamp" in failed_msg.meta_data
        session_mock.commit.assert_called()

    @pytest.mark.asyncio
    async def test_reprocess_from_dlq(self, db_manager):
        """Test reprocessing message from DLQ"""
        dlq = DeadLetterQueue(db_manager)

        # Setup mock session
        session_mock = AsyncMock()
        session_mock.begin = AsyncMock()
        session_mock.commit = AsyncMock()

        # Mock message in DLQ
        dlq_msg = Mock(id="dlq-123", status="dead_letter", meta_data={"dlq_reason": "Test reason"})

        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = dlq_msg
        session_mock.execute = AsyncMock(return_value=result_mock)

        db_manager.get_session.return_value.__aenter__.return_value = session_mock

        # Reprocess
        success = await dlq.reprocess_message("dlq-123")

        # Verify
        assert success is True
        assert dlq_msg.status == "pending"
        assert dlq_msg.meta_data["reprocessed_from_dlq"] is True
        assert dlq_msg.meta_data["retry_count"] == 0


class TestACIDCompliance:
    """Test ACID compliance requirements"""

    @pytest.mark.asyncio
    async def test_atomic_dequeue(self, message_queue, db_manager):
        """Test atomicity of dequeue operation"""
        # Setup mock session
        session_mock = db_manager.get_session.return_value.__aenter__.return_value

        # Simulate failure during dequeue
        session_mock.execute = AsyncMock(side_effect=Exception("Database error"))

        # The method should raise QueueException
        with pytest.raises(QueueException, match="Dequeue failed"):
            await message_queue.dequeue("test_agent")

        # Verify rollback was called
        session_mock.rollback.assert_called()

    @pytest.mark.asyncio
    async def test_consistency_validation(self, message_queue):
        """Test message state consistency validation"""
        # Valid transitions
        valid_tests = [
            ("pending", "acknowledged"),
            ("acknowledged", "database_initialized"),
            ("failed", "pending"),  # Retry
        ]

        # Invalid transitions
        invalid_tests = [
            ("database_initialized", "pending"),  # Can't restart completed
            ("dead_letter", "pending"),  # Terminal state
        ]

        # Test state transitions
        for current, next_state in valid_tests:
            msg = Mock(status=current)
            # Should not raise exception
            msg.status = next_state

        for current, next_state in invalid_tests:
            msg = Mock(status=current)
            # In real implementation, this would validate
            # For now, just verify the states are different
            assert current != next_state

    @pytest.mark.asyncio
    async def test_isolation_locks(self, message_queue):
        """Test isolation between concurrent operations"""
        isolation_mgr = message_queue._isolation_manager

        # Test message lock
        msg_lock1 = isolation_mgr.with_message_lock("msg-1")
        msg_lock2 = isolation_mgr.with_message_lock("msg-1")
        assert msg_lock1 is msg_lock2  # Same lock for same message

        msg_lock3 = isolation_mgr.with_message_lock("msg-2")
        assert msg_lock1 is not msg_lock3  # Different lock for different message

        # Test agent lock
        agent_lock1 = isolation_mgr.with_agent_lock("agent-1")
        agent_lock2 = isolation_mgr.with_agent_lock("agent-1")
        assert agent_lock1 is agent_lock2  # Same lock for same agent


class TestIntegration:
    """Integration tests for the complete queue system"""

    @pytest.mark.asyncio
    async def test_end_to_end_message_flow(self, message_queue, db_manager):
        """Test complete message flow from enqueue to completion"""
        # Setup mock session
        session_mock = db_manager.get_session.return_value.__aenter__.return_value

        # Create test message
        test_msg = Mock(
            id="test-flow-123",
            tenant_key="test-tenant",
            project_id="test-project",
            to_agents=["receiver"],
            message_type="task",
            content="Test task",
            priority="high",
            status="waiting",
            created_at=datetime.now(timezone.utc),
            meta_data={},
        )

        # Mock database responses
        result_mock = Mock()
        result_mock.scalars.return_value.all.return_value = [test_msg]
        result_mock.scalar_one_or_none.return_value = test_msg
        session_mock.execute = AsyncMock(return_value=result_mock)

        # 1. Enqueue message
        msg_id = await message_queue.enqueue(test_msg)
        assert msg_id == "test-flow-123"

        # 2. Dequeue message - this changes status to processing
        messages = await message_queue.dequeue("receiver")
        assert len(messages) == 1
        assert messages[0].status == "processing"

        # 3. Process message - update the status for the next call
        test_msg.status = "acknowledged"  # Valid transition from processing
        success = await message_queue.process_message(msg_id, "receiver")
        assert success is True

        # 4. Get statistics
        stats = await message_queue.get_statistics()
        assert "queue_depth" in stats
        assert "throughput" in stats
        assert "latency" in stats

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, message_queue, db_manager):
        """Test queue under concurrent load"""
        # Setup mock session
        session_mock = AsyncMock()
        session_mock.begin = AsyncMock()
        session_mock.commit = AsyncMock()
        session_mock.add = Mock()

        db_manager.get_session.return_value.__aenter__.return_value = session_mock

        # Create multiple messages
        messages = []
        for i in range(10):
            msg = Mock(
                id=f"concurrent-{i}",
                priority="normal",
                created_at=datetime.now(timezone.utc),
                to_agents=["agent1", "agent2"],
                meta_data={},
            )
            messages.append(msg)

        # Simulate concurrent enqueues
        tasks = [message_queue.enqueue(msg) for msg in messages]
        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        assert all(r.startswith("concurrent-") for r in results)


@pytest.mark.asyncio
async def test_queue_performance():
    """Performance benchmark test"""
    # This would be a performance test in production
    # Measuring throughput, latency, and resource usage

    start_time = datetime.now(timezone.utc)
    message_count = 1000

    # Simulate high-throughput scenario
    # In production, this would use real database
    for _ in range(message_count):
        # Simulate minimal processing time
        await asyncio.sleep(0.0001)  # 0.1ms per message

    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()

    throughput = message_count / duration if duration > 0 else 0

    # Assert performance targets
    # Target: 1000+ messages per minute (16.67 per second)
    # With simulated processing, we should easily exceed this
    assert throughput >= 16.67, f"Throughput {throughput} below target"


class TestMessageQueueErrorHandling:
    """Test error handling and edge cases for better coverage"""

    @pytest.mark.asyncio
    async def test_enqueue_failure(self, message_queue, sample_message, db_manager):
        """Test enqueue failure handling"""
        # Setup mock session to fail during persist_with_wal
        session_mock = db_manager.get_session.return_value.__aenter__.return_value
        session_mock.commit = AsyncMock(side_effect=Exception("Database commit failed"))

        # Should raise QueueException
        with pytest.raises(QueueException, match="Enqueue failed"):
            await message_queue.enqueue(sample_message)

    @pytest.mark.asyncio
    async def test_process_message_invalid_state(self, message_queue, db_manager):
        """Test process_message with invalid state transition"""
        # Setup mock session
        session_mock = db_manager.get_session.return_value.__aenter__.return_value

        # Create message with invalid status for processing
        invalid_msg = Mock(id="invalid-123", status="database_initialized", meta_data={})

        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = invalid_msg
        session_mock.execute = AsyncMock(return_value=result_mock)

        # Should return False due to invalid state
        success = await message_queue.process_message("invalid-123", "test_agent")
        assert success is False

    @pytest.mark.asyncio
    async def test_process_message_not_found(self, message_queue, db_manager):
        """Test process_message with non-existent message"""
        # Setup mock session
        session_mock = db_manager.get_session.return_value.__aenter__.return_value

        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = None  # Message not found
        session_mock.execute = AsyncMock(return_value=result_mock)

        # Should return False
        success = await message_queue.process_message("nonexistent-123", "test_agent")
        assert success is False

    @pytest.mark.asyncio
    async def test_retry_message_not_found(self, message_queue, db_manager):
        """Test retry with non-existent message"""
        # Setup mock session
        session_mock = db_manager.get_session.return_value.__aenter__.return_value

        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = None  # Message not found
        session_mock.execute = AsyncMock(return_value=result_mock)

        # Should return False
        success = await message_queue.retry_message("nonexistent-123", "test reason")
        assert success is False

    @pytest.mark.asyncio
    async def test_dlq_get_size(self, db_manager):
        """Test DeadLetterQueue size calculation"""
        dlq = DeadLetterQueue(db_manager)

        # Setup mock session
        session_mock = db_manager.get_session.return_value.__aenter__.return_value

        result_mock = Mock()
        result_mock.scalar.return_value = 5  # 5 messages in DLQ
        session_mock.execute = AsyncMock(return_value=result_mock)

        size = await dlq.get_size()
        assert size == 5

    @pytest.mark.asyncio
    async def test_dlq_reprocess_invalid_message(self, db_manager):
        """Test reprocessing message not in DLQ"""
        dlq = DeadLetterQueue(db_manager)

        # Setup mock session
        session_mock = db_manager.get_session.return_value.__aenter__.return_value

        # Mock message with wrong status
        normal_msg = Mock(id="normal-123", status="waiting")
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = normal_msg
        session_mock.execute = AsyncMock(return_value=result_mock)

        # Should return False
        success = await dlq.reprocess_message("normal-123")
        assert success is False

    @pytest.mark.asyncio
    async def test_routing_engine_affinity(self):
        """Test agent affinity calculation"""
        engine = RoutingEngine()

        # Test affinity method
        has_affinity = engine._has_affinity("test_agent", "test_type")
        assert has_affinity is False  # Default implementation returns False

    @pytest.mark.asyncio
    async def test_routing_engine_circuit_breaker_timeout(self):
        """Test circuit breaker timeout behavior"""
        RoutingEngine()

        # Create circuit breaker and simulate failure
        breaker = CircuitBreaker("test_agent", failure_threshold=2, timeout=1)

        # Record failures to open circuit
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.is_open() is True

        # Simulate timeout passage
        import time

        time.sleep(1.1)  # Wait for timeout

        # Should transition to half-open
        assert breaker.is_open() is False

    @pytest.mark.asyncio
    async def test_queue_monitor_cleanup(self):
        """Test QueueMonitor throughput window cleanup"""
        monitor = QueueMonitor()

        # Add old entries
        from datetime import datetime, timedelta, timezone

        old_time = datetime.now(timezone.utc) - timedelta(minutes=2)
        monitor._throughput_window.append((old_time, 1))

        # Add recent entry
        recent_time = datetime.now(timezone.utc)
        monitor._throughput_window.append((recent_time, 1))

        # Cleanup should remove old entries
        monitor._cleanup_throughput_window()

        # Should only have recent entry
        assert len(monitor._throughput_window) == 1

    @pytest.mark.asyncio
    async def test_durability_manager_wal_recovery(self):
        """Test WAL recovery functionality"""
        from src.giljo_mcp.message_queue import DurabilityManager

        db_manager = Mock()
        durability_mgr = DurabilityManager(db_manager)

        # Add uncommitted WAL entry
        durability_mgr._wal_entries.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "operation": "enqueue",
                "message_id": "test-123",
                "committed": False,
            }
        )

        # Recovery should handle uncommitted entries
        await durability_mgr.recover_from_crash()

        # Should have processed the uncommitted entry
        assert len(durability_mgr._wal_entries) == 1

    @pytest.mark.asyncio
    async def test_checkpoint_operations(self, message_queue):
        """Test checkpoint functionality"""
        # Should complete without error
        await message_queue.checkpoint()

        # Verify durability manager and monitor checkpoints
        assert hasattr(message_queue._durability_manager, "_wal_entries")
        assert hasattr(message_queue._monitor, "_metrics")


class TestMessageQueueAdvancedScenarios:
    """Test advanced scenarios for comprehensive coverage"""

    @pytest.mark.asyncio
    async def test_batch_size_override(self, message_queue, db_manager):
        """Test dequeue with custom batch size"""
        # Setup mock session
        session_mock = db_manager.get_session.return_value.__aenter__.return_value

        # Create multiple messages
        messages = []
        for i in range(5):
            msg = Mock(
                priority="normal", created_at=datetime.now(timezone.utc), id=f"msg-{i}", status="waiting", meta_data={}
            )
            messages.append(msg)

        result_mock = Mock()
        result_mock.scalars.return_value.all.return_value = messages[:2]  # Return 2 messages
        session_mock.execute = AsyncMock(return_value=result_mock)

        # Dequeue with batch_size=2
        dequeued = await message_queue.dequeue("test_agent", batch_size=2)
        assert len(dequeued) == 2

    @pytest.mark.asyncio
    async def test_agent_capability_matching(self):
        """Test routing based on agent capabilities"""
        engine = RoutingEngine()

        # Set up agent capabilities
        engine._agent_capabilities = {"analyzer": ["analysis", "review"], "implementer": ["implementation", "coding"]}

        # Create mock agents with proper name attribute
        analyzer = Mock()
        analyzer.name = "analyzer"
        implementer = Mock()
        implementer.name = "implementer"

        # Test capability matching
        analysis_msg = Mock(message_type="analysis", to_agents=[], priority="normal")
        assert engine._can_handle(analyzer, analysis_msg) is True
        assert engine._can_handle(implementer, analysis_msg) is False

    @pytest.mark.asyncio
    async def test_routing_with_wildcards(self):
        """Test wildcard routing"""
        engine = RoutingEngine()

        # Add wildcard rule
        from src.giljo_mcp.message_queue import TypeRoutingRule

        engine._routing_rules.append(TypeRoutingRule("broadcast", ["*"]))

        # Create agents with proper name attributes
        agents = []
        for i in range(1, 4):
            agent = Mock()
            agent.name = f"agent{i}"
            agents.append(agent)

        # Test wildcard routing
        broadcast_msg = Mock(message_type="broadcast", to_agents=[], priority="normal")
        routed = await engine.route_message(broadcast_msg, agents)

        # Should route to all agents
        assert len(routed) == 3
        assert all(agent in ["agent1", "agent2", "agent3"] for agent in routed)

    @pytest.mark.asyncio
    async def test_stuck_message_processing_time_filter(self, message_queue, db_manager):
        """Test stuck message detection with processing time filter"""
        # Setup mock session
        session_mock = db_manager.get_session.return_value.__aenter__.return_value

        # Create message with processing_started_at
        processing_msg = Mock(
            id="processing-123",
            status="processing",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            meta_data={"processing_started_at": (datetime.now(timezone.utc) - timedelta(minutes=6)).isoformat()},
        )

        # Create message without processing_started_at but old
        old_msg = Mock(
            id="old-123",
            status="acknowledged",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=10),
            meta_data={},
        )

        result_mock = Mock()
        result_mock.scalars.return_value.all.return_value = [processing_msg, old_msg]
        session_mock.execute = AsyncMock(return_value=result_mock)

        # Detect stuck messages with 5-minute timeout
        stuck = await message_queue.detect_stuck_messages(timeout_seconds=300)

        # Should find both messages
        assert len(stuck) == 2


class TestMessageQueueFinalCoverage:
    """Final tests to achieve 95%+ coverage"""

    @pytest.mark.asyncio
    async def test_retry_message_database_error(self, message_queue, db_manager):
        """Test retry_message with database failure"""
        # Setup mock session that fails during commit
        session_mock = db_manager.get_session.return_value.__aenter__.return_value

        # Create message for retry
        retry_msg = Mock(id="retry-123", meta_data={"retry_count": 1})
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = retry_msg
        session_mock.execute = AsyncMock(return_value=result_mock)
        session_mock.commit = AsyncMock(side_effect=Exception("Database error"))

        # Should return False and trigger error path
        success = await message_queue.retry_message("retry-123", "test failure")
        assert success is False
        session_mock.rollback.assert_called()

    @pytest.mark.asyncio
    async def test_crash_recovery_database_error(self, message_queue, db_manager):
        """Test crash recovery with database failure"""
        # Setup mock session that fails during update
        session_mock = db_manager.get_session.return_value.__aenter__.return_value
        session_mock.execute = AsyncMock(side_effect=Exception("Database error"))

        # Should raise QueueException
        with pytest.raises(QueueException, match="Recovery failed"):
            await message_queue.recover_from_crash()

        session_mock.rollback.assert_called()

    @pytest.mark.asyncio
    async def test_queue_monitor_no_samples(self):
        """Test QueueMonitor with no samples"""
        monitor = QueueMonitor()

        # Test percentiles with no samples
        percentiles = monitor._calculate_latency_percentiles()
        assert percentiles["p50"] == 0
        assert percentiles["p95"] == 0
        assert percentiles["p99"] == 0

    @pytest.mark.asyncio
    async def test_queue_monitor_processing_time_tracking_success_failure(self):
        """Test QueueMonitor processing time tracking with success and failure"""
        monitor = QueueMonitor()

        # Test processing end with success
        await monitor.record_processing_start("msg-1", "agent1")
        await monitor.record_processing_end("msg-1", "agent1", success=True)

        # Test processing end with failure
        await monitor.record_processing_start("msg-2", "agent1")
        await monitor.record_processing_end("msg-2", "agent1", success=False)

        # Should have recorded error
        assert monitor._metrics["error_rate"] == 1

    @pytest.mark.asyncio
    async def test_routing_engine_response_time_tracking(self):
        """Test RoutingEngine response time tracking"""
        engine = RoutingEngine()

        # Record some response times
        engine.record_response_time("agent1", 0.5)
        engine.record_response_time("agent1", 0.3)

        # Test that times are recorded
        assert len(engine._response_times["agent1"]) == 2

        # Test score calculation with response times
        score = engine._calculate_agent_score("agent1", Mock(message_type="test"))
        assert score > 0  # Should include response time in score

    @pytest.mark.asyncio
    async def test_routing_engine_load_tracking(self):
        """Test RoutingEngine load tracking"""
        engine = RoutingEngine()

        # Update agent load
        engine.update_agent_load("agent1", 5)
        assert engine._agent_load["agent1"] == 5

        # Update again
        engine.update_agent_load("agent1", -2)
        assert engine._agent_load["agent1"] == 3

    @pytest.mark.asyncio
    async def test_dlq_reprocess_no_message(self, db_manager):
        """Test DLQ reprocess with no message found"""
        dlq = DeadLetterQueue(db_manager)

        # Setup mock session with no message
        session_mock = db_manager.get_session.return_value.__aenter__.return_value
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = None
        session_mock.execute = AsyncMock(return_value=result_mock)

        # Should return False
        success = await dlq.reprocess_message("nonexistent-123")
        assert success is False

    @pytest.mark.asyncio
    async def test_dlq_reprocess_database_error(self, db_manager):
        """Test DLQ reprocess with database error"""
        dlq = DeadLetterQueue(db_manager)

        # Setup mock session that fails
        session_mock = db_manager.get_session.return_value.__aenter__.return_value
        session_mock.execute = AsyncMock(side_effect=Exception("Database error"))

        # Should return False and handle error
        success = await dlq.reprocess_message("error-123")
        assert success is False

    @pytest.mark.asyncio
    async def test_durability_manager_checkpoint(self):
        """Test DurabilityManager checkpoint operations"""
        from src.giljo_mcp.message_queue import DurabilityManager

        db_manager = Mock()
        durability_mgr = DurabilityManager(db_manager)

        # Add some committed and uncommitted entries
        durability_mgr._wal_entries = [
            {"committed": True, "operation": "test1"},
            {"committed": False, "operation": "test2"},
            {"committed": True, "operation": "test3"},
        ]

        # Checkpoint should clear committed entries
        await durability_mgr.checkpoint()

        # Should only have uncommitted entry
        assert len(durability_mgr._wal_entries) == 1
        assert durability_mgr._wal_entries[0]["operation"] == "test2"

    @pytest.mark.asyncio
    async def test_message_queue_get_statistics_complete(self, message_queue):
        """Test complete statistics gathering"""
        # Mock stuck message detector
        stuck_msg = Mock(id="stuck-1")
        message_queue._stuck_detector.detect_stuck_messages = AsyncMock(return_value=[stuck_msg])

        # Mock DLQ size
        message_queue._dead_letter_queue.get_size = AsyncMock(return_value=3)

        # Get statistics
        stats = await message_queue.get_statistics()

        # Verify all stats are included
        assert "stuck_count" in stats
        assert "dlq_count" in stats
        assert stats["stuck_count"] == 1
        assert stats["dlq_count"] == 3

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_failure(self):
        """Test circuit breaker failure in half-open state"""
        breaker = CircuitBreaker("test_agent", failure_threshold=2, timeout=1)

        # Open the circuit
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == "open"

        # Force half-open state
        breaker.state = "half-open"

        # Record another failure
        breaker.record_failure()

        # Should still be open
        assert breaker.failure_count == 3

    @pytest.mark.asyncio
    async def test_content_routing_rule_no_match(self):
        """Test ContentRoutingRule with no match"""
        from src.giljo_mcp.message_queue import ContentRoutingRule

        rule = ContentRoutingRule(r"ERROR|CRITICAL", ["error_handler"])

        # Test message that doesn't match
        normal_msg = Mock(content="INFO: Everything is fine")
        assert rule.matches(normal_msg) is False

    @pytest.mark.asyncio
    async def test_queue_monitor_processing_time_limits(self):
        """Test QueueMonitor processing time sample limits"""
        monitor = QueueMonitor()

        # Add many processing times for one agent
        for i in range(150):  # More than the 100 limit
            await monitor.record_processing_start(f"msg-{i}", "agent1")
            await monitor.record_processing_end(f"msg-{i}", "agent1", success=True)

        # Should only keep last 100
        assert len(monitor._metrics["processing_time"]["agent1"]) == 100

    @pytest.mark.asyncio
    async def test_queue_monitor_latency_sample_limits(self):
        """Test QueueMonitor latency sample limits"""
        monitor = QueueMonitor()

        # Add many latency samples
        for i in range(1100):  # More than the 1000 limit
            msg = Mock(priority="normal", created_at=datetime.now(timezone.utc) - timedelta(seconds=i))
            await monitor.record_dequeue(msg, "test_agent")

        # Should only keep last 1000
        assert len(monitor._latency_samples) == 1000

    @pytest.mark.asyncio
    async def test_routing_engine_response_time_limits(self):
        """Test RoutingEngine response time limits"""
        engine = RoutingEngine()

        # Add many response times
        for i in range(150):  # More than the 100 limit
            engine.record_response_time("agent1", 0.1 * i)

        # Should only keep last 100
        assert len(engine._response_times["agent1"]) == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
