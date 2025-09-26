"""
WebSocket manager for real-time updates
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException, WebSocket

from api.auth_utils import check_subscription_permission


logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections and subscriptions with authentication"""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.auth_contexts: dict[str, dict[str, Any]] = {}  # NEW: Store auth context
        self.subscriptions: dict[str, set[str]] = {}  # client_id -> set of subscriptions
        self.entity_subscribers: dict[str, set[str]] = {}  # entity_key -> set of client_ids

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
            logger.warning(f"Unauthorized subscription attempt by {client_id} " f"for {entity_type}:{entity_id}")
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
            except Exception:
                logger.exception("Error sending message to {client_id}")
                self.disconnect(client_id)

    async def send_json(self, data: dict, client_id: str):
        """Send JSON data to specific client"""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_json(data)
            except Exception:
                logger.exception("Error sending JSON to {client_id}")
                self.disconnect(client_id)

    async def broadcast(self, message: str):
        """Broadcast message to all connected clients"""
        disconnected = []
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message)
            except Exception:
                logger.exception("Error broadcasting to {client_id}")
                disconnected.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)

    async def broadcast_json(self, data: dict):
        """Broadcast JSON data to all connected clients"""
        message = json.dumps(data)
        await self.broadcast(message)

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
                    except Exception:
                        logger.exception("Error notifying {client_id}")
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

    async def broadcast_agent_spawn(
        self,
        agent_id: str,
        agent_name: str,
        parent_agent_id: Optional[str],
        project_id: str,
        tenant_key: str,
        role: str,
        mission: Optional[str] = None,
        initial_status: str = "active",
        meta_data: Optional[dict] = None,
    ):
        """
        Broadcast when a new agent is created/spawned.
        Includes parent agent ID for hierarchy visualization.
        """
        message = {
            "type": "agent:spawn",
            "data": {
                "agent_id": agent_id,
                "agent_name": agent_name,
                "parent_agent_id": parent_agent_id,
                "project_id": project_id,
                "tenant_key": tenant_key,
                "role": role,
                "mission": mission,
                "initial_status": initial_status,
                "meta_data": meta_data or {},
                "spawn_time": datetime.now(timezone.utc).isoformat(),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Only notify connections with matching tenant_key for multi-tenant isolation
        for client_id, websocket in self.active_connections.items():
            auth_context = self.auth_contexts.get(client_id, {})
            if auth_context.get("tenant_key") == tenant_key:
                try:
                    await websocket.send_json(message)
                except Exception:
                    logger.exception("Error broadcasting agent:spawn to websocket")

        # Also notify project and parent agent subscribers
        await self.notify_entity_update("project", project_id, message)
        if parent_agent_id:
            await self.notify_entity_update("agent", f"{project_id}:{parent_agent_id}", message)

        logger.info(f"Broadcast agent:spawn - {agent_name} (role: {role}, parent: {parent_agent_id})")

    async def broadcast_agent_complete(
        self,
        agent_id: str,
        agent_name: str,
        project_id: str,
        tenant_key: str,
        duration_seconds: float,
        final_status: str,
        context_usage: int,
        completion_reason: Optional[str] = None,
        meta_data: Optional[dict] = None,
    ):
        """
        Broadcast when an agent completes its work.
        Includes duration, final status, and context usage metrics.
        """
        message = {
            "type": "agent:complete",
            "data": {
                "agent_id": agent_id,
                "agent_name": agent_name,
                "project_id": project_id,
                "tenant_key": tenant_key,
                "duration_seconds": duration_seconds,
                "final_status": final_status,
                "context_usage": context_usage,
                "completion_reason": completion_reason,
                "meta_data": meta_data or {},
                "complete_time": datetime.now(timezone.utc).isoformat(),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Multi-tenant isolation
        for client_id, websocket in self.active_connections.items():
            auth_context = self.auth_contexts.get(client_id, {})
            if auth_context.get("tenant_key") == tenant_key:
                try:
                    await websocket.send_json(message)
                except Exception:
                    logger.exception("Error broadcasting agent:complete to websocket")

        # Notify project subscribers
        await self.notify_entity_update("project", project_id, message)
        await self.notify_entity_update("agent", f"{project_id}:{agent_name}", message)

        logger.info(
            f"Broadcast agent:complete - {agent_name} (duration: {duration_seconds}s, context: {context_usage})"
        )

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
    ):
        """
        Broadcast real-time status updates during agent execution.
        Includes context usage changes and current task information.
        """
        message = {
            "type": "agent:update",
            "data": {
                "agent_id": agent_id,
                "agent_name": agent_name,
                "project_id": project_id,
                "tenant_key": tenant_key,
                "status": status,
                "context_usage": context_usage,
                "context_delta": context_delta,  # Change since last update
                "current_task": current_task,
                "progress_percentage": progress_percentage,
                "meta_data": meta_data or {},
                "update_time": datetime.now(timezone.utc).isoformat(),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Multi-tenant isolation
        for client_id, websocket in self.active_connections.items():
            auth_context = self.auth_contexts.get(client_id, {})
            if auth_context.get("tenant_key") == tenant_key:
                try:
                    await websocket.send_json(message)
                except Exception:
                    logger.exception("Error broadcasting agent:update to websocket")

        # Notify entity subscribers
        await self.notify_entity_update("project", project_id, message)
        await self.notify_entity_update("agent", f"{project_id}:{agent_name}", message)

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
        """
        Broadcast template CRUD operations.
        Includes change metadata and user information.
        """
        message = {
            "type": "template:update",
            "data": {
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
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Multi-tenant isolation - only broadcast to same tenant
        for client_id, websocket in self.active_connections.items():
            auth_context = self.auth_contexts.get(client_id, {})
            if auth_context.get("tenant_key") == tenant_key:
                try:
                    await websocket.send_json(message)
                except Exception:
                    logger.exception("Error broadcasting template:update to websocket")

        # Notify product subscribers
        await self.notify_entity_update("product", product_id, message)

        logger.info(f"Broadcast template:update - {template_name} ({operation}) by user {user_id}")
