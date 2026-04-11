# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Integration tests for OAuthService.

Tests OAuth 2.1 Authorization Code flow with PKCE:
- Authorization code generation and storage
- Code exchange for JWT tokens
- PKCE challenge/verifier validation
- Request validation (client_id, redirect_uri, etc.)
- Expired and used code rejection
- Cleanup of expired codes

These tests require a database session (PostgreSQL via test fixtures).
"""

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select

from src.giljo_mcp.models.auth import User
from src.giljo_mcp.models.oauth import OAuthAuthorizationCode
from src.giljo_mcp.services.oauth_service import OAuthService


def _generate_pkce_pair() -> tuple[str, str]:
    """Generate a valid PKCE code_verifier and code_challenge pair.

    Returns:
        Tuple of (code_verifier, code_challenge) where the challenge
        is the base64url-encoded SHA256 hash of the verifier.
    """
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session, test_tenant_key) -> User:
    """Create a test user for OAuth tests."""
    user = User(
        id=str(uuid4()),
        username=f"oauth_test_user_{uuid4().hex[:8]}",
        email=f"oauth_test_{uuid4().hex[:8]}@example.com",
        role="developer",
        tenant_key=test_tenant_key,
        is_active=True,
        is_system_user=False,
        must_change_password=False,
        must_set_pin=False,
        failed_pin_attempts=0,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture(scope="function")
async def oauth_service(db_session) -> OAuthService:
    """Create an OAuthService instance for testing."""
    return OAuthService(db_session=db_session)


class TestValidateAuthorizeRequest:
    """Tests for validate_authorize_request validation logic."""

    def test_valid_request_passes(self, oauth_service):
        """A fully valid authorize request should not raise."""
        _verifier, challenge = _generate_pkce_pair()
        oauth_service.validate_authorize_request(
            client_id="giljo-mcp-default",
            redirect_uri="http://localhost:3000/callback",
            code_challenge=challenge,
            code_challenge_method="S256",
            response_type="code",
            scope="mcp",
        )

    def test_invalid_client_id_rejected(self, oauth_service):
        """An unknown client_id must be rejected."""
        _verifier, challenge = _generate_pkce_pair()
        with pytest.raises(ValueError, match="client_id"):
            oauth_service.validate_authorize_request(
                client_id="unknown-client",
                redirect_uri="http://localhost:3000/callback",
                code_challenge=challenge,
                code_challenge_method="S256",
                response_type="code",
                scope="mcp",
            )

    def test_invalid_response_type_rejected(self, oauth_service):
        """Only response_type='code' is allowed."""
        _verifier, challenge = _generate_pkce_pair()
        with pytest.raises(ValueError, match="response_type"):
            oauth_service.validate_authorize_request(
                client_id="giljo-mcp-default",
                redirect_uri="http://localhost:3000/callback",
                code_challenge=challenge,
                code_challenge_method="S256",
                response_type="token",
                scope="mcp",
            )

    def test_invalid_challenge_method_rejected(self, oauth_service):
        """Only code_challenge_method='S256' is allowed."""
        _verifier, challenge = _generate_pkce_pair()
        with pytest.raises(ValueError, match="code_challenge_method"):
            oauth_service.validate_authorize_request(
                client_id="giljo-mcp-default",
                redirect_uri="http://localhost:3000/callback",
                code_challenge=challenge,
                code_challenge_method="plain",
                response_type="code",
                scope="mcp",
            )

    def test_empty_code_challenge_rejected(self, oauth_service):
        """An empty code_challenge must be rejected."""
        with pytest.raises(ValueError, match="code_challenge"):
            oauth_service.validate_authorize_request(
                client_id="giljo-mcp-default",
                redirect_uri="http://localhost:3000/callback",
                code_challenge="",
                code_challenge_method="S256",
                response_type="code",
                scope="mcp",
            )

    def test_disallowed_redirect_uri_rejected(self, oauth_service):
        """A redirect_uri not matching allowed patterns must be rejected."""
        _verifier, challenge = _generate_pkce_pair()
        with pytest.raises(ValueError, match="redirect_uri"):
            oauth_service.validate_authorize_request(
                client_id="giljo-mcp-default",
                redirect_uri="https://evil.example.com/callback",
                code_challenge=challenge,
                code_challenge_method="S256",
                response_type="code",
                scope="mcp",
            )


class TestValidateRedirectUri:
    """Tests for the static validate_redirect_uri method."""

    @pytest.mark.parametrize(
        "uri",
        [
            "http://localhost/callback",
            "http://localhost:3000/callback",
            "http://localhost:8080/auth/callback",
            "http://127.0.0.1/callback",
            "http://127.0.0.1:5173/callback",
            "http://[::1]/callback",
            "http://[::1]:3000/callback",
        ],
    )
    def test_allowed_uris_accepted(self, uri):
        assert OAuthService.validate_redirect_uri(uri) is True

    @pytest.mark.parametrize(
        "uri",
        [
            "https://evil.example.com/callback",
            "http://192.168.1.100/callback",
            "http://10.0.0.1:8080/callback",
            "ftp://localhost/callback",
            "",
        ],
    )
    def test_disallowed_uris_rejected(self, uri):
        assert OAuthService.validate_redirect_uri(uri) is False


class TestVerifyPkce:
    """Tests for the static PKCE verification method."""

    def test_pkce_valid_verifier_accepted(self):
        """A correct code_verifier must pass PKCE verification."""
        verifier, challenge = _generate_pkce_pair()
        assert OAuthService.verify_pkce(verifier, challenge) is True

    def test_pkce_invalid_verifier_rejected(self):
        """An incorrect code_verifier must fail PKCE verification."""
        _verifier, challenge = _generate_pkce_pair()
        wrong_verifier = secrets.token_urlsafe(64)
        assert OAuthService.verify_pkce(wrong_verifier, challenge) is False

    def test_pkce_empty_verifier_rejected(self):
        """An empty verifier must fail."""
        _verifier, challenge = _generate_pkce_pair()
        assert OAuthService.verify_pkce("", challenge) is False


@pytest.mark.asyncio
class TestGenerateAuthorizationCode:
    """Tests for generate_authorization_code."""

    async def test_generate_code_stores_in_db(self, oauth_service, test_user, test_tenant_key, db_session):
        """Generating a code must persist it in the database."""
        _verifier, challenge = _generate_pkce_pair()
        code = await oauth_service.generate_authorization_code(
            user_id=test_user.id,
            tenant_key=test_tenant_key,
            client_id="giljo-mcp-default",
            redirect_uri="http://localhost:3000/callback",
            code_challenge=challenge,
            scope="mcp",
        )

        assert isinstance(code, str)
        assert len(code) > 32

        result = await db_session.execute(select(OAuthAuthorizationCode).where(OAuthAuthorizationCode.code == code))
        stored = result.scalar_one()
        assert stored.user_id == test_user.id
        assert stored.tenant_key == test_tenant_key
        assert stored.client_id == "giljo-mcp-default"
        assert stored.redirect_uri == "http://localhost:3000/callback"
        assert stored.code_challenge == challenge
        assert stored.code_challenge_method == "S256"
        assert stored.scope == "mcp"
        assert stored.used is False
        assert stored.expires_at > datetime.now(timezone.utc)

    async def test_generate_code_sets_expiry(self, oauth_service, test_user, test_tenant_key, db_session):
        """The code expiry must be approximately 10 minutes in the future."""
        _verifier, challenge = _generate_pkce_pair()
        before = datetime.now(timezone.utc)
        code = await oauth_service.generate_authorization_code(
            user_id=test_user.id,
            tenant_key=test_tenant_key,
            client_id="giljo-mcp-default",
            redirect_uri="http://localhost:3000/callback",
            code_challenge=challenge,
        )
        after = datetime.now(timezone.utc)

        result = await db_session.execute(select(OAuthAuthorizationCode).where(OAuthAuthorizationCode.code == code))
        stored = result.scalar_one()
        expected_min = before + timedelta(minutes=9, seconds=59)
        expected_max = after + timedelta(minutes=10, seconds=1)
        assert expected_min <= stored.expires_at <= expected_max


@pytest.mark.asyncio
class TestExchangeCodeForToken:
    """Tests for exchange_code_for_token."""

    async def test_exchange_valid_code_returns_jwt(self, oauth_service, test_user, test_tenant_key):
        """Exchanging a valid code with correct PKCE verifier must return a JWT."""
        verifier, challenge = _generate_pkce_pair()
        code = await oauth_service.generate_authorization_code(
            user_id=test_user.id,
            tenant_key=test_tenant_key,
            client_id="giljo-mcp-default",
            redirect_uri="http://localhost:3000/callback",
            code_challenge=challenge,
        )

        token_response = await oauth_service.exchange_code_for_token(
            code=code,
            client_id="giljo-mcp-default",
            code_verifier=verifier,
            redirect_uri="http://localhost:3000/callback",
        )

        assert "access_token" in token_response
        assert token_response["token_type"] == "bearer"
        assert token_response["expires_in"] == 86400
        assert isinstance(token_response["access_token"], str)
        assert token_response["access_token"].count(".") == 2  # JWT has 3 parts

    async def test_exchange_expired_code_rejected(self, oauth_service, test_user, test_tenant_key, db_session):
        """An expired code must be rejected."""
        verifier, challenge = _generate_pkce_pair()
        code = await oauth_service.generate_authorization_code(
            user_id=test_user.id,
            tenant_key=test_tenant_key,
            client_id="giljo-mcp-default",
            redirect_uri="http://localhost:3000/callback",
            code_challenge=challenge,
        )

        # Manually expire the code
        result = await db_session.execute(select(OAuthAuthorizationCode).where(OAuthAuthorizationCode.code == code))
        stored = result.scalar_one()
        stored.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        await db_session.flush()

        with pytest.raises(ValueError, match="expired"):
            await oauth_service.exchange_code_for_token(
                code=code,
                client_id="giljo-mcp-default",
                code_verifier=verifier,
                redirect_uri="http://localhost:3000/callback",
            )

    async def test_exchange_used_code_rejected(self, oauth_service, test_user, test_tenant_key):
        """A code that has already been used must be rejected."""
        verifier, challenge = _generate_pkce_pair()
        code = await oauth_service.generate_authorization_code(
            user_id=test_user.id,
            tenant_key=test_tenant_key,
            client_id="giljo-mcp-default",
            redirect_uri="http://localhost:3000/callback",
            code_challenge=challenge,
        )

        # First exchange succeeds
        await oauth_service.exchange_code_for_token(
            code=code,
            client_id="giljo-mcp-default",
            code_verifier=verifier,
            redirect_uri="http://localhost:3000/callback",
        )

        # Second exchange must fail
        with pytest.raises(ValueError, match="used"):
            await oauth_service.exchange_code_for_token(
                code=code,
                client_id="giljo-mcp-default",
                code_verifier=verifier,
                redirect_uri="http://localhost:3000/callback",
            )

    async def test_exchange_wrong_client_id_rejected(self, oauth_service, test_user, test_tenant_key):
        """A mismatched client_id must be rejected."""
        verifier, challenge = _generate_pkce_pair()
        code = await oauth_service.generate_authorization_code(
            user_id=test_user.id,
            tenant_key=test_tenant_key,
            client_id="giljo-mcp-default",
            redirect_uri="http://localhost:3000/callback",
            code_challenge=challenge,
        )

        with pytest.raises(ValueError, match="client_id"):
            await oauth_service.exchange_code_for_token(
                code=code,
                client_id="wrong-client",
                code_verifier=verifier,
                redirect_uri="http://localhost:3000/callback",
            )

    async def test_exchange_wrong_redirect_uri_rejected(self, oauth_service, test_user, test_tenant_key):
        """A mismatched redirect_uri must be rejected."""
        verifier, challenge = _generate_pkce_pair()
        code = await oauth_service.generate_authorization_code(
            user_id=test_user.id,
            tenant_key=test_tenant_key,
            client_id="giljo-mcp-default",
            redirect_uri="http://localhost:3000/callback",
            code_challenge=challenge,
        )

        with pytest.raises(ValueError, match="redirect_uri"):
            await oauth_service.exchange_code_for_token(
                code=code,
                client_id="giljo-mcp-default",
                code_verifier=verifier,
                redirect_uri="http://localhost:4000/different",
            )

    async def test_exchange_wrong_pkce_verifier_rejected(self, oauth_service, test_user, test_tenant_key):
        """An incorrect PKCE code_verifier must be rejected."""
        _verifier, challenge = _generate_pkce_pair()
        code = await oauth_service.generate_authorization_code(
            user_id=test_user.id,
            tenant_key=test_tenant_key,
            client_id="giljo-mcp-default",
            redirect_uri="http://localhost:3000/callback",
            code_challenge=challenge,
        )

        wrong_verifier = secrets.token_urlsafe(64)
        with pytest.raises(ValueError, match="PKCE"):
            await oauth_service.exchange_code_for_token(
                code=code,
                client_id="giljo-mcp-default",
                code_verifier=wrong_verifier,
                redirect_uri="http://localhost:3000/callback",
            )

    async def test_exchange_nonexistent_code_rejected(self, oauth_service):
        """A code that does not exist must be rejected."""
        with pytest.raises(ValueError, match="not found"):
            await oauth_service.exchange_code_for_token(
                code="nonexistent-code-value",
                client_id="giljo-mcp-default",
                code_verifier="some-verifier",
                redirect_uri="http://localhost:3000/callback",
            )


@pytest.mark.asyncio
class TestCleanupExpiredCodes:
    """Tests for cleanup_expired_codes."""

    async def test_cleanup_deletes_expired_codes(self, oauth_service, test_user, test_tenant_key, db_session):
        """Expired codes must be deleted by cleanup."""
        _verifier, challenge = _generate_pkce_pair()
        code = await oauth_service.generate_authorization_code(
            user_id=test_user.id,
            tenant_key=test_tenant_key,
            client_id="giljo-mcp-default",
            redirect_uri="http://localhost:3000/callback",
            code_challenge=challenge,
        )

        # Expire the code
        result = await db_session.execute(select(OAuthAuthorizationCode).where(OAuthAuthorizationCode.code == code))
        stored = result.scalar_one()
        stored.expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        await db_session.flush()

        deleted_count = await oauth_service.cleanup_expired_codes()
        assert deleted_count >= 1

        result = await db_session.execute(select(OAuthAuthorizationCode).where(OAuthAuthorizationCode.code == code))
        assert result.scalar_one_or_none() is None

    async def test_cleanup_deletes_used_codes(self, oauth_service, test_user, test_tenant_key, db_session):
        """Used codes must be deleted by cleanup."""
        verifier, challenge = _generate_pkce_pair()
        code = await oauth_service.generate_authorization_code(
            user_id=test_user.id,
            tenant_key=test_tenant_key,
            client_id="giljo-mcp-default",
            redirect_uri="http://localhost:3000/callback",
            code_challenge=challenge,
        )

        # Exchange the code (marks it as used)
        await oauth_service.exchange_code_for_token(
            code=code,
            client_id="giljo-mcp-default",
            code_verifier=verifier,
            redirect_uri="http://localhost:3000/callback",
        )

        deleted_count = await oauth_service.cleanup_expired_codes()
        assert deleted_count >= 1

    async def test_cleanup_preserves_valid_codes(self, oauth_service, test_user, test_tenant_key, db_session):
        """Valid, unused codes must not be deleted by cleanup."""
        _verifier, challenge = _generate_pkce_pair()
        code = await oauth_service.generate_authorization_code(
            user_id=test_user.id,
            tenant_key=test_tenant_key,
            client_id="giljo-mcp-default",
            redirect_uri="http://localhost:3000/callback",
            code_challenge=challenge,
        )

        await oauth_service.cleanup_expired_codes()

        result = await db_session.execute(select(OAuthAuthorizationCode).where(OAuthAuthorizationCode.code == code))
        assert result.scalar_one_or_none() is not None
