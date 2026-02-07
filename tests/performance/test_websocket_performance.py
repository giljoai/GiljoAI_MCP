"""
WebSocket Performance Benchmarks - Baseline Metrics

Creates baseline performance metrics for WebSocket operations to enable
performance regression testing. Focuses on message latency and connection
timing rather than load/stress testing.

Target Metrics (from Handover 0129b):
- Message latency: <50ms (acceptable <100ms)
- Connection setup: <100ms (acceptable <200ms)
- Broadcast (10 clients): <100ms (acceptable <200ms)
- Broadcast (100 clients): <500ms (acceptable <1000ms)
"""

import asyncio
import json
import statistics
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List

import pytest
import websockets
from websockets.client import WebSocketClientProtocol


class WebSocketBenchmarks:
    """WebSocket performance benchmark suite for baseline metrics."""

    def __init__(self, ws_url: str, tenant_key: str):
        self.ws_url = ws_url
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
        return {
            "websocket_benchmarks": self.results,
            "timestamp": datetime.now().isoformat(),
            "tenant_key": self.tenant_key,
        }


# Benchmark functions


async def benchmark_connection_setup(ws_url: str, tenant_key: str):
    """Benchmark WebSocket connection establishment."""
    async with websockets.connect(ws_url) as ws:
        # Send authentication
        await ws.send(json.dumps({"type": "auth", "tenant_key": tenant_key}))

        # Wait for auth response
        response = await ws.recv()
        auth_data = json.loads(response)
        assert auth_data.get("type") == "auth_success" or auth_data.get("status") == "authenticated"


async def benchmark_message_latency(ws: WebSocketClientProtocol):
    """Benchmark WebSocket message round-trip latency (ping-pong)."""
    message_id = str(uuid.uuid4())

    # Send ping
    await ws.send(json.dumps({"type": "ping", "message_id": message_id}))

    # Wait for pong
    response = await ws.recv()
    response_data = json.loads(response)

    # Verify response
    assert response_data.get("type") == "pong" or "ping" in str(response_data).lower()


async def benchmark_message_send(ws: WebSocketClientProtocol, tenant_key: str):
    """Benchmark sending a message (no response expected)."""
    await ws.send(json.dumps({"type": "status_update", "tenant_key": tenant_key, "status": "active"}))


async def benchmark_subscribe_channel(ws: WebSocketClientProtocol, channel: str):
    """Benchmark subscribing to a channel."""
    await ws.send(json.dumps({"type": "subscribe", "channel": channel}))

    # Wait for subscription confirmation
    response = await ws.recv()
    response_data = json.loads(response)
    # May receive subscription confirmation or other messages


async def benchmark_broadcast_latency(ws_url: str, tenant_key: str, num_clients: int):
    """
    Benchmark broadcast latency to multiple clients.

    Args:
        ws_url: WebSocket URL
        tenant_key: Tenant key for authentication
        num_clients: Number of clients to broadcast to
    """
    clients: List[WebSocketClientProtocol] = []

    try:
        # Connect multiple clients
        for _ in range(num_clients):
            ws = await websockets.connect(ws_url)

            # Authenticate
            await ws.send(json.dumps({"type": "auth", "tenant_key": tenant_key}))

            # Wait for auth response
            await ws.recv()

            # Subscribe to broadcast channel
            await ws.send(json.dumps({"type": "subscribe", "channel": "updates"}))

            clients.append(ws)

        # Small delay to ensure all subscriptions are processed
        await asyncio.sleep(0.1)

        # Trigger broadcast by sending a message to first client
        # (In production, this would be triggered by server-side event)
        broadcast_message = {"type": "broadcast", "channel": "updates", "message": f"Broadcast test {uuid.uuid4()}"}

        await clients[0].send(json.dumps(broadcast_message))

        # Wait for all clients to receive the broadcast
        # Note: This is a simplified benchmark. In production, you'd need
        # actual server-side broadcast mechanism
        await asyncio.sleep(0.2)

    finally:
        # Clean up connections
        for ws in clients:
            await ws.close()


# Test class


