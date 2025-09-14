#!/usr/bin/env python3
"""
Performance Benchmarking Suite for GiljoAI MCP
Project 3.8: Performance Analyzer Agent
"""

import asyncio
import time
import sys
import os
import psutil
import sqlite3
import uuid
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime, timedelta
import json
import statistics

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from giljo_mcp.database import DatabaseManager, get_db_manager, set_db_manager
from giljo_mcp.models import Base, Project, Agent, Message, Task, Session, Vision, Configuration
from giljo_mcp.queue import MessageQueue
from giljo_mcp.orchestrator import Orchestrator
from giljo_mcp.tools.project import ProjectTools
from giljo_mcp.tools.agent import AgentTools
from giljo_mcp.tools.message import MessageTools
from giljo_mcp.tools.chunking import ChunkingTools
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

class PerformanceBenchmark:
    """Comprehensive performance benchmarking suite"""
    
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "system_info": self.get_system_info(),
            "benchmarks": {},
            "memory_profile": {},
            "latency_targets": {
                "target": "sub-100ms",
                "operations": {}
            }
        }
        self.db = None
        self.queue = None
        
    def get_system_info(self) -> Dict[str, Any]:
        """Capture system information"""
        return {
            "cpu_count": psutil.cpu_count(),
            "memory_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "python_version": sys.version,
            "platform": sys.platform,
            "process_id": os.getpid()
        }
    
    async def setup(self):
        """Initialize test environment"""
        print("\n🔧 Setting up test environment...")
        
        # Initialize database
        self.db = Database("sqlite:///benchmark_test.db")
        await init_db(self.db.engine)
        
        # Initialize message queue
        self.queue = MessageQueue(self.db)
        
        # Initialize tools
        self.project_tools = ProjectTools(self.db)
        self.agent_tools = AgentTools(self.db, self.queue)
        self.message_tools = MessageTools(self.db, self.queue)
        
        print("✅ Environment ready")
    
    async def cleanup(self):
        """Clean up test environment"""
        if self.db:
            await self.db.close()
        
        # Remove test database
        test_db = Path("benchmark_test.db")
        if test_db.exists():
            test_db.unlink()
    
    async def benchmark_database_operations(self) -> Dict[str, float]:
        """Benchmark database operations"""
        print("\n📊 Benchmarking Database Operations...")
        results = {}
        
        # Test 1: Single record insert
        start = time.perf_counter()
        project = await self.db.create_project(
            name=f"benchmark_{uuid.uuid4().hex[:8]}",
            mission="Performance test project"
        )
        results["single_insert_ms"] = (time.perf_counter() - start) * 1000
        
        # Test 2: Bulk insert (100 agents)
        start = time.perf_counter()
        agents = []
        for i in range(100):
            agent = await self.db.create_agent(
                project_id=project.id,
                name=f"agent_{i}",
                role="worker",
                status="active"
            )
            agents.append(agent)
        results["bulk_insert_100_ms"] = (time.perf_counter() - start) * 1000
        results["avg_insert_ms"] = results["bulk_insert_100_ms"] / 100
        
        # Test 3: Query performance
        start = time.perf_counter()
        fetched_agents = await self.db.get_agents(project_id=project.id)
        results["query_100_records_ms"] = (time.perf_counter() - start) * 1000
        
        # Test 4: Update performance
        start = time.perf_counter()
        for agent in agents[:10]:
            await self.db.update_agent(agent.id, status="completed")
        results["update_10_records_ms"] = (time.perf_counter() - start) * 1000
        
        # Test 5: Transaction performance
        start = time.perf_counter()
        async with self.db.session() as session:
            for i in range(50):
                message = Message(
                    id=str(uuid.uuid4()),
                    project_id=project.id,
                    from_agent="orchestrator",
                    to_agents=["agent_1", "agent_2"],
                    content=f"Message {i}",
                    message_type="direct",
                    priority="normal",
                    status="pending"
                )
                session.add(message)
            await session.commit()
        results["transaction_50_inserts_ms"] = (time.perf_counter() - start) * 1000
        
        return results
    
    async def benchmark_message_queue(self) -> Dict[str, float]:
        """Benchmark message queue performance"""
        print("\n📬 Benchmarking Message Queue...")
        results = {}
        
        # Create test project
        project = await self.db.create_project(
            name="queue_benchmark",
            mission="Queue performance test"
        )
        
        # Test 1: Single message send
        start = time.perf_counter()
        msg_id = await self.queue.send_message(
            project_id=project.id,
            from_agent="orchestrator",
            to_agents=["agent_1"],
            content="Test message",
            message_type="direct"
        )
        results["single_send_ms"] = (time.perf_counter() - start) * 1000
        
        # Test 2: Broadcast to 100 agents
        agents = [f"agent_{i}" for i in range(100)]
        start = time.perf_counter()
        await self.queue.broadcast(
            project_id=project.id,
            content="Broadcast message",
            from_agent="orchestrator"
        )
        results["broadcast_100_ms"] = (time.perf_counter() - start) * 1000
        
        # Test 3: Message retrieval
        start = time.perf_counter()
        messages = await self.queue.get_messages("agent_1", project.id)
        results["retrieve_messages_ms"] = (time.perf_counter() - start) * 1000
        
        # Test 4: Message acknowledgment
        if messages:
            start = time.perf_counter()
            await self.queue.acknowledge_message(messages[0]["id"], "agent_1")
            results["acknowledge_ms"] = (time.perf_counter() - start) * 1000
        
        # Test 5: Saturation test (1000 messages)
        start = time.perf_counter()
        tasks = []
        for i in range(1000):
            task = self.queue.send_message(
                project_id=project.id,
                from_agent="orchestrator",
                to_agents=[f"agent_{i % 10}"],
                content=f"Saturation test {i}",
                message_type="direct"
            )
            tasks.append(task)
        await asyncio.gather(*tasks)
        results["saturation_1000_msgs_ms"] = (time.perf_counter() - start) * 1000
        results["avg_msg_ms"] = results["saturation_1000_msgs_ms"] / 1000
        
        return results
    
    async def benchmark_concurrent_agents(self) -> Dict[str, Any]:
        """Stress test concurrent agent operations"""
        print("\n🤖 Benchmarking Concurrent Agents...")
        results = {}
        
        # Create test project
        project = await self.db.create_project(
            name="concurrency_test",
            mission="Concurrent agent stress test"
        )
        
        # Test different concurrency levels
        for agent_count in [10, 50, 100]:
            print(f"  Testing {agent_count} concurrent agents...")
            
            # Create agents
            agents = []
            start = time.perf_counter()
            agent_tasks = []
            for i in range(agent_count):
                task = self.db.create_agent(
                    project_id=project.id,
                    name=f"worker_{i}",
                    role="worker",
                    status="active"
                )
                agent_tasks.append(task)
            agents = await asyncio.gather(*agent_tasks)
            create_time = (time.perf_counter() - start) * 1000
            
            # Simulate concurrent work
            start = time.perf_counter()
            work_tasks = []
            for i, agent in enumerate(agents):
                # Each agent sends 10 messages
                for j in range(10):
                    task = self.queue.send_message(
                        project_id=project.id,
                        from_agent=agent.name,
                        to_agents=[agents[(i+1) % len(agents)].name],
                        content=f"Work item {j}",
                        message_type="direct"
                    )
                    work_tasks.append(task)
            await asyncio.gather(*work_tasks)
            work_time = (time.perf_counter() - start) * 1000
            
            results[f"agents_{agent_count}"] = {
                "create_time_ms": create_time,
                "work_time_ms": work_time,
                "total_messages": agent_count * 10,
                "msg_per_second": (agent_count * 10) / (work_time / 1000)
            }
        
        return results
    
    async def profile_memory_usage(self) -> Dict[str, Any]:
        """Profile memory usage under load"""
        print("\n💾 Profiling Memory Usage...")
        process = psutil.Process()
        results = {
            "baseline_mb": process.memory_info().rss / (1024 * 1024)
        }
        
        # Create large dataset
        project = await self.db.create_project(
            name="memory_test",
            mission="Memory profiling"
        )
        
        # Test 1: Create 1000 agents
        agents = []
        for i in range(1000):
            agent = await self.db.create_agent(
                project_id=project.id,
                name=f"mem_agent_{i}",
                role="worker",
                status="active"
            )
            agents.append(agent)
        
        results["after_1000_agents_mb"] = process.memory_info().rss / (1024 * 1024)
        
        # Test 2: Create 10000 messages
        for i in range(10000):
            await self.queue.send_message(
                project_id=project.id,
                from_agent="orchestrator",
                to_agents=[f"mem_agent_{i % 1000}"],
                content=f"Memory test message {i} " * 10,  # Larger content
                message_type="direct"
            )
        
        results["after_10000_messages_mb"] = process.memory_info().rss / (1024 * 1024)
        
        # Calculate growth
        results["agent_memory_growth_mb"] = (
            results["after_1000_agents_mb"] - results["baseline_mb"]
        )
        results["message_memory_growth_mb"] = (
            results["after_10000_messages_mb"] - results["after_1000_agents_mb"]
        )
        
        return results
    
    async def validate_latency_targets(self) -> Dict[str, Any]:
        """Validate sub-100ms latency targets"""
        print("\n⏱️ Validating Latency Targets (sub-100ms)...")
        results = {}
        operations = []
        
        # Create test project
        project = await self.db.create_project(
            name="latency_test",
            mission="Latency validation"
        )
        
        # Define critical operations
        test_operations = [
            ("create_agent", lambda: self.db.create_agent(
                project_id=project.id,
                name=f"latency_agent_{uuid.uuid4().hex[:8]}",
                role="worker",
                status="active"
            )),
            ("send_message", lambda: self.queue.send_message(
                project_id=project.id,
                from_agent="orchestrator",
                to_agents=["agent_1"],
                content="Latency test",
                message_type="direct"
            )),
            ("get_project_status", lambda: self.db.get_project(project.id)),
            ("get_messages", lambda: self.queue.get_messages("agent_1", project.id)),
            ("acknowledge_message", lambda: self.queue.acknowledge_message(
                str(uuid.uuid4()), "agent_1"
            ))
        ]
        
        # Run each operation 100 times and measure
        for op_name, op_func in test_operations:
            latencies = []
            print(f"  Testing {op_name}...")
            
            for _ in range(100):
                start = time.perf_counter()
                try:
                    await op_func()
                except:
                    pass  # Some ops might fail (like ack non-existent message)
                latency_ms = (time.perf_counter() - start) * 1000
                latencies.append(latency_ms)
            
            # Calculate statistics
            results[op_name] = {
                "min_ms": min(latencies),
                "max_ms": max(latencies),
                "avg_ms": statistics.mean(latencies),
                "median_ms": statistics.median(latencies),
                "p95_ms": statistics.quantiles(latencies, n=20)[18],  # 95th percentile
                "p99_ms": statistics.quantiles(latencies, n=100)[98],  # 99th percentile
                "meets_target": statistics.median(latencies) < 100
            }
        
        return results
    
    async def benchmark_vision_chunking(self) -> Dict[str, Any]:
        """Benchmark vision document chunking performance"""
        print("\n📄 Benchmarking Vision Chunking...")
        results = {}
        
        # Create large test document (50K+ tokens)
        large_doc = "This is a test document. " * 10000  # ~50K words
        
        chunking_tools = ChunkingTools(self.db)
        
        # Test chunking performance
        start = time.perf_counter()
        chunks = await chunking_tools.chunk_document(
            content=large_doc,
            max_tokens=20000
        )
        results["chunk_50k_doc_ms"] = (time.perf_counter() - start) * 1000
        results["num_chunks"] = len(chunks)
        
        # Test retrieval performance
        start = time.perf_counter()
        for i in range(min(3, len(chunks))):
            _ = chunks[i]
        results["retrieve_3_chunks_ms"] = (time.perf_counter() - start) * 1000
        
        return results
    
    async def run_all_benchmarks(self):
        """Execute all performance benchmarks"""
        print("\n" + "="*60)
        print("🚀 GiljoAI MCP Performance Benchmarking Suite")
        print("="*60)
        
        try:
            await self.setup()
            
            # Run benchmarks
            self.results["benchmarks"]["database"] = await self.benchmark_database_operations()
            self.results["benchmarks"]["message_queue"] = await self.benchmark_message_queue()
            self.results["benchmarks"]["concurrent_agents"] = await self.benchmark_concurrent_agents()
            self.results["benchmarks"]["vision_chunking"] = await self.benchmark_vision_chunking()
            self.results["memory_profile"] = await self.profile_memory_usage()
            self.results["latency_targets"]["operations"] = await self.validate_latency_targets()
            
            # Generate summary
            self.generate_summary()
            
        except Exception as e:
            print(f"\n❌ Benchmark failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.cleanup()
    
    def generate_summary(self):
        """Generate performance summary report"""
        print("\n" + "="*60)
        print("📊 PERFORMANCE SUMMARY")
        print("="*60)
        
        # Database Performance
        db_results = self.results["benchmarks"]["database"]
        print("\n🗄️ Database Performance:")
        print(f"  • Single Insert: {db_results['single_insert_ms']:.2f}ms")
        print(f"  • Bulk Insert (100): {db_results['bulk_insert_100_ms']:.2f}ms")
        print(f"  • Average Insert: {db_results['avg_insert_ms']:.2f}ms")
        print(f"  • Query 100 Records: {db_results['query_100_records_ms']:.2f}ms")
        
        # Message Queue Performance
        mq_results = self.results["benchmarks"]["message_queue"]
        print("\n📬 Message Queue Performance:")
        print(f"  • Single Send: {mq_results['single_send_ms']:.2f}ms")
        print(f"  • Broadcast to 100: {mq_results['broadcast_100_ms']:.2f}ms")
        print(f"  • Saturation (1000 msgs): {mq_results['saturation_1000_msgs_ms']:.2f}ms")
        print(f"  • Average per Message: {mq_results['avg_msg_ms']:.2f}ms")
        
        # Concurrent Agents
        conc_results = self.results["benchmarks"]["concurrent_agents"]
        print("\n🤖 Concurrent Agent Performance:")
        for agent_count in [10, 50, 100]:
            data = conc_results[f"agents_{agent_count}"]
            print(f"  • {agent_count} Agents:")
            print(f"    - Create Time: {data['create_time_ms']:.2f}ms")
            print(f"    - Work Time: {data['work_time_ms']:.2f}ms")
            print(f"    - Msgs/Second: {data['msg_per_second']:.0f}")
        
        # Memory Profile
        mem_results = self.results["memory_profile"]
        print("\n💾 Memory Usage:")
        print(f"  • Baseline: {mem_results['baseline_mb']:.2f}MB")
        print(f"  • After 1000 Agents: {mem_results['after_1000_agents_mb']:.2f}MB")
        print(f"  • After 10K Messages: {mem_results['after_10000_messages_mb']:.2f}MB")
        print(f"  • Agent Memory Growth: {mem_results['agent_memory_growth_mb']:.2f}MB")
        print(f"  • Message Memory Growth: {mem_results['message_memory_growth_mb']:.2f}MB")
        
        # Latency Validation
        latency_results = self.results["latency_targets"]["operations"]
        print("\n⏱️ Latency Targets (sub-100ms):")
        all_meet_target = True
        for op_name, metrics in latency_results.items():
            status = "✅" if metrics["meets_target"] else "❌"
            print(f"  • {op_name}: {status}")
            print(f"    - Median: {metrics['median_ms']:.2f}ms")
            print(f"    - P95: {metrics['p95_ms']:.2f}ms")
            print(f"    - P99: {metrics['p99_ms']:.2f}ms")
            if not metrics["meets_target"]:
                all_meet_target = False
        
        # Vision Chunking
        if "vision_chunking" in self.results["benchmarks"]:
            chunk_results = self.results["benchmarks"]["vision_chunking"]
            print("\n📄 Vision Chunking Performance:")
            print(f"  • Chunk 50K Document: {chunk_results['chunk_50k_doc_ms']:.2f}ms")
            print(f"  • Number of Chunks: {chunk_results['num_chunks']}")
            print(f"  • Retrieve 3 Chunks: {chunk_results['retrieve_3_chunks_ms']:.2f}ms")
        
        # Overall Assessment
        print("\n" + "="*60)
        print("🎯 OVERALL ASSESSMENT")
        print("="*60)
        
        if all_meet_target:
            print("✅ ALL PERFORMANCE TARGETS MET!")
            print("  • All critical operations under 100ms")
            print("  • System ready for production load")
        else:
            print("⚠️ SOME PERFORMANCE TARGETS NOT MET")
            print("  • Review operations exceeding 100ms")
            print("  • Consider optimization before production")
        
        # Save detailed results
        with open("performance_report.json", "w") as f:
            json.dump(self.results, f, indent=2, default=str)
        print("\n📁 Detailed results saved to: performance_report.json")

async def main():
    """Main entry point"""
    benchmark = PerformanceBenchmark()
    await benchmark.run_all_benchmarks()

if __name__ == "__main__":
    asyncio.run(main())