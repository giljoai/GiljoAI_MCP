"""
Integration tests for unified authentication flow (Phase 2)

Tests complete authentication flow:
1. Fresh install creates admin/admin
2. Login blocks with default password active
3. Password change succeeds and sets default_password_active: false
4. Login succeeds after password changed
5. WebSocket requires auth for all connections

Following TDD principles - tests written BEFORE implementation.
"""

import pytest
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from passlib.hash import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import User, SetupState
from src.giljo_mcp.database import DatabaseManager


@pytest.fixture
async def test_db():
    """Create test database"""
    db_manager = DatabaseManager.get_instance()
    async with db_manager.get_session_async() as session:
        # Clean up before test
        from sqlalchemy import delete
        await session.execute(delete(User))
        await session.execute(delete(SetupState))
        await session.commit()
        yield session
        # Clean up after test
        await session.rollback()


@pytest.fixture
def test_client(test_app):
    """Create FastAPI test client"""
    return TestClient(test_app)


class TestCompleteAuthFlow:
    """Test complete unified authentication flow"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_01_fresh_install_creates_admin(self, test_db):
        """Step 1: Fresh install creates admin/admin account"""
        from installer.core.database import DatabaseInstaller

        # Run installer
        db_installer = DatabaseInstaller(settings={'pg_password': '4010'})
        result = await db_installer.create_default_admin_account(test_db)

        # Verify admin created
        assert result['success'] is True
        assert result['credentials']['username'] == 'admin'
        assert result['credentials']['password'] == 'admin'

        # Verify user in database
        from sqlalchemy import select
        stmt = select(User).where(User.username == 'admin')
        db_result = await test_db.execute(stmt)
        admin_user = db_result.scalar_one()

        assert admin_user.username == 'admin'
        assert admin_user.role == 'admin'
        assert bcrypt.verify('admin', admin_user.password_hash)

        # Verify setup state
        stmt = select(SetupState).where(SetupState.tenant_key == 'default')
        state_result = await test_db.execute(stmt)
        setup_state = state_result.scalar_one()

        assert setup_state.meta_data.get('default_password_active') is True

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_02_login_with_default_password_blocked(self, test_client, test_db):
        """Step 2: Login is blocked when default password is active"""
        # Create admin with default password
        admin = User(
            username='admin',
            password_hash=bcrypt.hash('admin'),
            role='admin',
            tenant_key='default',
            is_active=True
        )
        test_db.add(admin)

        # Setup state with default_password_active
        setup_state = SetupState(
            tenant_key='default',
            database_initialized=False,
            meta_data={'default_password_active': True}
        )
        test_db.add(setup_state)
        await test_db.commit()

        # Attempt login
        response = test_client.post('/auth/login', json={
            'username': 'admin',
            'password': 'admin'
        })

        # Should be blocked
        assert response.status_code == 403
        assert 'must_change_password' in response.json().get('detail', {}).get('error', '')

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_03_password_change_succeeds(self, test_client, test_db):
        """Step 3: Password change succeeds and updates setup state"""
        # Create admin
        admin = User(
            username='admin',
            password_hash=bcrypt.hash('admin'),
            role='admin',
            tenant_key='default',
            is_active=True
        )
        test_db.add(admin)

        # Setup state
        setup_state = SetupState(
            tenant_key='default',
            database_initialized=False,
            meta_data={'default_password_active': True}
        )
        test_db.add(setup_state)
        await test_db.commit()

        # Change password
        response = test_client.post('/auth/change-password', json={
            'current_password': 'admin',
            'new_password': 'MyNewSecurePassword123!',
            'confirm_password': 'MyNewSecurePassword123!'
        }, headers={
            'Authorization': f'Bearer {self._get_admin_token(test_client)}'
        })

        # Should succeed
        assert response.status_code == 200
        assert 'token' in response.json()

        # Verify password changed
        from sqlalchemy import select
        stmt = select(User).where(User.username == 'admin')
        result = await test_db.execute(stmt)
        user = result.scalar_one()

        assert not bcrypt.verify('admin', user.password_hash)
        assert bcrypt.verify('MyNewSecurePassword123!', user.password_hash)

        # Verify setup state updated
        stmt = select(SetupState).where(SetupState.tenant_key == 'default')
        state_result = await test_db.execute(stmt)
        setup_state = state_result.scalar_one()

        assert setup_state.meta_data.get('default_password_active') is False

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_04_login_after_password_change_succeeds(self, test_client, test_db):
        """Step 4: Login succeeds after password changed"""
        # Create admin with changed password
        admin = User(
            username='admin',
            password_hash=bcrypt.hash('MyNewSecurePassword123!'),
            role='admin',
            tenant_key='default',
            is_active=True
        )
        test_db.add(admin)

        # Setup state with password changed
        setup_state = SetupState(
            tenant_key='default',
            database_initialized=True,
            meta_data={'default_password_active': False}
        )
        test_db.add(setup_state)
        await test_db.commit()

        # Login
        response = test_client.post('/auth/login', json={
            'username': 'admin',
            'password': 'MyNewSecurePassword123!'
        })

        # Should succeed
        assert response.status_code == 200
        assert response.json()['message'] == 'Login successful'
        assert response.json()['username'] == 'admin'

        # Should set cookie
        assert 'access_token' in response.cookies

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_05_websocket_requires_auth_post_setup(self, test_client, test_db):
        """Step 5: WebSocket requires auth for all connections after setup"""
        # Setup completed
        setup_state = SetupState(
            tenant_key='default',
            database_initialized=True,
            meta_data={'default_password_active': False}
        )
        test_db.add(setup_state)
        await test_db.commit()

        # Attempt WebSocket connection without auth
        with pytest.raises(Exception):  # WebSocketException
            with test_client.websocket_connect('/ws/progress'):
                pass

        # Should fail for both localhost and network
        # (implementation detail: TestClient simulates localhost)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_06_websocket_with_token_succeeds(self, test_client, test_db):
        """Step 6: WebSocket with valid token succeeds"""
        # Create admin
        admin = User(
            username='admin',
            password_hash=bcrypt.hash('SecurePassword123!'),
            role='admin',
            tenant_key='default',
            is_active=True
        )
        test_db.add(admin)

        # Setup completed
        setup_state = SetupState(
            tenant_key='default',
            database_initialized=True,
            meta_data={'default_password_active': False}
        )
        test_db.add(setup_state)
        await test_db.commit()

        # Get valid token
        login_response = test_client.post('/auth/login', json={
            'username': 'admin',
            'password': 'SecurePassword123!'
        })
        token = login_response.json().get('token')

        # Connect with token
        with test_client.websocket_connect(f'/ws/progress?token={token}') as websocket:
            # Should succeed
            data = websocket.receive_json()
            assert 'authenticated' in data or data  # Implementation dependent

    def _get_admin_token(self, client):
        """Helper to get admin token"""
        response = client.post('/auth/login', json={
            'username': 'admin',
            'password': 'admin'
        })
        return response.json().get('token')


class TestLocalhostNetworkEquality:
    """Test that localhost and network clients are treated equally"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_localhost_requires_same_auth_as_network(self, test_client, test_db):
        """Test that localhost clients need same auth as network clients"""
        # Create admin
        admin = User(
            username='admin',
            password_hash=bcrypt.hash('SecurePassword123!'),
            role='admin',
            tenant_key='default',
            is_active=True
        )
        test_db.add(admin)

        # Setup completed
        setup_state = SetupState(
            tenant_key='default',
            database_initialized=True,
            meta_data={'default_password_active': False}
        )
        test_db.add(setup_state)
        await test_db.commit()

        # Both should require login
        # (TestClient always uses localhost, so we test the behavior)

        # Without auth - should fail
        response = test_client.get('/auth/me')
        assert response.status_code in [401, 403]  # Unauthorized

        # With auth - should succeed
        login_response = test_client.post('/auth/login', json={
            'username': 'admin',
            'password': 'SecurePassword123!'
        })
        token = login_response.cookies.get('access_token')

        response = test_client.get('/auth/me', cookies={'access_token': token})
        assert response.status_code == 200


