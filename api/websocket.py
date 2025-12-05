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
            logger.warning(f"Unauthorized subscription attempt by {client_id} for {entity_type}:{entity_id}")
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

    async def broadcast_to_tenant(
        self,
        tenant_key: str,
        event_type: str,
        data: dict[str, Any],
        schema_version: str = "1.0",
        exclude_client: Optional[str] = None,
    ) -> int:
        """
        Broadcast event to all connected clients in a specific tenant.

        Ensures multi-tenant isolation by only sending to clients authenticated
        with the specified tenant_key.

        Args:
            tenant_key: Tenant identifier (required, cannot be empty)
            event_type: Event type (e.g., "project:mission_updated")
            data: Event payload dictionary
            schema_version: Event schema version (default: "1.0")
            exclude_client: Optional client ID to exclude from broadcast

        Returns:
            Number of clients that successfully received the message

        Raises:
            ValueError: If tenant_key is None or empty

        Example:
            >>> sent_count = await ws_manager.broadcast_to_tenant(
            ...     tenant_key="tenant_123",
            ...     event_type="project:mission_updated",
            ...     data={"project_id": "...", "mission": "..."}
            ... )
            >>> print(f"Broadcasted to {sent_count} clients")

        Note:
            Failed sends to individual clients are logged but don't stop
            the broadcast to other clients (partial success allowed).

        Handover 0086A: Production-Grade Stage Project
        Added: 2025-11-02
        """
        # Validate required parameters
        if not tenant_key:
            raise ValueError("tenant_key cannot be empty")

        if not event_type:
            raise ValueError("event_type cannot be empty")

        # Build standardized message structure
        message = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "schema_version": schema_version,
            "data": data,
        }

        # Track successful sends and failures
        sent_count = 0
        failed_count = 0
        disconnected_clients = []

        # Iterate through all active connections
        logger.info(f"[BROADCAST DEBUG] Total active connections: {len(self.active_connections)}, Target tenant: {tenant_key}")
        for client_id, connection in self.active_connections.items():
            websocket = connection
            if hasattr(connection, "websocket"):
                websocket = connection.websocket

            # Skip excluded client if specified
            if exclude_client and client_id == exclude_client:
                continue

            # Check tenant isolation - CRITICAL for multi-tenant security
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

            logger.info(f"[BROADCAST DEBUG] Client {client_id[:8]}: tenant={client_tenant}, target={tenant_key}, match={client_tenant == tenant_key}")

            # Skip if client is not in the target tenant
            if client_tenant != tenant_key:
                logger.info(f"[BROADCAST DEBUG] Skipping client {client_id[:8]} - tenant mismatch")
                continue

            # Try to send to this client
            try:
                await websocket.send_json(message)
                sent_count += 1

            except Exception as e:
                # Log but don't fail the entire broadcast
                failed_count += 1
                logger.warning(
                    f"Failed to send WebSocket message to client {client_id}: {e}",
                    extra={"tenant_key": tenant_key, "event_type": event_type, "client_id": client_id, "error": str(e)},
                )
                # Mark for disconnection
                disconnected_clients.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)

        # Log broadcast summary
        logger.info(
            f"WebSocket broadcast to tenant completed: {sent_count} sent, {failed_count} failed",
            extra={
                "tenant_key": tenant_key,
                "event_type": event_type,
                "sent_count": sent_count,
                "failed_count": failed_count,
                "total_clients": len(self.active_connections),
                "exclude_client": exclude_client,
            },
        )

        return sent_count

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
        failure_reason: Optional[str] = None,  # Handover 0113
        decommissioned_at: Optional[str] = None,  # Handover 0113
    ):
        """
        Broadcast real-time status updates during agent execution.
        Includes context usage changes and current task information.
        
        Handover 0113: Added failure_reason and decommissioned_at for 7-state system.
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

        # Handover 0113: Include failure_reason for failed status
        if status == "failed" and failure_reason:
            message["data"]["failure_reason"] = failure_reason

        # Handover 0113: Include decommissioned_at for decommissioned status
        if status == "decommissioned" and decommissioned_at:
            message["data"]["decommissioned_at"] = decommissioned_at

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

    # Agent Job Event Broadcasts (Handover 0019)

    async def broadcast_job_created(
        self,
        job_id: str,
        agent_type: str,
        tenant_key: str,
        spawned_by: Optional[str] = None,
        mission_preview: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ):
        """
        Broadcast agent job creation event.
        Event type: 'agent_job:created'

        Args:
            job_id: Unique job identifier
            agent_type: Type of agent (orchestrator, analyzer, etc.)
            tenant_key: Tenant key for multi-tenant isolation
            spawned_by: Optional parent agent ID that spawned this job
            mission_preview: First 100 characters of mission
            created_at: Job creation timestamp
        """
        message = {
            "type": "agent_job:created",
            "data": {
                "job_id": job_id,
                "agent_type": agent_type,
                "spawned_by": spawned_by,
                "mission_preview": mission_preview,
                "created_at": (created_at or datetime.now(timezone.utc)).isoformat(),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Multi-tenant isolation - only broadcast to same tenant
        disconnected = []
        for client_id, websocket in self.active_connections.items():
            auth_context = self.auth_contexts.get(client_id, {})
            if auth_context.get("tenant_key") == tenant_key:
                try:
                    await websocket.send_json(message)
                except Exception:
                    logger.exception(f"Error broadcasting agent_job:created to {client_id}")
                    disconnected.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)

        logger.info(f"Broadcast agent_job:created - {job_id} (type: {agent_type}, spawned_by: {spawned_by})")

    async def broadcast_job_status_update(
        self,
        job_id: str,
        agent_type: str,
        tenant_key: str,
        old_status: str,
        new_status: str,
        updated_at: Optional[datetime] = None,
        duration_seconds: Optional[float] = None,
    ):
        """
        Broadcast agent job status change event.
        Event type: 'agent:status_changed' (frontend-compatible naming)

        Args:
            job_id: Unique job identifier
            agent_type: Type of agent
            tenant_key: Tenant key for multi-tenant isolation
            old_status: Previous status
            new_status: New status (pending, active, completed, failed)
            updated_at: Status update timestamp
            duration_seconds: Job duration (for completed/failed status)
        """
        # Use unified event type for all status changes (frontend expects this)
        event_type = "agent:status_changed"

        message_data = {
            "job_id": job_id,
            "agent_type": agent_type,
            "old_status": old_status,
            "status": new_status,  # Frontend expects 'status', not 'new_status'
            "tenant_key": tenant_key,  # Add tenant_key to payload for frontend validation
            "updated_at": (updated_at or datetime.now(timezone.utc)).isoformat(),
        }

        # Add duration for completed/failed jobs
        if duration_seconds is not None:
            message_data["duration_seconds"] = duration_seconds

        message = {
            "type": event_type,
            "data": message_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Multi-tenant isolation - only broadcast to same tenant
        disconnected = []
        for client_id, websocket in self.active_connections.items():
            auth_context = self.auth_contexts.get(client_id, {})
            if auth_context.get("tenant_key") == tenant_key:
                try:
                    await websocket.send_json(message)
                except Exception:
                    logger.exception(f"Error broadcasting {event_type} to {client_id}")
                    disconnected.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)

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
        """
        Broadcast agent job message event.
        Event type: 'message:new' (frontend-compatible naming)

        Args:
            job_id: Unique job identifier
            message_id: Message identifier
            from_agent: Agent that sent the message
            tenant_key: Tenant key for multi-tenant isolation
            to_agent: Optional target agent
            message_type: Type of message (status, error, result, etc.)
            content_preview: First 100 characters of message content
            timestamp: Message timestamp
        """
        message = {
            "type": "message:new",  # Frontend expects 'message:new', not 'agent_job:message'
            "data": {
                "job_id": job_id,
                "message_id": message_id,
                "from_agent": from_agent,
                "to_agent": to_agent,
                "message_type": message_type,
                "message": content_preview,  # Frontend expects 'message', not 'content_preview'
                "tenant_key": tenant_key,  # Add tenant_key to payload for frontend validation
                "timestamp": (timestamp or datetime.now(timezone.utc)).isoformat(),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Multi-tenant isolation - only broadcast to same tenant
        disconnected = []
        for client_id, websocket in self.active_connections.items():
            auth_context = self.auth_contexts.get(client_id, {})
            if auth_context.get("tenant_key") == tenant_key:
                try:
                    await websocket.send_json(message)
                except Exception:
                    logger.exception(f"Error broadcasting agent_job:message to {client_id}")
                    disconnected.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)

        logger.debug(f"Broadcast message:new - {job_id} (from: {from_agent}, to: {to_agent})")

    async def broadcast_children_spawned(
        self,
        parent_job_id: str,
        tenant_key: str,
        children_spawned: int,
        child_job_ids: list[str],
        spawned_at: Optional[datetime] = None,
    ):
        """
        Broadcast child job spawn event.
        Event type: 'agent_job:children_spawned'

        Args:
            parent_job_id: Parent job identifier
            tenant_key: Tenant key for multi-tenant isolation
            children_spawned: Number of children spawned
            child_job_ids: List of child job IDs
            spawned_at: Spawn timestamp
        """
        message = {
            "type": "agent_job:children_spawned",
            "data": {
                "parent_job_id": parent_job_id,
                "children_spawned": children_spawned,
                "child_job_ids": child_job_ids,
                "spawned_at": (spawned_at or datetime.now(timezone.utc)).isoformat(),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Multi-tenant isolation - only broadcast to same tenant
        disconnected = []
        for client_id, websocket in self.active_connections.items():
            auth_context = self.auth_contexts.get(client_id, {})
            if auth_context.get("tenant_key") == tenant_key:
                try:
                    await websocket.send_json(message)
                except Exception:
                    logger.exception(f"Error broadcasting agent_job:children_spawned to {client_id}")
                    disconnected.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)

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
    ):
        """
        Broadcast message sent event for agent-orchestrator communication.
        Event type: 'message:sent' (frontend-compatible naming)

        Args:
            message_id: Unique message identifier
            job_id: Job ID associated with the message
            tenant_key: Tenant key for multi-tenant isolation
            from_agent: Agent that sent the message
            to_agent: Target agent (None for broadcast)
            message_type: Type of message (task, info, error, etc.)
            content_preview: First 200 characters of message content
            priority: Message priority (0=low, 1=normal, 2=high)
            timestamp: Message timestamp
        """
        message = {
            "type": "message:sent",  # Frontend expects 'message:sent', not 'agent_communication:message_sent'
            "data": {
                "message_id": message_id,
                "job_id": job_id,
                "project_id": project_id or job_id,
                "from_agent": from_agent,
                "to_agent": to_agent,
                "message_type": message_type,
                # Provide multiple aliases for compatibility (content, content_preview, message)
                "message": content_preview[:200] if content_preview else "",
                "content": content_preview[:200] if content_preview else "",
                "content_preview": content_preview[:200] if content_preview else "",
                "tenant_key": tenant_key,  # Add tenant_key to payload for frontend validation
                "priority": priority,
                "timestamp": (timestamp or datetime.now(timezone.utc)).isoformat(),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Multi-tenant isolation
        disconnected = []
        for client_id, websocket in self.active_connections.items():
            auth_context = self.auth_contexts.get(client_id, {})
            if auth_context.get("tenant_key") == tenant_key:
                try:
                    await websocket.send_json(message)
                except Exception:
                    logger.exception(f"Error broadcasting message_sent to {client_id}")
                    disconnected.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)

        logger.debug(f"Broadcast message_sent - {message_id} (from: {from_agent}, to: {to_agent})")

    async def broadcast_message_received(
        self,
        message_id: str,
        job_id: str,
        tenant_key: str,
        from_agent: str,
        to_agent_ids: list[str],  # List of recipient agent IDs (job_ids)
        message_type: str,
        content_preview: str,
        priority: int,
        timestamp: Optional[datetime] = None,
        project_id: Optional[str] = None,
    ):
        """
        Broadcast message received event to RECIPIENT agent(s).
        Event type: 'message:received' (frontend-compatible naming)
        
        This event increments "Messages Waiting" counter on recipient agent cards.
        For broadcasts, to_agent_ids contains ALL agent job_ids.
        For direct messages, to_agent_ids contains a single job_id.
        
        Args:
            message_id: Unique message identifier
            job_id: Job ID of the SENDER (orchestrator typically)
            tenant_key: Tenant key for multi-tenant isolation
            from_agent: Agent that sent the message
            to_agent_ids: List of recipient agent job IDs
            message_type: Type of message (task, info, error, etc.)
            content_preview: First 200 characters of message content
            priority: Message priority (0=low, 1=normal, 2=high)
            timestamp: Message timestamp
            project_id: Project ID
        """
        message = {
            "type": "message:received",  # New event type for recipient agents
            "data": {
                "message_id": message_id,
                "job_id": job_id,  # Sender's job_id
                "project_id": project_id or job_id,
                "from_agent": from_agent,
                "to_agent_ids": to_agent_ids,  # List of recipients
                "message_type": message_type,
                # Provide multiple aliases for compatibility
                "message": content_preview[:200] if content_preview else "",
                "content": content_preview[:200] if content_preview else "",
                "content_preview": content_preview[:200] if content_preview else "",
                "tenant_key": tenant_key,
                "priority": priority,
                "timestamp": (timestamp or datetime.now(timezone.utc)).isoformat(),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        # Multi-tenant isolation
        disconnected = []
        for client_id, websocket in self.active_connections.items():
            auth_context = self.auth_contexts.get(client_id, {})
            if auth_context.get("tenant_key") == tenant_key:
                try:
                    await websocket.send_json(message)
                except Exception:
                    logger.exception(f"Error broadcasting message_received to {client_id}")
                    disconnected.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)
        
        logger.debug(f"Broadcast message_received - {message_id} to {len(to_agent_ids)} recipient(s)")

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
        """
        Broadcast agent status update event.
        Event type: 'agent_communication:status_update'

        Args:
            job_id: Agent job ID
            tenant_key: Tenant key for multi-tenant isolation
            agent_id: Agent reporting status
            status: Current status (pending, active, completed, failed)
            current_task: Description of current task
            progress_percentage: Progress from 0-100
            context_usage: Current context token usage
            timestamp: Status update timestamp
        """
        message_data = {
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

        message = {
            "type": "agent_communication:status_update",
            "data": message_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Multi-tenant isolation
        disconnected = []
        for client_id, websocket in self.active_connections.items():
            auth_context = self.auth_contexts.get(client_id, {})
            if auth_context.get("tenant_key") == tenant_key:
                try:
                    await websocket.send_json(message)
                except Exception:
                    logger.exception(f"Error broadcasting status_update to {client_id}")
                    disconnected.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)

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
        """
        Broadcast artifact creation event.
        Event type: 'agent_communication:artifact_created'

        Args:
            job_id: Agent job ID that created the artifact
            tenant_key: Tenant key for multi-tenant isolation
            agent_id: Agent that created the artifact
            artifact_type: Type of artifact (file, test, documentation, etc.)
            artifact_path: Path to the artifact
            artifact_metadata: Optional metadata (lines, size, language, etc.)
            timestamp: Creation timestamp
        """
        message_data = {
            "job_id": job_id,
            "agent_id": agent_id,
            "artifact_type": artifact_type,
            "artifact_path": artifact_path,
            "created_at": (timestamp or datetime.now(timezone.utc)).isoformat(),
        }

        if artifact_metadata:
            message_data["metadata"] = artifact_metadata

        message = {
            "type": "agent_communication:artifact_created",
            "data": message_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Multi-tenant isolation
        disconnected = []
        for client_id, websocket in self.active_connections.items():
            auth_context = self.auth_contexts.get(client_id, {})
            if auth_context.get("tenant_key") == tenant_key:
                try:
                    await websocket.send_json(message)
                except Exception:
                    logger.exception(f"Error broadcasting artifact_created to {client_id}")
                    disconnected.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)

        logger.info(f"Broadcast artifact_created - {artifact_type}: {artifact_path} (job: {job_id})")

    # Agent Health Monitoring Events (Handover 0106)

    async def broadcast_health_alert(
        self,
        tenant_key: str,
        job_id: str,
        agent_type: str,
        health_status: Any,
    ):
        """
        Broadcast agent health alert.

        Event type: 'agent:health_alert'

        Args:
            tenant_key: Tenant key for isolation
            job_id: Job ID experiencing health issues
            agent_type: Type of agent
            health_status: AgentHealthStatus object with health details
        """
        message_data = {
            "job_id": job_id,
            "agent_type": agent_type,
            "health_state": health_status.health_state,
            "issue_description": health_status.issue_description,
            "minutes_since_update": health_status.minutes_since_update,
            "recommended_action": health_status.recommended_action,
        }

        message = {
            "type": "agent:health_alert",
            "data": message_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Multi-tenant isolation
        disconnected = []
        for client_id, websocket in self.active_connections.items():
            auth_context = self.auth_contexts.get(client_id, {})
            if auth_context.get("tenant_key") == tenant_key:
                try:
                    await websocket.send_json(message)
                except Exception:
                    logger.exception(f"Error broadcasting health_alert to {client_id}")
                    disconnected.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)

        logger.warning(
            f"Broadcast health_alert - job {job_id}: {health_status.health_state} "
            f"({health_status.minutes_since_update:.1f}m since update)"
        )

    async def broadcast_agent_auto_failed(
        self,
        tenant_key: str,
        job_id: str,
        agent_type: str,
        reason: str,
    ):
        """
        Broadcast agent auto-fail event.

        Event type: 'agent:auto_failed'

        Args:
            tenant_key: Tenant key for isolation
            job_id: Job ID that was auto-failed
            agent_type: Type of agent
            reason: Reason for auto-fail
        """
        message_data = {
            "job_id": job_id,
            "agent_type": agent_type,
            "reason": reason,
            "auto_failed": True,
        }

        message = {
            "type": "agent:auto_failed",
            "data": message_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Multi-tenant isolation
        disconnected = []
        for client_id, websocket in self.active_connections.items():
            auth_context = self.auth_contexts.get(client_id, {})
            if auth_context.get("tenant_key") == tenant_key:
                try:
                    await websocket.send_json(message)
                except Exception:
                    logger.exception(f"Error broadcasting auto_failed to {client_id}")
                    disconnected.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)

        logger.error(f"Broadcast auto_failed - job {job_id}: {reason}")

    async def broadcast_validation_failure(
        self,
        tenant_key: str,
        template_id: str,
        validation_errors: list
    ):
        """
        Broadcast template validation failure event.

        Event type: 'template:validation_failed'

        Used when a template fails validation and system falls back to default.
        Alerts users to template issues requiring attention.

        Args:
            tenant_key: Tenant key for isolation
            template_id: Template ID that failed validation
            validation_errors: List of ValidationError objects
        """
        message_data = {
            "template_id": template_id,
            "errors": [e.to_dict() if hasattr(e, 'to_dict') else str(e) for e in validation_errors],
            "fallback_used": True,
            "severity": "warning"
        }

        message = {
            "type": "template:validation_failed",
            "data": message_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Multi-tenant isolation
        disconnected = []
        for client_id, websocket in self.active_connections.items():
            auth_context = self.auth_contexts.get(client_id, {})
            if auth_context.get("tenant_key") == tenant_key:
                try:
                    await websocket.send_json(message)
                except Exception:
                    logger.exception(f"Error broadcasting validation_failure to {client_id}")
                    disconnected.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)

        logger.warning(
            f"Broadcast validation_failed - template {template_id}: "
            f"{len(validation_errors)} error(s)"
        )
