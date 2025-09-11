"""
FastAPI application for GiljoAI MCP
Provides REST API and WebSocket endpoints for orchestration system
"""

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any
import asyncio
import logging
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.giljo_mcp.database import DatabaseManager, get_db_manager
from src.giljo_mcp.models import Project, Agent, Message, Task
from src.giljo_mcp.config_manager import ConfigManager
from src.giljo_mcp.auth import AuthManager
from src.giljo_mcp.tenant import TenantManager
from src.giljo_mcp.tools.tool_accessor import ToolAccessor
from .endpoints import projects, agents, messages, tasks, context
from .websocket import WebSocketManager
from .middleware import AuthMiddleware

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
        self.connections: Dict[str, WebSocket] = {}

state = APIState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting GiljoAI MCP API...")
    
    # Initialize configuration
    state.config = ConfigManager()
    
    # Initialize database
    db_url = state.config.get('database.url', 'sqlite:///giljo_mcp.db')
    state.db_manager = DatabaseManager(db_url, is_async=True)
    await state.db_manager.init_db()
    
    # Initialize tenant manager
    state.tenant_manager = TenantManager(state.db_manager)
    
    # Initialize tool accessor
    state.tool_accessor = ToolAccessor(state.db_manager, state.tenant_manager)
    
    # Initialize auth
    state.auth = AuthManager(state.config)
    
    # Initialize WebSocket manager
    state.websocket_manager = WebSocketManager()
    
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
        description="Multi-agent orchestration system API",
        version="1.0.0",
        lifespan=lifespan
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
    
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "name": "GiljoAI MCP Orchestrator",
            "version": "1.0.0",
            "status": "operational",
            "endpoints": {
                "api": "/docs",
                "websocket": "/ws",
                "health": "/health"
            }
        }
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        checks = {
            "api": "healthy",
            "database": "unknown",
            "websocket": "unknown"
        }
        
        # Check database
        if state.db_manager:
            try:
                async with state.db_manager.session() as session:
                    result = await session.execute("SELECT 1")
                    checks["database"] = "healthy"
            except Exception as e:
                checks["database"] = f"unhealthy: {str(e)}"
        
        # Check WebSocket manager
        if state.websocket_manager:
            checks["websocket"] = "healthy"
            checks["active_connections"] = len(state.connections)
        
        status = "healthy" if all(v == "healthy" or isinstance(v, int) 
                                 for v in checks.values()) else "degraded"
        
        return {
            "status": status,
            "checks": checks
        }
    
    @app.websocket("/ws/{client_id}")
    async def websocket_endpoint(websocket: WebSocket, client_id: str):
        """WebSocket endpoint for real-time updates"""
        await state.websocket_manager.connect(websocket, client_id)
        state.connections[client_id] = websocket
        
        try:
            while True:
                data = await websocket.receive_json()
                
                # Handle different message types
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                
                elif data.get("type") == "subscribe":
                    # Subscribe to project/agent updates
                    entity_type = data.get("entity_type")
                    entity_id = data.get("entity_id")
                    await state.websocket_manager.subscribe(client_id, entity_type, entity_id)
                    await websocket.send_json({
                        "type": "subscribed",
                        "entity_type": entity_type,
                        "entity_id": entity_id
                    })
                
                elif data.get("type") == "unsubscribe":
                    # Unsubscribe from updates
                    entity_type = data.get("entity_type")
                    entity_id = data.get("entity_id")
                    await state.websocket_manager.unsubscribe(client_id, entity_type, entity_id)
                    await websocket.send_json({
                        "type": "unsubscribed",
                        "entity_type": entity_type,
                        "entity_id": entity_id
                    })
        
        except WebSocketDisconnect:
            state.websocket_manager.disconnect(client_id)
            del state.connections[client_id]
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        """Custom HTTP exception handler"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "status_code": exc.status_code
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        """General exception handler"""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc) if state.config and state.config.get('debug', False) else None
            }
        )
    
    # Store state reference in app
    app.state.api_state = state
    
    return app

# Export for uvicorn
app = create_app()