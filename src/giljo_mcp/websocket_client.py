"""
WebSocket client for MCP tools to send real-time updates
"""

import logging
from typing import Optional, Dict, Any
import aiohttp
from datetime import datetime

logger = logging.getLogger(__name__)


class WebSocketEventClient:
    """Client for sending WebSocket events from MCP tools to the FastAPI server"""

    def __init__(self, ws_url: str = "ws://localhost:6000/ws/mcp_tool_client"):
        self.ws_url = ws_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._connected = False

    async def connect(self, api_key: Optional[str] = None):
        """Connect to the WebSocket server"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            # Add API key if provided
            url = self.ws_url
            if api_key:
                url = f"{url}?api_key={api_key}"

            self.ws = await self.session.ws_connect(url)
            self._connected = True
            logger.info(f"Connected to WebSocket server at {self.ws_url}")

        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            self._connected = False
            raise

    async def disconnect(self):
        """Disconnect from the WebSocket server"""
        try:
            if self.ws:
                await self.ws.close()
            if self.session:
                await self.session.close()
            self._connected = False
            logger.info("Disconnected from WebSocket server")
        except Exception as e:
            logger.error(f"Error disconnecting from WebSocket: {e}")

    async def send_event(self, event_type: str, data: Dict[str, Any]):
        """Send an event to the WebSocket server"""
        if not self._connected or not self.ws:
            logger.warning(
                "Not connected to WebSocket server, attempting to connect..."
            )
            await self.connect()

        try:
            message = {
                "type": event_type,
                "data": data,
                "timestamp": datetime.utcnow().isoformat(),
            }

            await self.ws.send_json(message)
            logger.debug(f"Sent WebSocket event: {event_type}")

        except Exception as e:
            logger.error(f"Failed to send WebSocket event: {e}")
            self._connected = False
            # Try to reconnect on next send

    async def broadcast_sub_agent_spawned(
        self,
        interaction_id: str,
        parent_agent_name: str,
        sub_agent_name: str,
        project_id: str,
        mission: str,
        start_time: str,
        meta_data: Optional[Dict] = None,
    ):
        """Broadcast when a parent agent spawns a sub-agent"""
        await self.send_event(
            "agent.sub_agent.spawned",
            {
                "interaction_id": interaction_id,
                "parent_agent_name": parent_agent_name,
                "sub_agent_name": sub_agent_name,
                "project_id": project_id,
                "mission": mission,
                "start_time": start_time,
                "meta_data": meta_data or {},
            },
        )

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
        meta_data: Optional[Dict] = None,
    ):
        """Broadcast when a sub-agent completes (success or error)"""
        event_type = (
            "agent.sub_agent.completed"
            if status == "completed"
            else "agent.sub_agent.error"
        )

        await self.send_event(
            event_type,
            {
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
        )

    async def __aenter__(self):
        """Context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.disconnect()


# Global instance for reuse across MCP tools
_global_ws_client: Optional[WebSocketEventClient] = None


async def get_websocket_client() -> WebSocketEventClient:
    """Get or create the global WebSocket client"""
    global _global_ws_client

    if _global_ws_client is None:
        _global_ws_client = WebSocketEventClient()
        # Don't connect immediately - let it connect on first use

    return _global_ws_client


async def broadcast_sub_agent_event(event_type: str, **kwargs):
    """Utility function to broadcast sub-agent events"""
    try:
        client = await get_websocket_client()

        if event_type == "spawned":
            await client.broadcast_sub_agent_spawned(**kwargs)
        elif event_type in ["completed", "error"]:
            await client.broadcast_sub_agent_completed(**kwargs)
        else:
            logger.warning(f"Unknown event type: {event_type}")

    except Exception as e:
        # Don't fail the MCP tool if WebSocket fails
        logger.error(f"Failed to broadcast WebSocket event: {e}")
