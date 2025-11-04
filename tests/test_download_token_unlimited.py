"""
Tests for Download Token System - Unlimited Downloads Within 15-Minute Window

Tests verify:
1. Unlimited downloads within 15-minute expiry window
2. Token expiry after 15 minutes
3. Multi-tenant isolation
4. Security (filename validation, directory traversal prevention)

Handover 0096 Refactoring: Remove single-use constraint, natural language instructions
"""

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.downloads.token_manager import TokenManager
from src.giljo_mcp.file_staging import FileStaging
from src.giljo_mcp.models import DownloadToken


# Fixtures


@pytest.fixture
async def token_manager(db_session: AsyncSession) -> TokenManager:
    """Create TokenManager instance with test database session."""
    return TokenManager(db_session=db_session)


@pytest.fixture
async def file_staging(db_session: AsyncSession) -> FileStaging:
    """Create FileStaging instance with test database session."""
    base_path = Path.cwd() / "temp" / "test_downloads"
    base_path.mkdir(parents=True, exist_ok=True)
    return FileStaging(base_path=base_path, db_session=db_session)


@pytest.fixture
def tenant_key() -> str:
    """Generate unique tenant key for tests."""
    return f"test_tenant_{uuid4().hex[:8]}"


# Token Generation Tests


@pytest.mark.asyncio
async def test_generate_token_slash_commands(
    token_manager: TokenManager, tenant_key: str
):
    """Test token generation for slash commands."""
    # Create a test file
    test_file = Path.cwd() / "temp" / "test.zip"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("test content")

    try:
        token = await token_manager.generate_token(
            tenant_key=tenant_key,
            download_type="slash_commands",
            file_path=str(test_file),
            metadata={"filename": "slash_commands.zip", "file_count": 1},
        )

        # Verify token is UUID format
        assert len(token) == 36  # UUID v4 string length
        assert token.count("-") == 4

        # Verify token in database
        stmt = select(DownloadToken).where(DownloadToken.token == token)
        result = await token_manager.db_session.execute(stmt)
        token_record = result.scalar_one_or_none()

        assert token_record is not None
        assert token_record.tenant_key == tenant_key
        assert token_record.download_type == "slash_commands"
        assert token_record.meta_data["file_path"] == str(test_file)
        assert token_record.is_used is False
        assert token_record.downloaded_at is None

    finally:
        # Cleanup
        if test_file.exists():
            test_file.unlink()


@pytest.mark.asyncio
async def test_generate_token_invalid_download_type(
    token_manager: TokenManager, tenant_key: str
):
    """Test token generation with invalid download type."""
    with pytest.raises(ValueError, match="Invalid download_type"):
        await token_manager.generate_token(
            tenant_key=tenant_key,
            download_type="invalid_type",
            file_path="/tmp/test.zip",
            metadata={},
        )


# Token Validation Tests - Unlimited Downloads


@pytest.mark.asyncio
async def test_validate_token_multiple_times_within_window(
    token_manager: TokenManager, tenant_key: str
):
    """Test that token can be validated multiple times within 15-minute window."""
    # Create test file
    test_file = Path.cwd() / "temp" / "test.zip"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("test content")

    try:
        # Generate token
        token = await token_manager.generate_token(
            tenant_key=tenant_key,
            download_type="slash_commands",
            file_path=str(test_file),
            metadata={"filename": "slash_commands.zip"},
        )

        # First validation
        result1 = await token_manager.validate_token(token, "slash_commands.zip")
        assert result1["valid"] is True
        assert "token_data" in result1

        # Second validation (should still be valid - NO single-use enforcement)
        result2 = await token_manager.validate_token(token, "slash_commands.zip")
        assert result2["valid"] is True
        assert "token_data" in result2

        # Third validation (should still be valid)
        result3 = await token_manager.validate_token(token, "slash_commands.zip")
        assert result3["valid"] is True
        assert "token_data" in result3

    finally:
        if test_file.exists():
            test_file.unlink()


