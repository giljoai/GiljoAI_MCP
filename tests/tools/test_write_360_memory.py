# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""MCP-boundary regression tests for write_360_memory (IMP-5037 bug 2).

IMP-5037 bug 2: prior to the fix, ``_check_and_emit_tuning_staleness`` was
called with ``user_id=str(product.tenant_key)``, so the user lookup always
returned None and notification preferences silently fell back to defaults
(enabled=True, threshold=10). The staleness reminder then fired forever
because the no-drift submission path never stamped ``last_tuned_at_sequence``
(see bug 1, fixed in the prompt template at the same time).

These tests exercise the bug at the @mcp.tool wrapper boundary by calling
``write_360_memory`` end-to-end against the in-memory test DB. They assert
on the ``user_id`` argument that reaches
``ProductTuningService.check_tuning_staleness`` -- the layer where the bug
actually lived. A pre-fix run would see ``tenant_key`` here instead of a
real user UUID.
"""

from __future__ import annotations

import random
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from giljo_mcp.models import Project
from giljo_mcp.models.auth import User
from giljo_mcp.tools.write_memory_entry import write_360_memory


@pytest_asyncio.fixture
async def linked_project(db_session, test_tenant_key, test_product):
    """A project linked to test_product (write_360_memory requires product link)."""
    project = Project(
        id=str(uuid.uuid4()),
        name="IMP-5037 Boundary Test Project",
        description="Project for write_360_memory boundary tests",
        mission="Test mission",
        status="active",
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        series_number=random.randint(1, 9000),
    )
    db_session.add(project)
    await db_session.commit()
    return project


@pytest_asyncio.fixture
async def opt_in_user(db_session, test_tenant_key):
    """A user who has opted in to context-tuning reminders with threshold=3."""
    user = User(
        id=str(uuid.uuid4()),
        username=f"opt-in-{uuid.uuid4().hex[:8]}",
        email=f"opt-in-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="x",
        tenant_key=test_tenant_key,
        is_active=True,
        role="developer",
        notification_preferences={
            "context_tuning_reminder": True,
            "tuning_reminder_threshold": 3,
        },
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.mark.asyncio
async def test_write_360_memory_passes_real_user_id_to_staleness_check(
    db_session, test_tenant_key, test_product, linked_project, opt_in_user
):
    """IMP-5037 bug 2 regression: write_360_memory must call
    check_tuning_staleness with a real user UUID, NOT tenant_key.

    Before the fix, the caller passed ``user_id=str(product.tenant_key)``
    so the user lookup silently failed. This test asserts the actual
    user_id argument that reaches the service layer.
    """
    mock_db_manager = MagicMock()
    captured_user_ids: list[str] = []

    async def _spy_check(self, product_id, user_id):
        captured_user_ids.append(user_id)
        return {"is_stale": False, "projects_since_tune": 0, "threshold": 3, "enabled": True}

    with patch(
        "giljo_mcp.services.product_tuning_service.ProductTuningService.check_tuning_staleness",
        new=_spy_check,
    ):
        await write_360_memory(
            project_id=str(linked_project.id),
            tenant_key=test_tenant_key,
            summary="Closeout passing explicit user_id",
            key_outcomes=["Outcome A"],
            decisions_made=["Decision A"],
            entry_type="session_handover",
            db_manager=mock_db_manager,
            session=db_session,
            user_id=str(opt_in_user.id),
        )

    assert captured_user_ids == [str(opt_in_user.id)], (
        f"Expected check_tuning_staleness to receive the explicit user_id "
        f"{opt_in_user.id!r}, but got {captured_user_ids!r}. With the pre-fix code "
        f"this list would contain the tenant_key {test_tenant_key!r}."
    )


@pytest.mark.asyncio
async def test_write_360_memory_resolves_tenant_user_when_user_id_omitted(
    db_session, test_tenant_key, test_product, linked_project, opt_in_user
):
    """When the caller omits user_id, the helper must resolve the primary
    active user for the tenant via _resolve_tenant_user_id -- NOT pass
    tenant_key in. This is the CE-solo fallback path.
    """
    mock_db_manager = MagicMock()
    # Wire mock_db_manager.get_session_async to yield db_session so the
    # resolver query runs against the test DB.
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _yield_db_session():
        yield db_session

    mock_db_manager.get_session_async = MagicMock(side_effect=_yield_db_session)

    captured_user_ids: list[str] = []

    async def _spy_check(self, product_id, user_id):
        captured_user_ids.append(user_id)
        return {"is_stale": False, "projects_since_tune": 0, "threshold": 3, "enabled": True}

    with patch(
        "giljo_mcp.services.product_tuning_service.ProductTuningService.check_tuning_staleness",
        new=_spy_check,
    ):
        await write_360_memory(
            project_id=str(linked_project.id),
            tenant_key=test_tenant_key,
            summary="Closeout with user_id resolved from tenant",
            key_outcomes=["Outcome A"],
            decisions_made=["Decision A"],
            entry_type="session_handover",
            db_manager=mock_db_manager,
            session=db_session,
            # user_id omitted on purpose
        )

    assert captured_user_ids == [str(opt_in_user.id)], (
        f"Expected the tenant-resolver fallback to pass the active user {opt_in_user.id!r}, got {captured_user_ids!r}."
    )


@pytest.mark.asyncio
async def test_write_360_memory_emits_notification_when_threshold_exceeded(
    db_session, test_tenant_key, test_product, linked_project, opt_in_user
):
    """Counter-test: when the staleness service reports is_stale=True,
    write_360_memory MUST emit a notification:new event with type=context_tuning.
    Proves the emit path is wired and not bypassed.
    """
    mock_db_manager = MagicMock()
    captured_events: list[dict] = []

    async def _stale_check(self, product_id, user_id):
        return {"is_stale": True, "projects_since_tune": 5, "threshold": 3, "enabled": True}

    async def _capture_emit(*, event_type, tenant_key, product_id, data):
        captured_events.append(
            {"event_type": event_type, "tenant_key": tenant_key, "product_id": product_id, "data": data}
        )

    with (
        patch(
            "giljo_mcp.services.product_tuning_service.ProductTuningService.check_tuning_staleness",
            new=_stale_check,
        ),
        patch("giljo_mcp.tools.write_memory_entry.emit_websocket_event", new=AsyncMock(side_effect=_capture_emit)),
    ):
        await write_360_memory(
            project_id=str(linked_project.id),
            tenant_key=test_tenant_key,
            summary="Closeout that should emit tuning reminder",
            key_outcomes=["Outcome A"],
            decisions_made=["Decision A"],
            entry_type="session_handover",
            db_manager=mock_db_manager,
            session=db_session,
            user_id=str(opt_in_user.id),
        )

    tuning_events = [
        e
        for e in captured_events
        if e["event_type"] == "notification:new" and e["data"].get("type") == "context_tuning"
    ]
    assert len(tuning_events) == 1, (
        f"Expected exactly one context_tuning notification when is_stale=True, got: {tuning_events}"
    )
    assert tuning_events[0]["tenant_key"] == test_tenant_key
    assert tuning_events[0]["data"]["metadata"]["product_id"] == str(test_product.id)
