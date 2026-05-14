# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Tests for TenantExportService and the export endpoint (BE-5062).

Service-layer tests (9) cover the export pipeline: strip filters (credentials,
platform metadata, tenant_key), ephemeral and ops table exclusion, manifest
SHA-256 integrity, vision file bundling, missing vision file warning, and the
schema.md redaction notice.

Endpoint-layer tests (5) hit the FastAPI router via httpx ASGI transport:
CE-mode happy path, 403 in demo/saas, 401 unauthenticated, and tenant
isolation between two users.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.endpoints import tenant_data
from api.exception_handlers import register_exception_handlers
from giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from giljo_mcp.models import (
    Product,
    User,
    VisionDocument,
)
from giljo_mcp.models.organizations import Organization
from giljo_mcp.services.tenant_export_service import TenantExportService
from giljo_mcp.tenant import TenantManager


pytestmark = pytest.mark.asyncio


# --------------------------------------------------------------------------- #
# Shared seeding helpers
# --------------------------------------------------------------------------- #


async def _seed_user(
    db_session: AsyncSession,
    tenant_key: str,
    *,
    password_hash: str = "$2b$12$abcdefghijklmnopqrstuv",
    recovery_pin_hash: str = "$2b$12$PIN_HASH_SECRET_VALUE12",
    username_suffix: str | None = None,
) -> User:
    suffix = username_suffix or uuid4().hex[:8]
    org = Organization(
        name=f"Org {suffix}",
        slug=f"org-{suffix}",
        tenant_key=tenant_key,
        is_active=True,
    )
    db_session.add(org)
    await db_session.flush()

    user = User(
        username=f"user_{suffix}",
        email=f"u_{suffix}@example.com",
        password_hash=password_hash,
        recovery_pin_hash=recovery_pin_hash,
        tenant_key=tenant_key,
        role="developer",
        org_id=org.id,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _seed_product(db_session: AsyncSession, tenant_key: str, name: str = "P") -> Product:
    product = Product(
        id=str(uuid4()),
        name=name,
        description="seed",
        tenant_key=tenant_key,
        is_active=True,
    )
    db_session.add(product)
    await db_session.flush()
    return product


# --------------------------------------------------------------------------- #
# Service-layer tests (9)
# --------------------------------------------------------------------------- #


async def test_export_strips_credentials(db_session: AsyncSession) -> None:
    """CREDENTIAL_STRIP values must not appear in any data/*.json bytes."""
    tenant_key = TenantManager.generate_tenant_key()
    secret_pw = "$2b$12$NEEDLE_PASSWORD_HASH_VALUE"
    secret_pin = "$2b$12$NEEDLE_PIN_HASH_VALUE_X"
    await _seed_user(db_session, tenant_key, password_hash=secret_pw, recovery_pin_hash=secret_pin)
    await db_session.commit()

    service = TenantExportService(db_session=db_session)
    zip_path, _ = await service.export(tenant_key=tenant_key)

    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            if name.startswith("data/") and name.endswith(".json"):
                blob = zf.read(name)
                assert secret_pw.encode() not in blob, f"password_hash leaked in {name}"
                assert secret_pin.encode() not in blob, f"recovery_pin_hash leaked in {name}"


async def test_export_strips_platform_metadata(db_session: AsyncSession) -> None:
    """PLATFORM_METADATA_STRIP values must not appear in data/*.json bytes."""
    tenant_key = TenantManager.generate_tenant_key()
    user = await _seed_user(db_session, tenant_key)
    # stripe_customer_id lives on Organization in SaaS; in CE we synthetically set
    # the attribute on the in-memory instance via setattr to simulate platform
    # metadata that MIGHT exist if the column were ever added. Since CE has no
    # such column, the strip filter must operate by NAME (not by presence) so
    # that SaaS rows surviving in a CE export still get scrubbed.
    needle = "cus_NEEDLE_STRIPE_CUSTOMER"
    # Inject into Configuration JSONB (a tenant-scoped table) as a worst-case carrier.
    from giljo_mcp.models import Configuration

    cfg = Configuration(
        tenant_key=tenant_key,
        key="billing.stripe_customer_id",
        value=needle,  # JSONB scalar; preserved by serializer (mission says preserve JSONB)
        category="billing",
    )
    db_session.add(cfg)
    # And as a real PLATFORM_METADATA_STRIP test, set a User attribute that IS in the strip list.
    # User has no stripe_customer_id column today, so we add it dynamically — the strip filter
    # must remove it regardless of column existence.
    object.__setattr__(user, "stripe_customer_id", "cus_FIELD_NEEDLE_USER")
    await db_session.commit()

    service = TenantExportService(db_session=db_session)
    zip_path, _ = await service.export(tenant_key=tenant_key)

    with zipfile.ZipFile(zip_path, "r") as zf:
        user_blob = zf.read("data/User.json")
        # Field-level strip on User: the synthetic attribute must NOT survive
        assert b"cus_FIELD_NEEDLE_USER" not in user_blob
        # Configuration JSONB value is intentionally preserved (mission says don't
        # post-process JSONB content). We only require the User field strip.


async def test_export_strips_tenant_key_from_rows(db_session: AsyncSession) -> None:
    """tenant_key must be absent from every record but present in manifest."""
    tenant_key = TenantManager.generate_tenant_key()
    await _seed_user(db_session, tenant_key)
    await _seed_product(db_session, tenant_key)
    await db_session.commit()

    service = TenantExportService(db_session=db_session)
    zip_path, _ = await service.export(tenant_key=tenant_key)

    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            if name.startswith("data/") and name.endswith(".json"):
                rows = json.loads(zf.read(name))
                assert isinstance(rows, list)
                for row in rows:
                    assert "tenant_key" not in row, f"tenant_key leaked in {name}"
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["tenant_key"] == tenant_key


async def test_export_excludes_ephemeral_tables(db_session: AsyncSession) -> None:
    """EPHEMERAL_EXCLUDE_MODELS must not appear as data/*.json files."""
    tenant_key = TenantManager.generate_tenant_key()
    await _seed_user(db_session, tenant_key)
    await db_session.commit()

    service = TenantExportService(db_session=db_session)
    zip_path, _ = await service.export(tenant_key=tenant_key)

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = set(zf.namelist())
        for forbidden in (
            "data/APIKey.json",
            "data/ApiKeyIpLog.json",
            "data/DownloadToken.json",
            "data/ApiMetrics.json",
            "data/OAuthAuthorizationCode.json",
            "data/MCPSession.json",
            "data/OptimizationMetric.json",
        ):
            assert forbidden not in names, f"ephemeral table leaked: {forbidden}"


async def test_export_excludes_ops_tables(db_session: AsyncSession) -> None:
    """OPS_EXCLUDE_TABLES must not appear as data/*.json files."""
    tenant_key = TenantManager.generate_tenant_key()
    await _seed_user(db_session, tenant_key)
    await db_session.commit()

    service = TenantExportService(db_session=db_session)
    zip_path, _ = await service.export(tenant_key=tenant_key)

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = set(zf.namelist())
        assert "data/ops_audit_log.json" not in names
        assert "data/ops_stripe_links.json" not in names


async def test_manifest_sha256_matches_contents(db_session: AsyncSession) -> None:
    """Per-file SHA-256 in manifest must equal SHA-256 of extracted file."""
    tenant_key = TenantManager.generate_tenant_key()
    await _seed_user(db_session, tenant_key)
    await _seed_product(db_session, tenant_key)
    await db_session.commit()

    service = TenantExportService(db_session=db_session)
    zip_path, _ = await service.export(tenant_key=tenant_key)

    with zipfile.ZipFile(zip_path, "r") as zf:
        manifest = json.loads(zf.read("manifest.json"))
        files = manifest["files"]
        assert files, "manifest.files must include at least one entry"
        for entry in files:
            zpath = entry["zip_path"]
            expected = entry["sha256"]
            actual = hashlib.sha256(zf.read(zpath)).hexdigest()
            assert actual == expected, f"checksum mismatch for {zpath}"


async def test_vision_files_bundled_when_present(
    db_session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Existing vision files must be added under files/products/<id>/vision/."""
    tenant_key = TenantManager.generate_tenant_key()
    product = await _seed_product(db_session, tenant_key, name="VisProduct")

    # Build a fake vision file on disk under a tmp_path "products" root.
    products_root = tmp_path / "products" / product.id / "vision"
    products_root.mkdir(parents=True, exist_ok=True)
    vision_file = products_root / "readme.md"
    vision_file.write_text("# Vision\nHello world.\n", encoding="utf-8")

    vd = VisionDocument(
        id=str(uuid4()),
        product_id=product.id,
        tenant_key=tenant_key,
        document_name="Readme",
        document_type="vision",
        storage_type="file",
        vision_path=str(vision_file),
        vision_document=None,
    )
    db_session.add(vd)
    await db_session.commit()

    service = TenantExportService(db_session=db_session, products_root=tmp_path / "products")
    zip_path, _ = await service.export(tenant_key=tenant_key)

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        expected = f"files/products/{product.id}/vision/readme.md"
        assert expected in names, f"vision file missing; got {names}"


async def test_vision_files_missing_emits_warning_not_error(
    db_session: AsyncSession, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Missing vision file must log a warning and not raise."""
    tenant_key = TenantManager.generate_tenant_key()
    product = await _seed_product(db_session, tenant_key, name="VisGhost")
    vd = VisionDocument(
        id=str(uuid4()),
        product_id=product.id,
        tenant_key=tenant_key,
        document_name="Ghost",
        document_type="vision",
        storage_type="file",
        vision_path=str(tmp_path / "products" / product.id / "vision" / "missing.md"),
        vision_document=None,
    )
    db_session.add(vd)
    await db_session.commit()

    service = TenantExportService(db_session=db_session, products_root=tmp_path / "products")
    with caplog.at_level("WARNING"):
        zip_path, _ = await service.export(tenant_key=tenant_key)

    assert any("missing.md" in rec.message or "vision" in rec.message.lower() for rec in caplog.records)
    # And the zip is still valid
    with zipfile.ZipFile(zip_path, "r") as zf:
        assert "manifest.json" in zf.namelist()


async def test_schema_md_includes_redaction_notice(db_session: AsyncSession) -> None:
    """schema.md must carry the top-line redaction notice."""
    tenant_key = TenantManager.generate_tenant_key()
    await _seed_user(db_session, tenant_key)
    await db_session.commit()

    service = TenantExportService(db_session=db_session)
    zip_path, _ = await service.export(tenant_key=tenant_key)

    with zipfile.ZipFile(zip_path, "r") as zf:
        schema_md = zf.read("schema.md").decode("utf-8")

    assert "Password hashes" in schema_md
    assert "redacted" in schema_md.lower()


# --------------------------------------------------------------------------- #
# Endpoint-layer tests (5) — FastAPI router via httpx
# --------------------------------------------------------------------------- #


def _build_app(
    db_manager,
    db_session: AsyncSession | None,
    user: User | None,
) -> FastAPI:
    """Mount the tenant_data router with auth + db overrides."""
    app = FastAPI()
    app.include_router(tenant_data.router, prefix="/api/v1/account")
    register_exception_handlers(app)

    # Provide a websocket manager stub so service event emission is no-op.
    ws = MagicMock()
    ws.broadcast_event_to_tenant = AsyncMock()
    app.state.websocket_manager = ws

    if user is not None:

        async def _override_user() -> User:
            return user

        app.dependency_overrides[get_current_active_user] = _override_user

    if db_session is not None:

        async def _override_db() -> AsyncIterator[AsyncSession]:
            yield db_session

        app.dependency_overrides[get_db_session] = _override_db

    return app


@pytest_asyncio.fixture
async def export_user(db_session: AsyncSession) -> User:
    tenant_key = TenantManager.generate_tenant_key()
    user = await _seed_user(db_session, tenant_key, username_suffix="alpha")
    await _seed_product(db_session, tenant_key, name="AlphaProduct")
    await db_session.commit()
    return user


async def test_endpoint_returns_download_url_in_ce(db_manager, db_session: AsyncSession, export_user: User) -> None:
    """CE mode: POST /api/v1/account/export returns 200 with download_url."""
    app = _build_app(db_manager, db_session, export_user)

    transport = ASGITransport(app=app)
    with patch("api.app_state.GILJO_MODE", "ce"):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/account/export")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "download_url" in body
    assert "expires_at" in body
    assert "model_counts" in body
    assert isinstance(body["model_counts"], dict)


async def test_endpoint_403_in_demo(db_manager, db_session: AsyncSession, export_user: User) -> None:
    app = _build_app(db_manager, db_session, export_user)
    transport = ASGITransport(app=app)
    with patch("api.app_state.GILJO_MODE", "demo"):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/account/export")
    assert resp.status_code == 403
    body = resp.json()
    detail = body.get("detail") or body.get("message") or ""
    assert "not available" in detail.lower()


async def test_endpoint_403_in_saas(db_manager, db_session: AsyncSession, export_user: User) -> None:
    app = _build_app(db_manager, db_session, export_user)
    transport = ASGITransport(app=app)
    with patch("api.app_state.GILJO_MODE", "saas"):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/account/export")
    assert resp.status_code == 403


async def test_endpoint_requires_auth(db_manager, db_session: AsyncSession) -> None:
    """Unauthenticated request must yield 401."""
    app = _build_app(db_manager, db_session, user=None)
    transport = ASGITransport(app=app)
    with patch("api.app_state.GILJO_MODE", "ce"):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/account/export")
    assert resp.status_code in (401, 403)


async def test_endpoint_tenant_isolation(db_manager, db_session: AsyncSession) -> None:
    """User A's export must not contain User B's data."""
    tk_a = TenantManager.generate_tenant_key()
    tk_b = TenantManager.generate_tenant_key()
    user_a = await _seed_user(db_session, tk_a, username_suffix="aaa")
    needle_b = f"bbb_{uuid4().hex[:8]}"
    await _seed_user(db_session, tk_b, username_suffix=needle_b)
    await _seed_product(db_session, tk_b, name="OtherTenantProduct")
    await db_session.commit()

    app = _build_app(db_manager, db_session, user_a)
    transport = ASGITransport(app=app)
    with patch("api.app_state.GILJO_MODE", "ce"):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/account/export")

    assert resp.status_code == 200, resp.text

    # Fetch the staged ZIP off disk via the service (the endpoint stages it).
    # We verify isolation by exporting User A's tenant via the service directly
    # and asserting no Tenant B data appears.
    service = TenantExportService(db_session=db_session)
    zip_path, _ = await service.export(tenant_key=tk_a)

    with zipfile.ZipFile(zip_path, "r") as zf:
        blob = b""
        for name in zf.namelist():
            if name.startswith("data/") and name.endswith(".json"):
                blob += zf.read(name)
    assert needle_b.encode() not in blob
    assert b"OtherTenantProduct" not in blob


# --------------------------------------------------------------------------- #
# Post-migration constraint regression — startup.py upgrade path
#
# This test exercises the live test DB (which is created with the model's
# current CheckConstraint and is what `alembic upgrade head` would produce
# on a customer install). It is the regression test for the "broken on
# customer upgrade" failure mode: if migration ce_0025 ever stops shipping
# or the constraint definition drifts, this test fails before the export
# endpoint silently 500s in production.
# --------------------------------------------------------------------------- #


async def test_download_type_constraint_admits_tenant_export(db_session: AsyncSession) -> None:
    """Post-migration DB must accept download_type='tenant_export'."""
    from datetime import UTC, datetime, timedelta

    from giljo_mcp.models import DownloadToken

    tk = TenantManager.generate_tenant_key()
    record = DownloadToken(
        tenant_key=tk,
        download_type="tenant_export",
        filename="tenant_export.zip",
        expires_at=datetime.now(UTC) + timedelta(minutes=15),
    )
    db_session.add(record)
    await db_session.commit()
    assert record.id is not None
    assert record.download_type == "tenant_export"


async def test_download_type_constraint_still_rejects_unknown(db_session: AsyncSession) -> None:
    """Post-migration DB must still reject unknown download_type values."""
    from datetime import UTC, datetime, timedelta

    from sqlalchemy.exc import IntegrityError

    from giljo_mcp.models import DownloadToken

    tk = TenantManager.generate_tenant_key()
    record = DownloadToken(
        tenant_key=tk,
        download_type="not_a_real_type",
        filename="bogus.zip",
        expires_at=datetime.now(UTC) + timedelta(minutes=15),
    )
    db_session.add(record)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()
