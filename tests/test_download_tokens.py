"""
Comprehensive test suite for one-time download token system.

This test suite follows TDD methodology - tests are written BEFORE implementation.
Tests verify secure, multi-tenant download token functionality for slash commands
and agent templates.

Architecture:
    - TokenManager: Token generation, validation, cleanup
    - FileStaging: Temporary file preparation and cleanup
    - Download Endpoints: Token-based secure downloads
    - Multi-tenant isolation: Zero cross-tenant leakage

Handover: One-Time Download Token System (TDD)
Author: Backend Integration Tester Agent
"""

import asyncio
import json
import time
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from io import BytesIO
from unittest.mock import patch

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select

from src.giljo_mcp.models import AgentTemplate, User


# ============================================================================
# TEST DATA & UTILITIES
# ============================================================================


class TokenTestData:
    """Test data generators for token system"""

    @staticmethod
    def generate_tenant_key() -> str:
        """Generate unique tenant key for isolation testing"""
        return f"tk_test_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def generate_token() -> str:
        """Generate UUID token for testing"""
        return str(uuid.uuid4())

    @staticmethod
    def generate_download_metadata(
        tenant_key: str,
        download_type: str = "slash_commands",
        filename: str = "download.zip",
    ) -> dict:
        """Generate download metadata structure"""
        return {
            "tenant_key": tenant_key,
            "download_type": download_type,
            "filename": filename,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
            "file_count": 3,
            "file_size_bytes": 1024,
        }


# ============================================================================
# UNIT TESTS: TokenManager
# ============================================================================


