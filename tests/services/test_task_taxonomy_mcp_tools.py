# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition - source-available, single-user use only.

"""Tenant-isolation + happy-path tests for the Phase B/C/D MCP task tools.

Covers:
- ``TaskService.create_task_for_mcp`` (Phase B): task_type validation against
  TaxonomyService; rejection payload includes valid_types.
- ``TaskService.update_task_for_mcp`` (Phase C): status transitions, enum
  validation, task_type rebind, tenant scoping, TaskService-routed write.
- ``TaskService.complete_task_for_mcp`` (Phase C): sets status=completed
  and completed_at; tenant scoping.
- ``TaskService.list_tasks_for_mcp`` (Phase D): summary/full mode shapes,
  filters, tenant scoping.

Real DB; no mocks. Uses the two_tenant_service_setup fixture from
tests/services/conftest.py.
"""

from __future__ import annotations

import pytest

from giljo_mcp.exceptions import ValidationError
from giljo_mcp.services.taxonomy_service import TaxonomyService


pytestmark = pytest.mark.asyncio


async def _seed_taxonomy_for(db_session, tenant_key: str, db_manager) -> None:
    """Seed BE/FE/INF rows for a tenant using TaxonomyService (test-scoped session).

    Idempotent: skips abbreviations that already exist. Commits via the test's
    db_session so rows are visible to the new sessions that
    ``create_task_for_mcp`` opens via ``db_manager.get_session_async()``.
    """
    service = TaxonomyService(db_manager=db_manager, session=db_session)
    existing = {row.abbreviation for row in await service.list_types(tenant_key)}
    for i, (abbr, label) in enumerate([("BE", "Backend"), ("FE", "Frontend"), ("INF", "Infrastructure")]):
        if abbr in existing:
            continue
        await service.create_type(
            tenant_key=tenant_key,
            abbreviation=abbr,
            label=label,
            sort_order=i,
        )
    await db_session.commit()


# ---------------------------------------------------------------------------
# Phase B: create_task_for_mcp + task_type validation
# ---------------------------------------------------------------------------


async def test_create_task_for_mcp_resolves_known_task_type(db_session, two_tenant_service_setup):
    tenant_a = two_tenant_service_setup["tenant_a"]
    db_manager = two_tenant_service_setup["db_manager"]
    task_service_a = two_tenant_service_setup["task_service_a"]

    await _seed_taxonomy_for(db_session, tenant_a, db_manager)

    response = await task_service_a.create_task_for_mcp(
        title="Investigate flaky test",
        description="Repro and fix the websocket flake",
        priority="high",
        task_type="BE",
        tenant_key=tenant_a,
        db_manager=db_manager,
    )

    assert response["success"] is True
    assert response["task_id"]
    assert response["task_type"] == "BE"
    assert "valid_types" not in response


async def test_create_task_for_mcp_rejects_unknown_task_type_with_valid_types(db_session, two_tenant_service_setup):
    tenant_a = two_tenant_service_setup["tenant_a"]
    db_manager = two_tenant_service_setup["db_manager"]
    task_service_a = two_tenant_service_setup["task_service_a"]

    await _seed_taxonomy_for(db_session, tenant_a, db_manager)

    with pytest.raises(ValidationError) as excinfo:
        await task_service_a.create_task_for_mcp(
            title="will fail",
            description="will fail",
            task_type="MADEUP",
            tenant_key=tenant_a,
            db_manager=db_manager,
        )

    err = excinfo.value
    valid_types = err.context.get("valid_types") or []
    abbrs = {t["abbreviation"] for t in valid_types}
    assert {"BE", "FE", "INF"}.issubset(abbrs)


async def test_create_task_for_mcp_omitted_task_type_returns_valid_types_hint(db_session, two_tenant_service_setup):
    tenant_a = two_tenant_service_setup["tenant_a"]
    db_manager = two_tenant_service_setup["db_manager"]
    task_service_a = two_tenant_service_setup["task_service_a"]

    await _seed_taxonomy_for(db_session, tenant_a, db_manager)

    response = await task_service_a.create_task_for_mcp(
        title="No type provided",
        description="UI hint flow",
        tenant_key=tenant_a,
        db_manager=db_manager,
    )

    assert response["success"] is True
    abbrs = {t["abbreviation"] for t in response.get("valid_types", [])}
    assert {"BE", "FE", "INF"}.issubset(abbrs)


async def test_create_task_does_not_leak_other_tenants_taxonomy(db_session, two_tenant_service_setup):
    tenant_a = two_tenant_service_setup["tenant_a"]
    tenant_b = two_tenant_service_setup["tenant_b"]
    db_manager = two_tenant_service_setup["db_manager"]
    task_service_a = two_tenant_service_setup["task_service_a"]

    # Only seed tenant B's taxonomy.
    await _seed_taxonomy_for(db_session, tenant_b, db_manager)

    # Tenant A trying to use BE (which only exists in tenant B's table) must fail.
    with pytest.raises(ValidationError):
        await task_service_a.create_task_for_mcp(
            title="cross-tenant taxonomy",
            description="should not resolve",
            task_type="BE",
            tenant_key=tenant_a,
            db_manager=db_manager,
        )


