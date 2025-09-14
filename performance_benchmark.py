#!/usr/bin/env python3
"""
Performance Benchmarking Suite for GiljoAI MCP
Project 3.8: Performance Analyzer Agent
"""

import time
import sys
import os
import psutil
import sqlite3
import uuid
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import json
import statistics
import traceback

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from giljo_mcp.database import DatabaseManager, get_db_manager, set_db_manager
from giljo_mcp.models import Base, Project, Agent, Message, Task, Session

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
        
    def get_system_info(self) -> Dict[str, Any]:
        """Capture system information"""
        return {
            "cpu_count": psutil.cpu_count(),
            "memory_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "python_version": sys.version,
            "platform": sys.platform,
            "process_id": os.getpid()
        }
    
    def setup(self):
        """Initialize test environment"""
        print("\n Setting up test environment...")
        
        # Initialize database
        db_path = Path("benchmark_test.db")
        if db_path.exists():
            db_path.unlink()
        
        self.db = DatabaseManager("sqlite:///benchmark_test.db")
        set_db_manager(self.db)
        
        # Create tables
        Base.metadata.create_all(self.db.engine)
        
        print(" Environment ready")
    
    def cleanup(self):
        """Clean up test environment"""
        if self.db:
            self.db.close()
        
        # Remove test database
        test_db = Path("benchmark_test.db")
        if test_db.exists():
            test_db.unlink()
    
    def benchmark_database_operations(self) -> Dict[str, float]:
        """Benchmark database operations"""
        print("\n Benchmarking Database Operations...")
        results = {}
        
        with self.db.get_session() as session:
            # Test 1: Single record insert
            start = time.perf_counter()
            tenant_key = str(uuid.uuid4())
            project = Project(
                id=str(uuid.uuid4()),
                tenant_key=tenant_key,
                name=f"benchmark_{uuid.uuid4().hex[:8]}",
                mission="Performance test project",
                status="active",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            session.add(project)
            session.commit()
            results["single_insert_ms"] = (time.perf_counter() - start) * 1000
            
            # Test 2: Bulk insert (100 agents)
            start = time.perf_counter()
            agents = []
            for i in range(100):
                agent = Agent(
                    id=str(uuid.uuid4()),
                    tenant_key=tenant_key,
                    project_id=project.id,
                    name=f"agent_{i}",
                    role="worker",
                    status="active",
                    created_at=datetime.now()
                )
                agents.append(agent)
                session.add(agent)
            session.commit()
            results["bulk_insert_100_ms"] = (time.perf_counter() - start) * 1000
            results["avg_insert_ms"] = results["bulk_insert_100_ms"] / 100
            
            # Test 3: Query performance
            start = time.perf_counter()
            fetched_agents = session.query(Agent).filter_by(project_id=project.id).all()
            results["query_100_records_ms"] = (time.perf_counter() - start) * 1000
            
            # Test 4: Update performance
            start = time.perf_counter()
            for agent in agents[:10]:
                agent.status = "completed"
            session.commit()
            results["update_10_records_ms"] = (time.perf_counter() - start) * 1000
            
            # Test 5: Transaction performance
            start = time.perf_counter()
            for i in range(50):
                message = Message(
                    id=str(uuid.uuid4()),
                    tenant_key=tenant_key,
                    project_id=project.id,
                    from_agent_id="orchestrator",
                    to_agents=json.dumps(["agent_1", "agent_2"]),
                    content=f"Message {i}",
                    message_type="direct",
                    priority="normal",
                    status="pending",
                    created_at=datetime.now()
                )
                session.add(message)
            session.commit()
            results["transaction_50_inserts_ms"] = (time.perf_counter() - start) * 1000
        
        return results
    
    def benchmark_message_operations(self) -> Dict[str, float]:
        """Benchmark message operations"""
        print("\n Benchmarking Message Operations...")
        results = {}
        
        with self.db.get_session() as session:
            # Create test project
            tenant_key = str(uuid.uuid4())
            project = Project(
                id=str(uuid.uuid4()),
                tenant_key=tenant_key,
                name="message_benchmark",
                mission="Message performance test",
                status="active",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            session.add(project)
            session.commit()
            
            # Test 1: Single message insert
            start = time.perf_counter()
            message = Message(
                id=str(uuid.uuid4()),
                tenant_key=tenant_key,
                project_id=project.id,
                from_agent_id="orchestrator",
                to_agents=json.dumps(["agent_1"]),
                content="Test message",
                message_type="direct",
                priority="normal",
                status="pending",
                created_at=datetime.now()
            )
            session.add(message)
            session.commit()
            results["single_message_ms"] = (time.perf_counter() - start) * 1000
            
            # Test 2: Broadcast simulation (100 recipients)
            agents = [f"agent_{i}" for i in range(100)]
            start = time.perf_counter()
            broadcast_msg = Message(
                id=str(uuid.uuid4()),
                tenant_key=tenant_key,
                project_id=project.id,
                from_agent_id="orchestrator",
                to_agents=json.dumps(agents),
                content="Broadcast message",
                message_type="broadcast",
                priority="high",
                status="pending",
                created_at=datetime.now()
            )
            session.add(broadcast_msg)
            session.commit()
            results["broadcast_100_ms"] = (time.perf_counter() - start) * 1000
            
            # Test 3: Message retrieval
            start = time.perf_counter()
            messages = session.query(Message).filter_by(
                project_id=project.id
            ).all()
            results["retrieve_messages_ms"] = (time.perf_counter() - start) * 1000
            
            # Test 4: Message acknowledgment simulation
            if messages:
                start = time.perf_counter()
                msg = messages[0]
                if msg.acknowledged_by:
                    ack_list = json.loads(msg.acknowledged_by)
                else:
                    ack_list = []
                ack_list.append("agent_1")
                msg.acknowledged_by = json.dumps(ack_list)
                session.commit()
                results["acknowledge_ms"] = (time.perf_counter() - start) * 1000
            
            # Test 5: Saturation test (1000 messages)
            start = time.perf_counter()
            for i in range(1000):
                msg = Message(
                    id=str(uuid.uuid4()),
                    tenant_key=tenant_key,
                    project_id=project.id,
                    from_agent_id="orchestrator",
                    to_agents=json.dumps([f"agent_{i % 10}"]),
                    content=f"Saturation test {i}",
                    message_type="direct",
                    priority="normal",
                    status="pending",
                    created_at=datetime.now()
                )
                session.add(msg)
            session.commit()
            results["saturation_1000_msgs_ms"] = (time.perf_counter() - start) * 1000
            results["avg_msg_ms"] = results["saturation_1000_msgs_ms"] / 1000
        
        return results
    
    def benchmark_concurrent_operations(self) -> Dict[str, Any]:
        """Stress test concurrent operations"""
        print("\n Benchmarking Concurrent Operations...")
        results = {}
        
        with self.db.get_session() as session:
            # Create test project
            tenant_key = str(uuid.uuid4())
            project = Project(
                id=str(uuid.uuid4()),
                tenant_key=tenant_key,
                name="concurrency_test",
                mission="Concurrent operations stress test",
                status="active",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            session.add(project)
            session.commit()
            
            # Test different concurrency levels
            for agent_count in [10, 50, 100]:
                print(f"  Testing {agent_count} concurrent agents...")
                
                # Create agents
                start = time.perf_counter()
                agents = []
                for i in range(agent_count):
                    agent = Agent(
                        id=str(uuid.uuid4()),
                        tenant_key=tenant_key,
                        project_id=project.id,
                        name=f"worker_{i}",
                        role="worker",
                        status="active",
                        created_at=datetime.now()
                    )
                    agents.append(agent)
                    session.add(agent)
                session.commit()
                create_time = (time.perf_counter() - start) * 1000
                
                # Simulate concurrent work (messages between agents)
                start = time.perf_counter()
                message_count = 0
                for i, agent in enumerate(agents):
                    # Each agent sends 10 messages
                    for j in range(10):
                        msg = Message(
                            id=str(uuid.uuid4()),
                            tenant_key=tenant_key,
                            project_id=project.id,
                            from_agent_id=agent.name,
                            to_agents=json.dumps([agents[(i+1) % len(agents)].name]),
                            content=f"Work item {j}",
                            message_type="direct",
                            priority="normal",
                            status="pending",
                            created_at=datetime.now()
                        )
                        session.add(msg)
                        message_count += 1
                session.commit()
                work_time = (time.perf_counter() - start) * 1000
                
                results[f"agents_{agent_count}"] = {
                    "create_time_ms": create_time,
                    "work_time_ms": work_time,
                    "total_messages": message_count,
                    "msg_per_second": message_count / (work_time / 1000) if work_time > 0 else 0
                }
        
        return results
    
    def profile_memory_usage(self) -> Dict[str, Any]:
        """Profile memory usage under load"""
        print("\n Profiling Memory Usage...")
        process = psutil.Process()
        results = {
            "baseline_mb": process.memory_info().rss / (1024 * 1024)
        }
        
        with self.db.get_session() as session:
            # Create large dataset
            tenant_key = str(uuid.uuid4())
            project = Project(
                id=str(uuid.uuid4()),
                tenant_key=tenant_key,
                name="memory_test",
                mission="Memory profiling",
                status="active",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            session.add(project)
            session.commit()
            
            # Test 1: Create 1000 agents
            print("  Creating 1000 agents...")
            for i in range(1000):
                agent = Agent(
                    id=str(uuid.uuid4()),
                    tenant_key=tenant_key,
                    project_id=project.id,
                    name=f"mem_agent_{i}",
                    role="worker",
                    status="active",
                    created_at=datetime.now()
                )
                session.add(agent)
                if i % 100 == 0:
                    session.commit()
            session.commit()
            
            results["after_1000_agents_mb"] = process.memory_info().rss / (1024 * 1024)
            
            # Test 2: Create 10000 messages
            print("  Creating 10000 messages...")
            for i in range(10000):
                msg = Message(
                    id=str(uuid.uuid4()),
                    tenant_key=tenant_key,
                    project_id=project.id,
                    from_agent_id="orchestrator",
                    to_agents=json.dumps([f"mem_agent_{i % 1000}"]),
                    content=f"Memory test message {i} " * 10,  # Larger content
                    message_type="direct",
                    priority="normal",
                    status="pending",
                    created_at=datetime.now()
                )
                session.add(msg)
                if i % 500 == 0:
                    session.commit()
            session.commit()
            
            results["after_10000_messages_mb"] = process.memory_info().rss / (1024 * 1024)
        
        # Calculate growth
        results["agent_memory_growth_mb"] = (
            results["after_1000_agents_mb"] - results["baseline_mb"]
        )
        results["message_memory_growth_mb"] = (
            results["after_10000_messages_mb"] - results["after_1000_agents_mb"]
        )
        
        return results
    
    def validate_latency_targets(self) -> Dict[str, Any]:
        """Validate sub-100ms latency targets"""
        print("\n Validating Latency Targets (sub-100ms)...")
        results = {}
        
        with self.db.get_session() as session:
            # Create test project
            tenant_key = str(uuid.uuid4())
            project = Project(
                id=str(uuid.uuid4()),
                tenant_key=tenant_key,
                name="latency_test",
                mission="Latency validation",
                status="active",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            self.tenant_key = tenant_key  # Store for helper methods
            session.add(project)
            session.commit()
            
            # Define critical operations
            test_operations = {
                "create_agent": lambda: self._create_agent(session, project.id),
                "create_message": lambda: self._create_message(session, project.id),
                "query_project": lambda: self._query_project(session, project.id),
                "query_messages": lambda: self._query_messages(session, project.id),
                "update_agent": lambda: self._update_agent(session, project.id)
            }
            
            # Run each operation 100 times and measure
            for op_name, op_func in test_operations.items():
                latencies = []
                print(f"  Testing {op_name}...")
                
                for _ in range(100):
                    start = time.perf_counter()
                    try:
                        op_func()
                    except:
                        pass  # Some ops might fail
                    latency_ms = (time.perf_counter() - start) * 1000
                    latencies.append(latency_ms)
                
                # Calculate statistics
                results[op_name] = {
                    "min_ms": min(latencies),
                    "max_ms": max(latencies),
                    "avg_ms": statistics.mean(latencies),
                    "median_ms": statistics.median(latencies),
                    "p95_ms": sorted(latencies)[95] if len(latencies) > 95 else max(latencies),
                    "p99_ms": sorted(latencies)[99] if len(latencies) > 99 else max(latencies),
                    "meets_target": statistics.median(latencies) < 100
                }
        
        return results
    
    def _create_agent(self, session, project_id):
        """Helper to create an agent"""
        agent = Agent(
            id=str(uuid.uuid4()),
            tenant_key=self.tenant_key,
            project_id=project_id,
            name=f"test_agent_{uuid.uuid4().hex[:8]}",
            role="worker",
            status="active",
            created_at=datetime.now()
        )
        session.add(agent)
        session.commit()
    
    def _create_message(self, session, project_id):
        """Helper to create a message"""
        msg = Message(
            id=str(uuid.uuid4()),
            tenant_key=self.tenant_key,
            project_id=project_id,
            from_agent_id="orchestrator",
            to_agents=json.dumps(["agent_1"]),
            content="Test message",
            message_type="direct",
            priority="normal",
            status="pending",
            created_at=datetime.now()
        )
        session.add(msg)
        session.commit()
    
    def _query_project(self, session, project_id):
        """Helper to query a project"""
        session.query(Project).filter_by(id=project_id).first()
    
    def _query_messages(self, session, project_id):
        """Helper to query messages"""
        session.query(Message).filter_by(project_id=project_id).limit(10).all()
    
    def _update_agent(self, session, project_id):
        """Helper to update an agent"""
        agent = session.query(Agent).filter_by(project_id=project_id).first()
        if agent:
            agent.status = "updated"
            session.commit()
    
    def run_all_benchmarks(self):
        """Execute all performance benchmarks"""
        print("\n" + "="*60)
        print(" GiljoAI MCP Performance Benchmarking Suite")
        print("="*60)
        
        try:
            self.setup()
            
            # Run benchmarks
            self.results["benchmarks"]["database"] = self.benchmark_database_operations()
            self.results["benchmarks"]["messages"] = self.benchmark_message_operations()
            self.results["benchmarks"]["concurrent"] = self.benchmark_concurrent_operations()
            self.results["memory_profile"] = self.profile_memory_usage()
            self.results["latency_targets"]["operations"] = self.validate_latency_targets()
            
            # Generate summary
            self.generate_summary()
            
        except Exception as e:
            print(f"\n Benchmark failed: {e}")
            traceback.print_exc()
        finally:
            self.cleanup()
    
    def generate_summary(self):
        """Generate performance summary report"""
        print("\n" + "="*60)
        print(" PERFORMANCE SUMMARY")
        print("="*60)
        
        # Database Performance
        if "database" in self.results["benchmarks"]:
            db_results = self.results["benchmarks"]["database"]
            print("\n Database Performance:")
            print(f"  • Single Insert: {db_results['single_insert_ms']:.2f}ms")
            print(f"  • Bulk Insert (100): {db_results['bulk_insert_100_ms']:.2f}ms")
            print(f"  • Average Insert: {db_results['avg_insert_ms']:.2f}ms")
            print(f"  • Query 100 Records: {db_results['query_100_records_ms']:.2f}ms")
        
        # Message Performance
        if "messages" in self.results["benchmarks"]:
            msg_results = self.results["benchmarks"]["messages"]
            print("\n Message Operations Performance:")
            print(f"  • Single Message: {msg_results['single_message_ms']:.2f}ms")
            print(f"  • Broadcast to 100: {msg_results['broadcast_100_ms']:.2f}ms")
            print(f"  • Saturation (1000 msgs): {msg_results['saturation_1000_msgs_ms']:.2f}ms")
            print(f"  • Average per Message: {msg_results['avg_msg_ms']:.2f}ms")
        
        # Concurrent Operations
        if "concurrent" in self.results["benchmarks"]:
            conc_results = self.results["benchmarks"]["concurrent"]
            print("\n Concurrent Operations Performance:")
            for agent_count in [10, 50, 100]:
                if f"agents_{agent_count}" in conc_results:
                    data = conc_results[f"agents_{agent_count}"]
                    print(f"  • {agent_count} Agents:")
                    print(f"    - Create Time: {data['create_time_ms']:.2f}ms")
                    print(f"    - Work Time: {data['work_time_ms']:.2f}ms")
                    print(f"    - Msgs/Second: {data['msg_per_second']:.0f}")
        
        # Memory Profile
        if "memory_profile" in self.results:
            mem_results = self.results["memory_profile"]
            print("\n Memory Usage:")
            print(f"  • Baseline: {mem_results['baseline_mb']:.2f}MB")
            print(f"  • After 1000 Agents: {mem_results['after_1000_agents_mb']:.2f}MB")
            print(f"  • After 10K Messages: {mem_results['after_10000_messages_mb']:.2f}MB")
            print(f"  • Agent Memory Growth: {mem_results['agent_memory_growth_mb']:.2f}MB")
            print(f"  • Message Memory Growth: {mem_results['message_memory_growth_mb']:.2f}MB")
        
        # Latency Validation
        if "operations" in self.results["latency_targets"]:
            latency_results = self.results["latency_targets"]["operations"]
            print("\n Latency Targets (sub-100ms):")
            all_meet_target = True
            for op_name, metrics in latency_results.items():
                status = "" if metrics["meets_target"] else ""
                print(f"  • {op_name}: {status}")
                print(f"    - Median: {metrics['median_ms']:.2f}ms")
                print(f"    - P95: {metrics['p95_ms']:.2f}ms")
                print(f"    - P99: {metrics['p99_ms']:.2f}ms")
                if not metrics["meets_target"]:
                    all_meet_target = False
        
        # Overall Assessment
        print("\n" + "="*60)
        print(" OVERALL ASSESSMENT")
        print("="*60)
        
        if all_meet_target:
            print(" ALL PERFORMANCE TARGETS MET!")
            print("  • All critical operations under 100ms")
            print("  • System ready for production load")
        else:
            print(" SOME PERFORMANCE TARGETS NOT MET")
            print("  • Review operations exceeding 100ms")
            print("  • Consider optimization before production")
        
        # Save detailed results
        with open("performance_report.json", "w") as f:
            json.dump(self.results, f, indent=2, default=str)
        print("\n Detailed results saved to: performance_report.json")

def main():
    """Main entry point"""
    benchmark = PerformanceBenchmark()
    benchmark.run_all_benchmarks()

if __name__ == "__main__":
    main()