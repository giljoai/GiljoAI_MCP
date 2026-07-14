# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""TSK-6219 — authoritative event-origin (``source``) on the implementation-launched event.

Regression at the failing layer (the WS-payload boundary): the FE live-follow
(``useChainAutoNav.js``) needs to tell a HEADLESS MCP drive ("follow it") from a
user's own dashboard click ("stay put"). FE-6218 P1 shipped only a client-side
anti-hijack time window; P2 (this) adds the authoritative signal — a
``source: "mcp" | "ui"`` marker on the EXISTING ``project:implementation_launched``
broadcast, set by which door flipped the gate:

  - the ``launch_implementation`` MCP tool (a headless / agent drive) -> ``"mcp"``
  - the dashboard Implement REST endpoint (a human click)            -> ``"ui"``

``implementation_launched`` is the ONLY one of the three live-follow events that has
both a UI door and an MCP door (staging_complete / sequence:updated are
agent/conductor-driven, so "ui" cannot occur for them) — so it is where origin is
both meaningful and testable both ways.

When no origin is threaded the field is OMITTED, and the FE falls back to its
client-side anti-hijack window (the P1 behaviour) — proven by the third test.

Parallel-safe: db_session is a TransactionalTestContext (rolled back at teardown);
each test builds its own capturing WS manager. No module-level mutable state.
"""

from __future__ import annotations

import random
from uuid import uuid4

import pytest

from giljo_mcp.models.organizations import Organization
from giljo_mcp.models.products import Product
from giljo_mcp.models.projects import Project
from giljo_mcp.services.project_staging_service import ProjectStagingService
from giljo_mcp.tools.tool_accessor import ToolAccessor


pytestmark = pytest.mark.asyncio

_EVENT = "project:implementation_launched"


class _CapturingWebSocketManager:
    """Records every broadcast_to_tenant call's (event_type, data)."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def broadcast_to_tenant(self, tenant_key: str, event_type: str, data: dict) -> None:
        self.calls.append({"tenant_key": tenant_key, "event_type": event_type, "data": data})

    def launch_payload(self) -> dict:
        for call in self.calls:
            if call["event_type"] == _EVENT:
                return call["data"]
        raise AssertionError(f"no {_EVENT} broadcast captured; saw {[c['event_type'] for c in self.calls]}")


async def _seed_staging_complete_project(db_session, tenant_key: str) -> str:
    """Create org + product + a staging_complete, not-yet-launched project. Returns project_id."""
    suffix = uuid4().hex[:8]
    org = Organization(name=f"Org {suffix}", slug=f"org-{suffix}", tenant_key=tenant_key, is_active=True)
    db_session.add(org)
    await db_session.flush()

    product = Product(
        id=str(uuid4()),
        name=f"Product {suffix}",
        description="TSK-6219 event-origin tests",
        tenant_key=tenant_key,
        is_active=True,
        product_memory={},
    )
    db_session.add(product)
    await db_session.flush()

    project = Project(
        id=str(uuid4()),
        tenant_key=tenant_key,
        product_id=product.id,
        name=f"Project {suffix}",
        description="x",
        mission="x",
        status="active",
        execution_mode="claude_code_cli",
        staging_status="staging_complete",
        implementation_launched_at=None,
        series_number=random.randint(1, 9000),
    )
    db_session.add(project)
    await db_session.commit()
    return project.id


async def test_mcp_door_emits_source_mcp(db_manager, db_session):
    """The launch_implementation MCP tool (headless door) tags the broadcast source='mcp'.

    Exercised through the REAL MCP-door code path — the ToolAccessor method that the
    FastMCP @mcp.tool wrapper dispatches to — so the origin threading is proven end to
    end, not just at the service signature.
    """
    tenant_key = "tk_tsk6219_mcp"
    project_id = await _seed_staging_complete_project(db_session, tenant_key)
    ws = _CapturingWebSocketManager()

    accessor = ToolAccessor(
        db_manager=db_manager,
        tenant_manager=None,
        test_session=db_session,
        websocket_manager=ws,
    )
    result = await accessor.launch_implementation(project_id=project_id, tenant_key=tenant_key)
    assert result["already_launched"] is False

    assert ws.launch_payload().get("source") == "mcp"


async def test_ui_door_emits_source_ui(db_manager, db_session):
    """The dashboard Implement REST door tags the broadcast source='ui'.

    The REST endpoint's sole contribution to origin is ``origin="ui"`` passed into this
    single-writer (orchestration.py launch-implementation); this asserts that value
    reaches the payload. Driven through the service with test_session so the write lands
    in the rolled-back test transaction (the endpoint builds its own non-test session).
    """
    tenant_key = "tk_tsk6219_ui"
    project_id = await _seed_staging_complete_project(db_session, tenant_key)
    ws = _CapturingWebSocketManager()

    service = ProjectStagingService(
        db_manager=db_manager,
        tenant_manager=None,
        test_session=db_session,
        websocket_manager=ws,
    )
    result = await service.launch_implementation(project_id=project_id, tenant_key=tenant_key, origin="ui")
    assert result["already_launched"] is False

    assert ws.launch_payload().get("source") == "ui"


async def test_no_origin_omits_source(db_manager, db_session):
    """When no origin is threaded the field is OMITTED so the FE falls back to its
    client-side anti-hijack window (the FE-6218 P1 behaviour)."""
    tenant_key = "tk_tsk6219_none"
    project_id = await _seed_staging_complete_project(db_session, tenant_key)
    ws = _CapturingWebSocketManager()

    service = ProjectStagingService(
        db_manager=db_manager,
        tenant_manager=None,
        test_session=db_session,
        websocket_manager=ws,
    )
    await service.launch_implementation(project_id=project_id, tenant_key=tenant_key)

    assert "source" not in ws.launch_payload()
