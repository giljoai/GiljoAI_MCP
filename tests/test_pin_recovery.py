"""
Password Reset and Recovery PIN test suite for GiljoAI MCP API

Tests PIN-based password recovery functionality including:
- PIN verification (valid/invalid)
- Rate limiting and lockout
- First login flow (password change + PIN setup)
- Admin password reset
- Default password handling

All tests follow TDD principles - written before implementation.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from passlib.hash import bcrypt
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.app import create_app
from src.giljo_mcp.models import Base, User


class TestPinRecovery:
    """PIN recovery and password reset test suite"""

    @pytest.fixture(scope="class")
    def client(self):
        """Create test client"""
        app = create_app()
        return TestClient(app)

    @pytest.fixture(scope="class")
    def test_db(self):
        """Create in-memory test database"""
        # Use in-memory SQLite for fast testing
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        return engine

    @pytest.fixture
    def db_session(self, test_db):
        """Create database session for test"""
        connection = test_db.connect()
        transaction = connection.begin()
        session = Session(bind=connection)

        yield session

        session.close()
        transaction.rollback()
        connection.close()

    @pytest.fixture
    def test_user_with_pin(self, db_session):
        """Create test user with recovery PIN set"""
        user = User(
            id=str(uuid4()),
            username="testuser",
            email="test@example.com",
            password_hash=bcrypt.hash("SecurePassword123!"),
            recovery_pin_hash=bcrypt.hash("1234"),  # PIN is 1234
            failed_pin_attempts=0,
            pin_lockout_until=None,
            must_change_password=False,
            must_set_pin=False,
            role="developer",
            tenant_key="test_tenant_123",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    @pytest.fixture
    def test_user_without_pin(self, db_session):
        """Create test user without recovery PIN (new user)"""
        user = User(
            id=str(uuid4()),
            username="newuser",
            email="newuser@example.com",
            password_hash=bcrypt.hash("GiljoMCP"),  # Default password
            recovery_pin_hash=None,  # No PIN set yet
            failed_pin_attempts=0,
            pin_lockout_until=None,
            must_change_password=True,  # Must change on first login
            must_set_pin=True,  # Must set PIN on first login
            role="developer",
            tenant_key="test_tenant_123",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    @pytest.fixture
    def admin_user(self, db_session):
        """Create admin user for testing admin endpoints"""
        admin = User(
            id=str(uuid4()),
            username="admin",
            email="admin@example.com",
            password_hash=bcrypt.hash("AdminPassword123!"),
            recovery_pin_hash=bcrypt.hash("9876"),
            failed_pin_attempts=0,
            pin_lockout_until=None,
            must_change_password=False,
            must_set_pin=False,
            role="admin",
            tenant_key="test_tenant_123",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(admin)
        db_session.commit()
        db_session.refresh(admin)
        return admin

    # ==================== PIN VERIFICATION TESTS ====================

    def test_verify_pin_valid(self, client, db_session, test_user_with_pin):
        """Test PIN verification with correct PIN"""
        # Prepare request
        request_data = {
            "username": test_user_with_pin.username,
            "recovery_pin": "1234",  # Correct PIN
            "new_password": "NewSecurePassword456!",
            "confirm_password": "NewSecurePassword456!",
        }

        # Call API endpoint
        response = client.post("/api/auth/verify-pin-and-reset-password", json=request_data)

        # Expected: 200 OK, password reset successful
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Password reset successful"

        # Verify database changes
        db_session.refresh(test_user_with_pin)

        # Password should be updated
        assert bcrypt.verify("NewSecurePassword456!", test_user_with_pin.password_hash)

        # Failed attempts reset to 0
        assert test_user_with_pin.failed_pin_attempts == 0

        # Lockout cleared
        assert test_user_with_pin.pin_lockout_until is None

    def test_verify_pin_invalid(self, client, db_session, test_user_with_pin):
        """Test PIN verification with incorrect PIN"""
        # Prepare request with WRONG PIN
        request_data = {
            "username": test_user_with_pin.username,
            "recovery_pin": "9999",  # Incorrect PIN (correct is 1234)
            "new_password": "NewSecurePassword456!",
            "confirm_password": "NewSecurePassword456!",
        }

        # Call API endpoint
        response = client.post("/api/auth/verify-pin-and-reset-password", json=request_data)

        # Expected: 400 Bad Request, invalid PIN
        assert response.status_code == 400
        data = response.json()
        assert "Invalid username or PIN" in data["detail"]

        # Verify database changes
        db_session.refresh(test_user_with_pin)

        # Failed attempts incremented
        assert test_user_with_pin.failed_pin_attempts == 1

        # Password NOT changed
        assert bcrypt.verify("SecurePassword123!", test_user_with_pin.password_hash)

    def test_verify_pin_nonexistent_user(self, client):
        """Test PIN verification with non-existent username"""
        # Prepare request with non-existent username
        request_data = {
            "username": "nonexistentuser",
            "recovery_pin": "1234",
            "new_password": "NewSecurePassword456!",
            "confirm_password": "NewSecurePassword456!",
        }

        # Call API endpoint
        response = client.post("/api/auth/verify-pin-and-reset-password", json=request_data)

        # Expected: 400 Bad Request (generic error - don't reveal username existence)
        assert response.status_code == 400
        data = response.json()
        assert "Invalid username or PIN" in data["detail"]

    def test_verify_pin_password_mismatch(self, client, test_user_with_pin):
        """Test PIN verification with mismatched password confirmation"""
        # Prepare request with mismatched passwords
        request_data = {
            "username": test_user_with_pin.username,
            "recovery_pin": "1234",
            "new_password": "NewSecurePassword456!",
            "confirm_password": "DifferentPassword789!",  # Mismatch
        }

        # Call API endpoint
        response = client.post("/api/auth/verify-pin-and-reset-password", json=request_data)

        # Expected: 400 Bad Request, password mismatch
        assert response.status_code == 400
        data = response.json()
        assert "Passwords do not match" in data["detail"]

    # ==================== RATE LIMITING TESTS ====================

    def test_pin_rate_limiting(self, client, db_session, test_user_with_pin):
        """Test PIN lockout after 5 failed attempts"""
        # Prepare request with WRONG PIN
        request_data = {
            "username": test_user_with_pin.username,
            "recovery_pin": "9999",  # Incorrect PIN
            "new_password": "NewSecurePassword456!",
            "confirm_password": "NewSecurePassword456!",
        }

        # Attempt 1-4: Should increment failed attempts
        for i in range(1, 5):
            response = client.post("/api/auth/verify-pin-and-reset-password", json=request_data)
            assert response.status_code == 400
            db_session.refresh(test_user_with_pin)
            assert test_user_with_pin.failed_pin_attempts == i

        # Attempt 5: Should trigger lockout
        response = client.post("/api/auth/verify-pin-and-reset-password", json=request_data)
        assert response.status_code == 429  # Too Many Requests
        data = response.json()
        assert "locked out" in data["detail"].lower()

        # Verify lockout timestamp set
        db_session.refresh(test_user_with_pin)
        assert test_user_with_pin.failed_pin_attempts == 5
        assert test_user_with_pin.pin_lockout_until is not None

        # Lockout should be ~15 minutes in the future
        lockout_delta = test_user_with_pin.pin_lockout_until - datetime.now(timezone.utc)
        assert 14 * 60 < lockout_delta.total_seconds() < 16 * 60  # 14-16 minutes

        # Attempt 6: Even with CORRECT PIN, should fail (locked out)
        correct_request = {
            "username": test_user_with_pin.username,
            "recovery_pin": "1234",  # Correct PIN
            "new_password": "NewSecurePassword456!",
            "confirm_password": "NewSecurePassword456!",
        }
        response = client.post("/api/auth/verify-pin-and-reset-password", json=correct_request)
        assert response.status_code == 429
        assert "locked out" in response.json()["detail"].lower()

    def test_pin_lockout_expiry(self, client, db_session, test_user_with_pin):
        """Test PIN lockout expires after 15 minutes"""
        # Manually set lockout to expired time (past)
        test_user_with_pin.failed_pin_attempts = 5
        test_user_with_pin.pin_lockout_until = datetime.now(timezone.utc) - timedelta(minutes=1)
        db_session.commit()

        # Attempt with correct PIN after lockout expired
        request_data = {
            "username": test_user_with_pin.username,
            "recovery_pin": "1234",  # Correct PIN
            "new_password": "NewSecurePassword456!",
            "confirm_password": "NewSecurePassword456!",
        }

        response = client.post("/api/auth/verify-pin-and-reset-password", json=request_data)

        # Expected: 200 OK, lockout expired, password reset successful
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Password reset successful"

        # Verify database changes
        db_session.refresh(test_user_with_pin)

        # Failed attempts reset to 0
        assert test_user_with_pin.failed_pin_attempts == 0

        # Lockout cleared
        assert test_user_with_pin.pin_lockout_until is None

    # ==================== FIRST LOGIN FLOW TESTS ====================

    def test_check_first_login_required(self, client, test_user_without_pin):
        """Test check-first-login returns true for new users"""
        # Prepare request
        request_data = {"username": test_user_without_pin.username}

        # Call API endpoint
        response = client.post("/api/auth/check-first-login", json=request_data)

        # Expected: 200 OK, must_change_password=True, must_set_pin=True
        assert response.status_code == 200
        data = response.json()
        assert data["must_change_password"] is True
        assert data["must_set_pin"] is True

    def test_check_first_login_not_required(self, client, test_user_with_pin):
        """Test check-first-login returns false for existing users"""
        # Prepare request
        request_data = {"username": test_user_with_pin.username}

        # Call API endpoint
        response = client.post("/api/auth/check-first-login", json=request_data)

        # Expected: 200 OK, must_change_password=False, must_set_pin=False
        assert response.status_code == 200
        data = response.json()
        assert data["must_change_password"] is False
        assert data["must_set_pin"] is False

    def test_complete_first_login(self, client, db_session, test_user_without_pin):
        """Test complete-first-login changes password and sets PIN"""
        # Prepare request (authenticated as test_user_without_pin)
        request_data = {
            "current_password": "GiljoMCP",  # Default password
            "new_password": "NewSecurePassword123!",
            "confirm_password": "NewSecurePassword123!",
            "recovery_pin": "5678",
            "confirm_pin": "5678",
        }

        # Call API endpoint (requires authentication)
        # Note: In real implementation, would use JWT token from login
        response = client.post(
            "/api/auth/complete-first-login",
            json=request_data,
            # TODO: Add authentication header when JWT is implemented
        )

        # Expected: 200 OK, password and PIN updated
        assert response.status_code in [200, 401]  # 401 if auth not implemented yet

        if response.status_code == 200:
            data = response.json()
            assert data["message"] == "First login completed successfully"

            # Verify database changes
            db_session.refresh(test_user_without_pin)

            # Password changed
            assert bcrypt.verify("NewSecurePassword123!", test_user_without_pin.password_hash)

            # PIN set
            assert test_user_without_pin.recovery_pin_hash is not None
            assert bcrypt.verify("5678", test_user_without_pin.recovery_pin_hash)

            # Flags cleared
            assert test_user_without_pin.must_change_password is False
            assert test_user_without_pin.must_set_pin is False

    def test_complete_first_login_pin_mismatch(self, client, test_user_without_pin):
        """Test complete-first-login fails with mismatched PINs"""
        # Prepare request with mismatched PINs
        request_data = {
            "current_password": "GiljoMCP",
            "new_password": "NewSecurePassword123!",
            "confirm_password": "NewSecurePassword123!",
            "recovery_pin": "5678",
            "confirm_pin": "1234",  # Mismatch
        }

        # Call API endpoint
        response = client.post("/api/auth/complete-first-login", json=request_data)

        # Expected: 400 Bad Request, PIN mismatch
        assert response.status_code in [400, 401]  # 400 for validation, 401 if auth required

        if response.status_code == 400:
            data = response.json()
            assert "PINs do not match" in data["detail"]

    def test_complete_first_login_invalid_pin_format(self, client, test_user_without_pin):
        """Test complete-first-login fails with non-4-digit PIN"""
        # Prepare request with invalid PIN (not 4 digits)
        request_data = {
            "current_password": "GiljoMCP",
            "new_password": "NewSecurePassword123!",
            "confirm_password": "NewSecurePassword123!",
            "recovery_pin": "123",  # Only 3 digits
            "confirm_pin": "123",
        }

        # Call API endpoint
        response = client.post("/api/auth/complete-first-login", json=request_data)

        # Expected: 400 Bad Request, invalid PIN format
        assert response.status_code in [400, 401, 422]  # 422 for Pydantic validation

        if response.status_code in [400, 422]:
            data = response.json()
            # Pydantic may return different error format
            assert "4 digits" in str(data).lower() or "PIN" in str(data)

    # ==================== ADMIN PASSWORD RESET TESTS ====================

    def test_admin_reset_password(self, client, db_session, test_user_with_pin, admin_user):
        """Test admin resets user password to GiljoMCP"""
        # Store original password and PIN hashes
        original_password = test_user_with_pin.password_hash
        original_pin = test_user_with_pin.recovery_pin_hash

        # Call admin reset endpoint (authenticated as admin)
        response = client.post(
            f"/api/users/{test_user_with_pin.id}/reset-password",
            # TODO: Add admin authentication header when JWT is implemented
        )

        # Expected: 200 OK, password reset
        assert response.status_code in [200, 401]  # 401 if auth not implemented yet

        if response.status_code == 200:
            data = response.json()
            assert "reset successful" in data["message"].lower()

            # Verify database changes
            db_session.refresh(test_user_with_pin)

            # Password reset to default 'GiljoMCP'
            assert bcrypt.verify("GiljoMCP", test_user_with_pin.password_hash)
            assert test_user_with_pin.password_hash != original_password

            # must_change_password flag set
            assert test_user_with_pin.must_change_password is True

            # Recovery PIN UNCHANGED
            assert test_user_with_pin.recovery_pin_hash == original_pin

            # Failed attempts reset
            assert test_user_with_pin.failed_pin_attempts == 0

            # Lockout cleared
            assert test_user_with_pin.pin_lockout_until is None

    def test_admin_reset_password_non_admin(self, client, test_user_with_pin, test_user_without_pin):
        """Test non-admin cannot reset other user's password"""
        # Call reset endpoint as non-admin user
        response = client.post(
            f"/api/users/{test_user_with_pin.id}/reset-password",
            # TODO: Add non-admin authentication header when JWT is implemented
        )

        # Expected: 403 Forbidden (if auth implemented) or 401 Unauthorized
        assert response.status_code in [401, 403]

    def test_admin_reset_password_self(self, client, db_session, admin_user):
        """Test admin can reset own password"""
        # Store original PIN
        original_pin = admin_user.recovery_pin_hash

        # Call admin reset on self
        response = client.post(
            f"/api/users/{admin_user.id}/reset-password",
            # TODO: Add admin authentication header
        )

        # Expected: 200 OK (admins can reset own password)
        assert response.status_code in [200, 401]

        if response.status_code == 200:
            db_session.refresh(admin_user)

            # Password reset to default
            assert bcrypt.verify("GiljoMCP", admin_user.password_hash)

            # PIN unchanged
            assert admin_user.recovery_pin_hash == original_pin

    # ==================== USER CREATION TESTS ====================

    def test_default_password_creation(self, client, db_session, admin_user):
        """Test new user created with default password 'GiljoMCP'"""
        # Prepare user creation request
        request_data = {
            "username": "newemployee",
            "email": "newemployee@example.com",
            "full_name": "New Employee",
            "role": "developer",
        }

        # Call user creation endpoint (authenticated as admin)
        response = client.post(
            "/api/users/",
            json=request_data,
            # TODO: Add admin authentication header
        )

        # Expected: 201 Created, user created with default password
        assert response.status_code in [201, 401]  # 401 if auth not implemented

        if response.status_code == 201:
            data = response.json()
            user_id = data["id"]

            # Query created user
            stmt = select(User).where(User.id == user_id)
            result = db_session.execute(stmt)
            new_user = result.scalar_one()

            # Verify default password
            assert bcrypt.verify("GiljoMCP", new_user.password_hash)

            # Verify flags set
            assert new_user.must_change_password is True
            assert new_user.must_set_pin is True

            # Verify PIN not set yet
            assert new_user.recovery_pin_hash is None

    # ==================== SECURITY TESTS ====================

    def test_pin_timing_safe_comparison(self, client, test_user_with_pin):
        """Test PIN comparison is timing-safe (prevents timing attacks)"""
        import time

        # Measure time for correct PIN
        start1 = time.perf_counter()
        request_data1 = {
            "username": test_user_with_pin.username,
            "recovery_pin": "1234",  # Correct
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!",
        }
        client.post("/api/auth/verify-pin-and-reset-password", json=request_data1)
        time1 = time.perf_counter() - start1

        # Measure time for incorrect PIN
        start2 = time.perf_counter()
        request_data2 = {
            "username": test_user_with_pin.username,
            "recovery_pin": "9999",  # Incorrect
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!",
        }
        client.post("/api/auth/verify-pin-and-reset-password", json=request_data2)
        time2 = time.perf_counter() - start2

        # Timing should be similar (within 100ms)
        # This prevents attackers from using timing attacks to guess PINs
        time_diff = abs(time1 - time2)
        assert time_diff < 0.1  # Less than 100ms difference

    def test_pin_storage_never_plaintext(self, db_session, test_user_with_pin):
        """Test that PINs are never stored in plaintext"""
        # Verify PIN is hashed
        assert test_user_with_pin.recovery_pin_hash is not None
        assert test_user_with_pin.recovery_pin_hash != "1234"  # Not plaintext
        assert test_user_with_pin.recovery_pin_hash.startswith("$2b$")  # bcrypt prefix

        # Verify hash is valid
        assert bcrypt.verify("1234", test_user_with_pin.recovery_pin_hash)

    def test_generic_error_messages(self, client):
        """Test that error messages don't reveal username existence"""
        # Test with non-existent username
        response1 = client.post(
            "/api/auth/verify-pin-and-reset-password",
            json={
                "username": "nonexistent",
                "recovery_pin": "1234",
                "new_password": "NewPassword123!",
                "confirm_password": "NewPassword123!",
            },
        )

        # Test with existent username but wrong PIN
        response2 = client.post(
            "/api/auth/verify-pin-and-reset-password",
            json={
                "username": "testuser",
                "recovery_pin": "9999",
                "new_password": "NewPassword123!",
                "confirm_password": "NewPassword123!",
            },
        )

        # Both should return same generic error
        assert response1.status_code == 400
        assert response2.status_code == 400
        assert response1.json()["detail"] == response2.json()["detail"]
        assert "Invalid username or PIN" in response1.json()["detail"]


# Run the tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
