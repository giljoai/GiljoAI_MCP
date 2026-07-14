# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-8000i regression test: OAuth expired-code reaper actually runs.

``OAuthService.cleanup_expired_codes`` existed and was correct but had ZERO
production callers -- ``exchange_code_for_token`` only flips ``used=True`` on
a code (never deletes it), and ``generate_authorization_code`` inserts a new
row per ``/authorize`` call, so ``oauth_authorization_codes`` grew unbounded.

This exercises the REGISTERED background task
(``oauth_code_reaper.cleanup_expired_oauth_codes_task``), not just the
underlying service method, against a session with NO ambient tenant context --
exactly the
topology the real background-task loop uses (a fresh
``db_manager.get_session_async()`` call with nothing flushed on it yet).
Before this fix, the cross-tenant DELETE inside
``OAuthService.cleanup_expired_codes`` had no tenant-isolation bypass, so the
fail-closed guard would raise ``TenantIsolationError`` the moment this task
ever actually ran -- the same dead-reaper pattern BE-3011 fixed for
``cleanup_expired_mcp_sessions_task``. Reverting the bypass makes this test
fail with that exact error, which is what makes it a genuine regression guard
rather than a happy-path smoke test.

``TransactionalTestContext`` (``db_session``) binds one connection per test, so
a second, genuinely separate ``db_manager.get_session_async()`` connection
cannot see this test's uncommitted rows. ``_BareSessionManager`` below stands
in for ``state.db_manager``: it hands back the SAME ``db_session`` (so seeded
rows stay visible) but strips any ambient tenant context first, reproducing
the one property that actually matters -- a session that has nothing on it
yet.

Parallel-safe: TransactionalTestContext (``db_session``) for setup and the
task call, random tenant/user ids, no module-level mutable state, no test-
ordering deps.
"""

import asyncio
import types
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from api.startup import oauth_code_reaper
from giljo_mcp.database import TENANT_CONTEXT_SOURCE_KEY, tenant_isolation_bypass
from giljo_mcp.models.auth import User
from giljo_mcp.models.oauth import OAuthAuthorizationCode


class _BareSessionManager:
    """Stand-in for ``state.db_manager``: yields the given session with its
    ambient tenant context stripped, mirroring a session with nothing flushed
    on it yet (the real background-task topology)."""

    def __init__(self, session):
        self._session = session

    @asynccontextmanager
    async def get_session_async(self):
        self._session.info.pop("tenant_key", None)
        self._session.info.pop(TENANT_CONTEXT_SOURCE_KEY, None)
        yield self._session


async def _seed_user_and_code(session, *, tenant_key: str, expires_at: datetime, used: bool) -> str:
    """Insert a User + OAuthAuthorizationCode row and COMMIT.

    The commit must be durable across connections: the task under test opens
    its OWN separate session/connection (mirroring the real background loop),
    which will only see this row if it was actually committed here.
    """
    user_id = str(uuid4())
    code = f"code_{uuid4().hex}"
    with tenant_isolation_bypass(session, reason="test setup: seed oauth code", models=(User, OAuthAuthorizationCode)):
        session.add(
            User(
                id=user_id,
                username=f"oauth_reaper_{uuid4().hex[:8]}",
                email=f"oauth_reaper_{uuid4().hex[:8]}@example.com",
                role="developer",
                tenant_key=tenant_key,
                is_active=True,
                is_system_user=False,
                must_change_password=False,
                must_set_pin=False,
                failed_pin_attempts=0,
            )
        )
        session.add(
            OAuthAuthorizationCode(
                id=str(uuid4()),
                code=code,
                client_id="giljo-mcp-default",
                user_id=user_id,
                tenant_key=tenant_key,
                redirect_uri="http://localhost:3000/callback",
                code_challenge="challenge",
                code_challenge_method="S256",
                expires_at=expires_at,
                used=used,
            )
        )
        await session.flush()
    await session.commit()
    return code


def _single_iteration_sleep():
    """Fake ``asyncio.sleep`` letting the reaper's ``while True`` loop run its
    body exactly once, then raise ``CancelledError`` on the loop's second
    sleep so the infinite task exits cleanly after one iteration."""
    calls = {"n": 0}

    async def _fake_sleep(_seconds):
        calls["n"] += 1
        if calls["n"] > 1:
            raise asyncio.CancelledError

    return _fake_sleep


@pytest.mark.asyncio
class TestOAuthCodeReaperTask:
    async def test_registered_task_deletes_expired_and_used_codes(self, monkeypatch, db_session):
        """Two-sided: expired + used codes are removed; a valid unused code
        survives -- exercised through the REGISTERED asyncio task, against a
        session with no ambient tenant context (the real bug's failure mode).
        """
        now = datetime.now(UTC)
        tenant = f"t_{uuid4().hex[:8]}"

        expired_code = await _seed_user_and_code(
            db_session, tenant_key=tenant, expires_at=now - timedelta(minutes=5), used=False
        )
        used_code = await _seed_user_and_code(
            db_session, tenant_key=tenant, expires_at=now + timedelta(minutes=10), used=True
        )
        valid_code = await _seed_user_and_code(
            db_session, tenant_key=tenant, expires_at=now + timedelta(minutes=10), used=False
        )

        monkeypatch.setattr(oauth_code_reaper.asyncio, "sleep", _single_iteration_sleep())
        state = types.SimpleNamespace(db_manager=_BareSessionManager(db_session))

        with pytest.raises(asyncio.CancelledError):
            await oauth_code_reaper.cleanup_expired_oauth_codes_task(state)

        with tenant_isolation_bypass(
            db_session, reason="test assert: read remaining oauth codes", models=(OAuthAuthorizationCode,)
        ):
            remaining = (
                (
                    await db_session.execute(
                        select(OAuthAuthorizationCode.code).where(OAuthAuthorizationCode.tenant_key == tenant)
                    )
                )
                .scalars()
                .all()
            )

        assert expired_code not in remaining
        assert used_code not in remaining
        assert valid_code in remaining  # load-bearing half: untouched codes survive

    async def test_registered_task_is_a_noop_without_a_db_manager(self, monkeypatch):
        """``state.db_manager is None`` (e.g. mid-shutdown) must not raise."""
        monkeypatch.setattr(oauth_code_reaper.asyncio, "sleep", _single_iteration_sleep())
        state = types.SimpleNamespace(db_manager=None)

        with pytest.raises(asyncio.CancelledError):
            await oauth_code_reaper.cleanup_expired_oauth_codes_task(state)
