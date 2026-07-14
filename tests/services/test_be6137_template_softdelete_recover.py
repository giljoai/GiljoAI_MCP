# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6137 regression: AgentTemplate soft-delete (trash) -> recover round-trip.

``DELETE /agent-templates/{id}`` is converted from hard-delete to soft-delete
(BE-6137), extending the BE-6130b Task/VisionDocument pattern. These
service-layer tests prove:

* delete_template stamps deleted_at and the template drops out of all live
  reads (get_template/list_templates/get_by_name);
* the trashed template surfaces only in list_deleted_templates;
* restore_template within the 30-day window clears deleted_at and the
  template returns to live reads;
* restore past the 30-day window raises ValidationError;
* ARCHIVE SURVIVAL: archives created before soft-delete still exist after
  trash; restore re-surfaces template + archives as a unit;
* tenant isolation: a soft-deleted template in tenant A is invisible to
  tenant B live reads and cannot be restored by tenant B.

Real DB (rollback-isolated ``db_session``), no mocks — parallel-safe: each
test creates its own isolated template name, no module-level mutable state.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select, update

from giljo_mcp.exceptions import ResourceNotFoundError, ValidationError
from giljo_mcp.models.templates import AgentTemplate, TemplateArchive
from giljo_mcp.services.template_service import TemplateService
from giljo_mcp.tenant import TenantManager


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_template(tenant_key: str, suffix: str | None = None) -> AgentTemplate:
    """Construct an AgentTemplate ORM instance (not yet added to session)."""
    name = f"be6137-tpl-{suffix or uuid4().hex[:8]}"
    return AgentTemplate(
        id=str(uuid4()),
        tenant_key=tenant_key,
        name=name,
        role="custom",
        category="custom",
        system_instructions="# Test\nSoft-delete regression template.",
        is_active=True,
        version="1.0.0",
    )


def _make_service(db_manager, tenant_key: str, db_session) -> TemplateService:
    """TemplateService wired to the shared test session and a mock TenantManager."""
    mock_tm = MagicMock()
    mock_tm.get_current_tenant.return_value = tenant_key
    return TemplateService(db_manager=db_manager, tenant_manager=mock_tm, session=db_session)


@pytest_asyncio.fixture
async def live_template(db_session, test_tenant_key) -> AgentTemplate:
    """A live template committed to the DB for tests that need a pre-existing row."""
    tpl = _make_template(test_tenant_key)
    db_session.add(tpl)
    await db_session.commit()
    await db_session.refresh(tpl)
    return tpl


# ---------------------------------------------------------------------------
# Test: soft-delete stamps deleted_at and template drops out of live reads
# ---------------------------------------------------------------------------


async def test_delete_template_stamps_deleted_at(db_manager, db_session, test_tenant_key, live_template):
    svc = _make_service(db_manager, test_tenant_key, db_session)

    deleted = await svc.delete_template(db_session, live_template.id, test_tenant_key)
    assert deleted is True

    await db_session.refresh(live_template)
    assert live_template.deleted_at is not None


async def test_deleted_template_absent_from_list_templates(db_manager, db_session, test_tenant_key):
    tpl = _make_template(test_tenant_key)
    db_session.add(tpl)
    await db_session.commit()
    await db_session.refresh(tpl)

    svc = _make_service(db_manager, test_tenant_key, db_session)

    result = await svc.list_templates_with_filters(db_session, test_tenant_key)
    assert tpl.id in {t.id for t in result}

    await svc.delete_template(db_session, tpl.id, test_tenant_key)

    result = await svc.list_templates_with_filters(db_session, test_tenant_key)
    assert tpl.id not in {t.id for t in result}


async def test_deleted_template_absent_from_get_by_id(db_manager, db_session, test_tenant_key):
    """get_template() raises TemplateNotFoundError for a soft-deleted template (not found in live reads)."""
    from giljo_mcp.exceptions import TemplateNotFoundError

    tpl = _make_template(test_tenant_key)
    db_session.add(tpl)
    await db_session.commit()
    await db_session.refresh(tpl)

    svc = _make_service(db_manager, test_tenant_key, db_session)
    await svc.delete_template(db_session, tpl.id, test_tenant_key)

    # get_template raises TemplateNotFoundError because the soft-deleted row is
    # excluded from live reads — indistinguishable from "does not exist".
    with pytest.raises(TemplateNotFoundError):
        await svc.get_template(template_id=tpl.id, tenant_key=test_tenant_key)


async def test_deleted_template_absent_from_get_by_name(db_manager, db_session, test_tenant_key):
    """get_template() raises TemplateNotFoundError for a soft-deleted template name."""
    from giljo_mcp.exceptions import TemplateNotFoundError

    tpl = _make_template(test_tenant_key)
    db_session.add(tpl)
    await db_session.commit()
    await db_session.refresh(tpl)

    svc = _make_service(db_manager, test_tenant_key, db_session)
    await svc.delete_template(db_session, tpl.id, test_tenant_key)

    with pytest.raises(TemplateNotFoundError):
        await svc.get_template(template_name=tpl.name, tenant_key=test_tenant_key)


