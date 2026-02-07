"""
API Endpoint Performance Benchmarks - Baseline Metrics

Creates baseline performance metrics for API endpoints to enable
performance regression testing. Focuses on individual endpoint latency
rather than load/stress testing.

Target Metrics (from Handover 0129b):
- GET (single): <50ms (acceptable <100ms)
- GET (list): <100ms (acceptable <200ms)
- POST/PUT: <100ms (acceptable <200ms)
- DELETE: <50ms (acceptable <100ms)
- Complex operations: <200ms (acceptable <500ms)
"""

import statistics
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List

import pytest
from httpx import AsyncClient


class APIBenchmarks:
    """API endpoint performance benchmark suite for baseline metrics."""

    def __init__(self, client: AsyncClient, tenant_key: str):
        self.client = client
        self.tenant_key = tenant_key
        self.headers = {"X-Tenant-Key": tenant_key}
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
            "iterations": iterations,
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
        return {"api_benchmarks": self.results, "timestamp": datetime.now().isoformat(), "tenant_key": self.tenant_key}


# Benchmark functions


async def benchmark_get_products_list(client: AsyncClient, headers: Dict[str, str]):
    """Benchmark GET list of products."""
    response = await client.get("/api/v1/products", headers=headers)
    assert response.status_code == 200
    return response.json()


async def benchmark_get_product_single(client: AsyncClient, headers: Dict[str, str], product_id: int):
    """Benchmark GET single product."""
    response = await client.get(f"/api/v1/products/{product_id}", headers=headers)
    assert response.status_code == 200
    return response.json()


async def benchmark_post_product(client: AsyncClient, headers: Dict[str, str], tenant_key: str):
    """Benchmark POST (create) product."""
    product_data = {"name": f"Benchmark Product {uuid.uuid4()}", "status": "active"}
    response = await client.post("/api/v1/products", headers=headers, json=product_data)
    assert response.status_code == 201
    product = response.json()

    # Clean up
    await client.delete(f"/api/v1/products/{product['id']}", headers=headers)

    return product


async def benchmark_put_product(client: AsyncClient, headers: Dict[str, str], product_id: int):
    """Benchmark PUT (update) product."""
    update_data = {"name": f"Updated Product {uuid.uuid4()}"}
    response = await client.put(f"/api/v1/products/{product_id}", headers=headers, json=update_data)
    assert response.status_code == 200
    return response.json()


async def benchmark_get_projects_list(client: AsyncClient, headers: Dict[str, str], product_id: int):
    """Benchmark GET list of projects."""
    response = await client.get(f"/api/v1/products/{product_id}/projects", headers=headers)
    assert response.status_code == 200
    return response.json()


async def benchmark_get_project_single(client: AsyncClient, headers: Dict[str, str], project_id: int):
    """Benchmark GET single project."""
    response = await client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert response.status_code == 200
    return response.json()


async def benchmark_post_project(client: AsyncClient, headers: Dict[str, str], product_id: int):
    """Benchmark POST (create) project."""
    project_data = {
        "name": f"Benchmark Project {uuid.uuid4()}",
        "mission": "Performance benchmark project",
        "product_id": product_id,
    }
    response = await client.post(f"/api/v1/products/{product_id}/projects", headers=headers, json=project_data)
    assert response.status_code == 201
    project = response.json()

    # Clean up
    await client.delete(f"/api/v1/projects/{project['id']}", headers=headers)

    return project


async def benchmark_get_templates_list(client: AsyncClient, headers: Dict[str, str]):
    """Benchmark GET list of templates."""
    response = await client.get("/api/v1/templates", headers=headers)
    assert response.status_code == 200
    return response.json()


async def benchmark_get_agent_jobs_list(client: AsyncClient, headers: Dict[str, str], project_id: int):
    """Benchmark GET list of agent jobs."""
    response = await client.get(f"/api/v1/projects/{project_id}/agent_jobs", headers=headers)
    assert response.status_code == 200
    return response.json()


async def benchmark_complex_project_with_context(client: AsyncClient, headers: Dict[str, str], product_id: int):
    """Benchmark complex operation: create project with context."""
    # This is a more complex operation involving multiple steps
    project_data = {
        "name": f"Complex Project {uuid.uuid4()}",
        "mission": "Complex benchmark operation",
        "product_id": product_id,
    }
    response = await client.post(f"/api/v1/products/{product_id}/projects", headers=headers, json=project_data)
    assert response.status_code == 201
    project = response.json()

    # Get project details (includes context loading)
    response = await client.get(f"/api/v1/projects/{project['id']}", headers=headers)
    assert response.status_code == 200

    # Clean up
    await client.delete(f"/api/v1/projects/{project['id']}", headers=headers)

    return project


# Test class


