# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6076 — server-side projects-list pagination + search/filter/sort in SQL.

Regression tests at the failing layer:

* Repository layer (real DB): the SQL pushdown lives in
  ``ProjectRepository.list_projects`` / ``count_projects`` — pagination
  (limit/offset), whitelisted sort, substring search, and a filtered COUNT that
  reflects the same WHERE as the page (never the unfiltered table size).
* Endpoint layer (stub service): the default (no limit/offset) path returns the
  bare ``list[ProjectListResponse]`` byte-compatibly and the filtered total is
  carried out-of-band on the ``X-Total-Count`` header; the paginated path drives
  the COUNT; the multi-status `statuses` param flows through.

Edition Scope: Both.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.endpoints.projects import router as projects_router
from api.endpoints.projects.dependencies import get_project_service
from giljo_mcp.auth.dependencies import get_current_active_user
from giljo_mcp.database import tenant_session_context
from giljo_mcp.models import Product, Project
from giljo_mcp.models.projects import TaxonomyType
from giljo_mcp.repositories.project_repository import ProjectRepository
from giljo_mcp.tenant import TenantManager


# ---------------------------------------------------------------------------
# Repository-layer fixture: a deterministic, tenant-scoped project set
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="function")
async def seeded_projects(db_session):
    """Seed one tenant/product with a known project set for SQL-side assertions.

    6 inactive rows (varied name/series/created_at), 1 hidden inactive row, and 1
    completed row — so search, hidden, status, sort, and pagination each have a
    distinguishable target. Status is ``inactive`` (not ``active``) because a
    partial unique index allows only ONE active project per product.
    """
    tenant = TenantManager.generate_tenant_key()
    product = Product(
        id=str(uuid.uuid4()),
        name="BE-6076 Product",
        description="seed",
        tenant_key=tenant,
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()

    be_type = TaxonomyType(id=str(uuid.uuid4()), tenant_key=tenant, abbreviation="BE", label="Backend")
    db_session.add(be_type)
    await db_session.commit()

    base = datetime(2026, 1, 1, tzinfo=UTC)

    def _proj(name, series, status="inactive", hidden=False, day=1, completed=None):
        return Project(
            id=str(uuid.uuid4()),
            name=name,
            description="d",
            mission="m",
            tenant_key=tenant,
            product_id=product.id,
            status=status,
            hidden=hidden,
            project_type_id=be_type.id,
            series_number=series,
            created_at=base.replace(day=day),
            completed_at=completed,
        )

    rows = [
        _proj("Alpha login", 5001, day=1),
        _proj("Bravo cache", 5002, day=2),
        _proj("Charlie api", 5003, day=3),
        _proj("Delta alpha sync", 5004, day=4),
        _proj("Echo queue", 5005, day=5),
        _proj("Foxtrot ui", 5006, day=6),
        _proj("Hidden ghost", 5007, hidden=True, day=7),
        _proj("Zulu done", 5008, status="completed", day=8, completed=base.replace(day=9)),
    ]
    db_session.add_all(rows)
    await db_session.commit()
    for r in rows:
        await db_session.refresh(r)

    return {"tenant": tenant, "product": product, "type": be_type, "rows": rows}


# A repo bound to nothing — list/count take the session explicitly.
_REPO = ProjectRepository()

_ACTIVE_STATUSES = ["active", "inactive", "completed", "cancelled", "terminated"]


# ---------------------------------------------------------------------------
# Backward-compat: default path (no new params) is unchanged
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_default_path_no_pagination_returns_full_set(db_session, seeded_projects):
    """No limit/offset/search/sort -> the exact pre-BE-6076 result set.

    Visible (hidden excluded) active-lifecycle rows = the 6 visible active rows
    + the completed row, but NOT the hidden one when hidden=False is applied by
    the caller. Here we call with status=None default semantics (bare tenant,
    include_cancelled) which returns ALL non-deleted rows including hidden —
    pinning that the new optional args do not perturb that contract.
    """
    tenant = seeded_projects["tenant"]
    product = seeded_projects["product"]

    rows = await _REPO.list_projects(db_session, tenant, include_cancelled=True, product_id=product.id)
    # All 8 non-deleted rows (hidden included — hidden=None default), no slice.
    assert len(rows) == 8
    # No ORDER BY is forced on the default path: result is the full set.
    assert {r.name for r in rows} == {
        "Alpha login",
        "Bravo cache",
        "Charlie api",
        "Delta alpha sync",
        "Echo queue",
        "Foxtrot ui",
        "Hidden ghost",
        "Zulu done",
    }


# ---------------------------------------------------------------------------
# Pagination (limit/offset) + sort applied in SQL
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pagination_slices_sorted_page(db_session, seeded_projects):
    tenant = seeded_projects["tenant"]
    product = seeded_projects["product"]

    page1 = await _REPO.list_projects(
        db_session,
        tenant,
        status=_ACTIVE_STATUSES,
        product_id=product.id,
        sort_key="series_number",
        sort_dir="asc",
        limit=3,
        offset=0,
    )
    page2 = await _REPO.list_projects(
        db_session,
        tenant,
        status=_ACTIVE_STATUSES,
        product_id=product.id,
        sort_key="series_number",
        sort_dir="asc",
        limit=3,
        offset=3,
    )
    assert [r.series_number for r in page1] == [5001, 5002, 5003]
    assert [r.series_number for r in page2] == [5004, 5005, 5006]
    # No row appears on both pages (stable, non-overlapping boundary).
    assert not ({r.id for r in page1} & {r.id for r in page2})


@pytest.mark.asyncio
async def test_sort_desc_applied_in_sql(db_session, seeded_projects):
    """Sort happens in SQL: the rows come back ordered without any Python sort."""
    tenant = seeded_projects["tenant"]
    product = seeded_projects["product"]

    rows = await _REPO.list_projects(
        db_session,
        tenant,
        status=_ACTIVE_STATUSES,
        product_id=product.id,
        sort_key="name",
        sort_dir="desc",
    )
    names = [r.name for r in rows]
    assert names == sorted(names, reverse=True), f"rows not SQL-sorted desc: {names}"


# ---------------------------------------------------------------------------
# FE-6179: roadmap-order sort (mirrors /roadmap's roadmap_items.sort_order)
# ---------------------------------------------------------------------------


async def _seed_roadmap(db_session, tenant, product, ordered_projects):
    """Place ``ordered_projects`` on the product roadmap, in the given order.

    ``ordered_projects`` is a list of Project rows; their roadmap ``sort_order``
    is assigned 0,1,2,... in list order. Returns the Roadmap row. Projects not in
    the list are intentionally left OFF the roadmap (to exercise the NULLS-last
    fallback). Mirrors how /roadmap stores ordering (RoadmapService writes
    sort_order; get_roadmap reads ORDER BY sort_order ASC).
    """
    from giljo_mcp.models.roadmaps import Roadmap, RoadmapItem

    roadmap = Roadmap(id=str(uuid.uuid4()), tenant_key=tenant, product_id=product.id)
    db_session.add(roadmap)
    await db_session.commit()

    for position, proj in enumerate(ordered_projects):
        db_session.add(
            RoadmapItem(
                id=str(uuid.uuid4()),
                tenant_key=tenant,
                roadmap_id=roadmap.id,
                item_type="project",
                project_id=proj.id,
                sort_order=position,
            )
        )
    await db_session.commit()
    return roadmap


@pytest.mark.asyncio
async def test_roadmap_sort_matches_roadmap_item_order(db_session, seeded_projects):
    """sort_key='roadmap' returns projects in roadmap_items.sort_order -- the
    SAME ordering /roadmap renders (ORDER BY sort_order ASC)."""
    tenant = seeded_projects["tenant"]
    product = seeded_projects["product"]
    rows = seeded_projects["rows"]

    # Deliberately roadmap-order them OPPOSITE to series_number / created_at so a
    # passing assertion can only come from the roadmap ordering, not a fallback.
    # rows[0..5] are the 6 visible inactive projects; place a 4-project subset on
    # the roadmap in a scrambled order, leaving two off the roadmap.
    roadmap_order = [rows[3], rows[0], rows[5], rows[2]]  # Delta, Alpha, Foxtrot, Charlie
    await _seed_roadmap(db_session, tenant, product, roadmap_order)

    page = await _REPO.list_projects(
        db_session,
        tenant,
        status=_ACTIVE_STATUSES,
        product_id=product.id,
        hidden=False,
        sort_key="roadmap",
        sort_dir="asc",
    )

    on_roadmap_ids = {p.id for p in roadmap_order}
    leading = [r for r in page if r.id in on_roadmap_ids]
    # The on-roadmap projects appear first, in exactly their sort_order sequence.
    assert [r.id for r in leading] == [p.id for p in roadmap_order]
    assert [r.name for r in leading] == [
        "Delta alpha sync",
        "Alpha login",
        "Foxtrot ui",
        "Charlie api",
    ]


@pytest.mark.asyncio
async def test_roadmap_sort_places_off_roadmap_projects_last(db_session, seeded_projects):
    """Projects not on the roadmap (no roadmap_item) sort AFTER every on-roadmap
    project (NULLS-last), so the sort never drops or mis-leads them."""
    tenant = seeded_projects["tenant"]
    product = seeded_projects["product"]
    rows = seeded_projects["rows"]

    on_roadmap = [rows[2], rows[0]]  # Charlie, Alpha
    await _seed_roadmap(db_session, tenant, product, on_roadmap)
    on_roadmap_ids = {p.id for p in on_roadmap}

    page = await _REPO.list_projects(
        db_session,
        tenant,
        status=_ACTIVE_STATUSES,
        product_id=product.id,
        hidden=False,  # mirrors the UI default (Show hidden off)
        sort_key="roadmap",
        sort_dir="asc",
    )

    # The first len(on_roadmap) rows are the on-roadmap subset in sort_order; the
    # rest (off-roadmap) trail behind and the count is unchanged (nothing dropped).
    assert [r.id for r in page[: len(on_roadmap)]] == [p.id for p in on_roadmap]
    assert all(r.id not in on_roadmap_ids for r in page[len(on_roadmap) :])
    assert len(page) == 7  # 6 visible inactive + 1 completed (hidden ghost excluded)


@pytest.mark.asyncio
async def test_roadmap_sort_is_tenant_scoped(db_session, seeded_projects):
    """A roadmap_item from ANOTHER tenant never bleeds into this tenant's sort
    (ADR-009): the correlated subquery is tenant_key-scoped."""
    from giljo_mcp.models.roadmaps import Roadmap, RoadmapItem

    tenant = seeded_projects["tenant"]
    product = seeded_projects["product"]
    rows = seeded_projects["rows"]

    # Seed the FOREIGN tenant FIRST: it plants one of OUR project ids (Alpha) at
    # sort_order 0 on its own roadmap. If the subquery were not tenant-scoped,
    # Alpha (0) would leapfrog Echo (5) to the front. Seeded first so the LAST
    # flush before the read leaves the session's (flush-derived) tenant context
    # on OUR tenant -- the guard then lets the explicit predicate authorize.
    other_tenant = TenantManager.generate_tenant_key()
    other_product = Product(
        id=str(uuid.uuid4()),
        name="Foreign Product",
        description="x",
        tenant_key=other_tenant,
        is_active=True,
    )
    db_session.add(other_product)
    await db_session.commit()
    other_roadmap = Roadmap(id=str(uuid.uuid4()), tenant_key=other_tenant, product_id=other_product.id)
    db_session.add(other_roadmap)
    await db_session.commit()
    db_session.add(
        RoadmapItem(
            id=str(uuid.uuid4()),
            tenant_key=other_tenant,
            roadmap_id=other_roadmap.id,
            item_type="project",
            project_id=rows[0].id,  # OUR Alpha, planted under the foreign tenant
            sort_order=0,
        )
    )
    await db_session.commit()

    # THIS tenant's roadmap has a single item -- Echo at a LATE sort_order (5).
    # Committed LAST so session.info["tenant_key"] == our tenant for the read.
    our_roadmap = Roadmap(id=str(uuid.uuid4()), tenant_key=tenant, product_id=product.id)
    db_session.add(our_roadmap)
    await db_session.commit()
    db_session.add(
        RoadmapItem(
            id=str(uuid.uuid4()),
            tenant_key=tenant,
            roadmap_id=our_roadmap.id,
            item_type="project",
            project_id=rows[4].id,  # Echo
            sort_order=5,
        )
    )
    await db_session.commit()

    # Read under an explicit ("service") tenant context for OUR tenant. The
    # cross-tenant inserts above leave the session's tenant context flush-derived,
    # which the guard refuses to let authorize an explicit predicate; this anchors
    # it to our tenant (the same thing the real service-session path does).
    with tenant_session_context(db_session, tenant):
        page = await _REPO.list_projects(
            db_session,
            tenant,
            status=_ACTIVE_STATUSES,
            product_id=product.id,
            hidden=False,
            sort_key="roadmap",
            sort_dir="asc",
        )
    # Echo is the ONLY project on THIS tenant's roadmap, so it leads despite its
    # late sort_order. The foreign Alpha row is invisible here -> Alpha is treated
    # as off-roadmap and never promoted ahead of Echo.
    assert page[0].id == rows[4].id  # Echo leads; cross-tenant Alpha was ignored


# ---------------------------------------------------------------------------
# Filtered COUNT reflects the filter, not the table size
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_count_reflects_search_not_unfiltered(db_session, seeded_projects):
    tenant = seeded_projects["tenant"]
    product = seeded_projects["product"]

    # "alpha" matches "Alpha login" + "Delta alpha sync" (case-insensitive).
    total = await _REPO.count_projects(
        db_session, tenant, status=_ACTIVE_STATUSES, product_id=product.id, search="alpha"
    )
    assert total == 2, "count must reflect the search filter, not the full set"

    page = await _REPO.list_projects(
        db_session,
        tenant,
        status=_ACTIVE_STATUSES,
        product_id=product.id,
        search="alpha",
        sort_key="series_number",
        sort_dir="asc",
        limit=10,
        offset=0,
    )
    assert {r.name for r in page} == {"Alpha login", "Delta alpha sync"}
    assert len(page) == total, "page rows must agree with the filtered count"


@pytest.mark.asyncio
async def test_search_matches_taxonomy_alias(db_session, seeded_projects):
    """Search hits the computed taxonomy_alias column_property (e.g. 'BE-5004')."""
    tenant = seeded_projects["tenant"]
    product = seeded_projects["product"]

    rows = await _REPO.list_projects(
        db_session, tenant, status=_ACTIVE_STATUSES, product_id=product.id, search="BE-5004"
    )
    assert {r.name for r in rows} == {"Delta alpha sync"}


@pytest.mark.asyncio
async def test_count_reflects_hidden_filter(db_session, seeded_projects):
    tenant = seeded_projects["tenant"]
    product = seeded_projects["product"]

    visible = await _REPO.count_projects(
        db_session, tenant, status=_ACTIVE_STATUSES, product_id=product.id, hidden=False
    )
    only_hidden = await _REPO.count_projects(
        db_session, tenant, status=_ACTIVE_STATUSES, product_id=product.id, hidden=True
    )
    # 7 visible active-lifecycle rows (6 active + 1 completed); 1 hidden.
    assert visible == 7
    assert only_hidden == 1


@pytest.mark.asyncio
async def test_count_matches_page_total_across_pages(db_session, seeded_projects):
    """Sum of paged rows equals the filtered count — the items-length contract."""
    tenant = seeded_projects["tenant"]
    product = seeded_projects["product"]

    total = await _REPO.count_projects(db_session, tenant, status=_ACTIVE_STATUSES, product_id=product.id, hidden=False)
    collected = []
    offset = 0
    while True:
        page = await _REPO.list_projects(
            db_session,
            tenant,
            status=_ACTIVE_STATUSES,
            product_id=product.id,
            hidden=False,
            sort_key="series_number",
            sort_dir="asc",
            limit=2,
            offset=offset,
        )
        if not page:
            break
        collected.extend(page)
        offset += 2
    assert len(collected) == total
    assert len({r.id for r in collected}) == total, "no duplicate rows across pages"


# ---------------------------------------------------------------------------
# Endpoint layer — backward-compat body + X-Total-Count header
# ---------------------------------------------------------------------------


_FAKE_TENANT = "tenant-be6076"


class _FakeUser:
    id = "user-be6076"
    username = "be6076_tester"
    tenant_key = _FAKE_TENANT


class _StubProjectService:
    """Captures list/count calls and returns canned ProjectListItem rows."""

    def __init__(self, items):
        self._items = items
        self.list_calls: list[dict] = []
        self.count_calls: list[dict] = []

    async def list_projects(self, **kwargs):
        self.list_calls.append(kwargs)
        return list(self._items)

    async def count_projects(self, **kwargs):
        self.count_calls.append(kwargs)
        return 137  # a sentinel total distinct from len(items)


def _item(name="P", status="active"):
    from giljo_mcp.schemas.service_responses import ProjectListItem

    now = datetime(2026, 1, 1, tzinfo=UTC).isoformat()
    return ProjectListItem(
        id=str(uuid.uuid4()),
        name=name,
        mission="",
        description="",
        status=status,
        staging_status=None,
        tenant_key=_FAKE_TENANT,
        product_id="prod-1",
        created_at=now,
        updated_at=now,
        completed_at=None,
        execution_mode=None,
        project_type_id=None,
        project_type=None,
        series_number=1,
        subseries=None,
        taxonomy_alias="abc123",
        hidden=False,
    )


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


@pytest.mark.asyncio
async def test_endpoint_default_path_body_is_bare_list_and_header_is_len():
    """Default (no limit/offset): body is the bare list (backward-compat), no
    extra COUNT query, and X-Total-Count == number of rows returned."""
    stub = _StubProjectService([_item("A"), _item("B")])
    app = _build_app(stub)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/projects/")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body, list) and len(body) == 2
    assert resp.headers["X-Total-Count"] == "2"
    # No pagination -> count_projects must NOT be invoked (single query path).
    assert stub.count_calls == [], "default path must not run the extra COUNT query"


@pytest.mark.asyncio
async def test_endpoint_paginated_path_uses_filtered_count_header():
    """With limit/offset: X-Total-Count comes from count_projects (the filtered
    total), and the same search/status filters flow to BOTH list and count."""
    stub = _StubProjectService([_item("A")])
    app = _build_app(stub)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/projects/",
            params={
                "limit": 10,
                "offset": 0,
                "search": "alpha",
                "statuses": ["active", "inactive"],
                "sort": "series_number",
                "sort_dir": "desc",
            },
        )
    assert resp.status_code == 200, resp.text
    assert resp.headers["X-Total-Count"] == "137", "paginated total must come from count_projects"

    # search + multi-status flow to the page query...
    list_kwargs = stub.list_calls[-1]
    assert list_kwargs["search"] == "alpha"
    assert list_kwargs["status"] == ["active", "inactive"]
    assert list_kwargs["limit"] == 10
    assert list_kwargs["sort_key"] == "series_number"
    assert list_kwargs["sort_dir"] == "desc"
    # ...and the SAME filters flow to the count (so the total matches the page).
    count_kwargs = stub.count_calls[-1]
    assert count_kwargs["search"] == "alpha"
    assert count_kwargs["status"] == ["active", "inactive"]
    # count takes no sort/limit/offset
    assert "limit" not in count_kwargs and "sort_key" not in count_kwargs
