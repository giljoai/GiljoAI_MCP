# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Tests for Product Context Write Protection (commit 712a1888f).

Covers three work items implemented in handover:
- WI-1: Active Product Guard — update_product() blocks writes to inactive products
- WI-2: Overwrite Confirmation — force parameter prevents accidental JSONB overwrites
- WI-3: tenant_key Consistency Check — API key auth rejects user/key tenant mismatch
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from giljo_mcp.exceptions import ValidationError


# ============================================================================
# SHARED FIXTURES
# ============================================================================


@pytest.fixture
def mock_db_manager():
    """Mock database manager that yields a mock async session."""
    db_manager = Mock()
    session = AsyncMock()

    async_cm = AsyncMock()
    async_cm.__aenter__ = AsyncMock(return_value=session)
    async_cm.__aexit__ = AsyncMock(return_value=False)

    db_manager.get_session_async = Mock(return_value=async_cm)
    return db_manager, session


@pytest.fixture
def inactive_product():
    """Mock Product with is_active=False."""
    product = MagicMock()
    product.id = "inactive-product-id"
    product.is_active = False
    product.tenant_key = "test-tenant"
    product.tech_stack = None
    product.architecture = None
    product.test_config = None
    return product


@pytest.fixture
def active_product():
    """Mock Product with is_active=True and no populated config fields."""
    product = MagicMock()
    product.id = "active-product-id"
    product.is_active = True
    product.tenant_key = "test-tenant"
    product.tech_stack = None
    product.architecture = None
    product.test_config = None
    product.core_features = None
    return product


@pytest.fixture
def active_product_with_tech_stack(active_product):
    """Active product that already has tech_stack populated."""
    active_product.tech_stack = MagicMock()  # Non-None — existing relationship row
    return active_product


@pytest.fixture
def active_product_with_all_fields(active_product):
    """Active product with all three JSONB config fields populated."""
    active_product.tech_stack = MagicMock()
    active_product.architecture = MagicMock()
    active_product.test_config = MagicMock()
    return active_product


def _build_service_with_product(mock_db_manager, product):
    """
    Helper: wire up ProductService so _repo.get_by_id returns the given product
    and commit/refresh are no-ops.
    """
    from giljo_mcp.services.product_service import ProductService

    db_manager, _session = mock_db_manager

    mock_repo = AsyncMock()
    mock_repo.get_by_id = AsyncMock(return_value=product)
    mock_repo.update_config_relations = AsyncMock()
    mock_repo.commit = AsyncMock()
    mock_repo.refresh = AsyncMock()

    service = ProductService(db_manager, "test-tenant")
    service._repo = mock_repo

    return service


# ============================================================================
# WI-1: Active Product Guard
# ============================================================================


class TestActiveProductGuard:
    """update_product() must raise ValidationError when product.is_active is False."""

    @pytest.mark.asyncio
    async def test_update_inactive_product_raises_validation_error(self, mock_db_manager, inactive_product):
        """Calling update_product() on an inactive product raises ValidationError."""
        service = _build_service_with_product(mock_db_manager, inactive_product)

        with pytest.raises(ValidationError) as exc_info:
            await service.update_product("inactive-product-id", name="New Name")

        assert "not the active product" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_update_inactive_product_error_message_mentions_switch(self, mock_db_manager, inactive_product):
        """Error message for inactive product includes guidance to switch products."""
        service = _build_service_with_product(mock_db_manager, inactive_product)

        with pytest.raises(ValidationError) as exc_info:
            await service.update_product("inactive-product-id", description="new desc")

        assert "switch" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_update_inactive_product_error_includes_product_id_in_context(
        self, mock_db_manager, inactive_product
    ):
        """ValidationError context must contain the product_id for debugging."""
        service = _build_service_with_product(mock_db_manager, inactive_product)

        with pytest.raises(ValidationError) as exc_info:
            await service.update_product("inactive-product-id", name="x")

        assert exc_info.value.context is not None
        assert "product_id" in exc_info.value.context

    @pytest.mark.asyncio
    async def test_update_active_product_succeeds_without_raising(self, mock_db_manager, active_product):
        """update_product() on an active product with no config fields completes normally."""
        service = _build_service_with_product(mock_db_manager, active_product)

        # Should not raise
        result = await service.update_product("active-product-id", name="Updated Name")
        assert result is not None

    @pytest.mark.asyncio
    async def test_active_guard_checked_before_overwrite_guard(self, mock_db_manager, inactive_product):
        """
        When product is inactive AND has tech_stack, inactive guard fires first.
        This verifies the ordering in the implementation.
        """
        inactive_product.tech_stack = MagicMock()  # Would trigger overwrite guard too
        service = _build_service_with_product(mock_db_manager, inactive_product)

        with pytest.raises(ValidationError) as exc_info:
            await service.update_product(
                "inactive-product-id",
                tech_stack={"language": "Python"},
                force=False,
            )

        # The "not active" message should fire, not the "already populated" one
        assert "not the active product" in exc_info.value.message.lower()