async def test_deleted_template_surfaces_in_list_deleted(db_manager, db_session, test_tenant_key):
    tpl = _make_template(test_tenant_key)
    db_session.add(tpl)
    await db_session.commit()
    await db_session.refresh(tpl)

    svc = _make_service(db_manager, test_tenant_key, db_session)
    await svc.delete_template(db_session, tpl.id, test_tenant_key)

    trashed = await svc.list_deleted_templates(tenant_key=test_tenant_key)
    assert tpl.id in {t.id for t in trashed}
    row = next(t for t in trashed if t.id == tpl.id)
    assert row.deleted_at is not None


# ---------------------------------------------------------------------------
# Test: restore within window round-trips
# ---------------------------------------------------------------------------


async def test_restore_template_within_window(db_manager, db_session, test_tenant_key):
    tpl = _make_template(test_tenant_key)
    db_session.add(tpl)
    await db_session.commit()
    await db_session.refresh(tpl)

    svc = _make_service(db_manager, test_tenant_key, db_session)
    await svc.delete_template(db_session, tpl.id, test_tenant_key)

    restored = await svc.restore_template(tpl.id, test_tenant_key)
    assert restored.deleted_at is None
    assert restored.id == tpl.id

    # Re-appears in live reads.
    result = await svc.list_templates_with_filters(db_session, test_tenant_key)
    assert tpl.id in {t.id for t in result}

    # No longer in trash.
    trashed = await svc.list_deleted_templates(tenant_key=test_tenant_key)
    assert tpl.id not in {t.id for t in trashed}


# ---------------------------------------------------------------------------
# Test: restore past 30-day window raises ValidationError
# ---------------------------------------------------------------------------


async def test_restore_window_expired_raises(db_manager, db_session, test_tenant_key):
    tpl = _make_template(test_tenant_key)
    db_session.add(tpl)
    await db_session.commit()
    await db_session.refresh(tpl)

    svc = _make_service(db_manager, test_tenant_key, db_session)
    await svc.delete_template(db_session, tpl.id, test_tenant_key)

    # Backdate deleted_at beyond the 30-day window.
    await db_session.execute(
        update(AgentTemplate)
        .where(AgentTemplate.id == tpl.id)
        .values(deleted_at=datetime.now(UTC) - timedelta(days=31))
    )
    await db_session.flush()

    with pytest.raises(ValidationError):
        await svc.restore_template(tpl.id, test_tenant_key)

    # Still trashed.
    trashed = await svc.list_deleted_templates(tenant_key=test_tenant_key)
    assert tpl.id in {t.id for t in trashed}


# ---------------------------------------------------------------------------
# Test: archive survival across trash / restore cycle
# ---------------------------------------------------------------------------


async def test_archive_survives_soft_delete_and_restore(db_manager, db_session, test_tenant_key):
    """Archives created before soft-delete must persist after trash and still be
    present after restore — they recover as a unit with the parent template."""
    tpl = _make_template(test_tenant_key)
    db_session.add(tpl)
    await db_session.commit()
    await db_session.refresh(tpl)

    # Create an archive row referencing this template.
    archive = TemplateArchive(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        template_id=tpl.id,
        name=tpl.name,
        category=tpl.category,
        version="0.9.0",
        system_instructions="# old\nPrevious version.",
        archive_reason="pre-delete snapshot",
        archive_type="manual",
    )
    db_session.add(archive)
    await db_session.commit()
    await db_session.refresh(archive)

    svc = _make_service(db_manager, test_tenant_key, db_session)
    await svc.delete_template(db_session, tpl.id, test_tenant_key)

    # Archive still present after soft-delete (soft-delete is UPDATE, not DELETE).
    archive_check = (
        await db_session.execute(select(TemplateArchive).where(TemplateArchive.id == archive.id))
    ).scalar_one_or_none()
    assert archive_check is not None, "Archive must survive soft-delete"

    # Restore the template.
    restored = await svc.restore_template(tpl.id, test_tenant_key)
    assert restored.deleted_at is None

    # Archive still there after restore.
    archive_after = (
        await db_session.execute(select(TemplateArchive).where(TemplateArchive.id == archive.id))
    ).scalar_one_or_none()
    assert archive_after is not None, "Archive must survive restore"


# ---------------------------------------------------------------------------
# Test: tenant isolation
# ---------------------------------------------------------------------------


async def test_restore_is_tenant_isolated(db_manager, db_session, test_tenant_key):
    """A trashed template owned by tenant A cannot be restored by tenant B."""
    tpl = _make_template(test_tenant_key)
    db_session.add(tpl)
    await db_session.commit()
    await db_session.refresh(tpl)

    svc_a = _make_service(db_manager, test_tenant_key, db_session)
    await svc_a.delete_template(db_session, tpl.id, test_tenant_key)

    # Tenant B cannot see the trashed template or restore it.
    other_tenant = TenantManager.generate_tenant_key()
    svc_b = _make_service(db_manager, other_tenant, db_session)

    trashed_b = await svc_b.list_deleted_templates(tenant_key=other_tenant)
    assert tpl.id not in {t.id for t in trashed_b}

    with pytest.raises(ResourceNotFoundError):
        await svc_b.restore_template(tpl.id, other_tenant)

    # The owning tenant can still restore it.
    restored = await svc_a.restore_template(tpl.id, test_tenant_key)
    assert restored.id == tpl.id
    assert restored.deleted_at is None
