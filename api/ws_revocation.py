# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""WebSocket revocation helper extracted from WebSocketManager (TSK-9006).

Force-close a tenant's live sockets when a user is deactivated. Extracted from
api/websocket.py so that already-at-budget file does not grow (shrink-only size
ratchet). This operates directly on the manager's connection registry + broker —
treat it as an internal of WebSocketManager, not a public API. Edition Scope:
Both (CE-shared; no saas imports).
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import asyncpg

from api.broker.base import WebSocketBrokerMessage
from giljo_mcp.logging import ErrorCode


if TYPE_CHECKING:
    from api.websocket import WebSocketManager


logger = logging.getLogger(__name__)


async def close_tenant_sockets(
    manager: WebSocketManager,
    tenant_key: str,
    *,
    reason: str,
    publish_to_broker: bool,
) -> int:
    """Force-close every live socket in ``tenant_key`` (the body of disconnect_tenant).

    Backs "deactivating a user must bite live sessions": is_active is only
    re-checked at the WS handshake, so a deactivated account keeps a live socket
    until it reconnects. Scope is the tenant (ADR-009: revocation is
    tenant/account-scoped; tenant_key is per-user today) via the BE-3008b index.
    Multi-worker: after closing local sockets, publish a control message on the
    SAME giljo_ws_events broker (no new channel); the origin-echo guard in
    attach_broker stops a self re-close, and the publish gate matches
    broadcast_event_to_tenant (broker attached AND multi-worker). Close code 1008
    (policy violation) matches the handshake-reject convention in
    wiring/websocket.py. Returns the local sockets closed.
    """
    if not tenant_key:
        raise ValueError("tenant_key cannot be empty")

    # Read the send timeout via the module so a test monkeypatch is honored.
    import api.websocket as ws_mod

    timeout = ws_mod._WS_SEND_TIMEOUT_SECONDS

    # Snapshot: close()/disconnect() mutate the index + connection dict.
    closed_count = 0
    for client_id in list(manager.tenant_connections.get(tenant_key, set())):
        connection = manager.active_connections.get(client_id)
        if connection is not None:
            websocket = manager._unwrap_websocket_connection(connection)
            try:
                # Bound the close so a wedged socket can't hang the loop.
                await asyncio.wait_for(websocket.close(code=1008, reason=reason), timeout=timeout)
                closed_count += 1
            except (RuntimeError, ValueError, KeyError, TimeoutError, OSError) as e:
                logger.debug("disconnect_tenant close failed for client_id=%s: %s", client_id, e)
        # Always deregister so a half-closed socket receives no more fan-out.
        manager.disconnect(client_id)

    if publish_to_broker and manager._event_broker and manager._publish_to_broker_enabled:
        try:
            await manager._event_broker.publish(
                WebSocketBrokerMessage(
                    tenant_key=tenant_key, event={}, origin=manager._broker_origin, control="disconnect_tenant"
                )
            )
        except (RuntimeError, ValueError, KeyError, asyncpg.PostgresError) as e:
            # Local eviction already happened; a publish failure must not raise.
            logger.warning(
                "websocket_disconnect_tenant_publish_failed error_code=%s tenant_key=%s error_message=%s",
                ErrorCode.WS_BROADCAST_FAILED.value,
                tenant_key,
                str(e),
            )

    logger.info(
        "WebSocket disconnect_tenant: %s local socket(s) closed",
        closed_count,
        extra={"tenant_key": tenant_key, "closed_count": closed_count},
    )
    return closed_count
