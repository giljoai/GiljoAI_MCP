# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-9208 D1 — serve-layer regression: staged ZIP serves a pre-change snapshot.

Bug: ``giljo_setup`` / bootstrap stages the combined ZIP to
``temp/{tenant}/{token}/`` AT CALL TIME (querying the DB then). The public
``GET /api/download/temp/{token}/{filename}`` endpoint later serves those FROZEN
bytes and never re-checks the DB. A template created/edited AFTER staging is
never reflected in an already-staged token's ZIP, so a reused/old download URL
serves a stale snapshot (the live incident: a tenant's new user templates were
missing while the ZIP carried only the pre-change defaults). The Codex path
assembles live per request, which is why it "worked".

STALENESS GUARANTEE (BE-9208 D1, EM-ratified): a 200 token download for a
template-bearing ZIP NEVER carries template content older than the tenant's
latest template write; a stale snapshot returns 410 Gone (re-run giljo_setup)
rather than serving frozen bytes. Static slash-commands ZIPs are untouched.

Two-sided: `test_..._stale_snapshot` proves a post-staging write ⇒ 410 (was 200
with frozen bytes pre-fix); `test_..._fresh_token_still_served` proves the guard
does NOT break the normal flow (no post-staging write ⇒ 200 with content).

Exercises the FAILING layer — the real HTTP token-download endpoint through
FastAPI DI via the ASGI client — per the failing-layer rule.

Parallel-safe: each test seeds its own unique tenant + token UUID, stages into a
unique ``temp/<tenant>/<token>/`` dir, and deletes its temp dir + committed rows
in teardown; no module-level mutable state; no ordering dependency.

