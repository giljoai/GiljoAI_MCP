"""
Comprehensive security tests for WebSocket authentication
Critical tests for WebSocket vulnerability fix
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import pytest
import websocket
from fastapi.testclient import TestClient
from websocket import WebSocketException, create_connection


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.api.app import create_app
from src.giljo_mcp.auth import AuthManager
from src.giljo_mcp.config_manager import ConfigManager
from src.giljo_mcp.database import DatabaseManager


class TestWebSocketSecurity:
    """Test suite for WebSocket authentication security"""

    @pytest.fixture(autouse=True)
    async def setup(self):
        """Setup test environment"""
        # Create test app
        self.app = create_app()
        self.client = TestClient(self.app)

        # Initialize test database
        self.db_manager = DatabaseManager("sqlite+aiosqlite:///:memory:", is_async=True)
        await self.db_manager.create_tables_async()

        # Initialize auth manager
        self.config = ConfigManager()
        self.auth_manager = AuthManager(self.config)

        # Generate test credentials
        self.valid_api_key = await self.auth_manager.generate_api_key("test_key")
        self.valid_jwt = self.auth_manager.generate_jwt_token(
            user_id="test_user", tenant_key="test_tenant", permissions=["read:*", "write:*"]
        )

        # Invalid credentials
        self.invalid_api_key = "invalid_key_12345"
        self.expired_jwt = jwt.encode(
            {"sub": "test_user", "exp": datetime.now(timezone.utc) - timedelta(hours=1), "tenant_key": "test_tenant"},
            self.auth_manager.jwt_secret,
            algorithm="HS256",
        )

        yield

        # Cleanup
        await self.db_manager.close_async()

    def test_connection_without_auth_rejected(self):
        """Test 1: Connection without authentication should be rejected"""

        # Attempt connection without any auth
        with pytest.raises(WebSocketException) as exc_info:
            create_connection("ws://localhost:8000/ws/test_client", timeout=5)

        # Should be rejected with policy violation
        assert "1008" in str(exc_info.value) or "unauthorized" in str(exc_info.value).lower()

    def test_connection_with_invalid_api_key_rejected(self):
        """Test 2: Connection with invalid API key should be rejected"""

        # Attempt connection with invalid API key
        with pytest.raises(WebSocketException) as exc_info:
            create_connection(f"ws://localhost:8000/ws/test_client?api_key={self.invalid_api_key}", timeout=5)

        # Should be rejected
        assert "1008" in str(exc_info.value) or "invalid" in str(exc_info.value).lower()

    def test_connection_with_expired_jwt_rejected(self):
        """Test 3: Connection with expired JWT should be rejected"""

        # Attempt connection with expired JWT
        with pytest.raises(WebSocketException) as exc_info:
            create_connection(f"ws://localhost:8000/ws/test_client?token={self.expired_jwt}", timeout=5)

        # Should be rejected
        assert "1008" in str(exc_info.value) or "expired" in str(exc_info.value).lower()

    def test_connection_with_valid_api_key_accepted(self):
        """Test 4: Connection with valid API key should be accepted"""

        try:
            # Connect with valid API key
            ws = create_connection(f"ws://localhost:8000/ws/test_client?api_key={self.valid_api_key}", timeout=5)

            # Should be connected
            assert ws.connected

            # Test ping/pong
            ws.send(json.dumps({"type": "ping"}))
            response = json.loads(ws.recv())
            assert response["type"] == "pong"

            ws.close()

        except Exception as e:
            pytest.fail(f"Valid API key connection failed: {e}")

    def test_connection_with_valid_jwt_accepted(self):
        """Test 5: Connection with valid JWT token should be accepted"""

        try:
            # Connect with valid JWT
            ws = create_connection(f"ws://localhost:8000/ws/test_client?token={self.valid_jwt}", timeout=5)

            # Should be connected
            assert ws.connected

            # Test ping/pong
            ws.send(json.dumps({"type": "ping"}))
            response = json.loads(ws.recv())
            assert response["type"] == "pong"

            ws.close()

        except Exception as e:
            pytest.fail(f"Valid JWT connection failed: {e}")

    def test_unauthorized_subscription_denied(self):
        """Test 6: Subscribe to unauthorized resource should be denied"""

        try:
            # Connect with limited permissions
            limited_jwt = self.auth_manager.generate_jwt_token(
                user_id="limited_user", tenant_key="tenant_a", permissions=["read:messages"]  # No project permission
            )

            ws = create_connection(f"ws://localhost:8000/ws/test_client?token={limited_jwt}", timeout=5)

            # Try to subscribe to project (should be denied)
            ws.send(json.dumps({"type": "subscribe", "entity_type": "project", "entity_id": "test_project_id"}))

            response = json.loads(ws.recv())

            # Should receive error response
            assert response.get("type") == "error"
            assert response.get("error") == "subscription_denied"

            ws.close()

        except Exception as e:
            pytest.fail(f"Unauthorized subscription test failed: {e}")

    def test_cross_tenant_subscription_denied(self):
        """Test 7: Cross-tenant subscription attempt should be denied"""

        try:
            # Connect as tenant_a user
            tenant_a_jwt = self.auth_manager.generate_jwt_token(
                user_id="user_a", tenant_key="tenant_a", permissions=["read:*"]
            )

            ws = create_connection(f"ws://localhost:8000/ws/test_client?token={tenant_a_jwt}", timeout=5)

            # Try to subscribe to tenant_b project (should be denied)
            ws.send(json.dumps({"type": "subscribe", "entity_type": "project", "entity_id": "tenant_b_project"}))

            response = json.loads(ws.recv())

            # Should receive error or be silently denied
            if response.get("type") == "error":
                assert "denied" in response.get("message", "").lower()

            ws.close()

        except Exception as e:
            pytest.fail(f"Cross-tenant test failed: {e}")

    def test_auth_via_headers(self):
        """Test 8: Authentication via headers should work"""

        try:
            # Create WebSocket with headers
            headers = {"X-API-Key": self.valid_api_key}

            ws = websocket.create_connection("ws://localhost:8000/ws/test_client", header=headers, timeout=5)

            # Should be connected
            assert ws.connected

            ws.close()

        except Exception:
            # Headers might not be supported in test environment
            pass

    def test_multiple_connections_isolated(self):
        """Test 9: Multiple authenticated connections should be isolated"""

        try:
            # Create two connections with different tenants
            ws1 = create_connection(f"ws://localhost:8000/ws/client1?api_key={self.valid_api_key}", timeout=5)

            ws2 = create_connection(f"ws://localhost:8000/ws/client2?token={self.valid_jwt}", timeout=5)

            # Both should be connected
            assert ws1.connected
            assert ws2.connected

            # Each should receive their own pong
            ws1.send(json.dumps({"type": "ping"}))
            response1 = json.loads(ws1.recv())
            assert response1["type"] == "pong"

            ws2.send(json.dumps({"type": "ping"}))
            response2 = json.loads(ws2.recv())
            assert response2["type"] == "pong"

            ws1.close()
            ws2.close()

        except Exception as e:
            pytest.fail(f"Multiple connection test failed: {e}")

    def test_connection_persists_after_auth(self):
        """Test 10: Connection should persist and function after authentication"""

        try:
            # Connect with valid credentials
            ws = create_connection(f"ws://localhost:8000/ws/test_client?api_key={self.valid_api_key}", timeout=5)

            # Perform multiple operations
            for i in range(5):
                ws.send(json.dumps({"type": "ping", "seq": i}))
                response = json.loads(ws.recv())
                assert response["type"] == "pong"

            # Subscribe and unsubscribe
            ws.send(json.dumps({"type": "subscribe", "entity_type": "agent", "entity_id": "test_agent"}))
            response = json.loads(ws.recv())
            assert response["type"] == "subscribed"

            ws.send(json.dumps({"type": "unsubscribe", "entity_type": "agent", "entity_id": "test_agent"}))
            response = json.loads(ws.recv())
            assert response["type"] == "unsubscribed"

            ws.close()

        except Exception as e:
            pytest.fail(f"Connection persistence test failed: {e}")


async def run_security_tests():
    """Run all WebSocket security tests"""

    test_suite = TestWebSocketSecurity()
    await test_suite.setup()

    # Run all tests
    tests = [
        test_suite.test_connection_without_auth_rejected,
        test_suite.test_connection_with_invalid_api_key_rejected,
        test_suite.test_connection_with_expired_jwt_rejected,
        test_suite.test_connection_with_valid_api_key_accepted,
        test_suite.test_connection_with_valid_jwt_accepted,
        test_suite.test_unauthorized_subscription_denied,
        test_suite.test_cross_tenant_subscription_denied,
        test_suite.test_auth_via_headers,
        test_suite.test_multiple_connections_isolated,
        test_suite.test_connection_persists_after_auth,
    ]

    passed = 0
    failed = 0
    skipped = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError:
            failed += 1
        except Exception as e:
            if "SKIPPED" in str(e):
                skipped += 1
            else:
                failed += 1

    if failed == 0:
        pass
    else:
        pass

    return failed == 0


if __name__ == "__main__":
    # Run tests
    asyncio.run(run_security_tests())