@pytest.mark.asyncio
async def test_validate_token_expired(token_manager: TokenManager, tenant_key: str):
    """Test that expired tokens are rejected."""
    # Create test file
    test_file = Path.cwd() / "temp" / "test.zip"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("test content")

    try:
        # Generate token
        token = await token_manager.generate_token(
            tenant_key=tenant_key,
            download_type="slash_commands",
            file_path=str(test_file),
            metadata={"filename": "slash_commands.zip"},
        )

        # Manually expire the token
        stmt = select(DownloadToken).where(DownloadToken.token == token)
        result = await token_manager.db_session.execute(stmt)
        token_record = result.scalar_one_or_none()

        token_record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        await token_manager.db_session.commit()

        # Validate expired token
        validation = await token_manager.validate_token(token, "slash_commands.zip")
        assert validation["valid"] is False
        assert validation["reason"] == "expired"

    finally:
        if test_file.exists():
            test_file.unlink()


@pytest.mark.asyncio
async def test_validate_token_not_found(token_manager: TokenManager):
    """Test validation of non-existent token."""
    fake_token = str(uuid4())
    validation = await token_manager.validate_token(fake_token, "test.zip")

    assert validation["valid"] is False
    assert validation["reason"] == "not_found"


@pytest.mark.asyncio
async def test_validate_token_filename_mismatch(
    token_manager: TokenManager, tenant_key: str
):
    """Test validation with mismatched filename."""
    # Create test file
    test_file = Path.cwd() / "temp" / "test.zip"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("test content")

    try:
        # Generate token
        token = await token_manager.generate_token(
            tenant_key=tenant_key,
            download_type="slash_commands",
            file_path=str(test_file),
            metadata={"filename": "slash_commands.zip"},
        )

        # Validate with wrong filename
        validation = await token_manager.validate_token(token, "wrong_file.zip")
        assert validation["valid"] is False
        assert validation["reason"] == "filename_mismatch"

    finally:
        if test_file.exists():
            test_file.unlink()


# Multi-Tenant Isolation Tests


@pytest.mark.asyncio
async def test_token_tenant_isolation(
    token_manager: TokenManager, db_session: AsyncSession
):
    """Test that tokens are isolated per tenant."""
    tenant_a = f"tenant_a_{uuid4().hex[:8]}"
    tenant_b = f"tenant_b_{uuid4().hex[:8]}"

    # Create test file
    test_file = Path.cwd() / "temp" / "test.zip"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("test content")

    try:
        # Generate token for tenant A
        token_a = await token_manager.generate_token(
            tenant_key=tenant_a,
            content_type="slash_commands",
            file_path=str(test_file),
            metadata={"filename": "test.zip"},
        )

        # Get token data with tenant A (should succeed)
        data_a = await token_manager.get_token_data(token_a, tenant_a)
        assert data_a is not None
        assert data_a["tenant_key"] == tenant_a

        # Get token data with tenant B (should fail - cross-tenant access)
        data_b = await token_manager.get_token_data(token_a, tenant_b)
        assert data_b is None

    finally:
        if test_file.exists():
            test_file.unlink()


# Token Expiry Tests


@pytest.mark.asyncio
async def test_token_expiry_15_minutes(token_manager: TokenManager, tenant_key: str):
    """Test that tokens expire after 15 minutes."""
    # Create test file
    test_file = Path.cwd() / "temp" / "test.zip"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("test content")

    try:
        # Generate token
        token = await token_manager.generate_token(
            tenant_key=tenant_key,
            content_type="slash_commands",
            file_path=str(test_file),
            metadata={"filename": "test.zip"},
        )

        # Get token record
        stmt = select(DownloadToken).where(DownloadToken.token == token)
        result = await token_manager.db_session.execute(stmt)
        token_record = result.scalar_one_or_none()

        # Verify expiry is ~15 minutes from now
        now = datetime.now(timezone.utc)
        expiry = token_record.expires_at
        time_until_expiry = (expiry - now).total_seconds()

        # Allow 10 second variance for test execution time
        assert 890 <= time_until_expiry <= 910  # 15 minutes = 900 seconds

    finally:
        if test_file.exists():
            test_file.unlink()


# Cleanup Tests