class TestWebSocketPerformance:
    """WebSocket performance benchmark tests."""

    @pytest.mark.asyncio
    async def test_websocket_benchmarks(self, test_tenant, websocket_server_url):
        """
        Run all WebSocket benchmarks and generate baseline report.

        This test establishes baseline performance metrics for WebSocket operations.
        It should be run against a running application server with WebSocket support.

        Args:
            test_tenant: Test tenant fixture
            websocket_server_url: WebSocket server URL (from fixture or config)
        """
        # Default WebSocket URL if not provided by fixture
        ws_url = websocket_server_url or "ws://localhost:8000/ws"

        benchmarks = WebSocketBenchmarks(ws_url, test_tenant.tenant_key)

        print("\n=== Running WebSocket Performance Benchmarks ===\n")

        # Benchmark 1: Connection setup
        print("Benchmarking WebSocket connection setup...")
        await benchmarks.run_benchmark(
            "connection_setup", lambda: benchmark_connection_setup(ws_url, test_tenant.tenant_key), iterations=50
        )

        # For remaining benchmarks, maintain a single connection
        async with websockets.connect(ws_url) as ws:
            # Authenticate
            await ws.send(json.dumps({"type": "auth", "tenant_key": test_tenant.tenant_key}))
            await ws.recv()  # Wait for auth response

            # Benchmark 2: Message round-trip latency
            print("Benchmarking message round-trip latency (ping-pong)...")
            await benchmarks.run_benchmark("message_latency", lambda: benchmark_message_latency(ws), iterations=100)

            # Benchmark 3: Message send (one-way)
            print("Benchmarking one-way message send...")
            await benchmarks.run_benchmark(
                "message_send", lambda: benchmark_message_send(ws, test_tenant.tenant_key), iterations=100
            )

            # Benchmark 4: Channel subscription
            print("Benchmarking channel subscription...")
            await benchmarks.run_benchmark(
                "subscribe_channel",
                lambda: benchmark_subscribe_channel(ws, f"test_channel_{uuid.uuid4()}"),
                iterations=50,
            )

        # Benchmark 5: Broadcast to 10 clients
        print("Benchmarking broadcast latency (10 clients)...")
        await benchmarks.run_benchmark(
            "broadcast_10_clients",
            lambda: benchmark_broadcast_latency(ws_url, test_tenant.tenant_key, 10),
            iterations=10,  # Fewer iterations for multi-client tests
        )

        # Benchmark 6: Broadcast to 50 clients
        print("Benchmarking broadcast latency (50 clients)...")
        await benchmarks.run_benchmark(
            "broadcast_50_clients",
            lambda: benchmark_broadcast_latency(ws_url, test_tenant.tenant_key, 50),
            iterations=5,  # Even fewer for larger client counts
        )

        # Generate report
        report = benchmarks.generate_report()

        # Print results
        print("\n=== WebSocket Performance Report ===\n")
        for name, metrics in report["websocket_benchmarks"].items():
            status = "✅ PASS" if metrics["mean"] < self._get_target(name) else "⚠️ WARNING"
            print(f"\n{name}: {status}")
            print(f"  Mean:   {metrics['mean']:.2f}ms (target: <{self._get_target(name)}ms)")
            print(f"  Median: {metrics['median']:.2f}ms")
            print(f"  P95:    {metrics['p95']:.2f}ms")
            print(f"  P99:    {metrics['p99']:.2f}ms")
            print(f"  Min:    {metrics['min']:.2f}ms")
            print(f"  Max:    {metrics['max']:.2f}ms")

        # Assertions against acceptable targets
        assert report["websocket_benchmarks"]["connection_setup"]["mean"] < 200, (
            f"Connection setup exceeds acceptable target (200ms): {report['websocket_benchmarks']['connection_setup']['mean']:.2f}ms"
        )

        assert report["websocket_benchmarks"]["message_latency"]["mean"] < 100, (
            f"Message latency exceeds acceptable target (100ms): {report['websocket_benchmarks']['message_latency']['mean']:.2f}ms"
        )

        assert report["websocket_benchmarks"]["broadcast_10_clients"]["mean"] < 200, (
            f"Broadcast (10 clients) exceeds acceptable target (200ms): {report['websocket_benchmarks']['broadcast_10_clients']['mean']:.2f}ms"
        )

        assert report["websocket_benchmarks"]["broadcast_50_clients"]["mean"] < 500, (
            f"Broadcast (50 clients) exceeds acceptable target (500ms): {report['websocket_benchmarks']['broadcast_50_clients']['mean']:.2f}ms"
        )

        print("\n✅ All WebSocket benchmarks completed successfully!\n")

        return report

    def _get_target(self, benchmark_name: str) -> float:
        """Get target metric for benchmark."""
        targets = {
            "connection_setup": 100,
            "message_latency": 50,
            "message_send": 50,
            "subscribe_channel": 100,
            "broadcast_10_clients": 100,
            "broadcast_50_clients": 500,
        }
        return targets.get(benchmark_name, 100)


# Fixtures


@pytest.fixture
def websocket_server_url():
    """
    Provide WebSocket server URL.

    Override this fixture in conftest.py if you need a different URL.
    """
    return "ws://localhost:8000/ws"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
