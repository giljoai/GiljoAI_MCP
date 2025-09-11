"""
WebSocket manager for real-time updates
"""

from typing import Dict, Set, List
from fastapi import WebSocket
import json
import asyncio
import logging

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Manages WebSocket connections and subscriptions"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.subscriptions: Dict[str, Set[str]] = {}  # client_id -> set of subscriptions
        self.entity_subscribers: Dict[str, Set[str]] = {}  # entity_key -> set of client_ids
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept and track new WebSocket connection"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.subscriptions[client_id] = set()
        logger.info(f"WebSocket connected: {client_id}")
    
    def disconnect(self, client_id: str):
        """Remove WebSocket connection and clean up subscriptions"""
        # Remove from active connections
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        
        # Clean up subscriptions
        if client_id in self.subscriptions:
            for entity_key in self.subscriptions[client_id]:
                if entity_key in self.entity_subscribers:
                    self.entity_subscribers[entity_key].discard(client_id)
                    if not self.entity_subscribers[entity_key]:
                        del self.entity_subscribers[entity_key]
            del self.subscriptions[client_id]
        
        logger.info(f"WebSocket disconnected: {client_id}")
    
    async def subscribe(self, client_id: str, entity_type: str, entity_id: str):
        """Subscribe client to entity updates"""
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