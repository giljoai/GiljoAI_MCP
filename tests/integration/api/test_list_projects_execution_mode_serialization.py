# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Regression guards for the REST project LIST endpoints.

Covers three failing layers on ``api/endpoints/projects/crud.py``:
  * ``execution_mode`` serialization (original BE-6052 500 — below);
  * IMP-1002 Task B — the dashboard list default-status filter (excludes
    archived rows, preserves the show-all path);
  * IMP-1002 Task C(a) — the thin ``ProjectListResponse`` wire shape omits
    per-row ``mission``/``description`` (payload trim).

Failing layer (execution_mode): the REST list/deleted endpoints map each
``ProjectListItem`` the service returns into a list-wire response model and
read ``proj.execution_mode``. Commit 9e4ce19a7 dropped the hardcoded
``"multi_terminal"`` in favor of ``proj.execution_mode`` but ``ProjectListItem``
was the one project schema without that field — so serializing ANY project list
raised ``AttributeError: 'ProjectListItem' object has no attribute
'execution_mode'`` and ``GET /api/v1/projects/`` 500'd in prod for every tenant
with projects.

These tests exercise the exact field-by-field mapping the endpoints perform, so
a future drop of ``execution_mode`` from ``ProjectListItem`` fails here instead
of in production. The service-layer list tests never caught it because the
service returns ``ProjectListItem`` fine; only the REST projection read the
missing attribute.

