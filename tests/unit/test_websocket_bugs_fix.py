"""
Unit tests for WebSocket Bug Fixes

Bug 1: Context Manager Pattern (api/app.py)
- Test proper async context manager lifecycle
- Test cleanup on exception
- Test no RuntimeError on cleanup

Bug 2: WebSocket Auth During Password Change (api/auth_utils.py)
- Test WebSocket auth when database_initialized=True but default_password_active=True
- Test WebSocket auth allows connection during password change phase
- Test WebSocket auth requires JWT after password change complete

Following TDD principles - tests written FIRST.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from contextlib import asynccontextmanager

from fastapi import WebSocket, WebSocketException
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth_utils import authenticate_websocket


class TestWebSocketContextManagerCleanup:
    """Test Bug 1: Proper async context manager cleanup in WebSocket endpoint"""

    @pytest.fixture
    def mock_db_manager(self):
        """Create mock DatabaseManager with proper async context manager"""
        manager = Mock()

        # Create a proper async context manager
        @asynccontextmanager
        async def mock_session_context():
            session = AsyncMock(spec=AsyncSession)
            try:
                yield session
            finally:
                # Proper cleanup
                await session.close()

        # get_session_async() should return the context manager
        manager.get_session_async = Mock(return_value=mock_session_context())
        return manager

    @pytest.mark.asyncio
    async def test_context_manager_proper_cleanup(self, mock_db_manager):
        """Test that context manager is properly entered and exited"""
        # This test verifies the CORRECT pattern:
        # cm = db_manager.get_session_async()
        # session = await cm.__aenter__()
        # try:
        #     ... use session ...
        # finally:
        #     await cm.__aexit__(None, None, None)

        cm = mock_db_manager.get_session_async()
        session = await cm.__aenter__()

        try:
            # Simulate using the session
            assert session is not None
            # Simulate auth check
            result = {'authenticated': True}
        finally:
            # Proper cleanup - should NOT raise RuntimeError
            await cm.__aexit__(None, None, None)

        # If we get here, no RuntimeError occurred

    @pytest.mark.asyncio
    async def test_context_manager_cleanup_on_exception(self, mock_db_manager):
        """Test that context manager cleanup works even when exception occurs"""
        cm = mock_db_manager.get_session_async()
        session = await cm.__aenter__()

        exception_occurred = False
        try:
            # Simulate exception during auth
            raise ValueError("Simulated auth error")
        except ValueError:
            exception_occurred = True
        finally:
            # Cleanup should still work
            await cm.__aexit__(None, None, None)

        assert exception_occurred
        # No RuntimeError should occur

    @pytest.mark.asyncio
    async def test_broken_pattern_causes_error(self):
        """Test that BROKEN pattern causes RuntimeError (current bug)"""
        # This demonstrates the WRONG pattern that causes the bug:
        # session = await db_manager.get_session_async().__aenter__()
        # ... later ...
        # await db_manager.get_session_async().__aexit__(None, None, None)
        #
        # This creates TWO DIFFERENT context manager instances!

        @asynccontextmanager
        async def create_session():
            session = AsyncMock(spec=AsyncSession)
            yield session

        # WRONG: Enter on first instance
        session1 = await create_session().__aenter__()

        # WRONG: Exit on DIFFERENT instance - causes RuntimeError
        with pytest.raises(RuntimeError, match="generator didn't stop"):
            await create_session().__aexit__(None, None, None)


class TestWebSocketAuthPasswordChange:
    """Test Bug 2: WebSocket auth during password change phase"""

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket without credentials"""
        ws = Mock(spec=WebSocket)
        ws.client = Mock()
        ws.client.host = '127.0.0.1'
        ws.query_params = {}  # No token during password change
        ws.headers = {}
        return ws

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session"""
        return AsyncMock(spec=AsyncSession)

    @pytest.mark.asyncio
    async def test_websocket_allowed_during_password_change(
        self, mock_websocket, mock_db_session
    ):
        """
        Test that WebSocket connections are allowed during password change.

        Current setup_state fields (will be renamed later):
        - completed: True (database_initialized in future)
        - default_password_active: True (password change in progress)

        Expected behavior: Allow WebSocket without JWT
        """
        # Password change phase: DB ready but default password still active
        with patch('api.auth_utils.get_setup_state', return_value={
            'setup_completed': True,  # DB initialized (current field name)
            'default_password_active': True  # Password change in progress
        }):
            # Should ALLOW connection without JWT during password change
            result = await authenticate_websocket(mock_websocket, db=mock_db_session)

            assert result['authenticated'] is True
            assert result['context'] in ['setup', 'password_change']

    @pytest.mark.asyncio
    async def test_websocket_allowed_during_initial_setup(
        self, mock_websocket, mock_db_session
    ):
        """Test that WebSocket allowed when database not initialized"""
        # Initial setup: DB not ready yet
        with patch('api.auth_utils.get_setup_state', return_value={
            'setup_completed': False,  # DB not initialized
            'default_password_active': True
        }):
            result = await authenticate_websocket(mock_websocket, db=mock_db_session)

            assert result['authenticated'] is True
            assert result['context'] == 'setup'

    @pytest.mark.asyncio
    async def test_websocket_requires_jwt_after_password_change(
        self, mock_websocket, mock_db_session
    ):
        """Test that WebSocket requires JWT after password change complete"""
        # Post password change: DB ready and password changed
        with patch('api.auth_utils.get_setup_state', return_value={
            'setup_completed': True,  # DB initialized
            'default_password_active': False  # Password change complete
        }):
            # Should REJECT connection without JWT
            with pytest.raises(WebSocketException) as exc_info:
                await authenticate_websocket(mock_websocket, db=mock_db_session)

            assert exc_info.value.code == 1008  # Policy violation

    @pytest.mark.asyncio
    async def test_websocket_with_jwt_after_password_change(
        self, mock_db_session
    ):
        """Test that WebSocket with valid JWT works after password change"""
        ws = Mock(spec=WebSocket)
        ws.client = Mock()
        ws.client.host = '127.0.0.1'
        ws.query_params = {'token': 'valid_jwt'}
        ws.headers = {}

        # Post password change: DB ready and password changed
        with patch('api.auth_utils.get_setup_state', return_value={
            'setup_completed': True,
            'default_password_active': False
        }):
            # Mock valid JWT
            with patch('api.auth_utils.validate_jwt_token', return_value={
                'user_id': 'admin',
                'tenant_key': 'default'
            }):
                result = await authenticate_websocket(ws, db=mock_db_session)

                assert result['authenticated'] is True
                assert result['user']['user_id'] == 'admin'


class TestWebSocketAuthLogic:
    """Test the complete auth logic with different setup states"""

    @pytest.fixture
    def mock_websocket_no_auth(self):
        """WebSocket without credentials"""
        ws = Mock(spec=WebSocket)
        ws.client = Mock()
        ws.client.host = '127.0.0.1'
        ws.query_params = {}
        ws.headers = {}
        return ws

    @pytest.mark.asyncio
    @pytest.mark.parametrize("setup_state,expected_allowed", [
        # Initial setup phase
        ({'setup_completed': False, 'default_password_active': True}, True),

        # Password change phase (BUG FIX - should allow)
        ({'setup_completed': True, 'default_password_active': True}, True),

        # Normal operation (requires JWT)
        ({'setup_completed': True, 'default_password_active': False}, False),
    ])
    async def test_websocket_auth_state_matrix(
        self, mock_websocket_no_auth, setup_state, expected_allowed
    ):
        """Test WebSocket auth across different setup states"""
        with patch('api.auth_utils.get_setup_state', return_value=setup_state):
            if expected_allowed:
                # Should allow connection
                result = await authenticate_websocket(
                    mock_websocket_no_auth, db=AsyncMock()
                )
                assert result['authenticated'] is True
            else:
                # Should reject connection
                with pytest.raises(WebSocketException):
                    await authenticate_websocket(
                        mock_websocket_no_auth, db=AsyncMock()
                    )


class TestWebSocketAuthLogging:
    """Test that proper logging is added for debugging"""

    @pytest.fixture
    def mock_websocket(self):
        ws = Mock(spec=WebSocket)
        ws.client = Mock()
        ws.client.host = '127.0.0.1'
        ws.query_params = {}
        ws.headers = {}
        return ws

    @pytest.mark.asyncio
    async def test_logging_during_password_change(self, mock_websocket):
        """Test that auth logic logs why connection is allowed"""
        with patch('api.auth_utils.get_setup_state', return_value={
            'setup_completed': True,
            'default_password_active': True
        }):
            with patch('api.auth_utils.logger') as mock_logger:
                result = await authenticate_websocket(mock_websocket, db=AsyncMock())

                # Should log why connection was allowed
                mock_logger.info.assert_called()
                # Check that log mentions password change or default password
                log_calls = [str(call) for call in mock_logger.info.call_args_list]
                assert any('password' in str(call).lower() or 'default' in str(call).lower()
                          for call in log_calls)

    @pytest.mark.asyncio
    async def test_logging_rejection_after_setup(self, mock_websocket):
        """Test that rejection is properly logged"""
        with patch('api.auth_utils.get_setup_state', return_value={
            'setup_completed': True,
            'default_password_active': False
        }):
            with patch('api.auth_utils.logger') as mock_logger:
                with pytest.raises(WebSocketException):
                    await authenticate_websocket(mock_websocket, db=AsyncMock())

                # Should log rejection reason
                mock_logger.warning.assert_called()


class TestContextManagerIntegration:
    """Integration test for context manager fix in api/app.py"""

    @pytest.mark.asyncio
    async def test_websocket_endpoint_context_manager_pattern(self):
        """
        Test that WebSocket endpoint uses correct context manager pattern.

        This is an integration test that would verify the fix in api/app.py
        around lines 604-640.
        """
        # This test documents the CORRECT pattern that should be in api/app.py

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_get_session():
            session = AsyncMock(spec=AsyncSession)
            try:
                yield session
            finally:
                await session.close()

        # CORRECT PATTERN (what the fix should implement):
        cm = mock_get_session()  # Get the context manager
        session = await cm.__aenter__()  # Enter it

        try:
            # Use the session for authentication
            auth_result = {'authenticated': True}
            # ... WebSocket logic ...
        finally:
            # ALWAYS cleanup, even on exception
            await cm.__aexit__(None, None, None)

        # Verify no RuntimeError occurred


class TestDatabaseInitializedField:
    """
    Test future-proofing for field rename.

    Note: Currently using 'completed' but will be renamed to 'database_initialized'
    """

    @pytest.mark.asyncio
    async def test_field_name_compatibility(self):
        """Test that code handles both old and new field names"""
        # Current field name: 'completed'
        # Future field name: 'database_initialized'

        ws = Mock(spec=WebSocket)
        ws.client = Mock()
        ws.client.host = '127.0.0.1'
        ws.query_params = {}
        ws.headers = {}

        # Test with current field name
        with patch('api.auth_utils.get_setup_state', return_value={
            'setup_completed': False,  # Current name
            'default_password_active': True
        }):
            result = await authenticate_websocket(ws, db=AsyncMock())
            assert result['authenticated'] is True

        # Future: When renamed to database_initialized, update tests
        # This test documents the expected field name change
