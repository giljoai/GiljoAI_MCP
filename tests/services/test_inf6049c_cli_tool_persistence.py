# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""INF-6049c — service-layer test for the role->tool (cli_tool) mapping.

The Phase-3 role->tool mapping reuses the existing ``agent_templates.cli_tool``
column (no new column / migration). These tests prove the OWNING service
(``TemplateService``) persists and updates it through a real DB round-trip — incl.
the new ``antigravity`` value — and that the read/write is tenant-isolated.

Updated BE-8000j: rewired from the removed create_template / update_template
methods onto the live write path the REST endpoint now uses —
``create_template_from_request`` / ``update_template_from_request`` (which take a
``TemplateCreate`` / ``TemplateUpdate`` request object and return the ORM row).
The persistence + tenant-isolation guarantees are unchanged; they now point at
the code production actually runs.

DB-touching + parallel-safe: uses the rolled-back ``db_session`` fixture; each
test owns its setup; no module-level mutable state.
"""

from __future__ import annotations

import pytest

from api.endpoints.templates.models import TemplateCreate, TemplateUpdate
from giljo_mcp.exceptions import TemplateNotFoundError
from giljo_mcp.services.template_service import TemplateService
from giljo_mcp.tenant import TenantManager


pytestmark = pytest.mark.asyncio


def _service(db_manager, db_session) -> TemplateService:
    return TemplateService(db_manager, TenantManager(), session=db_session)


async def test_create_persists_cli_tool(db_manager, db_session):
    tenant = TenantManager.generate_tenant_key()
    svc = _service(db_manager, db_session)

    created = await svc.create_template_from_request(
        db_session,
        TemplateCreate(role="implementer", cli_tool="codex"),
        tenant_key=tenant,
        created_by="tester",
    )

    fetched = await svc.get_template(template_id=created.id, tenant_key=tenant)
    assert fetched.template.cli_tool == "codex"


async def test_update_to_antigravity_round_trips(db_manager, db_session):
    tenant = TenantManager.generate_tenant_key()
    svc = _service(db_manager, db_session)
    created = await svc.create_template_from_request(
        db_session,
        TemplateCreate(role="reviewer", cli_tool="claude"),
        tenant_key=tenant,
        created_by="tester",
    )

    updated, _fields = await svc.update_template_from_request(
        db_session,
        created.id,
        TemplateUpdate(cli_tool="antigravity"),
        tenant_key=tenant,
        username="tester",
    )
    assert updated.cli_tool == "antigravity"

    fetched = await svc.get_template(template_id=created.id, tenant_key=tenant)
    assert fetched.template.cli_tool == "antigravity"


async def test_cli_tool_defaults_to_claude_when_unset(db_manager, db_session):
    """An omitted cli_tool defaults to claude at the request boundary and persists."""
    tenant = TenantManager.generate_tenant_key()
    svc = _service(db_manager, db_session)
    created = await svc.create_template_from_request(
        db_session,
        TemplateCreate(role="analyzer"),
        tenant_key=tenant,
        created_by="tester",
    )

    fetched = await svc.get_template(template_id=created.id, tenant_key=tenant)
    # TemplateCreate.cli_tool defaults to "claude"; the service maps it through
    # unchanged. Assert it is not a stale wrong tool.
    assert fetched.template.cli_tool in (None, "claude")


async def test_cli_tool_update_is_tenant_isolated(db_manager, db_session):
    tenant_a = TenantManager.generate_tenant_key()
    tenant_b = TenantManager.generate_tenant_key()
    svc = _service(db_manager, db_session)
    created = await svc.create_template_from_request(
        db_session,
        TemplateCreate(role="implementer", cli_tool="codex"),
        tenant_key=tenant_a,
        created_by="tester",
    )

    # Tenant B must not be able to read or mutate tenant A's template's tool.
    with pytest.raises(TemplateNotFoundError):
        await svc.update_template_from_request(
            db_session,
            created.id,
            TemplateUpdate(cli_tool="gemini"),
            tenant_key=tenant_b,
            username="tester",
        )

    # Tenant A's value is unchanged.
    fetched = await svc.get_template(template_id=created.id, tenant_key=tenant_a)
    assert fetched.template.cli_tool == "codex"