# ============================================================================
# WI-2: Overwrite Confirmation (force parameter)
# ============================================================================


class TestOverwriteConfirmation:
    """update_product() must guard populated JSONB fields behind force=True."""

    @pytest.mark.asyncio
    async def test_update_populated_tech_stack_without_force_raises_validation_error(
        self, mock_db_manager, active_product_with_tech_stack
    ):
        """Writing tech_stack when it already exists and force=False raises ValidationError."""
        service = _build_service_with_product(mock_db_manager, active_product_with_tech_stack)

        with pytest.raises(ValidationError) as exc_info:
            await service.update_product(
                "active-product-id",
                tech_stack={"language": "Python"},
                force=False,
            )

        assert "tech_stack" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_overwrite_error_message_lists_populated_fields(
        self, mock_db_manager, active_product_with_tech_stack
    ):
        """Error message for overwrite guard names the already-populated fields."""
        service = _build_service_with_product(mock_db_manager, active_product_with_tech_stack)

        with pytest.raises(ValidationError) as exc_info:
            await service.update_product(
                "active-product-id",
                tech_stack={"language": "Python"},
            )

        assert "already populated" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_overwrite_error_includes_populated_fields_in_context(
        self, mock_db_manager, active_product_with_tech_stack
    ):
        """ValidationError context must include 'populated_fields' list."""
        service = _build_service_with_product(mock_db_manager, active_product_with_tech_stack)

        with pytest.raises(ValidationError) as exc_info:
            await service.update_product(
                "active-product-id",
                tech_stack={"language": "Python"},
            )

        assert exc_info.value.context is not None
        assert "populated_fields" in exc_info.value.context
        assert "tech_stack" in exc_info.value.context["populated_fields"]

    @pytest.mark.asyncio
    async def test_update_populated_tech_stack_with_force_true_succeeds(
        self, mock_db_manager, active_product_with_tech_stack
    ):
        """Writing tech_stack when already populated is allowed when force=True."""
        service = _build_service_with_product(mock_db_manager, active_product_with_tech_stack)

        # Should not raise
        result = await service.update_product(
            "active-product-id",
            tech_stack={"language": "Go"},
            force=True,
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_update_empty_fields_without_force_succeeds(self, mock_db_manager, active_product):
        """Writing JSONB fields when they are empty does not require force=True."""
        service = _build_service_with_product(mock_db_manager, active_product)

        # No existing tech_stack → should succeed without force
        result = await service.update_product(
            "active-product-id",
            tech_stack={"language": "Python"},
            force=False,
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_all_three_populated_fields_listed_in_error(self, mock_db_manager, active_product_with_all_fields):
        """All three populated config fields appear in the error context."""
        service = _build_service_with_product(mock_db_manager, active_product_with_all_fields)

        with pytest.raises(ValidationError) as exc_info:
            await service.update_product(
                "active-product-id",
                tech_stack={"language": "Python"},
                architecture={"pattern": "microservices"},
                test_config={"framework": "pytest"},
                force=False,
            )

        populated = exc_info.value.context["populated_fields"]
        assert "tech_stack" in populated
        assert "architecture" in populated
        assert "test_config" in populated

    @pytest.mark.asyncio
    async def test_non_dict_tech_stack_value_does_not_trigger_overwrite_guard(
        self, mock_db_manager, active_product_with_tech_stack
    ):
        """
        A non-dict tech_stack value (e.g., None) is ignored by the guard.
        Only dict payloads trigger overwrite protection.
        """
        service = _build_service_with_product(mock_db_manager, active_product_with_tech_stack)

        # Passing None as tech_stack — not a dict → guard should not fire
        result = await service.update_product(
            "active-product-id",
            name="Updated Name",
            force=False,
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_force_default_is_false(self, mock_db_manager, active_product_with_tech_stack):
        """
        Calling update_product() without specifying force triggers overwrite guard
        (confirms default is False, not True).
        """
        service = _build_service_with_product(mock_db_manager, active_product_with_tech_stack)

        with pytest.raises(ValidationError):
            await service.update_product(
                "active-product-id",
                tech_stack={"language": "Rust"},
                # force not specified — defaults to False
            )


# ============================================================================
# WI-3: tenant_key Consistency on API Key Authentication
# ============================================================================


class TestApiKeyTenantKeyConsistency:
    """
    API key auth must reject a match where the User.tenant_key differs from
    the APIKey.tenant_key, preventing cross-tenant privilege escalation.

    These tests exercise the query logic in dependencies.py and mcp_session.py
    by mocking the database responses.
    """

    def _make_api_key_record(self, tenant_key="tk_abc123", user_id="user-1"):
        key = MagicMock()
        key.id = "key-id-1"
        key.tenant_key = tenant_key
        key.user_id = user_id
        key.is_active = True
        key.name = "Test Key"
        key.last_used = None
        key.expires_at = None
        return key

    def _make_user(self, tenant_key="tk_abc123", user_id="user-1", is_active=True):
        user = MagicMock()
        user.id = user_id
        user.tenant_key = tenant_key
        user.is_active = is_active
        user.username = "testuser"
        return user

    @pytest.mark.asyncio
    async def test_matching_tenant_key_returns_user(self):
        """
        When User.tenant_key == APIKey.tenant_key, authentication returns the user.
        """
        from giljo_mcp.auth.dependencies import get_current_user

        tenant_key = "tk_matching"
        key_record = self._make_api_key_record(tenant_key=tenant_key)
        user = self._make_user(tenant_key=tenant_key)

        # Build a raw_key that produces the correct key_prefix
        raw_key = "gk_abcdef123456789xyz"
        expected_prefix = f"{raw_key[:12]}..."
        key_record.key_prefix = expected_prefix
        key_record.key_hash = "hashed"

        mock_db = AsyncMock()

        # First query returns api_key candidates; second returns the matching user
        first_result = MagicMock()
        first_result.scalars.return_value.all.return_value = [key_record]
        second_result = MagicMock()
        second_result.scalar_one_or_none.return_value = user

        mock_db.execute = AsyncMock(side_effect=[first_result, second_result])
        mock_db.commit = AsyncMock()

        mock_request = MagicMock()
        mock_request.url.path = "/mcp/test"
        mock_request.client = None

        with patch("giljo_mcp.auth.dependencies.verify_api_key", return_value=True):
            result = await get_current_user(
                request=mock_request,
                access_token=None,
                authorization=None,
                x_api_key=raw_key,
                db=mock_db,
            )

        assert result is user

    @pytest.mark.asyncio
    async def test_mismatched_tenant_key_rejects_authentication(self):
        """
        When User.tenant_key != APIKey.tenant_key, the user query returns None
        (filtered by the consistency WHERE clause) and authentication is rejected.
        """
        from giljo_mcp.auth.dependencies import get_current_user

        key_tenant = "tk_key_tenant"

        key_record = self._make_api_key_record(tenant_key=key_tenant)
        raw_key = "gk_abcdef123456789xyz"
        key_record.key_prefix = f"{raw_key[:12]}..."
        key_record.key_hash = "hashed"

        mock_db = AsyncMock()

        # First query: returns the api_key candidate
        first_result = MagicMock()
        first_result.scalars.return_value.all.return_value = [key_record]
        # Second query: returns None — user not found because tenant_key filter excludes them
        second_result = MagicMock()
        second_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(side_effect=[first_result, second_result])
        mock_db.commit = AsyncMock()

        mock_request = MagicMock()
        mock_request.url.path = "/mcp/test"
        mock_request.client = None

        with patch("giljo_mcp.auth.dependencies.verify_api_key", return_value=True):
            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(
                    request=mock_request,
                    access_token=None,
                    authorization=None,
                    x_api_key=raw_key,
                    db=mock_db,
                )

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_inactive_user_with_matching_tenant_key_is_rejected(self):
        """
        An inactive user is rejected even when tenant_keys match.
        The User.is_active filter is part of the same WHERE clause.
        """
        from giljo_mcp.auth.dependencies import get_current_user

        tenant_key = "tk_matching"
        key_record = self._make_api_key_record(tenant_key=tenant_key)
        raw_key = "gk_abcdef123456789xyz"
        key_record.key_prefix = f"{raw_key[:12]}..."
        key_record.key_hash = "hashed"

        mock_db = AsyncMock()

        # First query: api_key found
        first_result = MagicMock()
        first_result.scalars.return_value.all.return_value = [key_record]
        # Second query: user not returned because User.is_active == False
        second_result = MagicMock()
        second_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(side_effect=[first_result, second_result])
        mock_db.commit = AsyncMock()

        mock_request = MagicMock()
        mock_request.url.path = "/mcp/test"
        mock_request.client = None

        with patch("giljo_mcp.auth.dependencies.verify_api_key", return_value=True):
            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(
                    request=mock_request,
                    access_token=None,
                    authorization=None,
                    x_api_key=raw_key,
                    db=mock_db,
                )

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_key_prefix_narrowing_limits_candidates(self):
        """
        The key_prefix WHERE clause is applied when querying APIKey candidates.
        An api key whose prefix does not match the presented key is not returned.
        """
        from giljo_mcp.auth.dependencies import get_current_user

        raw_key = "gk_abcdef123456789xyz"

        # Key with a different prefix — would not be returned by the DB query
        wrong_prefix_key = self._make_api_key_record()
        wrong_prefix_key.key_prefix = "gk_zzzzzzzzz..."
        wrong_prefix_key.key_hash = "hashed"

        mock_db = AsyncMock()

        # DB query returns empty (prefix did not match)
        first_result = MagicMock()
        first_result.scalars.return_value.all.return_value = []

        mock_db.execute = AsyncMock(return_value=first_result)
        mock_db.commit = AsyncMock()

        mock_request = MagicMock()
        mock_request.url.path = "/mcp/test"
        mock_request.client = None

        with patch("giljo_mcp.auth.dependencies.verify_api_key", return_value=False):
            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(
                    request=mock_request,
                    access_token=None,
                    authorization=None,
                    x_api_key=raw_key,
                    db=mock_db,
                )

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_mcp_session_mismatched_tenant_key_rejects_user(self):
        """
        MCPSessionManager.authenticate_api_key() rejects a user whose tenant_key
        does not match the API key's tenant_key.
        """
        from api.endpoints.mcp_session import MCPSessionManager

        tenant_key_key = "tk_key_tenant"
        key_record = self._make_api_key_record(tenant_key=tenant_key_key)
        raw_key = "gk_abcdef123456789xyz"
        key_record.key_prefix = f"{raw_key[:12]}..."
        key_record.key_hash = "hashed"

        mock_db = AsyncMock()

        # First query: api_key candidates (uses scalars().all())
        first_result = MagicMock()
        first_result.scalars.return_value.all.return_value = [key_record]
        # Second query: user not found (tenant mismatch filtered out by WHERE clause)
        second_result = MagicMock()
        second_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(side_effect=[first_result, second_result])
        mock_db.commit = AsyncMock()

        manager = MCPSessionManager(mock_db)

        with patch("api.endpoints.mcp_session.verify_api_key", return_value=True):
            result = await manager.authenticate_api_key(raw_key)

        assert result is None

    @pytest.mark.asyncio
    async def test_mcp_session_matching_tenant_key_returns_key_and_user(self):
        """
        MCPSessionManager.authenticate_api_key() returns (key_record, user) when
        tenant_keys match and user is active.
        """
        from api.endpoints.mcp_session import MCPSessionManager

        tenant_key = "tk_matching"
        user_id = "user-abc"
        key_record = self._make_api_key_record(tenant_key=tenant_key, user_id=user_id)
        user = self._make_user(tenant_key=tenant_key, user_id=user_id)
        raw_key = "gk_abcdef123456789xyz"
        key_record.key_prefix = f"{raw_key[:12]}..."
        key_record.key_hash = "hashed"

        mock_db = AsyncMock()

        # First query: api_key candidates (uses scalars().all())
        first_result = MagicMock()
        first_result.scalars.return_value.all.return_value = [key_record]
        # Second query: user found (tenant_keys match)
        second_result = MagicMock()
        second_result.scalar_one_or_none.return_value = user

        mock_db.execute = AsyncMock(side_effect=[first_result, second_result])
        mock_db.commit = AsyncMock()

        manager = MCPSessionManager(mock_db)

        with patch("api.endpoints.mcp_session.verify_api_key", return_value=True):
            result = await manager.authenticate_api_key(raw_key)

        assert result is not None
        _key_out, user_out = result
        assert user_out is user
