"""
TDD Test: Session cleanup behavior when GeneratorExit occurs during active transaction.

This test captures the BEHAVIOR we expect:
- When a session is yielded and GeneratorExit occurs (HTTPException, client disconnect)
- The session MUST be rolled back if active
- The session MUST be closed without IllegalStateChangeError
- No connection pool leaks

This test should FAIL (RED) with the current buggy implementation and
PASS (GREEN) after the fix.

Test Philosophy:
- Tests BEHAVIOR, not implementation details
- Uses descriptive test names per TDD guidelines
- Exercises the REAL database.py and dependencies.py code
"""

import asyncio
import warnings
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from sqlalchemy.exc import IllegalStateChangeError


class TestSessionCleanupBehavior:
    """
    Test that session cleanup handles GeneratorExit correctly.

    BEHAVIOR UNDER TEST:
    When FastAPI dependency get_db_session() yields a session and GeneratorExit
    is raised (due to HTTPException or client disconnect), the cleanup MUST:
    1. Rollback any active transaction
    2. Close the session without IllegalStateChangeError
    3. Return the connection to the pool
    """

    @pytest.mark.asyncio
    async def test_cleanup_rolls_back_active_session_before_close(self):
        """
        Test that an active session is rolled back before close() is called.

        BEHAVIOR: When session.is_active is True during cleanup, rollback MUST
        be called before close to prevent IllegalStateChangeError.

        This is the core behavioral requirement.
        """
        from src.giljo_mcp.database import DatabaseManager

        # Track method calls
        rollback_called = False
        close_called = False
        close_called_while_active = False

        class MockAsyncSession:
            """Mock session that tracks cleanup order."""

            def __init__(self):
                self._is_active = True  # Simulate active transaction

            @property
            def is_active(self):
                return self._is_active

            async def commit(self):
                self._is_active = False

            async def rollback(self):
                nonlocal rollback_called
                rollback_called = True
                self._is_active = False

            async def close(self):
                nonlocal close_called, close_called_while_active
                close_called = True
                if self._is_active:
                    close_called_while_active = True
                    # This is what SQLAlchemy does in production
                    raise IllegalStateChangeError(
                        "Method 'close()' can't be called here; "
                        "method '_connection_for_bind()' is already in progress"
                    )

        # Create a real DatabaseManager but mock the session creation
        mock_session = MockAsyncSession()

        # Mock AsyncSessionLocal as a callable that returns the session directly
        # (matching the new single-layer implementation in database.py)
        def mock_session_factory():
            return mock_session

        # Patch the AsyncSessionLocal to return our mock
        with patch.object(DatabaseManager, '__init__', lambda self, *args, **kwargs: None):
            db_manager = DatabaseManager.__new__(DatabaseManager)
            db_manager.is_async = True
            db_manager.AsyncSessionLocal = mock_session_factory

            # Act: Use get_session_async and simulate GeneratorExit
            try:
                async with db_manager.get_session_async() as session:
                    # Session is active (simulating mid-transaction)
                    assert session.is_active, "Session should be active"
                    # Simulate GeneratorExit (what FastAPI does on HTTPException)
                    raise GeneratorExit()
            except GeneratorExit:
                pass  # Expected
            except IllegalStateChangeError as e:
                pytest.fail(
                    f"IllegalStateChangeError during cleanup: {e}\n"
                    f"This means close() was called while session was still active.\n"
                    f"Rollback should have been called first to clear is_active flag."
                )

        # Assert BEHAVIOR
        assert close_called, "Session.close() was never called - connection leak!"
        assert not close_called_while_active, (
            "close() was called while session was still active. "
            "Rollback should have been called first."
        )


    @pytest.mark.asyncio
    async def test_cleanup_does_not_raise_illegal_state_change_error(self):
        """
        Test that cleanup completes without IllegalStateChangeError.

        BEHAVIOR: Even when GeneratorExit interrupts an active session,
        cleanup MUST complete without raising IllegalStateChangeError.
        """
        from src.giljo_mcp.database import DatabaseManager

        class StrictMockSession:
            """Session that strictly enforces state rules like SQLAlchemy does."""

            def __init__(self):
                self._is_active = True
                self._in_transaction = True

            @property
            def is_active(self):
                return self._is_active

            async def commit(self):
                self._is_active = False
                self._in_transaction = False

            async def rollback(self):
                self._is_active = False
                self._in_transaction = False

            async def close(self):
                if self._in_transaction:
                    raise IllegalStateChangeError(
                        "Method 'close()' can't be called here; "
                        "method '_connection_for_bind()' is already in progress"
                    )

        mock_session = StrictMockSession()

        # Mock AsyncSessionLocal as a callable that returns the session directly
        def mock_session_factory():
            return mock_session

        with patch.object(DatabaseManager, '__init__', lambda self, *args, **kwargs: None):
            db_manager = DatabaseManager.__new__(DatabaseManager)
            db_manager.is_async = True
            db_manager.AsyncSessionLocal = mock_session_factory

            # This should NOT raise IllegalStateChangeError
            try:
                async with db_manager.get_session_async() as session:
                    raise GeneratorExit()
            except GeneratorExit:
                pass
            except IllegalStateChangeError as e:
                pytest.fail(f"IllegalStateChangeError raised during cleanup: {e}")


    @pytest.mark.asyncio
    async def test_cleanup_handles_generator_exit_as_base_exception(self):
        """
        Test that GeneratorExit (which is BaseException, not Exception) is handled.

        BEHAVIOR: GeneratorExit must trigger proper cleanup even though it's
        not caught by 'except Exception:' blocks.
        """
        from src.giljo_mcp.database import DatabaseManager

        cleanup_completed = False

        class TrackingMockSession:
            def __init__(self):
                self._is_active = False

            @property
            def is_active(self):
                return self._is_active

            async def commit(self):
                pass

            async def rollback(self):
                pass

            async def close(self):
                nonlocal cleanup_completed
                cleanup_completed = True

        mock_session = TrackingMockSession()

        # Mock AsyncSessionLocal as a callable that returns the session directly
        def mock_session_factory():
            return mock_session

        with patch.object(DatabaseManager, '__init__', lambda self, *args, **kwargs: None):
            db_manager = DatabaseManager.__new__(DatabaseManager)
            db_manager.is_async = True
            db_manager.AsyncSessionLocal = mock_session_factory

            try:
                async with db_manager.get_session_async() as session:
                    # GeneratorExit is BaseException, NOT Exception
                    raise GeneratorExit()
            except GeneratorExit:
                pass

        assert cleanup_completed, (
            "Cleanup did not complete when GeneratorExit was raised. "
            "GeneratorExit is BaseException (not Exception) and must be handled."
        )


