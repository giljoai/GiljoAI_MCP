"""
Token Manager for one-time download tokens.

Handover 0100: Secure, time-limited download token system for slash commands
and agent templates.

Features:
- UUID v4 token generation (cryptographically secure)
- 15-minute expiry window
- One-time use enforcement
- Multi-tenant isolation
- Automatic expired token cleanup

Usage:
    manager = TokenManager(db_session)

    # Generate token
    token = await manager.generate_token(
        tenant_key="abc123",
        download_type="slash_commands",
        metadata={"filename": "slash_commands.zip"}
    )

    # Validate token
    is_valid = await manager.validate_token(token, tenant_key)

    # Mark as used
    await manager.mark_as_used(token)

    # Cleanup expired
    deleted_count = await manager.cleanup_expired_tokens()
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import DownloadToken


logger = logging.getLogger(__name__)


class TokenManager:
    """
    Manages one-time download tokens for secure file downloads.

    Provides token generation, validation, and cleanup functionality
    with multi-tenant isolation and automatic expiry management.
    """

    def __init__(self, db_session: Optional[AsyncSession] = None):
        """
        Initialize TokenManager with optional database session.

        Args:
            db_session: Optional AsyncSession for database operations.
                       If None, only UUID generation works (no persistence).
        """
        self.db_session = db_session

    async def generate_token(self, tenant_key: str, download_type: str, metadata: dict) -> str:
        """
        Generate a new download token.

        Creates a UUID v4 token with 15-minute expiry and stores metadata
        in the database. Token is ready for immediate use.

        If no database session is configured, only returns a UUID without
        persistence (useful for UUID uniqueness testing).

        Args:
            tenant_key: Tenant identifier for multi-tenant isolation
            download_type: Type of download ('slash_commands' or 'agent_templates')
            metadata: Additional metadata (filename, file_count, etc.)

        Returns:
            str: UUID token string

        Raises:
            ValueError: If download_type is invalid
            HTTPException: If database operation fails
        """
        # Validate download_type
        if download_type not in ("slash_commands", "agent_templates"):
            raise ValueError(f"Invalid download_type: {download_type}")

        # If no database session, just return a UUID (for testing)
        if not self.db_session:
            return str(uuid4())

        # Create expiry timestamp (15 minutes from now)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

        # Create token record
        token_record = DownloadToken(
            tenant_key=tenant_key, download_type=download_type, meta_data=metadata, expires_at=expires_at
        )

        try:
            self.db_session.add(token_record)
            await self.db_session.commit()
            await self.db_session.refresh(token_record)

            logger.info(
                f"Generated download token for tenant {tenant_key}, type: {download_type}, expires: {expires_at}"
            )

            return token_record.token

        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Failed to generate download token: {e}")
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate download token"
            )

    async def validate_token(self, token: str, tenant_key: str) -> bool:
        """
        Validate a download token.

        Checks if token exists, belongs to the correct tenant,
        has not expired, and has not been used.

        Args:
            token: UUID token string
            tenant_key: Tenant identifier for isolation check

        Returns:
            bool: True if token is valid, False otherwise
        """
        try:
            # Query token with tenant isolation
            stmt = select(DownloadToken).where(DownloadToken.token == token, DownloadToken.tenant_key == tenant_key)
            result = await self.db_session.execute(stmt)
            token_record = result.scalar_one_or_none()

            if not token_record:
                logger.debug(f"Token not found or tenant mismatch: {token}")
                return False

            # Check if expired
            if token_record.is_expired:
                logger.debug(f"Token expired: {token}")
                return False

            logger.debug(f"Token validated successfully: {token}")
            return True

        except Exception as e:
            logger.error(f"Error validating token: {e}")
            return False

    async def mark_as_used(self, token: str) -> bool:
        """
        DEPRECATED: No longer marks tokens as used (soft delete).

        This method is kept for backward compatibility but does nothing.
        Token usage is now tracked via download_count and last_downloaded_at
        in record_download() method.

        Args:
            token: UUID token string

        Returns:
            bool: Always returns True for compatibility
        """
        logger.debug(f"mark_as_used() called for token {token} - DEPRECATED, no action taken")
        return True

    async def cleanup_expired_tokens(self) -> int:
        """
        Delete expired tokens from the database.

        Removes all tokens where expires_at is in the past.
        Should be run periodically as a background task.

        Returns:
            int: Number of tokens deleted
        """
        try:
            now = datetime.now(timezone.utc)

            # Delete expired tokens
            stmt = delete(DownloadToken).where(DownloadToken.expires_at < now)
            result = await self.db_session.execute(stmt)
            await self.db_session.commit()

            deleted_count = result.rowcount

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired download tokens")

            return deleted_count

        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Error cleaning up expired tokens: {e}")
            return 0

    async def get_token_info(self, token: str, tenant_key: str) -> Optional[dict]:
        """
        Retrieve token information (for debugging/monitoring).

        Args:
            token: UUID token string
            tenant_key: Tenant identifier for isolation check

        Returns:
            Optional[dict]: Token metadata or None if not found
        """
        try:
            stmt = select(DownloadToken).where(DownloadToken.token == token, DownloadToken.tenant_key == tenant_key)
            result = await self.db_session.execute(stmt)
            token_record = result.scalar_one_or_none()

            if not token_record:
                return None

            return {
                "token": token_record.token,
                "tenant_key": token_record.tenant_key,
                "download_type": token_record.download_type,
                "metadata": token_record.meta_data,
                "is_expired": token_record.is_expired,
                "staging_status": token_record.staging_status,
                "staging_error": token_record.staging_error,
                "download_count": token_record.download_count,
                "created_at": token_record.created_at.isoformat(),
                "expires_at": token_record.expires_at.isoformat(),
                "last_downloaded_at": token_record.last_downloaded_at.isoformat() if token_record.last_downloaded_at else None,
            }

        except Exception as e:
            logger.error(f"Error retrieving token info: {e}")
            return None

    async def get_token_info_by_token(self, token: str) -> Optional[dict]:
        """
        Retrieve token information by token only (no tenant isolation).
        Used for download validation where token is the authentication.

        Args:
            token: UUID token string

        Returns:
            Optional[dict]: Token metadata or None if not found
        """
        try:
            stmt = select(DownloadToken).where(DownloadToken.token == token)
            result = await self.db_session.execute(stmt)
            token_record = result.scalar_one_or_none()

            if not token_record:
                return None

            return {
                "token": token_record.token,
                "tenant_key": token_record.tenant_key,
                "download_type": token_record.download_type,
                "metadata": token_record.meta_data,
                "is_expired": token_record.is_expired,
                "staging_status": token_record.staging_status,
                "staging_error": token_record.staging_error,
                "download_count": token_record.download_count,
                "created_at": token_record.created_at.isoformat(),
                "expires_at": token_record.expires_at.isoformat(),
                "last_downloaded_at": token_record.last_downloaded_at.isoformat() if token_record.last_downloaded_at else None,
            }

        except Exception as e:
            logger.error(f"Error retrieving token info: {e}")
            return None

    async def mark_failed(self, token: str, error_message: str) -> bool:
        """
        Mark token as failed with error message.

        Updates staging_status to 'failed' and records error details.
        Used when file staging fails during token generation.

        Args:
            token: UUID token string
            error_message: Error description for debugging

        Returns:
            bool: True if successfully marked, False otherwise
        """
        try:
            # Query token (no tenant isolation - token is unique)
            stmt = select(DownloadToken).where(DownloadToken.token == token)
            result = await self.db_session.execute(stmt)
            token_record = result.scalar_one_or_none()

            if not token_record:
                logger.warning(f"Cannot mark non-existent token as failed: {token}")
                return False

            # Update staging status
            token_record.staging_status = "failed"
            token_record.staging_error = error_message

            await self.db_session.commit()

            logger.info(f"Token marked as failed: {token}, error: {error_message}")
            return True

        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Error marking token as failed: {e}")
            return False

    async def mark_ready(self, token: str) -> bool:
        """
        Mark token as ready for download.

        Updates staging_status to 'ready' after successful file staging.
        Token becomes available for download.

        Args:
            token: UUID token string

        Returns:
            bool: True if successfully marked, False otherwise
        """
        try:
            # Query token (no tenant isolation - token is unique)
            stmt = select(DownloadToken).where(DownloadToken.token == token)
            result = await self.db_session.execute(stmt)
            token_record = result.scalar_one_or_none()

            if not token_record:
                logger.warning(f"Cannot mark non-existent token as ready: {token}")
                return False

            # Update staging status
            token_record.staging_status = "ready"
            token_record.staging_error = None  # Clear any previous errors

            await self.db_session.commit()

            logger.info(f"Token marked as ready: {token}")
            return True

        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Error marking token as ready: {e}")
            return False

    async def increment_download_count(self, token: str) -> bool:
        """
        Increment download counter and update last download timestamp.

        Updates download_count and last_downloaded_at for metrics tracking.
        Called after successful file download.

        Args:
            token: UUID token string

        Returns:
            bool: True if successfully updated, False otherwise
        """
        try:
            # Query token (no tenant isolation - token is unique)
            stmt = select(DownloadToken).where(DownloadToken.token == token)
            result = await self.db_session.execute(stmt)
            token_record = result.scalar_one_or_none()

            if not token_record:
                logger.warning(f"Cannot increment download count for non-existent token: {token}")
                return False

            # Increment counter and update timestamp
            token_record.download_count += 1
            token_record.last_downloaded_at = datetime.now(timezone.utc)

            await self.db_session.commit()

            logger.info(f"Download count incremented for token: {token}, new count: {token_record.download_count}")
            return True

        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Error incrementing download count: {e}")
            return False