class TestTokenManager:
    """
    Unit tests for TokenManager component.

    The TokenManager is responsible for:
    - Generating unique one-time tokens (UUID v4)
    - Storing token metadata (tenant_key, expiration, download status)
    - Validating tokens (exists, not expired, not used)
    - Marking tokens as used (one-time use enforcement)
    - Cleaning up expired tokens (background task)
    """

    @pytest.mark.asyncio
    async def test_generate_token_creates_unique_uuid(self):
        """Test token generation produces unique UUIDs"""
        from src.giljo_mcp.download_tokens import TokenManager

        manager = TokenManager()

        # Generate multiple tokens
        tokens = set()
        for _ in range(100):
            token = await manager.generate_token(
                tenant_key="test-tenant", download_type="slash_commands", metadata={"test": True}
            )
            tokens.add(token)

        # All tokens should be unique
        assert len(tokens) == 100

        # Each token should be valid UUID
        for token in tokens:
            uuid.UUID(token)  # Raises if invalid

    @pytest.mark.asyncio
    async def test_generate_token_stores_metadata(self, db_session):
        """Test token generation persists metadata to database"""
        from src.giljo_mcp.download_tokens import TokenManager
        from src.giljo_mcp.models import DownloadToken

        manager = TokenManager(db_session)
        tenant_key = TokenTestData.generate_tenant_key()

        metadata = {"filename": "test.zip", "file_count": 5, "file_size": 2048}

        token = await manager.generate_token(tenant_key=tenant_key, download_type="agent_templates", metadata=metadata)

        # Verify token exists in database
        stmt = select(DownloadToken).where(DownloadToken.token == token)
        result = await db_session.execute(stmt)
        db_token = result.scalar_one()

        assert db_token.token == token
        assert db_token.tenant_key == tenant_key
        assert db_token.download_type == "agent_templates"
        assert db_token.download_count == 0
        assert db_token.metadata == metadata
        assert db_token.expires_at > datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_validate_token_success(self, db_session):
        """Test valid token passes validation"""
        from src.giljo_mcp.download_tokens import TokenManager

        manager = TokenManager(db_session)
        tenant_key = TokenTestData.generate_tenant_key()

        token = await manager.generate_token(tenant_key=tenant_key, download_type="slash_commands", metadata={})

        # Validate token
        is_valid = await manager.validate_token(token, tenant_key)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_token_not_found(self, db_session):
        """Test validation fails for non-existent token"""
        from src.giljo_mcp.download_tokens import TokenManager

        manager = TokenManager(db_session)
        fake_token = TokenTestData.generate_token()

        is_valid = await manager.validate_token(fake_token, "test-tenant")
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_token_expired(self, db_session):
        """Test validation fails for expired token"""
        from src.giljo_mcp.download_tokens import TokenManager
        from src.giljo_mcp.models import DownloadToken

        manager = TokenManager(db_session)
        tenant_key = TokenTestData.generate_tenant_key()

        # Create token
        token = await manager.generate_token(tenant_key=tenant_key, download_type="slash_commands", metadata={})

        # Manually expire token
        stmt = select(DownloadToken).where(DownloadToken.token == token)
        result = await db_session.execute(stmt)
        db_token = result.scalar_one()

        db_token.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        await db_session.commit()

        # Validate expired token
        is_valid = await manager.validate_token(token, tenant_key)
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_token_already_used(self, db_session):
        """Test validation fails for already downloaded token (one-time use)"""
        from src.giljo_mcp.download_tokens import TokenManager

        manager = TokenManager(db_session)
        tenant_key = TokenTestData.generate_tenant_key()

        token = await manager.generate_token(tenant_key=tenant_key, download_type="slash_commands", metadata={})

        # Mark as used
        await manager.mark_as_used(token)

        # Validate used token
        is_valid = await manager.validate_token(token, tenant_key)
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_token_cross_tenant_access_denied(self, db_session):
        """Test multi-tenant isolation: Token cannot be validated by different tenant"""
        from src.giljo_mcp.download_tokens import TokenManager

        manager = TokenManager(db_session)
        tenant_a = TokenTestData.generate_tenant_key()
        tenant_b = TokenTestData.generate_tenant_key()

        # Tenant A creates token
        token = await manager.generate_token(tenant_key=tenant_a, download_type="slash_commands", metadata={})

        # Tenant B tries to validate
        is_valid = await manager.validate_token(token, tenant_b)
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_mark_as_used_deprecated(self, db_session):
        """Test marking token as used (DEPRECATED - no-op for compatibility)"""
        from src.giljo_mcp.download_tokens import TokenManager

        manager = TokenManager(db_session)
        tenant_key = TokenTestData.generate_tenant_key()

        token = await manager.generate_token(tenant_key=tenant_key, download_type="slash_commands", metadata={})

        # Mark as used (deprecated method, returns True for compatibility)
        result = await manager.mark_as_used(token)
        assert result is True

    @pytest.mark.asyncio
    async def test_cleanup_expired_tokens(self, db_session):
        """Test expired token cleanup removes old tokens"""
        from src.giljo_mcp.download_tokens import TokenManager
        from src.giljo_mcp.models import DownloadToken

        manager = TokenManager(db_session)
        tenant_key = TokenTestData.generate_tenant_key()

        # Create fresh token
        fresh_token = await manager.generate_token(tenant_key=tenant_key, download_type="slash_commands", metadata={})

        # Create expired token
        expired_token = await manager.generate_token(tenant_key=tenant_key, download_type="slash_commands", metadata={})

        # Manually expire second token
        stmt = select(DownloadToken).where(DownloadToken.token == expired_token)
        result = await db_session.execute(stmt)
        db_token = result.scalar_one()
        db_token.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        await db_session.commit()

        # Run cleanup
        deleted_count = await manager.cleanup_expired_tokens()

        # Verify expired token deleted
        assert deleted_count == 1

        stmt = select(DownloadToken).where(DownloadToken.token == expired_token)
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is None

        # Verify fresh token still exists
        stmt = select(DownloadToken).where(DownloadToken.token == fresh_token)
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_concurrent_token_generation_thread_safe(self, db_session):
        """Test concurrent token generation maintains uniqueness (race condition test)"""
        from src.giljo_mcp.download_tokens import TokenManager

        manager = TokenManager(db_session)
        tenant_key = TokenTestData.generate_tenant_key()

        # Generate 50 tokens concurrently
        tasks = [
            manager.generate_token(tenant_key=tenant_key, download_type="slash_commands", metadata={})
            for _ in range(50)
        ]

        tokens = await asyncio.gather(*tasks)

        # All tokens should be unique
        assert len(set(tokens)) == 50

    @pytest.mark.asyncio
    async def test_concurrent_downloads_one_token_fails(self, db_session):
        """Test concurrent download attempts with same token - only first succeeds"""
        from src.giljo_mcp.download_tokens import TokenManager

        manager = TokenManager(db_session)
        tenant_key = TokenTestData.generate_tenant_key()

        token = await manager.generate_token(tenant_key=tenant_key, download_type="slash_commands", metadata={})

        # Simulate concurrent downloads
        async def attempt_download():
            is_valid = await manager.validate_token(token, tenant_key)
            if is_valid:
                await manager.mark_as_used(token)
            return is_valid

        # 10 concurrent download attempts
        tasks = [attempt_download() for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # Only one should succeed (one-time use)
        successful = sum(results)
        assert successful == 1


# ============================================================================
# UNIT TESTS: FileStaging
# ============================================================================


class TestFileStaging:
    """
    Unit tests for FileStaging component.

    The FileStaging system is responsible for:
    - Creating temporary directories per token (temp/{tenant_key}/{token}/)
    - Generating ZIP files (slash commands or agent templates)
    - Persisting metadata JSON files
    - Cleaning up files after download
    - Preventing directory traversal attacks
    """

    @pytest.mark.asyncio
    async def test_create_staging_directory_structure(self, tmp_path):
        """Test staging directory creation follows proper structure"""
        from src.giljo_mcp.file_staging import FileStaging

        staging = FileStaging(base_path=tmp_path)
        tenant_key = TokenTestData.generate_tenant_key()
        token = TokenTestData.generate_token()

        staging_dir = await staging.create_staging_directory(tenant_key, token)

        # Verify structure: temp/{tenant_key}/{token}/
        assert staging_dir.exists()
        assert staging_dir.parent.name == tenant_key
        assert staging_dir.name == token

    @pytest.mark.asyncio
    async def test_stage_slash_commands_creates_zip(self, tmp_path, db_session):
        """Test slash command ZIP file generation"""
        from src.giljo_mcp.file_staging import FileStaging

        staging = FileStaging(base_path=tmp_path)
        tenant_key = TokenTestData.generate_tenant_key()
        token = TokenTestData.generate_token()

        staging_dir = await staging.create_staging_directory(tenant_key, token)
        zip_path, message = await staging.stage_slash_commands(staging_dir)

        # Verify ZIP exists
        assert zip_path.exists()
        assert zip_path.suffix == ".zip"

        # Verify ZIP contents
        with zipfile.ZipFile(zip_path, "r") as zf:
            namelist = zf.namelist()
            # Refactored 0102: Only gil_handover.md included in slash commands
            assert "gil_handover.md" in namelist

    @pytest.mark.asyncio
    async def test_stage_agent_templates_creates_zip(self, tmp_path, db_session):
        """Test agent template ZIP file generation with user's templates"""
        from src.giljo_mcp.file_staging import FileStaging

        # Create test user and templates
        tenant_key = TokenTestData.generate_tenant_key()

        templates = [
            AgentTemplate(
                name="orchestrator",
                role="orchestrator",
                template_content="# Orchestrator",
                tool="claude",
                tenant_key=tenant_key,
                is_active=True,
            ),
            AgentTemplate(
                name="implementor",
                role="implementor",
                template_content="# Implementor",
                tool="claude",
                tenant_key=tenant_key,
                is_active=True,
            ),
        ]
        db_session.add_all(templates)
        await db_session.commit()

        staging = FileStaging(base_path=tmp_path, db_session=db_session)
        token = TokenTestData.generate_token()

        staging_dir = await staging.create_staging_directory(tenant_key, token)
        zip_path, message = await staging.stage_agent_templates(staging_dir, tenant_key, db_session=db_session)

        # Verify ZIP exists
        assert zip_path.exists()

        # Verify ZIP contents
        with zipfile.ZipFile(zip_path, "r") as zf:
            namelist = zf.namelist()
            assert "orchestrator.md" in namelist
            assert "implementor.md" in namelist

    @pytest.mark.asyncio
    async def test_save_metadata_creates_json(self, tmp_path):
        """Test metadata persistence to JSON file"""
        from src.giljo_mcp.file_staging import FileStaging

        staging = FileStaging(base_path=tmp_path)
        tenant_key = TokenTestData.generate_tenant_key()
        token = TokenTestData.generate_token()

        metadata = TokenTestData.generate_download_metadata(tenant_key)

        staging_dir = await staging.create_staging_directory(tenant_key, token)
        metadata_path = await staging.save_metadata(staging_dir, metadata)

        # Verify metadata file exists
        assert metadata_path.exists()
        assert metadata_path.name == "metadata.json"

        # Verify content
        saved_metadata = json.loads(metadata_path.read_text())
        assert saved_metadata["tenant_key"] == tenant_key
        assert saved_metadata["download_type"] == metadata["download_type"]

    @pytest.mark.asyncio
    async def test_cleanup_removes_staging_directory(self, tmp_path):
        """Test cleanup removes entire staging directory"""
        from src.giljo_mcp.file_staging import FileStaging

        staging = FileStaging(base_path=tmp_path)
        tenant_key = TokenTestData.generate_tenant_key()
        token = TokenTestData.generate_token()

        staging_dir = await staging.create_staging_directory(tenant_key, token)

        # Create some files
        (staging_dir / "test.txt").write_text("test")
        (staging_dir / "subdir").mkdir()
        (staging_dir / "subdir" / "file.txt").write_text("content")

        # Cleanup
        await staging.cleanup(tenant_key, token)

        # Verify directory removed
        assert not staging_dir.exists()

    @pytest.mark.asyncio
    async def test_directory_traversal_prevention(self, tmp_path):
        """Test protection against directory traversal attacks"""
        from src.giljo_mcp.file_staging import FileStaging

        staging = FileStaging(base_path=tmp_path)

        # Attempt directory traversal
        malicious_tenant = "../../../etc"
        malicious_token = "passwd"

        with pytest.raises((ValueError, HTTPException)):
            await staging.create_staging_directory(malicious_tenant, malicious_token)


# ============================================================================
# INTEGRATION TESTS: Download Endpoints
# ============================================================================


class TestDownloadEndpointsWithTokens:
    """
    Integration tests for token-based download endpoints.

    Tests the full flow:
    1. Tool/UI generates download token
    2. User receives download URL with token
    3. User downloads file using token (one-time)
    4. Subsequent downloads with same token fail
    5. Files cleaned up after download
    """

    @pytest.mark.asyncio
    async def test_generate_token_endpoint_success(self, api_client, auth_headers, db_session):
        """Test POST /api/download/generate-token creates valid token"""
        response = await api_client.post(
            "/api/download/generate-token", headers=auth_headers, json={"download_type": "slash_commands"}
        )

        assert response.status_code == 201
        data = response.json()

        assert "token" in data
        assert "download_url" in data
        assert "expires_at" in data

        # Verify token is valid UUID
        uuid.UUID(data["token"])

        # Verify URL structure
        assert f"/api/download/file/{data['token']}" in data["download_url"]

    @pytest.mark.asyncio
    async def test_download_with_valid_token_success(self, api_client, auth_headers, db_session):
        """Test GET /api/download/file/{token} downloads file successfully"""
        # Generate token
        response = await api_client.post(
            "/api/download/generate-token", headers=auth_headers, json={"download_type": "slash_commands"}
        )
        token = response.json()["token"]

        # Download file
        response = await api_client.get(f"/api/download/file/{token}")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert "attachment" in response.headers.get("content-disposition", "")

        # Verify ZIP is valid
        zip_bytes = response.content
        with zipfile.ZipFile(BytesIO(zip_bytes), "r") as zf:
            assert len(zf.namelist()) > 0

    @pytest.mark.asyncio
    async def test_download_with_expired_token_fails(self, api_client, auth_headers, db_session):
        """Test download fails with expired token (15 min timeout)"""
        from src.giljo_mcp.download_tokens import TokenManager
        from src.giljo_mcp.models import DownloadToken

        # Create token and manually expire it
        manager = TokenManager(db_session)
        tenant_key = "test-tenant"

        token = await manager.generate_token(tenant_key=tenant_key, download_type="slash_commands", metadata={})

        # Expire token
        stmt = select(DownloadToken).where(DownloadToken.token == token)
        result = await db_session.execute(stmt)
        db_token = result.scalar_one()
        db_token.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        await db_session.commit()

        # Attempt download
        response = await api_client.get(f"/api/download/file/{token}")

        assert response.status_code == 410  # Gone
        assert "expired" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_download_with_used_token_fails(self, api_client, auth_headers, db_session):
        """Test one-time use enforcement: Second download with same token fails"""
        # Generate token
        response = await api_client.post(
            "/api/download/generate-token", headers=auth_headers, json={"download_type": "slash_commands"}
        )
        token = response.json()["token"]

        # First download succeeds
        response1 = await api_client.get(f"/api/download/file/{token}")
        assert response1.status_code == 200

        # Second download fails
        response2 = await api_client.get(f"/api/download/file/{token}")
        assert response2.status_code == 410  # Gone
        assert "already used" in response2.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_download_with_invalid_token_fails(self, api_client):
        """Test download fails with non-existent token"""
        fake_token = TokenTestData.generate_token()

        response = await api_client.get(f"/api/download/file/{fake_token}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_download_cross_tenant_access_denied(self, api_client, auth_headers, db_session):
        """Test multi-tenant isolation: Token from tenant A cannot be used by tenant B"""
        from src.giljo_mcp.download_tokens import TokenManager

        # Tenant A creates token
        manager = TokenManager(db_session)
        tenant_a = "tenant-a"

        token = await manager.generate_token(tenant_key=tenant_a, download_type="slash_commands", metadata={})

        # Tenant B tries to download (using different auth)
        # (In practice, tenant key comes from JWT token)
        response = await api_client.get(
            f"/api/download/file/{token}", headers={"Authorization": "Bearer tenant-b-token"}
        )

        assert response.status_code == 403  # Forbidden
        assert "access denied" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_download_cleanup_after_success(self, api_client, auth_headers, db_session, tmp_path):
        """Test file cleanup occurs after successful download"""
        from src.giljo_mcp.file_staging import FileStaging

        # Generate token
        response = await api_client.post(
            "/api/download/generate-token", headers=auth_headers, json={"download_type": "slash_commands"}
        )
        token = response.json()["token"]

        # Check staging directory exists
        staging = FileStaging(base_path=tmp_path)
        tenant_key = "test-tenant"
        staging_dir = tmp_path / tenant_key / token

        # Download file (triggers cleanup)
        response = await api_client.get(f"/api/download/file/{token}")
        assert response.status_code == 200

        # Verify cleanup occurred (after download completes)
        await asyncio.sleep(0.1)  # Small delay for async cleanup
        assert not staging_dir.exists()


# ============================================================================
# INTEGRATION TESTS: MCP Tool Integration
# ============================================================================
# Note: Tests removed - setup_slash_commands() and get_agent_download_url()
# MCP tools have been deprecated and removed from the codebase.


# ============================================================================
# END-TO-END TESTS
# ============================================================================


class TestEndToEndDownloadFlow:
    """
    End-to-end tests covering complete download workflows.

    Scenarios:
    - UI button → token → download → cleanup
    - MCP slash command → token → download → cleanup
    - Concurrent downloads from different tenants
    """

    @pytest.mark.asyncio
    async def test_ui_button_download_flow(self, api_client, auth_headers):
        """Test complete flow: UI button → generate token → download → cleanup"""
        # Step 1: UI requests download token
        response = await api_client.post(
            "/api/download/generate-token", headers=auth_headers, json={"download_type": "slash_commands"}
        )
        assert response.status_code == 201

        token = response.json()["token"]
        download_url = response.json()["download_url"]

        # Step 2: User clicks download link
        response = await api_client.get(download_url)
        assert response.status_code == 200

        # Step 3: Verify ZIP content
        with zipfile.ZipFile(BytesIO(response.content), "r") as zf:
            assert len(zf.namelist()) > 0

        # Step 4: Verify token now invalid (one-time use)
        response = await api_client.get(download_url)
        assert response.status_code == 410

    @pytest.mark.asyncio
    async def test_concurrent_downloads_different_tenants(self, api_client, db_session):
        """Test concurrent downloads from multiple tenants (isolation verification)"""
        from src.giljo_mcp.download_tokens import TokenManager

        manager = TokenManager(db_session)

        # Create tokens for 5 different tenants
        tenants = [f"tenant-{i}" for i in range(5)]
        tokens = []

        for tenant in tenants:
            token = await manager.generate_token(tenant_key=tenant, download_type="slash_commands", metadata={})
            tokens.append((tenant, token))

        # Simulate concurrent downloads
        async def download_for_tenant(tenant_key, token):
            # Each tenant can only access their own token
            is_valid = await manager.validate_token(token, tenant_key)
            return is_valid

        tasks = [download_for_tenant(tenant, token) for tenant, token in tokens]
        results = await asyncio.gather(*tasks)

        # All downloads should succeed (proper isolation)
        assert all(results)


# ============================================================================
# EDGE CASES & ERROR HANDLING
# ============================================================================


class TestEdgeCasesAndErrors:
    """
    Tests for edge cases and error conditions.

    Coverage:
    - Malformed tokens
    - Missing metadata
    - Database errors
    - Filesystem errors
    - Network timeouts
    - Rate limiting
    """

    @pytest.mark.asyncio
    async def test_malformed_token_uuid(self, api_client):
        """Test download with malformed token format"""
        malformed_token = "not-a-uuid"

        response = await api_client.get(f"/api/download/file/{malformed_token}")
        assert response.status_code == 400
        assert "invalid token" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_token_generation_database_error(self, db_session):
        """Test token generation handles database errors gracefully"""
        from src.giljo_mcp.download_tokens import TokenManager

        # Mock database error
        with patch.object(db_session, "commit", side_effect=Exception("DB error")):
            manager = TokenManager(db_session)

            with pytest.raises(HTTPException) as exc_info:
                await manager.generate_token(tenant_key="test", download_type="slash_commands", metadata={})

            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_file_staging_disk_full_error(self, tmp_path):
        """Test file staging handles disk full errors"""
        from src.giljo_mcp.file_staging import FileStaging

        staging = FileStaging(base_path=tmp_path)
        tenant_key = TokenTestData.generate_tenant_key()
        token = TokenTestData.generate_token()
        staging_dir = await staging.create_staging_directory(tenant_key, token)

        # Mock disk full error on writing into ZIP
        with patch("zipfile.ZipFile.writestr", side_effect=OSError("No space left")):
            zip_path, message = await staging.stage_slash_commands(staging_dir)
            assert zip_path is None
            assert "disk" in message.lower() or "error" in message.lower()

    @pytest.mark.asyncio
    async def test_cleanup_handles_missing_directory(self, tmp_path):
        """Test cleanup gracefully handles already-deleted directories"""
        from src.giljo_mcp.file_staging import FileStaging

        staging = FileStaging(base_path=tmp_path)

        # Attempt cleanup on non-existent directory (should not raise)
        await staging.cleanup("tenant", "nonexistent-token")
        # No assertion - just verify it doesn't crash

    @pytest.mark.asyncio
    async def test_rate_limiting_token_generation(self, api_client, auth_headers):
        """Test rate limiting prevents token generation abuse"""
        # Generate many tokens rapidly
        responses = []
        for _ in range(100):
            response = await api_client.post(
                "/api/download/generate-token", headers=auth_headers, json={"download_type": "slash_commands"}
            )
            responses.append(response.status_code)

        # Should hit rate limit at some point
        assert 429 in responses  # Too Many Requests


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================


class TestDownloadPerformance:
    """
    Performance tests for download token system.

    Benchmarks:
    - Token generation latency (<50ms)
    - Download latency (<200ms for small files)
    - Concurrent token validation (1000 req/s)
    - Cleanup performance (1000 tokens in <1s)
    """

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_token_generation_latency(self, db_session):
        """Test token generation completes in <50ms"""
        from src.giljo_mcp.download_tokens import TokenManager

        manager = TokenManager(db_session)

        # Warmup
        for _ in range(10):
            await manager.generate_token("test", "slash_commands", {})

        # Measure
        start = time.perf_counter()
        for _ in range(100):
            await manager.generate_token("test", "slash_commands", {})
        end = time.perf_counter()

        avg_latency_ms = (end - start) / 100 * 1000
        assert avg_latency_ms < 50, f"Token generation too slow: {avg_latency_ms:.2f}ms"

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_concurrent_token_validation_throughput(self, db_session):
        """Test system handles 1000 concurrent token validations"""
        from src.giljo_mcp.download_tokens import TokenManager

        manager = TokenManager(db_session)

        # Create 1000 tokens
        tokens = []
        for i in range(1000):
            token = await manager.generate_token(f"tenant-{i}", "slash_commands", {})
            tokens.append((f"tenant-{i}", token))

        # Validate concurrently
        start = time.perf_counter()
        tasks = [manager.validate_token(token, tenant) for tenant, token in tokens]
        results = await asyncio.gather(*tasks)
        end = time.perf_counter()

        # All should succeed
        assert all(results)

        # Performance check
        throughput = len(tokens) / (end - start)
        assert throughput > 1000, f"Validation too slow: {throughput:.0f} req/s"

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_cleanup_performance(self, db_session):
        """Test expired token cleanup handles 1000 tokens in <1s"""
        from src.giljo_mcp.download_tokens import TokenManager
        from src.giljo_mcp.models import DownloadToken

        manager = TokenManager(db_session)

        # Create 1000 expired tokens
        for i in range(1000):
            token = await manager.generate_token(f"tenant-{i}", "slash_commands", {})

            # Expire token
            stmt = select(DownloadToken).where(DownloadToken.token == token)
            result = await db_session.execute(stmt)
            db_token = result.scalar_one()
            db_token.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)

        await db_session.commit()

        # Cleanup
        start = time.perf_counter()
        deleted_count = await manager.cleanup_expired_tokens()
        end = time.perf_counter()

        assert deleted_count == 1000
        assert (end - start) < 1.0, f"Cleanup too slow: {(end - start):.2f}s"


# ============================================================================
# FIXTURES
# ============================================================================


@pytest_asyncio.fixture
async def test_user(db_session):
    """Create test user with tenant key"""
    user = User(
        id=str(uuid.uuid4()),
        username="testuser",
        email="test@example.com",
        tenant_key=TokenTestData.generate_tenant_key(),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def auth_headers(test_user):
    """Generate authentication headers for test user"""
    # In practice, this would create a valid JWT token
    return {"Authorization": f"Bearer test-token-{test_user.id}"}


@pytest_asyncio.fixture
async def api_client():
    """Create async HTTP client for API testing"""
    # This would be a TestClient or httpx.AsyncClient
    # connected to the FastAPI app
