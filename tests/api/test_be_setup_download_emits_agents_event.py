# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Endpoint-layer regression test: setup downloads emit setup:agents_downloaded.

Bug: ``GET /api/download/temp/{token}/{filename}`` only emitted a WebSocket
event when the served file was ``slash_commands.zip``. The ``giljo_setup`` tool
actually serves a COMBINED zip named ``giljo_setup.zip`` (slash commands + agent
templates), and the agent-only refresh path serves ``agent_templates.zip`` --
neither matched the single ``== "slash_commands.zip"`` branch, so NO
``setup:agents_downloaded`` event was broadcast. The open Agent Template Manager
(``/settings?tab=agents``) listens for that event to clear its "templates
expired" markers in real time; with no event, the markers only cleared after a
manual page refresh.

Fix: the endpoint emits ``setup:agents_downloaded`` for both ``giljo_setup.zip``
(combined -- plus ``setup:commands_installed``) and ``agent_templates.zip``.

This test exercises the FAILING layer -- the real HTTP download endpoint through
FastAPI DI via the ASGI client -- per the CLAUDE.md failing-layer rule
(BE-5042 lesson). It asserts on the events handed to the websocket manager's
``broadcast_event_to_tenant``.

Parallel-safe: each test seeds its own unique tenant + token UUID, stages into a
unique ``temp/<tenant>/<token>/`` dir cleaned up in teardown, and swaps in its
own websocket-manager stub on ``app.state`` restored in teardown. No
module-level mutable state; no ordering dependency.

Edition Scope: CE.
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


_ZIP_BYTES = b"PK\x03\x04 fake-but-non-empty zip payload for the regression test"


class _RecordingWsManager:
    """Captures every event passed to broadcast_event_to_tenant."""

    def __init__(self) -> None:
        self.events: list[dict] = []

    async def broadcast_event_to_tenant(self, *, tenant_key: str, event: dict) -> None:  # noqa: ARG002
        self.events.append(event)


def _event_types(ws: _RecordingWsManager) -> list[str]:
    return [e.get("type") or e.get("event_type") for e in ws.events]


async def _seed_ready_token(db_manager, filename: str) -> dict:
    """Create a ready DownloadToken in a fresh tenant + stage its file on disk."""
    tenant_key = TenantManager.generate_tenant_key()
    token = str(uuid.uuid4())

    async with db_manager.get_session_async() as session:
        session.add(
            DownloadToken(
                token=token,
                tenant_key=tenant_key,
                download_type="slash_commands",
                filename=filename,
                staging_status="ready",
                download_count=0,
                expires_at=datetime.now(UTC) + timedelta(minutes=15),
            )
        )
        await session.commit()

    # The endpoint computes the path as cwd()/temp/<tenant>/<token>/<filename>.
    staged_dir = Path.cwd() / "temp" / tenant_key / token
    staged_dir.mkdir(parents=True, exist_ok=True)
    (staged_dir / filename).write_bytes(_ZIP_BYTES)

    return {
        "tenant_key": tenant_key,
        "token": token,
        "filename": filename,
        "url": f"/api/download/temp/{token}/{filename}",
        "tenant_dir": Path.cwd() / "temp" / tenant_key,
    }


@pytest_asyncio.fixture(scope="function")
async def recording_ws():
    """Swap a recording websocket manager onto the shared app, restore after."""
    from api.app import app

    prior = getattr(app.state, "websocket_manager", None)
    ws = _RecordingWsManager()
    app.state.websocket_manager = ws
    try:
        yield ws
    finally:
        app.state.websocket_manager = prior


@pytest.mark.asyncio
async def test_combined_setup_zip_emits_agents_downloaded(
    api_client: AsyncClient, db_manager, recording_ws: _RecordingWsManager
) -> None:
    """Regression: downloading giljo_setup.zip emits setup:agents_downloaded.

    Before the fix the combined zip matched no branch and emitted nothing, so the
    Agent Template Manager never cleared its stale markers without a refresh.
    """
    seeded = await _seed_ready_token(db_manager, "giljo_setup.zip")
    try:
        resp = await api_client.get(seeded["url"])
        assert resp.status_code == 200, resp.text
        assert resp.content == _ZIP_BYTES

        types = _event_types(recording_ws)
        # Combined zip carries BOTH commands and agents.
        assert "setup:agents_downloaded" in types, types
        assert "setup:commands_installed" in types, types

        agent_evt = next(e for e in recording_ws.events if (e.get("type") == "setup:agents_downloaded"))
        assert agent_evt["data"]["tenant_key"] == seeded["tenant_key"]
    finally:
        shutil.rmtree(seeded["tenant_dir"], ignore_errors=True)


@pytest.mark.asyncio
async def test_agent_templates_zip_emits_agents_downloaded(
    api_client: AsyncClient, db_manager, recording_ws: _RecordingWsManager
) -> None:
    """The dedicated agent-only zip emits agents_downloaded (not commands)."""
    seeded = await _seed_ready_token(db_manager, "agent_templates.zip")
    try:
        resp = await api_client.get(seeded["url"])
        assert resp.status_code == 200, resp.text

        types = _event_types(recording_ws)
        assert "setup:agents_downloaded" in types, types
        assert "setup:commands_installed" not in types, types
    finally:
        shutil.rmtree(seeded["tenant_dir"], ignore_errors=True)


@pytest.mark.asyncio
async def test_slash_commands_zip_still_emits_only_commands(
    api_client: AsyncClient, db_manager, recording_ws: _RecordingWsManager
) -> None:
    """Guard: the pre-existing slash_commands.zip behaviour is unchanged."""
    seeded = await _seed_ready_token(db_manager, "slash_commands.zip")
    try:
        resp = await api_client.get(seeded["url"])
        assert resp.status_code == 200, resp.text

        types = _event_types(recording_ws)
        assert "setup:commands_installed" in types, types
        assert "setup:agents_downloaded" not in types, types
    finally:
        shutil.rmtree(seeded["tenant_dir"], ignore_errors=True)
