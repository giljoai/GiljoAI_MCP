# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Regression tests for BE-6026 auth-layer bypass-review hygiene fixes.

Item 2 (api.auth_utils.validate_api_key): the candidate set MUST be narrowed by
``key_prefix`` BEFORE bcrypt verification so a caller cannot force a full-table
bcrypt scan of every active key (DoS footgun). Tests assert the prefix filter is
applied at the SQL layer (decoy keys with other prefixes are never bcrypt-checked)
and that a wrong-prefix presentation resolves to None without scanning.

Item 3 (giljo_mcp.auth_manager.AuthManager._build_api_key_result): the user object
MUST be resolved by the key's stored ``user_id`` + ``tenant_key``, NOT by matching
the key's free-text display label against ``User.username``. A label that collides
with another user's username must not resolve to that other account.

Tests use real PostgreSQL via the shared transactional ``db_session`` (rolled back
at teardown). No module-level mutable state; no ordering dependencies.
"""

from types import SimpleNamespace
from uuid import uuid4

import bcrypt
import pytest

from giljo_mcp.api_key_utils import get_key_prefix
from giljo_mcp.models.auth import APIKey, User
from giljo_mcp.tenant import TenantManager


def _stored_key_prefix(plaintext: str) -> str:
    """Replicate the key_prefix value stored at key CREATION time.

    Both CE (auth_service.create_api_key) and SaaS (org_api_keys) persist
    ``get_key_prefix(plaintext, length=12)``; lookups must compute the same value.
    """
    return get_key_prefix(plaintext, length=12)


def _user(tenant_key: str, username: str) -> User:
    return User(
        id=str(uuid4()),
        tenant_key=tenant_key,
        username=username,
        email=f"{username}_{uuid4().hex[:6]}@example.com",
        password_hash="not-used",
        role="developer",
        is_active=True,
    )


def _api_key_row(tenant_key: str, user_id: str, plaintext: str, *, name: str) -> APIKey:
    """Build an APIKey row with the same key_prefix convention as production.

    Uses get_key_prefix so the stored prefix matches creation-time persistence
    (auth_service / org_api_keys), not the inline lookup slice.
    """
    key_prefix = _stored_key_prefix(plaintext)
    return APIKey(
        id=str(uuid4()),
        tenant_key=tenant_key,
        user_id=user_id,
        name=name,
        key_hash=bcrypt.hashpw(plaintext.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
        key_prefix=key_prefix,
        permissions=["*"],
        is_active=True,
    )


# ---------------------------------------------------------------------------
# Item 2: validate_api_key narrows by key_prefix before bcrypt
# ---------------------------------------------------------------------------


class TestValidateApiKeyNarrowsByPrefix:
    @pytest.mark.asyncio
    async def test_only_prefix_matching_key_is_bcrypt_checked(self, db_session, monkeypatch):
        """Decoy keys with other prefixes must never reach bcrypt verification."""
        from api import auth_utils

        tenant = TenantManager.generate_tenant_key()
        user = _user(tenant, f"apikey_owner_{uuid4().hex[:6]}")
        db_session.add(user)
        await db_session.flush()

        real_plaintext = "gk_realkey_" + uuid4().hex
        real_key = _api_key_row(tenant, user.id, real_plaintext, name="real")

        # Decoys: active keys with DIFFERENT prefixes that must be excluded by
        # the SQL WHERE clause and therefore never bcrypt-checked.
        decoys = [
            _api_key_row(tenant, user.id, "gk_decoyAAA_" + uuid4().hex, name="decoy-a"),
            _api_key_row(tenant, user.id, "gk_decoyBBB_" + uuid4().hex, name="decoy-b"),
        ]
        db_session.add_all([real_key, *decoys])
        await db_session.commit()

        checked_hashes: list[str] = []
        real_checkpw = bcrypt.checkpw

        def _spy_checkpw(password: bytes, hashed: bytes) -> bool:
            checked_hashes.append(hashed.decode("utf-8"))
            return real_checkpw(password, hashed)

        monkeypatch.setattr("bcrypt.checkpw", _spy_checkpw)

        result = await auth_utils.validate_api_key(real_plaintext, db=db_session)

        assert result is not None
        assert result["tenant_key"] == tenant
        # Only the prefix-matching candidate may be bcrypt-checked. The decoy
        # hashes must never appear: prefix narrowing excluded them at the SQL layer.
        assert real_key.key_hash in checked_hashes
        for decoy in decoys:
            assert decoy.key_hash not in checked_hashes
        assert len(checked_hashes) == 1

    @pytest.mark.asyncio
    async def test_wrong_prefix_presentation_returns_none_without_scanning(self, db_session, monkeypatch):
        """A presented key whose prefix matches no stored row returns None and bcrypt-checks nothing."""
        from api import auth_utils

        tenant = TenantManager.generate_tenant_key()
        user = _user(tenant, f"apikey_owner_{uuid4().hex[:6]}")
        db_session.add(user)
        await db_session.flush()

        stored_plaintext = "gk_storedkey_" + uuid4().hex
        db_session.add(_api_key_row(tenant, user.id, stored_plaintext, name="stored"))
        await db_session.commit()

        check_count = {"n": 0}
        real_checkpw = bcrypt.checkpw

        def _spy_checkpw(password: bytes, hashed: bytes) -> bool:
            check_count["n"] += 1
            return real_checkpw(password, hashed)

        monkeypatch.setattr("bcrypt.checkpw", _spy_checkpw)

        # Different 12-char prefix than any stored key -> filtered out by WHERE.
        result = await auth_utils.validate_api_key("gk_nomatchXX_" + uuid4().hex, db=db_session)

        assert result is None
        assert check_count["n"] == 0


# ---------------------------------------------------------------------------
# Item 3: _build_api_key_result resolves by user_id, not by label==username
# ---------------------------------------------------------------------------


class TestBuildApiKeyResultResolvesByUserId:
    @pytest.mark.asyncio
    async def test_label_colliding_with_other_username_does_not_resolve_wrong_user(self, db_session, db_manager):
        """The key label must NOT be matched against usernames for identity."""
        from contextlib import asynccontextmanager

        from giljo_mcp.auth_manager import AuthManager

        tenant = TenantManager.generate_tenant_key()
        # The key's true owner.
        owner = _user(tenant, f"true_owner_{uuid4().hex[:6]}")
        # A DIFFERENT user whose username equals the key's display label. The
        # latent bug would resolve to THIS user via username == label.
        label = f"shared_label_{uuid4().hex[:6]}"
        impostor = _user(tenant, label)
        db_session.add_all([owner, impostor])
        await db_session.commit()

        @asynccontextmanager
        async def _session_ctx():
            yield db_session

        db_manager.get_session_async = _session_ctx

        mgr = AuthManager()
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db_manager=db_manager)))

        key_info = {
            "name": label,  # label collides with impostor.username
            "user_id": owner.id,  # the true identity
            "tenant_key": tenant,
            "permissions": ["*"],
        }

        result = await mgr._build_api_key_result(key_info, request)

        assert result["authenticated"] is True
        assert result["tenant_key"] == tenant
        # Resolved the OWNER by user_id, never the impostor whose username == label.
        assert "user_obj" in result
        assert result["user_obj"].id == owner.id
        assert result["user_obj"].username == owner.username
        # BE-6028: once the real user resolves, user/user_id must be the resolved
        # username (matching the JWT path), NOT the key's free-text label.
        assert result["user"] == owner.username
        assert result["user_id"] == owner.username
        assert result["user"] != label
        assert result["user_id"] != label

    @pytest.mark.asyncio
    async def test_keyinfo_without_user_id_skips_enrichment(self, db_session, db_manager):
        """Installer-style keys carry no user_id; enrichment is skipped, tenant_key honored."""
        from contextlib import asynccontextmanager

        from giljo_mcp.auth_manager import AuthManager

        tenant = TenantManager.generate_tenant_key()

        called = {"session": False}

        @asynccontextmanager
        async def _session_ctx():
            called["session"] = True
            yield db_session

        db_manager.get_session_async = _session_ctx

        mgr = AuthManager()
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db_manager=db_manager)))

        key_info = {
            "name": "Installer Generated",
            "tenant_key": tenant,
            "permissions": ["*"],
            # no user_id
        }

        result = await mgr._build_api_key_result(key_info, request)

        assert result["authenticated"] is True
        assert result["tenant_key"] == tenant
        assert "user_obj" not in result
        # No user_id -> no DB enrichment attempt at all.
        assert called["session"] is False
        # BE-6028: with no user to resolve, the label fallback is preserved
        # unchanged on both user and user_id.
        assert result["user"] == "Installer Generated"
        assert result["user_id"] == "Installer Generated"


# ---------------------------------------------------------------------------
# BE-6028 Item 2: stored vs computed key_prefix agree at every length boundary
# ---------------------------------------------------------------------------


class TestKeyPrefixConventionAgreement:
    """The prefix stored at creation must equal the prefix computed at lookup.

    Creation persists ``get_key_prefix(plaintext, length=12)`` (auth_service,
    org_api_keys). The three lookup sites (api/auth_utils, auth/dependencies,
    api/endpoints/mcp_session) MUST narrow by the SAME value. The previous inline
    slice ``f"{key[:12]}..." if len(key) >= 12 else key`` disagreed at exactly 12
    characters (lookup added an ellipsis the stored value did not have), so an
    exactly-12-char key could never be found. These tests pin the convergence.
    """

    @pytest.mark.parametrize(
        "plaintext",
        [
            "",
            "gk_a",
            "12345678901",  # 11 chars: below boundary
            "123456789012",  # 12 chars: the exact boundary that previously diverged
            "1234567890123",  # 13 chars: above boundary
            "gk_realisticlongtoken_" + "a" * 30,
        ],
    )
    def test_stored_and_lookup_prefix_match(self, plaintext):
        """Lookup prefix == stored prefix for keys of every relevant length."""
        stored = _stored_key_prefix(plaintext)
        # The lookup sites now delegate to get_key_prefix; assert that single
        # source of truth produces the same value the row was created with.
        lookup = get_key_prefix(plaintext)
        assert lookup == stored

    def test_exact_boundary_has_no_spurious_ellipsis(self):
        """A 12-char key stores and looks up WITHOUT an ellipsis (regression)."""
        plaintext = "123456789012"
        assert len(plaintext) == 12
        assert _stored_key_prefix(plaintext) == "123456789012"
        assert get_key_prefix(plaintext) == "123456789012"

    @pytest.mark.asyncio
    async def test_validate_api_key_finds_exact_boundary_key(self, db_session):
        """End-to-end: a stored exactly-12-char key resolves via validate_api_key."""
        from api import auth_utils

        tenant = TenantManager.generate_tenant_key()
        user = _user(tenant, f"apikey_owner_{uuid4().hex[:6]}")
        db_session.add(user)
        await db_session.flush()

        boundary_plaintext = "abcdefghijkl"  # exactly 12 chars
        assert len(boundary_plaintext) == 12
        db_session.add(_api_key_row(tenant, user.id, boundary_plaintext, name="boundary"))
        await db_session.commit()

        result = await auth_utils.validate_api_key(boundary_plaintext, db=db_session)

        assert result is not None
        assert result["tenant_key"] == tenant
