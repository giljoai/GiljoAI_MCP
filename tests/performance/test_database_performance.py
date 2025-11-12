"""
Database Performance Benchmarks - Baseline Metrics

Creates baseline performance metrics for database operations to enable
performance regression testing. Focuses on individual operation timing
rather than load/stress testing.

Target Metrics (from Handover 0129b):
- Simple SELECT: <10ms (acceptable <20ms)
- Complex JOIN: <50ms (acceptable <100ms)
- INSERT/UPDATE: <20ms (acceptable <50ms)
- Transaction: <30ms (acceptable <75ms)
- Connection Pool: <5ms (acceptable <10ms)
"""

import time
import statistics
import uuid
from typing import List, Dict, Any
from datetime import datetime

import pytest
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import (
    Tenant, Product, Project, MCPAgentJob, Task, Context
)


class DatabaseBenchmarks:
    """Database performance benchmark suite for baseline metrics."""

    def __init__(self, db_session: AsyncSession, tenant_key: str):
        self.db_session = db_session
        self.tenant_key = tenant_key
        self.results: Dict[str, Dict[str, float]] = {}

    async def run_benchmark(self, name: str, func, iterations: int = 100):
        """
        Run a benchmark multiple times and collect statistics.

        Args:
            name: Benchmark name
            func: Async function to benchmark
            iterations: Number of iterations to run
        """
        timings: List[float] = []

        for _ in range(iterations):
            start = time.perf_counter()
            await func()
            duration = time.perf_counter() - start
            timings.append(duration * 1000)  # Convert to milliseconds

        self.results[name] = {
            "mean": statistics.mean(timings),
            "median": statistics.median(timings),
            "stdev": statistics.stdev(timings) if len(timings) > 1 else 0,
            "min": min(timings),
            "max": max(timings),
            "p95": self._percentile(timings, 95),
            "p99": self._percentile(timings, 99),
            "iterations": iterations
        }

    @staticmethod
    def _percentile(data: List[float], percentile: int) -> float:
        """Calculate percentile."""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        if index >= len(sorted_data):
            index = len(sorted_data) - 1
        return sorted_data[index]

    def generate_report(self) -> Dict[str, Any]:
        """Generate benchmark report."""
        return {
            "database_benchmarks": self.results,
            "timestamp": datetime.now().isoformat(),
            "tenant_key": self.tenant_key
        }


# Benchmark functions

async def benchmark_simple_select(db_session: AsyncSession, tenant_key: str):
    """Benchmark simple SELECT query."""
    result = await db_session.execute(
        select(Tenant).filter_by(tenant_key=tenant_key)
    )
    tenant = result.scalar_one_or_none()
    return tenant


async def benchmark_complex_join(db_session: AsyncSession, tenant_key: str):
    """Benchmark complex JOIN query."""
    result = await db_session.execute(
        select(Project, Product)
        .join(Product, Project.product_id == Product.id)
        .filter(Product.tenant_key == tenant_key)
        .limit(10)
    )
    projects = result.all()
    return projects


async def benchmark_insert(db_session: AsyncSession, tenant_key: str):
    """Benchmark INSERT operation."""
    product = Product(
        tenant_key=tenant_key,
        name=f"Benchmark Product {uuid.uuid4()}",
        status="active"
    )
    db_session.add(product)
    await db_session.flush()

    # Clean up
    await db_session.delete(product)
    await db_session.flush()


async def benchmark_update(db_session: AsyncSession, tenant_key: str, product_id: int):
    """Benchmark UPDATE operation."""
    result = await db_session.execute(
        select(Product).filter_by(id=product_id)
    )
    product = result.scalar_one_or_none()
    if product:
        product.name = f"Updated {uuid.uuid4()}"
        await db_session.flush()


async def benchmark_transaction(db_session: AsyncSession, tenant_key: str, product_id: int):
    """Benchmark multi-operation transaction."""
    # Multiple operations in one transaction
    product = Product(
        tenant_key=tenant_key,
        name=f"Transaction Test {uuid.uuid4()}",
        status="active"
    )
    db_session.add(product)
    await db_session.flush()

    project = Project(
        product_id=product.id,
        tenant_key=tenant_key,
        name=f"Transaction Project {uuid.uuid4()}",
        mission="Benchmark transaction test"
    )
    db_session.add(project)
    await db_session.flush()

    # Clean up
    await db_session.delete(project)
    await db_session.delete(product)
    await db_session.flush()


