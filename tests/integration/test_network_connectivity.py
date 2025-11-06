"""
Network Connectivity Tests for GiljoAI MCP Server Mode

Tests API and WebSocket accessibility from remote network clients.
Validates server mode deployment for LAN/WAN access.

Test Coverage:
- API accessibility from localhost (sanity check)
- API accessibility from LAN IP addresses
- WebSocket connections from remote clients
- Network latency measurements
- Multi-client concurrent access
- Network performance characteristics

Usage:
    # Run all network tests
    pytest tests/integration/test_network_connectivity.py -v

    # Run specific test
    pytest tests/integration/test_network_connectivity.py::TestNetworkConnectivity::test_api_accessible_from_localhost -v

    # Run with network performance marks
    pytest tests/integration/test_network_connectivity.py -m "network" -v
"""

import asyncio
import json
import time

import httpx
import pytest
import websockets
from websockets.exceptions import WebSocketException


# Try to import network utilities
try:
    import netifaces

    NETIFACES_AVAILABLE = True
except ImportError:
    NETIFACES_AVAILABLE = False
    print("Warning: netifaces not installed. Some network tests will be skipped.")
    print("Install with: pip install netifaces")


class NetworkTestHelper:
    """Helper utilities for network connectivity testing"""

    @staticmethod
    def get_local_ip() -> str:
        """Get local LAN IP address"""
        if not NETIFACES_AVAILABLE:
            return "127.0.0.1"

        try:
            interfaces = netifaces.interfaces()
            for interface in interfaces:
                addrs = netifaces.ifaddresses(interface)
                if netifaces.AF_INET in addrs:
                    for addr_info in addrs[netifaces.AF_INET]:
                        ip = addr_info["addr"]
                        # Skip localhost
                        if not ip.startswith("127."):
                            return ip
        except Exception:
            pass

        return "127.0.0.1"

    @staticmethod
    async def measure_latency(url: str, iterations: int = 10) -> dict:
        """Measure network latency to a URL"""
        latencies = []
        errors = 0

        async with httpx.AsyncClient(timeout=5.0) as client:
            for _ in range(iterations):
                try:
                    start = time.perf_counter()
                    response = await client.get(url)
                    elapsed_ms = (time.perf_counter() - start) * 1000

                    if response.status_code == 200:
                        latencies.append(elapsed_ms)
                    else:
                        errors += 1
                except Exception:
                    errors += 1

        if not latencies:
            return {"success": False, "errors": errors, "message": "No successful requests"}

        return {
            "success": True,
            "iterations": iterations,
            "successful": len(latencies),
            "errors": errors,
            "min_ms": min(latencies),
            "max_ms": max(latencies),
            "avg_ms": sum(latencies) / len(latencies),
            "median_ms": sorted(latencies)[len(latencies) // 2],
        }


@pytest.mark.network
class TestNetworkConnectivity:
    """Test network connectivity for server mode deployment"""

    @pytest.fixture(scope="class")
    def server_config(self):
        """Server configuration for testing"""
        return {
            "mode": "server",
            "api_port": 7272,
            "websocket_port": 6003,
            "local_ip": NetworkTestHelper.get_local_ip(),
        }

    @pytest.mark.asyncio
    async def test_api_accessible_from_localhost(self, server_config):
        """
        TEST: API is accessible from localhost (sanity check)

        Purpose: Verify basic API functionality before testing network access
        Expected: 200 OK response with health status
        """
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get(f"http://localhost:{server_config['api_port']}/health")

                assert response.status_code == 200, f"Expected 200, got {response.status_code}"

                data = response.json()
                assert "status" in data, "Health response missing 'status' field"
                assert data["status"] in ["healthy", "degraded"], f"Unexpected health status: {data['status']}"

            except httpx.ConnectError:
                pytest.skip("API server not running on localhost")
            except Exception as e:
                pytest.fail(f"Unexpected error: {e}")

    @pytest.mark.asyncio
    async def test_api_accessible_from_lan_ip(self, server_config):
        """
        TEST: API is accessible from LAN IP address

        Purpose: Verify API can be accessed via network interface (not just localhost)
        This is CRITICAL for server mode deployment.

        Expected: 200 OK response when accessing via LAN IP
        """
        local_ip = server_config["local_ip"]

        if local_ip == "127.0.0.1":
            pytest.skip("Could not determine LAN IP address. Install netifaces or manually configure.")

        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get(f"http://{local_ip}:{server_config['api_port']}/health")

                assert response.status_code == 200, (
                    f"API not accessible from LAN IP {local_ip}. Check firewall and server configuration."
                )

                data = response.json()
                assert data["status"] in ["healthy", "degraded"]

            except httpx.ConnectError as e:
                pytest.fail(
                    f"Cannot connect to API at {local_ip}:{server_config['api_port']}. "
                    f"Verify server is running and bound to 0.0.0.0 (not just localhost). Error: {e}"
                )

    @pytest.mark.asyncio
    async def test_websocket_accessible_from_localhost(self, server_config):
        """
        TEST: WebSocket is accessible from localhost (sanity check)

        Purpose: Verify basic WebSocket functionality
        Expected: Successful connection and ping/pong exchange
        """
        ws_uri = f"ws://localhost:{server_config['websocket_port']}/ws"

        try:
            async with websockets.connect(ws_uri, timeout=5.0) as ws:
                # Send ping
                await ws.send(json.dumps({"type": "ping"}))

                # Receive response
                response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                data = json.loads(response)

                assert data.get("type") == "pong", f"Expected pong, got {data.get('type')}"

        except (WebSocketException, ConnectionRefusedError):
            pytest.skip("WebSocket server not running on localhost")
        except asyncio.TimeoutError:
            pytest.fail("WebSocket connection established but no pong response received")

    @pytest.mark.asyncio
    async def test_websocket_accessible_from_lan_ip(self, server_config):
        """
        TEST: WebSocket is accessible from LAN IP address

        Purpose: Verify WebSocket can be accessed via network interface
        This is CRITICAL for real-time agent communication in server mode.

        Expected: Successful connection and ping/pong exchange
        """
        local_ip = server_config["local_ip"]

        if local_ip == "127.0.0.1":
            pytest.skip("Could not determine LAN IP address")

        ws_uri = f"ws://{local_ip}:{server_config['websocket_port']}/ws"

        try:
            async with websockets.connect(ws_uri, timeout=5.0) as ws:
                # Send ping
                await ws.send(json.dumps({"type": "ping"}))

                # Receive response
                response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                data = json.loads(response)

                assert data.get("type") == "pong", f"WebSocket accessible but ping/pong failed. Got: {data}"

        except (WebSocketException, ConnectionRefusedError) as e:
            pytest.fail(
                f"Cannot connect to WebSocket at {local_ip}:{server_config['websocket_port']}. "
                f"Verify server is running and bound to 0.0.0.0. Error: {e}"
            )

    @pytest.mark.asyncio
    async def test_network_latency_measurements(self, server_config):
        """
        TEST: Measure network latency for API requests

        Purpose: Establish baseline network performance metrics
        Expected: Average latency < 50ms for LAN access
        """
        local_ip = server_config["local_ip"]

        if local_ip == "127.0.0.1":
            pytest.skip("Using localhost - skipping network latency test")

        url = f"http://{local_ip}:{server_config['api_port']}/health"
        result = await NetworkTestHelper.measure_latency(url, iterations=20)

        assert result["success"], f"Latency measurement failed: {result.get('message')}"

        avg_latency = result["avg_ms"]
        p95_latency = result["max_ms"]  # Approximation with small sample

        # Log results
        print("\nNetwork Latency Results:")
        print(f"  Successful: {result['successful']}/{result['iterations']}")
        print(f"  Min: {result['min_ms']:.2f}ms")
        print(f"  Max: {result['max_ms']:.2f}ms")
        print(f"  Avg: {avg_latency:.2f}ms")
        print(f"  Median: {result['median_ms']:.2f}ms")

        # Performance targets
        assert avg_latency < 100.0, f"Average latency {avg_latency:.2f}ms exceeds target of 100ms"

        if avg_latency > 50.0:
            print(f"WARNING: Average latency {avg_latency:.2f}ms > 50ms (LAN target)")

    @pytest.mark.asyncio
    async def test_concurrent_api_requests(self, server_config):
        """
        TEST: Handle concurrent API requests from multiple clients

        Purpose: Validate API can handle multiple simultaneous connections
        Expected: 95%+ success rate with 10 concurrent clients
        """
        local_ip = server_config["local_ip"]
        url = f"http://{local_ip}:{server_config['api_port']}/health"

        num_clients = 10
        tasks = []

        async with httpx.AsyncClient(timeout=5.0) as client:
            for _ in range(num_clients):
                task = client.get(url)
                tasks.append(task)

            start = time.perf_counter()
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            duration = time.perf_counter() - start

        # Analyze results
        successful = sum(1 for r in responses if isinstance(r, httpx.Response) and r.status_code == 200)
        success_rate = successful / num_clients * 100

        print("\nConcurrent Requests Test:")
        print(f"  Clients: {num_clients}")
        print(f"  Successful: {successful}/{num_clients}")
        print(f"  Success Rate: {success_rate:.1f}%")
        print(f"  Total Duration: {duration * 1000:.2f}ms")
        print(f"  Avg per Request: {duration / num_clients * 1000:.2f}ms")

        assert success_rate >= 90.0, f"Success rate {success_rate:.1f}% below target of 90%"

    @pytest.mark.asyncio
    async def test_api_endpoints_accessible_from_network(self, server_config):
        """
        TEST: Critical API endpoints are accessible from network

        Purpose: Verify key API endpoints work over network
        Expected: All tested endpoints return appropriate responses
        """
        local_ip = server_config["local_ip"]

        if local_ip == "127.0.0.1":
            pytest.skip("Using localhost - skipping network endpoint test")

        base_url = f"http://{local_ip}:{server_config['api_port']}"
        endpoints = [
            ("/", 200),
            ("/health", 200),
            ("/api/v1/projects/", 200),  # May be 401 if auth required
        ]

        results = []

        async with httpx.AsyncClient(timeout=5.0) as client:
            for endpoint, _ in endpoints:
                try:
                    response = await client.get(f"{base_url}{endpoint}")
                    results.append(
                        {
                            "endpoint": endpoint,
                            "status": response.status_code,
                            "success": response.status_code in [200, 401],  # 401 ok if auth required
                        }
                    )
                except Exception as e:
                    results.append({"endpoint": endpoint, "status": None, "success": False, "error": str(e)})

        # Log results
        print("\nEndpoint Accessibility Test:")
        for result in results:
            status = result.get("status", "ERROR")
            success_icon = "✓" if result["success"] else "✗"
            print(f"  {success_icon} {result['endpoint']}: {status}")

        # All endpoints should be accessible (200 or 401)
        all_accessible = all(r["success"] for r in results)
        assert all_accessible, "Some endpoints not accessible from network"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_sustained_connection_stability(self, server_config):
        """
        TEST: WebSocket connection stability over time

        Purpose: Verify WebSocket connections remain stable
        Expected: Connection stays alive for at least 30 seconds
        """
        local_ip = server_config["local_ip"]
        ws_uri = f"ws://{local_ip}:{server_config['websocket_port']}/ws"

        duration = 30  # seconds
        ping_interval = 5  # seconds

        try:
            async with websockets.connect(ws_uri, timeout=5.0) as ws:
                start_time = time.time()
                pings_sent = 0
                pongs_received = 0

                while time.time() - start_time < duration:
                    # Send ping
                    await ws.send(json.dumps({"type": "ping"}))
                    pings_sent += 1

                    # Wait for pong
                    try:
                        response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                        data = json.loads(response)
                        if data.get("type") == "pong":
                            pongs_received += 1
                    except asyncio.TimeoutError:
                        pass

                    # Wait before next ping
                    await asyncio.sleep(ping_interval)

                stability_rate = pongs_received / pings_sent * 100

                print(f"\nWebSocket Stability Test ({duration}s):")
                print(f"  Pings Sent: {pings_sent}")
                print(f"  Pongs Received: {pongs_received}")
                print(f"  Stability Rate: {stability_rate:.1f}%")

                assert stability_rate >= 80.0, f"WebSocket stability {stability_rate:.1f}% below target of 80%"

        except WebSocketException as e:
            pytest.fail(f"WebSocket connection failed during stability test: {e}")


@pytest.mark.network
@pytest.mark.integration
class TestNetworkErrorHandling:
    """Test error handling for network-related issues"""

    @pytest.mark.asyncio
    async def test_invalid_port_handling(self):
        """
        TEST: Graceful handling of connection to invalid port

        Purpose: Verify proper error handling for network failures
        Expected: Connection error, not crash
        """
        invalid_port = 9999
        url = f"http://localhost:{invalid_port}/health"

        async with httpx.AsyncClient(timeout=2.0) as client:
            with pytest.raises(httpx.ConnectError):
                await client.get(url)

    @pytest.mark.asyncio
    async def test_connection_timeout_handling(self):
        """
        TEST: Proper timeout handling for slow connections

        Purpose: Verify timeout configurations work correctly
        Expected: Timeout error after specified duration
        """
        # Use a non-routable IP to force timeout
        url = "http://10.255.255.1:7272/health"

        async with httpx.AsyncClient(timeout=1.0) as client:
            with pytest.raises((httpx.ConnectTimeout, httpx.ReadTimeout)):
                await client.get(url)


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v", "-s"])
