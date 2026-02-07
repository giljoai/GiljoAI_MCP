"""
WebSocket Bridge Endpoint - MCP to WebSocket Event Emission

Provides HTTP endpoints that MCP tools can call to trigger WebSocket broadcasts.
Solves the cross-process communication problem where MCP tools run in a separate
process and cannot directly access FastAPI's WebSocketManager.

Handover 0111 Issue #2: MCP-to-WebSocket HTTP Bridge
Created: 2025-11-07
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.dependencies.websocket import WebSocketDependency, get_websocket_dependency


logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket-bridge"])


class WebSocketEventRequest(BaseModel):
    """Request model for triggering WebSocket events from MCP tools."""

    event_type: str
    tenant_key: str
    data: dict[str, Any]


class WebSocketEventResponse(BaseModel):
    """Response model for WebSocket event emissions."""

    success: bool
    event_type: str
    clients_notified: int
    message: str | None = None


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
                        "agent_display_name": "implementer",
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
                status_code=status.HTTP_400_BAD_REQUEST, detail="event_type and tenant_key are required"
            )

        # Check if WebSocket manager is available
        if not ws_dep.manager:
            logger.warning(
                "WebSocket manager not available for broadcast",
                extra={"event_type": request.event_type, "tenant_key": request.tenant_key},
            )
            return WebSocketEventResponse(
                success=False,
                event_type=request.event_type,
                clients_notified=0,
                message="WebSocket manager not available",
            )

        clients_notified = await ws_dep.broadcast_to_tenant(
            tenant_key=request.tenant_key,
            event_type=request.event_type,
            data=request.data or {},
            schema_version="1.0",
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

    except Exception as e:
        logger.error(
            f"Failed to emit WebSocket event: {e}",
            extra={"event_type": request.event_type, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to emit WebSocket event: {e!s}",
        ) from e
