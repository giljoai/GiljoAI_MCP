# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""WebSocket connection/auth/subscribe wiring extracted from api/app.py.

Behavior-preserving (BE-6042b): these are the exact helpers ``app.py`` used to
host as module-level free functions, moved verbatim. They are invoked by the
``/ws/{client_id}`` endpoint registered in ``api.wiring.events``.
"""

from __future__ import annotations

import logging
from contextlib import nullcontext

from fastapi import HTTPException, WebSocket
from fastapi.exceptions import WebSocketException
from sqlalchemy import select

from api.app_state import state
from api.auth_utils import authenticate_websocket
from giljo_mcp.database import tenant_isolation_bypass
from giljo_mcp.models import Project
from giljo_mcp.models.agent_identity import AgentJob
from giljo_mcp.models.tasks import Message
from giljo_mcp.utils.log_sanitizer import sanitize


logger = logging.getLogger("api.app")


async def authenticate_ws_connection(
    websocket: WebSocket,
    client_id: str,
    api_key: str | None,
    token: str | None,
) -> dict | None:
    """Authenticate an incoming WebSocket connection and return the auth context.

    Obtains a short-lived database session (None in setup mode), delegates to
    authenticate_websocket, validates that a tenant_key is present for normal
    connections, and then cleans up the session.  On failure the connection is
    closed with code 1008 and None is returned.

    Args:
        websocket: The incoming WebSocket connection (not yet accepted).
        client_id: Caller-supplied client identifier.
        api_key: Optional API-key query param.
        token: Optional JWT query param.

    Returns:
        auth_context dict on success, or None if the connection was rejected.
    """
    try:
        session = None
        session_cm = None
        if state.db_manager:
            session_cm = state.db_manager.get_session_async()
            session = await session_cm.__aenter__()

        try:
            auth_result = await authenticate_websocket(websocket, db=session)

            await websocket.accept()

            user_info = auth_result.get("user", {})
            is_setup = auth_result.get("context") == "setup"
            tenant_key_from_user = user_info.get("tenant_key")

            if not tenant_key_from_user and not is_setup:
                logger.error("WebSocket rejected for %s: missing tenant_key in auth context", sanitize(client_id))
                await websocket.close(code=1008, reason="Missing tenant key")
                return None

            auth_context = {
                "user": user_info,
                "context": auth_result.get("context", "normal"),
                "tenant_key": tenant_key_from_user,
            }
            if token:
                auth_context["auth_type"] = "jwt"
            elif api_key:
                auth_context["auth_type"] = "api_key"
            else:
                auth_context["auth_type"] = "setup"

            await state.websocket_manager.connect(websocket, client_id, auth_context=auth_context)
            state.connections[client_id] = websocket

            auth_type = auth_context.get("auth_type", "setup")
            logger.info(
                "WebSocket connected: %s (context: %s, auth_type: %s)",
                sanitize(client_id),
                sanitize(str(auth_result.get("context", "normal"))),
                sanitize(auth_type),
            )
            return auth_context

        finally:
            if session_cm is not None:
                await session_cm.__aexit__(None, None, None)

    except WebSocketException as e:
        logger.warning("WebSocket authentication failed for %s: %s", sanitize(client_id), sanitize(str(e.reason)))
        await websocket.close(code=1008, reason=e.reason or "Unauthorized")
        return None


def ws_entity_resolution_scope(session, *, is_setup: bool, tenant_key: str | None):
    """Return the guard scope for a WS subscribe entity-resolution read.

    Authenticated connections pass their validated ``tenant_key`` into
    ``get_session_async`` so the session already carries tenant context and the
    guard applies its normal per-tenant filter — no bypass needed (nullcontext).

    Setup-mode connections have no tenant yet, so resolving the entity's tenant
    is a genuine pre-auth cross-tenant lookup; authorize it with a scoped bypass.
    """
    if is_setup or not tenant_key:
        return tenant_isolation_bypass(
            session,
            reason="setup-mode WS subscribe resolves entity tenant before auth",
            models=(Project, AgentJob, Message),
        )
    return nullcontext()


async def handle_ws_subscribe(
    websocket: WebSocket,
    client_id: str,
    data: dict,
    auth_context: dict,
) -> None:
    """Handle a WebSocket subscribe message with tenant isolation enforcement.

    Resolves the tenant_key for the requested entity by querying the database,
    denies the subscription when the tenant cannot be resolved, and blocks
    cross-tenant subscriptions (Handover 0769a security fix).

    Args:
        websocket: Active WebSocket connection.
        client_id: Caller-supplied client identifier.
        data: Parsed JSON message containing ``entity_type`` and ``entity_id``.
        auth_context: Auth context dict from authenticate_ws_connection,
                      must contain ``tenant_key``.
    """
    entity_type = data.get("entity_type")
    entity_id = data.get("entity_id")
    connection_tenant_key = auth_context.get("tenant_key")
    is_setup = auth_context.get("context") == "setup"

    try:
        tenant_key = None
        if state.db_manager:
            # Authenticated connections scope the entity-resolution read to the
            # connection's validated tenant_key (a client may only subscribe to
            # entities in its own tenant; the cross-tenant check below is then
            # belt-and-suspenders). Setup-mode connections have no tenant yet, so
            # the resolution read is a genuine pre-auth cross-tenant lookup —
            # authorize it with a scoped bypass.
            async with state.db_manager.get_session_async(tenant_key=connection_tenant_key) as session:
                with ws_entity_resolution_scope(session, is_setup=is_setup, tenant_key=connection_tenant_key):
                    if entity_type == "project":
                        stmt = select(Project).where(Project.id == entity_id)
                        result = await session.execute(stmt)
                        project = result.scalar_one_or_none()
                        if project:
                            tenant_key = project.tenant_key
                    elif entity_type == "agent":
                        stmt = select(AgentJob).where(AgentJob.job_id == entity_id)
                        result = await session.execute(stmt)
                        agent_job = result.scalar_one_or_none()
                        if agent_job:
                            tenant_key = agent_job.tenant_key
                    elif entity_type == "message":
                        stmt = select(Message).where(Message.id == entity_id)
                        result = await session.execute(stmt)
                        message = result.scalar_one_or_none()
                        if message:
                            tenant_key = message.tenant_key

        if not tenant_key:
            await websocket.send_json(
                {
                    "type": "error",
                    "error": "subscription_denied",
                    "message": f"Cannot resolve tenant for {entity_type}:{entity_id}",
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                }
            )
            return

        if tenant_key != auth_context.get("tenant_key"):
            logger.warning(
                f"Cross-tenant subscription blocked: user tenant={auth_context.get('tenant_key')}, "
                f"entity tenant={tenant_key}"
            )
            await websocket.send_json(
                {
                    "type": "error",
                    "error": "subscription_denied",
                    "message": "Cross-tenant subscription not allowed",
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                }
            )
            return

        await state.websocket_manager.subscribe(client_id, entity_type, entity_id, tenant_key)
        await websocket.send_json({"type": "subscribed", "entity_type": entity_type, "entity_id": entity_id})

    except HTTPException as e:
        await websocket.send_json(
            {
                "type": "error",
                "error": "subscription_denied",
                "message": str(e.detail),
                "entity_type": entity_type,
                "entity_id": entity_id,
            }
        )
