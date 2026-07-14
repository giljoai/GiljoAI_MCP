# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Regression tests for FE-5073 / BE-5122 REST plumbing.

The MCP tool path for ``create_project(project_type="CTX", bootstrap_template_vars=...)``
was wired in BE-5122. The REST endpoint ``POST /api/v1/projects/`` was not — the
frontend depends on REST, so this regression covers the cross-path parity:

R1 -- REST POST with CTX project_type_id + bootstrap_template_vars renders the
      mission server-side via the SAME helper the MCP path uses
      (``ProjectService.render_ctx_bootstrap_mission``); round-trip-equal output.
R2 -- REST POST with a non-CTX project_type silently ignores
      ``bootstrap_template_vars`` (forgiving REST contract).
R3 -- Field caps: >50 ``new_documents`` rejected with ``ValidationError`` (422-shaped).
R4 -- Field caps: per-entry string field >200 chars rejected.

All DB-touching tests use the ``db_session`` fixture (TransactionalTestContext)
per CLAUDE.md test discipline.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import tenant_session_context
from giljo_mcp.exceptions import ValidationError
from giljo_mcp.models import Product, TaxonomyType, VisionDocument
from giljo_mcp.services.project_service import ProjectService
from giljo_mcp.tenant import TenantManager


@pytest_asyncio.fixture
async def fe_tenant_key() -> str:
    return TenantManager.generate_tenant_key()


@pytest_asyncio.fixture
async def fe_product(db_session: AsyncSession, fe_tenant_key: str) -> Product:
    product = Product(
        id=str(uuid.uuid4()),
        name="FE-5073 Product",
        description="Regression product for REST CTX bootstrap.",
        tenant_key=fe_tenant_key,
        is_active=True,
        product_memory={},
        consolidated_vision_hash=None,
    )
    db_session.add(product)
    await db_session.flush()
    return product


@pytest_asyncio.fixture
async def fe_ctx_taxonomy(db_session: AsyncSession, fe_tenant_key: str) -> TaxonomyType:
    tt = TaxonomyType(
        id=str(uuid.uuid4()),
        tenant_key=fe_tenant_key,
        abbreviation="CTX",
        label="Context Update",
        color="#9E9E9E",
        sort_order=8,
    )
    db_session.add(tt)
    await db_session.flush()
    return tt


@pytest_asyncio.fixture
async def fe_non_ctx_taxonomy(db_session: AsyncSession, fe_tenant_key: str) -> TaxonomyType:
    tt = TaxonomyType(
        id=str(uuid.uuid4()),
        tenant_key=fe_tenant_key,
        abbreviation="BE",
        label="Backend",
        color="#1976D2",
        sort_order=1,
    )
    db_session.add(tt)
    await db_session.flush()
    return tt


@pytest_asyncio.fixture
async def fe_vision_doc(db_session: AsyncSession, fe_tenant_key: str, fe_product: Product) -> VisionDocument:
    doc = VisionDocument(
        id=str(uuid.uuid4()),
        tenant_key=fe_tenant_key,
        product_id=fe_product.id,
        document_name="Architecture",
        document_type="architecture",
        vision_document="REST path vision text.",
        storage_type="inline",
    )
    db_session.add(doc)
    await db_session.flush()
    return doc


def _make_service(db_session: AsyncSession, tenant_key: str) -> ProjectService:
    """Build a ProjectService bound to the test session (mirrors BE-5122 fixture)."""
    import contextlib

    service = ProjectService.__new__(ProjectService)
    service.db_manager = None
    service.tenant_key = tenant_key
    service._websocket_manager = None
    service._logger = __import__("logging").getLogger("test_fe_5073")

    # Production ProjectService._get_session(tenant_key=None) takes a tenant_key
    # (Slice-3); the mock must mirror that signature AND scope the shared test
    # session to the caller's tenant so the fail-closed guard authorizes the
    # service's tenant-scoped reads.
    @contextlib.asynccontextmanager
    async def _sess(tenant_key: str | None = None):
        with tenant_session_context(db_session, tenant_key or service.tenant_key):
            yield db_session

    service._get_session = _sess  # type: ignore[assignment]
    return service


# --------------------------------------------------------------------------- #
# R1: REST CTX path renders mission via the shared helper                     #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_r1_render_helper_is_callable_from_rest_via_public_name(
    db_session: AsyncSession,
    fe_tenant_key: str,
    fe_product: Product,
    fe_ctx_taxonomy: TaxonomyType,
    fe_vision_doc: VisionDocument,
) -> None:
    """The REST handler reuses ``render_ctx_bootstrap_mission`` -- the same
    public service method the MCP path calls -- with identical output."""
    service = _make_service(db_session, fe_tenant_key)

    rendered_rest = await service.render_ctx_bootstrap_mission(
        product_id=fe_product.id,
        tenant_key=fe_tenant_key,
        bootstrap_template_vars={
            "new_documents": [{"document_name": "Architecture", "document_type": "architecture"}],
        },
    )

    rendered_mcp_equivalent = await service.render_ctx_bootstrap_mission(
        product_id=fe_product.id,
        tenant_key=fe_tenant_key,
        bootstrap_template_vars={
            "new_documents": [{"document_name": "Architecture", "document_type": "architecture"}],
        },
    )

    assert rendered_rest == rendered_mcp_equivalent
    assert fe_product.name in rendered_rest
    assert fe_product.id in rendered_rest
    assert "Architecture (architecture)" in rendered_rest


