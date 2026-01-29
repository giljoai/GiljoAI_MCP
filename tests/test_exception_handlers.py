"""
Comprehensive Tests for Exception Framework Foundation - Handover 0480a Task 5

Tests cover:
1. BaseGiljoException base class behavior
2. HTTP status code mapping across exception hierarchy
3. Exception handler integration with FastAPI
4. Legacy HTTPException compatibility

Test Structure:
- TestBaseGiljoException: Core exception class behavior
- TestHTTPStatusCodeMapping: Verify status code assignments
- TestExceptionHandlerIntegration: FastAPI handler integration tests
- TestLegacyHTTPExceptionCompatibility: Backward compatibility tests

Created as part of Handover 0480a: Exception Hierarchy Foundation
"""

import pytest
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient


# ============================================================================
# TEST CLASS 1: BaseGiljoException Core Behavior
# ============================================================================

class TestBaseGiljoException:
    """Tests for BaseGiljoException base class."""

    def test_default_error_code_from_class_name(self):
        """Error code should default to uppercase class name."""
        from src.giljo_mcp.exceptions import BaseGiljoException

        exc = BaseGiljoException("test message")
        assert exc.error_code == "BASEGILJOEXCEPTION"

    def test_custom_error_code(self):
        """Custom error code should override default."""
        from src.giljo_mcp.exceptions import BaseGiljoException

        exc = BaseGiljoException("test", error_code="CUSTOM_CODE")
        assert exc.error_code == "CUSTOM_CODE"

    def test_to_dict_contains_all_fields(self):
        """to_dict() should include all required fields."""
        from src.giljo_mcp.exceptions import BaseGiljoException

        exc = BaseGiljoException("test message", context={"key": "value"})
        result = exc.to_dict()

        assert "error_code" in result
        assert "message" in result
        assert "context" in result
        assert "timestamp" in result
        assert "status_code" in result

        assert result["message"] == "test message"
        assert result["context"] == {"key": "value"}
        assert result["status_code"] == 500  # default

    def test_timestamp_is_utc(self):
        """Timestamp should be in UTC."""
        from src.giljo_mcp.exceptions import BaseGiljoException

        exc = BaseGiljoException("test")
        # Timestamp should be close to now
        now = datetime.now(timezone.utc)
        assert abs((now - exc.timestamp).total_seconds()) < 1

    def test_default_status_code(self):
        """Base exception should have status code 500."""
        from src.giljo_mcp.exceptions import BaseGiljoException

        assert BaseGiljoException.default_status_code == 500

    def test_message_attribute(self):
        """Exception should store message attribute."""
        from src.giljo_mcp.exceptions import BaseGiljoException

        exc = BaseGiljoException("test message")
        assert exc.message == "test message"

    def test_context_defaults_to_empty_dict(self):
        """Context should default to empty dict when not provided."""
        from src.giljo_mcp.exceptions import BaseGiljoException

        exc = BaseGiljoException("test")
        assert exc.context == {}

    def test_str_representation_with_context(self):
        """String representation should include context when present."""
        from src.giljo_mcp.exceptions import BaseGiljoException

        exc = BaseGiljoException("test message", context={"field": "email"})
        str_repr = str(exc)
        assert "test message" in str_repr
        assert "field" in str_repr or "email" in str_repr

    def test_str_representation_without_context(self):
        """String representation should be message only when no context."""
        from src.giljo_mcp.exceptions import BaseGiljoException

        exc = BaseGiljoException("test message")
        assert str(exc) == "test message"


# ============================================================================
# TEST CLASS 2: HTTP Status Code Mapping
# ============================================================================

