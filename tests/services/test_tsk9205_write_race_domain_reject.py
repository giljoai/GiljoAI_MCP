# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""TSK-9205 regression: two write-races surface a clean domain rejection, not a 500.

Two independent instances of one class, both fixed by mapping the losing writer's
``IntegrityError`` to the existing already-exists domain rejection (409) at the
owning-service write:

1. ``ProductVisionService.upload_vision_document`` — two concurrent same-name
   uploads race past any pre-check; the loser hits the ``uq_vision_doc_product_name``
   partial unique index. Reproduced here with a real DB constraint (a live doc of
   the same name already present == the concurrent winner).
2. ``template_import.import_default_templates`` — two concurrent import sessions
   both pass the name pre-check and race to add the same name+version; the loser
   hits ``uq_template_tenant_name_version``. Reproduced by injecting the losing
   writer's ``IntegrityError`` at the owning-service write.

Happy paths are asserted unchanged. Real DB, rollback-isolated ``db_session``;
each test mints its own tenant key (parallel-safe, no module-level mutable state).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from giljo_mcp.database import tenant_session_context
from giljo_mcp.exceptions import AlreadyExistsError
from giljo_mcp.models import Product, VisionDocument
from giljo_mcp.services.product_vision_service import ProductVisionService
from giljo_mcp.services.template_service import TemplateService
from giljo_mcp.template_import import import_default_templates


pytestmark = pytest.mark.asyncio


def _tk(suffix: str) -> str:
    return f"tk_tsk9205_{suffix}_{uuid4().hex[:6]}"


async def _make_product(db_session, tenant: str) -> Product:
    product = Product(
        id=str(uuid4()),
        name=f"TSK9205 Product {uuid4().hex[:6]}",
        description="write-race tests",
        tenant_key=tenant,
        is_active=True,
    )
    db_session.add(product)
    await db_session.flush()
    return product


# ---------------------------------------------------------------------------
# Site 1 — vision document upload name race
# ---------------------------------------------------------------------------


async def test_duplicate_vision_upload_raises_already_exists(db_manager, db_session):
    """A second upload of an already-present doc name -> AlreadyExistsError (409),
    not the generic BaseGiljoError 500 the broad catch used to produce."""
    tenant = _tk("vision_race")
    svc = ProductVisionService(db_manager=db_manager, tenant_key=tenant, test_session=db_session)
    with tenant_session_context(db_session, tenant):
        product = await _make_product(db_session, tenant)
        # The concurrent winner: a live doc with the contested name already committed.
        db_session.add(
            VisionDocument(
                id=str(uuid4()),
                tenant_key=tenant,
                product_id=product.id,
                document_name="spec.md",
                document_type="vision",
                vision_document="winner body",
                storage_type="inline",
                is_active=True,
                display_order=0,
                version="1.0.0",
            )
        )
        await db_session.flush()

        with pytest.raises(AlreadyExistsError) as exc:
            await svc.upload_vision_document(
                product_id=product.id,
                content="loser body",
                filename="spec.md",
                auto_chunk=False,
            )
    assert "already exists" in str(exc.value).lower()


async def test_vision_upload_happy_path_unchanged(db_manager, db_session):
    """A unique-name upload still succeeds (the new IntegrityError branch does not
    touch the happy path)."""
    tenant = _tk("vision_ok")
    svc = ProductVisionService(db_manager=db_manager, tenant_key=tenant, test_session=db_session)
    with tenant_session_context(db_session, tenant):
        product = await _make_product(db_session, tenant)
        result = await svc.upload_vision_document(
            product_id=product.id,
            content="fresh vision body",
            filename="fresh.md",
            auto_chunk=False,
        )
    assert result.document_name == "fresh.md"


# ---------------------------------------------------------------------------
# Site 2 — default-template import name+version race
# ---------------------------------------------------------------------------


async def test_default_import_write_race_raises_already_exists(db_manager, db_session, monkeypatch):
    """When the losing import session's write trips uq_template_tenant_name_version,
    import_default_templates re-raises AlreadyExistsError (409), not a raw 500."""
    tenant = _tk("import_race")

    async def _raise_integrity(self, session, template):  # noqa: ARG001
        raise IntegrityError(
            "INSERT INTO agent_templates ...",
            {},
            Exception('duplicate key value violates unique constraint "uq_template_tenant_name_version"'),
        )

    monkeypatch.setattr(TemplateService, "add_and_commit_template", _raise_integrity)

    with pytest.raises(AlreadyExistsError) as exc:
        await import_default_templates(db_session, tenant)
    assert "already exists" in str(exc.value).lower()


async def test_default_import_happy_path_unchanged(db_manager, db_session):
    """A fresh tenant imports the seeded defaults with no collision (happy path
    unaffected by the new IntegrityError branch)."""
    tenant = _tk("import_ok")
    report = await import_default_templates(db_session, tenant)
    # Seeded defaults land as first-time adds for a previously-empty tenant.
    assert report.added
    assert not report.added_as_duplicate


async def test_default_import_is_idempotent_after_race_retry(db_manager, db_session):
    """After the losing writer bails out, a retry is safe: the second import over
    the same tenant adds nothing new (proves the domain rejection is recoverable,
    not corrupting)."""
    tenant = _tk("import_retry")
    first = await import_default_templates(db_session, tenant)
    assert first.added
    second = await import_default_templates(db_session, tenant)
    # Everything the first run added is now present -> the retry skips it.
    assert not second.added