# ---------------------------------------------------------------------------
# Phase C: update_task_for_mcp (status transitions) + complete_task_for_mcp
# ---------------------------------------------------------------------------


async def _create_seed_task(db_session, two_tenant_service_setup) -> str:
    tenant_a = two_tenant_service_setup["tenant_a"]
    db_manager = two_tenant_service_setup["db_manager"]
    task_service_a = two_tenant_service_setup["task_service_a"]
    await _seed_taxonomy_for(db_session, tenant_a, db_manager)

    response = await task_service_a.create_task_for_mcp(
        title="seed task",
        description="for status updates",
        task_type="BE",
        tenant_key=tenant_a,
        db_manager=db_manager,
    )
    return response["task_id"]


async def test_update_task_status_field_transitions_to_in_progress(db_session, two_tenant_service_setup):
    """Status flows through update_task (no dedicated update_task_status tool)."""
    task_id = await _create_seed_task(db_session, two_tenant_service_setup)
    tenant_a = two_tenant_service_setup["tenant_a"]
    task_service_a = two_tenant_service_setup["task_service_a"]

    response = await task_service_a.update_task_for_mcp(
        task_id=task_id,
        status="in_progress",
        tenant_key=tenant_a,
    )

    assert response["task_id"] == task_id
    assert "status" in response["updated_fields"]


async def test_update_task_blocks_cross_tenant_task(db_session, two_tenant_service_setup):
    """Tenant A may not update a Tenant B task — 404, not 200."""
    from giljo_mcp.exceptions import ResourceNotFoundError
    from giljo_mcp.services.task_service import TaskService
    from giljo_mcp.tenant import TenantManager

    tenant_a = two_tenant_service_setup["tenant_a"]
    tenant_b = two_tenant_service_setup["tenant_b"]
    db_manager = two_tenant_service_setup["db_manager"]
    await _seed_taxonomy_for(db_session, tenant_b, db_manager)

    task_service_b = TaskService(
        db_manager=db_manager,
        tenant_manager=TenantManager(),
        session=db_session,
    )
    response = await task_service_b.create_task_for_mcp(
        title="tenant b task",
        description="x",
        task_type="BE",
        tenant_key=tenant_b,
        db_manager=db_manager,
    )
    b_task_id = response["task_id"]

    task_service_a = two_tenant_service_setup["task_service_a"]
    with pytest.raises(ResourceNotFoundError):
        await task_service_a.update_task_for_mcp(
            task_id=b_task_id,
            status="in_progress",
            tenant_key=tenant_a,
        )


async def test_complete_task_sets_completed_status_and_timestamp(db_session, two_tenant_service_setup):
    task_id = await _create_seed_task(db_session, two_tenant_service_setup)
    tenant_a = two_tenant_service_setup["tenant_a"]
    task_service_a = two_tenant_service_setup["task_service_a"]

    response = await task_service_a.complete_task_for_mcp(
        task_id=task_id,
        tenant_key=tenant_a,
        completion_notes="all green",
    )

    assert response["task_id"] == task_id
    assert response["status"] == "completed"
    assert response["completed_at"]


# ---------------------------------------------------------------------------
# Phase C addition: update_task_for_mcp (full-field update + task_type rebind)
# ---------------------------------------------------------------------------


async def test_update_task_changes_title_and_priority(db_session, two_tenant_service_setup):
    task_id = await _create_seed_task(db_session, two_tenant_service_setup)
    tenant_a = two_tenant_service_setup["tenant_a"]
    task_service_a = two_tenant_service_setup["task_service_a"]

    response = await task_service_a.update_task_for_mcp(
        task_id=task_id,
        tenant_key=tenant_a,
        title="Renamed",
        priority="critical",
    )

    assert response["task_id"] == task_id
    assert "title" in response["updated_fields"]
    assert "priority" in response["updated_fields"]


async def test_update_task_rebinds_task_type_via_taxonomy(db_session, two_tenant_service_setup):
    """Pass a different abbreviation; service resolves it to a new task_type_id."""
    task_id = await _create_seed_task(db_session, two_tenant_service_setup)
    tenant_a = two_tenant_service_setup["tenant_a"]
    task_service_a = two_tenant_service_setup["task_service_a"]

    response = await task_service_a.update_task_for_mcp(
        task_id=task_id,
        tenant_key=tenant_a,
        task_type="FE",
    )

    assert "task_type_id" in response["updated_fields"]


async def test_update_task_rejects_unknown_task_type(db_session, two_tenant_service_setup):
    task_id = await _create_seed_task(db_session, two_tenant_service_setup)
    tenant_a = two_tenant_service_setup["tenant_a"]
    task_service_a = two_tenant_service_setup["task_service_a"]

    with pytest.raises(ValidationError):
        await task_service_a.update_task_for_mcp(
            task_id=task_id,
            tenant_key=tenant_a,
            task_type="BOGUS",
        )