class TestHTTPStatusCodeMapping:
    """Tests for HTTP status code mapping on exception classes."""

    def test_validation_error_is_400(self):
        """ValidationError should have status code 400."""
        from src.giljo_mcp.exceptions import ValidationError

        assert ValidationError.default_status_code == 400

    def test_resource_not_found_is_404(self):
        """ResourceNotFoundError should have status code 404."""
        from src.giljo_mcp.exceptions import ResourceNotFoundError

        assert ResourceNotFoundError.default_status_code == 404

    def test_template_not_found_is_404(self):
        """TemplateNotFoundError should have status code 404."""
        from src.giljo_mcp.exceptions import TemplateNotFoundError

        assert TemplateNotFoundError.default_status_code == 404

    def test_authentication_error_is_401(self):
        """AuthenticationError should have status code 401."""
        from src.giljo_mcp.exceptions import AuthenticationError

        assert AuthenticationError.default_status_code == 401

    def test_authorization_error_is_403(self):
        """AuthorizationError should have status code 403."""
        from src.giljo_mcp.exceptions import AuthorizationError

        assert AuthorizationError.default_status_code == 403

    def test_database_error_is_500(self):
        """DatabaseError should have status code 500."""
        from src.giljo_mcp.exceptions import DatabaseError

        assert DatabaseError.default_status_code == 500

    def test_rate_limit_error_is_429(self):
        """RateLimitError should have status code 429."""
        from src.giljo_mcp.exceptions import RateLimitError

        assert RateLimitError.default_status_code == 429

    def test_base_exception_is_500(self):
        """BaseGiljoException should have status code 500."""
        from src.giljo_mcp.exceptions import BaseGiljoException

        assert BaseGiljoException.default_status_code == 500

    def test_exception_instance_inherits_status_code(self):
        """Exception instances should inherit class default_status_code."""
        from src.giljo_mcp.exceptions import ValidationError

        exc = ValidationError("test")
        # The instance should have access to the class attribute
        assert exc.default_status_code == 400


# ============================================================================
# TEST CLASS 3: Exception Handler Integration
# ============================================================================

class TestExceptionHandlerIntegration:
    """Integration tests for global exception handlers."""

    @pytest.fixture
    def app(self):
        """Create test app with exception handlers."""
        from src.giljo_mcp.exceptions import (
            ValidationError,
            ResourceNotFoundError,
            AuthenticationError,
        )
        # Import handler registration - this will be created by system-architect
        try:
            from api.exception_handlers import register_exception_handlers
        except ImportError:
            # If exception_handlers.py doesn't exist yet, skip these tests
            pytest.skip("api.exception_handlers not implemented yet")

        app = FastAPI()
        register_exception_handlers(app)

        @app.get("/raise-validation")
        async def raise_validation():
            raise ValidationError("Invalid input", context={"field": "email"})

        @app.get("/raise-not-found")
        async def raise_not_found():
            raise ResourceNotFoundError("Resource not found", context={"id": "123"})

        @app.get("/raise-auth")
        async def raise_auth():
            raise AuthenticationError("Invalid credentials")

        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_validation_error_returns_400(self, client):
        """ValidationError should return 400 with proper structure."""
        response = client.get("/raise-validation")
        assert response.status_code == 400
        data = response.json()
        assert data["error_code"] == "VALIDATIONERROR"
        assert data["message"] == "Invalid input"
        assert data["context"]["field"] == "email"
        assert "timestamp" in data

    def test_not_found_error_returns_404(self, client):
        """ResourceNotFoundError should return 404 with proper structure."""
        response = client.get("/raise-not-found")
        assert response.status_code == 404
        data = response.json()
        assert data["error_code"] == "RESOURCENOTFOUNDERROR"
        assert data["message"] == "Resource not found"
        assert data["context"]["id"] == "123"
        assert "timestamp" in data

    def test_auth_error_returns_401(self, client):
        """AuthenticationError should return 401 with proper structure."""
        response = client.get("/raise-auth")
        assert response.status_code == 401
        data = response.json()
        assert data["error_code"] == "AUTHENTICATIONERROR"
        assert data["message"] == "Invalid credentials"
        assert "timestamp" in data

    def test_response_has_json_content_type(self, client):
        """Error responses should have JSON content type."""
        response = client.get("/raise-validation")
        assert "application/json" in response.headers.get("content-type", "")

    def test_multiple_exceptions_have_consistent_structure(self, client):
        """All exception responses should have consistent structure."""
        validation_response = client.get("/raise-validation")
        not_found_response = client.get("/raise-not-found")
        auth_response = client.get("/raise-auth")

        # All should have same keys
        validation_keys = set(validation_response.json().keys())
        not_found_keys = set(not_found_response.json().keys())
        auth_keys = set(auth_response.json().keys())

        assert validation_keys == not_found_keys == auth_keys

        # All should have required keys
        required_keys = {"error_code", "message", "context", "timestamp", "status_code"}
        assert required_keys.issubset(validation_keys)


