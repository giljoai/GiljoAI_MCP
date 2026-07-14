# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Endpoint-layer regression test for BE-6019.

Bug: ``GET /api/download/temp/{token}/{filename}`` (the public token download
that serves ``giljo_setup`` zips) returned HTTP 500 under the fail-closed tenant
guard. The endpoint served the file fine, then called
``TokenManager.increment_download_count(token)`` -- a metrics counter bump that
ran a plain ORM statement on ``DownloadToken`` with NO tenant context. The guard
(``_enforce_tenant_scope``) raised ``TenantIsolationError`` and the unhandled
exception became a 500, breaking every token download on test.giljo.ai / any
SaaS deploy running in enforce mode.

Fix (two parts):
1. ``increment_download_count`` takes the already-resolved ``tenant_key`` and
   runs inside ``tenant_session_context`` so the write is a properly
   tenant-scoped query -- no isolation bypass (the caller resolved the tenant
   from the token row, so the context is known and honest).
2. The endpoint wraps the metrics increment fire-and-forget so a non-critical
   metrics failure can never fail an otherwise-successful download.

This test exercises the FAILING layer -- the real HTTP download endpoint through
FastAPI DI via the ASGI client, under enforce guard mode -- per the CLAUDE.md
failing-layer rule (BE-5042 lesson).

Parallel-safe: every test seeds its own unique tenant + token UUID and stages
into a unique ``temp/<tenant>/<token>/`` dir cleaned up in teardown; guard mode
is set via ``monkeypatch.setenv``; no module-level mutable state; no ordering
dependency.

Project: BE-6019.
"""

from __future__ import annotations

import shutil
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient

from giljo_mcp.models import DownloadToken
from giljo_mcp.tenant import TenantManager


_FILENAME = "giljo_setup.zip"
_ZIP_BYTES = b"PK\x03\x04 fake-but-non-empty zip payload for the regression test"


async def _seed_ready_token(db_manager) -> dict:
    """Create a ready DownloadToken in a fresh tenant + stage its file on disk."""
    tenant_key = TenantManager.generate_tenant_key()
    token = str(uuid.uuid4())

    async with db_manager.get_session_async() as session:
        session.add(
            DownloadToken(
                token=token,
                tenant_key=tenant_key,
                download_type="slash_commands",
                filename=_FILENAME,
                staging_status="ready",
                download_count=0,
                expires_at=datetime.now(UTC) + timedelta(minutes=15),
            )
        )
        await session.commit()

    # The endpoint computes the path as cwd()/temp/<tenant>/<token>/<filename>.
    staged_dir = Path.cwd() / "temp" / tenant_key / token
    staged_dir.mkdir(parents=True, exist_ok=True)
    (staged_dir / _FILENAME).write_bytes(_ZIP_BYTES)

    return {
        "tenant_key": tenant_key,
        "token": token,
        "url": f"/api/download/temp/{token}/{_FILENAME}",
        "tenant_dir": Path.cwd() / "temp" / tenant_key,
    }


@pytest_asyncio.fixture(scope="function")
async def staged_token(db_manager):
    seeded = await _seed_ready_token(db_manager)
    try:
        yield seeded
    finally:
        shutil.rmtree(seeded["tenant_dir"], ignore_errors=True)


@pytest.mark.asyncio
async def test_temp_download_returns_200_under_enforce_guard(
    api_client: AsyncClient, db_manager, staged_token: dict, monkeypatch
) -> None:
    """Regression: token download succeeds under enforce mode (was 500).

    Before BE-6019 the metrics increment ran without tenant context and the
    fail-closed guard raised TenantIsolationError -> 500. After the fix the write
    is tenant-scoped and the download returns the staged bytes.
    """
    monkeypatch.setenv("GILJO_TENANT_GUARD_MODE", "enforce")

    resp = await api_client.get(staged_token["url"])

    assert resp.status_code == 200, resp.text
    assert resp.content == _ZIP_BYTES
    assert resp.headers["content-type"] == "application/zip"

    # The tenant-scoped metrics write actually committed (proves it ran, not bypassed).
    async with db_manager.get_session_async() as session:
        from sqlalchemy import select

        from giljo_mcp.database import tenant_session_context

        with tenant_session_context(session, staged_token["tenant_key"]):
            row = (
                await session.execute(select(DownloadToken).where(DownloadToken.token == staged_token["token"]))
            ).scalar_one()
        assert row.download_count == 1
        assert row.last_downloaded_at is not None


@pytest.mark.asyncio
async def test_temp_download_survives_metrics_failure(api_client: AsyncClient, staged_token: dict, monkeypatch) -> None:
    """Resilience: a failing metrics increment must NOT fail the download.

    Even if the counter bump blows up for any reason, the file is already read
    and ready -- the user must still get a 200 with the payload.
    """
    monkeypatch.setenv("GILJO_TENANT_GUARD_MODE", "enforce")

    from giljo_mcp.download_tokens import TokenManager

    async def _boom(self, token, tenant_key):  # noqa: ANN001 - test stub
        raise RuntimeError("simulated metrics backend failure")

    monkeypatch.setattr(TokenManager, "increment_download_count", _boom)

    resp = await api_client.get(staged_token["url"])

    assert resp.status_code == 200, resp.text
    assert resp.content == _ZIP_BYTES
