# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Regression tests for the two fresh-install first-run defects found by the
INF-6174d chain-validation capstone (both reproduced live on a throwaway DB).

Defect 1 — taxonomy seeding missing on the resolve path:
    On a fresh tenant the FIRST typed ``create_project`` resolved its
    ``project_type`` against an EMPTY taxonomy table and failed with
    "Unknown project type 'INF'. Valid types: ... INF ..." — the error's own
    valid_types list was seeded while rendering the error
    (``_get_valid_project_types`` seeds lazily), so the retry succeeded.
    Fix: ``get_project_type_by_label`` seeds the defaults before resolving.

Defect 2 — ``create_first_admin`` was not failure-atomic:
    The admin row + org + memberships were COMMITTED before the login JWT was
    minted. The endpoint is one-shot (locked once any user exists), so a
    token-mint failure (reproduced live: JWT secret missing from the
    environment) stranded a half-bootstrapped install: user committed,
    endpoint disabled, agent templates never seeded, no retry path.
    Fix: the JWT is minted BEFORE the first DB write, so the same failure now
    aborts cleanly and the endpoint stays retryable.
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select

from giljo_mcp.auth.jwt_manager import JWTManager
from giljo_mcp.exceptions import BaseGiljoError
from giljo_mcp.models.auth import User
from giljo_mcp.repositories.auth_repository import AuthRepository
from giljo_mcp.services.auth_service import AuthService


@pytest_asyncio.fixture
async def auth_service(db_manager, db_session):
    return AuthService(db_manager=db_manager, websocket_manager=None, session=db_session)


class TestTypeResolutionSeedsFreshTenant:
    """Defect 1: the resolve path must seed defaults on a fresh tenant."""

    @pytest.mark.asyncio
    async def test_first_typed_lookup_on_fresh_tenant_resolves(self, project_service_with_session):
        """A brand-new tenant's FIRST lookup of a default abbreviation succeeds.

        Pre-fix this returned None (empty taxonomy table -> create_project
        raised "Unknown project type" while listing the same type as valid).
        """
        fresh_tenant = f"tk_{uuid4().hex}"
        result = await project_service_with_session.get_project_type_by_label("INF", fresh_tenant)
        assert result is not None, "first typed resolve on a fresh tenant must seed the defaults and match"
        assert result.abbreviation == "INF"
        assert result.tenant_key == fresh_tenant

    @pytest.mark.asyncio
    async def test_reserved_types_still_rejected_on_fresh_tenant(self, project_service_with_session):
        """Seeding-on-resolve must not weaken the reserved TSK/CHT rejection."""
        fresh_tenant = f"tk_{uuid4().hex}"
        assert await project_service_with_session.get_project_type_by_label("TSK", fresh_tenant) is None
        assert await project_service_with_session.get_project_type_by_label("CHT", fresh_tenant) is None


class TestFirstAdminFailureAtomicity:
    """Defect 2: a token-mint failure must leave NO user row behind."""

    @pytest.mark.asyncio
    async def test_token_mint_failure_writes_nothing_and_stays_retryable(self, auth_service, db_session, monkeypatch):
        username = f"first_admin_{uuid4().hex[:8]}"

        # Fresh-install precondition (the shared test DB has other tenants' users).
        monkeypatch.setattr(AuthRepository, "get_total_user_count", staticmethod(_zero_users))

        # Reproduce the live failure: JWT secret missing -> mint raises.
        def _mint_raises(**_kwargs):
            raise RuntimeError("JWT secret key not found in environment variables (simulated)")

        monkeypatch.setattr(JWTManager, "create_access_token", staticmethod(_mint_raises))

        with pytest.raises(BaseGiljoError):
            await auth_service.create_first_admin(
                username=username, email=None, password="SecureAdmin123!@#", full_name=None
            )

        # The failure must be a clean abort: no half-bootstrapped admin row.
        from giljo_mcp.database import tenant_isolation_bypass

        with tenant_isolation_bypass(
            db_session,
            reason="regression test verifies NO admin row survived the aborted bootstrap",
            models=(User,),
        ):
            result = await db_session.execute(select(User).where(User.username == username))
        assert result.scalar_one_or_none() is None, (
            "token-mint failure left a committed admin row — create_first_admin regressed to non-atomic"
        )

    @pytest.mark.asyncio
    async def test_retry_after_mint_failure_succeeds(self, auth_service, db_session, monkeypatch):
        username = f"first_admin_{uuid4().hex[:8]}"
        monkeypatch.setattr(AuthRepository, "get_total_user_count", staticmethod(_zero_users))

        real_mint = JWTManager.create_access_token
        calls = {"n": 0}

        def _fail_once_then_work(**kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("JWT secret key not found (simulated, first attempt)")
            return real_mint(**kwargs)

        monkeypatch.setattr(JWTManager, "create_access_token", staticmethod(_fail_once_then_work))

        with pytest.raises(BaseGiljoError):
            await auth_service.create_first_admin(
                username=username, email=None, password="SecureAdmin123!@#", full_name=None
            )

        # Operator fixes the secret and simply retries — the pre-fix code path
        # could never reach here (the first call had already burned the one-shot).
        result = await auth_service.create_first_admin(
            username=username, email=None, password="SecureAdmin123!@#", full_name=None
        )
        assert result.username == username
        assert result.token


async def _zero_users(_session):
    return 0
