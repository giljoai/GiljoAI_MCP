"""
Project Management Tools for GiljoAI MCP
Handles project lifecycle: create, list, switch, close
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import select, update

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Project
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.tenant import TenantManager, current_tenant


logger = logging.getLogger(__name__)


# Module-level variables for test injection (Handover 0366c)
_db_manager_instance: Optional[DatabaseManager] = None
_test_session: Optional[Any] = None


def init_for_testing(db_manager: DatabaseManager, db_session) -> None:
    """
    Initialize module for testing with shared session (Handover 0366c).

    This allows project tools to use the same database session as test fixtures,
    preventing session isolation issues during testing.

    Args:
        db_manager: DatabaseManager instance for tests
        db_session: Shared AsyncSession for test transaction isolation

    Usage:
        @pytest_asyncio.fixture(scope="function", autouse=True)
        async def setup_project_tools(db_manager, db_session):
            from src.giljo_mcp.tools import project
            project.init_for_testing(db_manager, db_session)
            yield
    """
    global _db_manager_instance, _test_session
    _db_manager_instance = db_manager
    _test_session = db_session


class _SessionWrapper:
    """
    Wrapper for database session that intercepts commit() in test mode.

    In tests: Converts commit() to flush() for transaction isolation
    In production: Passes through to real session
    """

    def __init__(self, session, test_mode=False):
        self._session = session
        self._test_mode = test_mode

    async def commit(self):
        """Commit in production, flush in tests."""
        if self._test_mode:
            await self._session.flush()
            # Don't expire all - let SQLAlchemy's session manage object state
            # Objects will be refreshed when accessed if needed
        else:
            await self._session.commit()

    async def flush(self):
        """Always flush."""
        await self._session.flush()

    async def refresh(self, *args, **kwargs):
        """Delegate to session."""
        return await self._session.refresh(*args, **kwargs)

    def add(self, *args, **kwargs):
        """Delegate to session."""
        return self._session.add(*args, **kwargs)

    async def execute(self, *args, **kwargs):
        """Delegate to session."""
        return await self._session.execute(*args, **kwargs)

    def __getattr__(self, name):
        """Delegate all other attributes to the wrapped session."""
        return getattr(self._session, name)


class _SessionContext:
    """
    Context manager for database sessions that handles both test and production modes.

    In tests: Uses injected test session (no commit, uses flush)
    In production: Creates new session via db_manager (commits)
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.test_mode = _test_session is not None
        self.session = None
        self.context_manager = None

    async def __aenter__(self):
        if self.test_mode:
            # Test mode - use injected session with wrapper
            self.session = _SessionWrapper(_test_session, test_mode=True)
        else:
            # Production mode - create new session
            self.context_manager = self.db_manager.get_session_async()
            real_session = await self.context_manager.__aenter__()
            self.session = _SessionWrapper(real_session, test_mode=False)
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if not self.test_mode and self.context_manager:
            # Production mode - let context manager handle cleanup
            return await self.context_manager.__aexit__(exc_type, exc_val, exc_tb)
        # Test mode - do nothing, test fixture handles cleanup
        return False


