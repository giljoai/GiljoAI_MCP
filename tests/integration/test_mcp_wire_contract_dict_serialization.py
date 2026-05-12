# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Transport-layer regression: MCP wire-contract Pydantic-to-dict normalisation.

Every ``@mcp.tool`` wrapper in ``api/endpoints/mcp_sdk_server.py`` is annotated
``-> dict[str, Any]``. The underlying service layer, however, returns typed
Pydantic response models (``MissionResponse``, ``ProgressResult``,
``SpawnResult``, ``SendMessageResult``, etc.). Without normalisation at the
boundary, FastMCP validates the return against the annotation and rejects the
Pydantic instance with::

    1 validation error for DictModel
    Input should be a valid dictionary [type=dict_type, input_value=...]

The catastrophic property of this bug is that the server-side write has
already landed by the time the validator runs — so the orchestrator sees a
hard error client-side while every state transition has actually been
persisted. Discovered in production while spawning agents on dogfood; staged
agents transitioned waiting→working, progress reports persisted, but every
client surface showed DictModel errors.

Failing-layer discipline (CLAUDE.md): service-layer tests pass because
``MissionService.get_agent_mission`` correctly returns a ``MissionResponse``.
The bug is in the ``_call_tool`` dispatcher that surfaces that model to
FastMCP. The fix and its regression coverage must live at that boundary.
"""

from __future__ import annotations

import json

import pytest
import pytest_asyncio
from mcp.shared.memory import create_connected_server_and_client_session
from pydantic import BaseModel

from giljo_mcp.tenant import TenantManager


pytestmark = pytest.mark.asyncio


def _payload(call_tool_result) -> dict:
    """Decode a CallToolResult into a dict."""
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


class _FakeMissionResponse(BaseModel):
    """Stand-in for any Pydantic response model the service layer returns.

    Mirrors the shape of ``MissionResponse`` closely enough that the wire-
    serialised payload is recognisable, without coupling the test to the
    real model's field set (which evolves independently of this contract).
    """

    job_id: str
    status: str = "working"
    mission: str | None = None
    full_protocol: str | None = None


@pytest_asyncio.fixture
async def wire_contract_client(monkeypatch):
    """In-memory FastMCP client with a stub ToolAccessor returning a Pydantic model.

    The test does not need a real DB — it asserts the boundary, not the
    service. We swap ``ToolAccessor.get_agent_mission`` for an async stub
    returning a Pydantic instance, monkeypatch ``_resolve_tenant`` so no auth
    middleware is required, and neutralise the post-call heartbeat /
    silent-clear paths (which would otherwise reach for a live db_manager).
    """
    from api import app_state
    from api.endpoints import mcp_sdk_server

    state = app_state.state
    prior_tool_accessor = state.tool_accessor
    prior_tenant_manager = state.tenant_manager

    if state.tenant_manager is None:
        state.tenant_manager = TenantManager()

    class _StubAccessor:
        async def get_agent_mission(self, job_id: str, tenant_key: str):
            return _FakeMissionResponse(
                job_id=job_id,
                status="working",
                mission="stub mission body",
                full_protocol="stub protocol body",
            )

    state.tool_accessor = _StubAccessor()

    tenant_key = TenantManager.generate_tenant_key()
    monkeypatch.setattr(mcp_sdk_server, "_resolve_tenant", lambda ctx: tenant_key)
    monkeypatch.setattr(mcp_sdk_server, "_resolve_user_id", lambda ctx: None)

    # Neutralise post-call side effects that would otherwise need a live
    # db_manager. The wire-contract assertion is orthogonal to these.
    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr("giljo_mcp.services.silence_detector.auto_clear_silent", _noop)
    monkeypatch.setattr("giljo_mcp.services.heartbeat.touch_heartbeat", _noop)

    def _new_client():
        return create_connected_server_and_client_session(mcp_sdk_server.mcp)

    try:
        yield _new_client, tenant_key
    finally:
        state.tool_accessor = prior_tool_accessor
        state.tenant_manager = prior_tenant_manager


async def test_pydantic_response_is_serialised_to_dict_at_mcp_boundary(wire_contract_client):
    """A Pydantic BaseModel returned by the service must reach the client as a dict.

    This is the regression for the DictModel wire-contract bug. Before the
    fix, FastMCP raised a validation error against the ``-> dict[str, Any]``
    annotation on ``get_agent_mission`` because ``_call_tool`` returned the
    raw Pydantic instance. After the fix, ``_call_tool`` calls
    ``model_dump(mode="json")`` on any ``BaseModel`` result so the wire
    payload is a plain dict — exactly what the annotation promises.
    """
    new_client, _tenant_key = wire_contract_client

    async with new_client() as session:
        result = await session.call_tool(
            "get_agent_mission",
            {"job_id": "11111111-1111-1111-1111-111111111111"},
        )

    assert result.isError is False, _error_text(result)

    payload = _payload(result)
    assert isinstance(payload, dict), f"expected dict, got {type(payload).__name__}: {payload!r}"
    assert payload["job_id"] == "11111111-1111-1111-1111-111111111111"
    assert payload["status"] == "working"
    assert payload["mission"] == "stub mission body"
    assert payload["full_protocol"] == "stub protocol body"


async def test_call_tool_helper_normalises_basemodel_to_dict():
    """Unit-level guard on the dispatcher itself.

    Even if FastMCP's validation behaviour ever changes, ``_call_tool``
    should still hand callers a dict so downstream consumers (logs, audit
    sinks, scoped-tool wrappers) do not have to discriminate on response
    type. This test bypasses the FastMCP transport and calls ``_call_tool``
    directly with a stub accessor.
    """
    from unittest.mock import MagicMock

    from api import app_state
    from api.endpoints import mcp_sdk_server

    state = app_state.state
    prior_tool_accessor = state.tool_accessor
    prior_tenant_manager = state.tenant_manager

    if state.tenant_manager is None:
        state.tenant_manager = TenantManager()

    class _StubAccessor:
        async def get_agent_mission(self, job_id: str, tenant_key: str):
            return _FakeMissionResponse(job_id=job_id, mission="x")

    state.tool_accessor = _StubAccessor()

    # Build a Context whose request scope state carries a tenant_key.
    tenant_key = TenantManager.generate_tenant_key()
    ctx = MagicMock()
    ctx.request_context.request.scope = {"state": {"tenant_key": tenant_key}}

    try:
        result = await mcp_sdk_server._call_tool(
            ctx,
            "get_agent_mission",
            {"job_id": "job-1"},
        )
    finally:
        state.tool_accessor = prior_tool_accessor
        state.tenant_manager = prior_tenant_manager

    assert isinstance(result, dict), f"_call_tool must return dict, got {type(result).__name__}"
    assert result == {
        "job_id": "job-1",
        "status": "working",
        "mission": "x",
        "full_protocol": None,
    }
