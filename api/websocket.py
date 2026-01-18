"""
WebSocket manager for real-time updates
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from fastapi import HTTPException, WebSocket

from api.broker.base import WebSocketBrokerMessage, WebSocketEventBroker
from api.auth_utils import check_subscription_permission
from api.events.schemas import EventFactory
from src.giljo_mcp.logging import get_logger, ErrorCode


logger = get_logger(__name__)

EVENT_TYPE_ALIASES: dict[str, tuple[str, ...]] = {
    # Legacy drift: underscore vs colon
    "agent:update": ("agent_update",),
    # Product events (legacy underscore variants)
    "product:memory:updated": ("product:memory_updated",),
    "product:learning:added": ("product:learning_added",),
    "product:status:changed": ("product:status_changed",),
}


class WebSocketManager:
    """Manages WebSocket connections and subscriptions with authentication"""

    def __init__(self, *, emit_legacy_aliases: bool = True):
        self.emit_legacy_aliases = emit_legacy_aliases
        self.active_connections: dict[str, WebSocket] = {}
        self.auth_contexts: dict[str, dict[str, Any]] = {}  # NEW: Store auth context
        self.subscriptions: dict[str, set[str]] = {}  # client_id -> set of subscriptions
        self.entity_subscribers: dict[str, set[str]] = (
            {}
        )  # entity_key -> set of client_ids  # entity_key -> set of client_ids
        self._event_broker: Optional[WebSocketEventBroker] = None
        self._broker_unsubscribe = None
        self._broker_origin = uuid4().hex

    def attach_broker(self, broker: WebSocketEventBroker) -> None:
        if self._broker_unsubscribe:
            try:
                self._broker_unsubscribe()
            except Exception:
                logger.debug("Failed unsubscribing broker handler", exc_info=True)
            self._broker_unsubscribe = None

        self._event_broker = broker

        async def _handle(message: WebSocketBrokerMessage) -> None:
            # Avoid echo: the publishing worker already broadcast locally.
            if message.origin and message.origin == self._broker_origin:
                return

            await self.broadcast_event_to_tenant(
                tenant_key=message.tenant_key,
                event=message.event,
                exclude_client=message.exclude_client,
                publish_to_broker=False,
            )

        self._broker_unsubscribe = broker.subscribe(_handle)

    def _event_types_for_broadcast(self, event_type: str) -> list[str]:
        if not self.emit_legacy_aliases:
            return [event_type]

        for canonical, aliases in EVENT_TYPE_ALIASES.items():
            types = (canonical, *aliases)
            if event_type in types:
                # Always emit canonical first, then legacy aliases.
                seen: set[str] = set()
                ordered = [canonical, *aliases]
                return [t for t in ordered if not (t in seen or seen.add(t))]

        return [event_type]

    @staticmethod
    def _unwrap_websocket_connection(connection: Any) -> Any:
        websocket = getattr(connection, "websocket", None)
        if isinstance(websocket, WebSocket):
            return websocket
        return connection

    async def broadcast_event_to_tenant(
        self,
        tenant_key: str,
        event: dict[str, Any],
        exclude_client: Optional[str] = None,
        *,
        publish_to_broker: bool = True,
    ) -> int:
        """Broadcast a canonical event envelope to all clients in a tenant."""
        if not tenant_key:
            raise ValueError("tenant_key cannot be empty")

        if not isinstance(event, dict):
            raise ValueError("event must be a dictionary")

        event_type = event.get("type")
        if not event_type:
            raise ValueError("event.type cannot be empty")

        data = event.get("data") or {}
        if not isinstance(data, dict):
            raise ValueError("event.data must be a dictionary")

        if "tenant_key" not in data:
            data = {**data, "tenant_key": tenant_key}
        elif data.get("tenant_key") != tenant_key:
            raise ValueError("event.data.tenant_key must match tenant_key")

        message = {
            "type": event_type,
            "timestamp": event.get("timestamp") or datetime.now(timezone.utc).isoformat(),
            "schema_version": event.get("schema_version") or "1.0",
            "data": data,
        }

        event_types = self._event_types_for_broadcast(event_type)

        sent_count = 0
        failed_count = 0
        disconnected_clients: list[str] = []

        # Snapshot connections to avoid mutation during await.
        connections_snapshot = list(self.active_connections.items())

        for client_id, connection in connections_snapshot:
            websocket = self._unwrap_websocket_connection(connection)

            if exclude_client and client_id == exclude_client:
                continue

            auth_context = self.auth_contexts.get(client_id, {})
            if not auth_context:
                derived_tenant = getattr(connection, "tenant_key", None) or getattr(websocket, "tenant_key", None)
                derived_user = getattr(connection, "user_id", None)
                derived_username = getattr(connection, "username", None)
                if derived_tenant:
                    auth_context = {
                        "tenant_key": derived_tenant,
                        "user_id": derived_user,
                        "username": derived_username,
                    }
                    self.auth_contexts[client_id] = auth_context

            client_tenant = auth_context.get("tenant_key")
            if client_tenant != tenant_key:
                continue

            client_sent_any = False
            try:
                for t in event_types:
                    await websocket.send_json({**message, "type": t})
                    client_sent_any = True
            except Exception as e:
                failed_count += 1
                logger.warning(
                    "websocket_send_failed",
                    error_code=ErrorCode.WS_MESSAGE_SEND_FAILED.value,
                    client_id=client_id,
                    tenant_key=tenant_key,
                    event_type=event_type,
                    error_message=str(e),
                )
                disconnected_clients.append(client_id)

            if client_sent_any:
                sent_count += 1

        for client_id in disconnected_clients:
            self.disconnect(client_id)

        if publish_to_broker and self._event_broker:
            try:
                await self._event_broker.publish(
                    WebSocketBrokerMessage(
                        tenant_key=tenant_key,
                        event=message,
                        exclude_client=exclude_client,
                        origin=self._broker_origin,
                    )
                )
            except Exception as e:
                logger.warning(
                    "websocket_broker_publish_failed",
                    error_code=ErrorCode.WS_BROADCAST_FAILED.value,
                    tenant_key=tenant_key,
                    event_type=event_type,
                    error_message=str(e),
                )

        logger.info(
            f"WebSocket broadcast to tenant completed: {sent_count} sent, {failed_count} failed",
            extra={
                "tenant_key": tenant_key,
                "event_type": event_type,
                "sent_count": sent_count,
                "failed_count": failed_count,
                "total_clients": len(connections_snapshot),
                "exclude_client": exclude_client,
            },
        )

        return sent_count

    async def connect(self, websocket: WebSocket, client_id: str, auth_context: Optional[dict[str, Any]] = None):
        """Accept and track new WebSocket connection with auth context"""
        # Note: websocket.accept() is called in the endpoint after validation
        self.active_connections[client_id] = websocket
        self.auth_contexts[client_id] = auth_context or {}  # Store auth context
        self.subscriptions[client_id] = set()

        logger.info(
            f"WebSocket connected: {client_id} "
            f"(auth_type: {auth_context.get('auth_type', 'none') if auth_context else 'none'})"
        )

    def disconnect(self, client_id: str):
        """Remove WebSocket connection and clean up subscriptions"""
        # Remove from active connections
        if client_id in self.active_connections:
            del self.active_connections[client_id]

        # Remove auth context
        if client_id in self.auth_contexts:
            del self.auth_contexts[client_id]

        # Clean up subscriptions
        if client_id in self.subscriptions:
            for entity_key in self.subscriptions[client_id]:
                if entity_key in self.entity_subscribers:
                    self.entity_subscribers[entity_key].discard(client_id)
                    if not self.entity_subscribers[entity_key]:
                        del self.entity_subscribers[entity_key]
            del self.subscriptions[client_id]

        logger.info(f"WebSocket disconnected: {client_id}")

    async def subscribe(self, client_id: str, entity_type: str, entity_id: str, tenant_key: Optional[str] = None):
        """Subscribe client to entity updates with authorization check"""

        # Check authorization
        auth_context = self.auth_contexts.get(client_id, {})
        if not check_subscription_permission(auth_context, entity_type, entity_id, tenant_key):
            logger.warning(
                "unauthorized_subscription_attempt",
                error_code=ErrorCode.WS_AUTHENTICATION_FAILED.value,
                client_id=client_id,
                entity_type=entity_type,
                entity_id=entity_id,
                tenant_key=tenant_key,
            )
            raise HTTPException(status_code=403, detail="Not authorized to subscribe to this entity")

        entity_key = f"{entity_type}:{entity_id}"

        # Track subscription for client
        if client_id in self.subscriptions:
            self.subscriptions[client_id].add(entity_key)

        # Track subscribers for entity
        if entity_key not in self.entity_subscribers:
            self.entity_subscribers[entity_key] = set()
        self.entity_subscribers[entity_key].add(client_id)

        logger.debug(f"Client {client_id} subscribed to {entity_key}")

    async def unsubscribe(self, client_id: str, entity_type: str, entity_id: str):
        """Unsubscribe client from entity updates"""
        entity_key = f"{entity_type}:{entity_id}"

        # Remove subscription for client
        if client_id in self.subscriptions:
            self.subscriptions[client_id].discard(entity_key)

        # Remove subscriber from entity
        if entity_key in self.entity_subscribers:
            self.entity_subscribers[entity_key].discard(client_id)
            if not self.entity_subscribers[entity_key]:
                del self.entity_subscribers[entity_key]

        logger.debug(f"Client {client_id} unsubscribed from {entity_key}")

    async def send_personal_message(self, message: str, client_id: str):
        """Send message to specific client"""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.exception(
                    "websocket_send_message_error",
                    error_code=ErrorCode.WS_MESSAGE_SEND_FAILED.value,
                    client_id=client_id,
                    error_message=str(e),
                )
                self.disconnect(client_id)

    async def send_json(self, data: dict, client_id: str):
        """Send JSON data to specific client"""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_json(data)
            except Exception as e:
                logger.exception(
                    "websocket_send_json_error",
                    error_code=ErrorCode.WS_MESSAGE_SEND_FAILED.value,
                    client_id=client_id,
                    error_message=str(e),
                )
                self.disconnect(client_id)

    async def broadcast(self, message: str):
        """Broadcast message to all connected clients"""
        disconnected = []
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.exception(
                    "websocket_broadcast_error",
                    error_code=ErrorCode.WS_BROADCAST_FAILED.value,
                    client_id=client_id,
                    error_message=str(e),
                )
                disconnected.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)

    async def broadcast_json(self, data: dict):
        """Broadcast JSON data to all connected clients"""
        message = json.dumps(data)
        await self.broadcast(message)

    async def broadcast_to_tenant(
        self,
        tenant_key: str,
        event_type: str,
        data: dict[str, Any],
        schema_version: str = "1.0",
        exclude_client: Optional[str] = None,
    ) -> int:
        """Broadcast an event to all connected clients in a tenant.

        This is the canonical tenant broadcast entrypoint. It always sends a
        standardized event envelope: {type, timestamp, schema_version, data}.
        """
        if not tenant_key:
            raise ValueError("tenant_key cannot be empty")

        if not event_type:
            raise ValueError("event_type cannot be empty")

        event = EventFactory.tenant_envelope(
            event_type=event_type,
            tenant_key=tenant_key,
            data=data,
            schema_version=schema_version,
        )

        return await self.broadcast_event_to_tenant(
            tenant_key=tenant_key,
            event=event,
            exclude_client=exclude_client,
        )

    async def notify_entity_update(self, entity_type: str, entity_id: str, update_data: dict):
        """Notify all subscribers of an entity update"""
        entity_key = f"{entity_type}:{entity_id}"

        if entity_key in self.entity_subscribers:
            message = {"type": "entity_update", "entity_type": entity_type, "entity_id": entity_id, "data": update_data}

            disconnected = []
            for client_id in self.entity_subscribers[entity_key]:
                if client_id in self.active_connections:
                    try:
                        await self.send_json(message, client_id)
                    except Exception as e:
                        logger.exception(
                            "websocket_notify_error",
                            error_code=ErrorCode.WS_MESSAGE_SEND_FAILED.value,
                            client_id=client_id,
                            error_message=str(e),
                        )
                        disconnected.append(client_id)

            # Clean up disconnected clients
            for client_id in disconnected:
                self.disconnect(client_id)

    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)

    def get_subscription_count(self, entity_type: Optional[str] = None, entity_id: Optional[str] = None) -> int:
        """Get number of subscriptions for an entity"""
        if entity_type and entity_id:
            entity_key = f"{entity_type}:{entity_id}"
            return len(self.entity_subscribers.get(entity_key, []))
        return sum(len(subs) for subs in self.subscriptions.values())

    def get_auth_context(self, client_id: str) -> Optional[dict[str, Any]]:
        """Get auth context for a client"""
        return self.auth_contexts.get(client_id)

    def is_authenticated(self, client_id: str) -> bool:
        """Check if client is authenticated"""
        auth_context = self.auth_contexts.get(client_id, {})
        return auth_context.get("auth_type", "none") != "none"

    # Enhanced broadcast methods for real-time updates
    # Note: broadcast_agent_update method is defined later with full multi-tenant support

    async def broadcast_message_update(
        self,
        message_id: str,
        project_id: str,
        update_type: str,  # 'new', 'acknowledged', 'completed'
        message_data: dict,
    ):
        """Broadcast message queue updates to subscribed clients"""
        message = {
            "type": "message",
            "data": {
                "message_id": message_id,
                "project_id": project_id,
                "update_type": update_type,
                "from_agent": message_data.get("from_agent"),
                "to_agents": message_data.get("to_agents"),
                "content": message_data.get("content"),
                "priority": message_data.get("priority"),
                "status": message_data.get("status"),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Notify project subscribers
        await self.notify_entity_update("project", project_id, message)

        # Notify specific agent subscribers if applicable
        if message_data.get("to_agents"):
            for agent in message_data.get("to_agents", []):
                await self.notify_entity_update("agent", f"{project_id}:{agent}", message)

    async def broadcast_progress(
        self, operation_id: str, project_id: str, percentage: float, message: str, details: Optional[dict] = None
    ):
        """Broadcast progress updates for long-running operations"""
        progress_message = {
            "type": "progress",
            "data": {
                "operation_id": operation_id,
                "project_id": project_id,
                "percentage": min(100, max(0, percentage)),  # Clamp between 0-100
                "message": message,
                "details": details or {},
                "is_complete": percentage >= 100,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Notify project subscribers
        await self.notify_entity_update("project", project_id, progress_message)

    async def broadcast_notification(
        self,
        notification_type: str,  # 'info', 'warning', 'error', 'success'
        title: str,
        message: str,
        project_id: Optional[str] = None,
        target_clients: Optional[list[str]] = None,
    ):
        """Broadcast system notifications to clients"""
        notification = {
            "type": "notification",
            "data": {
                "notification_type": notification_type,
                "title": title,
                "message": message,
                "project_id": project_id,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if target_clients:
            # Send to specific clients
            for client_id in target_clients:
                await self.send_json(notification, client_id)
        elif project_id:
            # Send to project subscribers
            await self.notify_entity_update("project", project_id, notification)
        else:
            # Broadcast to all
            await self.broadcast_json(notification)

    async def broadcast_project_update(
        self,
        project_id: str,
        update_type: str,
        project_data: dict,  # 'created', 'status_changed', 'closed'
    ):
        """Broadcast project updates to subscribed clients"""
        message = {
            "type": "project_update",
            "data": {
                "project_id": project_id,
                "update_type": update_type,
                "name": project_data.get("name"),
                "status": project_data.get("status"),
                "mission": project_data.get("mission"),
                "context_used": project_data.get("context_used"),
                "context_budget": project_data.get("context_budget"),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Notify project subscribers
        await self.notify_entity_update("project", project_id, message)

    # Heartbeat mechanism

    async def start_heartbeat(self, interval: int = 30):
        """Start heartbeat mechanism to keep connections alive"""
        while True:
            await asyncio.sleep(interval)
            await self.send_heartbeat()

    async def send_heartbeat(self):
        """Send heartbeat ping to all connected clients"""
        heartbeat = {"type": "ping", "timestamp": datetime.now(timezone.utc).isoformat()}

        disconnected = []
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(heartbeat)
            except Exception as e:
                logger.debug(f"Heartbeat failed for {client_id}: {e}")
                disconnected.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)
            logger.info(f"Removed inactive connection: {client_id}")

    async def handle_pong(self, client_id: str):
        """Handle pong response from client"""
        # Could track last pong time for connection health monitoring
        logger.debug(f"Received pong from {client_id}")

    # Sub-agent integration broadcasts

    async def broadcast_sub_agent_spawned(
        self,
        interaction_id: str,
        parent_agent_name: str,
        sub_agent_name: str,
        project_id: str,
        mission: str,
        start_time: str,
        meta_data: Optional[dict] = None,
    ):
        """Broadcast when a parent agent spawns a sub-agent"""
        message = {
            "type": "agent.sub_agent.spawned",
            "data": {
                "interaction_id": interaction_id,
                "parent_agent_name": parent_agent_name,
                "sub_agent_name": sub_agent_name,
                "project_id": project_id,
                "mission": mission,
                "start_time": start_time,
                "meta_data": meta_data or {},
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Notify project subscribers
        await self.notify_entity_update("project", project_id, message)

        # Notify parent agent subscribers
        await self.notify_entity_update("agent", f"{project_id}:{parent_agent_name}", message)

        # Log for debugging
        logger.info(f"Broadcast sub-agent spawn: {parent_agent_name} -> {sub_agent_name}")

    async def broadcast_sub_agent_completed(
        self,
        interaction_id: str,
        sub_agent_name: str,
        parent_agent_name: str,
        project_id: str,
        status: str,  # 'completed' or 'error'
        duration_seconds: int,
        tokens_used: Optional[int] = None,
        result: Optional[str] = None,
        error_message: Optional[str] = None,
        meta_data: Optional[dict] = None,
    ):
        """Broadcast when a sub-agent completes (success or error)"""
        event_type = "agent.sub_agent.completed" if status == "completed" else "agent.sub_agent.error"

        message = {
            "type": event_type,
            "data": {
                "interaction_id": interaction_id,
                "sub_agent_name": sub_agent_name,
                "parent_agent_name": parent_agent_name,
                "project_id": project_id,
                "status": status,
                "duration_seconds": duration_seconds,
                "tokens_used": tokens_used,
                "result": result if status == "completed" else None,
                "error_message": error_message if status == "error" else None,
                "meta_data": meta_data or {},
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Notify project subscribers
        await self.notify_entity_update("project", project_id, message)

        # Notify parent agent subscribers
        await self.notify_entity_update("agent", f"{project_id}:{parent_agent_name}", message)

        # Log for debugging
        logger.info(f"Broadcast sub-agent {status}: {sub_agent_name} (duration: {duration_seconds}s)")

    async def broadcast_agent_update(
        self,
        agent_id: str,
        agent_name: str,
        project_id: str,
        tenant_key: str,
        status: str,
        context_usage: int,
        context_delta: Optional[int] = None,
        current_task: Optional[str] = None,
        progress_percentage: Optional[int] = None,
        meta_data: Optional[dict] = None,
        failure_reason: Optional[str] = None,  # Handover 0113
        decommissioned_at: Optional[str] = None,  # Handover 0113
    ):
        """Broadcast real-time status updates during agent execution."""
        data: dict[str, Any] = {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "project_id": project_id,
            "tenant_key": tenant_key,
            "status": status,
            "context_usage": context_usage,
            "context_delta": context_delta,
            "current_task": current_task,
            "progress_percentage": progress_percentage,
            "meta_data": meta_data or {},
            "update_time": datetime.now(timezone.utc).isoformat(),
        }

        if status == "failed" and failure_reason:
            data["failure_reason"] = failure_reason

        if status == "decommissioned" and decommissioned_at:
            data["decommissioned_at"] = decommissioned_at

        event = EventFactory.tenant_envelope(
            event_type="agent:update",
            tenant_key=tenant_key,
            data=data,
            schema_version="1.0",
        )

        await self.broadcast_event_to_tenant(tenant_key=tenant_key, event=event)

        await self.notify_entity_update("project", project_id, event)
        await self.notify_entity_update("agent", f"{project_id}:{agent_name}", event)

        logger.debug(f"Broadcast agent:update - {agent_name} (status: {status}, context: {context_usage})")

    async def broadcast_template_update(
        self,
        template_id: str,
        template_name: str,
        operation: str,  # 'create', 'update', 'delete', 'archive'
        tenant_key: str,
        product_id: str,
        user_id: Optional[str] = None,
        change_summary: Optional[str] = None,
        version: Optional[int] = None,
        meta_data: Optional[dict] = None,
    ):
        """Broadcast template CRUD operations."""
        data: dict[str, Any] = {
            "template_id": template_id,
            "template_name": template_name,
            "operation": operation,
            "tenant_key": tenant_key,
            "product_id": product_id,
            "user_id": user_id,
            "change_summary": change_summary,
            "version": version,
            "meta_data": meta_data or {},
            "update_time": datetime.now(timezone.utc).isoformat(),
        }

        event = EventFactory.tenant_envelope(
            event_type="template:update",
            tenant_key=tenant_key,
            data=data,
            schema_version="1.0",
        )

        await self.broadcast_event_to_tenant(tenant_key=tenant_key, event=event)

        await self.notify_entity_update("product", product_id, event)

        logger.info(f"Broadcast template:update - {template_name} ({operation}) by user {user_id}")

    async def broadcast_templates_exported(
        self,
        tenant_key: str,
        product_id: str,
        template_count: int,
        export_path: str,
        requested_by: Optional[str] = None,
    ):
        """Broadcast when templates are exported."""
        data: dict[str, Any] = {
            "tenant_key": tenant_key,
            "product_id": product_id,
            "template_count": template_count,
            "export_path": export_path,
            "requested_by": requested_by,
        }

        event = EventFactory.tenant_envelope(
            event_type="template:exported",
            tenant_key=tenant_key,
            data=data,
            schema_version="1.0",
        )

        await self.broadcast_event_to_tenant(tenant_key=tenant_key, event=event)

        await self.notify_entity_update("product", product_id, event)

        logger.info(f"Broadcast template:exported - {template_count} templates exported")

    # Agent Job Event Broadcasts (Handover 0019, 0286, 0362)

    async def broadcast_job_created(
        self,
        job_id: str,
        agent_display_name: str,
        tenant_key: str,
        spawned_by: Optional[str] = None,
        mission_preview: Optional[str] = None,
        created_at: Optional[datetime] = None,
        project_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        status: str = "waiting",
    ):
        """Broadcast agent job creation events."""
        created_ts = (created_at or datetime.now(timezone.utc)).isoformat()

        job_event = EventFactory.tenant_envelope(
            event_type="agent_job:created",
            tenant_key=tenant_key,
            data={
                "tenant_key": tenant_key,
                "job_id": job_id,
                "agent_display_name": agent_display_name,
                "spawned_by": spawned_by,
                "mission_preview": mission_preview,
                "created_at": created_ts,
                "project_id": project_id,
                "agent_name": agent_name,
                "status": status,
            },
            schema_version="1.0",
        )

        await self.broadcast_event_to_tenant(tenant_key=tenant_key, event=job_event)

        if project_id:
            agent_event = EventFactory.tenant_envelope(
                event_type="agent:created",
                tenant_key=tenant_key,
                data={
                    "tenant_key": tenant_key,
                    "project_id": project_id,
                    "job_id": job_id,
                    "agent_display_name": agent_display_name,
                    "agent_name": agent_name,
                    "status": status,
                },
                schema_version="1.0",
            )

            await self.broadcast_event_to_tenant(tenant_key=tenant_key, event=agent_event)

        logger.info(
            f"Broadcast agent_job:created - {job_id} (type: {agent_display_name}, spawned_by: {spawned_by}, project_id: {project_id})"
        )

    async def broadcast_job_status_update(
        self,
        job_id: str,
        agent_display_name: str,
        tenant_key: str,
        old_status: str,
        new_status: str,
        updated_at: Optional[datetime] = None,
        duration_seconds: Optional[float] = None,
    ):
        """Broadcast agent job status change event."""
        event_type = "agent:status_changed"

        message_data: dict[str, Any] = {
            "job_id": job_id,
            "agent_display_name": agent_display_name,
            "old_status": old_status,
            "status": new_status,
            "tenant_key": tenant_key,
            "updated_at": (updated_at or datetime.now(timezone.utc)).isoformat(),
        }

        if duration_seconds is not None:
            message_data["duration_seconds"] = duration_seconds

        event = EventFactory.tenant_envelope(
            event_type=event_type,
            tenant_key=tenant_key,
            data=message_data,
            schema_version="1.0",
        )

        await self.broadcast_event_to_tenant(tenant_key=tenant_key, event=event)

        logger.info(f"Broadcast {event_type} - {job_id} ({old_status} -> {new_status})")

    async def broadcast_job_message(
        self,
        job_id: str,
        message_id: str,
        from_agent: str,
        tenant_key: str,
        to_agent: Optional[str] = None,
        message_type: str = "status",
        content_preview: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        """Broadcast agent job message event."""
        data: dict[str, Any] = {
            "job_id": job_id,
            "message_id": message_id,
            "from_agent": from_agent,
            "to_agent": to_agent,
            "message_type": message_type,
            "message": content_preview,
            "tenant_key": tenant_key,
            "timestamp": (timestamp or datetime.now(timezone.utc)).isoformat(),
        }

        event = EventFactory.tenant_envelope(
            event_type="message:new",
            tenant_key=tenant_key,
            data=data,
            schema_version="1.0",
        )

        await self.broadcast_event_to_tenant(tenant_key=tenant_key, event=event)

        logger.debug(f"Broadcast message:new - {job_id} (from: {from_agent}, to: {to_agent})")

    async def broadcast_children_spawned(
        self,
        parent_job_id: str,
        tenant_key: str,
        children_spawned: int,
        child_job_ids: list[str],
        spawned_at: Optional[datetime] = None,
    ):
        """Broadcast child job spawn event."""
        data: dict[str, Any] = {
            "tenant_key": tenant_key,
            "parent_job_id": parent_job_id,
            "children_spawned": children_spawned,
            "child_job_ids": child_job_ids,
            "spawned_at": (spawned_at or datetime.now(timezone.utc)).isoformat(),
        }

        event = EventFactory.tenant_envelope(
            event_type="agent_job:children_spawned",
            tenant_key=tenant_key,
            data=data,
            schema_version="1.0",
        )

        await self.broadcast_event_to_tenant(tenant_key=tenant_key, event=event)

        logger.info(f"Broadcast agent_job:children_spawned - parent: {parent_job_id}, children: {children_spawned}")

    # Agent Communication Events (Handover 0040: Professional Agent Flow Visualization)

    async def broadcast_message_sent(
        self,
        message_id: str,
        job_id: str,
        tenant_key: str,
        from_agent: str,
        to_agent: Optional[str],
        message_type: str,
        content_preview: str,
        priority: int,
        timestamp: Optional[datetime] = None,
        project_id: Optional[str] = None,
        to_job_ids: Optional[list[str]] = None,
        sender_sent_count: Optional[int] = None,
        recipient_waiting_count: Optional[int] = None,
    ):
        """Broadcast message sent event for agent-orchestrator communication."""
        event = EventFactory.message_sent(
            message_id=message_id,
            project_id=project_id or job_id,
            tenant_key=tenant_key,
            from_job_id=job_id,
            to_job_ids=to_job_ids or [],
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            content_preview=(content_preview or "")[:200],
            priority=priority,
            message_timestamp=timestamp,
            sender_sent_count=sender_sent_count,
            recipient_waiting_count=recipient_waiting_count,
        )

        await self.broadcast_event_to_tenant(tenant_key=tenant_key, event=event)

        logger.debug(f"Broadcast message:sent - {message_id} (from: {from_agent}, to: {to_agent})")

    async def broadcast_message_received(
        self,
        message_id: str,
        job_id: str,
        tenant_key: str,
        from_agent: str,
        to_agent_ids: list[str],
        message_type: str,
        content_preview: str,
        priority: int,
        timestamp: Optional[datetime] = None,
        project_id: Optional[str] = None,
        waiting_count: Optional[int] = None,
    ):
        """Broadcast message received event to recipient agent(s)."""
        event = EventFactory.message_received(
            message_id=message_id,
            project_id=project_id or job_id,
            tenant_key=tenant_key,
            from_job_id=job_id,
            to_job_ids=to_agent_ids,
            from_agent=from_agent,
            to_agent_ids=to_agent_ids,
            message_type=message_type,
            content_preview=(content_preview or "")[:200],
            priority=priority,
            message_timestamp=timestamp,
            waiting_count=waiting_count,
        )

        await self.broadcast_event_to_tenant(tenant_key=tenant_key, event=event)

        logger.debug(f"Broadcast message:received - {message_id} to {len(to_agent_ids)} recipient(s)")

    async def broadcast_message_acknowledged(
        self,
        message_id: str,
        agent_id: str,
        tenant_key: str,
        project_id: str,
        message_ids: list[str],
        waiting_count: Optional[int] = None,
        read_count: Optional[int] = None,
    ):
        """Broadcast message acknowledged event when an agent reads messages."""
        event = EventFactory.message_acknowledged(
            message_id=message_id,
            project_id=project_id,
            tenant_key=tenant_key,
            from_job_id=agent_id,
            to_job_ids=[agent_id],
            agent_id=agent_id,
            message_ids=message_ids,
            waiting_count=waiting_count,
            read_count=read_count,
        )

        await self.broadcast_event_to_tenant(tenant_key=tenant_key, event=event)

        logger.debug(f"Broadcast message:acknowledged - {len(message_ids)} messages by agent {agent_id}")

    async def broadcast_agent_status_update(
        self,
        job_id: str,
        tenant_key: str,
        agent_id: str,
        status: str,
        current_task: Optional[str] = None,
        progress_percentage: Optional[int] = None,
        context_usage: Optional[int] = None,
        timestamp: Optional[datetime] = None,
    ):
        """Broadcast agent status update event."""
        message_data: dict[str, Any] = {
            "tenant_key": tenant_key,
            "job_id": job_id,
            "agent_id": agent_id,
            "status": status,
            "updated_at": (timestamp or datetime.now(timezone.utc)).isoformat(),
        }

        if current_task:
            message_data["current_task"] = current_task

        if progress_percentage is not None:
            message_data["progress_percentage"] = progress_percentage

        if context_usage is not None:
            message_data["context_usage"] = context_usage

        event = EventFactory.tenant_envelope(
            event_type="agent_communication:status_update",
            tenant_key=tenant_key,
            data=message_data,
            schema_version="1.0",
        )

        await self.broadcast_event_to_tenant(tenant_key=tenant_key, event=event)

        logger.debug(
            f"Broadcast status_update - job {job_id}: {status} (progress: {progress_percentage}%, task: {current_task})"
        )

    async def broadcast_artifact_created(
        self,
        job_id: str,
        tenant_key: str,
        agent_id: str,
        artifact_type: str,
        artifact_path: str,
        artifact_metadata: Optional[dict] = None,
        timestamp: Optional[datetime] = None,
    ):
        """Broadcast artifact creation event."""
        message_data: dict[str, Any] = {
            "tenant_key": tenant_key,
            "job_id": job_id,
            "agent_id": agent_id,
            "artifact_type": artifact_type,
            "artifact_path": artifact_path,
            "created_at": (timestamp or datetime.now(timezone.utc)).isoformat(),
        }

        if artifact_metadata:
            message_data["metadata"] = artifact_metadata

        event = EventFactory.tenant_envelope(
            event_type="agent_communication:artifact_created",
            tenant_key=tenant_key,
            data=message_data,
            schema_version="1.0",
        )

        await self.broadcast_event_to_tenant(tenant_key=tenant_key, event=event)

        logger.info(f"Broadcast artifact_created - {artifact_type}: {artifact_path} (job: {job_id})")

    # Agent Health Monitoring Events (Handover 0106)

    async def broadcast_health_alert(
        self,
        tenant_key: str,
        job_id: str,
        agent_display_name: str,
        health_status: Any,
    ):
        """Broadcast agent health alert."""
        message_data: dict[str, Any] = {
            "tenant_key": tenant_key,
            "job_id": job_id,
            "agent_display_name": agent_display_name,
            "health_state": health_status.health_state,
            "issue_description": health_status.issue_description,
            "minutes_since_update": health_status.minutes_since_update,
            "recommended_action": health_status.recommended_action,
        }

        event = EventFactory.tenant_envelope(
            event_type="agent:health_alert",
            tenant_key=tenant_key,
            data=message_data,
            schema_version="1.0",
        )

        await self.broadcast_event_to_tenant(tenant_key=tenant_key, event=event)

        logger.warning(
            "broadcast_health_alert",
            job_id=job_id,
            health_state=health_status.health_state,
            minutes_since_update=round(health_status.minutes_since_update, 1),
        )

    async def broadcast_agent_auto_failed(
        self,
        tenant_key: str,
        job_id: str,
        agent_display_name: str,
        reason: str,
    ):
        """Broadcast agent auto-fail event."""
        message_data: dict[str, Any] = {
            "tenant_key": tenant_key,
            "job_id": job_id,
            "agent_display_name": agent_display_name,
            "reason": reason,
            "auto_failed": True,
        }

        event = EventFactory.tenant_envelope(
            event_type="agent:auto_failed",
            tenant_key=tenant_key,
            data=message_data,
            schema_version="1.0",
        )

        await self.broadcast_event_to_tenant(tenant_key=tenant_key, event=event)

        logger.error(
            "broadcast_auto_failed",
            job_id=job_id,
            reason=reason,
        )

    async def broadcast_validation_failure(
        self,
        tenant_key: str,
        template_id: str,
        validation_errors: list,
    ):
        """Broadcast template validation failure event."""
        message_data: dict[str, Any] = {
            "tenant_key": tenant_key,
            "template_id": template_id,
            "errors": [e.to_dict() if hasattr(e, "to_dict") else str(e) for e in validation_errors],
            "fallback_used": True,
            "severity": "warning",
        }

        event = EventFactory.tenant_envelope(
            event_type="template:validation_failed",
            tenant_key=tenant_key,
            data=message_data,
            schema_version="1.0",
        )

        await self.broadcast_event_to_tenant(tenant_key=tenant_key, event=event)

        logger.warning(
            "broadcast_validation_failed",
            template_id=template_id,
            error_count=len(validation_errors),
        )
