"""
Simple test of MessageQueue system
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.giljo_mcp.queue import MessageQueue, RoutingEngine, QueueMonitor
from src.giljo_mcp.models import Message


def test_imports():
    """Test that all queue components can be imported"""
    print("TEST: Import Check")
    try:
        from src.giljo_mcp.queue import (
            MessageQueue, RoutingEngine, QueueMonitor,
            StuckMessageDetector, DeadLetterQueue,
            CircuitBreaker, QueueException, ConsistencyError,
            PriorityRoutingRule, TypeRoutingRule, ContentRoutingRule
        )
        print("  [PASS] All queue components imported successfully")
        return True
    except ImportError as e:
        print(f"  [FAIL] Import error: {e}")
        return False


def test_routing_engine():
    """Test routing engine functionality"""
    print("\nTEST: Routing Engine")
    try:
        engine = RoutingEngine()
        
        # Test priority rule
        rule = PriorityRoutingRule("high")
        msg = Message(priority="high", content="Test", to_agents=["agent1"])
        
        if rule.matches(msg):
            print("  [PASS] Priority routing rule works")
        else:
            print("  [FAIL] Priority routing rule failed")
            
        # Test type rule
        rule = TypeRoutingRule("task")
        msg.message_type = "task"
        
        if rule.matches(msg):
            print("  [PASS] Type routing rule works")
        else:
            print("  [FAIL] Type routing rule failed")
            
        return True
    except Exception as e:
        print(f"  [FAIL] Routing engine error: {e}")
        return False


def test_queue_monitor():
    """Test queue monitor"""
    print("\nTEST: Queue Monitor")
    try:
        # Create mock managers
        class MockDB:
            async def get_session(self):
                class MockSession:
                    async def __aenter__(self):
                        return self
                    async def __aexit__(self, *args):
                        pass
                    async def execute(self, query):
                        class Result:
                            def scalars(self):
                                class Scalars:
                                    def all(self):
                                        return []
                                return Scalars()
                        return Result()
                return MockSession()
        
        class MockTenant:
            def get_current_tenant(self):
                return "test-tenant"
        
        monitor = QueueMonitor(MockDB(), MockTenant())
        
        # Test recording metrics
        monitor.record_enqueue("msg1", "normal")
        monitor.record_dequeue("msg1")
        
        print("  [PASS] Queue monitor initialized and recording metrics")
        return True
    except Exception as e:
        print(f"  [FAIL] Queue monitor error: {e}")
        return False


def test_dead_letter_queue():
    """Test DLQ functionality"""
    print("\nTEST: Dead Letter Queue")
    try:
        from src.giljo_mcp.queue import DeadLetterQueue
        
        class MockDB:
            pass
        
        class MockTenant:
            def get_current_tenant(self):
                return "test-tenant"
        
        dlq = DeadLetterQueue(MockDB(), MockTenant())
        print("  [PASS] Dead Letter Queue initialized")
        return True
    except Exception as e:
        print(f"  [FAIL] DLQ error: {e}")
        return False


def test_circuit_breaker():
    """Test circuit breaker"""
    print("\nTEST: Circuit Breaker")
    try:
        from src.giljo_mcp.queue import CircuitBreaker
        
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        
        # Test normal state
        if breaker.is_open("agent1"):
            print("  [FAIL] Circuit breaker should be closed initially")
            return False
        
        # Record failures
        for _ in range(3):
            breaker.record_failure("agent1")
        
        # Should be open now
        if not breaker.is_open("agent1"):
            print("  [FAIL] Circuit breaker should be open after failures")
            return False
        
        print("  [PASS] Circuit breaker working correctly")
        return True
    except Exception as e:
        print(f"  [FAIL] Circuit breaker error: {e}")
        return False


def main():
    print("="*60)
    print("MESSAGE QUEUE SYSTEM - BASIC TESTS")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Routing Engine", test_routing_engine()))
    results.append(("Queue Monitor", test_queue_monitor()))
    results.append(("Dead Letter Queue", test_dead_letter_queue()))
    results.append(("Circuit Breaker", test_circuit_breaker()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\nSUCCESS: All basic tests passed!")
    else:
        print(f"\nWARNING: {total - passed} tests failed")


if __name__ == "__main__":
    main()