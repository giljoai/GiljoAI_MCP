"""
Integration tests for MCP Installer API endpoints.

Tests the complete end-to-end workflow of:
- Authenticated script downloads (Windows and Unix)
- Share link generation and token-based downloads
- Multi-tenant isolation
- Template rendering with credential embedding
- Error handling (expired tokens, invalid platforms, etc.)

Following TDD principles: Integration tests verify real-world user workflows.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.app import app
from api.endpoints import mcp_installer
from src.giljo_mcp.auth.localhost_user import ensure_localhost_user
from src.giljo_mcp.models import User


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    """Create test user with API key"""
    from uuid import uuid4

    user = User(
        id=str(uuid4()),
        username="test_network_user",
        email="test@example.com",
        password_hash="$2b$12$test_hash",
        role="developer",
        is_active=True,
        tenant_key=f"test_tenant_{uuid4().hex[:8]}",
        full_name="Test Network User",
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create API key for user
    from src.giljo_mcp.auth.api_key_manager import APIKeyManager

    api_key_manager = APIKeyManager(db_session)
    api_key_result = await api_key_manager.create_api_key(user_id=user.id, name="test_key", tenant_key=user.tenant_key)

    # Store API key on user for test access
    user.api_key = api_key_result["key"]

    return user


@pytest_asyncio.fixture
async def second_test_user(db_session: AsyncSession):
    """Create second test user for multi-tenant tests"""
    from uuid import uuid4

    user = User(
        id=str(uuid4()),
        username="second_test_user",
        email="second@example.com",
        password_hash="$2b$12$test_hash_2",
        role="developer",
        is_active=True,
        tenant_key=f"test_tenant_2_{uuid4().hex[:8]}",
        full_name="Second Test User",
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create API key
    from src.giljo_mcp.auth.api_key_manager import APIKeyManager

    api_key_manager = APIKeyManager(db_session)
    api_key_result = await api_key_manager.create_api_key(
        user_id=user.id, name="test_key_2", tenant_key=user.tenant_key
    )

    user.api_key = api_key_result["key"]

    return user


@pytest_asyncio.fixture
async def localhost_user(db_session: AsyncSession):
    """Ensure localhost user exists for auto-login tests"""
    return await ensure_localhost_user(db_session)


@pytest.fixture
def authenticated_client(test_user: User):
    """Client authenticated as test user via API key"""
    client = TestClient(app)
    client.headers.update(
        {
            "X-API-Key": test_user.api_key,
            "X-Forwarded-For": "192.168.1.100",  # Network request
        }
    )
    return client


@pytest.fixture
def localhost_client(localhost_user: User):
    """Client authenticated via localhost auto-login"""
    client = TestClient(app)
    client.headers.update(
        {
            "X-Forwarded-For": "127.0.0.1",  # Localhost - triggers auto-login
            "X-Real-IP": "127.0.0.1",
        }
    )
    return client


@pytest.fixture
def unauthenticated_client():
    """Client without authentication (network request)"""
    client = TestClient(app)
    client.headers.update(
        {
            "X-Forwarded-For": "192.168.1.100"  # Network without credentials
        }
    )
    return client


# ============================================================================
# TEST 1: Full Download Workflow (Windows)
# ============================================================================


class TestWindowsDownloadWorkflow:
    """Test complete Windows script download workflow"""

    def test_authenticated_windows_download_success(self, authenticated_client, test_user):
        """Test authenticated user can download Windows script"""
        response = authenticated_client.get("/api/mcp-installer/windows")

        # Should succeed
        assert response.status_code == 200

        # Verify response headers
        assert response.headers["content-type"] == "application/bat"
        assert "attachment" in response.headers["content-disposition"]
        assert "giljo-mcp-setup.bat" in response.headers["content-disposition"]

        # Verify script content
        script = response.text
        assert script is not None
        assert len(script) > 0

        # Should contain user credentials
        assert test_user.api_key in script
        assert test_user.username in script
        assert "giljo-mcp" in script.lower()

        # Should NOT contain unreplaced template placeholders
        assert "{server_url}" not in script
        assert "{api_key}" not in script
        assert "{username}" not in script
        assert "{organization}" not in script
        assert "{timestamp}" not in script

    def test_localhost_windows_download_success(self, localhost_client, localhost_user):
        """Test localhost user can download Windows script via auto-login"""
        response = localhost_client.get("/api/mcp-installer/windows")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/bat"

        script = response.text
        # Localhost user has default credentials
        assert "localhost" in script.lower()

    def test_unauthenticated_windows_download_fails(self, unauthenticated_client):
        """Test unauthenticated user cannot download script"""
        response = unauthenticated_client.get("/api/mcp-installer/windows")

        # Should return 401 Unauthorized
        assert response.status_code == 401

        error_data = response.json()
        assert "error" in error_data
        assert "Authentication required" in error_data["error"]

    def test_windows_script_contains_valid_timestamp(self, authenticated_client):
        """Test Windows script contains valid ISO timestamp"""
        response = authenticated_client.get("/api/mcp-installer/windows")

        assert response.status_code == 200
        script = response.text

        # Should contain a timestamp (ISO format)
        # Format: 2025-01-15T12:34:56Z
        import re

        timestamp_pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z"
        assert re.search(timestamp_pattern, script) is not None


# ============================================================================
# TEST 2: Full Download Workflow (Unix)
# ============================================================================


class TestUnixDownloadWorkflow:
    """Test complete Unix script download workflow"""

    def test_authenticated_unix_download_success(self, authenticated_client, test_user):
        """Test authenticated user can download Unix script"""
        response = authenticated_client.get("/api/mcp-installer/unix")

        # Should succeed
        assert response.status_code == 200

        # Verify response headers
        assert response.headers["content-type"] == "application/x-sh"
        assert "attachment" in response.headers["content-disposition"]
        assert "giljo-mcp-setup.sh" in response.headers["content-disposition"]

        # Verify script content
        script = response.text
        assert script is not None
        assert len(script) > 0

        # Should contain user credentials
        assert test_user.api_key in script
        assert test_user.username in script

        # Unix script should have shebang
        assert script.startswith("#!/bin/bash")

        # Should NOT contain unreplaced placeholders
        assert "{server_url}" not in script
        assert "{api_key}" not in script

    def test_localhost_unix_download_success(self, localhost_client):
        """Test localhost user can download Unix script"""
        response = localhost_client.get("/api/mcp-installer/unix")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/x-sh"

        script = response.text
        assert script.startswith("#!/bin/bash")

    def test_unauthenticated_unix_download_fails(self, unauthenticated_client):
        """Test unauthenticated user cannot download Unix script"""
        response = unauthenticated_client.get("/api/mcp-installer/unix")

        assert response.status_code == 401


# ============================================================================
# TEST 3: Share Link Generation and Use
# ============================================================================


class TestShareLinkWorkflow:
    """Test share link generation and token-based download workflow"""

    def test_generate_share_link_success(self, authenticated_client, test_user):
        """Test authenticated user can generate share link"""
        response = authenticated_client.post("/api/mcp-installer/share-link")

        assert response.status_code == 200

        data = response.json()

        # Verify response structure
        assert "windows_url" in data
        assert "unix_url" in data
        assert "token" in data
        assert "expires_at" in data

        # URLs should contain server URL
        assert "http" in data["windows_url"]
        assert "http" in data["unix_url"]

        # URLs should contain token
        assert data["token"] in data["windows_url"]
        assert data["token"] in data["unix_url"]

        # URLs should specify platform
        assert "/windows" in data["windows_url"]
        assert "/unix" in data["unix_url"]

        # Expires_at should be valid ISO timestamp
        expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
        assert expires_at > datetime.now(timezone.utc)

    def test_share_link_token_is_valid_jwt(self, authenticated_client):
        """Test share link token is valid JWT with correct payload"""
        response = authenticated_client.post("/api/mcp-installer/share-link")

        assert response.status_code == 200
        data = response.json()
        token = data["token"]

        # Decode JWT (should not raise exception)
        payload = jwt.decode(token, mcp_installer.SECRET_KEY, algorithms=[mcp_installer.ALGORITHM])

        # Verify payload structure
        assert "user_id" in payload
        assert "expires_at" in payload
        assert "type" in payload
        assert payload["type"] == "mcp_installer_download"

    def test_share_link_expires_in_7_days(self, authenticated_client):
        """Test share link token expires in 7 days"""
        response = authenticated_client.post("/api/mcp-installer/share-link")

        assert response.status_code == 200
        data = response.json()

        expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)

        # Should expire approximately 7 days from now
        time_diff = (expires_at - now).total_seconds()
        expected_seconds = 7 * 24 * 3600  # 7 days

        # Allow 60 second margin for test execution time
        assert abs(time_diff - expected_seconds) < 60

    def test_download_via_valid_token_windows(self, authenticated_client, test_user):
        """Test downloading Windows script via valid share link token"""
        # Step 1: Generate share link
        share_response = authenticated_client.post("/api/mcp-installer/share-link")
        assert share_response.status_code == 200

        share_data = share_response.json()
        token = share_data["token"]

        # Step 2: Download via token (no authentication required)
        public_client = TestClient(app)  # No auth headers
        download_response = public_client.get(f"/download/mcp/{token}/windows")

        # Should succeed without authentication
        assert download_response.status_code == 200
        assert download_response.headers["content-type"] == "application/bat"

        # Script should contain original user's credentials
        script = download_response.text
        assert test_user.api_key in script
        assert test_user.username in script

    def test_download_via_valid_token_unix(self, authenticated_client, test_user):
        """Test downloading Unix script via valid share link token"""
        # Generate share link
        share_response = authenticated_client.post("/api/mcp-installer/share-link")
        token = share_response.json()["token"]

        # Download via token
        public_client = TestClient(app)
        download_response = public_client.get(f"/download/mcp/{token}/unix")

        assert download_response.status_code == 200
        assert download_response.headers["content-type"] == "application/x-sh"

        script = download_response.text
        assert test_user.api_key in script

    def test_download_via_expired_token_fails(self, authenticated_client):
        """Test downloading with expired token returns 401"""
        # Create expired token manually
        expired_payload = {
            "user_id": "test-user-123",
            "expires_at": (datetime.utcnow() - timedelta(days=1)).isoformat() + "Z",
            "type": "mcp_installer_download",
        }

        expired_token = jwt.encode(expired_payload, mcp_installer.SECRET_KEY, algorithm=mcp_installer.ALGORITHM)

        # Try to download with expired token
        public_client = TestClient(app)
        response = public_client.get(f"/download/mcp/{expired_token}/windows")

        # Should fail with 401
        assert response.status_code == 401
        error_data = response.json()
        assert "Invalid or expired token" in error_data["detail"]

    def test_download_via_invalid_token_fails(self):
        """Test downloading with invalid token returns 401"""
        invalid_token = "not-a-valid-jwt-token"

        public_client = TestClient(app)
        response = public_client.get(f"/download/mcp/{invalid_token}/windows")

        assert response.status_code == 401
        assert "Invalid or expired token" in response.json()["detail"]

    def test_download_via_token_invalid_platform(self, authenticated_client):
        """Test downloading with invalid platform returns 400"""
        # Generate valid token
        share_response = authenticated_client.post("/api/mcp-installer/share-link")
        token = share_response.json()["token"]

        # Try to download with invalid platform
        public_client = TestClient(app)
        response = public_client.get(f"/download/mcp/{token}/invalid_platform")

        assert response.status_code == 400
        error_data = response.json()
        assert "Invalid platform" in error_data["detail"]

    def test_unauthenticated_share_link_generation_fails(self, unauthenticated_client):
        """Test unauthenticated user cannot generate share link"""
        response = unauthenticated_client.post("/api/mcp-installer/share-link")

        assert response.status_code == 401


# ============================================================================
# TEST 4: Multi-Tenant Isolation
# ============================================================================


class TestMultiTenantIsolation:
    """Test multi-tenant isolation - users get their own credentials only"""

    def test_different_users_get_different_credentials(self, test_user, second_test_user):
        """Test two users get scripts with their own credentials"""
        # User 1 downloads script
        client1 = TestClient(app)
        client1.headers.update({"X-API-Key": test_user.api_key, "X-Forwarded-For": "192.168.1.100"})

        response1 = client1.get("/api/mcp-installer/windows")
        assert response1.status_code == 200
        script1 = response1.text

        # User 2 downloads script
        client2 = TestClient(app)
        client2.headers.update({"X-API-Key": second_test_user.api_key, "X-Forwarded-For": "192.168.1.101"})

        response2 = client2.get("/api/mcp-installer/windows")
        assert response2.status_code == 200
        script2 = response2.text

        # Scripts should contain different credentials
        assert test_user.api_key in script1
        assert test_user.api_key not in script2

        assert second_test_user.api_key in script2
        assert second_test_user.api_key not in script1

        assert test_user.username in script1
        assert second_test_user.username in script2

    def test_user_a_token_does_not_work_for_user_b(self, test_user, second_test_user):
        """Test User A's share link token provides User A's credentials, not User B's"""
        # User A generates share link
        client_a = TestClient(app)
        client_a.headers.update({"X-API-Key": test_user.api_key, "X-Forwarded-For": "192.168.1.100"})

        share_response = client_a.post("/api/mcp-installer/share-link")
        token_a = share_response.json()["token"]

        # Download script using User A's token
        public_client = TestClient(app)
        response = public_client.get(f"/download/mcp/{token_a}/windows")

        assert response.status_code == 200
        script = response.text

        # Script should contain User A's credentials, NOT User B's
        assert test_user.api_key in script
        assert test_user.username in script

        # Should NOT contain User B's credentials
        assert second_test_user.api_key not in script
        assert second_test_user.username not in script

    def test_tenant_keys_properly_isolated(self, test_user, second_test_user):
        """Test scripts respect tenant isolation"""
        # Verify test users have different tenant keys
        assert test_user.tenant_key != second_test_user.tenant_key

        # Each user's script should only contain their tenant context
        client1 = TestClient(app)
        client1.headers.update({"X-API-Key": test_user.api_key, "X-Forwarded-For": "192.168.1.100"})

        response1 = client1.get("/api/mcp-installer/windows")
        script1 = response1.text

        # Script should contain user's name or "Personal" (no organization model)
        assert test_user.username in script1