# ============================================================================
# TEST CLASS 4: Legacy HTTPException Compatibility
# ============================================================================

class TestLegacyHTTPExceptionCompatibility:
    """Tests for backward compatibility with HTTPException."""

    @pytest.fixture
    def app(self):
        """Create test app with exception handlers."""
        try:
            from api.exception_handlers import register_exception_handlers
        except ImportError:
            pytest.skip("api.exception_handlers not implemented yet")

        app = FastAPI()
        register_exception_handlers(app)

        @app.get("/raise-http")
        async def raise_http():
            raise HTTPException(status_code=403, detail="Forbidden")

        @app.get("/raise-http-404")
        async def raise_http_404():
            raise HTTPException(status_code=404, detail="Not found")

        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_http_exception_still_works(self, client):
        """HTTPException should still work with handlers registered."""
        response = client.get("/raise-http")
        assert response.status_code == 403
        data = response.json()
        assert data["error_code"] == "HTTP_ERROR"
        assert data["message"] == "Forbidden"
        assert "timestamp" in data

    def test_http_exception_404(self, client):
        """HTTPException with 404 should return proper structure."""
        response = client.get("/raise-http-404")
        assert response.status_code == 404
        data = response.json()
        assert data["error_code"] == "HTTP_ERROR"
        assert data["message"] == "Not found"

    def test_http_exception_has_consistent_structure(self, client):
        """HTTPException responses should match GiljoException structure."""
        response = client.get("/raise-http")
        data = response.json()

        required_keys = {"error_code", "message", "timestamp"}
        assert required_keys.issubset(set(data.keys()))

    def test_http_exception_status_code_preserved(self, client):
        """HTTPException status code should be preserved in response."""
        response = client.get("/raise-http")
        assert response.status_code == 403
        data = response.json()
        # Status code is in HTTP response, not necessarily in body
        assert "error_code" in data
        assert "message" in data
        assert "timestamp" in data


# ============================================================================
# TEST CLASS 5: Exception Context Handling
# ============================================================================

class TestExceptionContextHandling:
    """Tests for exception context handling."""

    def test_context_can_contain_complex_data(self):
        """Exception context should handle complex nested data."""
        from src.giljo_mcp.exceptions import ValidationError

        context = {
            "field": "email",
            "value": "invalid@",
            "constraints": {
                "min_length": 5,
                "max_length": 100,
                "pattern": r"^[\w\.-]+@[\w\.-]+\.\w+$"
            },
            "errors": ["Invalid format", "Missing domain"]
        }

        exc = ValidationError("Validation failed", context=context)
        result = exc.to_dict()

        assert result["context"]["field"] == "email"
        assert result["context"]["constraints"]["min_length"] == 5
        assert len(result["context"]["errors"]) == 2

    def test_context_can_be_updated_after_creation(self):
        """Exception context should be mutable."""
        from src.giljo_mcp.exceptions import BaseGiljoException

        exc = BaseGiljoException("test", context={"key1": "value1"})
        exc.context["key2"] = "value2"

        result = exc.to_dict()
        assert result["context"]["key1"] == "value1"
        assert result["context"]["key2"] == "value2"

    def test_empty_context_in_to_dict(self):
        """Empty context should be included in to_dict() output."""
        from src.giljo_mcp.exceptions import BaseGiljoException

        exc = BaseGiljoException("test")
        result = exc.to_dict()

        assert "context" in result
        assert result["context"] == {}


# ============================================================================
# TEST CLASS 6: Exception Inheritance Behavior
# ============================================================================

