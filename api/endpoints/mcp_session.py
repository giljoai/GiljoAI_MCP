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
from typing import Any, Dict, Optional

from sqlalchemy import delete, select
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
        try:
            stmt = select(APIKey).where(APIKey.is_active == True)
            result = await self.db.execute(stmt)
            api_keys = result.scalars().all()

            for key_record in api_keys:
                if verify_api_key(api_key_value, key_record.key_hash):
                    key_record.last_used = datetime.now(timezone.utc)
                    await self.db.commit()

                    stmt = select(User).where(User.id == key_record.user_id, User.is_active == True)
                    result = await self.db.execute(stmt)
                    user = result.scalar_one_or_none()

                    if user:
                        logger.debug(f"API key authenticated: {key_record.name} (user: {user.username})")
                        return (key_record, user)

                    logger.warning(f"API key valid but user inactive: {key_record.user_id}")
                    return None

            logger.warning("Invalid API key provided")
            return None

        except Exception as e:
            logger.error(f"API key authentication error: {e}", exc_info=True)
            return None

    async def get_or_create_session(self, api_key_value: str, project_id: Optional[str] = None) -> Optional[MCPSession]:
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
            except (ValueError, KeyError) as cleanup_err:
                logger.error(f"[MCP Session] Failed to cleanup duplicate sessions: {cleanup_err}")

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

    async def get_session(self, session_id: str) -> Optional[MCPSession]:
        stmt = select(MCPSession).where(MCPSession.session_id == session_id)
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()

        if session and session.is_expired:
            logger.warning(f"Session expired: {session_id}")
            return None

        return session

    async def update_session_data(self, session_id: str, data: dict[str, Any], merge: bool = True) -> bool:
        session = await self.get_session(session_id)
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
        threshold = datetime.now(timezone.utc) - timedelta(hours=self.SESSION_CLEANUP_THRESHOLD_HOURS)

        stmt = delete(MCPSession).where(MCPSession.last_accessed < threshold)

        result = await self.db.execute(stmt)
        await self.db.commit()

        count = result.rowcount
        if count > 0:
            logger.info(f"Cleaned up {count} expired MCP sessions")

        return count

    async def delete_session(self, session_id: str) -> bool:
        stmt = delete(MCPSession).where(MCPSession.session_id == session_id)
        result = await self.db.execute(stmt)
        await self.db.commit()

        if result.rowcount > 0:
            logger.info(f"Deleted MCP session: {session_id}")
            return True

        return False