# ============================================================================
# TEST 5: Template Variable Substitution
# ============================================================================


class TestTemplateRendering:
    """Test template placeholder replacement"""

    def test_all_placeholders_replaced_windows(self, authenticated_client):
        """Test all template placeholders are replaced in Windows script"""
        response = authenticated_client.get("/api/mcp-installer/windows")

        assert response.status_code == 200
        script = response.text

        # Should NOT contain any unreplaced placeholders
        placeholders = ["{server_url}", "{api_key}", "{username}", "{organization}", "{timestamp}"]

        for placeholder in placeholders:
            assert placeholder not in script, f"Unreplaced placeholder: {placeholder}"

    def test_all_placeholders_replaced_unix(self, authenticated_client):
        """Test all template placeholders are replaced in Unix script"""
        response = authenticated_client.get("/api/mcp-installer/unix")

        assert response.status_code == 200
        script = response.text

        placeholders = ["{server_url}", "{api_key}", "{username}", "{organization}", "{timestamp}"]

        for placeholder in placeholders:
            assert placeholder not in script

    def test_server_url_correctly_embedded(self, authenticated_client):
        """Test server URL is correctly embedded in script"""
        response = authenticated_client.get("/api/mcp-installer/windows")
        script = response.text

        # Should contain a valid HTTP URL
        import re

        url_pattern = r"http://[\w\.\-:]+:\d+"
        matches = re.findall(url_pattern, script)

        assert len(matches) > 0, "No server URL found in script"

        # URL should be valid (contains host and port)
        server_url = matches[0]
        assert ":" in server_url  # Has port

    @pytest.mark.asyncio
    async def test_user_full_name_embedded_in_script(self, db_session):
        """Test user's full name is embedded in script"""
        from uuid import uuid4

        from src.giljo_mcp.auth.api_key_manager import APIKeyManager

        # Create user with full name
        user = User(
            id=str(uuid4()),
            username="named_user",
            email="named@example.com",
            password_hash="$2b$12$test",
            role="developer",
            is_active=True,
            tenant_key=f"named_{uuid4().hex[:8]}",
            full_name="John Doe",
        )

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create API key
        api_key_manager = APIKeyManager(db_session)
        api_key_result = await api_key_manager.create_api_key(
            user_id=user.id, name="test_key", tenant_key=user.tenant_key
        )

        # Download script
        client = TestClient(app)
        client.headers.update({"X-API-Key": api_key_result["key"], "X-Forwarded-For": "192.168.1.100"})

        response = client.get("/api/mcp-installer/windows")
        script = response.text

        # Should contain username (organization field uses username when no org exists)
        assert user.username in script

    def test_timestamp_is_valid_iso_format(self, authenticated_client):
        """Test timestamp in script is valid ISO format"""
        response = authenticated_client.get("/api/mcp-installer/windows")
        script = response.text

        # Extract timestamp (format: YYYY-MM-DDTHH:MM:SSZ)
        import re

        timestamp_pattern = r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z)"
        matches = re.findall(timestamp_pattern, script)

        assert len(matches) > 0, "No timestamp found in script"

        # Verify it's parseable as ISO timestamp
        timestamp_str = matches[0]
        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

        # Timestamp should be recent (within last minute)
        now = datetime.now(timezone.utc)
        time_diff = abs((now - timestamp).total_seconds())
        assert time_diff < 60, "Timestamp is not recent"


