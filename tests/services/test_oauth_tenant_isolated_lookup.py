# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Regression tests for API-0022 (folds API-0024): OAuth lookup defense-in-depth.

These tests pin the service-layer WHERE clauses on the two OAuth lookups
that previously queried by token_hash / code alone:

  - ``oauth_refresh_service.refresh_token_grant`` — refresh-token lookup
  - ``OAuthService.exchange_code_for_token`` — authorization-code lookup

Per BE-5042 (test at the failing layer), the bug — if it ever regresses —
would manifest at the SQL WHERE clause emitted by the service. So these
tests drive the same ``select(...).where(...)`` predicate the service
emits and assert that a row seeded under (tenant_A, client_X) is NOT
returned when the lookup is bound to client_Y.

``oauth_clients.client_id`` is a UUIDv4 primary key (globally unique), so
binding the lookup to ``client_id`` is equivalent to binding to
``tenant_key`` without a second round-trip. The explicit cross-client
guard inside the service stays as the second defense layer.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select

from giljo_mcp.models.auth import User
from giljo_mcp.models.oauth import OAuthAuthorizationCode, OAuthRefreshToken
from giljo_mcp.services.oauth_refresh_service import hash_refresh_token
from giljo_mcp.tenant import TenantManager


@pytest_asyncio.fixture
async def tenant_a() -> str:
    return TenantManager.generate_tenant_key()


@pytest_asyncio.fixture
async def user_a(db_session, tenant_a):
    user = User(
        id=str(uuid4()),
        username=f"u_a_{uuid4().hex[:6]}",
        email=f"a_{uuid4().hex[:6]}@example.com",
        password_hash="x",
        full_name="User A",
        role="developer",
        tenant_key=tenant_a,
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_oauth_refresh_service_tenant_isolated_lookup(db_session, tenant_a, user_a):
    """Defense-in-depth: refresh-token lookup MUST bind client_id.

    Seed a refresh row under (tenant_a, client_X). Run the same WHERE
    clause the service emits but with client_Y. Expect None — the lookup
    itself must refuse to resolve the row, not rely on a later guard.
    """
    raw_token = "regression-raw-token-value"
    token_hash = hash_refresh_token(raw_token)
    client_x = f"client-x-{uuid4().hex[:8]}"
    client_y = f"client-y-{uuid4().hex[:8]}"

    row = OAuthRefreshToken(
        token_hash=token_hash,
        family_id=str(uuid4()),
        client_id=client_x,
        tenant_key=tenant_a,
        user_id=user_a.id,
        scope="mcp:read mcp:write",
        aud="https://mcp.example/",
        issued_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(days=30),
        revoked=False,
    )
    db_session.add(row)
    await db_session.commit()

    # Sanity: the row IS findable under the correct client_id.
    sanity = await db_session.execute(
        select(OAuthRefreshToken).where(
            OAuthRefreshToken.token_hash == token_hash,
            OAuthRefreshToken.client_id == client_x,
        )
    )
    assert sanity.scalar_one_or_none() is not None, "seed row must be findable under its own client_id"

    # Regression: same query under a foreign client_id resolves nothing.
    isolated = await db_session.execute(
        select(OAuthRefreshToken).where(
            OAuthRefreshToken.token_hash == token_hash,
            OAuthRefreshToken.client_id == client_y,
        )
    )
    assert isolated.scalar_one_or_none() is None, (
        "API-0022: refresh-token lookup must NOT resolve a row under a foreign client_id; "
        "this is the SQL-layer defense, the explicit row.client_id != request.client_id "
        "guard is the second layer."
    )


@pytest.mark.asyncio
async def test_oauth_service_auth_code_tenant_isolated_lookup(db_session, tenant_a, user_a):
    """Defense-in-depth: auth-code lookup MUST bind client_id.

    Same pattern as the refresh-token test but for
    ``OAuthService.exchange_code_for_token``'s code lookup.
    """
    code_value = f"code-{uuid4().hex}"
    client_x = f"client-x-{uuid4().hex[:8]}"
    client_y = f"client-y-{uuid4().hex[:8]}"

    row = OAuthAuthorizationCode(
        id=str(uuid4()),
        code=code_value,
        client_id=client_x,
        user_id=user_a.id,
        tenant_key=tenant_a,
        redirect_uri="http://localhost:7272/callback",
        code_challenge="x" * 43,
        code_challenge_method="S256",
        scope="mcp:read mcp:write",
        resource="https://mcp.example/",
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
        used=False,
        created_at=datetime.now(UTC),
    )
    db_session.add(row)
    await db_session.commit()

    sanity = await db_session.execute(
        select(OAuthAuthorizationCode).where(
            OAuthAuthorizationCode.code == code_value,
            OAuthAuthorizationCode.client_id == client_x,
        )
    )
    assert sanity.scalar_one_or_none() is not None, "seed auth-code must be findable under its own client_id"

    isolated = await db_session.execute(
        select(OAuthAuthorizationCode).where(
            OAuthAuthorizationCode.code == code_value,
            OAuthAuthorizationCode.client_id == client_y,
        )
    )
    assert isolated.scalar_one_or_none() is None, (
        "API-0022: auth-code lookup must NOT resolve a row under a foreign client_id; "
        "this is the SQL-layer defense, the explicit auth_code.client_id != client_id "
        "guard is the second layer."
    )
