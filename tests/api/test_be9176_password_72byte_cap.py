# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-9176 — password-SET paths 500 on passwords over bcrypt's 72-UTF-8-byte limit.

Password-set schemas advertised ``max_length=128`` CHARACTERS (or no cap at
all) while bcrypt >= 4 raises ``ValueError`` on any secret over 72 UTF-8
BYTES — so setting a 73-128-char (or shorter multibyte, e.g. emoji) password
passed validation and 500'd at ``async_hash_password``. SEC-9174 #6 already
fail-closed the VERIFY side; this is the WRITE side.

Fix under test: every password-set schema caps at 72 (``max_length=72`` chars
as the advertised bound, plus the shared ``validate_password_byte_length``
check for multibyte strings that fit 72 chars but exceed 72 bytes), so the
reject is a clean 422 at the validation boundary.

Failing-layer regression tests (the bug lived at the validation boundary —
the schema admitted what the hasher cannot take), driven through the FastAPI
routes that reach the hash call:

  - PUT /api/v1/users/{user_id}/password          (change-password)
  - POST /api/auth/verify-pin-and-reset-password  (CE recovery-PIN reset)
  - POST /api/auth/complete-first-login           (first-login password set)

The register endpoints are gated BEFORE their hash call (/api/auth/register
403s via member_management_enabled(); /api/auth/create-first-admin only runs
on an empty users table), so the register-path cap is proven at the schema
layer (RegisterUserRequest / UserCreate) — the exact layer the fix lives at.

Two-sided: a password of exactly 72 UTF-8 bytes (ASCII and multibyte) still
validates and the route flows still succeed end-to-end.

