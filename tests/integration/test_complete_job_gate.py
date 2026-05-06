# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available, single-user use only.

"""Transport-layer regression tests for the BE-5059 Phase B close gates.

CLAUDE.md mandates a regression test at the failing layer for every bug-fix /
primitive project. The Phase B gates live inside the FastMCP ``@mcp.tool``
wrappers' downstream services -- this file exercises them through the MCP
transport (``create_connected_server_and_client_session``) so the wrapper +
``_call_tool`` dispatch + service-layer gate logic are all covered, not just
the service in isolation.

Two gates under test:

1. ``complete_job`` MUST refuse when the active execution is ``awaiting_user``
   and surface the pending ``approval_id`` in the error context.
2. ``close_project_and_update_memory`` (force=False) MUST refuse when ANY
   team member is ``awaiting_user`` and surface a per-agent ``approval_id`` in
   the blockers list with ``issue_type="awaiting_user_approval"``.

Pattern reference: ``tests/integration/test_request_approval_mcp_transport.py``
(Phase A) and ``tests/integration/test_task_tools_mcp_transport.py`` (BE-5057).
Same in-memory transport, same ``_resolve_tenant`` monkeypatch, same shared-
session service rebinding so writes happen inside the rolled-back test
transaction.
"""

from __future__ import annotations

import json
import random
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from mcp.shared.memory import create_connected_server_and_client_session

from giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from giljo_mcp.models.organizations import Organization
from giljo_mcp.models.products import Product
from giljo_mcp.models.projects import Project
from giljo_mcp.tenant import TenantManager


pytestmark = pytest.mark.asyncio


def _payload(call_tool_result) -> dict:
    if getattr(call_tool_result, "structuredContent", None):
        return call_tool_result.structuredContent
    first_block = call_tool_result.content[0]
    text = getattr(first_block, "text", None)
    if text is None:
        raise AssertionError(f"unexpected content block: {first_block!r}")
    return json.loads(text)


def _error_text(call_tool_result) -> str:
    parts = []
    for block in call_tool_result.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts)


async def _seed_full_context(db_session, tenant_key: str) -> dict:
    suffix = uuid4().hex[:8]
    org = Organization(
        name=f"Org {suffix}",
        slug=f"org-{suffix}",
        tenant_key=tenant_key,
        is_active=True,
    )
    db_session.add(org)
    await db_session.flush()

    product = Product(
        id=str(uuid4()),
        name=f"Product {suffix}",
        description="gate transport-layer tests",
        tenant_key=tenant_key,
        is_active=True,
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
        series_number=random.randint(1, 999_999_999),
    )
    db_session.add(project)
    await db_session.flush()

    job = AgentJob(
        job_id=str(uuid4()),
        tenant_key=tenant_key,
        project_id=project.id,
        job_type="implementer",
        mission="x",
        status="active",
        created_at=datetime.now(UTC),
    )
    db_session.add(job)
    await db_session.flush()

    execution = AgentExecution(
        id=str(uuid4()),
        agent_id=str(uuid4()),
        job_id=job.job_id,
        tenant_key=tenant_key,
        agent_display_name="implementer",
        status="working",
        started_at=datetime.now(UTC),
    )
    db_session.add(execution)
    await db_session.commit()
    return {"org": org, "product": product, "project": project, "job": job, "execution": execution}


