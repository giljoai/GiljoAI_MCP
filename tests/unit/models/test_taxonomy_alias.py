# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Regression tests for taxonomy_alias as a SELECT-time column_property.

BE-5058: ``Project.taxonomy_alias`` (and the new ``Task.taxonomy_alias`` mirror)
must be resolvable on a freshly-fetched ORM instance WITHOUT eager-loading the
``taxonomy_types`` relationship. Before this fix, ``taxonomy_alias`` was a
Python ``@property`` that dereferenced ``self.project_type`` and triggered an
async lazy load -- crashing as ``MissingGreenlet`` whenever a sync consumer
read the field after the loader scope closed.

The fix promotes the alias to a ``column_property`` whose value is computed at
SELECT time via correlated subquery, so subsequent attribute access never
issues IO.

The tests below assert:
* alias resolves with no eager loading on Project (regression case)
* alias respects ``tenant_key`` isolation in the correlated subquery
* fallback to the random ``alias`` column when no taxonomy fields are set
* equivalent behaviour for Task.taxonomy_alias mirror, including ``subseries``
"""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.models import Product, Project
from giljo_mcp.models.projects import TaxonomyType
from giljo_mcp.models.tasks import Task
from giljo_mcp.tenant import TenantManager


async def _make_taxonomy(session: AsyncSession, tenant_key: str, abbreviation: str) -> TaxonomyType:
    tt = TaxonomyType(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        abbreviation=abbreviation,
        label=f"{abbreviation} Label",
        color="#607D8B",
    )
    session.add(tt)
    await session.flush()
    return tt


async def _make_product(session: AsyncSession, tenant_key: str) -> Product:
    product = Product(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        name="Test Product",
        description="taxonomy_alias regression product",
    )
    session.add(product)
    await session.flush()
    return product


@pytest.mark.asyncio
async def test_project_taxonomy_alias_resolves_without_eager_load(db_session: AsyncSession):
    """A project read back without ``joinedload(project_type)`` must still
    return the taxonomy alias without triggering a lazy load."""
    tenant_key = TenantManager.generate_tenant_key()
    tt = await _make_taxonomy(db_session, tenant_key, "BE")
    product = await _make_product(db_session, tenant_key)

    project = Project(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        product_id=product.id,
        name="Alias Project",
        description="desc",
        mission="mission",
        project_type_id=tt.id,
        series_number=42,
        subseries="a",
    )
    db_session.add(project)
    await db_session.commit()

    # Drop everything from the identity map so re-fetch is forced.
    db_session.expunge_all()

    stmt = select(Project).where(Project.id == project.id)
    result = await db_session.execute(stmt)
    fetched = result.scalar_one()

    # Sync attribute access -- must NOT trigger async lazy load.
    assert fetched.taxonomy_alias == "BE-0042a"


@pytest.mark.asyncio
async def test_project_taxonomy_alias_falls_back_to_random_alias(db_session: AsyncSession):
    tenant_key = TenantManager.generate_tenant_key()
    product = await _make_product(db_session, tenant_key)

    project = Project(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        product_id=product.id,
        name="Untaxed Project",
        description="desc",
        mission="mission",
        alias="abc123",
    )
    db_session.add(project)
    await db_session.commit()
    db_session.expunge_all()

    fetched = (await db_session.execute(select(Project).where(Project.id == project.id))).scalar_one()

    assert fetched.taxonomy_alias == "abc123"


@pytest.mark.asyncio
async def test_project_taxonomy_alias_abbreviation_only(db_session: AsyncSession):
    tenant_key = TenantManager.generate_tenant_key()
    tt = await _make_taxonomy(db_session, tenant_key, "FE")
    product = await _make_product(db_session, tenant_key)

    project = Project(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        product_id=product.id,
        name="Abbr Only",
        description="desc",
        mission="mission",
        project_type_id=tt.id,
    )
    db_session.add(project)
    await db_session.commit()
    db_session.expunge_all()

    fetched = (await db_session.execute(select(Project).where(Project.id == project.id))).scalar_one()
    assert fetched.taxonomy_alias == "FE"


@pytest.mark.asyncio
async def test_project_taxonomy_alias_series_no_subseries(db_session: AsyncSession):
    tenant_key = TenantManager.generate_tenant_key()
    tt = await _make_taxonomy(db_session, tenant_key, "API")
    product = await _make_product(db_session, tenant_key)

    project = Project(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        product_id=product.id,
        name="Series Only",
        description="desc",
        mission="mission",
        project_type_id=tt.id,
        series_number=7,
    )
    db_session.add(project)
    await db_session.commit()
    db_session.expunge_all()

    fetched = (await db_session.execute(select(Project).where(Project.id == project.id))).scalar_one()
    assert fetched.taxonomy_alias == "API-0007"


@pytest.mark.asyncio
async def test_project_taxonomy_alias_respects_tenant_key(db_session: AsyncSession):
    """The correlated taxonomy_types lookup MUST filter by tenant_key.

    A taxonomy row in tenant A with the same id as one in tenant B must not
    leak its abbreviation across the boundary. We simulate this by writing a
    project whose project_type_id points to an id from a different tenant --
    the correlated subquery should return NULL and the alias should fall back.
    """
    tenant_a = TenantManager.generate_tenant_key()
    tenant_b = TenantManager.generate_tenant_key()
    tt_a = await _make_taxonomy(db_session, tenant_a, "BE")
    product_b = await _make_product(db_session, tenant_b)

    project = Project(
        id=str(uuid.uuid4()),
        tenant_key=tenant_b,
        product_id=product_b.id,
        name="Cross Tenant",
        description="desc",
        mission="mission",
        project_type_id=tt_a.id,  # belongs to tenant_a, not tenant_b
        series_number=1,
        alias="zz9999",
    )
    db_session.add(project)
    await db_session.commit()
    db_session.expunge_all()

    fetched = (await db_session.execute(select(Project).where(Project.id == project.id))).scalar_one()
    # Abbreviation must NOT leak; alias should be just the series since the
    # tenant-scoped subquery returned NULL for the abbreviation.
    assert "BE" not in fetched.taxonomy_alias
    assert fetched.taxonomy_alias == "0001"


@pytest.mark.asyncio
async def test_task_taxonomy_alias_resolves_without_eager_load(db_session: AsyncSession):
    tenant_key = TenantManager.generate_tenant_key()
    tt = await _make_taxonomy(db_session, tenant_key, "BE")
    product = await _make_product(db_session, tenant_key)

    task = Task(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        product_id=product.id,
        title="Alias Task",
        task_type_id=tt.id,
        series_number=3,
        subseries="b",
    )
    db_session.add(task)
    await db_session.commit()
    db_session.expunge_all()

    fetched = (await db_session.execute(select(Task).where(Task.id == task.id))).scalar_one()
    assert fetched.taxonomy_alias == "BE-0003b"


@pytest.mark.asyncio
async def test_task_taxonomy_alias_no_taxonomy_returns_empty(db_session: AsyncSession):
    """A task with no taxonomy fields has no random fallback alias column;
    the alias should resolve to an empty string (or None coerced to '')."""
    tenant_key = TenantManager.generate_tenant_key()
    product = await _make_product(db_session, tenant_key)

    task = Task(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        product_id=product.id,
        title="Bare Task",
    )
    db_session.add(task)
    await db_session.commit()
    db_session.expunge_all()

    fetched = (await db_session.execute(select(Task).where(Task.id == task.id))).scalar_one()
    assert fetched.taxonomy_alias == ""


# ---------------------------------------------------------------------------
# BE-6049a: no-truncation display + SQL<->Python parity
# ---------------------------------------------------------------------------


def test_format_taxonomy_alias_helper_pads_min4_never_truncates():
    """Pure-function contract for the shared formatter."""
    from giljo_mcp.utils.taxonomy_alias import format_taxonomy_alias

    assert format_taxonomy_alias("BE", 17) == "BE-0017"
    assert format_taxonomy_alias("BE", 17, "a") == "BE-0017a"
    assert format_taxonomy_alias("BE", 1) == "BE-0001"
    assert format_taxonomy_alias("BE", 9999) == "BE-9999"
    # The bug this fixes: 5-/6-digit serials must render in FULL, not truncate.
    assert format_taxonomy_alias("BE", 10000) == "BE-10000"
    assert format_taxonomy_alias("TSK", 99999) == "TSK-99999"
    # Untyped / unnumbered / fallback branches mirror the SQL column_property.
    assert format_taxonomy_alias(None, 17) == "0017"
    assert format_taxonomy_alias("BE", None) == "BE"
    assert format_taxonomy_alias(None, None) == ""
    assert format_taxonomy_alias(None, None, fallback="abc123") == "abc123"
    assert format_taxonomy_alias("", None, fallback="abc123") == "abc123"


@pytest.mark.asyncio
async def test_project_taxonomy_alias_no_truncation_5_and_6_digits(db_session: AsyncSession):
    """A grandfathered 5-/6-digit serial must render in full (lpad bug regression).

    The old fixed ``lpad(..., 4, '0')`` truncated 10000 -> '1000'.
    """
    tenant_key = TenantManager.generate_tenant_key()
    tt = await _make_taxonomy(db_session, tenant_key, "BE")
    product = await _make_product(db_session, tenant_key)

    for series, expected in [(10000, "BE-10000"), (99999, "BE-99999")]:
        proj = Project(
            id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name=f"Big serial {series}",
            description="desc",
            mission="mission",
            project_type_id=tt.id,
            series_number=series,
        )
        db_session.add(proj)
        await db_session.commit()
        db_session.expunge_all()
        fetched = (await db_session.execute(select(Project).where(Project.id == proj.id))).scalar_one()
        assert fetched.taxonomy_alias == expected


@pytest.mark.asyncio
async def test_sql_and_python_alias_builders_are_in_parity(db_session: AsyncSession):
    """The SQL column_property and the Python helper MUST agree for every input.

    This is the cross-cutting risk the scope flags (two builders drifting).
    Creates a Project and a Task per boundary case and asserts the DB-rendered
    ``taxonomy_alias`` equals ``format_taxonomy_alias(...)``.
    """
    from giljo_mcp.utils.taxonomy_alias import format_taxonomy_alias

    tenant_key = TenantManager.generate_tenant_key()
    tt = await _make_taxonomy(db_session, tenant_key, "BE")
    product = await _make_product(db_session, tenant_key)

    cases = [
        (1, None),
        (42, "a"),
        (9999, None),
        (9999, "z"),
        (10000, None),
        (99999, "b"),
    ]
    for idx, (series, subseries) in enumerate(cases):
        proj = Project(
            id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name=f"Parity proj {idx}",
            description="desc",
            mission="mission",
            project_type_id=tt.id,
            series_number=series,
            subseries=subseries,
        )
        task = Task(
            id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            title=f"Parity task {idx}",
            task_type_id=tt.id,
            series_number=series,
            subseries=subseries,
        )
        db_session.add_all([proj, task])
        await db_session.commit()
        db_session.expunge_all()

        fetched_proj = (await db_session.execute(select(Project).where(Project.id == proj.id))).scalar_one()
        fetched_task = (await db_session.execute(select(Task).where(Task.id == task.id))).scalar_one()
        expected = format_taxonomy_alias("BE", series, subseries)
        assert fetched_proj.taxonomy_alias == expected, f"Project SQL!=Python for {series}{subseries}"
        assert fetched_task.taxonomy_alias == expected, f"Task SQL!=Python for {series}{subseries}"


@pytest.mark.asyncio
async def test_empty_abbreviation_renders_no_leading_dash(db_session: AsyncSession):
    """BE-6079 (L4): an EMPTY-string abbreviation must render ``0017``, not ``-0017``.

    The SQL builders previously keyed the separator dash on a merely NON-NULL
    abbreviation, so an empty-string abbr produced a stray leading dash that the
    Python helper (``sep = "-" if abbr else ""``) never emits. The ``nullif(abbr,
    '')`` guard collapses empty -> NULL so both builders agree. Abbreviations are
    regex-gated non-empty in normal flow, so this pins the theoretical edge.
    """
    from giljo_mcp.utils.taxonomy_alias import format_taxonomy_alias

    tenant_key = TenantManager.generate_tenant_key()
    tt = await _make_taxonomy(db_session, tenant_key, "")  # empty abbreviation
    product = await _make_product(db_session, tenant_key)

    proj = Project(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        product_id=product.id,
        name="Empty abbr",
        description="desc",
        mission="mission",
        project_type_id=tt.id,
        series_number=17,
    )
    task = Task(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        product_id=product.id,
        title="Empty abbr task",
        task_type_id=tt.id,
        series_number=17,
    )
    db_session.add_all([proj, task])
    await db_session.commit()
    db_session.expunge_all()

    fetched_proj = (await db_session.execute(select(Project).where(Project.id == proj.id))).scalar_one()
    fetched_task = (await db_session.execute(select(Task).where(Task.id == task.id))).scalar_one()
    expected = format_taxonomy_alias("", 17)
    assert expected == "0017"
    assert fetched_proj.taxonomy_alias == "0017", f"Project rendered {fetched_proj.taxonomy_alias!r}"
    assert fetched_task.taxonomy_alias == "0017", f"Task rendered {fetched_task.taxonomy_alias!r}"
