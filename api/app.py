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
        agent_templates,
        agents,
        ai_tools,
        auth,
        auth_pin_recovery,
        claude_export,
        configuration,
        context,
        database_setup,
        downloads,
        mcp_http,
        mcp_installer,
        mcp_tools,
        messages,
        network,
        orchestration,
        products,
        projects,
        prompts,
        serena,
        setup_security,
        slash_commands,
        statistics,
        tasks,
        templates,
        user_settings,
        users,
        vision_documents,
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
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        self.health_monitor = None
        self.health_monitor_task: Optional[asyncio.Task] = None


state = APIState()


@asynccontextmanager
async def lifespan(app: FastAPI):
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
        logger.info("Configuration loaded successfully")
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
        logger.info("No API key configured - all clients require JWT authentication (unified auth)")

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

    # Start download token cleanup task (Handover 0100)
    async def cleanup_expired_download_tokens():
        """Background task to cleanup expired download tokens every 15 minutes"""
        from giljo_mcp.download_tokens import TokenManager

        while True:
            try:
                await asyncio.sleep(900)  # 15 minutes

                if state.db_manager:
                    async with state.db_manager.get_session_async() as session:
                        token_manager = TokenManager(session)
                        result = await token_manager.cleanup_expired_tokens()
                        # Backward-compatible handling: support int or dict
                        deleted_total = result.get("total", 0) if isinstance(result, dict) else int(result or 0)
                        if deleted_total > 0:
                            logger.info(f"Download token cleanup: {deleted_total} tokens removed")
                        else:
                            logger.debug("Download token cleanup: no tokens removed")
            except Exception as e:
                logger.error(f"Error during download token cleanup: {e}", exc_info=True)

    try:
        logger.info("Starting download token cleanup task...")
        cleanup_task = asyncio.create_task(cleanup_expired_download_tokens())
        state.cleanup_task = cleanup_task  # Store reference to prevent garbage collection
        logger.info("Download token cleanup task started (runs every 15 minutes)")
    except Exception as e:
        logger.error(f"Failed to start download token cleanup task: {e}", exc_info=True)

    # Start agent health monitoring service (Handover 0107)
    try:
        logger.info("Initializing agent health monitoring...")

        # Load health_monitoring config directly from YAML
        import yaml
        health_config_dict = {}
        if state.config.config_path.exists():
            with open(state.config.config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f) or {}
                health_config_dict = config_data.get('health_monitoring', {})

        # Only start if enabled in config
        if health_config_dict.get('enabled', True):
            from giljo_mcp.monitoring.agent_health_monitor import AgentHealthMonitor
            from giljo_mcp.monitoring.health_config import HealthCheckConfig

            # Build configuration from config.yaml
            timeout_config = health_config_dict.get('timeouts', {})
            health_config = HealthCheckConfig(
                waiting_timeout_minutes=timeout_config.get('waiting_timeout', 2),
                active_no_progress_minutes=timeout_config.get('active_no_progress', 5),
                heartbeat_timeout_minutes=timeout_config.get('heartbeat_timeout', 10),
                timeout_overrides={
                    'orchestrator': timeout_config.get('orchestrator', 15),
                    'implementer': timeout_config.get('implementer', 10),
                    'tester': timeout_config.get('tester', 8),
                    'analyzer': timeout_config.get('analyzer', 5),
                    'reviewer': timeout_config.get('reviewer', 6),
                    'documenter': timeout_config.get('documenter', 5),
                },
                scan_interval_seconds=health_config_dict.get('scan_interval_seconds', 300),
                auto_fail_on_timeout=health_config_dict.get('auto_fail_on_timeout', False),
                notify_orchestrator=health_config_dict.get('notify_orchestrator', True)
            )

            # Initialize monitor with dependencies
            state.health_monitor = AgentHealthMonitor(
                db_manager=state.db_manager,
                ws_manager=state.websocket_manager,
                config=health_config
            )

            # Start monitoring service
            await state.health_monitor.start()
            logger.info(f"Agent health monitoring started (scan interval: {health_config.scan_interval_seconds}s)")
        else:
            logger.info("Agent health monitoring disabled in configuration")
    except Exception as e:
        logger.error(f"Failed to start agent health monitoring: {e}", exc_info=True)
        logger.warning("Continuing without health monitoring")

    # v3.0: Removed localhost auto-login - unified authentication for all connections

    # Check setup state on startup (version tracking and validation)
    if state.db_manager:
        try:
            logger.info("Checking setup state...")
            from pathlib import Path

            # Get current version from config
            import yaml

            from src.giljo_mcp.setup.state_manager import SetupStateManager

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
                    logger.warning("⚠️ Setup validation failures detected:")
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

    # Cancel background tasks
    try:
        logger.info("Canceling background tasks...")
        if state.heartbeat_task:
            state.heartbeat_task.cancel()
            try:
                await state.heartbeat_task
            except asyncio.CancelledError:
                pass
        if state.cleanup_task:
            state.cleanup_task.cancel()
            try:
                await state.cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Background tasks canceled")
    except Exception as e:
        logger.error(f"Error canceling background tasks: {e}", exc_info=True)

    # Stop health monitoring gracefully
    if state.health_monitor:
        try:
            logger.info("Stopping agent health monitoring...")
            await state.health_monitor.stop()
            logger.info("Agent health monitoring stopped")
        except Exception as e:
            logger.error(f"Error stopping health monitor: {e}", exc_info=True)

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
            with open(config_path) as f:
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
            logger.warning("CORS origins contain wildcards - this reduces security. Consider using explicit origins.")

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
        # Adapter disconnected - log warning and fall back to localhost
        elif adapter_name:
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
    # Rate limiting configuration
    # Development: Higher limit or disabled via environment variable
    # Production: Standard 60 requests per minute
    import os

    rate_limit = int(os.getenv("API_RATE_LIMIT", "300"))  # Default 300 for development
    if os.getenv("DISABLE_RATE_LIMIT", "false").lower() == "true":
        logger.info("[Rate Limit] Rate limiting disabled via environment variable")
    else:
        logger.info(f"[Rate Limit] Configured at {rate_limit} requests per minute")
        app.add_middleware(RateLimitMiddleware, requests_per_minute=rate_limit)

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
    # Handover 0046 Issue #4: Router prefix moved to router definition
    app.include_router(products.router, prefix="/api")
    app.include_router(vision_documents.router, prefix="/api/vision-documents", tags=["vision-documents"])
    app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
    app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
    app.include_router(agent_management.router, tags=["Agent Management"])
    app.include_router(agent_templates.router, prefix="/api/v1/agents/templates", tags=["agent-templates"])
    app.include_router(claude_export.router, prefix="/api", tags=["claude-export"])
    app.include_router(downloads.router, tags=["downloads"])
    app.include_router(messages.router, prefix="/api/v1/messages", tags=["messages"])
    app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
    app.include_router(agent_jobs.router, prefix="/api/agent-jobs", tags=["agent-jobs"])
    app.include_router(orchestration.router, prefix="/api/orchestrator", tags=["orchestration"])
    app.include_router(prompts.router, prefix="/api/prompts", tags=["prompts"])
    app.include_router(context.router, prefix="/api/v1/context", tags=["context"])
    app.include_router(configuration.router, prefix="/api/v1/config", tags=["configuration"])
    app.include_router(statistics.router, prefix="/api/v1/stats", tags=["statistics"])
    app.include_router(templates.router, prefix="/api/v1/templates", tags=["templates"])
    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(auth_pin_recovery.router, prefix="/api/auth", tags=["auth"])
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

    # Slash command endpoints (Handover 0080a)
    app.include_router(slash_commands.router, prefix="/api", tags=["slash-commands"])

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
                    "user": auth_result.get("user", {}),
                    "context": auth_result.get("context", "normal"),  # 'setup' or 'normal'
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
        """Custom HTTP exception handler (JSON, with detail for tooling/tests)"""
        logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "detail": exc.detail,
                "status_code": exc.status_code,
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
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
