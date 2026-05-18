# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""CE-0037 — REST integration regression for ``implementation_launched_at``.

CE-0036 fixed the missing field at the schema layer (api/endpoints/projects/models.py).
CE-0028b's existing tests cover the Pydantic-model layer only. The bug actually
lived at the API serialization layer — the construction site in
api/endpoints/projects/crud.py::get_project had to be updated too, and any
future refactor that drops the ``implementation_launched_at=proj.implementation_launched_at``
mapping would silently regress without going through the wire.

This test exercises the actual FastAPI route via HTTP. It stubs ProjectService
so we don't need the full DB chain, but the test mounts the real router, runs
the real endpoint handler, and asserts against the JSON body that the frontend
actually consumes (BE-5042 failing-layer discipline).
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
from giljo_mcp.schemas.service_responses import ProjectDetail


pytestmark = pytest.mark.asyncio


_FAKE_USER_TENANT = "tenant-ce0037-test"


class _FakeUser:
    """Minimal stand-in for User. ``get_current_active_user`` returns whatever
    is set as an override, so duck-typing is sufficient — the route only reads
    ``tenant_key`` and ``username``."""

    id = "user-ce0037-test"
    username = "ce0037_tester"
    tenant_key = _FAKE_USER_TENANT


class _StubProjectService:
    """Returns a fixed ProjectDetail. We exercise the serialization layer, not
    the DB or repository. The bug lives in how the endpoint maps service-layer
    ProjectDetail → REST ProjectResponse → JSON."""

    def __init__(self, project_detail: ProjectDetail) -> None:
        self._project_detail = project_detail

    async def get_project(self, project_id: str, tenant_key: str) -> ProjectDetail:
        return self._project_detail


def _build_app(stub_service: _StubProjectService) -> FastAPI:
    """Mount the real projects router with auth + service overrides."""
    app = FastAPI()
    app.include_router(projects_router)

    async def _override_user() -> _FakeUser:
        return _FakeUser()

    async def _override_service() -> AsyncIterator[_StubProjectService]:
        yield stub_service

    app.dependency_overrides[get_current_active_user] = _override_user
    app.dependency_overrides[get_project_service] = _override_service
    return app


def _detail_with_launch_ts(launch_ts: datetime | None) -> ProjectDetail:
    """ProjectDetail factory matching the shape ProjectService.get_project()
    returns (see src/giljo_mcp/services/project_service.py:396-429)."""
    return ProjectDetail(
        id="proj-ce0037",
        alias="CE37",
        name="CE-0037 Regression Project",
        mission="exercise the API serialization layer",
        description="seeded for CE-0037 integration test",
        status="active",
        staging_status="staging_complete",
        implementation_launched_at=(launch_ts.isoformat() if launch_ts else None),
        product_id="prod-ce0037",
        tenant_key=_FAKE_USER_TENANT,
        execution_mode="multi_terminal",
        auto_checkin_enabled=False,
        auto_checkin_interval=10,
        created_at="2026-05-18T00:00:00+00:00",
        updated_at="2026-05-18T01:00:00+00:00",
        agents=[],
        agent_count=0,
        message_count=0,
    )


async def test_get_project_response_includes_implementation_launched_at_when_set():
    """The exact CE-0036 scenario: DB column is set, frontend expects the field
    in the JSON body so the Close Project HITL button can render."""
    launch_ts = datetime(2026, 5, 18, 3, 29, 18, tzinfo=UTC)
    detail = _detail_with_launch_ts(launch_ts)
    app = _build_app(_StubProjectService(detail))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/projects/{detail.id}")

    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert "implementation_launched_at" in body, (
        "REST ProjectResponse JSON is missing implementation_launched_at — the CE-0036 bug regressed. "
        "Check api/endpoints/projects/models.py::ProjectResponse and crud.py::get_project construction site."
    )
    # FastAPI serializes datetimes as ISO 8601 strings; the wire shape must
    # be parseable back to the same instant.
    assert body["implementation_launched_at"] is not None
    assert datetime.fromisoformat(body["implementation_launched_at"]) == launch_ts


async def test_get_project_response_keeps_implementation_launched_at_when_null():
    """Negative case: the frontend useProjectCloseout guard checks for the
    property's presence, not just truthiness. Missing-key vs explicit-null
    have different falsy semantics in JS. The field must always appear in
    the JSON body, even when null."""
    detail = _detail_with_launch_ts(None)
    app = _build_app(_StubProjectService(detail))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/projects/{detail.id}")

    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert "implementation_launched_at" in body, (
        "REST ProjectResponse JSON dropped implementation_launched_at when value is null — "
        "frontend gate relies on property presence, not just truthiness."
    )
    assert body["implementation_launched_at"] is None