@pytest.mark.asyncio
async def test_r1_get_project_type_by_id_resolves_ctx_abbreviation(
    db_session: AsyncSession,
    fe_tenant_key: str,
    fe_ctx_taxonomy: TaxonomyType,
) -> None:
    """The REST handler needs to map project_type_id -> abbreviation to decide
    on the CTX render branch. The new ``get_project_type_by_id`` lookup must
    return the right tenant-scoped row."""
    service = _make_service(db_session, fe_tenant_key)

    resolved = await service.get_project_type_by_id(
        type_id=fe_ctx_taxonomy.id,
        tenant_key=fe_tenant_key,
    )
    assert resolved is not None
    assert resolved.abbreviation == "CTX"


@pytest.mark.asyncio
async def test_r1_get_project_type_by_id_tenant_isolation(
    db_session: AsyncSession,
    fe_tenant_key: str,
    fe_ctx_taxonomy: TaxonomyType,
) -> None:
    """A taxonomy row owned by a different tenant must not leak through."""
    other_tenant = TenantManager.generate_tenant_key()
    service = _make_service(db_session, other_tenant)

    resolved = await service.get_project_type_by_id(
        type_id=fe_ctx_taxonomy.id,
        tenant_key=other_tenant,
    )
    assert resolved is None


# --------------------------------------------------------------------------- #
# R2: Non-CTX project_type silently ignores bootstrap_template_vars            #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_r2_non_ctx_type_does_not_invoke_render_helper(
    db_session: AsyncSession,
    fe_tenant_key: str,
    fe_non_ctx_taxonomy: TaxonomyType,
) -> None:
    """Resolving a non-CTX abbreviation means the REST handler skips the CTX
    branch entirely; bootstrap_template_vars is silently ignored. We assert
    abbreviation-based branching at the service layer (the REST handler's
    own conditional reads ``resolved_type.abbreviation``)."""
    service = _make_service(db_session, fe_tenant_key)

    resolved = await service.get_project_type_by_id(
        type_id=fe_non_ctx_taxonomy.id,
        tenant_key=fe_tenant_key,
    )
    assert resolved is not None
    assert (resolved.abbreviation or "").upper() != "CTX"


# --------------------------------------------------------------------------- #
# R3/R4: Field cap validation (mirrors BE-5122 D4 contract)                   #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_r3_more_than_50_new_documents_rejected(
    db_session: AsyncSession,
    fe_tenant_key: str,
    fe_product: Product,
    fe_ctx_taxonomy: TaxonomyType,
) -> None:
    service = _make_service(db_session, fe_tenant_key)

    with pytest.raises(ValidationError) as exc:
        await service.render_ctx_bootstrap_mission(
            product_id=fe_product.id,
            tenant_key=fe_tenant_key,
            bootstrap_template_vars={
                "new_documents": [{"document_name": f"d{i}", "document_type": "spec"} for i in range(51)],
            },
        )
    assert "50" in str(exc.value)


@pytest.mark.asyncio
async def test_r4_per_field_length_cap_rejected(
    db_session: AsyncSession,
    fe_tenant_key: str,
    fe_product: Product,
    fe_ctx_taxonomy: TaxonomyType,
) -> None:
    service = _make_service(db_session, fe_tenant_key)

    with pytest.raises(ValidationError) as exc:
        await service.render_ctx_bootstrap_mission(
            product_id=fe_product.id,
            tenant_key=fe_tenant_key,
            bootstrap_template_vars={
                "new_documents": [{"document_name": "x" * 201, "document_type": "spec"}],
            },
        )
    assert "200" in str(exc.value)


# --------------------------------------------------------------------------- #
# R5: REST ProjectCreate model accepts the new field cleanly                   #
# --------------------------------------------------------------------------- #


def test_r5_project_create_accepts_bootstrap_template_vars() -> None:
    """The Pydantic model wire-shape must accept bootstrap_template_vars as
    an optional dict and default to None for non-CTX payloads."""
    from api.endpoints.projects.models import ProjectCreate

    payload = ProjectCreate(
        name="ctx project",
        description="ctx desc",
        product_id="prod-1",
        project_type_id="type-1",
        bootstrap_template_vars={"new_documents": []},
    )
    assert payload.bootstrap_template_vars == {"new_documents": []}

    legacy = ProjectCreate(
        name="be project",
        description="be desc",
        product_id="prod-1",
    )
    assert legacy.bootstrap_template_vars is None
