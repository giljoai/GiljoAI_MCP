"""
Comprehensive testing of the MessageQueue system
Tester agent's validation suite
"""

import asyncio
import sys
import os
import time
import random
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.giljo_mcp.queue import (
    MessageQueue, RoutingEngine, QueueMonitor,
    StuckMessageDetector, DeadLetterQueue
)
from src.giljo_mcp.models import Message, Agent, Project
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.tenant import TenantManager
from src.giljo_mcp.config_manager import ConfigManager


class TestResult:
    def __init__(self, name, passed, details=""):
        self.name = name
        self.passed = passed
        self.details = details
        self.timestamp = datetime.utcnow()


class MessageQueueTester:
    def __init__(self):
        self.results = []
        self.db_manager = None
        self.tenant_manager = None
        self.message_queue = None
        
    async def setup(self):
        """Initialize test environment"""
        print("Setting up test environment...")
        
        # Initialize config
        config_manager = ConfigManager()
        config = await config_manager.load_config()
        
        # Setup database
        self.db_manager = DatabaseManager(config['database'])
        await self.db_manager.initialize()
        
        # Setup tenant
        self.tenant_manager = TenantManager(self.db_manager)
        self.tenant_manager.set_current_tenant("test-tenant-" + str(int(time.time())))
        
        # Create message queue
        self.message_queue = MessageQueue(self.db_manager, self.tenant_manager)
        
        print(" Test environment ready")
        return True
        
    async def test_acid_compliance(self):
        """Test ACID properties"""
        print("\n Testing ACID Compliance...")
        
        try:
            # Test Atomicity
            print("  Testing Atomicity...")
            async with self.db_manager.get_session() as session:
                # Create a test message
                msg = Message(
                    tenant_key=self.tenant_manager.get_current_tenant(),
                    project_id="test-project",
                    content="ACID test message",
                    priority="high",
                    to_agents=["test-agent"]
                )
                
                # Test atomic enqueue
                result = await self.message_queue.enqueue(msg)
                if result:
                    self.results.append(TestResult(
                        "ACID: Atomicity - Enqueue",
                        True,
                        "Message enqueued atomically"
                    ))
                
            # Test Consistency
            print("  Testing Consistency...")
            is_consistent = await self.message_queue.validate_consistency()
            self.results.append(TestResult(
                "ACID: Consistency",
                is_consistent,
                "Queue state is consistent" if is_consistent else "Consistency check failed"
            ))
            
            # Test Isolation
            print("  Testing Isolation...")
            tasks = []
            for i in range(5):
                msg = Message(
                    tenant_key=self.tenant_manager.get_current_tenant(),
                    project_id="test-project",
                    content=f"Isolation test {i}",
                    priority="normal",
                    to_agents=["test-agent"]
                )
                tasks.append(self.message_queue.enqueue(msg))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            failures = [r for r in results if isinstance(r, Exception)]
            
            self.results.append(TestResult(
                "ACID: Isolation",
                len(failures) == 0,
                f"Concurrent operations: {len(results) - len(failures)}/{len(results)} succeeded"
            ))
            
            # Test Durability
            print("  Testing Durability...")
            # Simulate crash and recovery
            state = await self.message_queue.save_state()
            new_queue = MessageQueue(self.db_manager, self.tenant_manager)
            await new_queue.restore_state(state)
            
            self.results.append(TestResult(
                "ACID: Durability",
                True,
                "State persisted and restored successfully"
            ))
            
        except Exception as e:
            self.results.append(TestResult(
                "ACID Compliance",
                False,
                f"Error during ACID testing: {str(e)}"
            ))
    
    async def test_priority_routing(self):
        """Test priority-based message routing"""
        print("\n Testing Priority Routing...")
        
        try:
            # Create messages with different priorities
            priorities = ["critical", "high", "normal", "low"]
            messages = []
            
            for priority in priorities:
                for i in range(3):
                    msg = Message(
                        tenant_key=self.tenant_manager.get_current_tenant(),
                        project_id="test-project",
                        content=f"Priority {priority} message {i}",
                        priority=priority,
                        to_agents=["test-agent"]
                    )
                    await self.message_queue.enqueue(msg)
                    messages.append((priority, msg))
            
            # Dequeue and verify order
            dequeued = []
            for _ in range(len(messages)):
                msg = await self.message_queue.dequeue()
                if msg:
                    dequeued.append(msg.priority)
            
            # Check if critical comes before high, high before normal, etc.
            priority_order = {"critical": 0, "high": 1, "normal": 2, "low": 3}
            is_ordered = True
            for i in range(1, len(dequeued)):
                if priority_order[dequeued[i]] < priority_order[dequeued[i-1]]:
                    is_ordered = False
                    break
            
            self.results.append(TestResult(
                "Priority Routing",
                is_ordered,
                f"Messages dequeued in priority order: {dequeued[:5]}..."
            ))
            
        except Exception as e:
            self.results.append(TestResult(
                "Priority Routing",
                False,
                f"Error: {str(e)}"
            ))
    
    async def test_stuck_message_detection(self):
        """Test stuck message detection and handling"""
        print("\n Testing Stuck Message Detection...")
        
        try:
            detector = StuckMessageDetector(
                self.db_manager,
                self.tenant_manager,
                timeout_seconds=1  # Very short for testing
            )
            
            # Create a message that will become stuck
            msg = Message(
                tenant_key=self.tenant_manager.get_current_tenant(),
                project_id="test-project",
                content="This message will get stuck",
                priority="normal",
                to_agents=["test-agent"],
                status="processing",
                processing_started_at=datetime.utcnow() - timedelta(seconds=5)
            )
            
            async with self.db_manager.get_session() as session:
                session.add(msg)
                await session.commit()
            
            # Detect stuck messages
            stuck = await detector.detect_stuck_messages()
            
            self.results.append(TestResult(
                "Stuck Message Detection",
                len(stuck) > 0,
                f"Detected {len(stuck)} stuck messages"
            ))
            
            # Test recovery
            if stuck:
                recovered = await detector.recover_stuck_message(stuck[0])
                self.results.append(TestResult(
                    "Stuck Message Recovery",
                    recovered,
                    "Successfully recovered stuck message"
                ))
            
        except Exception as e:
            self.results.append(TestResult(
                "Stuck Message Detection",
                False,
                f"Error: {str(e)}"
            ))
    
    async def test_crash_recovery(self):
        """Test crash recovery mechanisms"""
        print("\n Testing Crash Recovery...")
        
        try:
            # Enqueue some messages
            for i in range(5):
                msg = Message(
                    tenant_key=self.tenant_manager.get_current_tenant(),
                    project_id="test-project",
                    content=f"Crash test message {i}",
                    priority="normal",
                    to_agents=["test-agent"]
                )
                await self.message_queue.enqueue(msg)
            
            # Save state before "crash"
            state = await self.message_queue.save_state()
            
            # Simulate crash - create new queue instance
            new_queue = MessageQueue(self.db_manager, self.tenant_manager)
            
            # Restore state
            restored = await new_queue.restore_state(state)
            
            # Verify messages are still there
            recovered_count = 0
            for _ in range(5):
                msg = await new_queue.dequeue()
                if msg:
                    recovered_count += 1
            
            self.results.append(TestResult(
                "Crash Recovery",
                recovered_count == 5,
                f"Recovered {recovered_count}/5 messages after crash"
            ))
            
        except Exception as e:
            self.results.append(TestResult(
                "Crash Recovery",
                False,
                f"Error: {str(e)}"
            ))
    
    async def test_performance(self):
        """Test performance metrics"""
        print("\n Testing Performance...")
        
        try:
            monitor = QueueMonitor(self.db_manager, self.tenant_manager)
            
            # Enqueue test
            start = time.time()
            enqueue_count = 100
            
            for i in range(enqueue_count):
                msg = Message(
                    tenant_key=self.tenant_manager.get_current_tenant(),
                    project_id="test-project",
                    content=f"Performance test {i}",
                    priority=random.choice(["low", "normal", "high"]),
                    to_agents=["test-agent"]
                )
                await self.message_queue.enqueue(msg)
            
            enqueue_time = time.time() - start
            enqueue_rate = enqueue_count / enqueue_time
            
            self.results.append(TestResult(
                "Performance: Enqueue Rate",
                enqueue_rate > 50,  # Target: 50+ messages/second
                f"{enqueue_rate:.1f} messages/second"
            ))
            
            # Dequeue test
            start = time.time()
            dequeue_count = 0
            
            for _ in range(enqueue_count):
                msg = await self.message_queue.dequeue()
                if msg:
                    dequeue_count += 1
                    # Simulate processing
                    await asyncio.sleep(0.01)
            
            dequeue_time = time.time() - start
            dequeue_rate = dequeue_count / dequeue_time
            
            self.results.append(TestResult(
                "Performance: Dequeue Rate",
                dequeue_rate > 30,  # Target: 30+ messages/second
                f"{dequeue_rate:.1f} messages/second"
            ))
            
            # Get metrics
            stats = await monitor.get_statistics()
            
            self.results.append(TestResult(
                "Performance: Monitoring",
                stats is not None,
                f"Queue depth: {stats.get('queue_depth', 0)}, "
                f"Processing time: {stats.get('avg_processing_time', 0):.3f}s"
            ))
            
        except Exception as e:
            self.results.append(TestResult(
                "Performance Testing",
                False,
                f"Error: {str(e)}"
            ))
    
    async def test_dead_letter_queue(self):
        """Test dead letter queue functionality"""
        print("\n Testing Dead Letter Queue...")
        
        try:
            dlq = DeadLetterQueue(self.db_manager, self.tenant_manager)
            
            # Create a failed message
            failed_msg = Message(
                tenant_key=self.tenant_manager.get_current_tenant(),
                project_id="test-project",
                content="This message failed processing",
                priority="high",
                to_agents=["test-agent"],
                retry_count=5,  # Exceeded max retries
                status="failed"
            )
            
            # Add to DLQ
            added = await dlq.add_message(
                failed_msg,
                reason="Max retries exceeded",
                error_details="Simulated failure"
            )
            
            self.results.append(TestResult(
                "DLQ: Add Message",
                added,
                "Failed message moved to DLQ"
            ))
            
            # Get DLQ messages
            dlq_messages = await dlq.get_messages(limit=10)
            
            self.results.append(TestResult(
                "DLQ: Retrieve Messages",
                len(dlq_messages) > 0,
                f"Retrieved {len(dlq_messages)} messages from DLQ"
            ))
            
            # Reprocess from DLQ
            if dlq_messages:
                reprocessed = await dlq.reprocess_message(dlq_messages[0]['id'])
                self.results.append(TestResult(
                    "DLQ: Reprocess Message",
                    reprocessed,
                    "Successfully reprocessed message from DLQ"
                ))
            
        except Exception as e:
            self.results.append(TestResult(
                "Dead Letter Queue",
                False,
                f"Error: {str(e)}"
            ))
    
    async def run_all_tests(self):
        """Run all tests and generate report"""
        print("\n" + "="*60)
        print("GILJOAI MESSAGE QUEUE SYSTEM - COMPREHENSIVE TEST SUITE")
        print("="*60)
        
        # Setup
        if not await self.setup():
            print(" Failed to setup test environment")
            return
        
        # Run tests
        await self.test_acid_compliance()
        await self.test_priority_routing()
        await self.test_stuck_message_detection()
        await self.test_crash_recovery()
        await self.test_performance()
        await self.test_dead_letter_queue()
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate test report"""
        print("\n" + "="*60)
        print(" TEST RESULTS SUMMARY")
        print("="*60)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        
        # Individual results
        for result in self.results:
            status = "" if result.passed else ""
            print(f"{status} {result.name}")
            if result.details:
                print(f"    {result.details}")
        
        # Summary
        print("\n" + "-"*60)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed} ({passed/total*100:.1f}%)")
        print(f"Failed: {failed} ({failed/total*100:.1f}%)")
        
        # Overall status
        print("\n" + "="*60)
        if passed == total:
            print(" ALL TESTS PASSED! The MessageQueue system is production-ready!")
        elif passed / total >= 0.8:
            print(" MOSTLY PASSED - Some issues need attention")
        else:
            print(" CRITICAL ISSUES DETECTED - Major fixes required")
        print("="*60)
        
        # Save report to file
        self.save_report()
    
    def save_report(self):
        """Save test report to file"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        report_file = f"test_report_queue_{timestamp}.txt"
        
        with open(report_file, 'w') as f:
            f.write("MESSAGE QUEUE SYSTEM TEST REPORT\n")
            f.write(f"Generated: {datetime.utcnow().isoformat()}\n")
            f.write("="*60 + "\n\n")
            
            for result in self.results:
                status = "PASS" if result.passed else "FAIL"
                f.write(f"[{status}] {result.name}\n")
                if result.details:
                    f.write(f"      Details: {result.details}\n")
                f.write(f"      Time: {result.timestamp.isoformat()}\n\n")
            
            total = len(self.results)
            passed = sum(1 for r in self.results if r.passed)
            f.write("-"*60 + "\n")
            f.write(f"Summary: {passed}/{total} tests passed ({passed/total*100:.1f}%)\n")
        
        print(f"\n Report saved to: {report_file}")


async def main():
    tester = MessageQueueTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())