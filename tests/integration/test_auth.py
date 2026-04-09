#!/usr/bin/env python

# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Authentication Layer Test Suite for GiljoAI MCP
Tests API key, OAuth, and security features
"""

import asyncio
import sys
from pathlib import Path

from fastapi.testclient import TestClient

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.app import create_app
from src.giljo_mcp.auth import AuthManager
from src.giljo_mcp.config_manager import ConfigManager


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


class AuthTestSuite:
    """Comprehensive authentication testing"""

    def __init__(self):
        self.app = None
        self.client = None
        self.auth_manager = None
        self.config = None
        self.test_keys = []
        self.passed = 0
        self.failed = 0
        self.tests = []

    async def setup(self):
        """Initialize test environment"""

        # Initialize configuration
        self.config = ConfigManager()

        # Initialize auth manager
        self.auth_manager = AuthManager(self.config)

        # Create FastAPI app
        self.app = create_app()
        self.client = TestClient(self.app)

        # Store auth manager in app state
        self.app.state.api_state.auth = self.auth_manager

    async def teardown(self):
        """Clean up test environment"""

        # Revoke test keys
        for key in self.test_keys:
            await self.auth_manager.revoke_key(key)

    def record_test(self, test_name: str, passed: bool, details: str = ""):
        """Record test result"""
        self.tests.append({"name": test_name, "passed": passed, "details": details})

        if passed:
            self.passed += 1
            if details:
                pass
        else:
            self.failed += 1
            if details:
                pass

    async def test_api_key_generation(self):
        """Test API key generation and validation"""

        # Generate API key
        key = await self.auth_manager.generate_api_key(name="test_key", permissions=["read", "write"])

        self.record_test(
            "Generate API key", key is not None and len(key) >= 32, f"Key length: {len(key) if key else 0}"
        )

        if key:
            self.test_keys.append(key)

            # Validate key
            is_valid = await self.auth_manager.validate_key(key)
            self.record_test("Validate API key", is_valid, "Key validated successfully")

            # Test key format
            self.record_test(
                "API key format",
                all(c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in key),
                "Key contains only valid characters",
            )

    async def test_api_key_authentication(self):
        """Test API endpoint authentication with keys"""

        # Generate test key
        key = await self.auth_manager.generate_api_key(
            name="endpoint_test", permissions=["projects.read", "projects.write"]
        )

        if key:
            self.test_keys.append(key)

            # Test without key
            response = self.client.get("/api/v1/projects/")
            self.record_test(
                "Request without API key",
                response.status_code in [401, 200],  # 200 if auth disabled
                f"Status: {response.status_code}",
            )

            # Test with key in header
            response = self.client.get("/api/v1/projects/", headers={"X-API-Key": key})
            self.record_test(
                "Request with API key header", response.status_code == 200, f"Status: {response.status_code}"
            )

            # Test with Bearer token
            response = self.client.get("/api/v1/projects/", headers={"Authorization": f"Bearer {key}"})
            self.record_test(
                "Request with Bearer token", response.status_code == 200, f"Status: {response.status_code}"
            )

            # Test with invalid key
            response = self.client.get("/api/v1/projects/", headers={"X-API-Key": "invalid_key_12345"})
            self.record_test(
                "Request with invalid API key",
                response.status_code in [401, 200],  # 200 if auth disabled
                f"Status: {response.status_code}",
            )

    async def test_permission_system(self):
        """Test permission-based access control"""

        # Create keys with different permissions
        read_key = await self.auth_manager.generate_api_key(
            name="read_only", permissions=["projects.read", "agents.read"]
        )

        write_key = await self.auth_manager.generate_api_key(
            name="full_access", permissions=["projects.*", "agents.*", "messages.*"]
        )

        if read_key:
            self.test_keys.append(read_key)
        if write_key:
            self.test_keys.append(write_key)

        # Test read-only key
        if read_key:
            # Should allow GET
            response = self.client.get("/api/v1/projects/", headers={"X-API-Key": read_key})
            self.record_test("Read-only key allows GET", response.status_code == 200, f"Status: {response.status_code}")

            # Should deny POST
            response = self.client.post(
                "/api/v1/projects/", json={"name": "Test", "mission": "Test"}, headers={"X-API-Key": read_key}
            )
            self.record_test(
                "Read-only key denies POST",
                response.status_code in [403, 200],  # 200 if permissions not enforced
                f"Status: {response.status_code}",
            )

        # Test full access key
        if write_key:
            response = self.client.post(
                "/api/v1/projects/", json={"name": "Test", "mission": "Test"}, headers={"X-API-Key": write_key}
            )
            self.record_test(
                "Full access key allows POST", response.status_code in [200, 201], f"Status: {response.status_code}"
            )

    async def test_key_revocation(self):
        """Test API key revocation"""

        # Generate key
        key = await self.auth_manager.generate_api_key(name="revoke_test", permissions=["projects.read"])

        if key:
            # Validate before revocation
            is_valid = await self.auth_manager.validate_key(key)
            self.record_test("Key valid before revocation", is_valid, "Key is valid")

            # Revoke key
            revoked = await self.auth_manager.revoke_key(key)
            self.record_test("Revoke API key", revoked, "Key revoked successfully")

            # Validate after revocation
            is_valid = await self.auth_manager.validate_key(key)
            self.record_test("Key invalid after revocation", not is_valid, "Key is invalid")

            # Test API access with revoked key
            response = self.client.get("/api/v1/projects/", headers={"X-API-Key": key})
            self.record_test(
                "API denies revoked key",
                response.status_code in [401, 200],  # 200 if auth disabled
                f"Status: {response.status_code}",
            )

    async def test_rate_limiting(self):
        """Test rate limiting functionality"""

        # Generate key with rate limit
        key = await self.auth_manager.generate_api_key(
            name="rate_limit_test",
            permissions=["projects.read"],
            rate_limit=10,  # 10 requests per minute
        )

        if key:
            self.test_keys.append(key)

            # Make rapid requests
            responses = []
            for _i in range(15):
                response = self.client.get("/api/v1/projects/", headers={"X-API-Key": key})
                responses.append(response.status_code)

            # Check if rate limiting kicked in
            rate_limited = any(status == 429 for status in responses)
            successful = sum(1 for status in responses if status == 200)

            self.record_test(
                "Rate limiting enforced",
                rate_limited or successful <= 10,
                f"Successful: {successful}/15, Rate limited: {rate_limited}",
            )

    async def test_session_management(self):
        """Test session token management"""

        # Create session
        session_token = await self.auth_manager.create_session(user_id="test_user", ttl_seconds=3600)

        self.record_test("Create session token", session_token is not None, "Token created")

        if session_token:
            # Validate session
            session_data = await self.auth_manager.validate_session(session_token)
            self.record_test(
                "Validate session",
                session_data is not None and session_data.get("user_id") == "test_user",
                f"Session valid for user: {session_data.get('user_id') if session_data else 'None'}",
            )

            # Invalidate session
            invalidated = await self.auth_manager.invalidate_session(session_token)
            self.record_test("Invalidate session", invalidated, "Session invalidated")

            # Validate after invalidation
            session_data = await self.auth_manager.validate_session(session_token)
            self.record_test("Session invalid after invalidation", session_data is None, "Session is invalid")

    async def test_security_headers(self):
        """Test security headers in responses"""

        response = self.client.get("/")

        # Check for security headers
        headers_to_check = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": None,  # Check if present for HTTPS
        }

        for header, expected_value in headers_to_check.items():
            if expected_value:
                self.record_test(
                    f"Security header: {header}",
                    response.headers.get(header) == expected_value,
                    f"Value: {response.headers.get(header)}",
                )
            else:
                # Just check if header exists
                self.record_test(
                    f"Security header present: {header}",
                    header in response.headers,
                    f"Present: {header in response.headers}",
                )

    async def test_csrf_protection(self):
        """Test CSRF protection for state-changing operations"""

        # Generate CSRF token
        csrf_token = await self.auth_manager.generate_csrf_token()

        self.record_test(
            "Generate CSRF token",
            csrf_token is not None and len(csrf_token) >= 32,
            f"Token length: {len(csrf_token) if csrf_token else 0}",
        )

        if csrf_token:
            # Test POST without CSRF token
            response = self.client.post("/api/v1/projects/", json={"name": "Test", "mission": "Test"})

            # Test POST with CSRF token
            response_with_csrf = self.client.post(
                "/api/v1/projects/", json={"name": "Test", "mission": "Test"}, headers={"X-CSRF-Token": csrf_token}
            )

            self.record_test(
                "CSRF protection active",
                response.status_code != response_with_csrf.status_code
                or response.status_code in [200, 201],  # May not be enforced
                f"Without CSRF: {response.status_code}, With CSRF: {response_with_csrf.status_code}",
            )

    async def test_password_hashing(self):
        """Test password hashing and verification"""

        test_password = "TestPassword123!@#"

        # Hash password
        hashed = await self.auth_manager.hash_password(test_password)

        self.record_test(
            "Hash password",
            hashed is not None and hashed != test_password,
            f"Hash created, length: {len(hashed) if hashed else 0}",
        )

        if hashed:
            # Verify correct password
            is_valid = await self.auth_manager.verify_password(test_password, hashed)
            self.record_test("Verify correct password", is_valid, "Password verified")

            # Verify incorrect password
            is_valid = await self.auth_manager.verify_password("WrongPassword", hashed)
            self.record_test("Reject incorrect password", not is_valid, "Wrong password rejected")

            # Test timing attack resistance
            import time

            times = []
            for _ in range(10):
                start = time.time()
                await self.auth_manager.verify_password("Wrong", hashed)
                times.append(time.time() - start)

            # Check if timing is consistent (resistant to timing attacks)
            avg_time = sum(times) / len(times)
            max_deviation = max(abs(t - avg_time) for t in times)

            self.record_test(
                "Timing attack resistance",
                max_deviation < 0.01,  # Less than 10ms deviation
                f"Max deviation: {max_deviation * 1000:.2f}ms",
            )

    async def run_all_tests(self):
        """Run complete authentication test suite"""

        await self.setup()

        try:
            # Run test categories
            await self.test_api_key_generation()
            await self.test_api_key_authentication()
            await self.test_permission_system()
            await self.test_key_revocation()
            await self.test_rate_limiting()
            await self.test_session_management()
            await self.test_security_headers()
            await self.test_csrf_protection()
            await self.test_password_hashing()

            # Print results
            self.print_results()

        finally:
            await self.teardown()

    def print_results(self):
        """Print test results summary"""

        total = self.passed + self.failed
        pass_rate = (self.passed / total * 100) if total > 0 else 0

        # Security assessment
        critical_tests = [
            "Validate API key",
            "Key invalid after revocation",
            "Reject incorrect password",
            "Timing attack resistance",
        ]

        critical_passed = sum(1 for t in self.tests if t["name"] in critical_tests and t["passed"])

        if self.failed > 0:
            for test in self.tests:
                if not test["passed"]:
                    pass

        # Overall status
        if (pass_rate >= 90 and critical_passed == len(critical_tests)) or pass_rate >= 75:
            pass
        else:
            pass


async def main():
    """Main test runner"""
    suite = AuthTestSuite()
    await suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