Parallel-safe: unique tenant/user per test, monkeypatch-only module patching,
no module-level mutable state.
"""

from __future__ import annotations

import secrets
from uuid import uuid4

import bcrypt
import pytest
from pydantic import ValidationError

from giljo_mcp.auth.jwt_manager import JWTManager


OLD_PASSWORD = "OldPassword1!"
RECOVERY_PIN = "4242"

# 100 chars = 100 UTF-8 bytes: inside the old advertised 128-char cap, over bcrypt's 72.
LONG_ASCII_100 = "Aa1!" + "x" * 96
# 24 chars but 4 + 20*4 = 84 UTF-8 bytes: fits ANY character cap, over bcrypt's 72 bytes.
EMOJI_OVER_72_BYTES = "Aa1!" + "\U0001f600" * 20
# Boundary passes: exactly 72 bytes, ASCII (72 chars) and multibyte (21 chars).
EXACT_72_BYTES_ASCII = "Aa1!" + "x" * 68
EXACT_72_BYTES_EMOJI = "Aa1!" + "\U0001f600" * 17

OVERSIZED = [LONG_ASCII_100, EMOJI_OVER_72_BYTES]
EXACTLY_72 = [EXACT_72_BYTES_ASCII, EXACT_72_BYTES_EMOJI]

_CSRF = secrets.token_urlsafe(32)


def test_password_constants_byte_math():
    """Guard the fixture math the whole module leans on."""
    assert len(LONG_ASCII_100) == 100 and len(LONG_ASCII_100.encode("utf-8")) == 100
    assert len(EMOJI_OVER_72_BYTES) <= 72 and len(EMOJI_OVER_72_BYTES.encode("utf-8")) == 84
    assert len(EXACT_72_BYTES_ASCII.encode("utf-8")) == 72
    assert len(EXACT_72_BYTES_EMOJI) <= 72 and len(EXACT_72_BYTES_EMOJI.encode("utf-8")) == 72


# ---------------------------------------------------------------------------
# Route helpers (sec9047/sec9084 pattern)
# ---------------------------------------------------------------------------


async def _seed_user(db_manager, *, with_pin: bool = False, must_change_password: bool = False) -> tuple[str, str, str]:
    """Create org+user; return (user_id, username, tenant_key)."""
    from giljo_mcp.models.auth import User
    from giljo_mcp.models.organizations import Organization
    from giljo_mcp.tenant import TenantManager

    tk = TenantManager.generate_tenant_key()
    unique = uuid4().hex[:8]
    user_id = str(uuid4())
    username = f"be9176_user_{unique}"

    async with db_manager.get_session_async(tenant_key=tk) as session:
        org = Organization(
            name=f"BE9176 Org {unique}",
            slug=f"be9176-org-{unique}",
            tenant_key=tk,
            is_active=True,
        )
        session.add(org)
        await session.flush()
        session.add(
            User(
                id=user_id,
                username=username,
                email=f"be9176_{unique}@example.com",
                password_hash=bcrypt.hashpw(OLD_PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
                recovery_pin_hash=(
                    bcrypt.hashpw(RECOVERY_PIN.encode("utf-8"), bcrypt.gensalt()).decode("utf-8") if with_pin else None
                ),
                tenant_key=tk,
                role="developer",
                org_id=org.id,
                is_active=True,
                token_revocation_epoch=0,
                must_change_password=must_change_password,
                must_set_pin=False,
            )
        )
        await session.commit()

    return user_id, username, tk


def _cookie_headers(token: str) -> dict:
    """Cookie-auth headers with the CSRF double-submit pair (conftest pattern)."""
    return {
        "Cookie": f"access_token={token}; csrf_token={_CSRF}",
        "X-CSRF-Token": _CSRF,
    }


def _mint(user_id: str, username: str, tenant_key: str) -> str:
    return JWTManager.create_access_token(
        user_id=user_id,
        username=username,
        role="developer",
        tenant_key=tenant_key,
        revocation_epoch=0,
    )


class _NoopRateLimiter:
    async def check_rate_limit(self, *args, **kwargs):
        return None


def _pin_route_patches(monkeypatch) -> None:
    """CE-mode + rate-limit-free PIN recovery route (sec9047 pattern, parallel-safe)."""
    monkeypatch.setattr("api.endpoints.auth_pin_recovery.GILJO_MODE", "")
    monkeypatch.setattr("api.endpoints.auth_pin_recovery.get_rate_limiter", _NoopRateLimiter)


async def _persisted_password_hash(db_manager, *, tenant_key: str, user_id: str) -> str:
    from giljo_mcp.models.auth import User

    async with db_manager.get_session_async(tenant_key=tenant_key) as session:
        user = await session.get(User, user_id)
        return user.password_hash


# ---------------------------------------------------------------------------
# RED: change-password route (PUT /api/v1/users/{id}/password) — was a 500
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_password", OVERSIZED, ids=["ascii-100", "emoji-84-bytes"])
async def test_change_password_route_over_72_bytes_is_422(api_client, db_manager, monkeypatch, bad_password):
    """A >72-UTF-8-byte new password on the change-password route is a 422, not a 500."""
    monkeypatch.setenv("JWT_SECRET", "test_secret_key")
    user_id, username, tk = await _seed_user(db_manager)

    resp = await api_client.put(
        f"/api/v1/users/{user_id}/password",
        json={"old_password": OLD_PASSWORD, "new_password": bad_password},
        headers=_cookie_headers(_mint(user_id, username, tk)),
    )
    assert resp.status_code == 422, f"expected 422, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_change_password_route_exactly_72_bytes_succeeds(api_client, db_manager, monkeypatch):
    """Boundary GREEN: exactly-72-byte password changes fine and is the persisted credential."""
    monkeypatch.setenv("JWT_SECRET", "test_secret_key")
    user_id, username, tk = await _seed_user(db_manager)

    resp = await api_client.put(
        f"/api/v1/users/{user_id}/password",
        json={"old_password": OLD_PASSWORD, "new_password": EXACT_72_BYTES_ASCII},
        headers=_cookie_headers(_mint(user_id, username, tk)),
    )
    assert resp.status_code == 200, resp.text

    password_hash = await _persisted_password_hash(db_manager, tenant_key=tk, user_id=user_id)
    assert bcrypt.checkpw(EXACT_72_BYTES_ASCII.encode("utf-8"), password_hash.encode("utf-8"))
    assert not bcrypt.checkpw(OLD_PASSWORD.encode("utf-8"), password_hash.encode("utf-8"))


# ---------------------------------------------------------------------------
# RED: CE recovery-PIN reset route — was a 500
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_password", OVERSIZED, ids=["ascii-100", "emoji-84-bytes"])
async def test_pin_reset_route_over_72_bytes_is_422(api_client, db_manager, monkeypatch, bad_password):
    """A valid PIN with a >72-byte new password is a 422 at validation, not a 500 at the hash."""
    monkeypatch.setenv("JWT_SECRET", "test_secret_key")
    _pin_route_patches(monkeypatch)
    _, username, _ = await _seed_user(db_manager, with_pin=True)

    resp = await api_client.post(
        "/api/auth/verify-pin-and-reset-password",
        json={
            "username": username,
            "recovery_pin": RECOVERY_PIN,
            "new_password": bad_password,
            "confirm_password": bad_password,
        },
    )
    assert resp.status_code == 422, f"expected 422, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_pin_reset_route_exactly_72_bytes_succeeds(api_client, db_manager, monkeypatch):
    """Boundary GREEN: a 72-byte multibyte password resets fine through the PIN route."""
    monkeypatch.setenv("JWT_SECRET", "test_secret_key")
    _pin_route_patches(monkeypatch)
    user_id, username, tk = await _seed_user(db_manager, with_pin=True)

    resp = await api_client.post(
        "/api/auth/verify-pin-and-reset-password",
        json={
            "username": username,
            "recovery_pin": RECOVERY_PIN,
            "new_password": EXACT_72_BYTES_EMOJI,
            "confirm_password": EXACT_72_BYTES_EMOJI,
        },
    )
    assert resp.status_code == 200, resp.text

    password_hash = await _persisted_password_hash(db_manager, tenant_key=tk, user_id=user_id)
    assert bcrypt.checkpw(EXACT_72_BYTES_EMOJI.encode("utf-8"), password_hash.encode("utf-8"))


# ---------------------------------------------------------------------------
# RED: first-login password-set route — was a 500
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_password", OVERSIZED, ids=["ascii-100", "emoji-84-bytes"])
async def test_complete_first_login_over_72_bytes_is_422(api_client, db_manager, monkeypatch, bad_password):
    """A >72-byte first-login password is a 422, not a 500."""
    monkeypatch.setenv("JWT_SECRET", "test_secret_key")
    user_id, username, tk = await _seed_user(db_manager, must_change_password=True)

    resp = await api_client.post(
        "/api/auth/complete-first-login",
        json={
            "current_password": OLD_PASSWORD,
            "new_password": bad_password,
            "confirm_password": bad_password,
        },
        headers=_cookie_headers(_mint(user_id, username, tk)),
    )
    assert resp.status_code == 422, f"expected 422, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# Schema layer: every CE password-set schema rejects >72 bytes, accepts ==72
# (register endpoints are gated pre-hash, so this IS their failing layer)
# ---------------------------------------------------------------------------


def _schema_cases():
    from api.endpoints.auth.models import PasswordChangeRequest, RegisterUserRequest
    from api.endpoints.auth_models import CompleteFirstLoginRequest, PinPasswordResetRequest
    from api.endpoints.users import PasswordChange, UserCreate, UserUpdate

    def build(schema, password):
        if schema is UserCreate:
            return schema(username="be9176user", password=password)
        if schema is UserUpdate:
            return schema(password=password)
        if schema is PasswordChange:
            return schema(old_password=OLD_PASSWORD, new_password=password)
        if schema is RegisterUserRequest:
            return schema(username="be9176user", password=password)
        if schema is PinPasswordResetRequest:
            return schema(
                username="be9176user",
                recovery_pin=RECOVERY_PIN,
                new_password=password,
                confirm_password=password,
            )
        if schema is CompleteFirstLoginRequest:
            return schema(current_password=OLD_PASSWORD, new_password=password, confirm_password=password)
        if schema is PasswordChangeRequest:
            return schema(current_password=OLD_PASSWORD, new_password=password, confirm_password=password)
        raise AssertionError(f"unmapped schema {schema}")

    schemas = [
        UserCreate,
        UserUpdate,
        PasswordChange,
        RegisterUserRequest,
        PinPasswordResetRequest,
        CompleteFirstLoginRequest,
        PasswordChangeRequest,
    ]
    return build, schemas


@pytest.mark.parametrize("bad_password", OVERSIZED, ids=["ascii-100", "emoji-84-bytes"])
def test_all_password_set_schemas_reject_over_72_bytes(bad_password):
    build, schemas = _schema_cases()
    for schema in schemas:
        with pytest.raises(ValidationError):
            build(schema, bad_password)


@pytest.mark.parametrize("good_password", EXACTLY_72, ids=["ascii-72", "emoji-72-bytes"])
def test_all_password_set_schemas_accept_exactly_72_bytes(good_password):
    build, schemas = _schema_cases()
    for schema in schemas:
        built = build(schema, good_password)
        assert built is not None, schema.__name__
