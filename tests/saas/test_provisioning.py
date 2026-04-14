# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.

"""Tests for SaaS tenant provisioning service and registration endpoint (SAAS-004).

All tests in tests/saas/ -- CE CI strips SaaS dirs, so these never run in CE.
"""

from __future__ import annotations

import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from giljo_mcp.saas.provisioning.schemas import RegistrationRequest, RegistrationResponse
from giljo_mcp.saas.provisioning.service import (
    DuplicateEmailError,
    ProvisioningResult,
    ProvisioningService,
)


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------


class TestRegistrationRequest:
    """RegistrationRequest Pydantic model validation."""

    def test_valid_email_only(self):
        req = RegistrationRequest(email="user@example.com")
        assert str(req.email) == "user@example.com"
        assert req.name == ""
        assert req.website == ""

    def test_valid_with_name(self):
        req = RegistrationRequest(email="user@example.com", name="Patrik")
        assert req.name == "Patrik"

    def test_email_normalised_to_lowercase(self):
        req = RegistrationRequest(email="User@Example.COM")
        assert str(req.email) == "user@example.com"

    def test_email_whitespace_stripped(self):
        req = RegistrationRequest(email="  user@example.com  ")
        assert str(req.email) == "user@example.com"

    def test_name_whitespace_stripped(self):
        req = RegistrationRequest(email="u@e.com", name="  Patrik  ")
        assert req.name == "Patrik"

    def test_invalid_email_rejected(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RegistrationRequest(email="not-an-email")

    def test_email_too_long_rejected(self):
        from pydantic import ValidationError

        long_email = "a" * 250 + "@b.com"
        with pytest.raises(ValidationError):
            RegistrationRequest(email=long_email)

    def test_name_too_long_rejected(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RegistrationRequest(email="u@e.com", name="x" * 256)

    def test_honeypot_field_present(self):
        req = RegistrationRequest(email="u@e.com", website="http://spam.bot")
        assert req.website == "http://spam.bot"


class TestRegistrationResponse:
    """RegistrationResponse Pydantic model."""

    def test_with_org_id(self):
        resp = RegistrationResponse(message="OK", org_id="abc-123")
        assert resp.org_id == "abc-123"

    def test_without_org_id(self):
        resp = RegistrationResponse(message="OK")
        assert resp.org_id is None


# ---------------------------------------------------------------------------
# ProvisioningService unit tests (mocked DB session)
# ---------------------------------------------------------------------------


class TestProvisioningServiceHelpers:
    """Test static helper methods that don't need DB."""

    def test_generate_password_length(self):
        pw = ProvisioningService._generate_password()
        assert len(pw) == 16

    def test_generate_password_has_all_pools(self):
        pw = ProvisioningService._generate_password()
        assert any(c.isupper() for c in pw), "Must contain uppercase"
        assert any(c.islower() for c in pw), "Must contain lowercase"
        assert any(c.isdigit() for c in pw), "Must contain digit"
        assert any(c in "!@#$%&*" for c in pw), "Must contain symbol"

    def test_generate_password_uniqueness(self):
        passwords = {ProvisioningService._generate_password() for _ in range(50)}
        assert len(passwords) == 50, "50 passwords should all be unique"

    def test_derive_username_format(self):
        username = ProvisioningService._derive_username("patrik@giljo.ai")
        assert username.startswith("patrik_")
        assert len(username) == len("patrik_") + 4
        assert username[-4:].isdigit()

    def test_derive_username_special_chars_stripped(self):
        username = ProvisioningService._derive_username("p.a+t@giljo.ai")
        # Only alphanumeric and underscore kept
        local_part = username.rsplit("_", 1)[0]
        assert re.match(r"^[a-zA-Z0-9_]+$", local_part)

    def test_derive_username_empty_local_part(self):
        username = ProvisioningService._derive_username("@giljo.ai")
        assert username.startswith("user_")

    def test_generate_slug_basic(self):
        assert ProvisioningService._generate_slug("Patrik's Workspace") == "patriks-workspace"

    def test_generate_slug_special_chars(self):
        assert ProvisioningService._generate_slug("Test & Demo!") == "test-demo"

    def test_generate_slug_empty_returns_workspace(self):
        assert ProvisioningService._generate_slug("!!!") == "workspace"


class TestProvisioningServiceProvisionTenant:
    """Test provision_tenant with mocked AsyncSession."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock AsyncSession with awaitable async methods."""
        session = AsyncMock()
        session.add = MagicMock()  # add is sync
        return session

    @pytest.fixture
    def mock_session_no_existing(self, mock_session):
        """Session that returns no existing user/slug."""
        # Mock execute to return no results (no duplicate email, no slug collision)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        return mock_session

    @pytest.mark.asyncio
    async def test_provision_creates_all_entities(self, mock_session_no_existing):
        svc = ProvisioningService(mock_session_no_existing)
        result = await svc.provision_tenant(email="test@example.com", name="Test User")

        assert isinstance(result, ProvisioningResult)
        assert result.org_id
        assert result.user_id
        assert result.tenant_key.startswith("tk_")
        assert len(result.generated_password) == 16

        # Should have added 4 entities: User, Org, OrgMembership, SetupState
        assert mock_session_no_existing.add.call_count == 4
        # Should have flushed 3 times (after user, after org, final)
        assert mock_session_no_existing.flush.call_count == 3

    @pytest.mark.asyncio
    async def test_provision_derives_name_from_email(self, mock_session_no_existing):
        svc = ProvisioningService(mock_session_no_existing)
        await svc.provision_tenant(email="hello@world.com", name="")

        # The org name should be derived from the email local part
        add_calls = mock_session_no_existing.add.call_args_list
        # Second add call is the Organization
        org = add_calls[1][0][0]
        assert "hello" in org.name.lower()

    @pytest.mark.asyncio
    async def test_provision_duplicate_email_raises(self, mock_session):
        """If email exists in any tenant, DuplicateEmailError is raised."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "existing-user-id"
        mock_session.execute = AsyncMock(return_value=mock_result)

        svc = ProvisioningService(mock_session)
        with pytest.raises(DuplicateEmailError):
            await svc.provision_tenant(email="taken@example.com", name="Test")

    @pytest.mark.asyncio
    async def test_provision_user_has_correct_flags(self, mock_session_no_existing):
        svc = ProvisioningService(mock_session_no_existing)
        await svc.provision_tenant(email="test@example.com", name="Test")

        add_calls = mock_session_no_existing.add.call_args_list
        user = add_calls[0][0][0]
        assert user.role == "admin"
        assert user.is_active is True
        assert user.must_change_password is True
        assert user.must_set_pin is True
        assert user.email == "test@example.com"
        assert user.tenant_key.startswith("tk_")
        assert user.password_hash  # bcrypt hash should be set

    @pytest.mark.asyncio
    async def test_provision_org_membership_is_owner(self, mock_session_no_existing):
        svc = ProvisioningService(mock_session_no_existing)
        await svc.provision_tenant(email="test@example.com", name="Test")

        add_calls = mock_session_no_existing.add.call_args_list
        membership = add_calls[2][0][0]
        assert membership.role == "owner"
        assert membership.is_active is True

    @pytest.mark.asyncio
    async def test_provision_setup_state_initialized(self, mock_session_no_existing):
        svc = ProvisioningService(mock_session_no_existing)
        await svc.provision_tenant(email="test@example.com", name="Test")

        add_calls = mock_session_no_existing.add.call_args_list
        setup = add_calls[3][0][0]
        assert setup.database_initialized is True
        assert setup.setup_version == "3.1.0"
        assert setup.database_initialized_at is not None


# ---------------------------------------------------------------------------
# Registration endpoint unit tests (mocked dependencies)
# ---------------------------------------------------------------------------


class TestRegisterEndpoint:
    """Test the registration endpoint handler logic with mocks."""

    @pytest.mark.asyncio
    async def test_honeypot_returns_fake_201(self):
        """If honeypot field is filled, return fake success (no DB work)."""
        from api.saas_endpoints.register import register

        mock_request = MagicMock()
        mock_request.client.host = "1.2.3.4"
        mock_request.base_url = "http://test/"

        body = RegistrationRequest(email="bot@spam.com", website="http://spam.bot")
        mock_db = AsyncMock()

        # Patch rate limiter to allow
        with patch("api.saas_endpoints.register.get_rate_limiter") as mock_rl:
            mock_rl.return_value.check_rate_limit.return_value = True
            resp = await register(request=mock_request, body=body, db=mock_db)

        assert isinstance(resp, RegistrationResponse)
        assert "successful" in resp.message.lower()
        # DB should NOT have been used for provisioning
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_duplicate_email_returns_409(self):
        """Duplicate email returns 409 conflict."""
        from api.saas_endpoints.register import register

        mock_request = MagicMock()
        mock_request.client.host = "1.2.3.4"
        mock_request.base_url = "http://test/"

        body = RegistrationRequest(email="taken@example.com")
        mock_db = AsyncMock()

        with (
            patch("api.saas_endpoints.register.get_rate_limiter") as mock_rl,
            patch("api.saas_endpoints.register.ProvisioningService") as mock_svc_cls,
        ):
            mock_rl.return_value.check_rate_limit.return_value = True
            mock_svc_cls.return_value.provision_tenant = AsyncMock(side_effect=DuplicateEmailError("exists"))
            resp = await register(request=mock_request, body=body, db=mock_db)

        assert resp.status_code == 409
        assert "already exists" in resp.body.decode().lower()

    @pytest.mark.asyncio
    async def test_successful_registration_returns_201(self):
        """Happy path: provision + email send, returns 201."""
        from api.saas_endpoints.register import register

        mock_request = MagicMock()
        mock_request.client.host = "1.2.3.4"
        mock_request.base_url = "http://test/"

        body = RegistrationRequest(email="new@example.com", name="New User")
        mock_db = AsyncMock()

        fake_result = ProvisioningResult(
            org_id="org-123",
            user_id="user-456",
            tenant_key="tk_abc",
            generated_password="Abcd1234!@#$efgh",
        )

        with (
            patch("api.saas_endpoints.register.get_rate_limiter") as mock_rl,
            patch("api.saas_endpoints.register.ProvisioningService") as mock_svc_cls,
            patch("api.saas_endpoints.register.get_email_service") as mock_email,
        ):
            mock_rl.return_value.check_rate_limit.return_value = True
            mock_svc_cls.return_value.provision_tenant = AsyncMock(return_value=fake_result)
            mock_email.return_value.send_template = AsyncMock(return_value=True)

            resp = await register(request=mock_request, body=body, db=mock_db)

        assert isinstance(resp, RegistrationResponse)
        assert resp.org_id == "org-123"
        assert "successful" in resp.message.lower()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_email_failure_does_not_rollback(self):
        """If welcome email fails, the registration still succeeds."""
        from api.saas_endpoints.register import register

        mock_request = MagicMock()
        mock_request.client.host = "1.2.3.4"
        mock_request.base_url = "http://test/"

        body = RegistrationRequest(email="new@example.com", name="New User")
        mock_db = AsyncMock()

        fake_result = ProvisioningResult(
            org_id="org-123",
            user_id="user-456",
            tenant_key="tk_abc",
            generated_password="Abcd1234!@#$efgh",
        )

        with (
            patch("api.saas_endpoints.register.get_rate_limiter") as mock_rl,
            patch("api.saas_endpoints.register.ProvisioningService") as mock_svc_cls,
            patch("api.saas_endpoints.register.get_email_service") as mock_email,
        ):
            mock_rl.return_value.check_rate_limit.return_value = True
            mock_svc_cls.return_value.provision_tenant = AsyncMock(return_value=fake_result)
            mock_email.return_value.send_template = AsyncMock(side_effect=RuntimeError("SMTP down"))

            resp = await register(request=mock_request, body=body, db=mock_db)

        # Registration still succeeds despite email failure
        assert isinstance(resp, RegistrationResponse)
        assert resp.org_id == "org-123"
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded_returns_429(self):
        """When rate limit is exceeded, endpoint returns 429."""
        from fastapi import HTTPException

        from api.saas_endpoints.register import register

        mock_request = MagicMock()
        mock_request.client.host = "1.2.3.4"
        mock_request.base_url = "http://test/"

        body = RegistrationRequest(email="new@example.com")
        mock_db = AsyncMock()

        with patch("api.saas_endpoints.register.get_rate_limiter") as mock_rl:
            mock_rl.return_value.check_rate_limit.side_effect = HTTPException(
                status_code=429, detail="Too many requests."
            )
            with pytest.raises(HTTPException) as exc_info:
                await register(request=mock_request, body=body, db=mock_db)
            assert exc_info.value.status_code == 429

        # DB should NOT have been touched
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_email_rejected_by_schema(self):
        """Request without email field fails Pydantic validation (422)."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RegistrationRequest()

    @pytest.mark.asyncio
    async def test_db_error_during_provision_does_not_commit(self):
        """If ProvisioningService raises an unexpected error, no commit happens."""
        from api.saas_endpoints.register import register

        mock_request = MagicMock()
        mock_request.client.host = "1.2.3.4"
        mock_request.base_url = "http://test/"

        body = RegistrationRequest(email="new@example.com")
        mock_db = AsyncMock()

        with (
            patch("api.saas_endpoints.register.get_rate_limiter") as mock_rl,
            patch("api.saas_endpoints.register.ProvisioningService") as mock_svc_cls,
        ):
            mock_rl.return_value.check_rate_limit.return_value = True
            mock_svc_cls.return_value.provision_tenant = AsyncMock(side_effect=RuntimeError("DB connection lost"))
            with pytest.raises(RuntimeError, match="DB connection lost"):
                await register(request=mock_request, body=body, db=mock_db)

        mock_db.commit.assert_not_called()


# ---------------------------------------------------------------------------
# Additional ProvisioningService edge-case tests
# ---------------------------------------------------------------------------


class TestProvisioningServiceEdgeCases:
    """Edge cases for ProvisioningService not covered in the base suite."""

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.add = MagicMock()
        return session

    @pytest.fixture
    def mock_session_no_existing(self, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        return mock_session

    @pytest.mark.asyncio
    async def test_all_entities_share_same_tenant_key(self, mock_session_no_existing):
        """User, Organization, OrgMembership, and SetupState must all get the same tenant_key."""
        svc = ProvisioningService(mock_session_no_existing)
        result = await svc.provision_tenant(email="test@example.com", name="Test")

        add_calls = mock_session_no_existing.add.call_args_list
        user = add_calls[0][0][0]
        org = add_calls[1][0][0]
        membership = add_calls[2][0][0]
        setup_state = add_calls[3][0][0]

        assert user.tenant_key == result.tenant_key
        assert org.tenant_key == result.tenant_key
        assert membership.tenant_key == result.tenant_key
        assert setup_state.tenant_key == result.tenant_key

    @pytest.mark.asyncio
    async def test_slug_collision_appends_suffix(self):
        """When the generated slug already exists, a random suffix is appended."""
        session = AsyncMock()
        session.add = MagicMock()

        # First execute: no duplicate email. Second: slug exists. Third: no duplicate (flush).
        call_count = 0
        mock_no_result = MagicMock()
        mock_no_result.scalar_one_or_none.return_value = None
        mock_slug_exists = MagicMock()
        mock_slug_exists.scalar_one_or_none.return_value = "existing-org-id"

        async def side_effect_execute(stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_no_result  # No duplicate email
            if call_count == 2:
                return mock_slug_exists  # Slug collision
            return mock_no_result

        session.execute = AsyncMock(side_effect=side_effect_execute)

        svc = ProvisioningService(session)
        await svc.provision_tenant(email="test@example.com", name="Test")

        # Verify the org slug has a suffix (longer than the base slug)
        add_calls = session.add.call_args_list
        org = add_calls[1][0][0]
        base_slug = ProvisioningService._generate_slug("Test's Workspace")
        assert org.slug.startswith(base_slug)
        assert len(org.slug) > len(base_slug)  # suffix was appended

    @pytest.mark.asyncio
    async def test_user_org_id_set_after_org_creation(self, mock_session_no_existing):
        """The user.org_id is set to the created organization's id."""
        svc = ProvisioningService(mock_session_no_existing)
        result = await svc.provision_tenant(email="test@example.com", name="Test")

        add_calls = mock_session_no_existing.add.call_args_list
        user = add_calls[0][0][0]
        org = add_calls[1][0][0]
        assert user.org_id == org.id
        assert user.org_id == result.org_id

    @pytest.mark.asyncio
    async def test_password_hash_is_bcrypt(self, mock_session_no_existing):
        """The stored password_hash is a valid bcrypt hash."""
        svc = ProvisioningService(mock_session_no_existing)
        result = await svc.provision_tenant(email="test@example.com", name="Test")

        add_calls = mock_session_no_existing.add.call_args_list
        user = add_calls[0][0][0]
        # bcrypt hashes start with $2b$
        assert user.password_hash.startswith("$2b$")
        # Verify the plaintext password matches the hash
        import bcrypt

        assert bcrypt.checkpw(
            result.generated_password.encode("utf-8"),
            user.password_hash.encode("utf-8"),
        )

    def test_generate_slug_long_input_produces_valid_slug(self):
        """Very long org names produce a valid slug without breaking."""
        long_name = "A" * 500 + "'s Workspace"
        slug = ProvisioningService._generate_slug(long_name)
        assert re.match(r"^[a-z0-9-]+$", slug)
        assert slug  # not empty

    def test_derive_username_truncates_long_local_part(self):
        """Email local part > 55 chars gets truncated in username."""
        long_local = "a" * 100
        username = ProvisioningService._derive_username(f"{long_local}@example.com")
        local_part = username.rsplit("_", 1)[0]
        assert len(local_part) <= 55


# ---------------------------------------------------------------------------
# Additional schema edge-case tests
# ---------------------------------------------------------------------------


class TestRegistrationRequestEdgeCases:
    """Edge cases for RegistrationRequest not covered in the base suite."""

    def test_name_non_string_rejected(self):
        """Non-string name values are rejected by Pydantic strict string type."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="string"):
            RegistrationRequest(email="u@e.com", name=123)

    def test_email_non_string_rejected(self):
        """Non-string email values are rejected by Pydantic validation."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RegistrationRequest(email=12345)

    def test_website_max_length_rejected(self):
        """website field exceeding max_length=500 is rejected."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RegistrationRequest(email="u@e.com", website="x" * 501)

    def test_website_within_max_length_accepted(self):
        """website field at exactly 500 chars is accepted."""
        req = RegistrationRequest(email="u@e.com", website="x" * 500)
        assert len(req.website) == 500

    def test_empty_email_rejected(self):
        """Empty string email fails validation."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RegistrationRequest(email="")

    def test_name_exactly_255_chars_accepted(self):
        """Name at exactly 255 chars is accepted."""
        req = RegistrationRequest(email="u@e.com", name="a" * 255)
        assert len(req.name) == 255


# ---------------------------------------------------------------------------
# Additional endpoint edge-case tests
# ---------------------------------------------------------------------------


class TestRegisterEndpointEdgeCases:
    """Additional endpoint tests for uncovered branches."""

    @pytest.mark.asyncio
    async def test_honeypot_does_not_invoke_provisioning_service(self):
        """If honeypot is filled, ProvisioningService is never instantiated."""
        from api.saas_endpoints.register import register

        mock_request = MagicMock()
        mock_request.client.host = "1.2.3.4"
        mock_request.base_url = "http://test/"

        body = RegistrationRequest(email="bot@spam.com", website="http://spam.bot")
        mock_db = AsyncMock()

        with (
            patch("api.saas_endpoints.register.get_rate_limiter") as mock_rl,
            patch("api.saas_endpoints.register.ProvisioningService") as mock_svc_cls,
        ):
            mock_rl.return_value.check_rate_limit.return_value = True
            resp = await register(request=mock_request, body=body, db=mock_db)

        # ProvisioningService should never have been called
        mock_svc_cls.assert_not_called()
        assert isinstance(resp, RegistrationResponse)

    @pytest.mark.asyncio
    async def test_successful_registration_commits_before_email(self):
        """The DB commit happens before the email send attempt."""
        from api.saas_endpoints.register import register

        mock_request = MagicMock()
        mock_request.client.host = "1.2.3.4"
        mock_request.base_url = "http://test/"

        body = RegistrationRequest(email="new@example.com", name="New User")
        mock_db = AsyncMock()

        call_order = []

        async def track_commit():
            call_order.append("commit")

        mock_db.commit = AsyncMock(side_effect=track_commit)

        fake_result = ProvisioningResult(
            org_id="org-123",
            user_id="user-456",
            tenant_key="tk_abc",
            generated_password="Abcd1234!@#$efgh",
        )

        async def track_email(*args, **kwargs):
            call_order.append("email")
            return True

        with (
            patch("api.saas_endpoints.register.get_rate_limiter") as mock_rl,
            patch("api.saas_endpoints.register.ProvisioningService") as mock_svc_cls,
            patch("api.saas_endpoints.register.get_email_service") as mock_email,
        ):
            mock_rl.return_value.check_rate_limit.return_value = True
            mock_svc_cls.return_value.provision_tenant = AsyncMock(return_value=fake_result)
            mock_email.return_value.send_template = AsyncMock(side_effect=track_email)

            await register(request=mock_request, body=body, db=mock_db)

        assert call_order == ["commit", "email"]

    @pytest.mark.asyncio
    async def test_successful_registration_response_contains_message(self):
        """The response message contains human-readable success text."""
        from api.saas_endpoints.register import register

        mock_request = MagicMock()
        mock_request.client.host = "1.2.3.4"
        mock_request.base_url = "http://test/"

        body = RegistrationRequest(email="new@example.com")
        mock_db = AsyncMock()

        fake_result = ProvisioningResult(
            org_id="org-123",
            user_id="user-456",
            tenant_key="tk_abc",
            generated_password="Abcd1234!@#$efgh",
        )

        with (
            patch("api.saas_endpoints.register.get_rate_limiter") as mock_rl,
            patch("api.saas_endpoints.register.ProvisioningService") as mock_svc_cls,
            patch("api.saas_endpoints.register.get_email_service") as mock_email,
        ):
            mock_rl.return_value.check_rate_limit.return_value = True
            mock_svc_cls.return_value.provision_tenant = AsyncMock(return_value=fake_result)
            mock_email.return_value.send_template = AsyncMock(return_value=True)

            resp = await register(request=mock_request, body=body, db=mock_db)

        assert "email" in resp.message.lower()
        assert "credential" in resp.message.lower() or "login" in resp.message.lower()
