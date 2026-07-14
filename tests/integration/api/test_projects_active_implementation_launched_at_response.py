# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Regression: GET /api/v1/projects/active must not 500 on implementation_launched_at.

The execution_mode-lock-on-launch change (5ec00ec99 / 6a3400c57) added
``Project.implementation_launched_at`` and the crud.py::get_active_project handler
reads ``proj.implementation_launched_at`` (crud.py:348) — but ``ActiveProjectDetail``
(the model ProjectQueryService.get_active_project returns) never carried the field,
so the route 500'd with ``AttributeError: 'ActiveProjectDetail' object has no
attribute 'implementation_launched_at'``.

The sibling CE-0037 test only covered ``GET /{project_id}`` (ProjectDetail), NOT
``/active`` (ActiveProjectDetail) — which is exactly why this slipped to prod-bound
code. This test drives the REAL FastAPI route over HTTP (BE-5042 failing-layer
discipline) and asserts 200 + the field present.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.endpoints.projects import router as projects_router
from api.endpoints.projects.dependencies import get_project_service
from giljo_mcp.auth.dependencies import get_current_active_user
from giljo_mcp.schemas.service_responses import ActiveProjectDetail


pytestmark = pytest.mark.asyncio

_TENANT = "tenant-active-impl-ts-test"


class _FakeUser:
    """Duck-typed User — the /active route only reads ``tenant_key``/``username``."""

    id = "user-active-test"
    username = "active_tester"
    tenant_key = _TENANT


class _FakeQuery:
    """Stands in for ProjectService.query — the /active handler calls
    ``project_service.query.get_active_project()`` (crud.py:328)."""

    def __init__(self, detail: ActiveProjectDetail | None) -> None:
        self._detail = detail

    async def get_active_project(self) -> ActiveProjectDetail | None:
        return self._detail


class _StubProjectService:
    def __init__(self, detail: ActiveProjectDetail | None) -> None:
        self.query = _FakeQuery(detail)


def _build_app(stub: _StubProjectService) -> FastAPI:
    app = FastAPI()
    app.include_router(projects_router)

    async def _override_user() -> _FakeUser:
        return _FakeUser()

    async def _override_service() -> AsyncIterator[_StubProjectService]:
        yield stub

    app.dependency_overrides[get_current_active_user] = _override_user
    app.dependency_overrides[get_project_service] = _override_service
    return app


def _active_detail(launch_ts: datetime | None) -> ActiveProjectDetail:
    """Mirror the field set ProjectQueryService.get_active_project() constructs."""
    return ActiveProjectDetail(
        id="proj-active-impl",
        alias="ACT",
        name="Active Impl-TS Project",
        mission="exercise GET /active serialization",
        description="seeded for active-impl-ts regression",
        status="active",
        product_id="prod-active",
        created_at="2026-06-10T00:00:00+00:00",
        updated_at="2026-06-10T01:00:00+00:00",
        completed_at=None,
        implementation_launched_at=(launch_ts.isoformat() if launch_ts else None),
        deleted_at=None,
        agent_count=0,
        message_count=0,
    )


async def test_active_endpoint_includes_implementation_launched_at_when_set():
    launch_ts = datetime(2026, 6, 10, 3, 29, 18, tzinfo=UTC)
    app = _build_app(_StubProjectService(_active_detail(launch_ts)))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/projects/active")

    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert "implementation_launched_at" in body, (
        "GET /active dropped implementation_launched_at — the ActiveProjectDetail "
        "schema regressed. Check schemas/responses/project.py::ActiveProjectDetail "
        "and services/project_query_service.py construction site."
    )
    assert body["implementation_launched_at"] is not None
    assert datetime.fromisoformat(body["implementation_launched_at"]) == launch_ts


async def test_active_endpoint_keeps_implementation_launched_at_when_null():
    app = _build_app(_StubProjectService(_active_detail(None)))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/projects/active")

    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert "implementation_launched_at" in body
    assert body["implementation_launched_at"] is None


async def test_active_endpoint_returns_null_when_no_active_project():
    app = _build_app(_StubProjectService(None))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/projects/active")

    assert resp.status_code == 200
    assert resp.json() is None
