# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""TSK-9163 regression: update_task 500 on a due_date write via the MCP surface.

Edition Scope: Both.

The @mcp.tool update_task wrapper delivers ``due_date`` as an ISO 8601 STRING
(the MCP param is typed str). ``update_task_for_mcp`` passed it through
unparsed, ``_update_task_impl`` setattr'd the raw string onto the
``DateTime(timezone=True)`` column, and asyncpg rejected the str at commit —
wrapped by the service boundary into the generic internal-error envelope.
The REST PATCH path never hit this because Pydantic's ``TaskUpdate.due_date:
datetime | None`` parses the string before the service sees it.

Field-level, not row-specific: the original report blamed a legacy-shaped row
(TSK-6010, created 2026-05-29) because that was the only row a due_date write
was ever tried on via MCP. Both a faithful legacy-shaped row AND a fresh row
are pinned here.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select

from giljo_mcp.database import tenant_session_context
from giljo_mcp.exceptions import ValidationError
from giljo_mcp.models import Task
from giljo_mcp.services.taxonomy_service import TaxonomyService


pytestmark = pytest.mark.asyncio


async def _insert_legacy_shaped_task(db_session, tenant_key: str, product_id: str) -> str:
    """Insert a task row shaped like the 2026-05 era (TSK-6010): direct ORM
    insert with an old created_at, a series number, no project, no creator,
    and no due_date."""
    task_id = str(uuid4())
    db_session.add(
        Task(
            id=task_id,
            tenant_key=tenant_key,
            product_id=product_id,
            title="INF-legacy operator-gated deploy validation",
            description="legacy-shaped row for TSK-9163 repro",
            status="pending",
            priority="high",
            series_number=6010,
            created_at=datetime(2026, 5, 29, 2, 16, 5, tzinfo=UTC),
        )
    )
    await db_session.commit()
    return task_id


async def _get_due_date(db_session, tenant_key: str, task_id: str):
    with tenant_session_context(db_session, tenant_key):
        result = await db_session.execute(
            select(Task.due_date).where(Task.id == task_id, Task.tenant_key == tenant_key)
        )
        return result.scalar_one()


async def test_update_task_due_date_string_on_legacy_shaped_row(db_session, two_tenant_service_setup):
    """The TSK-9163 repro: an ISO date STRING due_date on a legacy-shaped row
    must be written, not die in the generic internal-error envelope."""
    tenant_a = two_tenant_service_setup["tenant_a"]
    product_a = two_tenant_service_setup["product_a"]
    task_service = two_tenant_service_setup["task_service_a"]

    task_id = await _insert_legacy_shaped_task(db_session, tenant_a, product_a.id)

    result = await task_service.update_task_for_mcp(
        task_id=task_id,
        tenant_key=tenant_a,
        due_date="2026-07-15",
    )

    assert "due_date" in result["updated_fields"]
    stored = await _get_due_date(db_session, tenant_a, task_id)
    assert stored is not None
    assert (stored.year, stored.month, stored.day) == (2026, 7, 15)


async def test_update_task_due_date_string_on_fresh_row(db_session, two_tenant_service_setup):
    """Field-level pin: the same string due_date write succeeds on a fresh row
    created through the normal MCP create path."""
    tenant_a = two_tenant_service_setup["tenant_a"]
    db_manager = two_tenant_service_setup["db_manager"]
    task_service = two_tenant_service_setup["task_service_a"]

    # create_task_for_mcp resolves TSK lazily; ensure the reserved tag exists.
    taxonomy = TaxonomyService(db_manager=db_manager, session=db_session)
    await taxonomy.ensure_reserved_task_type(tenant_a)

    created = await task_service.create_task_for_mcp(
        title="fresh row due_date write",
        description="",
        tenant_key=tenant_a,
        db_manager=db_manager,
    )
    task_id = created["task_id"]

    result = await task_service.update_task_for_mcp(
        task_id=task_id,
        tenant_key=tenant_a,
        due_date="2026-07-15T09:00:00+00:00",
    )

    assert "due_date" in result["updated_fields"]
    stored = await _get_due_date(db_session, tenant_a, task_id)
    assert stored is not None
    assert (stored.year, stored.month, stored.day) == (2026, 7, 15)


async def test_update_task_due_date_garbage_string_is_agent_actionable(db_session, two_tenant_service_setup):
    """An unparseable due_date must raise ValidationError (agent-actionable),
    never the wrapped internal-error envelope."""
    tenant_a = two_tenant_service_setup["tenant_a"]
    product_a = two_tenant_service_setup["product_a"]
    task_service = two_tenant_service_setup["task_service_a"]

    task_id = await _insert_legacy_shaped_task(db_session, tenant_a, product_a.id)

    with pytest.raises(ValidationError):
        await task_service.update_task_for_mcp(
            task_id=task_id,
            tenant_key=tenant_a,
            due_date="not-a-date",
        )

    assert await _get_due_date(db_session, tenant_a, task_id) is None


async def test_update_task_due_date_datetime_object_still_works(db_session, two_tenant_service_setup):
    """Regression guard: a real datetime due_date (REST path parity) keeps
    working unchanged."""
    tenant_a = two_tenant_service_setup["tenant_a"]
    product_a = two_tenant_service_setup["product_a"]
    task_service = two_tenant_service_setup["task_service_a"]

    task_id = await _insert_legacy_shaped_task(db_session, tenant_a, product_a.id)

    result = await task_service.update_task_for_mcp(
        task_id=task_id,
        tenant_key=tenant_a,
        due_date=datetime(2026, 7, 20, 12, 0, tzinfo=UTC),
    )

    assert "due_date" in result["updated_fields"]
    stored = await _get_due_date(db_session, tenant_a, task_id)
    assert (stored.year, stored.month, stored.day) == (2026, 7, 20)
