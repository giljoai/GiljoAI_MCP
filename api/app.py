"""
FastAPI application for GiljoAI MCP
Provides REST API and WebSocket endpoints for orchestration system
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.giljo_mcp.auth import AuthManager
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Project
from src.giljo_mcp.tenant import TenantManager
from src.giljo_mcp.tools.tool_accessor import ToolAccessor

from .auth_utils import extract_credentials, get_websocket_close_code, validate_websocket_auth
from .endpoints import agents, configuration, context, messages, projects, statistics, tasks, templates
from .middleware import AuthMiddleware
from .websocket import WebSocketManager


if TYPE_CHECKING:
    from src.giljo_mcp.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class APIState:
    """Shared application state"""

    def __init__(self):
        self.db_manager: Optional[DatabaseManager] = None
        self.config: Optional[ConfigManager] = None
        self.auth: Optional[AuthManager] = None
        self.tenant_manager: Optional[TenantManager] = None
        self.tool_accessor: Optional[ToolAccessor] = None
        self.websocket_manager: Optional[WebSocketManager] = None
        self.connections: dict[str, WebSocket] = {}


state = APIState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting GiljoAI MCP API...")

    # Initialize configuration
    from src.giljo_mcp.config_manager import get_config

    state.config = get_config()  # Use the singleton getter

    # Initialize database
    db_url = getattr(state.config.database, "url", "sqlite:///giljo_mcp.db")
    state.db_manager = DatabaseManager(db_url, is_async=True)
    await state.db_manager.create_tables_async()

    # Initialize tenant manager
    state.tenant_manager = TenantManager()  # TenantManager uses static methods

    # Initialize tool accessor
    state.tool_accessor = ToolAccessor(state.db_manager, state.tenant_manager)

    # Initialize auth
    state.auth = AuthManager(state.config)

    # Initialize WebSocket manager
    state.websocket_manager = WebSocketManager()

    # Start heartbeat task
    asyncio.create_task(state.websocket_manager.start_heartbeat(interval=30))

    logger.info("API startup complete")

    yield

    # Shutdown
    logger.info("Shutting down GiljoAI MCP API...")

    # Close all WebSocket connections
    for ws in state.connections.values():
        await ws.close()

    # Close database
    if state.db_manager:
        await state.db_manager.close()

    logger.info("API shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""

    app = FastAPI(
        title="GiljoAI MCP Orchestrator API",
        description="""
        ## Multi-Agent Orchestration System REST API

        The GiljoAI MCP Orchestrator provides a comprehensive REST API for managing AI agent orchestration,
        enabling coordinated development teams that can tackle projects of unlimited complexity.

        ### Key Features:
        - **Project Management**: Create and manage development projects with AI agents
        - **Agent Orchestration**: Coordinate multiple specialized AI agents working together
        - **Message Queue**: Reliable inter-agent communication with acknowledgment
        - **Task Tracking**: Capture and manage technical debt and work items
        - **Configuration**: Flexible runtime and tenant-specific configuration
        - **Real-time Updates**: WebSocket support for live monitoring
        - **Statistics**: Comprehensive metrics and performance monitoring

        ### Authentication:
        API authentication can be enabled via configuration. Supports API key and OAuth methods.

        ### WebSocket:
        Connect to `/ws/{client_id}` for real-time updates on projects, agents, and messages.

        ### Rate Limiting:
        Rate limiting can be configured per tenant. Default: 60 requests/minute.
        """,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        openapi_tags=[
            {
                "name": "projects",
                "description": "Project management operations - create, update, and monitor AI development projects",
            },
            {"name": "agents", "description": "Agent control operations - spawn, manage, and decommission AI agents"},
            {
                "name": "messages",
                "description": "Inter-agent messaging - send, acknowledge, and complete messages between agents",
            },
            {"name": "tasks", "description": "Task management - track and manage development tasks and technical debt"},
            {"name": "context", "description": "Context operations - access vision documents and project context"},
            {"name": "configuration", "description": "Configuration management - system and tenant-specific settings"},
            {
                "name": "statistics",
                "description": "Statistics and monitoring - system metrics, performance, and health checks",
            },
        ],
        servers=[
            {"url": "http://localhost:8000", "description": "Local development server"},
            {"url": "http://0.0.0.0:8000", "description": "LAN accessible server"},
            {"url": "https://api.giljoai.com", "description": "Production server (future)"},
        ],
        contact={
            "name": "GiljoAI Support",
            "url": "https://github.com/giljoai/mcp-orchestrator",
            "email": "support@giljoai.com",
        },
        license_info={"name": "MIT License", "url": "https://opensource.org/licenses/MIT"},
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure based on deployment
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add authentication middleware
    app.add_middleware(AuthMiddleware, auth_manager=lambda: state.auth)

    # Include routers
    app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
    app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
    app.include_router(messages.router, prefix="/api/v1/messages", tags=["messages"])
    app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
    app.include_router(context.router, prefix="/api/v1/context", tags=["context"])
    app.include_router(configuration.router, prefix="/api/v1/config", tags=["configuration"])
    app.include_router(statistics.router, prefix="/api/v1/stats", tags=["statistics"])
    app.include_router(templates.router, prefix="/api/v1/templates", tags=["templates"])

    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "name": "GiljoAI MCP Orchestrator",
            "version": "1.0.0",
            "status": "operational",
            "endpoints": {"api": "/docs", "websocket": "/ws", "health": "/health"},
        }

    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        checks = {"api": "healthy", "database": "unknown", "websocket": "unknown"}

        # Check database
        if state.db_manager:
            try:
                async with state.db_manager.get_session_async() as session:
                    from sqlalchemy import text

                    await session.execute(text("SELECT 1"))
                    checks["database"] = "healthy"
            except Exception as e:
                checks["database"] = f"unhealthy: {e!s}"

        # Check WebSocket manager
        if state.websocket_manager:
            checks["websocket"] = "healthy"
            checks["active_connections"] = len(state.connections)

        status = "healthy" if all(v == "healthy" or isinstance(v, int) for v in checks.values()) else "degraded"

        return {"status": status, "checks": checks}

    @app.websocket("/ws/{client_id}")
    async def websocket_endpoint(
        websocket: WebSocket, client_id: str, api_key: Optional[str] = Query(None), token: Optional[str] = Query(None)
    ):
        """WebSocket endpoint for real-time updates with authentication"""

        # STEP 1: Extract credentials
        auth_credentials = await extract_credentials(websocket, api_key, token)

        # STEP 2: Validate BEFORE accepting connection
        auth_result = await validate_websocket_auth(auth_credentials, state.auth)

        if not auth_result.is_valid:
            # REJECT CONNECTION IMMEDIATELY
            logger.warning(f"WebSocket authentication failed for {client_id}: " f"{auth_result.error_message}")
            close_code = get_websocket_close_code("unauthorized")
            await websocket.close(code=close_code, reason=auth_result.error_message or "Unauthorized")
            return

        # STEP 3: Accept connection with auth context
        await websocket.accept()

        # STEP 4: Store auth context with connection
        await state.websocket_manager.connect(websocket, client_id, auth_context=auth_result.context)
        state.connections[client_id] = websocket

        # Log successful connection
        logger.info(
            f"WebSocket authenticated connection: {client_id} "
            f"(auth_type: {auth_result.context.get('auth_type', 'unknown')})"
        )

        try:
            while True:
                data = await websocket.receive_json()

                # Handle different message types
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

                elif data.get("type") == "subscribe":
                    # Subscribe to project/agent updates with authorization
                    entity_type = data.get("entity_type")
                    entity_id = data.get("entity_id")

                    try:
                        # Get tenant key for entity if needed
                        tenant_key = None
                        if entity_type == "project" and state.db_manager:
                            # Get project tenant for validation
                            async with state.db_manager.session() as session:
                                from sqlalchemy import select

                                stmt = select(Project).where(Project.id == entity_id)
                                result = await session.execute(stmt)
                                project = result.scalar_one_or_none()
                                if project:
                                    tenant_key = project.tenant_key

                        await state.websocket_manager.subscribe(client_id, entity_type, entity_id, tenant_key)
                        await websocket.send_json(
                            {"type": "subscribed", "entity_type": entity_type, "entity_id": entity_id}
                        )
                    except HTTPException as e:
                        # Send authorization error to client
                        await websocket.send_json(
                            {
                                "type": "error",
                                "error": "subscription_denied",
                                "message": str(e.detail),
                                "entity_type": entity_type,
                                "entity_id": entity_id,
                            }
                        )

                elif data.get("type") == "unsubscribe":
                    # Unsubscribe from updates
                    entity_type = data.get("entity_type")
                    entity_id = data.get("entity_id")
                    await state.websocket_manager.unsubscribe(client_id, entity_type, entity_id)
                    await websocket.send_json(
                        {"type": "unsubscribed", "entity_type": entity_type, "entity_id": entity_id}
                    )

        except WebSocketDisconnect:
            state.websocket_manager.disconnect(client_id)
            del state.connections[client_id]
            logger.info(f"WebSocket disconnected: {client_id}")
        except Exception as e:
            logger.exception(f"WebSocket error for {client_id}: {e}")
            state.websocket_manager.disconnect(client_id)
            if client_id in state.connections:
                del state.connections[client_id]

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        """Custom HTTP exception handler"""
        return JSONResponse(status_code=exc.status_code, content={"error": exc.detail, "status_code": exc.status_code})

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        """General exception handler"""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc) if state.config and state.config.get("debug", False) else None,
            },
        )

    # Store state reference in app
    app.state.api_state = state

    return app


# Export for uvicorn
app = create_app()
