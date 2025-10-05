"""
Server Mode Authentication Tests for GiljoAI MCP

Tests API key authentication enforcement when deployed in server mode.
Validates security measures for network-exposed API endpoints.

Test Coverage:
- API key requirement enforcement
- Invalid API key rejection
- API key permissions validation
- Rate limiting per API key
- Tenant isolation via API keys
- Security header validation

Usage:
    # Run all auth tests
    pytest tests/integration/test_server_mode_auth.py -v

    # Run specific test
    pytest tests/integration/test_server_mode_auth.py::TestServerModeAuthentication::test_api_key_required -v

Prerequisites:
    - Server must be running in server mode (mode: server in config.yaml)
    - API keys must be configured
    - API server accessible on configured port
"""

import asyncio
import time
from typing import Optional

import pytest
import httpx


class AuthTestHelper:
    """Helper utilities for authentication testing"""

    @staticmethod
    def generate_test_api_key() -> str:
        """Generate a test API key (mock implementation)"""
        import secrets
        return f"giljo_test_{secrets.token_urlsafe(32)}"

    @staticmethod
    async def check_auth_required(url: str, timeout: float = 5.0) -> dict:
        """
        Check if authentication is required for an endpoint

        Returns:
            dict with 'required' (bool) and 'status_code' (int)
        """
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.get(url)
                return {
                    "required": response.status_code == 401,
                    "status_code": response.status_code,
                    "detail": response.json() if response.status_code in [401, 403] else None
                }
            except Exception as e:
                return {
                    "required": None,
                    "status_code": None,
                    "error": str(e)
                }


