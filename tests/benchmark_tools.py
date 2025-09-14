"""
Performance benchmarking utilities for Tool-API integration testing
"""

import time
import asyncio
import statistics
from typing import List, Dict, Any, Callable
from dataclasses import dataclass, field
import json
from pathlib import Path
from datetime import datetime


@dataclass
class BenchmarkResult:
    """Results from a benchmark run"""
    name: str
    iterations: int
    times: List[float] = field(default_factory=list)
    errors: int = 0
    success_rate: float = 0.0
    
    @property
    def min_time(self) -> float:
        return min(self.times) if self.times else 0
    
    @property
    def max_time(self) -> float:
        return max(self.times) if self.times else 0
    
    @property
    def avg_time(self) -> float:
        return statistics.mean(self.times) if self.times else 0
    
    @property
    def median_time(self) -> float:
        return statistics.median(self.times) if self.times else 0
    
    @property
    def std_dev(self) -> float:
        return statistics.stdev(self.times) if len(self.times) > 1 else 0
    
    @property
    def p95(self) -> float:
        """95th percentile"""
        if not self.times:
            return 0
        sorted_times = sorted(self.times)
        index = int(len(sorted_times) * 0.95)
        return sorted_times[index] if index < len(sorted_times) else sorted_times[-1]
    
    @property
    def p99(self) -> float:
        """99th percentile"""
        if not self.times:
            return 0
        sorted_times = sorted(self.times)
        index = int(len(sorted_times) * 0.99)
        return sorted_times[index] if index < len(sorted_times) else sorted_times[-1]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "iterations": self.iterations,
            "success_rate": f"{self.success_rate:.1f}%",
            "errors": self.errors,
            "timing_ms": {
                "min": f"{self.min_time:.2f}",
                "max": f"{self.max_time:.2f}",
                "avg": f"{self.avg_time:.2f}",
                "median": f"{self.median_time:.2f}",
                "std_dev": f"{self.std_dev:.2f}",
                "p95": f"{self.p95:.2f}",
                "p99": f"{self.p99:.2f}"
            },
            "meets_100ms_target": self.avg_time < 100
        }


class PerformanceBenchmark:
    """Performance benchmarking for Tool-API integration"""
    
    def __init__(self, target_time_ms: float = 100.0):
        self.target_time_ms = target_time_ms
        self.results: Dict[str, BenchmarkResult] = {}
        
    async def benchmark_async(
        self,
        name: str,
        func: Callable,
        iterations: int = 100,
        warmup: int = 5
    ) -> BenchmarkResult:
        """Benchmark an async function"""
        
        result = BenchmarkResult(name=name, iterations=iterations)
        
        # Warmup runs
        for _ in range(warmup):
            try:
                await func()
            except:
                pass
        
        # Actual benchmark
        successful = 0
        for i in range(iterations):
            try:
                start = time.perf_counter()
                await func()
                elapsed_ms = (time.perf_counter() - start) * 1000
                result.times.append(elapsed_ms)
                successful += 1
            except Exception as e:
                result.errors += 1
                
        result.success_rate = (successful / iterations) * 100
        self.results[name] = result
        return result
    
    def benchmark_sync(
        self,
        name: str,
        func: Callable,
        iterations: int = 100,
        warmup: int = 5
    ) -> BenchmarkResult:
        """Benchmark a synchronous function"""
        
        result = BenchmarkResult(name=name, iterations=iterations)
        
        # Warmup runs
        for _ in range(warmup):
            try:
                func()
            except:
                pass
        
        # Actual benchmark
        successful = 0
        for i in range(iterations):
            try:
                start = time.perf_counter()
                func()
                elapsed_ms = (time.perf_counter() - start) * 1000
                result.times.append(elapsed_ms)
                successful += 1
            except Exception:
                result.errors += 1
                
        result.success_rate = (successful / iterations) * 100
        self.results[name] = result
        return result
    
    async def load_test(
        self,
        name: str,
        func: Callable,
        concurrent_requests: int = 10,
        duration_seconds: int = 10
    ) -> Dict[str, Any]:
        """Run a load test with concurrent requests"""
        
        results = []
        errors = 0
        start_time = time.time()
        
        async def worker():
            nonlocal errors
            while time.time() - start_time < duration_seconds:
                try:
                    req_start = time.perf_counter()
                    await func()
                    elapsed_ms = (time.perf_counter() - req_start) * 1000
                    results.append(elapsed_ms)
                except Exception:
                    errors += 1
                    
        # Run concurrent workers
        workers = [worker() for _ in range(concurrent_requests)]
        await asyncio.gather(*workers)
        
        # Calculate stats
        total_requests = len(results) + errors
        success_rate = (len(results) / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "name": name,
            "concurrent_requests": concurrent_requests,
            "duration_seconds": duration_seconds,
            "total_requests": total_requests,
            "successful_requests": len(results),
            "errors": errors,
            "success_rate": f"{success_rate:.1f}%",
            "requests_per_second": total_requests / duration_seconds,
            "timing_ms": {
                "min": f"{min(results):.2f}" if results else "0",
                "max": f"{max(results):.2f}" if results else "0",
                "avg": f"{statistics.mean(results):.2f}" if results else "0",
                "median": f"{statistics.median(results):.2f}" if results else "0",
                "p95": f"{sorted(results)[int(len(results)*0.95)]:.2f}" if results else "0",
                "p99": f"{sorted(results)[int(len(results)*0.99)]:.2f}" if results else "0"
            } if results else {}
        }
    
    def generate_report(self) -> str:
        """Generate a performance report"""
        
        report_lines = [
            "=" * 80,
            "PERFORMANCE BENCHMARK REPORT",
            "=" * 80,
            f"Timestamp: {datetime.now().isoformat()}",
            f"Target Time: {self.target_time_ms}ms",
            "",
            "RESULTS:",
            "-" * 80
        ]
        
        # Sort results by average time
        sorted_results = sorted(
            self.results.values(),
            key=lambda r: r.avg_time
        )
        
        for result in sorted_results:
            status = "[PASS]" if result.avg_time < self.target_time_ms else "[FAIL]"
            report_lines.extend([
                f"\n{status} {result.name}",
                f"  Iterations: {result.iterations}",
                f"  Success Rate: {result.success_rate:.1f}%",
                f"  Errors: {result.errors}",
                f"  Timing (ms):",
                f"    Min: {result.min_time:.2f}",
                f"    Max: {result.max_time:.2f}",
                f"    Avg: {result.avg_time:.2f}",
                f"    Median: {result.median_time:.2f}",
                f"    Std Dev: {result.std_dev:.2f}",
                f"    P95: {result.p95:.2f}",
                f"    P99: {result.p99:.2f}"
            ])
        
        # Summary
        passing = sum(1 for r in sorted_results if r.avg_time < self.target_time_ms)
        total = len(sorted_results)
        
        report_lines.extend([
            "",
            "=" * 80,
            "SUMMARY:",
            f"  Total Tests: {total}",
            f"  Passing (<{self.target_time_ms}ms): {passing}",
            f"  Failing: {total - passing}",
            f"  Pass Rate: {(passing/total*100):.1f}%" if total > 0 else "N/A",
            "=" * 80
        ])
        
        return "\n".join(report_lines)
    
    def save_results(self, filepath: Path):
        """Save results to JSON file"""
        
        data = {
            "timestamp": datetime.now().isoformat(),
            "target_time_ms": self.target_time_ms,
            "results": {
                name: result.to_dict()
                for name, result in self.results.items()
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)