@pytest_asyncio.fixture
async def gate_mcp_client(db_manager, db_session, monkeypatch):
    """Wire ToolAccessor's user_approval AND job_completion services to db_session.

    Same pattern as ``approval_mcp_client`` in
    ``tests/integration/test_request_approval_mcp_transport.py`` -- replace the
    accessor's services with shared-session instances so writes land inside the
    rolled-back test transaction. JobCompletionService also accepts a
    test_session, so the complete_job gate sees the same seed rows.
    """
    from api import app_state
    from api.endpoints import mcp_sdk_server
    from giljo_mcp.services.job_completion_service import JobCompletionService
    from giljo_mcp.services.user_approval_service import UserApprovalService
    from giljo_mcp.tools.tool_accessor import ToolAccessor

    state = app_state.state
    prior_tool_accessor = state.tool_accessor
    prior_tenant_manager = state.tenant_manager
    prior_db_manager = state.db_manager

    if state.tenant_manager is None:
        state.tenant_manager = TenantManager()
    state.db_manager = db_manager

    tenant_key = TenantManager.generate_tenant_key()

    accessor = ToolAccessor(db_manager=db_manager, tenant_manager=state.tenant_manager)
    accessor._user_approval_service = UserApprovalService(
        db_manager=db_manager,
        tenant_manager=state.tenant_manager,
        test_session=db_session,
    )
    accessor._job_completion_service = JobCompletionService(
        db_manager=db_manager,
        tenant_manager=state.tenant_manager,
        test_session=db_session,
    )

    # close_project_and_update_memory tool opens a new session via db_manager,
    # which won't see the test-transaction seed rows. Override the accessor's
    # method to forward the rolled-back db_session into the tool function.
    from giljo_mcp.tools.project_closeout import (
        close_project_and_update_memory as _close_tool,
    )

    async def _close_with_test_session(*, project_id, summary, key_outcomes, decisions_made, tenant_key, **kwargs):
        return await _close_tool(
            project_id=project_id,
            summary=summary,
            key_outcomes=key_outcomes,
            decisions_made=decisions_made,
            tenant_key=tenant_key,
            db_manager=db_manager,
            session=db_session,
            **kwargs,
        )

    accessor.close_project_and_update_memory = _close_with_test_session

    state.tool_accessor = accessor

    monkeypatch.setattr(mcp_sdk_server, "_resolve_tenant", lambda ctx: tenant_key)
    monkeypatch.setattr(mcp_sdk_server, "_resolve_user_id", lambda ctx: None)

    def _new_client():
        return create_connected_server_and_client_session(mcp_sdk_server.mcp)

    try:
        yield _new_client, tenant_key
    finally:
        state.tool_accessor = prior_tool_accessor
        state.tenant_manager = prior_tenant_manager
        state.db_manager = prior_db_manager


async def _request_approval_via_transport(new_client, seed):
    """Drive request_approval through the MCP wrapper to flip status atomically."""
    async with new_client() as session:
        result = await session.call_tool(
            "request_approval",
            {
                "job_id": seed["job"].job_id,
                "project_id": seed["project"].id,
                "reason": "Closeout: awaiting user review",
                "options": [
                    {"id": "approve", "label": "Approve and close"},
                    {"id": "rework", "label": "Send back for rework"},
                ],
                "context": {"deferred_findings": ["finding-1"]},
            },
        )
    assert result.isError is False, _error_text(result)
    return _payload(result)["approval_id"]


# ---------------------------------------------------------------------------
# complete_job gate
# ---------------------------------------------------------------------------


async def test_complete_job_blocked_when_agent_is_awaiting_user(gate_mcp_client, db_session):
    """complete_job through the MCP transport must refuse on awaiting_user.

    The error must surface ``approval_id`` in its context so callers can route
    directly to the decide endpoint. Service-layer-only coverage would miss the
    @mcp.tool wrapper's exception serialization shape, which is the actual
    surface the orchestrator sees.
    """
    new_client, tenant_key = gate_mcp_client
    seed = await _seed_full_context(db_session, tenant_key)

    approval_id = await _request_approval_via_transport(new_client, seed)
    assert approval_id

    async with new_client() as session:
        result = await session.call_tool(
            "complete_job",
            {
                "job_id": seed["job"].job_id,
                "result": {"summary": "premature complete attempt"},
            },
        )

    assert result.isError is True, "GATE LEAK: complete_job returned success while agent was awaiting_user"
    err = _error_text(result)
    assert "awaiting" in err.lower() or "AWAITING_USER_APPROVAL" in err or approval_id in err, (
        f"expected awaiting_user gate error, got: {err!r}"
    )


# ---------------------------------------------------------------------------
# close_project_and_update_memory gate
# ---------------------------------------------------------------------------


async def test_close_project_blocked_when_any_team_member_awaiting_user(gate_mcp_client, db_session):
    """close_project (force=False) must refuse when any agent is awaiting_user.

    Asserts:
    1. The transport result is an error.
    2. The blocker carries ``issue_type="awaiting_user_approval"`` and the
       resolved ``approval_id`` (so the UI can deep-link to the decide route).
    """
    new_client, tenant_key = gate_mcp_client
    seed = await _seed_full_context(db_session, tenant_key)

    approval_id = await _request_approval_via_transport(new_client, seed)
    assert approval_id

    async with new_client() as session:
        result = await session.call_tool(
            "close_project_and_update_memory",
            {
                "project_id": seed["project"].id,
                "summary": "premature close attempt",
                "key_outcomes": ["x"],
                "decisions_made": ["x"],
                "tags": ["chore", "backend"],
            },
        )

    assert result.isError is True, (
        "GATE LEAK: close_project_and_update_memory returned success with awaiting_user agent"
    )
    err = _error_text(result)
    assert "awaiting" in err.lower() or "approval" in err.lower() or "CLOSEOUT_BLOCKED" in err or approval_id in err, (
        f"expected awaiting_user closeout blocker, got: {err!r}"
    )