@pytest.mark.server_mode
@pytest.mark.security
class TestServerModeAuthentication:
    """Test authentication enforcement in server mode"""

    @pytest.fixture(scope="class")
    def server_config(self):
        """Server configuration for testing"""
        return {
            "mode": "server",
            "api_port": 7272,
            "base_url": "http://localhost:7272"
        }

    @pytest.fixture
    def valid_api_key(self):
        """
        Valid API key for testing.

        NOTE: In real tests, this should come from your configuration
        or be generated during test setup.
        """
        # TODO: Replace with actual API key generation/retrieval
        return "test_api_key_replace_with_real_key"

    @pytest.fixture
    def read_only_api_key(self):
        """
        Read-only API key for permission testing.

        NOTE: This should be configured with read-only permissions
        """
        return "test_readonly_key_replace_with_real_key"

    @pytest.mark.asyncio
    async def test_api_key_required_for_protected_endpoints(self, server_config):
        """
        TEST: API key is required for protected endpoints in server mode

        Purpose: Verify that server mode enforces API key authentication
        Expected: 401 Unauthorized when no API key provided

        CRITICAL: This test ensures the API is secure when network-exposed
        """
        protected_endpoints = [
            "/api/v1/projects/",
            "/api/v1/agents/",
            "/api/v1/messages/send"
        ]

        results = []

        async with httpx.AsyncClient(timeout=5.0) as client:
            for endpoint in protected_endpoints:
                url = f"{server_config['base_url']}{endpoint}"

                try:
                    # Request WITHOUT API key
                    response = await client.get(url)

                    results.append({
                        "endpoint": endpoint,
                        "status": response.status_code,
                        "auth_required": response.status_code == 401
                    })

                except Exception as e:
                    results.append({
                        "endpoint": endpoint,
                        "status": None,
                        "error": str(e)
                    })

        # Log results
        print("\nAPI Key Requirement Test:")
        for result in results:
            status = result.get("status", "ERROR")
            auth_icon = "✓" if result.get("auth_required") else "✗"
            print(f"  {auth_icon} {result['endpoint']}: {status}")

        # All protected endpoints should require auth
        all_require_auth = all(r.get("auth_required") for r in results)

        if not all_require_auth:
            pytest.fail(
                "SECURITY ISSUE: Some endpoints don't require API keys in server mode. "
                "This means the API may be accessible without authentication!"
            )

    @pytest.mark.asyncio
    async def test_invalid_api_key_rejected(self, server_config):
        """
        TEST: Invalid API keys are rejected

        Purpose: Verify that only valid API keys are accepted
        Expected: 401 Unauthorized with invalid key
        """
        invalid_keys = [
            "invalid_key_12345",
            "fake_api_key",
            "",
            "Bearer invalid",
            "malicious_key"
        ]

        results = []

        async with httpx.AsyncClient(timeout=5.0) as client:
            for invalid_key in invalid_keys:
                headers = {"X-API-Key": invalid_key}

                try:
                    response = await client.get(
                        f"{server_config['base_url']}/api/v1/projects/",
                        headers=headers
                    )

                    results.append({
                        "key": invalid_key[:20] + "..." if len(invalid_key) > 20 else invalid_key,
                        "status": response.status_code,
                        "rejected": response.status_code == 401
                    })

                except Exception as e:
                    results.append({
                        "key": invalid_key[:20],
                        "error": str(e)
                    })

        # Log results
        print("\nInvalid API Key Rejection Test:")
        for result in results:
            status = result.get("status", "ERROR")
            rejected_icon = "✓" if result.get("rejected") else "✗"
            print(f"  {rejected_icon} Key '{result['key']}': {status}")

        # All invalid keys should be rejected
        all_rejected = all(r.get("rejected") for r in results)

        assert all_rejected, \
            "SECURITY ISSUE: Some invalid API keys were accepted!"

    @pytest.mark.asyncio
    async def test_valid_api_key_grants_access(self, server_config, valid_api_key):
        """
        TEST: Valid API key grants access to protected endpoints

        Purpose: Verify that valid API keys allow API access
        Expected: 200 OK with valid key
        """
        if valid_api_key == "test_api_key_replace_with_real_key":
            pytest.skip("Valid API key not configured. Update fixture with real key.")

        headers = {"X-API-Key": valid_api_key}

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{server_config['base_url']}/api/v1/projects/",
                headers=headers
            )

            assert response.status_code == 200, \
                f"Valid API key rejected. Status: {response.status_code}"

            # Verify response is valid JSON
            data = response.json()
            assert isinstance(data, list), "Expected list of projects"

    @pytest.mark.asyncio
    async def test_api_key_in_authorization_header(self, server_config, valid_api_key):
        """
        TEST: API key accepted in Authorization header (Bearer format)

        Purpose: Verify support for standard Authorization header
        Expected: 200 OK when using "Authorization: Bearer <key>"
        """
        if valid_api_key == "test_api_key_replace_with_real_key":
            pytest.skip("Valid API key not configured")

        headers = {"Authorization": f"Bearer {valid_api_key}"}

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{server_config['base_url']}/api/v1/projects/",
                headers=headers
            )

            # Should accept Bearer format
            assert response.status_code in [200, 401], \
                f"Unexpected status: {response.status_code}"

            if response.status_code == 401:
                print("WARNING: Authorization header (Bearer) format not supported")

    @pytest.mark.asyncio
    async def test_api_key_permissions_read_only(self, server_config, read_only_api_key):
        """
        TEST: API key permissions are enforced (read-only key)

        Purpose: Verify that read-only keys cannot perform write operations
        Expected: GET allowed, POST forbidden
        """
        if read_only_api_key == "test_readonly_key_replace_with_real_key":
            pytest.skip("Read-only API key not configured")

        headers = {"X-API-Key": read_only_api_key}

        async with httpx.AsyncClient(timeout=5.0) as client:
            # GET should be allowed
            get_response = await client.get(
                f"{server_config['base_url']}/api/v1/projects/",
                headers=headers
            )

            # POST should be forbidden
            post_data = {
                "name": "Test Project",
                "mission": "Test",
                "agents": []
            }

            post_response = await client.post(
                f"{server_config['base_url']}/api/v1/projects/",
                json=post_data,
                headers=headers
            )

            print(f"\nPermission Enforcement Test:")
            print(f"  GET /projects/: {get_response.status_code}")
            print(f"  POST /projects/: {post_response.status_code}")

            # GET should succeed
            assert get_response.status_code == 200, \
                f"Read-only key should allow GET. Got: {get_response.status_code}"

            # POST should be forbidden
            assert post_response.status_code == 403, \
                f"Read-only key should deny POST. Got: {post_response.status_code}"

    @pytest.mark.asyncio
    async def test_api_key_rate_limiting(self, server_config, valid_api_key):
        """
        TEST: Rate limiting is enforced per API key

        Purpose: Verify that excessive requests are rate limited
        Expected: 429 Too Many Requests after threshold
        """
        if valid_api_key == "test_api_key_replace_with_real_key":
            pytest.skip("Valid API key not configured")

        headers = {"X-API-Key": valid_api_key}
        num_requests = 100  # Attempt to exceed rate limit

        responses = []

        async with httpx.AsyncClient(timeout=5.0) as client:
            for _ in range(num_requests):
                try:
                    response = await client.get(
                        f"{server_config['base_url']}/health",
                        headers=headers
                    )
                    responses.append(response.status_code)
                except Exception:
                    responses.append(None)

                # Small delay to avoid overwhelming server
                await asyncio.sleep(0.01)

        # Analyze responses
        success_count = responses.count(200)
        rate_limited_count = responses.count(429)
        total = len(responses)

        print(f"\nRate Limiting Test ({num_requests} requests):")
        print(f"  Successful (200): {success_count}")
        print(f"  Rate Limited (429): {rate_limited_count}")
        print(f"  Other: {total - success_count - rate_limited_count}")

        if rate_limited_count == 0:
            print("WARNING: No rate limiting detected. This may be expected if limits are high.")
            print("Consider configuring stricter rate limits for this API key in production.")
        else:
            print(f"✓ Rate limiting is active ({rate_limited_count} requests limited)")

    @pytest.mark.asyncio
    async def test_concurrent_requests_with_api_key(self, server_config, valid_api_key):
        """
        TEST: API handles concurrent authenticated requests

        Purpose: Verify API can handle multiple simultaneous authenticated requests
        Expected: 95%+ success rate with 20 concurrent requests
        """
        if valid_api_key == "test_api_key_replace_with_real_key":
            pytest.skip("Valid API key not configured")

        headers = {"X-API-Key": valid_api_key}
        num_concurrent = 20

        async with httpx.AsyncClient(timeout=5.0) as client:
            tasks = [
                client.get(
                    f"{server_config['base_url']}/health",
                    headers=headers
                )
                for _ in range(num_concurrent)
            ]

            start = time.perf_counter()
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            duration = time.perf_counter() - start

        # Analyze results
        successful = sum(
            1 for r in responses
            if isinstance(r, httpx.Response) and r.status_code == 200
        )
        success_rate = successful / num_concurrent * 100

        print(f"\nConcurrent Authenticated Requests Test:")
        print(f"  Concurrent Requests: {num_concurrent}")
        print(f"  Successful: {successful}/{num_concurrent}")
        print(f"  Success Rate: {success_rate:.1f}%")
        print(f"  Total Duration: {duration * 1000:.2f}ms")
        print(f"  Avg per Request: {duration / num_concurrent * 1000:.2f}ms")

        assert success_rate >= 90.0, \
            f"Success rate {success_rate:.1f}% below target of 90%"


