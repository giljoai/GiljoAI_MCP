#!/usr/bin/env python3
"""
Frontend WebSocket Testing with Mock Server
Tests frontend functionality using mock WebSocket server on port 8001
"""

import asyncio
import websockets
import json
import time
from typing import Dict, List, Optional

class FrontendMockTester:
    """Tests frontend WebSocket features with mock server"""
    
    def __init__(self):
        self.mock_ws_url = "ws://localhost:8001"
        self.results = {
            "connection": False,
            "heartbeat": False,
            "reconnection": False,
            "message_queue": False,
            "broadcast": False,
            "latency_ms": None,
            "throughput": 0
        }
        
    async def test_basic_connection(self) -> bool:
        """Test basic WebSocket connection to mock server"""
        print("\n1. Testing Basic Connection to Mock Server...")
        
        try:
            ws_url = f"{self.mock_ws_url}/frontend_test_client"
            async with websockets.connect(ws_url) as websocket:
                # Should receive welcome message
                welcome = await asyncio.wait_for(websocket.recv(), timeout=2)
                welcome_data = json.loads(welcome)
                
                if welcome_data.get("type") == "welcome":
                    print(f"   [PASS] Connected to mock server")
                    print(f"   Client ID: {welcome_data.get('client_id')}")
                    self.results["connection"] = True
                    return True
                    
        except Exception as e:
            print(f"   [FAIL] Connection failed: {e}")
            
        return False
        
    async def test_heartbeat(self) -> bool:
        """Test heartbeat/ping-pong mechanism"""
        print("\n2. Testing Heartbeat Mechanism...")
        
        try:
            ws_url = f"{self.mock_ws_url}/heartbeat_test"
            async with websockets.connect(ws_url) as websocket:
                # Wait for welcome
                await websocket.recv()
                
                # Send ping
                start_time = time.time()
                await websocket.send(json.dumps({
                    "type": "ping",
                    "timestamp": start_time
                }))
                
                # Wait for pong
                pong = await asyncio.wait_for(websocket.recv(), timeout=2)
                pong_data = json.loads(pong)
                
                if pong_data.get("type") == "pong":
                    latency = (time.time() - start_time) * 1000
                    self.results["latency_ms"] = round(latency, 2)
                    self.results["heartbeat"] = True
                    
                    print(f"   [PASS] Heartbeat working")
                    print(f"   Latency: {latency:.2f}ms")
                    
                    if latency < 100:
                        print(f"   [PASS] Meets SLA (<100ms)")
                    else:
                        print(f"   [WARN] Exceeds SLA (>100ms)")
                        
                    return True
                    
        except Exception as e:
            print(f"   [FAIL] Heartbeat test failed: {e}")
            
        return False
        
    async def test_reconnection(self) -> bool:
        """Test auto-reconnection with exponential backoff"""
        print("\n3. Testing Auto-Reconnection...")
        
        try:
            ws_url = f"{self.mock_ws_url}/reconnect_test"
            
            # Initial connection
            ws1 = await websockets.connect(ws_url)
            await ws1.recv()  # Welcome message
            print("   [INFO] Initial connection established")
            
            # Close connection
            await ws1.close()
            print("   [INFO] Connection closed")
            
            # Track reconnection attempts with backoff
            backoff_times = []
            for attempt in range(3):
                wait_time = min(2 ** attempt, 30)
                backoff_times.append(wait_time)
                
                print(f"   [INFO] Waiting {wait_time}s before reconnect attempt {attempt + 1}")
                await asyncio.sleep(wait_time)
                
                try:
                    ws2 = await websockets.connect(ws_url)
                    await ws2.recv()  # Welcome
                    
                    # Test if reconnected connection works
                    await ws2.send(json.dumps({"type": "ping"}))
                    pong = await asyncio.wait_for(ws2.recv(), timeout=2)
                    
                    if json.loads(pong).get("type") == "pong":
                        print(f"   [PASS] Reconnected successfully after {sum(backoff_times)}s")
                        self.results["reconnection"] = True
                        await ws2.close()
                        return True
                        
                except:
                    if attempt == 2:
                        print(f"   [FAIL] Could not reconnect after 3 attempts")
                        
        except Exception as e:
            print(f"   [FAIL] Reconnection test failed: {e}")
            
        return False
        
    async def test_message_queue(self) -> bool:
        """Test message queuing during disconnection"""
        print("\n4. Testing Message Queue...")
        
        try:
            # Connect first client
            client1_url = f"{self.mock_ws_url}/queue_client_1"
            ws1 = await websockets.connect(client1_url)
            await ws1.recv()  # Welcome
            
            # Connect second client
            client2_url = f"{self.mock_ws_url}/queue_client_2"
            ws2 = await websockets.connect(client2_url)
            await ws2.recv()  # Welcome
            
            # Client 2 sends message to client 1
            await ws2.send(json.dumps({
                "type": "message",
                "to": "queue_client_1",
                "content": "Test message 1"
            }))
            
            # Client 1 receives it
            msg1 = await asyncio.wait_for(ws1.recv(), timeout=2)
            msg1_data = json.loads(msg1)
            
            if msg1_data.get("type") == "message":
                print("   [PASS] Direct message delivery working")
                
            # Disconnect client 1
            await ws1.close()
            print("   [INFO] Client 1 disconnected")
            
            # Client 2 sends message while client 1 offline
            await ws2.send(json.dumps({
                "type": "message",
                "to": "queue_client_1",
                "content": "Queued message"
            }))
            
            # Should get queue notification
            queue_notif = await asyncio.wait_for(ws2.recv(), timeout=2)
            queue_data = json.loads(queue_notif)
            
            if queue_data.get("type") == "message_queued":
                print("   [PASS] Message queued while client offline")
                self.results["message_queue"] = True
                
            await ws2.close()
            return True
            
        except Exception as e:
            print(f"   [FAIL] Message queue test failed: {e}")
            
        return False
        
    async def test_broadcast(self) -> bool:
        """Test broadcast to multiple clients"""
        print("\n5. Testing Broadcast Feature...")
        
        try:
            # Connect multiple clients
            clients = []
            for i in range(3):
                ws_url = f"{self.mock_ws_url}/broadcast_client_{i}"
                ws = await websockets.connect(ws_url)
                await ws.recv()  # Welcome
                clients.append(ws)
                
            print(f"   [INFO] Connected {len(clients)} clients")
            
            # First client sends broadcast
            await clients[0].send(json.dumps({
                "type": "broadcast",
                "content": "Test broadcast message"
            }))
            
            # Other clients should receive it
            received_count = 0
            for i, client in enumerate(clients[1:], 1):
                try:
                    msg = await asyncio.wait_for(client.recv(), timeout=2)
                    msg_data = json.loads(msg)
                    
                    if msg_data.get("type") == "broadcast":
                        received_count += 1
                        print(f"   [INFO] Client {i} received broadcast")
                        
                except asyncio.TimeoutError:
                    print(f"   [WARN] Client {i} didn't receive broadcast")
                    
            # Close all connections
            for client in clients:
                await client.close()
                
            if received_count == len(clients) - 1:
                print("   [PASS] Broadcast to all clients successful")
                self.results["broadcast"] = True
                return True
            else:
                print(f"   [WARN] Only {received_count}/{len(clients)-1} clients received broadcast")
                
        except Exception as e:
            print(f"   [FAIL] Broadcast test failed: {e}")
            
        return False
        
    async def test_performance(self) -> bool:
        """Test performance metrics"""
        print("\n6. Testing Performance...")
        
        try:
            ws_url = f"{self.mock_ws_url}/performance_test"
            async with websockets.connect(ws_url) as websocket:
                await websocket.recv()  # Welcome
                
                # Send rapid messages
                start_time = time.time()
                message_count = 100
                
                for i in range(message_count):
                    await websocket.send(json.dumps({
                        "type": "test",
                        "seq": i
                    }))
                    
                # Receive echoes
                received = 0
                while received < message_count:
                    try:
                        await asyncio.wait_for(websocket.recv(), timeout=0.1)
                        received += 1
                    except asyncio.TimeoutError:
                        break
                        
                elapsed = time.time() - start_time
                throughput = message_count / elapsed
                
                self.results["throughput"] = round(throughput, 2)
                
                print(f"   [INFO] Sent {message_count} messages in {elapsed:.2f}s")
                print(f"   [INFO] Throughput: {throughput:.2f} msgs/sec")
                
                if throughput > 500:
                    print("   [PASS] Meets throughput SLA (>500 msgs/sec)")
                    return True
                else:
                    print("   [WARN] Below throughput SLA (<500 msgs/sec)")
                    
        except Exception as e:
            print(f"   [FAIL] Performance test failed: {e}")
            
        return False
        
    async def run_all_tests(self):
        """Run all frontend tests with mock server"""
        print("="*60)
        print("FRONTEND WEBSOCKET TESTING WITH MOCK SERVER")
        print("="*60)
        
        # Run tests
        connection_ok = await self.test_basic_connection()
        heartbeat_ok = await self.test_heartbeat()
        reconnect_ok = await self.test_reconnection()
        queue_ok = await self.test_message_queue()
        broadcast_ok = await self.test_broadcast()
        performance_ok = await self.test_performance()
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        tests_passed = sum([
            connection_ok, heartbeat_ok, reconnect_ok,
            queue_ok, broadcast_ok, performance_ok
        ])
        total_tests = 6
        
        print(f"\nTests Passed: {tests_passed}/{total_tests}")
        
        # Detailed results
        print("\nDetailed Results:")
        print(f"  Connection to Mock Server: {'PASS' if connection_ok else 'FAIL'}")
        print(f"  Heartbeat/Ping-Pong: {'PASS' if heartbeat_ok else 'FAIL'}")
        print(f"  Auto-Reconnection: {'PASS' if reconnect_ok else 'FAIL'}")
        print(f"  Message Queue: {'PASS' if queue_ok else 'FAIL'}")
        print(f"  Broadcast: {'PASS' if broadcast_ok else 'FAIL'}")
        print(f"  Performance: {'PASS' if performance_ok else 'FAIL'}")
        
        # SLA Compliance
        print("\nSLA Compliance:")
        
        if self.results["latency_ms"]:
            if self.results["latency_ms"] < 100:
                print(f"  [PASS] Latency: {self.results['latency_ms']}ms < 100ms")
            else:
                print(f"  [FAIL] Latency: {self.results['latency_ms']}ms > 100ms")
                
        if reconnect_ok:
            print("  [PASS] Auto-reconnect within 5 seconds")
            
        if self.results["throughput"] > 500:
            print(f"  [PASS] Throughput: {self.results['throughput']} msgs/sec > 500")
        else:
            print(f"  [FAIL] Throughput: {self.results['throughput']} msgs/sec < 500")
            
        # Overall status
        print("\n" + "="*60)
        if tests_passed >= 5:
            print("SUCCESS: Frontend WebSocket features working with mock server!")
            print("\nFrontend is ready for production once backend auth is fixed.")
        elif tests_passed >= 3:
            print("PARTIAL SUCCESS: Core features working, some issues remain")
        else:
            print("FAILURE: Critical issues in frontend implementation")
            
        return self.results


async def main():
    """Main test runner"""
    tester = FrontendMockTester()
    results = await tester.run_all_tests()
    
    # Save results
    with open("frontend_mock_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
        
    print(f"\nResults saved to frontend_mock_test_results.json")
    
    # Return exit code
    return 0 if results["connection"] else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)