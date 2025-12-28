"""
Handover 0379d: Backend Event Contract + Broadcast Unification

These tests enforce the backend WebSocket event contract:
- Canonical envelope: {type, timestamp, schema_version, data}
- Tenant-scoped events always include tenant_key in payload data
- Legacy event aliasing can be enabled during migration
- Message events include explicit job identifiers (from_job_id / to_job_ids)
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.asyncio


async def _connected_ws_manager(*, tenant_key: str):
    from api.websocket import WebSocketManager

    ws_manager = WebSocketManager()
    # Use a simple object so it does not look like a ConnectionInfo wrapper
    # (broadcast_to_tenant supports both raw websockets and connection wrappers).
    mock_ws = SimpleNamespace(send_json=AsyncMock())
    client_id = "client-1"
    ws_manager.active_connections[client_id] = mock_ws
    ws_manager.auth_contexts[client_id] = {"tenant_key": tenant_key}
    return ws_manager, mock_ws


class TestEventEnvelopeAndTenantKey:
    async def test_broadcast_to_tenant_injects_tenant_key_into_data(self):
        """
        Tenant-scoped events must always include tenant_key so the frontend router can fail-closed.
        """
        tenant_key = "tenant-A"
        ws_manager, mock_ws = await _connected_ws_manager(tenant_key=tenant_key)

        await ws_manager.broadcast_to_tenant(
            tenant_key=tenant_key,
            event_type="project:mission_updated",
            data={"project_id": str(uuid.uuid4()), "mission": "hello"},
        )

        sent = mock_ws.send_json.call_args[0][0]
        assert sent["type"] == "project:mission_updated"
        assert sent["schema_version"] == "1.0"
        assert "timestamp" in sent
        assert sent["data"]["tenant_key"] == tenant_key


class TestMessageEventJobIdentifiers:
    async def test_message_sent_includes_schema_version_and_job_ids(self):
        from api.websocket import WebSocketManager

        tenant_key = "tenant-123"
        ws_manager = WebSocketManager()
        mock_ws = SimpleNamespace(send_json=AsyncMock())
        ws_manager.active_connections["client-1"] = mock_ws
        ws_manager.auth_contexts["client-1"] = {"tenant_key": tenant_key}

        message_id = str(uuid.uuid4())
        from_job_id = str(uuid.uuid4())
        to_job_ids = [str(uuid.uuid4())]

        await ws_manager.broadcast_message_sent(
            message_id=message_id,
            job_id=from_job_id,
            project_id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            from_agent="orchestrator",
            to_agent="implementer",
            to_job_ids=to_job_ids,
            message_type="direct",
            content_preview="hello",
            priority=1,
        )

        sent = mock_ws.send_json.call_args[0][0]
        assert sent["type"] == "message:sent"
        assert sent["schema_version"] == "1.0"
        assert sent["data"]["tenant_key"] == tenant_key
        assert sent["data"]["from_job_id"] == from_job_id
        assert sent["data"]["to_job_ids"] == to_job_ids

    async def test_message_received_includes_schema_version_and_job_ids(self):
        from api.websocket import WebSocketManager

        tenant_key = "tenant-123"
        ws_manager = WebSocketManager()
        mock_ws = SimpleNamespace(send_json=AsyncMock())
        ws_manager.active_connections["client-1"] = mock_ws
        ws_manager.auth_contexts["client-1"] = {"tenant_key": tenant_key}

        message_id = str(uuid.uuid4())
        from_job_id = str(uuid.uuid4())
        to_job_ids = [str(uuid.uuid4()), str(uuid.uuid4())]

        await ws_manager.broadcast_message_received(
            message_id=message_id,
            job_id=from_job_id,
            project_id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            from_agent="orchestrator",
            to_agent_ids=to_job_ids,
            message_type="broadcast",
            content_preview="hello",
            priority=1,
        )

        sent = mock_ws.send_json.call_args[0][0]
        assert sent["type"] == "message:received"
        assert sent["schema_version"] == "1.0"
        assert sent["data"]["tenant_key"] == tenant_key
        assert sent["data"]["from_job_id"] == from_job_id
        assert sent["data"]["to_job_ids"] == to_job_ids

    async def test_message_acknowledged_includes_schema_version_and_job_ids(self):
        from api.websocket import WebSocketManager

        tenant_key = "tenant-123"
        ws_manager = WebSocketManager()
        mock_ws = SimpleNamespace(send_json=AsyncMock())
        ws_manager.active_connections["client-1"] = mock_ws
        ws_manager.auth_contexts["client-1"] = {"tenant_key": tenant_key}

        job_id = str(uuid.uuid4())
        message_ids = [str(uuid.uuid4()), str(uuid.uuid4())]

        await ws_manager.broadcast_message_acknowledged(
            message_id=message_ids[0],
            agent_id=job_id,
            tenant_key=tenant_key,
            project_id=str(uuid.uuid4()),
            message_ids=message_ids,
        )

        sent = mock_ws.send_json.call_args[0][0]
        assert sent["type"] == "message:acknowledged"
        assert sent["schema_version"] == "1.0"
        assert sent["data"]["tenant_key"] == tenant_key
        assert sent["data"]["from_job_id"] == job_id
        assert sent["data"]["to_job_ids"] == [job_id]


class TestLegacyEventAliasing:
    async def test_agent_update_emits_legacy_alias_when_enabled(self):
        from api.websocket import WebSocketManager

        tenant_key = "tenant-legacy"
        ws_manager = WebSocketManager(emit_legacy_aliases=True)
        mock_ws = SimpleNamespace(send_json=AsyncMock())
        ws_manager.active_connections["client-1"] = mock_ws
        ws_manager.auth_contexts["client-1"] = {"tenant_key": tenant_key}

        await ws_manager.broadcast_agent_update(
            agent_id=str(uuid.uuid4()),
            agent_name="Implementer",
            project_id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            status="working",
            context_usage=123,
        )

        event_types = [call.args[0]["type"] for call in mock_ws.send_json.call_args_list]
        assert "agent:update" in event_types
        assert "agent_update" in event_types