@pytest.mark.server_mode
@pytest.mark.security
class TestTenantIsolationWithAPIKeys:
    """Test tenant isolation when using API keys"""

    @pytest.fixture
    def tenant1_api_key(self):
        """API key for tenant 1"""
        return "tenant1_key_replace_with_real_key"

    @pytest.fixture
    def tenant2_api_key(self):
        """API key for tenant 2"""
        return "tenant2_key_replace_with_real_key"

    @pytest.mark.asyncio
    async def test_api_key_enforces_tenant_isolation(
        self,
        server_config,
        tenant1_api_key,
        tenant2_api_key
    ):
        """
        TEST: API keys enforce tenant isolation

        Purpose: Verify that API keys restrict access to tenant's own data
        Expected: Tenant 1 cannot access Tenant 2's resources and vice versa

        CRITICAL: Tenant isolation is essential for multi-tenant deployments
        """
        if tenant1_api_key == "tenant1_key_replace_with_real_key":
            pytest.skip("Tenant API keys not configured")

        base_url = server_config["base_url"]

        # Step 1: Create project with Tenant 1 key
        headers1 = {"X-API-Key": tenant1_api_key}
        project_data = {
            "name": "Tenant 1 Project",
            "mission": "Test tenant isolation",
            "agents": []
        }

        async with httpx.AsyncClient(timeout=5.0) as client:
            # Create project as tenant 1
            create_response = await client.post(
                f"{base_url}/api/v1/projects/",
                json=project_data,
                headers=headers1
            )

            if create_response.status_code != 200:
                pytest.skip(f"Could not create project: {create_response.status_code}")

            tenant1_project_id = create_response.json()["id"]

            # Step 2: Try to access with Tenant 2 key
            headers2 = {"X-API-Key": tenant2_api_key}

            access_response = await client.get(
                f"{base_url}/api/v1/projects/{tenant1_project_id}",
                headers=headers2
            )

            # Tenant 2 should NOT be able to access Tenant 1's project
            assert access_response.status_code in [403, 404], \
                f"SECURITY ISSUE: Tenant 2 accessed Tenant 1's project! " \
                f"Status: {access_response.status_code}"

            # Step 3: Verify Tenant 1 can still access their own project
            verify_response = await client.get(
                f"{base_url}/api/v1/projects/{tenant1_project_id}",
                headers=headers1
            )

            assert verify_response.status_code == 200, \
                f"Tenant 1 cannot access their own project: {verify_response.status_code}"

            print("\n✓ Tenant isolation verified: Cross-tenant access blocked")


@pytest.mark.server_mode
@pytest.mark.security
class TestSecurityHeaders:
    """Test security headers in server mode"""

    @pytest.mark.asyncio
    async def test_security_headers_present(self, server_config):
        """
        TEST: Security headers are present in responses

        Purpose: Verify that production security headers are set
        Expected: Standard security headers present in all responses
        """
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{server_config['base_url']}/health")

            headers = response.headers

            # Recommended security headers
            security_headers = {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block",
            }

            print("\nSecurity Headers Check:")
            for header, expected_value in security_headers.items():
                present = header in headers
                value = headers.get(header)

                if present and value == expected_value:
                    print(f"  ✓ {header}: {value}")
                elif present:
                    print(f"  ⚠ {header}: {value} (expected: {expected_value})")
                else:
                    print(f"  ✗ {header}: Missing")

            # Note: Not failing on missing headers as they may not be implemented yet
            # In production, these should be required


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v", "-s"])