class TestAPIPerformance:
    """API endpoint performance benchmark tests."""

    @pytest.mark.asyncio
    async def test_api_benchmarks(self, async_client, test_tenant, test_product, test_project):
        """
        Run all API benchmarks and generate baseline report.

        This test establishes baseline performance metrics for API endpoints.
        It should be run against a running application server.
        """
        benchmarks = APIBenchmarks(async_client, test_tenant.tenant_key)

        print("\n=== Running API Performance Benchmarks ===\n")

        # Benchmark 1: GET products list
        print("Benchmarking GET products list...")
        await benchmarks.run_benchmark(
            "get_products_list", lambda: benchmark_get_products_list(async_client, benchmarks.headers), iterations=100
        )

        # Benchmark 2: GET single product
        print("Benchmarking GET single product...")
        await benchmarks.run_benchmark(
            "get_product_single",
            lambda: benchmark_get_product_single(async_client, benchmarks.headers, test_product.id),
            iterations=100,
        )

        # Benchmark 3: POST product
        print("Benchmarking POST product (create)...")
        await benchmarks.run_benchmark(
            "post_product",
            lambda: benchmark_post_product(async_client, benchmarks.headers, test_tenant.tenant_key),
            iterations=50,  # Fewer iterations for write operations
        )

        # Benchmark 4: PUT product
        print("Benchmarking PUT product (update)...")
        await benchmarks.run_benchmark(
            "put_product",
            lambda: benchmark_put_product(async_client, benchmarks.headers, test_product.id),
            iterations=50,
        )

        # Benchmark 5: GET projects list
        print("Benchmarking GET projects list...")
        await benchmarks.run_benchmark(
            "get_projects_list",
            lambda: benchmark_get_projects_list(async_client, benchmarks.headers, test_product.id),
            iterations=100,
        )

        # Benchmark 6: GET single project
        print("Benchmarking GET single project...")
        await benchmarks.run_benchmark(
            "get_project_single",
            lambda: benchmark_get_project_single(async_client, benchmarks.headers, test_project.id),
            iterations=100,
        )

        # Benchmark 7: POST project
        print("Benchmarking POST project (create)...")
        await benchmarks.run_benchmark(
            "post_project",
            lambda: benchmark_post_project(async_client, benchmarks.headers, test_product.id),
            iterations=50,
        )

        # Benchmark 8: GET templates list
        print("Benchmarking GET templates list...")
        await benchmarks.run_benchmark(
            "get_templates_list", lambda: benchmark_get_templates_list(async_client, benchmarks.headers), iterations=100
        )

        # Benchmark 9: GET agent jobs list
        print("Benchmarking GET agent jobs list...")
        await benchmarks.run_benchmark(
            "get_agent_jobs_list",
            lambda: benchmark_get_agent_jobs_list(async_client, benchmarks.headers, test_project.id),
            iterations=100,
        )

        # Benchmark 10: Complex operation
        print("Benchmarking complex project creation with context...")
        await benchmarks.run_benchmark(
            "complex_project_with_context",
            lambda: benchmark_complex_project_with_context(async_client, benchmarks.headers, test_product.id),
            iterations=30,  # Fewer iterations for complex operations
        )

        # Generate report
        report = benchmarks.generate_report()

        # Print results
        print("\n=== API Performance Report ===\n")
        for name, metrics in report["api_benchmarks"].items():
            status = "✅ PASS" if metrics["mean"] < self._get_target(name) else "⚠️ WARNING"
            print(f"\n{name}: {status}")
            print(f"  Mean:   {metrics['mean']:.2f}ms (target: <{self._get_target(name)}ms)")
            print(f"  Median: {metrics['median']:.2f}ms")
            print(f"  P95:    {metrics['p95']:.2f}ms")
            print(f"  P99:    {metrics['p99']:.2f}ms")
            print(f"  Min:    {metrics['min']:.2f}ms")
            print(f"  Max:    {metrics['max']:.2f}ms")

        # Assertions against acceptable targets
        assert report["api_benchmarks"]["get_products_list"]["mean"] < 200, (
            f"GET products list exceeds acceptable target (200ms): {report['api_benchmarks']['get_products_list']['mean']:.2f}ms"
        )

        assert report["api_benchmarks"]["get_product_single"]["mean"] < 100, (
            f"GET single product exceeds acceptable target (100ms): {report['api_benchmarks']['get_product_single']['mean']:.2f}ms"
        )

        assert report["api_benchmarks"]["post_product"]["mean"] < 200, (
            f"POST product exceeds acceptable target (200ms): {report['api_benchmarks']['post_product']['mean']:.2f}ms"
        )

        assert report["api_benchmarks"]["complex_project_with_context"]["mean"] < 500, (
            f"Complex operation exceeds acceptable target (500ms): {report['api_benchmarks']['complex_project_with_context']['mean']:.2f}ms"
        )

        print("\n✅ All API benchmarks completed successfully!\n")

        return report

    def _get_target(self, benchmark_name: str) -> float:
        """Get target metric for benchmark."""
        targets = {
            "get_products_list": 100,
            "get_product_single": 50,
            "post_product": 100,
            "put_product": 100,
            "get_projects_list": 100,
            "get_project_single": 50,
            "post_project": 100,
            "get_templates_list": 100,
            "get_agent_jobs_list": 100,
            "complex_project_with_context": 200,
        }
        return targets.get(benchmark_name, 100)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