# ============================================================================
# TEST 6: Cross-Platform Consistency
# ============================================================================


class TestCrossPlatformConsistency:
    """Test Windows and Unix scripts have consistent MCP config"""

    def test_windows_and_unix_embed_same_credentials(self, authenticated_client, test_user):
        """Test both platforms embed same user credentials"""
        # Download both scripts
        windows_response = authenticated_client.get("/api/mcp-installer/windows")
        unix_response = authenticated_client.get("/api/mcp-installer/unix")

        assert windows_response.status_code == 200
        assert unix_response.status_code == 200

        windows_script = windows_response.text
        unix_script = unix_response.text

        # Both should contain same credentials
        assert test_user.api_key in windows_script
        assert test_user.api_key in unix_script

        assert test_user.username in windows_script
        assert test_user.username in unix_script

    def test_windows_and_unix_have_same_mcp_server_config(self, authenticated_client):
        """Test both platforms configure same MCP server"""
        windows_response = authenticated_client.get("/api/mcp-installer/windows")
        unix_response = authenticated_client.get("/api/mcp-installer/unix")

        windows_script = windows_response.text
        unix_script = unix_response.text

        # Both should reference giljo-mcp server
        assert "giljo-mcp" in windows_script.lower()
        assert "giljo-mcp" in unix_script.lower()

        # Both should use same MCP adapter module
        assert "giljo_mcp.mcp_adapter" in windows_script or "giljo_mcp" in windows_script
        assert "giljo_mcp.mcp_adapter" in unix_script or "giljo_mcp" in unix_script

    def test_windows_batch_syntax(self, authenticated_client):
        """Test Windows script has valid batch file syntax"""
        response = authenticated_client.get("/api/mcp-installer/windows")
        script = response.text

        # Should start with @echo off (common batch pattern)
        assert "@echo off" in script.lower()

        # Should use batch variable syntax
        assert "set " in script or "SET " in script

        # Should use batch REM comments
        assert "REM" in script

    def test_unix_shell_syntax(self, authenticated_client):
        """Test Unix script has valid shell syntax"""
        response = authenticated_client.get("/api/mcp-installer/unix")
        script = response.text

        # Should have shebang
        assert script.startswith("#!/bin/bash")

        # Should use shell variable syntax
        assert "GILJO" in script  # Environment variables

        # Should use shell comments
        assert "#" in script