async def benchmark_count_query(db_session: AsyncSession, tenant_key: str):
    """Benchmark COUNT query."""
    result = await db_session.execute(
        select(func.count(Product.id)).filter_by(tenant_key=tenant_key)
    )
    count = result.scalar()
    return count


# Test class

class TestDatabasePerformance:
    """Database performance benchmark tests."""

    @pytest.mark.asyncio
    async def test_database_benchmarks(self, db_session, test_tenant, test_product):
        """
        Run all database benchmarks and generate baseline report.

        This test establishes baseline performance metrics for database operations.
        It should be run against a local PostgreSQL database.
        """
        benchmarks = DatabaseBenchmarks(db_session, test_tenant.tenant_key)

        print("\n=== Running Database Performance Benchmarks ===\n")

        # Benchmark 1: Simple SELECT
        print("Benchmarking simple SELECT queries...")
        await benchmarks.run_benchmark(
            "simple_select",
            lambda: benchmark_simple_select(db_session, test_tenant.tenant_key),
            iterations=100
        )

        # Benchmark 2: Complex JOIN
        print("Benchmarking complex JOIN queries...")
        await benchmarks.run_benchmark(
            "complex_join",
            lambda: benchmark_complex_join(db_session, test_tenant.tenant_key),
            iterations=100
        )

        # Benchmark 3: INSERT
        print("Benchmarking INSERT operations...")
        await benchmarks.run_benchmark(
            "insert",
            lambda: benchmark_insert(db_session, test_tenant.tenant_key),
            iterations=100
        )

        # Benchmark 4: UPDATE
        print("Benchmarking UPDATE operations...")
        await benchmarks.run_benchmark(
            "update",
            lambda: benchmark_update(db_session, test_tenant.tenant_key, test_product.id),
            iterations=100
        )

        # Benchmark 5: Transaction
        print("Benchmarking multi-operation transactions...")
        await benchmarks.run_benchmark(
            "transaction",
            lambda: benchmark_transaction(db_session, test_tenant.tenant_key, test_product.id),
            iterations=50  # Fewer iterations for complex operations
        )

        # Benchmark 6: COUNT query
        print("Benchmarking COUNT queries...")
        await benchmarks.run_benchmark(
            "count_query",
            lambda: benchmark_count_query(db_session, test_tenant.tenant_key),
            iterations=100
        )

        # Generate report
        report = benchmarks.generate_report()

        # Print results
        print("\n=== Database Performance Report ===\n")
        for name, metrics in report["database_benchmarks"].items():
            status = "✅ PASS" if metrics["mean"] < self._get_target(name) else "⚠️ WARNING"
            print(f"\n{name}: {status}")
            print(f"  Mean:   {metrics['mean']:.2f}ms (target: <{self._get_target(name)}ms)")
            print(f"  Median: {metrics['median']:.2f}ms")
            print(f"  P95:    {metrics['p95']:.2f}ms")
            print(f"  P99:    {metrics['p99']:.2f}ms")
            print(f"  Min:    {metrics['min']:.2f}ms")
            print(f"  Max:    {metrics['max']:.2f}ms")

        # Assertions against acceptable targets
        assert report["database_benchmarks"]["simple_select"]["mean"] < 20, \
            f"Simple SELECT exceeds acceptable target (20ms): {report['database_benchmarks']['simple_select']['mean']:.2f}ms"

        assert report["database_benchmarks"]["complex_join"]["mean"] < 100, \
            f"Complex JOIN exceeds acceptable target (100ms): {report['database_benchmarks']['complex_join']['mean']:.2f}ms"

        assert report["database_benchmarks"]["insert"]["mean"] < 50, \
            f"INSERT exceeds acceptable target (50ms): {report['database_benchmarks']['insert']['mean']:.2f}ms"

        assert report["database_benchmarks"]["update"]["mean"] < 50, \
            f"UPDATE exceeds acceptable target (50ms): {report['database_benchmarks']['update']['mean']:.2f}ms"

        assert report["database_benchmarks"]["transaction"]["mean"] < 75, \
            f"Transaction exceeds acceptable target (75ms): {report['database_benchmarks']['transaction']['mean']:.2f}ms"

        print("\n✅ All database benchmarks completed successfully!\n")

        return report

    def _get_target(self, benchmark_name: str) -> float:
        """Get target metric for benchmark."""
        targets = {
            "simple_select": 10,
            "complex_join": 50,
            "insert": 20,
            "update": 20,
            "transaction": 30,
            "count_query": 20
        }
        return targets.get(benchmark_name, 50)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
