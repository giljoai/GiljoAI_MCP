# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-8000j regression: the template create/update REST endpoints route their
writes through TemplateService (the owning service), not an inline direct-DB path.

Two things are proven here:

1. ROUTING (the failing layer for this waste-fix): spy on
   ``TemplateService.create_template_from_request`` /
   ``update_template_from_request`` and assert the endpoint awaits it exactly
   once — i.e. the write goes through the owning service, closing the
   direct-DB-access drift BE-8000j fixed.

2. BEHAVIOUR PRESERVED end-to-end (ported from the former mock-based
   test_0814_template_manager_ui.py items 1-4, now against a real DB through the
   endpoint): canonical MCP bootstrap injection, user_instructions storage,
   empty-user_instructions default, the system_instructions 403 guard, and the
   auto-archive on a user_instructions change.

Real DB via the shared transactional ``db_session`` (rolled back at teardown);
each test owns its setup; no module-level mutable state; parallel-safe.
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from giljo_mcp.models.auth import User
from giljo_mcp.models.templates import TemplateArchive
from giljo_mcp.template_seeder import _get_mcp_bootstrap_section


pytestmark = pytest.mark.asyncio


def _user(tenant_key: str) -> User:
    return User(
        id=str(uuid4()),
        tenant_key=tenant_key,
        username=f"caller_{uuid4().hex[:6]}",
        email=f"caller_{uuid4().hex[:6]}@example.com",
        password_hash="not-used",
        role="developer",
        is_active=True,
    )


async def _create(template_service, db_session, user, **payload_kwargs):
    """Drive the create endpoint and return its TemplateResponse."""
    from api.endpoints.templates.crud import create_template
    from api.endpoints.templates.models import TemplateCreate

    payload = TemplateCreate(**payload_kwargs)
    return await create_template(
        template=payload,
        current_user=user,
        session=db_session,
        template_service=template_service,
    )


# ---------------------------------------------------------------------------
# 1. Routing: endpoints go through the owning service
# ---------------------------------------------------------------------------


async def test_create_endpoint_routes_through_service(db_session, template_service, test_tenant_key, monkeypatch):
    """create endpoint must await TemplateService.create_template_from_request."""
    from api.endpoints.templates.crud import create_template
    from api.endpoints.templates.models import TemplateCreate

    user = _user(test_tenant_key)
    spy = AsyncMock(wraps=template_service.create_template_from_request)
    monkeypatch.setattr(template_service, "create_template_from_request", spy)

    resp = await create_template(
        template=TemplateCreate(role="reviewer", cli_tool="claude"),
        current_user=user,
        session=db_session,
        template_service=template_service,
    )

    spy.assert_awaited_once()
    # The endpoint returns the service-produced row, unchanged.
    assert resp.id
    assert resp.role == "reviewer"


async def test_update_endpoint_routes_through_service(db_session, template_service, test_tenant_key, monkeypatch):
    """update endpoint must await TemplateService.update_template_from_request."""
    from api.endpoints.templates.crud import update_template
    from api.endpoints.templates.models import TemplateUpdate

    user = _user(test_tenant_key)
    created = await _create(template_service, db_session, user, role="reviewer", cli_tool="claude")

    spy = AsyncMock(wraps=template_service.update_template_from_request)
    monkeypatch.setattr(template_service, "update_template_from_request", spy)

    resp = await update_template(
        template_id=created.id,
        updates=TemplateUpdate(description="edited via endpoint"),
        current_user=user,
        session=db_session,
        template_service=template_service,
    )

    spy.assert_awaited_once()
    assert resp.description == "edited via endpoint"


# ---------------------------------------------------------------------------
# 2. Behaviour preserved (ported from 0814 items 1-4, now end-to-end)
# ---------------------------------------------------------------------------


async def test_create_injects_canonical_bootstrap(db_session, template_service, test_tenant_key):
    """system_instructions is always the canonical MCP bootstrap, never the caller value."""
    user = _user(test_tenant_key)
    resp = await _create(
        template_service,
        db_session,
        user,
        role="implementer",
        cli_tool="claude",
        system_instructions="INJECTED EVIL INSTRUCTIONS",
        user_instructions="Legitimate role description.",
    )

    assert resp.system_instructions == _get_mcp_bootstrap_section()
    assert "INJECTED EVIL INSTRUCTIONS" not in resp.system_instructions
    # bootstrap carries the required coordination elements
    assert "health_check" in resp.system_instructions
    assert "get_job_mission" in resp.system_instructions
    assert "full_protocol" in resp.system_instructions


async def test_create_stores_user_instructions(db_session, template_service, test_tenant_key):
    """user_instructions from the request body are persisted."""
    user = _user(test_tenant_key)
    prose = "You are a senior code reviewer who provides constructive feedback on pull requests."
    resp = await _create(
        template_service, db_session, user, role="reviewer", cli_tool="claude", user_instructions=prose
    )

    assert resp.user_instructions == prose


async def test_create_empty_user_instructions_defaults_to_empty(db_session, template_service, test_tenant_key):
    """Omitted user_instructions defaults to an empty string (not None)."""
    user = _user(test_tenant_key)
    resp = await _create(template_service, db_session, user, role="tester", cli_tool="claude")

    assert resp.user_instructions == ""


async def test_update_rejects_system_instructions_with_403(db_session, template_service, test_tenant_key):
    """Sending system_instructions in an update payload returns 403 read-only."""
    from api.endpoints.templates.crud import update_template
    from api.endpoints.templates.models import TemplateUpdate

    user = _user(test_tenant_key)
    created = await _create(template_service, db_session, user, role="implementer", cli_tool="claude")

    with pytest.raises(HTTPException) as exc_info:
        await update_template(
            template_id=created.id,
            updates=TemplateUpdate(system_instructions="Attempt to override bootstrap"),
            current_user=user,
            session=db_session,
            template_service=template_service,
        )

    assert exc_info.value.status_code == 403
    assert "system_instructions" in str(exc_info.value.detail).lower()
    assert "read-only" in str(exc_info.value.detail).lower()


async def test_update_stores_user_instructions_and_archives(db_session, template_service, test_tenant_key):
    """A user_instructions change is persisted AND snapshots the prior version to an archive."""
    from api.endpoints.templates.crud import update_template
    from api.endpoints.templates.models import TemplateUpdate

    user = _user(test_tenant_key)
    created = await _create(
        template_service, db_session, user, role="implementer", cli_tool="claude", user_instructions="Old instructions"
    )

    new_prose = "Updated role description with deep expertise in testing."
    resp = await update_template(
        template_id=created.id,
        updates=TemplateUpdate(user_instructions=new_prose),
        current_user=user,
        session=db_session,
        template_service=template_service,
    )

    assert resp.user_instructions == new_prose

    # An auto-archive of the prior state must have been created.
    archives = (
        (await db_session.execute(select(TemplateArchive).where(TemplateArchive.template_id == created.id)))
        .scalars()
        .all()
    )
    assert len(archives) == 1
    assert archives[0].archive_reason == "Update user instructions"
    assert archives[0].archive_type == "auto"