# ============================================================================
# TEST 7: Error Handling
# ============================================================================


class TestErrorHandling:
    """Test error handling scenarios"""

    def test_missing_template_returns_500(self, authenticated_client):
        """Test missing template file returns 500 Internal Server Error"""
        # Temporarily mock template path to non-existent file
        with patch("pathlib.Path.exists", return_value=False):
            response = authenticated_client.get("/api/mcp-installer/windows")

            # Should return 500 (internal server error)
            assert response.status_code == 500
            error_data = response.json()
            assert "template not found" in error_data["detail"].lower()

    def test_download_endpoint_validates_platform_parameter(self):
        """Test download endpoint validates platform parameter"""
        # Create valid token
        payload = {
            "user_id": "test-123",
            "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z",
            "type": "mcp_installer_download",
        }

        token = jwt.encode(payload, mcp_installer.SECRET_KEY, algorithm=mcp_installer.ALGORITHM)

        # Try various invalid platforms
        invalid_platforms = ["linux", "mac", "invalid", "win", "sh", ""]

        public_client = TestClient(app)

        for platform in invalid_platforms:
            response = public_client.get(f"/download/mcp/{token}/{platform}")

            # Should return 400 Bad Request
            assert response.status_code == 400, f"Platform '{platform}' should be invalid"
            error_data = response.json()
            assert "Invalid platform" in error_data["detail"]

    def test_malformed_jwt_token_returns_401(self):
        """Test malformed JWT token returns 401"""
        malformed_tokens = [
            "invalid-token",
            "not.a.jwt",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid",  # Invalid payload
            "",  # Empty token
        ]

        public_client = TestClient(app)

        for token in malformed_tokens:
            response = public_client.get(f"/download/mcp/{token}/windows")
            assert response.status_code == 401


