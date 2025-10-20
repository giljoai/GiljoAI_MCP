"""
FastAPI application for GiljoAI MCP
Provides REST API and WebSocket endpoints for orchestration system
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Optional

# Set up logging early to catch import issues
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
)
logger = logging.getLogger(__name__)
logger.info("Loading FastAPI application...")

from dotenv import load_dotenv

try:
    from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
    from fastapi.exceptions import WebSocketException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from sqlalchemy import select, text

    logger.info("FastAPI and core dependencies loaded successfully")
except ImportError as e:
    logger.error(f"Failed to import FastAPI dependencies: {e}", exc_info=True)
    raise

# Load environment variables from .env file
# Ensure we load from project root (parent of api directory)
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)
logger.info(f"Environment variables loaded from .env file: {env_path}")

# Log JWT secret availability for debugging
jwt_secret = os.getenv("JWT_SECRET") or os.getenv("GILJO_MCP_SECRET_KEY") or os.getenv("SECRET_KEY")
if jwt_secret:
    logger.info("JWT secret key found in environment")
else:
    logger.error("JWT secret key NOT found in environment - authentication will fail")

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
logger.debug(f"Added to Python path: {Path(__file__).parent.parent / 'src'}")

try:
    from giljo_mcp.auth import AuthManager
    from giljo_mcp.config_manager import get_config
    from giljo_mcp.database import DatabaseManager
    from giljo_mcp.models import Project
    from giljo_mcp.tenant import TenantManager
    from giljo_mcp.tools.tool_accessor import ToolAccessor

    logger.info("GiljoAI MCP core modules loaded successfully")
except ImportError as e:
    logger.error(f"Failed to import GiljoAI MCP modules: {e}", exc_info=True)
    logger.error("Make sure the src/giljo_mcp package is properly installed")
    raise

try:
    from .auth_utils import authenticate_websocket
    from .endpoints import (
        agent_jobs,
        agent_management,
        agents,
        ai_tools,
        auth,
        configuration,
        context,
        database_setup,
        mcp_http,
        mcp_installer,
        messages,
        setup_security,
        mcp_tools,
        network,
        orchestration,
        products,
        projects,
        serena,
        statistics,
        tasks,
        templates,
        users,
        user_settings,
    )
    from .middleware import AuthMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware
    from .websocket import WebSocketManager

    logger.info("API endpoint modules loaded successfully")
except ImportError as e:
    logger.error(f"Failed to import API modules: {e}", exc_info=True)
    raise

if TYPE_CHECKING:
    from src.giljo_mcp.config_manager import ConfigManager


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
async def lifespan(app: FastAPI):  # noqa: ARG001
    """Application lifespan manager"""
    # app parameter is required by FastAPI even if unused
    # Startup
    logger.info("=" * 70)
    logger.info("Starting GiljoAI MCP API...")
    logger.info("=" * 70)

    try:
        # Initialize configuration
        logger.info("Initializing configuration...")
        state.config = get_config()  # Use the singleton getter
        logger.info(f"Configuration loaded successfully")
        # v3.0: DeploymentMode removed - server always binds 0.0.0.0, firewall controls access
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}", exc_info=True)
        raise

    # v3.0: Setup mode removed - all access requires authentication

    # Initialize database (ALWAYS - install.py creates DB before API starts)
    # v3.0: No "setup mode without database" - database exists from installation
    if True:  # Database always initialized
        # Check for DATABASE_URL in environment first
        logger.info("Initializing database connection...")
        db_url = os.getenv("DATABASE_URL")

        if db_url:
            logger.info("Using DATABASE_URL from environment")
        elif state.config.database:
            # Construct database URL using configuration manager (handles env + migrations)
            try:
                logger.info("Constructing database URL from configuration manager")
                db_url = state.config.database.get_connection_string()
                logger.debug(
                    f"Database config: host={state.config.database.host}, port={state.config.database.port}, database={state.config.database.database_name}"
                )
            except Exception as e:
                logger.error(f"Failed to build database URL from config: {e}")
                raise

        if not db_url:
            logger.error("No database configuration found")
            raise ValueError("Database URL not configured. PostgreSQL is required.")

        logger.info(f"Connecting to database: {db_url.split('@')[-1] if '@' in db_url else db_url}")

        try:
            state.db_manager = DatabaseManager(db_url, is_async=True)
            logger.info("Database manager created successfully")

            logger.info("Creating database tables...")
            await state.db_manager.create_tables_async()
            logger.info("Database tables created/verified successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}", exc_info=True)
            raise

    # Initialize tenant manager
    try:
        logger.info("Initializing tenant manager...")
        state.tenant_manager = TenantManager()  # TenantManager uses static methods
        logger.info("Tenant manager initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize tenant manager: {e}", exc_info=True)
        raise

    # Initialize tool accessor
    try:
        logger.info("Initializing tool accessor...")
        state.tool_accessor = ToolAccessor(state.db_manager, state.tenant_manager)
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
        logger.info("No API key configured - localhost auto-login available, network clients require JWT")

    # Initialize WebSocket manager
    try:
        logger.info("Initializing WebSocket manager...")
        state.websocket_manager = WebSocketManager()
        logger.info("WebSocket manager initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize WebSocket manager: {e}", exc_info=True)
        raise

    # Start heartbeat task
    try:
        logger.info("Starting WebSocket heartbeat task...")
        heartbeat_task = asyncio.create_task(state.websocket_manager.start_heartbeat(interval=30))
        state.heartbeat_task = heartbeat_task  # Store reference to prevent garbage collection
        logger.info("WebSocket heartbeat started (interval: 30s)")
    except Exception as e:
        logger.error(f"Failed to start heartbeat task: {e}", exc_info=True)

    # v3.0: Removed localhost auto-login - unified authentication for all connections

    # Check setup state on startup (version tracking and validation)
    if state.db_manager:
        try:
            logger.info("Checking setup state...")
            from src.giljo_mcp.setup.state_manager import SetupStateManager

            # Get current version from config
            import yaml
            from pathlib import Path

            config_path = Path.cwd() / "config.yaml"
            if config_path.exists():
                with open(config_path) as f:
                    config_data = yaml.safe_load(f) or {}
                current_version = config_data.get("installation", {}).get("version", "2.0.0")
                db_version = "18"  # PostgreSQL 18

                # Initialize state manager with versions
                state_manager = SetupStateManager.get_instance(
                    tenant_key="default", current_version=current_version, required_db_version=db_version
                )

                # Check if migration needed
                if state_manager.requires_migration():
                    logger.warning("⚠️ Setup state version mismatch detected!")
                    logger.warning(f"Current version: {current_version}")
                    setup_state = state_manager.get_state()
                    logger.warning(f"Stored version: {setup_state.get('setup_version')}")
                    logger.warning("Run POST /api/setup/migrate to update state")
                else:
                    logger.info("Setup state version is current")

                # Validate current state
                valid, failures = state_manager.validate_state()
                if not valid:
                    logger.warning(f"⚠️ Setup validation failures detected:")
                    for failure in failures:
                        logger.warning(f"  - {failure}")
                    logger.warning("Review setup configuration or run migration")
                else:
                    logger.info("Setup state validation passed")

        except Exception as e:
            logger.error(f"Startup setup check failed: {e}", exc_info=True)
            # Don't crash the app on startup check failure
            logger.warning("Continuing startup despite setup check failure")

    # Expose db_manager directly on app.state for auth middleware compatibility
    # This must be done AFTER initialization, not in create_app()
    app.state.db_manager = state.db_manager

    logger.info("=" * 70)
    logger.info("API startup complete - All systems initialized")
    logger.info("=" * 70)

    yield

    # Shutdown
    logger.info("Shutting down GiljoAI MCP API...")

    # Close all WebSocket connections
    try:
        logger.info("Closing WebSocket connections...")
        for ws in state.connections.values():
            await ws.close()
        logger.info("WebSocket connections closed")
    except Exception as e:
        logger.error(f"Error closing WebSocket connections: {e}", exc_info=True)

    # Close database
    if state.db_manager:
        try:
            logger.info("Closing database connection...")
            await state.db_manager.close_async()  # Use close_async() for async engine
            logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database: {e}", exc_info=True)

    logger.info("API shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    from giljo_mcp.config_manager import get_config

    app = FastAPI(
        title="GiljoAI MCP Orchestrator API v3.0.0",
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
        version="3.0.0",
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
                "name": "Agent Management",
                "description": "Agent management operations - vision chunking, job coordination, and context search (Handover 0017)",
            },
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
            {"url": "http://localhost:7272", "description": "Local development server"},
            {"url": "http://0.0.0.0:7272", "description": "LAN accessible server"},
            {"url": "https://api.giljoai.com", "description": "Production server (future)"},
        ],
        contact={
            "name": "GiljoAI Support",
            "url": "https://github.com/giljoai/mcp-orchestrator",
            "email": "support@giljoai.com",
        },
        license_info={"name": "MIT License", "url": "https://opensource.org/licenses/MIT"},
    )

    # Configure CORS - use explicit origins from config.yaml security section
    import yaml

    cors_origins = []

    # Try to load from config.yaml security section
    try:
        config_path = Path(__file__).parent.parent / "config.yaml"
        if config_path.exists():
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
                security_config = config.get("security", {})
                cors_config = security_config.get("cors", {})
                cors_origins = cors_config.get("allowed_origins", [])

                if cors_origins:
                    logger.info(f"Loaded CORS origins from config.yaml security section: {cors_origins}")
    except Exception as e:
        logger.warning(f"Could not load CORS config from config.yaml: {e}")

    # Fallback to environment variable (for backwards compatibility)
    if not cors_origins:
        cors_origins_str = os.getenv("CORS_ORIGINS", "")
        if cors_origins_str:
            # Parse CORS origins (handle both comma-separated and JSON array formats)
            if cors_origins_str.startswith("["):
                # JSON array format from installer
                import json

                try:
                    cors_origins = json.loads(cors_origins_str)
                except json.JSONDecodeError:
                    pass
            else:
                # Comma-separated format
                cors_origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]

    # Safe default: explicit localhost origins only (no wildcards)
    if not cors_origins:
        cors_origins = [
            "http://127.0.0.1:7274",
            "http://localhost:7274",
        ]
        logger.info(f"Using default CORS origins (no wildcards): {cors_origins}")
    else:
        # Validate no wildcard patterns for security
        has_wildcards = any("*" in origin for origin in cors_origins)
        if has_wildcards:
            logger.warning(f"CORS origins contain wildcards - this reduces security. Consider using explicit origins.")

    # Dynamic network adapter IP detection for CORS updates
    try:
        from giljo_mcp.network_detector import AdapterIPDetector

        detector = AdapterIPDetector()
        ip_changed, current_ip, adapter_name = detector.detect_ip_change(config)

        if current_ip:
            # Add adapter IP to CORS origins (whether changed or not)
            frontend_port = config.get("services", {}).get("frontend", {}).get("port", 7274)
            adapter_origins = [
                f"http://{current_ip}:{frontend_port}",
                f"http://{current_ip}:5173",  # Vite dev server
            ]

            # Add if not already present
            for origin in adapter_origins:
                if origin not in cors_origins:
                    cors_origins.append(origin)
                    logger.info(f"Added CORS origin: {origin}")

            if ip_changed:
                logger.info(f"Network adapter IP changed: {adapter_name} -> {current_ip}")
            else:
                logger.info(f"Network adapter IP unchanged: {adapter_name} @ {current_ip}")
        else:
            # Adapter disconnected - log warning and fall back to localhost
            if adapter_name:
                logger.warning(f"Network adapter '{adapter_name}' disconnected - using localhost fallback")

    except ImportError:
        logger.debug("Network detector not available - skipping dynamic IP detection")
    except Exception as e:
        logger.warning(f"Network IP detection failed: {e} - continuing with static CORS config")

    logger.info(f"Configuring CORS with origins: {cors_origins}")

    # Add middleware in reverse order of execution
    # (last middleware added = first middleware executed in request chain)

    # Add authentication middleware (executes 5th - after CORS, security, rate limit, setup)
    app.add_middleware(AuthMiddleware, auth_manager=lambda: state.auth)

    # Add rate limiting middleware (executes 4th - protects endpoints, 60 requests/minute for LAN security)
    app.add_middleware(RateLimitMiddleware, requests_per_minute=60)

    # Add security headers middleware (executes 3rd - adds security headers to all responses)
    app.add_middleware(SecurityHeadersMiddleware)

    # v3.0: Setup mode middleware removed - unified authentication for all endpoints

    # Add CORS middleware (executes 1st - MUST be first to handle OPTIONS preflight requests)
    # This MUST execute before all other middleware to add CORS headers to OPTIONS responses
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(products.router, prefix="/api/v1/products", tags=["products"])
    app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
    app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
    app.include_router(agent_management.router, tags=["Agent Management"])
    app.include_router(messages.router, prefix="/api/v1/messages", tags=["messages"])
    app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
    app.include_router(agent_jobs.router, prefix="/api/agent-jobs", tags=["agent-jobs"])
    app.include_router(orchestration.router, prefix="/api/orchestrator", tags=["orchestration"])
    app.include_router(context.router, prefix="/api/v1/context", tags=["context"])
    app.include_router(configuration.router, prefix="/api/v1/config", tags=["configuration"])
    app.include_router(statistics.router, prefix="/api/v1/stats", tags=["statistics"])
    app.include_router(templates.router, prefix="/api/v1/templates", tags=["templates"])
    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(users.router, prefix="/api/users", tags=["users"])
    # v3: authenticated user-scoped settings
    app.include_router(user_settings.router, prefix="/api/v1/user", tags=["user-settings"])
    app.include_router(database_setup.router, prefix="/api/setup/database", tags=["database-setup"])
    app.include_router(setup_security.router, prefix="/api/setup", tags=["setup-security"])
    app.include_router(serena.router, prefix="/api/serena", tags=["serena"])
    app.include_router(network.router, prefix="/api/network", tags=["network"])

    # MCP Installer endpoints for downloadable script generation (Phase 2.1)
    app.include_router(mcp_installer.router, prefix="/api/mcp-installer", tags=["MCP Integration"])

    # MCP tool endpoints for stdio-to-HTTP bridge
    app.include_router(mcp_tools.router, prefix="/mcp/tools", tags=["mcp_tools"])

    # Pure MCP JSON-RPC 2.0 over HTTP endpoint (Handover 0032)
    app.include_router(mcp_http.router, tags=["mcp"])

    # AI Tools configuration generator endpoints
    app.include_router(ai_tools.router, prefix="/api/ai-tools", tags=["ai-tools"])

    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "name": "GiljoAI MCP Orchestrator",
            "version": "3.0.0",
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
                    await session.execute(text("SELECT 1"))
                    checks["database"] = "healthy"
            except (ConnectionError, TimeoutError, Exception) as e:
                # Catching Exception is needed here for any database errors
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

        # STEP 1: Authenticate using unified WebSocket authentication
        # Handle setup mode (db_manager can be None)
        try:
            # Get database session (None during setup mode)
            session = None
            session_cm = None  # Store context manager instance
            if state.db_manager:
                # CRITICAL: Store the context manager instance
                session_cm = state.db_manager.get_session_async()
                session = await session_cm.__aenter__()

            try:
                auth_result = await authenticate_websocket(websocket, db=session)

                # STEP 2: Accept connection with authentication result
                await websocket.accept()

                # STEP 3: Store connection with authentication context
                auth_context = {
                    'user': auth_result.get('user', {}),
                    'context': auth_result.get('context', 'normal')  # 'setup' or 'normal'
                }
                # Determine auth type from query parameters
                if token:
                    auth_context['auth_type'] = 'jwt'
                elif api_key:
                    auth_context['auth_type'] = 'api_key'
                else:
                    auth_context['auth_type'] = 'setup'

                await state.websocket_manager.connect(websocket, client_id, auth_context=auth_context)
                state.connections[client_id] = websocket

                # Log successful connection
                auth_type = auth_context.get('auth_type', 'setup')
                logger.info(f"WebSocket connected: {client_id} (context: {auth_result.get('context', 'normal')}, auth_type: {auth_type})")

            finally:
                # Clean up session if created - use SAME context manager instance
                if session_cm is not None:
                    await session_cm.__aexit__(None, None, None)

        except WebSocketException as e:
            # REJECT CONNECTION IMMEDIATELY
            logger.warning(f"WebSocket authentication failed for {client_id}: {e.reason}")
            await websocket.close(code=1008, reason=e.reason or "Unauthorized")
            return

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
        except Exception:
            logger.exception(f"WebSocket error for {client_id}")
            state.websocket_manager.disconnect(client_id)
            if client_id in state.connections:
                del state.connections[client_id]

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):  # noqa: ARG001
        """Custom HTTP exception handler"""
        logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
        return JSONResponse(status_code=exc.status_code, content={"error": exc.detail, "status_code": exc.status_code})

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):  # noqa: ARG001
        """General exception handler"""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        logger.error(f"Request path: {request.url.path if hasattr(request, 'url') else 'unknown'}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc),  # Always show details in verbose mode
                "type": type(exc).__name__,
            },
        )

    # Store state reference in app
    app.state.api_state = state

    # Note: db_manager is exposed on app.state in lifespan() AFTER initialization
    # Setting it here would be None since lifespan hasn't run yet

    return app


# Export for uvicorn
app = create_app()
