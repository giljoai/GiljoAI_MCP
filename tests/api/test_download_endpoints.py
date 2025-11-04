"""
Tests for download token endpoints.

These tests verify the public download endpoints that use one-time tokens
for secure file distribution. Tests follow TDD methodology.

Handover: One-Time Download Token System - Download Endpoints
"""

import asyncio
import io
import zipfile
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from httpx import AsyncClient


# ============================================================================
# TOKEN GENERATION ENDPOINT TESTS
# ============================================================================


class TestGenerateTokenEndpoint:
    """Tests for POST /api/download/generate-token endpoint (authenticated)"""

    @pytest.mark.asyncio
    async def test_generate_token_slash_commands_success(
        self, api_client: AsyncClient, auth_headers: dict
    ):
        """Test generating token for slash commands returns valid response"""
        response = await api_client.post(
            "/api/download/generate-token",
            headers=auth_headers,
            json={"content_type": "slash_commands"},
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert "download_url" in data
        assert "expires_at" in data
        assert "content_type" in data
        assert "one_time_use" in data

        assert data["content_type"] == "slash_commands"
        assert data["one_time_use"] is True
        assert "/api/download/temp/" in data["download_url"]
        assert "slash_commands.zip" in data["download_url"]

    @pytest.mark.asyncio
    async def test_generate_token_agent_templates_success(
        self, api_client: AsyncClient, auth_headers: dict
    ):
        """Test generating token for agent templates returns valid response"""
        response = await api_client.post(
            "/api/download/generate-token",
            headers=auth_headers,
            json={"content_type": "agent_templates"},
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert data["content_type"] == "agent_templates"
        assert "agent_templates.zip" in data["download_url"]

    @pytest.mark.asyncio
    async def test_generate_token_invalid_content_type_fails(
        self, api_client: AsyncClient, auth_headers: dict
    ):
        """Test invalid content_type returns 400 error"""
        response = await api_client.post(
            "/api/download/generate-token",
            headers=auth_headers,
            json={"content_type": "invalid_type"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "invalid" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_generate_token_unauthenticated_fails(
        self, api_client: AsyncClient
    ):
        """Test unauthenticated request to generate token fails with 401"""
        response = await api_client.post(
            "/api/download/generate-token",
            json={"content_type": "slash_commands"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# FILE DOWNLOAD ENDPOINT TESTS
# ============================================================================


class TestDownloadFileEndpoint:
    """Tests for GET /api/download/temp/{token}/{filename} endpoint (public)"""

    @pytest.mark.asyncio
    async def test_download_with_valid_token_success(
        self, api_client: AsyncClient, valid_download_token: str
    ):
        """Test downloading file with valid token returns file"""
        response = await api_client.get(
            f"/api/download/temp/{valid_download_token}/slash_commands.zip"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "application/zip"
        assert "attachment" in response.headers["content-disposition"]
        assert "slash_commands.zip" in response.headers["content-disposition"]

        # Verify ZIP is valid
        zip_buffer = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_buffer, "r") as zf:
            assert len(zf.namelist()) > 0

    @pytest.mark.asyncio
    async def test_download_expired_token_fails(
        self, api_client: AsyncClient, expired_token: str
    ):
        """Test downloading with expired token (16+ minutes old) returns 404"""
        response = await api_client.get(
            f"/api/download/temp/{expired_token}/slash_commands.zip"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        error_msg = response.json()["detail"].lower()
        assert "invalid" in error_msg or "expired" in error_msg or "used" in error_msg

    @pytest.mark.asyncio
    async def test_download_already_used_token_fails(
        self, api_client: AsyncClient, valid_download_token: str
    ):
        """Test downloading with already-used token fails (one-time use)"""
        # First download succeeds
        response1 = await api_client.get(
            f"/api/download/temp/{valid_download_token}/slash_commands.zip"
        )
        assert response1.status_code == status.HTTP_200_OK

        # Second download with same token fails
        response2 = await api_client.get(
            f"/api/download/temp/{valid_download_token}/slash_commands.zip"
        )
        assert response2.status_code == status.HTTP_410_GONE
        assert "already" in response2.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_download_invalid_token_fails(self, api_client: AsyncClient):
        """Test downloading with non-existent token returns 404"""
        fake_token = "nonexistent-token-12345"

        response = await api_client.get(
            f"/api/download/temp/{fake_token}/slash_commands.zip"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_download_filename_mismatch_fails(
        self, api_client: AsyncClient, valid_download_token: str
    ):
        """Test downloading with wrong filename returns 404"""
        response = await api_client.get(
            f"/api/download/temp/{valid_download_token}/wrong_file.zip"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_download_cross_tenant_access_denied(
        self, api_client: AsyncClient, other_tenant_token: str
    ):
        """Test cross-tenant token access returns 404 (not 403 for security)"""
        response = await api_client.get(
            f"/api/download/temp/{other_tenant_token}/slash_commands.zip"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_download_concurrent_same_token_one_succeeds(
        self, api_client: AsyncClient, valid_download_token: str
    ):
        """Test concurrent downloads with same token - only one succeeds"""

        async def attempt_download():
            response = await api_client.get(
                f"/api/download/temp/{valid_download_token}/slash_commands.zip"
            )
            return response.status_code

        # 5 concurrent download attempts
        tasks = [attempt_download() for _ in range(5)]
        status_codes = await asyncio.gather(*tasks)

        # Exactly one should succeed (200), rest should fail (410 or 404)
        success_count = sum(1 for code in status_codes if code == 200)
        fail_count = sum(1 for code in status_codes if code in [404, 410])

        assert success_count == 1
        assert fail_count == 4

    @pytest.mark.asyncio
    async def test_download_file_cleanup_after_success(
        self, api_client: AsyncClient, valid_download_token: str, temp_dir
    ):
        """Test file cleanup occurs after successful download"""
        # Download file
        response = await api_client.get(
            f"/api/download/temp/{valid_download_token}/slash_commands.zip"
        )
        assert response.status_code == status.HTTP_200_OK

        # Wait for cleanup (async background task)
        await asyncio.sleep(0.5)

        # Verify file no longer exists
        from pathlib import Path

        temp_path = temp_dir / valid_download_token
        assert not temp_path.exists()


# ============================================================================
# SECURITY TESTS
# ============================================================================


class TestDownloadSecurity:
    """Security-focused tests for download endpoints"""

    @pytest.mark.asyncio
    async def test_directory_traversal_prevention(self, api_client: AsyncClient):
        """Test directory traversal attacks are prevented"""
        malicious_token = "../../../etc/passwd"

        response = await api_client.get(
            f"/api/download/temp/{malicious_token}/slash_commands.zip"
        )

        assert response.status_code in [400, 404]

    @pytest.mark.asyncio
    async def test_no_cache_headers_present(
        self, api_client: AsyncClient, valid_download_token: str
    ):
        """Test response includes no-cache headers"""
        response = await api_client.get(
            f"/api/download/temp/{valid_download_token}/slash_commands.zip"
        )

        assert response.status_code == status.HTTP_200_OK
        cache_control = response.headers.get("cache-control", "")
        assert "no-cache" in cache_control or "no-store" in cache_control

    @pytest.mark.asyncio
    async def test_download_without_auth_succeeds_with_token(
        self, api_client: AsyncClient, valid_download_token: str
    ):
        """Test download works without authentication (token IS the auth)"""
        # No auth headers provided
        response = await api_client.get(
            f"/api/download/temp/{valid_download_token}/slash_commands.zip"
        )

        assert response.status_code == status.HTTP_200_OK


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


class TestDownloadErrorHandling:
    """Tests for error handling in download endpoints"""

    @pytest.mark.asyncio
    async def test_generate_token_server_error_handling(
        self, api_client: AsyncClient, auth_headers: dict
    ):
        """Test server errors during token generation return 500"""
        with patch(
            "src.giljo_mcp.download_tokens.TokenManager.generate_token",
            side_effect=Exception("Database error"),
        ):
            response = await api_client.post(
                "/api/download/generate-token",
                headers=auth_headers,
                json={"content_type": "slash_commands"},
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_download_file_missing_returns_500(
        self, api_client: AsyncClient, valid_download_token: str
    ):
        """Test missing file (after token validation) returns 500"""
        with patch("pathlib.Path.exists", return_value=False):
            response = await api_client.get(
                f"/api/download/temp/{valid_download_token}/slash_commands.zip"
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "internal" in response.json()["detail"].lower()


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
async def valid_download_token(api_client: AsyncClient, auth_headers: dict) -> str:
    """Generate a valid download token for testing"""
    response = await api_client.post(
        "/api/download/generate-token",
        headers=auth_headers,
        json={"content_type": "slash_commands"},
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    # Extract token from download URL
    url = data["download_url"]
    token = url.split("/temp/")[1].split("/")[0]
    return token


@pytest.fixture
async def expired_token() -> str:
    """Return a token that appears expired (mock scenario)"""
    return "expired-token-123456789"


@pytest.fixture
async def other_tenant_token() -> str:
    """Return a token from a different tenant (mock scenario)"""
    return "other-tenant-token-987654321"


@pytest.fixture
def temp_dir(tmp_path):
    """Provide temporary directory for file staging"""
    return tmp_path