class TestSetupModeWebSocket:
    """Test WebSocket behavior during setup mode"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_setup_mode_allows_websocket_without_auth(self, test_client, test_db):
        """Test that setup mode allows WebSocket connections without auth"""
        # Setup NOT completed
        setup_state = SetupState(
            tenant_key='default',
            database_initialized=False,
            meta_data={'default_password_active': True}
        )
        test_db.add(setup_state)
        await test_db.commit()

        # Should allow connection for setup progress
        with test_client.websocket_connect('/ws/progress') as websocket:
            # Should succeed
            assert websocket.client_state == websocket.client_state.CONNECTED


class TestErrorHandling:
    """Test error handling in authentication flow"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_login_with_invalid_credentials(self, test_client, test_db):
        """Test login with invalid credentials"""
        response = test_client.post('/auth/login', json={
            'username': 'nonexistent',
            'password': 'wrongpassword'
        })

        assert response.status_code == 401
        assert 'Invalid credentials' in response.json().get('detail', '')

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_password_change_with_wrong_current_password(self, test_client, test_db):
        """Test password change with wrong current password"""
        # Create admin
        admin = User(
            username='admin',
            password_hash=bcrypt.hash('admin'),
            role='admin',
            tenant_key='default',
            is_active=True
        )
        test_db.add(admin)
        await test_db.commit()

        response = test_client.post('/auth/change-password', json={
            'current_password': 'wrong',
            'new_password': 'NewSecurePassword123!',
            'confirm_password': 'NewSecurePassword123!'
        }, headers={
            'Authorization': 'Bearer valid_token'
        })

        assert response.status_code == 401

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_websocket_with_invalid_token(self, test_client, test_db):
        """Test WebSocket with invalid token"""
        # Setup completed
        setup_state = SetupState(
            tenant_key='default',
            database_initialized=True,
            meta_data={'default_password_active': False}
        )
        test_db.add(setup_state)
        await test_db.commit()

        # Attempt with invalid token
        with pytest.raises(Exception):
            with test_client.websocket_connect('/ws/progress?token=invalid_token'):
                pass
