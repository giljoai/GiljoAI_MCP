"""
FastAPI application for GiljoAI MCP
Provides REST API and WebSocket endpoints for orchestration system
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager, suppress
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
    from src.giljo_mcp.auth import AuthManager
    from src.giljo_mcp.database import DatabaseManager
    from src.giljo_mcp.models import Project
    from src.giljo_mcp.system_prompts import SystemPromptService
    from src.giljo_mcp.tenant import TenantManager
    from src.giljo_mcp.tools.tool_accessor import ToolAccessor

    logger.info("GiljoAI MCP core modules loaded successfully")
except ImportError as e:
    logger.error(f"Failed to import GiljoAI MCP modules: {e}", exc_info=True)
    logger.exception("Make sure the src/giljo_mcp package is properly installed")
    raise

try:
    from .auth_utils import authenticate_websocket
    from .endpoints import (
        agent_jobs,
        agent_management,
        agent_templates,
        ai_tools,
        auth,
        auth_pin_recovery,
        claude_export,
        configuration,
        context,
        database_setup,
        downloads,
        git,
        mcp_http,
        mcp_installer,
        messages,
        network,
        products,
        projects,
        prompts,
        serena,
        settings,
        setup_security,
        slash_commands,
        statistics,
        system_prompts,
        tasks,
        templates,
        user_settings,
        users,
        vision_documents,
        websocket_bridge,
    )
    from .endpoints.organizations import crud as org_crud
    from .endpoints.organizations import members as org_members
    from .exception_handlers import register_exception_handlers
    from .middleware import (
        APIMetricsMiddleware,
        AuthMiddleware,
        InputValidationMiddleware,
        # CSRFProtectionMiddleware,  # Optional - requires frontend integration
        RateLimitMiddleware,
        SecurityHeadersMiddleware,
    )
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
        self.websocket_broker = None  # WebSocketEventBroker (0379e)
        self.event_bus = None  # EventBus instance (Handover 0111 Issue #1)
        self.connections: dict[str, WebSocket] = {}
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        self.metrics_sync_task: Optional[asyncio.Task] = None
        self.health_monitor = None
        self.health_monitor_task: Optional[asyncio.Task] = None
        self.silence_detector = None  # SilenceDetector (Handover 0491)
        self.api_call_count: dict[str, int] = {}
        self.mcp_call_count: dict[str, int] = {}
        self.system_prompt_service: Optional[SystemPromptService] = None


state = APIState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - orchestrates startup and shutdown"""
    from api.startup import (
        init_background_tasks,
        init_core_services,
        init_database,
        init_event_bus,
        init_health_monitor,
        init_silence_detector,
        init_validation,
        shutdown,
    )

    logger.info("=" * 70)
    logger.info("Starting GiljoAI MCP API...")
    logger.info("=" * 70)

    # Phase 1: Database and configuration
    await init_database(state)

    # Phase 2: Core services
    await init_core_services(state)

    # Phase 3: Event bus and WebSocket listener
    await init_event_bus(state)

    # Phase 4: Background tasks
    await init_background_tasks(state)

    # Phase 5: Health monitoring
    await init_health_monitor(state)

    # Phase 6: Silence detection (Handover 0491)
    await init_silence_detector(state)

    # Phase 7: Validation
    await init_validation(state)

    # Expose db_manager and websocket_manager directly on app.state
    # This must be done AFTER initialization, not in create_app()
    app.state.db_manager = state.db_manager
    app.state.websocket_manager = state.websocket_manager
    app.state.websocket_broker = state.websocket_broker

    logger.info("=" * 70)
    logger.info("API startup complete - All systems initialized")
    logger.info("=" * 70)

    yield

    # Shutdown
    await shutdown(state)

    logger.info("API shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""

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
    from src.giljo_mcp._config_io import read_config as _read_app_config

    cors_origins = []

    # Try to load from config.yaml security section
    try:
        config = _read_app_config()
        cors_origins = config.get("security", {}).get("cors", {}).get("allowed_origins", [])
        if cors_origins:
            logger.info(f"Loaded CORS origins from config.yaml security section: {cors_origins}")
    except (OSError, ValueError, KeyError) as e:
        logger.warning(f"Could not load CORS config from config.yaml: {e}")

    # Fallback to environment variable (for backwards compatibility)
    if not cors_origins:
        cors_origins_str = os.getenv("CORS_ORIGINS", "")
        if cors_origins_str:
            # Parse CORS origins (handle both comma-separated and JSON array formats)
            if cors_origins_str.startswith("["):
                # JSON array format from installer
                import json

                with suppress(json.JSONDecodeError):
                    cors_origins = json.loads(cors_origins_str)
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
            logger.warning("CORS origins contain wildcards - this reduces security. Consider using explicit origins.")

    # Dynamic network adapter IP detection for CORS updates
    network_mode = config.get("security", {}).get("network", {}).get("mode", "localhost")
    logger.info(f"Network mode: {network_mode}")

    if network_mode in ("auto", "static"):
        try:
            from src.giljo_mcp.network_detector import AdapterIPDetector

            detector = AdapterIPDetector()
            ip_changed, current_ip, adapter_name = detector.detect_ip_change(config)

            if current_ip:
                # Add adapter IP to CORS origins (whether changed or not)
                frontend_port = config.get("services", {}).get("frontend", {}).get("port", 7274)
                api_port = config.get("services", {}).get("api", {}).get("port", 7272)
                adapter_origins = [
                    f"http://{current_ip}:{frontend_port}",
                    f"http://{current_ip}:{api_port}",  # API port for direct access
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
            # Adapter disconnected - log warning and fall back to localhost
            elif adapter_name:
                logger.warning(f"Network adapter '{adapter_name}' disconnected - using localhost fallback")

        except ImportError:
            logger.debug("Network detector not available - skipping dynamic IP detection")
        except (RuntimeError, ValueError, OSError, KeyError) as e:
            logger.warning(f"Network IP detection failed: {e} - continuing with static CORS config")

    logger.info(f"Configuring CORS with origins: {cors_origins}")

    # Add middleware in reverse order of execution
    # (last middleware added = first middleware executed in request chain)

    # Add authentication middleware (executes 5th - after CORS, security, rate limit, setup)
    app.add_middleware(AuthMiddleware, auth_manager=lambda: state.auth)

    # Add rate limiting middleware (executes 4th - protects endpoints, 60 requests/minute for LAN security)
    # Rate limiting configuration
    # Development: Higher limit or disabled via environment variable
    # Production: Standard 60 requests per minute
    rate_limit = int(os.getenv("API_RATE_LIMIT", "300"))  # Default 300 for development
    if os.getenv("DISABLE_RATE_LIMIT", "false").lower() == "true":
        logger.info("[Rate Limit] Rate limiting disabled via environment variable")
    else:
        logger.info(f"[Rate Limit] Configured at {rate_limit} requests per minute")
        app.add_middleware(RateLimitMiddleware, requests_per_minute=rate_limit)

    # Add security headers middleware (executes 3rd - adds security headers to all responses)
    # Handover 0129c: Enhanced security headers (HSTS, CSP, X-Frame-Options, etc.)
    app.add_middleware(SecurityHeadersMiddleware)

    # Add input validation middleware (executes 3rd - validates query params, blocks malicious input)
    # Handover 0129c: Protection against SQL injection, XSS, path traversal
    app.add_middleware(InputValidationMiddleware, strict_mode=False)

    # Add API metrics middleware (executes 4th - counts API and MCP calls)
    app.add_middleware(APIMetricsMiddleware)

    # CSRF protection middleware (optional - requires frontend integration)
    # Handover 0129c: Uncomment when frontend is ready to send X-CSRF-Token headers

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
    # Handover 0046 Issue #4: Router prefix moved to router definition
    # Handover 0126: Modular products module (prefix and tags defined in module __init__.py)
    app.include_router(products.router)
    app.include_router(vision_documents.router, prefix="/api/vision-documents", tags=["vision-documents"])
    # Handover 0125: Modular projects module (prefix and tags defined in module __init__.py)
    app.include_router(projects.router)
    app.include_router(agent_management.router, tags=["Agent Management"])
    app.include_router(agent_templates.router, prefix="/api/v1/agents/templates", tags=["agent-templates"])
    app.include_router(claude_export.router, prefix="/api", tags=["claude-export"])
    app.include_router(downloads.router, tags=["downloads"])
    app.include_router(messages.router, prefix="/api/v1/messages", tags=["messages"])
    app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
    # Handover 0124: Consolidated agent_jobs module (includes orchestration endpoints)
    app.include_router(agent_jobs.router)  # Prefix and tags defined in module __init__.py
    # Handover 0107: Job operations (cancel, force-fail, health) at /api/jobs prefix
    app.include_router(agent_jobs.jobs_router)  # Separate prefix for job operations
    app.include_router(prompts.router, prefix="/api/v1/prompts", tags=["prompts"])  # Handover 0109
    app.include_router(context.router, prefix="/api/v1/context", tags=["context"])
    app.include_router(configuration.router, prefix="/api/v1/config", tags=["configuration"])
    app.include_router(system_prompts.router, prefix="/api/v1/system", tags=["system"])
    app.include_router(statistics.router, prefix="/api/v1/stats", tags=["statistics"])
    # Handover 0126: Modular templates module (prefix and tags defined in module __init__.py)
    app.include_router(templates.router)
    app.include_router(websocket_bridge.router, prefix="/api/v1/ws-bridge", tags=["websocket-bridge"])
    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(auth_pin_recovery.router, prefix="/api/auth", tags=["auth"])
    # Handover 0506: Fixed user endpoint path to /api/v1/users
    app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
    # v3: authenticated user-scoped settings
    app.include_router(user_settings.router, prefix="/api/v1/user", tags=["user-settings"])
    # Handover 0506: System settings endpoints (general, network, database, product-info, cookie-domain)
    app.include_router(settings.router, prefix="/api/v1/settings", tags=["settings"])
    app.include_router(database_setup.router, prefix="/api/setup/database", tags=["database-setup"])
    app.include_router(setup_security.router, prefix="/api/setup", tags=["setup-security"])
    app.include_router(serena.router, prefix="/api/serena", tags=["serena"])
    app.include_router(git.router, prefix="/api/git", tags=["git"])
    app.include_router(network.router, prefix="/api/network", tags=["network"])

    # MCP Installer endpoints for downloadable script generation (Phase 2.1)
    app.include_router(mcp_installer.router, prefix="/api/mcp-installer", tags=["MCP Integration"])

    # Pure MCP JSON-RPC 2.0 over HTTP endpoint (Handover 0032)
    app.include_router(mcp_http.router, tags=["mcp"])

    # Slash command endpoints (Handover 0080a)
    app.include_router(slash_commands.router, prefix="/api", tags=["slash-commands"])

    # AI Tools configuration generator endpoints
    app.include_router(ai_tools.router, prefix="/api/ai-tools", tags=["ai-tools"])

    # Organization endpoints (Handover 0424c)
    app.include_router(org_crud.router, prefix="/api/organizations", tags=["organizations"])
    app.include_router(org_members.router, prefix="/api/organizations", tags=["organization-members"])
    app.include_router(org_members.transfer_router, prefix="/api/organizations", tags=["organization-transfer"])

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
            except (ConnectionError, TimeoutError, RuntimeError, OSError) as e:
                # Database errors from connection/query
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
                user_info = auth_result.get("user", {})
                is_setup = auth_result.get("context") == "setup"
                tenant_key_from_user = user_info.get("tenant_key")

                # Reject non-setup connections missing tenant_key (Handover 0054)
                if not tenant_key_from_user and not is_setup:
                    logger.error(f"WebSocket rejected for {client_id}: missing tenant_key in auth context")
                    await websocket.close(code=1008, reason="Missing tenant key")
                    return

                logger.info(
                    f"[WS AUTH DEBUG] auth_result keys: {list(auth_result.keys())}, user_info keys: {list(user_info.keys())}, tenant_key={tenant_key_from_user}"
                )
                auth_context = {
                    "user": user_info,
                    "context": auth_result.get("context", "normal"),  # 'setup' or 'normal'
                    "tenant_key": tenant_key_from_user,  # CRITICAL: Extract for WebSocket filtering
                }
                # Determine auth type from query parameters
                if token:
                    auth_context["auth_type"] = "jwt"
                elif api_key:
                    auth_context["auth_type"] = "api_key"
                else:
                    auth_context["auth_type"] = "setup"

                await state.websocket_manager.connect(websocket, client_id, auth_context=auth_context)
                state.connections[client_id] = websocket

                # Log successful connection
                auth_type = auth_context.get("auth_type", "setup")
                logger.info(
                    f"WebSocket connected: {client_id} (context: {auth_result.get('context', 'normal')}, auth_type: {auth_type})"
                )

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
                            async with state.db_manager.get_session_async() as session:
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
        except (RuntimeError, ValueError, KeyError):
            logger.exception("WebSocket error for {client_id}")
            state.websocket_manager.disconnect(client_id)
            if client_id in state.connections:
                del state.connections[client_id]

    # Register global exception handlers (Handover 0480a)
    register_exception_handlers(app)
    # Store state reference in app
    app.state.api_state = state

    # Note: db_manager is exposed on app.state in lifespan() AFTER initialization
    # Setting it here would be None since lifespan hasn't run yet

    return app


# Export for uvicorn
app = create_app()
