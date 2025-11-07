"""
WebSocket Event Listener

Bridges EventBus events to WebSocket broadcasts.
Listens to events published from MCP tools and broadcasts via WebSocket manager.

Handover 0111 Issue #1: WebSocket Event Bus for MCP Context
Created: 2025-11-06
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from api.event_bus import EventBus

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

        self.logger.info(
            "WebSocket event listener started",
            extra={
                "registered_events": ["project:mission_updated", "agent:created"],
            },
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

            # Build standardized WebSocket message
            message = {
                "type": "project:mission_updated",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "schema_version": "1.0",
                "data": {
                    "project_id": project_id,
                    "tenant_key": tenant_key,
                    "mission": data.get("mission", ""),
                    "user_config_applied": data.get("user_config_applied", False),
                    "token_estimate": data.get("token_estimate", 0),
                },
            }

            # Broadcast to tenant with multi-tenant isolation
            sent_count = 0
            for client_id, ws in self.ws_manager.active_connections.items():
                auth_context = self.ws_manager.auth_contexts.get(client_id, {})

                if auth_context.get("tenant_key") != tenant_key:
                    continue

                try:
                    await ws.send_json(message)
                    sent_count += 1
                except Exception as e:
                    self.logger.warning(
                        f"Failed to send mission update to client {client_id}: {e}",
                        extra={"client_id": client_id, "error": str(e)},
                    )

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

            # Build standardized WebSocket message
            message = {
                "type": "agent:created",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "schema_version": "1.0",
                "data": {
                    "project_id": project_id,
                    "tenant_key": tenant_key,
                    "agent": {
                        "id": agent_id,
                        "job_id": agent_id,
                        "agent_type": data.get("agent_type", "unknown"),
                        "agent_name": data.get("agent_name", "Unknown Agent"),
                        "status": data.get("status", "pending"),
                        "thin_client": data.get("thin_client", True),
                    },
                },
            }

            # Broadcast to tenant with multi-tenant isolation
            sent_count = 0
            for client_id, ws in self.ws_manager.active_connections.items():
                auth_context = self.ws_manager.auth_contexts.get(client_id, {})

                if auth_context.get("tenant_key") != tenant_key:
                    continue

                try:
                    await ws.send_json(message)
                    sent_count += 1
                except Exception as e:
                    self.logger.warning(
                        f"Failed to send agent creation to client {client_id}: {e}",
                        extra={"client_id": client_id, "error": str(e)},
                    )

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
