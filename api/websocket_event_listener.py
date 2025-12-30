"""
WebSocket Event Listener

Bridges EventBus events to WebSocket broadcasts.
Listens to events published from MCP tools and broadcasts via WebSocket manager.

Handover 0111 Issue #1: WebSocket Event Bus for MCP Context
Created: 2025-11-06
"""

import logging
from typing import Any, Dict

from api.event_bus import EventBus
from api.events.schemas import EventFactory

logger = logging.getLogger(__name__)


class WebSocketEventListener:
    """
    Listens to EventBus events and broadcasts via WebSocket manager.

    Bridge between MCP context and WebSocket infrastructure.
    Maintains multi-tenant isolation when broadcasting.

    Usage:
        ws_listener = WebSocketEventListener(event_bus, ws_manager)
        await ws_listener.start()
    """

    def __init__(self, event_bus: EventBus, ws_manager):
        """
        Initialize WebSocket event listener.

        Args:
            event_bus: EventBus instance to subscribe to
            ws_manager: WebSocketManager instance for broadcasting
        """
        self.event_bus = event_bus
        self.ws_manager = ws_manager
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def start(self) -> None:
        """
        Register all event handlers with EventBus.

        Called at application startup to wire up event handlers.
        """
        await self.event_bus.subscribe("project:mission_updated", self.handle_mission_updated)
        await self.event_bus.subscribe("agent:created", self.handle_agent_created)
        await self.event_bus.subscribe("product:status:changed", self.handle_product_status_changed)

        self.logger.info(
            "WebSocket event listener started",
            extra={
                "registered_events": [
                    "project:mission_updated",
                    "agent:created",
                    "product:status:changed",
                ],
            },
        )

    async def handle_product_status_changed(self, data: Dict[str, Any]) -> None:
        """
        Handle product:status:changed event.

        Broadcasts product status changes (activate/deactivate) tenant-scoped.

        Args:
            data: { tenant_key: str, product_id: str, is_active: bool }
        """
        try:
            tenant_key = data.get("tenant_key")
            product_id = data.get("product_id")
            is_active = bool(data.get("is_active", False))

            if not tenant_key or not product_id:
                self.logger.error(
                    "Missing required fields for product status change",
                    extra={"data": data},
                )
                return

            event = EventFactory.tenant_envelope(
                event_type="product:status:changed",
                tenant_key=tenant_key,
                data={
                    "product_id": product_id,
                    "is_active": is_active,
                },
            )

            sent_count = await self.ws_manager.broadcast_event_to_tenant(tenant_key=tenant_key, event=event)
            self.logger.info(
                f"Product status broadcasted to {sent_count} client(s)",
                extra={"product_id": product_id, "tenant_key": tenant_key, "sent_count": sent_count},
            )

        except Exception as e:
            self.logger.error(
                f"Error handling product status change event: {e}",
                extra={"error": str(e)},
                exc_info=True,
            )

    async def handle_mission_updated(self, data: Dict[str, Any]) -> None:
        """
        Handle project:mission_updated event.

        Broadcasts mission update to all clients in tenant via WebSocket.

        Args:
            data: Event data containing:
                - tenant_key: Tenant isolation key
                - project_id: Project UUID
                - mission: Updated mission text
                - user_config_applied: Boolean flag
                - token_estimate: Estimated token count
        """
        try:
            tenant_key = data.get("tenant_key")
            project_id = data.get("project_id")

            if not tenant_key or not project_id:
                self.logger.error(
                    "Missing required fields for mission update",
                    extra={"data": data},
                )
                return

            event = EventFactory.project_mission_updated(
                project_id=project_id,
                tenant_key=tenant_key,
                mission=data.get("mission", ""),
                token_estimate=data.get("token_estimate", 0),
                user_config_applied=data.get("user_config_applied", False),
            )

            sent_count = await self.ws_manager.broadcast_event_to_tenant(tenant_key=tenant_key, event=event)
            self.logger.info(
                f"Mission update broadcasted to {sent_count} client(s)",
                extra={
                    "project_id": project_id,
                    "tenant_key": tenant_key,
                    "sent_count": sent_count,
                },
            )

        except Exception as e:
            self.logger.error(
                f"Error handling mission update event: {e}",
                extra={"error": str(e)},
                exc_info=True,
            )

    async def handle_agent_created(self, data: Dict[str, Any]) -> None:
        """
        Handle agent:created event.

        Broadcasts agent creation to all clients in tenant via WebSocket.

        Args:
            data: Event data containing:
                - tenant_key: Tenant isolation key
                - project_id: Project UUID
                - agent_id: Agent job UUID
                - agent_type: Agent type string
                - agent_name: Human-readable name
                - status: Agent status
        """
        try:
            tenant_key = data.get("tenant_key")
            project_id = data.get("project_id")
            agent_id = data.get("agent_id") or data.get("agent_job_id")

            if not tenant_key or not project_id or not agent_id:
                self.logger.error(
                    "Missing required fields for agent creation",
                    extra={"data": data},
                )
                return

            event = EventFactory.agent_created(
                project_id=project_id,
                tenant_key=tenant_key,
                agent={
                    "id": agent_id,
                    "job_id": agent_id,
                    "agent_type": data.get("agent_type", "unknown"),
                    "agent_name": data.get("agent_name", "Unknown Agent"),
                    "status": data.get("status", "pending"),
                    "thin_client": data.get("thin_client", True),
                },
            )

            sent_count = await self.ws_manager.broadcast_event_to_tenant(tenant_key=tenant_key, event=event)
            self.logger.info(
                f"Agent creation broadcasted to {sent_count} client(s)",
                extra={
                    "agent_id": agent_id,
                    "project_id": project_id,
                    "tenant_key": tenant_key,
                    "sent_count": sent_count,
                },
            )

        except Exception as e:
            self.logger.error(
                f"Error handling agent creation event: {e}",
                extra={"error": str(e)},
                exc_info=True,
            )