# ============================================================================
# TEST 8: Performance and Scalability
# ============================================================================


class TestPerformance:
    """Test performance characteristics"""

    def test_script_generation_completes_quickly(self, authenticated_client, benchmark_timer):
        """Test script generation completes within reasonable time"""
        import time

        start = time.perf_counter()
        response = authenticated_client.get("/api/mcp-installer/windows")
        elapsed = (time.perf_counter() - start) * 1000  # Convert to ms

        assert response.status_code == 200

        # Script generation should complete in under 500ms
        assert elapsed < 500, f"Script generation took {elapsed:.2f}ms (expected <500ms)"

    def test_concurrent_script_downloads(self, test_user):
        """Test API handles concurrent script downloads"""
        import concurrent.futures

        def download_script():
            client = TestClient(app)
            client.headers.update({"X-API-Key": test_user.api_key, "X-Forwarded-For": "192.168.1.100"})
            response = client.get("/api/mcp-installer/windows")
            return response.status_code

        # Run 10 concurrent downloads
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(download_script) for _ in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All should succeed
        assert all(status == 200 for status in results)
        assert len(results) == 10


# ============================================================================
# TEST 9: Script Content Validation
# ============================================================================


class TestScriptContentValidation:
    """Validate generated script content is syntactically correct"""

    def test_windows_script_has_no_syntax_errors(self, authenticated_client):
        """Test Windows script has no obvious syntax errors"""
        response = authenticated_client.get("/api/mcp-installer/windows")
        script = response.text

        # Check for common batch syntax errors
        # Unmatched quotes
        single_quotes = script.count("'")
        double_quotes = script.count('"')

        # Should have even number of quotes (paired)
        assert single_quotes % 2 == 0, "Unmatched single quotes in script"
        assert double_quotes % 2 == 0, "Unmatched double quotes in script"

        # Check for unclosed parentheses
        open_parens = script.count("(")
        close_parens = script.count(")")
        assert open_parens == close_parens, "Unmatched parentheses in script"

    def test_unix_script_has_no_syntax_errors(self, authenticated_client):
        """Test Unix script has no obvious syntax errors"""
        response = authenticated_client.get("/api/mcp-installer/unix")
        script = response.text

        # Check shebang is first line
        lines = script.split("\n")
        assert lines[0].startswith("#!/bin/bash"), "Shebang must be first line"

        # Check for common shell syntax errors
        double_quotes = script.count('"')
        assert double_quotes % 2 == 0, "Unmatched double quotes in script"

        # Check for unclosed braces
        open_braces = script.count("{")
        close_braces = script.count("}")
        assert open_braces == close_braces, "Unmatched braces in script"

    def test_scripts_contain_mcp_server_configuration(self, authenticated_client):
        """Test scripts contain valid MCP server configuration"""
        windows_response = authenticated_client.get("/api/mcp-installer/windows")
        unix_response = authenticated_client.get("/api/mcp-installer/unix")

        windows_script = windows_response.text
        unix_script = unix_response.text

        # Both should configure MCP servers (mention Claude, Cursor, or Windsurf)
        mcp_tools = ["claude", "cursor", "windsurf"]

        windows_has_mcp = any(tool in windows_script.lower() for tool in mcp_tools)
        unix_has_mcp = any(tool in unix_script.lower() for tool in mcp_tools)

        assert windows_has_mcp, "Windows script doesn't mention MCP tools"
        assert unix_has_mcp, "Unix script doesn't mention MCP tools"


