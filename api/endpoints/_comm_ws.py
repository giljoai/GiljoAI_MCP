# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Best-effort WS broadcast helpers for the Agent Message Hub (BE-6054ef).

These two helpers are called from BOTH the REST router (comm_threads.py) and
the MCP wrapper (_comm_tools.py) so every post/baton update pushes a live
WS event to the dashboard. All failures are swallowed and logged — the DB
write has already committed before these are called, so a WS send failure
must NEVER surface as a 500 to the caller.
"""

import logging
from typing import Any

from giljo_mcp.utils.log_sanitizer import sanitize


logger = logging.getLogger(__name__)


async def broadcast_thread_message(
    ws_manager: Any,
    tenant_key: str,
    *,
    thread_id: str,
    message_id: str,
    from_agent_id: str,
    from_display_name: str,
    content: str,
    message_type: str,
    priority: str,
    requires_action: bool,
    project_id: str | None,
) -> None:
    """Broadcast a new thread message event to all clients in a tenant.

    Caller MUST check ``if state.websocket_manager:`` before calling.
    """
    event: dict[str, Any] = {
        "type": "thread_message",
        "data": {
            "tenant_key": tenant_key,
            "thread_id": thread_id,
            "message_id": message_id,
            "from_agent_id": from_agent_id,
            "from_display_name": from_display_name,
            "content": content,
            "message_type": message_type,
            "priority": priority,
            "requires_action": requires_action,
            "project_id": project_id,
            "update_type": "new",
        },
    }
    try:
        await ws_manager.broadcast_event_to_tenant(tenant_key, event)
    except Exception:  # noqa: BLE001 - WS failure must not affect the already-committed write
        logger.warning("broadcast_thread_message failed for thread %s (non-fatal)", sanitize(thread_id), exc_info=True)


async def broadcast_thread_update(
    ws_manager: Any,
    tenant_key: str,
    *,
    thread_id: str,
    chat_id: str,
    status: str,
    next_action_owner: str | None,
    update_type: str,
) -> None:
    """Broadcast a thread metadata-change event (status/baton) to all clients in a tenant.

    Caller MUST check ``if state.websocket_manager:`` before calling.
    """
    event: dict[str, Any] = {
        "type": "thread_update",
        "data": {
            "tenant_key": tenant_key,
            "thread_id": thread_id,
            "chat_id": chat_id,
            "status": status,
            "next_action_owner": next_action_owner,
            "update_type": update_type,
        },
    }
    try:
        await ws_manager.broadcast_event_to_tenant(tenant_key, event)
    except Exception:  # noqa: BLE001 - WS failure must not affect the already-committed write
        logger.warning("broadcast_thread_update failed for thread %s (non-fatal)", sanitize(thread_id), exc_info=True)
