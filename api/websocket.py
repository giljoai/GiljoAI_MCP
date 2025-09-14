"""
WebSocket manager for real-time updates
"""

from typing import Dict, Set, List, Optional, Any
from fastapi import WebSocket, HTTPException
import json
import asyncio
import logging
from datetime import datetime
from api.auth_utils import check_subscription_permission

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Manages WebSocket connections and subscriptions with authentication"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.auth_contexts: Dict[str, Dict[str, Any]] = {}  # NEW: Store auth context
        self.subscriptions: Dict[str, Set[str]] = {}  # client_id -> set of subscriptions
        self.entity_subscribers: Dict[str, Set[str]] = {}  # entity_key -> set of client_ids
    
    async def connect(
        self, 
        websocket: WebSocket, 
        client_id: str,
        auth_context: Optional[Dict[str, Any]] = None
    ):
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
    
    async def subscribe(
        self, 
        client_id: str, 
        entity_type: str, 
        entity_id: str,
        tenant_key: Optional[str] = None
    ):
        """Subscribe client to entity updates with authorization check"""
        
        # Check authorization
        auth_context = self.auth_contexts.get(client_id, {})
        if not check_subscription_permission(
            auth_context, entity_type, entity_id, tenant_key
        ):
            logger.warning(
                f"Unauthorized subscription attempt by {client_id} "
                f"for {entity_type}:{entity_id}"
            )
            raise HTTPException(
                status_code=403,
                detail="Not authorized to subscribe to this entity"
            )
        
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
                logger.error(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)
    
    async def send_json(self, data: dict, client_id: str):
        """Send JSON data to specific client"""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_json(data)
            except Exception as e:
                logger.error(f"Error sending JSON to {client_id}: {e}")
                self.disconnect(client_id)
    
    async def broadcast(self, message: str):
        """Broadcast message to all connected clients"""
        disconnected = []
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
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
            message = {
                "type": "entity_update",
                "entity_type": entity_type,
                "entity_id": entity_id,
                "data": update_data
            }
            
            disconnected = []
            for client_id in self.entity_subscribers[entity_key]:
                if client_id in self.active_connections:
                    try:
                        await self.send_json(message, client_id)
                    except Exception as e:
                        logger.error(f"Error notifying {client_id}: {e}")
                        disconnected.append(client_id)
            
            # Clean up disconnected clients
            for client_id in disconnected:
                self.disconnect(client_id)
    
    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)
    
    def get_subscription_count(self, entity_type: str = None, entity_id: str = None) -> int:
        """Get number of subscriptions for an entity"""
        if entity_type and entity_id:
            entity_key = f"{entity_type}:{entity_id}"
            return len(self.entity_subscribers.get(entity_key, []))
        return sum(len(subs) for subs in self.subscriptions.values())
    
    def get_auth_context(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get auth context for a client"""
        return self.auth_contexts.get(client_id)
    
    def is_authenticated(self, client_id: str) -> bool:
        """Check if client is authenticated"""
        auth_context = self.auth_contexts.get(client_id, {})
        return auth_context.get('auth_type', 'none') != 'none'
    
    # Enhanced broadcast methods for real-time updates
    
    async def broadcast_agent_update(
        self, 
        agent_name: str, 
        project_id: str, 
        status: str,
        additional_data: Optional[Dict] = None
    ):
        """Broadcast agent status change to all subscribed clients"""
        message = {
            "type": "agent_update",
            "data": {
                "agent_name": agent_name,
                "project_id": project_id,
                "status": status,
                "health": additional_data.get("health") if additional_data else None,
                "active_jobs": additional_data.get("active_jobs") if additional_data else None,
                "context_used": additional_data.get("context_used") if additional_data else None
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Notify project subscribers
        await self.notify_entity_update("project", project_id, message)
        
        # Also notify agent-specific subscribers
        await self.notify_entity_update("agent", f"{project_id}:{agent_name}", message)
    
    async def broadcast_message_update(
        self,
        message_id: str,
        project_id: str,
        update_type: str,  # 'new', 'acknowledged', 'completed'
        message_data: Dict
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
                "status": message_data.get("status")
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Notify project subscribers
        await self.notify_entity_update("project", project_id, message)
        
        # Notify specific agent subscribers if applicable
        if message_data.get("to_agents"):
            for agent in message_data.get("to_agents", []):
                await self.notify_entity_update("agent", f"{project_id}:{agent}", message)
    
    async def broadcast_progress(
        self,
        operation_id: str,
        project_id: str,
        percentage: float,
        message: str,
        details: Optional[Dict] = None
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
                "is_complete": percentage >= 100
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Notify project subscribers
        await self.notify_entity_update("project", project_id, progress_message)
    
    async def broadcast_notification(
        self,
        notification_type: str,  # 'info', 'warning', 'error', 'success'
        title: str,
        message: str,
        project_id: Optional[str] = None,
        target_clients: Optional[List[str]] = None
    ):
        """Broadcast system notifications to clients"""
        notification = {
            "type": "notification",
            "data": {
                "notification_type": notification_type,
                "title": title,
                "message": message,
                "project_id": project_id
            },
            "timestamp": datetime.utcnow().isoformat()
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
        update_type: str,  # 'created', 'status_changed', 'closed'
        project_data: Dict
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
                "context_budget": project_data.get("context_budget")
            },
            "timestamp": datetime.utcnow().isoformat()
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
        heartbeat = {
            "type": "ping",
            "timestamp": datetime.utcnow().isoformat()
        }
        
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