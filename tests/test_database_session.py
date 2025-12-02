"""
Test database session cleanup and error handling.

This test suite validates the fix for SQLAlchemy async session cleanup
issues, particularly around GeneratorExit during FastAPI dependency
injection.

Bug Context:
- HTTPException raised in endpoints causes GeneratorExit in dependency
- Nested async context managers can cause IllegalStateChangeError
- Sessions must properly return to connection pool on all exit paths

Test Strategy (TDD Red Phase):
- Write failing tests first to validate expected behavior
- Tests should verify session cleanup, connection pool returns, and
  proper error handling for all edge cases
"""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, Request
from sqlalchemy.exc import IllegalStateChangeError
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_db_session


logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_session_cleanup_on_http_exception():
    """
    Test that session cleans up properly when endpoint raises HTTPException.

    Scenario:
    1. FastAPI dependency yields session
    2. Endpoint raises HTTPException (e.g., 401 Unauthorized)
    3. Dependency receives GeneratorExit
    4. Session must rollback and close without errors

    Expected Behavior:
    - No IllegalStateChangeError raised
    - Session is rolled back (not committed)
    - Session is properly closed
    - Connection returned to pool
    """
    # Mock app state with db_manager
    mock_request = MagicMock(spec=Request)
    mock_db_manager = MagicMock()
    mock_session = AsyncMock(spec=AsyncSession)

    # Track session lifecycle calls
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()

    # Mock session factory to return our tracked session
    mock_db_manager.AsyncSessionLocal = MagicMock(return_value=mock_session)

    # Setup app state
    mock_request.app.state.api_state.db_manager = mock_db_manager

    # Simulate HTTPException scenario
    dependency_gen = get_db_session(mock_request)

    try:
        # Start the dependency (yields session)
        session = await dependency_gen.__anext__()
        assert session is mock_session

        # Simulate HTTPException raised in endpoint
        # This causes GeneratorExit to be sent to the generator
        await dependency_gen.aclose()

    except StopAsyncIteration:
        pass  # Normal generator completion

    # ASSERTIONS: Verify proper cleanup
    # Session should NOT be committed when HTTPException occurs
    mock_session.commit.assert_not_called()

    # Session should be rolled back
    mock_session.rollback.assert_called_once()

    # Session should be closed
    mock_session.close.assert_called_once()

    # No IllegalStateChangeError should be raised (test passes if we reach here)


@pytest.mark.asyncio
async def test_session_cleanup_on_generator_exit():
    """
    Test that GeneratorExit during yield doesn't cause IllegalStateChangeError.

    Scenario:
    1. Dependency yields session
    2. Client disconnects or HTTPException raised
    3. Python sends GeneratorExit to generator
    4. Session cleanup must handle GeneratorExit gracefully

    Expected Behavior:
    - GeneratorExit is caught and handled
    - No IllegalStateChangeError propagates
    - Session cleanup completes successfully
    """
    mock_request = MagicMock(spec=Request)
    mock_db_manager = MagicMock()
    mock_session = AsyncMock(spec=AsyncSession)

    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()

    mock_db_manager.AsyncSessionLocal = MagicMock(return_value=mock_session)
    mock_request.app.state.api_state.db_manager = mock_db_manager

    # Create dependency generator
    dependency_gen = get_db_session(mock_request)

    try:
        # Get session
        session = await dependency_gen.__anext__()
        assert session is mock_session

        # Simulate GeneratorExit (e.g., from HTTPException)
        # This should NOT raise IllegalStateChangeError
        with pytest.raises(StopAsyncIteration):
            await dependency_gen.athrow(GeneratorExit)

    except GeneratorExit:
        # GeneratorExit might propagate in some scenarios
        pass

    # Verify cleanup happened
    mock_session.rollback.assert_called_once()
    mock_session.close.assert_called_once()


