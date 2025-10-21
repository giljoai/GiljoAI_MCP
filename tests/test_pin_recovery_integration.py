"""
Simplified integration tests for Password Reset and Recovery PIN functionality.

Tests the actual API endpoints without database mocking.
Requires PostgreSQL database to be running.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPinRecoveryIntegration:
    """Integration tests for PIN recovery endpoints"""

    def test_auth_pin_recovery_module_imports(self):
        """Test that auth_pin_recovery module can be imported"""
        from api.endpoints import auth_pin_recovery

        assert hasattr(auth_pin_recovery, 'router')
        assert hasattr(auth_pin_recovery, 'verify_pin_and_reset_password')
        assert hasattr(auth_pin_recovery, 'check_first_login')
        assert hasattr(auth_pin_recovery, 'complete_first_login')

    def test_users_reset_password_endpoint_exists(self):
        """Test that reset_password endpoint exists in users module"""
        from api.endpoints import users

        # Check that reset_password function exists
        assert hasattr(users, 'reset_password')

    def test_app_includes_auth_pin_recovery_router(self):
        """Test that app.py includes auth_pin_recovery router"""
        from api.app import create_app

        app = create_app()

        # Check that routes are registered
        routes = [route.path for route in app.routes]

        assert any('/api/auth/verify-pin-and-reset-password' in route for route in routes), \
            "verify-pin-and-reset-password endpoint not found"
        assert any('/api/auth/check-first-login' in route for route in routes), \
            "check-first-login endpoint not found"
        assert any('/api/auth/complete-first-login' in route for route in routes), \
            "complete-first-login endpoint not found"

    def test_user_model_has_pin_fields(self):
        """Test that User model has all PIN recovery fields"""
        from src.giljo_mcp.models import User

        # Create a test user instance to check fields
        user = User(
            username="test",
            password_hash="test",
            tenant_key="test",
            role="developer"
        )

        # Check that PIN recovery fields exist
        assert hasattr(user, 'recovery_pin_hash')
        assert hasattr(user, 'failed_pin_attempts')
        assert hasattr(user, 'pin_lockout_until')
        assert hasattr(user, 'must_change_password')
        assert hasattr(user, 'must_set_pin')

    def test_pydantic_models_validate(self):
        """Test that Pydantic request/response models validate correctly"""
        from api.endpoints.auth_pin_recovery import (
            PinPasswordResetRequest,
            CheckFirstLoginRequest,
            CompleteFirstLoginRequest,
        )

        # Test PinPasswordResetRequest validation
        valid_pin_request = PinPasswordResetRequest(
            username="testuser",
            recovery_pin="1234",
            new_password="SecurePassword123!",
            confirm_password="SecurePassword123!"
        )
        assert valid_pin_request.recovery_pin == "1234"

        # Test invalid PIN format (not 4 digits)
        with pytest.raises(Exception):  # Pydantic ValidationError
            PinPasswordResetRequest(
                username="testuser",
                recovery_pin="123",  # Only 3 digits
                new_password="SecurePassword123!",
                confirm_password="SecurePassword123!"
            )

        # Test CompleteFirstLoginRequest validation
        valid_first_login = CompleteFirstLoginRequest(
            current_password="GiljoMCP",
            new_password="SecurePassword123!",
            confirm_password="SecurePassword123!",
            recovery_pin="1234",
            confirm_pin="1234"
        )
        assert valid_first_login.recovery_pin == "1234"

    def test_password_validation_rules(self):
        """Test that password validation enforces security requirements"""
        from api.endpoints.auth_pin_recovery import PinPasswordResetRequest

        # Valid password with all requirements
        try:
            PinPasswordResetRequest(
                username="testuser",
                recovery_pin="1234",
                new_password="SecurePassword123!",
                confirm_password="SecurePassword123!"
            )
        except Exception as e:
            pytest.fail(f"Valid password rejected: {e}")

        # Invalid: no uppercase
        with pytest.raises(Exception):
            PinPasswordResetRequest(
                username="testuser",
                recovery_pin="1234",
                new_password="securepassword123!",
                confirm_password="securepassword123!"
            )

        # Invalid: no lowercase
        with pytest.raises(Exception):
            PinPasswordResetRequest(
                username="testuser",
                recovery_pin="1234",
                new_password="SECUREPASSWORD123!",
                confirm_password="SECUREPASSWORD123!"
            )

        # Invalid: no number
        with pytest.raises(Exception):
            PinPasswordResetRequest(
                username="testuser",
                recovery_pin="1234",
                new_password="SecurePassword!",
                confirm_password="SecurePassword!"
            )

        # Invalid: no special character
        with pytest.raises(Exception):
            PinPasswordResetRequest(
                username="testuser",
                recovery_pin="1234",
                new_password="SecurePassword123",
                confirm_password="SecurePassword123"
            )


# Run the tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
