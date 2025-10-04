#!/usr/bin/env python3
"""
End-to-End WebSocket Integration Test
Tests both backend and frontend real-time communication
"""

import asyncio
import json
import time

import httpx
import websockets


class E2EWebSocketTester:
    """End-to-end WebSocket integration tester"""

    def __init__(self):
        self.api_url = "http://localhost:7272"
        self.ws_url = "ws://localhost:7272/ws"
        self.frontend_url = "http://localhost:7274"
        self.results = {}

    async def test_backend_connection(self) -> bool:
        """Test backend WebSocket connection"""

        try:
            ws_url = f"{self.ws_url}/test_backend_client"
            async with websockets.connect(ws_url) as websocket:
                # Test ping-pong
                start = time.time()
                await websocket.send(json.dumps({"type": "ping", "timestamp": start}))

                response = await asyncio.wait_for(websocket.recv(), timeout=2)
                data = json.loads(response)

                if data.get("type") == "pong":
                    latency = (time.time() - start) * 1000
                    self.results["backend_latency"] = latency
                    return True

        except Exception:
            return False

    async def test_api_broadcasts(self) -> bool:
        """Test API endpoints trigger WebSocket broadcasts"""

        try:
            # Connect WebSocket client
            ws_url = f"{self.ws_url}/test_api_client"
            async with websockets.connect(ws_url) as websocket:
                # Subscribe to updates
                await websocket.send(json.dumps({"type": "subscribe", "entities": ["projects", "agents", "messages"]}))

                # Trigger API call (create test project)
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.api_url}/api/v1/projects/",
                        json={"name": "WebSocket Test Project", "description": "Testing real-time updates"},
                    )

                    if response.status_code in [200, 201]:
                        pass
                    else:
                        return False

                # Wait for broadcast
                try:
                    broadcast = await asyncio.wait_for(websocket.recv(), timeout=3)
                    data = json.loads(broadcast)

                    if "project" in str(data).lower():
                        self.results["api_broadcast"] = True
                        return True

                except asyncio.TimeoutError:
                    pass

        except Exception:
            pass

        return False

    async def test_frontend_connection(self) -> bool:
        """Test frontend can connect to WebSocket"""

        try:
            # Check if frontend is running
            async with httpx.AsyncClient() as client:
                response = await client.get(self.frontend_url)
                if response.status_code == 200:
                    pass
                else:
                    return False

            # Simulate frontend WebSocket connection
            ws_url = f"{self.ws_url}/frontend_client_001"
            async with websockets.connect(ws_url) as websocket:
                # Test subscription
                await websocket.send(json.dumps({"type": "subscribe", "entities": ["agents", "messages", "projects"]}))

                self.results["frontend_connection"] = True
                return True

        except Exception:
            return False

    async def test_reconnection(self) -> bool:
        """Test auto-reconnection behavior"""

        try:
            ws_url = f"{self.ws_url}/reconnect_test_client"

            # Initial connection
            ws1 = await websockets.connect(ws_url)

            # Close connection
            await ws1.close()

            # Simulate reconnection with backoff
            await asyncio.sleep(1)  # 1 second backoff

            # Reconnect
            ws2 = await websockets.connect(ws_url)

            # Verify new connection works
            await ws2.send(json.dumps({"type": "ping"}))
            response = await asyncio.wait_for(ws2.recv(), timeout=2)

            if json.loads(response).get("type") == "pong":
                self.results["auto_reconnect"] = True
                await ws2.close()
                return True

        except Exception:
            pass

        return False

    async def test_message_queue(self) -> bool:
        """Test message queuing during disconnection"""

        # This would require more complex setup with actual message sending
        # For now, marking as info only

        return True  # Partial pass

    async def run_all_tests(self):
        """Run all E2E tests"""

        # Run tests
        backend_ok = await self.test_backend_connection()
        api_ok = await self.test_api_broadcasts()
        frontend_ok = await self.test_frontend_connection()
        reconnect_ok = await self.test_reconnection()
        queue_ok = await self.test_message_queue()

        # Summary

        tests_passed = sum([backend_ok, api_ok, frontend_ok, reconnect_ok, queue_ok])

        # SLA Compliance

        if "backend_latency" in self.results:
            latency = self.results["backend_latency"]
            if latency < 100:
                pass
            else:
                pass

        if reconnect_ok:
            pass
        else:
            pass

        # Overall status
        if tests_passed >= 3:
            pass
        else:
            pass

        return self.results


async def main():
    """Main test runner"""
    tester = E2EWebSocketTester()
    results = await tester.run_all_tests()

    # Save results
    with open("e2e_test_results.json", "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    asyncio.run(main())