@pytest.mark.asyncio
async def test_session_returns_to_pool_after_error():
    """
    Test that connection returns to pool after error, no orphaned connections.

    Scenario:
    1. Multiple requests acquire sessions from pool
    2. Some requests fail with exceptions
    3. Sessions must return to pool for reuse
    4. Pool should not be exhausted by failed requests

    Expected Behavior:
    - Session close() called on all error paths
    - No connection leaks
    - Pool statistics show connections returned
    """
    mock_request = MagicMock(spec=Request)
    mock_db_manager = MagicMock()

    # Track created sessions
    created_sessions = []

    def create_session():
        session = AsyncMock(spec=AsyncSession)
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.close = AsyncMock()
        created_sessions.append(session)
        return session

    mock_db_manager.AsyncSessionLocal = MagicMock(side_effect=create_session)
    mock_request.app.state.api_state.db_manager = mock_db_manager

    # Simulate multiple requests with various failure modes
    failure_scenarios = [
        HTTPException(status_code=401, detail="Unauthorized"),
        ValueError("Database error"),
        GeneratorExit(),
    ]

    for error in failure_scenarios:
        dependency_gen = get_db_session(mock_request)

        try:
            session = await dependency_gen.__anext__()

            # Simulate error during request
            if isinstance(error, GeneratorExit):
                await dependency_gen.aclose()
            else:
                await dependency_gen.athrow(type(error), error)

        except (HTTPException, ValueError, StopAsyncIteration, GeneratorExit):
            pass  # Expected

    # ASSERTIONS: All sessions should be closed (returned to pool)
    assert len(created_sessions) == 3, "Should create 3 sessions"

    for session in created_sessions:
        session.close.assert_called_once(), "Each session must be closed"


@pytest.mark.asyncio
async def test_concurrent_session_requests():
    """
    Test that multiple concurrent requests don't cause session conflicts.

    Scenario:
    1. Multiple concurrent requests acquire sessions
    2. Each request operates on isolated session
    3. Some requests succeed, others fail
    4. No session state conflicts between requests

    Expected Behavior:
    - Each request gets independent session
    - No shared state between concurrent sessions
    - All sessions properly cleaned up
    - No deadlocks or race conditions
    """
    mock_db_manager = MagicMock()

    # Track sessions for each request
    sessions_by_request = {}

    def create_session():
        session = AsyncMock(spec=AsyncSession)
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.close = AsyncMock()
        return session

    mock_db_manager.AsyncSessionLocal = MagicMock(side_effect=create_session)

    async def simulate_request(request_id: int, should_fail: bool):
        """Simulate a single API request"""
        mock_request = MagicMock(spec=Request)
        mock_request.app.state.api_state.db_manager = mock_db_manager

        dependency_gen = get_db_session(mock_request)

        try:
            session = await dependency_gen.__anext__()
            sessions_by_request[request_id] = session

            # Simulate some work
            await asyncio.sleep(0.01)

            if should_fail:
                # Simulate failure
                await dependency_gen.athrow(
                    HTTPException,
                    HTTPException(status_code=500, detail="Internal error")
                )
            else:
                # Normal completion
                await dependency_gen.__anext__()

        except (HTTPException, StopAsyncIteration):
            pass  # Expected

    # Run 10 concurrent requests (5 succeed, 5 fail)
    tasks = [
        simulate_request(i, should_fail=(i % 2 == 0))
        for i in range(10)
    ]

    await asyncio.gather(*tasks, return_exceptions=True)

    # ASSERTIONS: Verify isolation and cleanup
    assert len(sessions_by_request) == 10, "Should create 10 independent sessions"

    # Verify all sessions are unique (no sharing)
    unique_sessions = set(id(s) for s in sessions_by_request.values())
    assert len(unique_sessions) == 10, "All sessions must be unique instances"

    # Verify all sessions were closed
    for session in sessions_by_request.values():
        session.close.assert_called_once(), "All sessions must be closed"