class TestExceptionInheritanceBehavior:
    """Tests for exception class inheritance."""

    def test_validation_error_is_base_exception(self):
        """ValidationError should be instance of BaseGiljoException."""
        from src.giljo_mcp.exceptions import ValidationError, BaseGiljoException

        exc = ValidationError("test")
        assert isinstance(exc, BaseGiljoException)

    def test_resource_not_found_is_base_exception(self):
        """ResourceNotFoundError should be instance of BaseGiljoException."""
        from src.giljo_mcp.exceptions import ResourceNotFoundError, BaseGiljoException

        exc = ResourceNotFoundError("test")
        assert isinstance(exc, BaseGiljoException)

    def test_all_exceptions_are_python_exceptions(self):
        """All custom exceptions should be Python exceptions."""
        from src.giljo_mcp.exceptions import (
            BaseGiljoException,
            ValidationError,
            ResourceNotFoundError,
            DatabaseError,
        )

        assert issubclass(BaseGiljoException, Exception)
        assert issubclass(ValidationError, Exception)
        assert issubclass(ResourceNotFoundError, Exception)
        assert issubclass(DatabaseError, Exception)

    def test_exception_can_be_caught_as_base_type(self):
        """Specific exceptions should be catchable as BaseGiljoException."""
        from src.giljo_mcp.exceptions import ValidationError, BaseGiljoException

        try:
            raise ValidationError("test")
        except BaseGiljoException as e:
            assert e.message == "test"
        else:
            pytest.fail("Exception was not caught")


# ============================================================================
# INTEGRATION TESTS: Real-World Scenarios
# ============================================================================

class TestRealWorldScenarios:
    """Integration tests simulating real-world exception scenarios."""

    @pytest.fixture
    def app_with_realistic_endpoints(self):
        """Create app with realistic endpoints."""
        from src.giljo_mcp.exceptions import (
            ValidationError,
            ResourceNotFoundError,
            DatabaseError,
        )

        try:
            from api.exception_handlers import register_exception_handlers
        except ImportError:
            pytest.skip("api.exception_handlers not implemented yet")

        app = FastAPI()
        register_exception_handlers(app)

        @app.post("/api/users")
        async def create_user(email: str):
            if "@" not in email:
                raise ValidationError(
                    "Invalid email format",
                    context={"field": "email", "value": email}
                )
            return {"id": "123", "email": email}

        @app.get("/api/users/{user_id}")
        async def get_user(user_id: str):
            if user_id == "999":
                raise ResourceNotFoundError(
                    "User not found",
                    context={"user_id": user_id}
                )
            return {"id": user_id, "name": "Test User"}

        @app.get("/api/health/db")
        async def check_database():
            # Simulate database connection failure
            raise DatabaseError(
                "Database connection failed",
                context={"host": "localhost", "port": 5432}
            )

        return app

    @pytest.fixture
    def client(self, app_with_realistic_endpoints):
        """Create test client."""
        return TestClient(app_with_realistic_endpoints)

    def test_user_creation_validation_error(self, client):
        """Invalid user data should return 400 with context."""
        response = client.post("/api/users?email=invalid")
        assert response.status_code == 400
        data = response.json()
        assert data["error_code"] == "VALIDATIONERROR"
        assert "email" in data["context"]["field"]

    def test_user_not_found_error(self, client):
        """Non-existent user should return 404 with context."""
        response = client.get("/api/users/999")
        assert response.status_code == 404
        data = response.json()
        assert data["error_code"] == "RESOURCENOTFOUNDERROR"
        assert data["context"]["user_id"] == "999"

    def test_database_connection_error(self, client):
        """Database errors should return 500 with context."""
        response = client.get("/api/health/db")
        assert response.status_code == 500
        data = response.json()
        assert data["error_code"] == "DATABASEERROR"
        assert "host" in data["context"]
        assert "port" in data["context"]


# ============================================================================
# TEST CLASS 7: AuthService Exception Migration Tests (Handover 0480b)
# ============================================================================