class TestFastAPIDependencySessionBehavior:
    """
    Test the FastAPI dependency get_db_session behavior.

    These tests verify the integration between FastAPI's dependency injection
    and our session management.
    """

    @pytest.mark.asyncio
    async def test_dependency_cleans_up_on_generator_exit(self):
        """
        Test that get_db_session dependency cleans up when generator is closed.

        BEHAVIOR: When FastAPI calls aclose() on the dependency generator
        (due to HTTPException), cleanup MUST execute.
        """
        from fastapi import Request
        from src.giljo_mcp.auth.dependencies import get_db_session
        from src.giljo_mcp.database import DatabaseManager

        session_closed = False

        class MockSession:
            def __init__(self):
                self._is_active = False

            @property
            def is_active(self):
                return self._is_active

            async def commit(self):
                pass

            async def rollback(self):
                pass

            async def close(self):
                nonlocal session_closed
                session_closed = True

        mock_session = MockSession()

        @asynccontextmanager
        async def mock_get_session():
            try:
                yield mock_session
                await mock_session.commit()
            except Exception:
                await mock_session.rollback()
                raise
            finally:
                await mock_session.close()

        # Create mock request with db_manager
        mock_request = MagicMock(spec=Request)
        mock_db_manager = MagicMock(spec=DatabaseManager)
        mock_db_manager.get_session_async = mock_get_session
        mock_request.app.state.api_state.db_manager = mock_db_manager

        # Get the generator
        gen = get_db_session(mock_request)

        # Start the generator (get session)
        session = await gen.__anext__()

        # Close the generator (simulates FastAPI cleanup on HTTPException)
        await gen.aclose()

        assert session_closed, (
            "Session was not closed when dependency generator was closed. "
            "This causes connection pool leaks."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=long"])
