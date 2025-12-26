"""Core services initialization module

Handles initialization of TenantManager, WebSocketManager, ToolAccessor, and AuthManager.
Extracted from api/app.py lifespan function (lines ~215-293).
"""

import asyncio
import logging
import os

from api.app import APIState
from api.websocket import WebSocketManager
from src.giljo_mcp.auth import AuthManager
from src.giljo_mcp.tenant import TenantManager
from src.giljo_mcp.tools.tool_accessor import ToolAccessor


logger = logging.getLogger(__name__)


async def init_core_services(state: APIState) -> None:
    """Initialize core services: TenantManager, WebSocketManager, ToolAccessor, AuthManager

    Args:
        state: APIState instance to populate with service managers

    Raises:
        Exception: If any service initialization fails
    """
    # Initialize tenant manager
    try:
        logger.info("Initializing tenant manager...")
        state.tenant_manager = TenantManager()  # TenantManager uses static methods
        logger.info("Tenant manager initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize tenant manager: {e}", exc_info=True)
        raise

    # Initialize WebSocket manager BEFORE tool accessor (needed for MessageService)
    try:
        logger.info("Initializing WebSocket manager...")
        state.websocket_manager = WebSocketManager()
        logger.info("WebSocket manager initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize WebSocket manager: {e}", exc_info=True)
        raise

    # Initialize WebSocket broker (0379e)
    try:
        from api.broker import create_websocket_event_broker

        broker = create_websocket_event_broker(
            config=state.config,
            database_url=getattr(state.db_manager, "database_url", None),
        )
        await broker.start()
        state.websocket_broker = broker
        state.websocket_manager.attach_broker(broker)
        logger.info(f"WebSocket broker initialized: {broker.__class__.__name__}")
    except Exception as e:
        logger.error(f"Failed to initialize WebSocket broker: {e}", exc_info=True)
        # Degrade gracefully: continue with local-only broadcasts.

    # Initialize tool accessor (now websocket_manager is available)
    try:
        logger.info("Initializing tool accessor...")
        state.tool_accessor = ToolAccessor(
            state.db_manager, state.tenant_manager, websocket_manager=state.websocket_manager
        )
        logger.info("Tool accessor initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize tool accessor: {e}", exc_info=True)
        raise

    # Initialize auth with database session (for auto-login support)
    try:
        logger.info("Initializing authentication manager...")
        # Note: db parameter will be set later per-request for auto-login
        # The db_manager provides sessions, not a single session
        state.auth = AuthManager(state.config, db=None)
        logger.info("Auth manager initialized (mode-independent authentication)")
    except Exception as e:
        logger.error(f"Failed to initialize auth manager: {e}", exc_info=True)
        raise

    # Load API key from environment if available
    api_key = os.getenv("API_KEY") or os.getenv("GILJO_MCP_API_KEY")
    if api_key:
        # Add the configured API key to AuthManager (for network clients)
        state.auth.api_keys[api_key] = {
            "name": "Installer Generated",
            "created_at": "2024-01-01T00:00:00Z",
            "permissions": ["*"],
            "active": True,
        }
        logger.info(
            f"Loaded API key from environment (key ending in: ...{api_key[-4:] if len(api_key) > 4 else 'XXXX'})"
        )
    else:
        logger.info("No API key configured - all clients require JWT authentication (unified auth)")

    # Start heartbeat task (WebSocket manager already initialized earlier)
    try:
        logger.info("Starting WebSocket heartbeat task...")
        heartbeat_task = asyncio.create_task(state.websocket_manager.start_heartbeat(interval=30))
        state.heartbeat_task = heartbeat_task  # Store reference to prevent garbage collection
        logger.info("WebSocket heartbeat started (interval: 30s)")
    except Exception as e:
        logger.error(f"Failed to start heartbeat task: {e}", exc_info=True)