class TestAuthServiceExceptionMigration:
    """
    Tests for AuthService migration to exception-based error handling.

    Part of Handover 0480b - Exception Handling Remediation.
    Verifies that auth_service.py raises proper exceptions instead of returning error dicts.

    Test Coverage:
    - AuthenticationError for invalid credentials
    - ResourceNotFoundError for missing users/API keys
    - AuthorizationError for inactive accounts
    - ValidationError for duplicate usernames/emails, weak passwords
    """

    @pytest.fixture
    async def auth_service(self, db_manager, db_session):
        """Create AuthService instance for testing"""
        from src.giljo_mcp.services.auth_service import AuthService
        return AuthService(
            db_manager=db_manager,
            websocket_manager=None,
            session=db_session
        )

    @pytest.fixture
    async def test_user(self, db_session):
        """Create test user with known credentials"""
        from src.giljo_mcp.models.auth import User
        from passlib.hash import bcrypt

        password = "Test1234!"
        user = User(
            id="test-user-001",
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            password_hash=bcrypt.hash(password),
            role="developer",
            tenant_key="test_tenant_001",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user, password

    @pytest.fixture
    async def test_inactive_user(self, db_session):
        """Create inactive test user"""
        from src.giljo_mcp.models.auth import User
        from passlib.hash import bcrypt

        password = "Inactive1234!"
        user = User(
            id="test-user-inactive",
            username="inactiveuser",
            email="inactive@example.com",
            password_hash=bcrypt.hash(password),
            role="developer",
            tenant_key="test_tenant_002",
            is_active=False,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user, password

    @pytest.fixture
    async def existing_user(self, db_session):
        """Create user for duplicate testing"""
        from src.giljo_mcp.models.auth import User
        from passlib.hash import bcrypt

        user = User(
            id="existing-user-001",
            username="existinguser",
            email="existing@example.com",
            password_hash=bcrypt.hash("Existing1234!"),
            role="developer",
            tenant_key="test_tenant_003",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    # Tests for authenticate_user

    @pytest.mark.asyncio
    async def test_authenticate_nonexistent_user_raises_authentication_error(self, auth_service):
        """Test that authenticating non-existent user raises AuthenticationError"""
        from src.giljo_mcp.exceptions import AuthenticationError

        with pytest.raises(AuthenticationError) as exc_info:
            await auth_service.authenticate_user("nonexistent", "password")

        assert "invalid credentials" in exc_info.value.message.lower()
        assert exc_info.value.default_status_code == 401

    @pytest.mark.asyncio
    async def test_authenticate_wrong_password_raises_authentication_error(self, auth_service, test_user):
        """Test that wrong password raises AuthenticationError"""
        from src.giljo_mcp.exceptions import AuthenticationError

        user, _ = test_user

        with pytest.raises(AuthenticationError) as exc_info:
            await auth_service.authenticate_user(user.username, "wrongpassword")

        assert "invalid credentials" in exc_info.value.message.lower()
        assert exc_info.value.default_status_code == 401

    @pytest.mark.asyncio
    async def test_authenticate_inactive_user_raises_authorization_error(self, auth_service, test_inactive_user):
        """Test that authenticating inactive user raises AuthorizationError"""
        from src.giljo_mcp.exceptions import AuthorizationError

        user, password = test_inactive_user

        with pytest.raises(AuthorizationError) as exc_info:
            await auth_service.authenticate_user(user.username, password)

        assert "inactive" in exc_info.value.message.lower()
        assert exc_info.value.default_status_code == 403

    # Tests for update_last_login

    @pytest.mark.asyncio
    async def test_update_last_login_nonexistent_user_raises_not_found(self, auth_service):
        """Test that updating last login for non-existent user raises ResourceNotFoundError"""
        from src.giljo_mcp.exceptions import ResourceNotFoundError

        with pytest.raises(ResourceNotFoundError) as exc_info:
            await auth_service.update_last_login("nonexistent-id", datetime.now(timezone.utc))

        assert "not found" in exc_info.value.message.lower()
        assert exc_info.value.default_status_code == 404

    # Tests for revoke_api_key

    @pytest.mark.asyncio
    async def test_revoke_nonexistent_api_key_raises_not_found(self, auth_service, test_user):
        """Test that revoking non-existent API key raises ResourceNotFoundError"""
        from src.giljo_mcp.exceptions import ResourceNotFoundError

        user, _ = test_user

        with pytest.raises(ResourceNotFoundError) as exc_info:
            await auth_service.revoke_api_key("nonexistent-key-id", user.id)

        assert "not found" in exc_info.value.message.lower()
        assert exc_info.value.default_status_code == 404

    # Tests for register_user

    @pytest.mark.asyncio
    async def test_register_duplicate_username_raises_validation_error(self, auth_service, existing_user):
        """Test that registering duplicate username raises ValidationError"""
        from src.giljo_mcp.exceptions import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            await auth_service.register_user(
                username=existing_user.username,  # Duplicate!
                email="newemail@example.com",
                password="NewPassword1234!",
                role="developer",
                requesting_admin_id="admin-001"
            )

        assert "already exists" in exc_info.value.message.lower()
        assert "username" in exc_info.value.message.lower()
        assert exc_info.value.default_status_code == 400

    @pytest.mark.asyncio
    async def test_register_duplicate_email_raises_validation_error(self, auth_service, existing_user):
        """Test that registering duplicate email raises ValidationError"""
        from src.giljo_mcp.exceptions import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            await auth_service.register_user(
                username="newusername",
                email=existing_user.email,  # Duplicate!
                password="NewPassword1234!",
                role="developer",
                requesting_admin_id="admin-001"
            )

        assert "already exists" in exc_info.value.message.lower()
        assert "email" in exc_info.value.message.lower()
        assert exc_info.value.default_status_code == 400

    # Tests for create_first_admin

    @pytest.mark.asyncio
    async def test_create_first_admin_when_users_exist_raises_validation_error(self, auth_service, existing_user):
        """Test that creating first admin when users exist raises ValidationError"""
        from src.giljo_mcp.exceptions import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            await auth_service.create_first_admin(
                username="admin",
                email="admin@example.com",
                password="AdminPassword123!",
                full_name="Administrator"
            )

        assert "already exists" in exc_info.value.message.lower()
        assert "administrator" in exc_info.value.message.lower()
        assert exc_info.value.default_status_code == 400

    @pytest.mark.asyncio
    async def test_create_first_admin_weak_password_raises_validation_error(self, db_manager):
        """Test that creating first admin with weak password raises ValidationError

        NOTE: This test may be skipped if there are already users in the database.
        The "admin already exists" check runs before password validation.
        """
        from src.giljo_mcp.exceptions import ValidationError
        from src.giljo_mcp.services.auth_service import AuthService
        from sqlalchemy import select, func
        from src.giljo_mcp.models.auth import User

        # Check if users exist (to explain skip)
        async with db_manager.get_session_async() as session:
            user_count_stmt = select(func.count(User.id))
            result = await session.execute(user_count_stmt)
            total_users = result.scalar()

        if total_users > 0:
            pytest.skip("Database already has users - cannot test first admin password validation")

        # Create a fresh auth service
        auth_service_isolated = AuthService(db_manager=db_manager)

        with pytest.raises(ValidationError) as exc_info:
            await auth_service_isolated.create_first_admin(
                username="admin",
                email="admin@example.com",
                password="short",  # Too short!
                full_name="Administrator"
            )

        assert "password" in exc_info.value.message.lower()
        assert "12 characters" in exc_info.value.message.lower()
        assert exc_info.value.default_status_code == 400

    @pytest.mark.asyncio
    async def test_create_first_admin_password_no_complexity_raises_validation_error(self, db_manager):
        """Test that creating first admin without password complexity raises ValidationError

        NOTE: This test may be skipped if there are already users in the database.
        The "admin already exists" check runs before password validation.
        """
        from src.giljo_mcp.exceptions import ValidationError
        from src.giljo_mcp.services.auth_service import AuthService
        from sqlalchemy import select, func
        from src.giljo_mcp.models.auth import User

        # Check if users exist (to explain skip)
        async with db_manager.get_session_async() as session:
            user_count_stmt = select(func.count(User.id))
            result = await session.execute(user_count_stmt)
            total_users = result.scalar()

        if total_users > 0:
            pytest.skip("Database already has users - cannot test first admin password validation")

        # Create a fresh auth service
        auth_service_isolated = AuthService(db_manager=db_manager)

        with pytest.raises(ValidationError) as exc_info:
            await auth_service_isolated.create_first_admin(
                username="admin",
                email="admin@example.com",
                password="alllowercase12",  # No uppercase, no special!
                full_name="Administrator"
            )

        assert "password" in exc_info.value.message.lower()
        assert exc_info.value.default_status_code == 400
