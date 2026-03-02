"""
Shared pytest fixtures for unit tests (Handover 0605-0608)

Provides correctly configured mocks for async database operations.
"""

from unittest.mock import AsyncMock, Mock

import pytest


@pytest.fixture
def mock_db_manager():
    """
    Create properly configured mock database manager.

    Returns tuple of (db_manager, session) where session is an async
    context manager that can be used with 'async with' statements.

    Example:
        db_manager, session = mock_db_manager
        service = MyService(db_manager, tenant_manager)
        # session is automatically configured as async context manager
    """
    db_manager = Mock()
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = Mock()
    session.delete = Mock()
    session.flush = AsyncMock()
    session.rollback = AsyncMock()
    db_manager.get_session_async = Mock(return_value=session)
    db_manager.get_tenant_session_async = Mock(return_value=session)
    return db_manager, session


@pytest.fixture
def mock_tenant_manager():
    """
    Create mock tenant manager with default test tenant.

    Returns a tenant manager that returns "test-tenant" by default.
    Override in tests by setting:
        tenant_manager.get_current_tenant = Mock(return_value="other-tenant")
    """
    tenant_manager = Mock()
    tenant_manager.get_current_tenant = Mock(return_value="test-tenant")
    return tenant_manager


@pytest.fixture
def failing_db_manager():
    """
    Create a database manager that raises exceptions.

    Useful for testing error handling paths.
    """
    db_manager = Mock()
    session = AsyncMock()
    session.__aenter__ = AsyncMock(side_effect=Exception("Connection lost"))
    session.__aexit__ = AsyncMock(return_value=False)
    db_manager.get_session_async = Mock(return_value=session)
    return db_manager