async def test_update_task_rejects_invalid_status(db_session, two_tenant_service_setup):
    task_id = await _create_seed_task(db_session, two_tenant_service_setup)
    tenant_a = two_tenant_service_setup["tenant_a"]
    task_service_a = two_tenant_service_setup["task_service_a"]

    with pytest.raises(ValidationError):
        await task_service_a.update_task_for_mcp(
            task_id=task_id,
            tenant_key=tenant_a,
            status="bogus",
        )


async def test_update_task_no_fields_returns_noop(db_session, two_tenant_service_setup):
    task_id = await _create_seed_task(db_session, two_tenant_service_setup)
    tenant_a = two_tenant_service_setup["tenant_a"]
    task_service_a = two_tenant_service_setup["task_service_a"]

    response = await task_service_a.update_task_for_mcp(
        task_id=task_id,
        tenant_key=tenant_a,
    )

    assert response["updated_fields"] == []


# ---------------------------------------------------------------------------
# Phase D: list_tasks_for_mcp
# ---------------------------------------------------------------------------


async def test_list_tasks_summary_mode_returns_compact_rows(db_session, two_tenant_service_setup):
    """Summary mode: id, title, status, priority, type, due_date, created_at only."""
    await _create_seed_task(db_session, two_tenant_service_setup)
    tenant_a = two_tenant_service_setup["tenant_a"]
    task_service_a = two_tenant_service_setup["task_service_a"]

    response = await task_service_a.list_tasks_for_mcp(
        tenant_key=tenant_a,
        mode="summary",
    )

    assert "tasks" in response
    assert len(response["tasks"]) >= 1
    row = response["tasks"][0]
    expected_keys = {"task_id", "title", "status", "priority", "task_type", "due_date", "created_at"}
    assert expected_keys.issuperset(set(row.keys()) - {"id"})


async def test_list_tasks_filters_by_status(db_session, two_tenant_service_setup):
    pending_id = await _create_seed_task(db_session, two_tenant_service_setup)
    tenant_a = two_tenant_service_setup["tenant_a"]
    task_service_a = two_tenant_service_setup["task_service_a"]

    # Move one task to in_progress, leave the other pending.
    second_id = await _create_seed_task(db_session, two_tenant_service_setup)
    await task_service_a.update_task_for_mcp(
        task_id=second_id,
        status="in_progress",
        tenant_key=tenant_a,
    )

    response = await task_service_a.list_tasks_for_mcp(
        tenant_key=tenant_a,
        mode="summary",
        status="pending",
    )

    ids = {t["task_id"] for t in response["tasks"]}
    assert pending_id in ids
    assert second_id not in ids


async def test_list_tasks_filters_by_task_type(db_session, two_tenant_service_setup):
    """Filtering by task_type abbreviation should narrow results."""
    tenant_a = two_tenant_service_setup["tenant_a"]
    db_manager = two_tenant_service_setup["db_manager"]
    task_service_a = two_tenant_service_setup["task_service_a"]
    await _seed_taxonomy_for(db_session, tenant_a, db_manager)

    be = await task_service_a.create_task_for_mcp(
        title="BE work",
        description="",
        task_type="BE",
        tenant_key=tenant_a,
        db_manager=db_manager,
    )
    fe = await task_service_a.create_task_for_mcp(
        title="FE work",
        description="",
        task_type="FE",
        tenant_key=tenant_a,
        db_manager=db_manager,
    )

    response = await task_service_a.list_tasks_for_mcp(
        tenant_key=tenant_a,
        mode="summary",
        task_type="BE",
    )
    ids = {t["task_id"] for t in response["tasks"]}
    assert be["task_id"] in ids
    assert fe["task_id"] not in ids


async def test_list_tasks_is_tenant_scoped(db_session, two_tenant_service_setup):
    """A tenant_a request must not see tenant_b tasks."""
    from giljo_mcp.services.task_service import TaskService
    from giljo_mcp.tenant import TenantManager

    tenant_a = two_tenant_service_setup["tenant_a"]
    tenant_b = two_tenant_service_setup["tenant_b"]
    db_manager = two_tenant_service_setup["db_manager"]
    await _seed_taxonomy_for(db_session, tenant_b, db_manager)

    # Tenant B task
    task_service_b = TaskService(
        db_manager=db_manager,
        tenant_manager=TenantManager(),
        session=db_session,
    )
    b = await task_service_b.create_task_for_mcp(
        title="tenant_b task",
        description="x",
        task_type="BE",
        tenant_key=tenant_b,
        db_manager=db_manager,
    )

    # Tenant A task
    a_task_id = await _create_seed_task(db_session, two_tenant_service_setup)

    task_service_a = two_tenant_service_setup["task_service_a"]
    response = await task_service_a.list_tasks_for_mcp(
        tenant_key=tenant_a,
        mode="summary",
    )
    ids = {t["task_id"] for t in response["tasks"]}
    assert a_task_id in ids
    assert b["task_id"] not in ids