BE-1000d / CE-0038: the original ``_map_like_endpoint`` helper below is a *copy*
of the crud.py construction — it only catches a field dropped from the schema,
not a NEW ``proj.<attr>`` read that crud.py adds and the schema lacks (the exact
direction the BE-6052 bug shipped from). The ``test_list_endpoint_real_router_*``
tests at the bottom close that gap: they drive the REAL ``GET /api/v1/projects/``
and ``/deleted`` routes through the actual ``crud.py`` against the real
``ProjectListItem`` class, so ANY future schema/crud drift in either direction
500s in CI instead of in prod. ``ProjectListItem`` is intentionally kept
standalone (NOT inheriting ``ProjectBase`` — its timestamps are required and it
omits ``auto_checkin_*``); this endpoint guard, not inheritance, is what prevents
the drift.
"""

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.endpoints.projects import router as projects_router
from api.endpoints.projects.dependencies import get_project_service
from api.endpoints.projects.models import ProjectListResponse
from giljo_mcp.auth.dependencies import get_current_active_user
from giljo_mcp.schemas.responses.project import ProjectListItem


def _list_item(execution_mode: str | None) -> ProjectListItem:
    """Build a ProjectListItem the way ProjectService.list_projects() does."""
    return ProjectListItem(
        id="11111111-1111-1111-1111-111111111111",
        name="Regression Project",
        mission="do the thing",
        description="desc",
        status="active",
        staging_status=None,
        implementation_launched_at=None,
        execution_mode=execution_mode,
        tenant_key="tk_test",
        product_id="22222222-2222-2222-2222-222222222222",
        created_at=datetime.now(UTC).isoformat(),
        updated_at=datetime.now(UTC).isoformat(),
        completed_at=None,
        project_type_id=None,
        project_type=None,
        series_number=None,
        subseries=None,
        taxonomy_alias=None,
        hidden=False,
    )


def _map_like_endpoint(proj: ProjectListItem) -> ProjectListResponse:
    """Mirror the crud.py list/deleted-endpoint thin-wire construction.

    IMP-1002: the list endpoints emit ``ProjectListResponse`` (no per-row
    mission/description); this helper mirrors that mapping exactly.
    """
    return ProjectListResponse(
        id=proj.id,
        alias="",
        name=proj.name,
        status=proj.status,
        staging_status=proj.staging_status,
        product_id=proj.product_id,
        created_at=proj.created_at,
        updated_at=proj.updated_at,
        completed_at=None,
        implementation_launched_at=None,
        agent_count=0,
        message_count=0,
        agents=[],
        execution_mode=proj.execution_mode,  # the line that 500'd in prod (BE-6052)
        project_type_id=proj.project_type_id,
        project_type=proj.project_type,
        series_number=proj.series_number,
        subseries=proj.subseries,
        taxonomy_alias=proj.taxonomy_alias,
        hidden=getattr(proj, "hidden", False),
    )


def test_project_list_item_has_execution_mode():
    """The attribute the REST list endpoints read must exist."""
    assert hasattr(_list_item(None), "execution_mode")


def test_list_endpoint_mapping_with_null_execution_mode():
    """NULL execution_mode (born-without-mode project) serializes, no crash."""
    resp = _map_like_endpoint(_list_item(None))
    assert resp.execution_mode is None


def test_list_endpoint_mapping_with_selected_execution_mode():
    """A chosen mode flows through honestly (no fabricated default)."""
    resp = _map_like_endpoint(_list_item("claude_code_cli"))
    assert resp.execution_mode == "claude_code_cli"


# ---------------------------------------------------------------------------
# BE-1000d / CE-0038 — REAL-router drift guard.
#
# Drives the actual ``GET /api/v1/projects/`` and ``/deleted`` routes through
# the real ``crud.py`` projection against the real ``ProjectListItem`` class.
# This is the guard that catches the crud.py-read -> schema-missing-field
# direction: if a future edit makes crud.py read ``proj.<attr>`` that
# ``ProjectListItem`` does not declare, serialization AttributeErrors and the
# route 500s here in CI instead of in prod (the BE-6052 failure mode).
#
# A static field-name list would NOT catch that direction — only the real
# endpoint running real crud.py does. The fail-direction self-check: remove
# ``execution_mode`` from ``ProjectListItem`` (a DIRECT ``proj.execution_mode``
# read, not the ``getattr``-guarded ``hidden``) and these two tests go red (500).
# ---------------------------------------------------------------------------


_GUARD_TENANT = "tenant-be1000d-guard"


class _FakeUser:
    id = "user-be1000d-guard"
    username = "be1000d_guard_tester"
    tenant_key = _GUARD_TENANT


class _StubProjectService:
    """Returns real ``ProjectListItem`` instances so the real crud.py
    projection runs against the real schema class. Signature accepts both the
    list call (``include_cancelled=True``) and the ``/deleted`` call shape."""

    def __init__(self, items: list[ProjectListItem]) -> None:
        self._items = items

    async def list_projects(
        self,
        status: str | None = None,
        tenant_key: str | None = None,
        include_cancelled: bool = False,
        product_id: str | None = None,
        hidden: bool | None = None,
        # BE-6076: the endpoint now forwards opt-in search/sort/pagination args.
        search: str | None = None,
        sort_key: str | None = None,
        sort_dir: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[ProjectListItem]:
        return self._items

    async def count_projects(self, **_kwargs) -> int:
        # BE-6076: only invoked on the paginated path; the default-path tests
        # here never pass limit/offset, so this stub total is unused.
        return len(self._items)


def _build_app(stub_service: _StubProjectService) -> FastAPI:
    app = FastAPI()
    app.include_router(projects_router)

    async def _override_user() -> _FakeUser:
        return _FakeUser()

    async def _override_service() -> AsyncIterator[_StubProjectService]:
        yield stub_service

    app.dependency_overrides[get_current_active_user] = _override_user
    app.dependency_overrides[get_project_service] = _override_service
    return app


def _fully_populated_item() -> ProjectListItem:
    """Every mapped field populated (no NULLs that could mask a missing read)."""
    now = datetime.now(UTC).isoformat()
    return ProjectListItem(
        id="33333333-3333-3333-3333-333333333333",
        name="Real-router Guard Project",
        mission="exercise the real endpoint",
        description="full population",
        status="active",
        staging_status="staging_complete",
        implementation_launched_at=now,
        execution_mode="claude_code_cli",
        tenant_key=_GUARD_TENANT,
        product_id="44444444-4444-4444-4444-444444444444",
        created_at=now,
        updated_at=now,
        completed_at=None,
        project_type_id="55555555-5555-5555-5555-555555555555",
        project_type=None,
        series_number=7,
        subseries="a",
        taxonomy_alias="BE-0007a",
        hidden=False,
    )


@pytest.mark.asyncio
async def test_list_endpoint_real_router_serializes() -> None:
    """``GET /api/v1/projects/`` runs real crud.py against ProjectListItem and
    returns 200 — any crud.py-read the schema lacks would 500 here."""
    app = _build_app(_StubProjectService([_fully_populated_item()]))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/projects/")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    assert body[0]["execution_mode"] == "claude_code_cli"


@pytest.mark.asyncio
async def test_deleted_endpoint_real_router_serializes() -> None:
    """``GET /api/v1/projects/deleted`` runs the real crud.py projection too;
    it reads the same ``proj.<attr>`` set, so it gets the same guard."""
    app = _build_app(_StubProjectService([_fully_populated_item()]))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/projects/deleted")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    assert body[0]["execution_mode"] == "claude_code_cli"


# ---------------------------------------------------------------------------
# IMP-1002 Task C(a) — list-wire payload-shape guard.
#
# The dashboard list payload grew monotonically with project count (~434 rows)
# because each row shipped the full ``mission``/``description`` free text. The
# REST list endpoints now emit the thin ``ProjectListResponse`` wire shape that
# OMITS those two fields; the bodies are fetched lazily on row-open via the
# single-project detail endpoint (``ProjectResponse``). The shared internal
# ``ProjectListItem`` projection KEEPS both fields (the MCP ``list_projects``
# planning/audit/forensic modes read them) — only the REST wire is thinned.
#
# These tests drive the REAL routes: the stub returns items with non-empty
# mission/description, and we assert they never reach the wire. A future re-add
# of either field to the list mapping re-inflates the payload and fails here.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_wire_omits_mission_and_description() -> None:
    """``GET /api/v1/projects/`` list rows carry no mission/description."""
    app = _build_app(_StubProjectService([_fully_populated_item()]))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/projects/")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    row = body[0]
    assert "mission" not in row, "list wire must not ship per-row mission"
    assert "description" not in row, "list wire must not ship per-row description"
    # Identity/badge fields the dashboard list still renders survive the trim.
    assert row["name"] == "Real-router Guard Project"
    assert row["taxonomy_alias"] == "BE-0007a"
    assert row["status"] == "active"


@pytest.mark.asyncio
async def test_deleted_wire_omits_mission_and_description() -> None:
    """``GET /api/v1/projects/deleted`` mirrors the thin list wire shape."""
    app = _build_app(_StubProjectService([_fully_populated_item()]))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/projects/deleted")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    row = body[0]
    assert "mission" not in row
    assert "description" not in row


def test_list_wire_model_drops_body_fields() -> None:
    """``ProjectListResponse`` (the list wire shape) has no mission/description
    field at all — the mapping cannot accidentally re-emit them."""
    fields = set(ProjectListResponse.model_fields)
    assert "mission" not in fields
    assert "description" not in fields


# ---------------------------------------------------------------------------
# IMP-1002 Task B — REST list endpoint default-filter guard.
#
# ``GET /api/v1/projects/`` is the dashboard list. Pre-IMP-1002 it passed
# ``status=None, include_cancelled=True`` whenever no explicit filter was
# given, so completed/cancelled/terminated/deleted rows inflated every reload.
# It now defaults to the SAME active-lifecycle exclusion the MCP
# ``list_projects`` tool applies (``LIFECYCLE_FINISHED_STATUSES`` complement),
# while preserving an explicit ``include_completed=true`` show-all path and an
# explicit ``status_filter`` override. These tests capture the exact ``status``
# argument crud.py hands the service so a future regression of the default
# (or loss of the show-all escape hatch) fails here instead of silently
# re-inflating the dashboard payload in prod.
# ---------------------------------------------------------------------------


class _CapturingProjectService:
    """Records the ``status``/``include_cancelled`` args crud.py passes so the
    endpoint's default-filter wiring is asserted at the real-router boundary."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def list_projects(
        self,
        status=None,
        tenant_key: str | None = None,
        include_cancelled: bool = False,
        product_id: str | None = None,
        hidden: bool | None = None,
        # BE-6076: opt-in search/sort/pagination args forwarded by the endpoint.
        search: str | None = None,
        sort_key: str | None = None,
        sort_dir: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[ProjectListItem]:
        self.calls.append(
            {
                "status": status,
                "tenant_key": tenant_key,
                "include_cancelled": include_cancelled,
                "product_id": product_id,
                "hidden": hidden,
                "search": search,
                "sort_key": sort_key,
                "sort_dir": sort_dir,
                "limit": limit,
                "offset": offset,
            }
        )
        return []

    async def count_projects(self, **_kwargs) -> int:
        return 0