@pytest.mark.asyncio
async def test_session_cleanup_on_rollback_failure():
    """
    Test that session close() is called even if rollback() fails.

    Scenario:
    1. Request fails with exception
    2. Rollback itself raises an error
    3. Session close() must still be called
    4. Original exception should be preserved

    Expected Behavior:
    - Close called even if rollback fails
    - Rollback error logged but not raised
    - Original exception propagates
    """
    mock_request = MagicMock(spec=Request)
    mock_db_manager = MagicMock()
    mock_session = AsyncMock(spec=AsyncSession)

    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock(side_effect=Exception("Rollback failed"))
    mock_session.close = AsyncMock()

    mock_db_manager.AsyncSessionLocal = MagicMock(return_value=mock_session)
    mock_request.app.state.api_state.db_manager = mock_db_manager

    dependency_gen = get_db_session(mock_request)

    original_error = ValueError("Database query failed")

    try:
        session = await dependency_gen.__anext__()
        # Trigger error
        await dependency_gen.athrow(type(original_error), original_error)
    except ValueError as e:
        # Original exception should propagate
        assert str(e) == "Database query failed"
    except StopAsyncIteration:
        pass

    # Even though rollback failed, close should still be called
    mock_session.close.assert_called_once()


@pytest.mark.asyncio
async def test_session_commit_only_on_success():
    """
    Test that session commits only when no exception occurs.

    Scenario:
    1. Request completes successfully
    2. No exceptions raised
    3. Session should commit changes

    Expected Behavior:
    - Commit called on successful completion
    - Rollback NOT called
    - Session closed after commit
    """
    mock_request = MagicMock(spec=Request)
    mock_db_manager = MagicMock()
    mock_session = AsyncMock(spec=AsyncSession)

    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()

    mock_db_manager.AsyncSessionLocal = MagicMock(return_value=mock_session)
    mock_request.app.state.api_state.db_manager = mock_db_manager

    dependency_gen = get_db_session(mock_request)

    try:
        session = await dependency_gen.__anext__()
        # Normal completion (no exception)
        await dependency_gen.__anext__()
    except StopAsyncIteration:
        pass  # Expected

    # Verify commit was called
    mock_session.commit.assert_called_once()

    # Verify rollback was NOT called
    mock_session.rollback.assert_not_called()

    # Session should still be closed
    mock_session.close.assert_called_once()


@pytest.mark.asyncio
async def test_db_session_without_db_manager():
    """
    Test that proper error is raised when db_manager not initialized.

    Scenario:
    1. App in setup mode (db_manager is None)
    2. Request tries to access database
    3. Should raise 503 Service Unavailable

    Expected Behavior:
    - HTTPException 503 raised
    - Clear error message about setup mode
    """
    mock_request = MagicMock(spec=Request)

    # Simulate missing db_manager (setup mode)
    mock_request.app.state.api_state.db_manager = None

    dependency_gen = get_db_session(mock_request)

    with pytest.raises(HTTPException) as exc_info:
        await dependency_gen.__anext__()

    assert exc_info.value.status_code == 503
    assert "setup" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_session_close_error_is_logged_not_raised():
    """
    Test that errors during session.close() are logged but don't propagate.

    Scenario:
    1. Session cleanup encounters close() error
    2. Error should be logged
    3. Error should NOT propagate to caller
    4. Connection pool cleanup handles orphaned connection

    Expected Behavior:
    - Close error logged as warning
    - No exception raised to caller
    - Test completes successfully
    """
    mock_request = MagicMock(spec=Request)
    mock_db_manager = MagicMock()
    mock_session = AsyncMock(spec=AsyncSession)

    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    # Simulate close() error
    mock_session.close = AsyncMock(side_effect=Exception("Connection already closed"))

    mock_db_manager.AsyncSessionLocal = MagicMock(return_value=mock_session)
    mock_request.app.state.api_state.db_manager = mock_db_manager

    dependency_gen = get_db_session(mock_request)

    # This should NOT raise even though close() fails
    try:
        session = await dependency_gen.__anext__()
        await dependency_gen.__anext__()
    except StopAsyncIteration:
        pass  # Expected - no error should propagate

    # Verify close was attempted
    mock_session.close.assert_called_once()

    # Test passes if we reach here (no exception propagated)
