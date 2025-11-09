"""
WebSocket Bridge Endpoint - MCP to WebSocket Event Emission

Provides HTTP endpoints that MCP tools can call to trigger WebSocket broadcasts.
Solves the cross-process communication problem where MCP tools run in a separate
process and cannot directly access FastAPI's WebSocketManager.

Handover 0111 Issue #2: MCP-to-WebSocket HTTP Bridge
Created: 2025-11-07
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.dependencies.websocket import WebSocketDependency, get_websocket_dependency


logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket-bridge"])


class WebSocketEventRequest(BaseModel):
    """Request model for triggering WebSocket events from MCP tools."""

    event_type: str
    tenant_key: str
    data: Dict[str, Any]


class WebSocketEventResponse(BaseModel):
    """Response model for WebSocket event emissions."""

    success: bool
    event_type: str
    clients_notified: int
    message: Optional[str] = None


@router.post("/emit", response_model=WebSocketEventResponse)
async def emit_websocket_event(
    request: WebSocketEventRequest,
    ws_dep: WebSocketDependency = Depends(get_websocket_dependency),
):
    """
    Emit WebSocket event to all clients in tenant.

    This endpoint is called by MCP tools (running in MCP server process) to trigger
    WebSocket broadcasts in the FastAPI process.

    **Security**: This endpoint is internal-only. It should NOT be exposed publicly.
    Consider adding IP whitelist or internal-only API key authentication.

    Args:
        request: WebSocketEventRequest containing event_type, tenant_key, and data
        ws_dep: WebSocket dependency (auto-injected)

    Returns:
        WebSocketEventResponse with success status and client count

    Example Usage from MCP Tool:
        ```python
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:7272/api/v1/ws-bridge/emit",
                json={
                    "event_type": "agent:created",
                    "tenant_key": "tk_...",
                    "data": {
                        "project_id": "proj_123",
                        "agent_id": "agent_456",
                        "agent_type": "implementer",
                        "agent_name": "Backend Implementer",
                        "status": "pending"
                    }
                }
            )
        ```
    """
    try:
        # Validate required fields
        if not request.event_type or not request.tenant_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="event_type and tenant_key are required"
            )

        # Prepare WebSocket message (FLATTEN payload for frontend handlers)
        # Frontend handlers expect fields like tenant_key, project_id at the top level, not nested.
        flattened = dict(request.data or {})
        flattened["tenant_key"] = request.tenant_key
        message = {
            "type": request.event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "schema_version": "1.0",
            **flattened,
        }

        # Check if WebSocket manager is available
        if not ws_dep.manager:
            logger.warning(
                "WebSocket manager not available for broadcast",
                extra={"event_type": request.event_type, "tenant_key": request.tenant_key}
            )
            return WebSocketEventResponse(
                success=False,
                event_type=request.event_type,
                clients_notified=0,
                message="WebSocket manager not available"
            )

        # Broadcast to tenant
        clients_notified = 0
        logger.info(f"[BRIDGE DEBUG] Total active connections: {len(ws_dep.manager.active_connections)}, Target tenant: {request.tenant_key}")
        for client_id, ws in ws_dep.manager.active_connections.items():
            auth_context = ws_dep.manager.auth_contexts.get(client_id, {})
            client_tenant = auth_context.get("tenant_key")

            logger.info(f"[BRIDGE DEBUG] Client {client_id[:8]}: tenant={client_tenant}, target={request.tenant_key}, match={client_tenant == request.tenant_key}")

            # Multi-tenant isolation
            if client_tenant != request.tenant_key:
                logger.info(f"[BRIDGE DEBUG] Skipping client {client_id[:8]} - tenant mismatch")
                continue

            try:
                await ws.send_json(message)
                clients_notified += 1
            except Exception as e:
                logger.warning(
                    f"Failed to send {request.event_type} to client {client_id}: {e}",
                    extra={"client_id": client_id, "error": str(e)},
                )

        logger.info(
            f"WebSocket event emitted: {request.event_type} to {clients_notified} client(s)",
            extra={
                "event_type": request.event_type,
                "tenant_key": request.tenant_key,
                "clients_notified": clients_notified,
            },
        )

        return WebSocketEventResponse(
            success=True,
            event_type=request.event_type,
            clients_notified=clients_notified,
            message=f"Event broadcasted to {clients_notified} client(s)",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to emit WebSocket event: {e}",
            extra={"event_type": request.event_type, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to emit WebSocket event: {str(e)}",
        ) from e