@pytest.mark.asyncio
async def test_cleanup_expired_tokens(
    token_manager: TokenManager, tenant_key: str, db_session: AsyncSession
):
    """Test cleanup of expired tokens."""
    # Create test files
    test_files = []
    for i in range(3):
        test_file = Path.cwd() / "temp" / f"test_{i}.zip"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text(f"test content {i}")
        test_files.append(test_file)

    try:
        # Generate tokens
        tokens = []
        for i, test_file in enumerate(test_files):
            token = await token_manager.generate_token(
                tenant_key=tenant_key,
                download_type="slash_commands",
                file_path=str(test_file),
                metadata={"filename": f"test_{i}.zip"},
            )
            tokens.append(token)

        # Expire first two tokens
        for token in tokens[:2]:
            stmt = select(DownloadToken).where(DownloadToken.token == token)
            result = await db_session.execute(stmt)
            token_record = result.scalar_one_or_none()
            token_record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        await db_session.commit()

        # Run cleanup
        deleted_count = await token_manager.cleanup_expired_tokens()

        # Verify 2 tokens deleted
        assert deleted_count == 2

        # Verify expired tokens removed from database
        for token in tokens[:2]:
            stmt = select(DownloadToken).where(DownloadToken.token == token)
            result = await db_session.execute(stmt)
            assert result.scalar_one_or_none() is None

        # Verify non-expired token still exists
        stmt = select(DownloadToken).where(DownloadToken.token == tokens[2])
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is not None

    finally:
        for test_file in test_files:
            if test_file.exists():
                test_file.unlink()


# File Staging Tests


@pytest.mark.asyncio
async def test_stage_slash_commands_only_handover(
    file_staging: FileStaging, tenant_key: str
):
    """Test that only gil_handover.md is staged (not import commands)."""
    token = str(uuid4())

    try:
        # Stage slash commands
        zip_path = await file_staging.stage_slash_commands(tenant_key, token)

        # Verify ZIP exists
        assert zip_path.exists()

        # Verify ZIP contents
        import zipfile

        with zipfile.ZipFile(zip_path, "r") as zf:
            filenames = zf.namelist()

            # Only gil_handover.md should be present
            assert "gil_handover.md" in filenames
            assert "gil_import_productagents.md" not in filenames
            assert "gil_import_personalagents.md" not in filenames

            # Verify content is not empty
            handover_content = zf.read("gil_handover.md").decode("utf-8")
            assert len(handover_content) > 0

    finally:
        # Cleanup
        await file_staging.cleanup(tenant_key, token)


@pytest.mark.asyncio
async def test_staging_directory_traversal_protection(file_staging: FileStaging):
    """Test protection against directory traversal attacks."""
    # Attempt directory traversal in tenant_key
    with pytest.raises(ValueError, match="path traversal detected"):
        await file_staging.create_staging_directory("../../../etc", "token123")

    # Attempt directory traversal in token
    with pytest.raises(ValueError, match="path traversal detected"):
        await file_staging.create_staging_directory("tenant", "../../etc/passwd")


# Security Tests


@pytest.mark.asyncio
async def test_token_security_no_cross_tenant_leak(
    token_manager: TokenManager, db_session: AsyncSession
):
    """Test that tokens cannot be accessed across tenants."""
    tenant_a = f"tenant_a_{uuid4().hex[:8]}"
    tenant_b = f"tenant_b_{uuid4().hex[:8]}"

    # Create test file
    test_file = Path.cwd() / "temp" / "test.zip"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("sensitive data")

    try:
        # Tenant A generates token
        token = await token_manager.generate_token(
            tenant_key=tenant_a,
            content_type="slash_commands",
            file_path=str(test_file),
            metadata={"filename": "test.zip"},
        )

        # Tenant B tries to access token data
        data = await token_manager.get_token_data(token, tenant_b)
        assert data is None  # Cross-tenant access denied

        # Validation should still work (no tenant_key parameter)
        validation = await token_manager.validate_token(token, "test.zip")
        assert validation["valid"] is True

    finally:
        if test_file.exists():
            test_file.unlink()


# Integration Tests


@pytest.mark.asyncio
async def test_full_download_flow_multiple_times(
    token_manager: TokenManager, file_staging: FileStaging, tenant_key: str
):
    """Test complete download flow: stage → token → download (multiple times)."""
    token = str(uuid4())

    try:
        # Stage files
        zip_path = await file_staging.stage_slash_commands(tenant_key, token)
        assert zip_path.exists()

        # Generate token
        download_token = await token_manager.generate_token(
            tenant_key=tenant_key,
            content_type="slash_commands",
            file_path=str(zip_path),
            metadata={"filename": "slash_commands.zip"},
        )

        # Validate token multiple times (unlimited downloads)
        for i in range(5):
            validation = await token_manager.validate_token(
                download_token, "slash_commands.zip"
            )
            assert validation["valid"] is True, f"Download {i+1} failed"

    finally:
        await file_staging.cleanup(tenant_key, token)