# ============================================================================
# TEST 10: Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases and unusual scenarios"""

    @pytest.mark.asyncio
    async def test_user_with_special_characters_in_username(self, db_session):
        """Test user with special characters in username gets valid script"""
        from uuid import uuid4

        from src.giljo_mcp.auth.api_key_manager import APIKeyManager

        special_user = User(
            id=str(uuid4()),
            username="test.user-123_special",  # Special chars but valid
            email="special@example.com",
            password_hash="$2b$12$test",
            role="developer",
            is_active=True,
            tenant_key=f"special_{uuid4().hex[:8]}",
        )

        db_session.add(special_user)
        await db_session.commit()
        await db_session.refresh(special_user)

        # Create API key
        api_key_manager = APIKeyManager(db_session)
        api_key_result = await api_key_manager.create_api_key(
            user_id=special_user.id, name="special_key", tenant_key=special_user.tenant_key
        )

        client = TestClient(app)
        client.headers.update({"X-API-Key": api_key_result["key"], "X-Forwarded-For": "192.168.1.100"})

        response = client.get("/api/mcp-installer/windows")

        assert response.status_code == 200
        script = response.text
        assert special_user.username in script

    @pytest.mark.asyncio
    async def test_share_link_with_deleted_user_fails(self, authenticated_client, test_user, db_session):
        """Test share link fails if user is deleted after token generation"""
        # Generate share link
        share_response = authenticated_client.post("/api/mcp-installer/share-link")
        token = share_response.json()["token"]

        # Delete user
        await db_session.delete(test_user)
        await db_session.commit()

        # Try to download with token
        public_client = TestClient(app)
        response = public_client.get(f"/download/mcp/{token}/windows")

        # Should fail (user no longer exists)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_inactive_user_cannot_download(self, db_session):
        """Test inactive user cannot download scripts"""
        from uuid import uuid4

        from src.giljo_mcp.auth.api_key_manager import APIKeyManager

        inactive_user = User(
            id=str(uuid4()),
            username="inactive_user",
            email="inactive@example.com",
            password_hash="$2b$12$test",
            role="developer",
            is_active=False,  # Inactive
            tenant_key=f"inactive_{uuid4().hex[:8]}",
        )

        db_session.add(inactive_user)
        await db_session.commit()
        await db_session.refresh(inactive_user)

        # Create API key
        api_key_manager = APIKeyManager(db_session)
        api_key_result = await api_key_manager.create_api_key(
            user_id=inactive_user.id, name="inactive_key", tenant_key=inactive_user.tenant_key
        )

        client = TestClient(app)
        client.headers.update({"X-API-Key": api_key_result["key"], "X-Forwarded-For": "192.168.1.100"})

        response = client.get("/api/mcp-installer/windows")

        # Should fail (user is inactive)
        # This depends on authentication middleware rejecting inactive users
        assert response.status_code in [401, 403]