Project: BE-9208.
"""

from __future__ import annotations

import io
import shutil
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete

from giljo_mcp.file_staging import FileStaging
from giljo_mcp.models import AgentTemplate, DownloadToken
from giljo_mcp.tenant import TenantManager


# A marker that only appears if the POST-staging template is in the served ZIP.
_POSTSTAGE_MARKER = "POSTSTAGE_MARKER_BE9208_do_not_freeze_me"


async def _make_template(session, tenant_key: str, name: str, *, marker: str = "", created: datetime | None = None):
    tmpl = AgentTemplate(
        tenant_key=tenant_key,
        name=name,
        role=name,
        version="1.0.0",
        cli_tool="claude",
        system_instructions=f"Original instructions for {name}. {marker}".strip(),
        is_active=True,
        is_default=False,
    )
    if created is not None:
        tmpl.created_at = created
    session.add(tmpl)
    await session.flush()


async def _seed_token(db_manager, filename: str, download_type: str, *, add_poststage: bool) -> dict:
    """Seed a tenant + one template, stage a ZIP, and optionally add a template AFTER staging.

    add_poststage=True reproduces the stale-snapshot scenario (a write the frozen
    ZIP cannot contain); add_poststage=False is the normal fresh-link flow.
    """
    tenant_key = TenantManager.generate_tenant_key()

    # 1) One active template exists at staging time.
    async with db_manager.get_session_async() as session:
        await _make_template(session, tenant_key, "agent-be9208-original")
        await session.commit()

    # 2) Generate a token + stage the ZIP against cwd()/temp (what the endpoint reads).
    from giljo_mcp.download_tokens import TokenManager

    async with db_manager.get_session_async() as session:
        token_manager = TokenManager(db_session=session)
        token = await token_manager.generate_token(
            tenant_key=tenant_key, download_type=download_type, filename=filename
        )
        staging = FileStaging(db_session=session)
        staging_path = await staging.create_staging_directory(tenant_key, token)
        if filename == "giljo_setup.zip":
            zip_path, msg = await staging.stage_combined_setup(
                staging_path, tenant_key, db_session=session, platform="claude_code"
            )
        else:
            zip_path, msg = await staging.stage_agent_templates(
                staging_path, tenant_key, db_session=session, platform="claude_code"
            )
        assert zip_path is not None, f"staging failed: {msg}"
        await token_manager.mark_ready(token)

    # 3) Optionally, AFTER staging: the user adds a new active template (deterministically
    #    newer than the token's staging time, so any freshness guard reads it as stale).
    if add_poststage:
        async with db_manager.get_session_async() as session:
            await _make_template(
                session,
                tenant_key,
                "agent-be9208-poststage",
                marker=_POSTSTAGE_MARKER,
                created=datetime.now(UTC) + timedelta(minutes=5),
            )
            await session.commit()

    return {
        "tenant_key": tenant_key,
        "token": token,
        "url": f"/api/download/temp/{token}/{filename}",
        "tenant_dir": Path.cwd() / "temp" / tenant_key,
    }


async def _cleanup(db_manager, seeded: dict) -> None:
    shutil.rmtree(seeded["tenant_dir"], ignore_errors=True)
    from giljo_mcp.database import tenant_session_context

    async with db_manager.get_session_async() as session:
        with tenant_session_context(session, seeded["tenant_key"]):
            await session.execute(delete(DownloadToken).where(DownloadToken.tenant_key == seeded["tenant_key"]))
            await session.execute(delete(AgentTemplate).where(AgentTemplate.tenant_key == seeded["tenant_key"]))
            await session.commit()


@pytest_asyncio.fixture(scope="function")
async def stale_token(request, db_manager):
    filename, download_type = request.param
    seeded = await _seed_token(db_manager, filename, download_type, add_poststage=True)
    try:
        yield seeded
    finally:
        await _cleanup(db_manager, seeded)


@pytest_asyncio.fixture(scope="function")
async def fresh_token(request, db_manager):
    filename, download_type = request.param
    seeded = await _seed_token(db_manager, filename, download_type, add_poststage=False)
    try:
        yield seeded
    finally:
        await _cleanup(db_manager, seeded)


def _zip_text(content: bytes) -> str:
    """Concatenate every entry name + body of a ZIP so we can search it."""
    parts: list[str] = []
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        for name in zf.namelist():
            parts.append(name)
            parts.append(zf.read(name).decode("utf-8", errors="ignore"))
    return "\n".join(parts)


_ZIP_CASES = [("giljo_setup.zip", "slash_commands"), ("agent_templates.zip", "agent_templates")]
_ZIP_IDS = ["giljo_setup", "agent_templates"]


@pytest.mark.asyncio
@pytest.mark.parametrize("stale_token", _ZIP_CASES, ids=_ZIP_IDS, indirect=True)
async def test_stale_snapshot_is_refused(api_client: AsyncClient, stale_token: dict) -> None:
    """A template added AFTER staging must not be silently missing from a 200 download.

    Post-fix contract: the endpoint refuses the stale snapshot with 410 Gone. (Pre-fix
    it returned 200 with the frozen pre-change bytes — this asserted the guarantee in a
    mechanism-agnostic form and was RED.)
    """
    resp = await api_client.get(stale_token["url"])

    if resp.status_code == 200:
        served = _zip_text(resp.content)
        assert _POSTSTAGE_MARKER in served, (
            "served a 200 with a stale snapshot: the template added after staging is "
            "missing from the ZIP (download served template content older than the "
            "tenant's latest template write)"
        )
    else:
        assert resp.status_code == 410, resp.text


@pytest.mark.asyncio
@pytest.mark.parametrize("fresh_token", _ZIP_CASES, ids=_ZIP_IDS, indirect=True)
async def test_fresh_token_still_served(api_client: AsyncClient, fresh_token: dict) -> None:
    """The freshness guard must NOT break the normal flow: no post-staging write ⇒ 200.

    This is the load-bearing half — the guard is correct only if it also lets the
    common case through with the staged content intact.
    """
    resp = await api_client.get(fresh_token["url"])

    assert resp.status_code == 200, resp.text
    served = _zip_text(resp.content)
    assert "agent-be9208-original" in served, "fresh token should serve the staged template content"


@pytest.mark.asyncio
async def test_zip_staged_before_any_template_is_stale(api_client: AsyncClient, db_manager) -> None:
    """EM point (iii): a ZIP staged when the tenant had NO templates (so nothing carries
    last_exported_at) must still be refused once templates are added.

    Here export_watermark is NULL (never exported) while content_watermark is not —
    the staged snapshot predates every current template, so it is stale. This is the
    yapper failure mode in its sharpest form (the new templates have no export stamp).
    """
    from giljo_mcp.download_tokens import TokenManager

    tenant_key = TenantManager.generate_tenant_key()
    filename = "giljo_setup.zip"

    # Stage a combined ZIP while the tenant has ZERO active templates (slash-commands only).
    async with db_manager.get_session_async() as session:
        token_manager = TokenManager(db_session=session)
        token = await token_manager.generate_token(
            tenant_key=tenant_key, download_type="slash_commands", filename=filename
        )
        staging = FileStaging(db_session=session)
        staging_path = await staging.create_staging_directory(tenant_key, token)
        zip_path, msg = await staging.stage_combined_setup(
            staging_path, tenant_key, db_session=session, platform="claude_code"
        )
        assert zip_path is not None, f"staging failed: {msg}"
        await token_manager.mark_ready(token)

    # Now the user creates their first active template — never exported.
    async with db_manager.get_session_async() as session:
        await _make_template(session, tenant_key, "agent-be9208-first", marker=_POSTSTAGE_MARKER)
        await session.commit()

    seeded = {"tenant_key": tenant_key, "token": token, "tenant_dir": Path.cwd() / "temp" / tenant_key}
    try:
        resp = await api_client.get(f"/api/download/temp/{token}/{filename}")
        assert resp.status_code == 410, resp.text
    finally:
        await _cleanup(db_manager, seeded)