@pytest.mark.asyncio
async def test_list_default_excludes_archived_statuses() -> None:
    """Default (no params) passes the active-lifecycle complement as a status
    list — completed/cancelled/terminated/deleted are excluded."""
    svc = _CapturingProjectService()
    app = _build_app(svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/projects/")
    assert resp.status_code == 200, resp.text

    passed_status = svc.calls[0]["status"]
    assert isinstance(passed_status, list)
    for archived in ("completed", "cancelled", "terminated", "deleted", "superseded"):
        assert archived not in passed_status, f"default list must exclude {archived}"
    assert "active" in passed_status
    # BE-6078: hidden is excluded server-side by default (False, not None).
    assert svc.calls[0]["hidden"] is False, "default list must exclude hidden rows"


@pytest.mark.asyncio
async def test_list_include_completed_shows_all() -> None:
    """``include_completed=true`` preserves the show-all path: status falls
    back to None so the repo returns archived buckets too."""
    svc = _CapturingProjectService()
    app = _build_app(svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/projects/?include_completed=true")
    assert resp.status_code == 200, resp.text

    assert svc.calls[0]["status"] is None
    assert svc.calls[0]["include_cancelled"] is True
    # BE-6078: the show-all path still excludes hidden unless asked otherwise.
    assert svc.calls[0]["hidden"] is False


@pytest.mark.asyncio
async def test_list_explicit_status_filter_overrides_default() -> None:
    """An explicit ``status_filter`` wins over the active-lifecycle default and
    is forwarded verbatim (even an archived value the default would exclude)."""
    svc = _CapturingProjectService()
    app = _build_app(svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/projects/?status_filter=completed")
    assert resp.status_code == 200, resp.text

    assert svc.calls[0]["status"] == "completed"


# ---------------------------------------------------------------------------
# BE-6078 — hidden server-side offload + completed_at emission.
#
# The Projects page now lists finished projects (include_completed=true) and
# the hidden flag is filtered SERVER-side instead of shipping every hidden row
# over the wire to be dropped in JS. "Show hidden" is a pure read view
# (hidden_only=true) that LISTS hidden rows — it never re-tags. These guards pin
# the exact hidden filter crud.py hands the service for each param combination,
# and that the list serializer emits the real completed_at (un-hardcoded).
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_default_excludes_hidden() -> None:
    """Default (no hidden params) → hidden=False (exclude hidden server-side)."""
    svc = _CapturingProjectService()
    app = _build_app(svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/projects/")
    assert resp.status_code == 200, resp.text
    assert svc.calls[0]["hidden"] is False


@pytest.mark.asyncio
async def test_list_hidden_only_returns_hidden() -> None:
    """``hidden_only=true`` → hidden=True (the 'Show hidden' view lists hidden
    rows); paired with include_completed=true it spans all lifecycle statuses."""
    svc = _CapturingProjectService()
    app = _build_app(svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/projects/?hidden_only=true&include_completed=true")
    assert resp.status_code == 200, resp.text
    assert svc.calls[0]["hidden"] is True
    assert svc.calls[0]["status"] is None


@pytest.mark.asyncio
async def test_list_include_hidden_returns_both() -> None:
    """``include_hidden=true`` (without hidden_only) → hidden=None (both)."""
    svc = _CapturingProjectService()
    app = _build_app(svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/projects/?include_hidden=true")
    assert resp.status_code == 200, resp.text
    assert svc.calls[0]["hidden"] is None


@pytest.mark.asyncio
async def test_hidden_only_wins_over_include_hidden() -> None:
    """When both are set, hidden_only is authoritative → hidden=True."""
    svc = _CapturingProjectService()
    app = _build_app(svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/projects/?include_hidden=true&hidden_only=true")
    assert resp.status_code == 200, resp.text
    assert svc.calls[0]["hidden"] is True


@pytest.mark.asyncio
async def test_list_emits_real_completed_at() -> None:
    """BE-6078: the list serializer emits the real ``completed_at`` (was
    hard-coded to None at crud.py:220), so the Completed column/sort is accurate
    once finished projects are listable."""
    completed_iso = datetime(2026, 6, 9, 12, 0, tzinfo=UTC).isoformat()
    item = ProjectListItem(
        id="66666666-6666-6666-6666-666666666666",
        name="Finished Project",
        mission="m",
        description="d",
        status="completed",
        staging_status=None,
        implementation_launched_at=None,
        execution_mode="claude_code_cli",
        tenant_key=_GUARD_TENANT,
        product_id="44444444-4444-4444-4444-444444444444",
        created_at=datetime(2026, 6, 1, tzinfo=UTC).isoformat(),
        updated_at=datetime(2026, 6, 9, tzinfo=UTC).isoformat(),
        completed_at=completed_iso,
        project_type_id=None,
        project_type=None,
        series_number=8,
        subseries=None,
        taxonomy_alias="BE-0008",
        hidden=False,
    )
    app = _build_app(_StubProjectService([item]))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/projects/?include_completed=true")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    assert body[0]["completed_at"] is not None, "completed_at must not be hard-coded to None"
    assert body[0]["completed_at"].startswith("2026-06-09")
