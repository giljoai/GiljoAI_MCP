# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
MCP Session Management for HTTP Transport

Provides session state management for MCP-over-HTTP connections.
Enables stateful context preservation across tool calls while maintaining
multi-tenant isolation.

Architecture:
- API key authentication via X-API-Key header
- Session persistence in PostgreSQL (mcp_sessions table)
- Auto-expiration after 24 hours of inactivity
- Tenant context resolution from API key -> User -> tenant_key
- Project context preservation across tool calls

Usage:
    session_manager = MCPSessionManager(db_session)
    session = await session_manager.get_or_create_session(api_key, project_id)
    await session_manager.update_session_data(session.session_id, data)
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.api_key_utils import verify_api_key
from src.giljo_mcp.models import APIKey, MCPSession, User


logger = logging.getLogger(__name__)


class MCPSessionManager:
    """Manages MCP HTTP sessions with PostgreSQL persistence"""

    DEFAULT_SESSION_LIFETIME_HOURS = 24
    SESSION_CLEANUP_THRESHOLD_HOURS = 48

    def __init__(self, db: AsyncSession):
        self.db = db

    async def authenticate_api_key(self, api_key_value: str):
        """Validate an API key and return the associated (APIKey, User) tuple.

        Iterates over active, non-expired keys and verifies the provided value
        against stored hashes. Returns None if no match is found or if the
        owning user is inactive.
        """
        try:
            # Defense-in-depth: narrow candidates by key_prefix to avoid loading all keys (Handover 0769a)
            # key_prefix is stored as "first12chars..." (see api_key_utils.get_key_prefix)
            key_prefix = f"{api_key_value[:12]}..." if len(api_key_value) >= 12 else api_key_value
            stmt = select(APIKey).where(
                APIKey.is_active,
                APIKey.key_prefix == key_prefix,
                or_(APIKey.expires_at > func.now(), APIKey.expires_at.is_(None)),
            )
            result = await self.db.execute(stmt)
            api_keys = result.scalars().all()

            for key_record in api_keys:
                if verify_api_key(api_key_value, key_record.key_hash):
                    key_record.last_used = datetime.now(timezone.utc)
                    await self.db.commit()

                    stmt = select(User).where(User.id == key_record.user_id, User.is_active)
                    result = await self.db.execute(stmt)
                    user = result.scalar_one_or_none()

                    if user:
                        logger.debug(f"API key authenticated: {key_record.name} (user: {user.username})")
                        return (key_record, user)

                    logger.warning(f"API key valid but user inactive: {key_record.user_id}")
                    return None

            logger.warning("Invalid API key provided")
            return None

        except Exception as e:  # Broad catch: API boundary, converts to HTTP error
            logger.error(f"API key authentication error: {e}", exc_info=True)
            return None

    async def log_ip(self, api_key_id: str, ip_address: str) -> None:
        """Log IP address for API key usage tracking (passive, non-blocking).

        Uses PostgreSQL upsert (INSERT ... ON CONFLICT) to either create a new
        entry or increment the request_count and update last_seen_at for an
        existing api_key + ip_address pair.

        This method is designed to never raise exceptions. All errors are
        caught and logged as warnings so that IP logging never blocks or
        slows down the authentication flow.

        Args:
            api_key_id: The ID of the API key that was used.
            ip_address: The client IP address (IPv4/IPv6 or 'unknown').
        """
        try:
            from uuid import uuid4

            from sqlalchemy.dialects.postgresql import insert as pg_insert

            from src.giljo_mcp.models.auth import ApiKeyIpLog

            stmt = (
                pg_insert(ApiKeyIpLog)
                .values(
                    id=str(uuid4()),
                    api_key_id=api_key_id,
                    ip_address=ip_address,
                )
                .on_conflict_do_update(
                    constraint="uq_api_key_ip",
                    set_={
                        "last_seen_at": func.now(),
                        "request_count": ApiKeyIpLog.request_count + 1,
                    },
                )
            )
            await self.db.execute(stmt)
            await self.db.commit()
        except Exception as e:  # noqa: BLE001 - API boundary: non-fatal IP logging
            logger.warning("Failed to log IP for API key %s: %s", api_key_id, e)

    async def get_or_create_session(self, api_key_value: str, project_id: str | None = None) -> MCPSession | None:
        """Authenticate and return an existing or newly created MCP session.

        Looks up an active session for the authenticated user's API key and
        tenant. If a valid session exists it is extended; otherwise a new one
        is created. Duplicate sessions are cleaned up automatically.
        """
        auth_result = await self.authenticate_api_key(api_key_value)
        if not auth_result:
            return None

        api_key, user = auth_result

        # Fetch any existing sessions for this API key + tenant ordered by most recent
        # Note: scalar_one_or_none() raises MultipleResultsFound when duplicates exist.
        # We tolerate duplicates by selecting the most recent and optionally cleaning up extras.
        stmt = (
            select(MCPSession)
            .where(MCPSession.api_key_id == api_key.id, MCPSession.tenant_key == user.tenant_key)
            .order_by(MCPSession.last_accessed.desc())
        )

        result = await self.db.execute(stmt)
        sessions = result.scalars().all()
        existing_session = sessions[0] if sessions else None

        # If duplicates exist, remove older ones to prevent future query exceptions
        if len(sessions) > 1:
            try:
                stale_ids = [s.id for s in sessions[1:]]
                if stale_ids:
                    await self.db.execute(delete(MCPSession).where(MCPSession.id.in_(stale_ids)))
                    await self.db.commit()
                    logger.warning(
                        f"[MCP Session] Deduplicated {len(stale_ids)} stale sessions for api_key={api_key.id} tenant={user.tenant_key}"
                    )
            except (ValueError, KeyError):
                logger.exception("[MCP Session] Failed to cleanup duplicate sessions")

        if existing_session and not existing_session.is_expired:
            existing_session.last_accessed = datetime.now(timezone.utc)
            existing_session.extend_expiration(self.DEFAULT_SESSION_LIFETIME_HOURS)

            if project_id:
                existing_session.project_id = project_id

            await self.db.commit()
            await self.db.refresh(existing_session)

            logger.debug(f"Reusing existing session: {existing_session.session_id}")
            return existing_session

        new_session = MCPSession(
            api_key_id=api_key.id,
            user_id=user.id,  # Handover 0424: Audit trail
            tenant_key=user.tenant_key,
            project_id=project_id,
            session_data={"initialized": False, "capabilities": {}, "client_info": {}, "tool_call_history": []},
            created_at=datetime.now(timezone.utc),
            last_accessed=datetime.now(timezone.utc),
        )
        new_session.extend_expiration(self.DEFAULT_SESSION_LIFETIME_HOURS)

        self.db.add(new_session)
        await self.db.commit()
        await self.db.refresh(new_session)

        logger.info(f"Created new MCP session: {new_session.session_id} (tenant: {user.tenant_key})")
        return new_session

    async def get_or_create_session_from_jwt(
        self, user_id: str, tenant_key: str, username: str | None = None
    ) -> MCPSession:
        """Create or reuse an MCP session for an OAuth JWT-authenticated user.

        Unlike get_or_create_session(), this method does not require an API key.
        Sessions are identified by user_id + tenant_key combination.

        Args:
            user_id: User ID from JWT 'sub' claim.
            tenant_key: Tenant key from JWT payload (required for isolation).
            username: Username from JWT payload (stored in session_data for audit).

        Returns:
            An existing or newly created MCPSession instance.
        """
        stmt = (
            select(MCPSession)
            .where(
                MCPSession.user_id == user_id,
                MCPSession.tenant_key == tenant_key,
                MCPSession.api_key_id.is_(None),
            )
            .order_by(MCPSession.last_accessed.desc())
        )
        result = await self.db.execute(stmt)
        sessions = result.scalars().all()
        existing_session = sessions[0] if sessions else None

        if existing_session and not existing_session.is_expired:
            existing_session.last_accessed = datetime.now(timezone.utc)
            existing_session.extend_expiration(self.DEFAULT_SESSION_LIFETIME_HOURS)
            await self.db.commit()
            await self.db.refresh(existing_session)
            logger.debug(f"Reusing JWT session: {existing_session.session_id}")
            return existing_session

        new_session = MCPSession(
            api_key_id=None,
            user_id=user_id,
            tenant_key=tenant_key,
            session_data={
                "initialized": False,
                "capabilities": {},
                "client_info": {},
                "tool_call_history": [],
                "auth_method": "oauth_jwt",
                "username": username,
            },
            created_at=datetime.now(timezone.utc),
            last_accessed=datetime.now(timezone.utc),
        )
        new_session.extend_expiration(self.DEFAULT_SESSION_LIFETIME_HOURS)

        self.db.add(new_session)
        await self.db.commit()
        await self.db.refresh(new_session)

        logger.info(f"Created new JWT session: {new_session.session_id} (tenant: {tenant_key})")
        return new_session

    async def get_session(self, session_id: str, tenant_key: str | None = None) -> MCPSession | None:
        """Retrieve a session by ID, returning None if expired or not found."""
        stmt = select(MCPSession).where(MCPSession.session_id == session_id)
        if tenant_key is not None:
            stmt = stmt.where(MCPSession.tenant_key == tenant_key)
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()

        if session and session.is_expired:
            logger.warning(f"Session expired: {session_id}")
            return None

        return session

    async def update_session_data(
        self, session_id: str, data: dict[str, Any], merge: bool = True, tenant_key: str | None = None
    ) -> bool:
        """Update the JSON session_data blob for a session.

        When merge is True (default), new keys are merged into existing data.
        When False, the entire blob is replaced.

        Args:
            tenant_key: When provided, the lookup is scoped to this tenant
                        (recommended for multi-tenant isolation).
        """
        session = await self.get_session(session_id, tenant_key=tenant_key)
        if not session:
            return False

        if merge:
            current_data = session.session_data or {}
            current_data.update(data)
            session.session_data = current_data
        else:
            session.session_data = data

        session.last_accessed = datetime.now(timezone.utc)
        await self.db.commit()

        logger.debug(f"Updated session data: {session_id}")
        return True

    async def cleanup_expired_sessions(self) -> int:
        """Delete sessions inactive beyond SESSION_CLEANUP_THRESHOLD_HOURS.

        Returns the number of sessions removed.
        """
        threshold = datetime.now(timezone.utc) - timedelta(hours=self.SESSION_CLEANUP_THRESHOLD_HOURS)

        stmt = delete(MCPSession).where(MCPSession.last_accessed < threshold)

        result = await self.db.execute(stmt)
        await self.db.commit()

        count = result.rowcount
        if count > 0:
            logger.info(f"Cleaned up {count} expired MCP sessions")

        return count

    async def delete_session(self, session_id: str, tenant_key: str | None = None) -> bool:
        """Delete a specific session by ID. Returns True if a session was removed.

        Args:
            tenant_key: When provided, the DELETE is scoped to this tenant
                        (recommended for multi-tenant isolation).
        """
        stmt = delete(MCPSession).where(MCPSession.session_id == session_id)
        if tenant_key is not None:
            stmt = stmt.where(MCPSession.tenant_key == tenant_key)
        result = await self.db.execute(stmt)
        await self.db.commit()

        if result.rowcount > 0:
            logger.info(f"Deleted MCP session: {session_id}")
            return True

        return False
