# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

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
    from fastapi import Depends, FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
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
    from src.giljo_mcp.models.agent_identity import AgentJob
    from src.giljo_mcp.models.tasks import Message
    from src.giljo_mcp.system_prompts import SystemPromptService
    from src.giljo_mcp.tenant import TenantManager
    from src.giljo_mcp.tools.tool_accessor import ToolAccessor

    logger.info("GiljoAI MCP core modules loaded successfully")
except ImportError as e:
    logger.error(f"Failed to import GiljoAI MCP modules: {e}", exc_info=True)
    logger.exception("Make sure the src/giljo_mcp package is properly installed")
    raise

try:
    logger.info("Loading API endpoints...")
    from .auth_utils import authenticate_websocket
    from .endpoints import (
        agent_jobs,
        ai_tools,
        auth,
        auth_pin_recovery,
        claude_export,
        configuration,
        database_setup,
        downloads,
        git,
        mcp_installer,
        messages,
        network,
        oauth,
        products,
        project_types,
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
    )
    from .endpoints.organizations import crud as org_crud
    from .endpoints.organizations import members as org_members

    logger.info("Loading middleware and websocket...")
    from .exception_handlers import register_exception_handlers
    from .middleware import (
        APIMetricsMiddleware,
        AuthMiddleware,
        CSRFProtectionMiddleware,
        InputValidationMiddleware,
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
    from src.giljo_mcp.licensing.validator import LicenseResult


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
        self.startup_complete: bool = False
        self.degraded_services: list[str] = []
        self.license: Optional[LicenseResult] = None  # Set during lifespan startup
        self.pending_migration: bool = False
        self.update_available: dict | None = None  # {"commits_behind": int, "message": str}
        self.update_checker_task: Optional[asyncio.Task] = None


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

    # Phase 0: License validation
    # [CE] License validation — CE always passes. Commercial builds enforce here.
    from src.giljo_mcp.licensing import LicenseValidator

    license_result = LicenseValidator().validate()
    if not license_result.valid:
        raise RuntimeError(f"License validation failed: {license_result.message}")
    state.license = license_result
    app.state.license = license_result
    logger.info("License: %s", license_result.message)

    # Phase 1: Database and configuration
    await init_database(state)

    # Phase 1.5: Check for pending migrations (read-only)
    try:
        from api.startup.migration_check import check_pending_migrations

        state.pending_migration = await check_pending_migrations(state)
        if state.pending_migration:
            logger.warning("Database has pending migrations. Run: python update.py")
    except Exception as e:
        logger.warning("Could not check migration status: %s", e)

    # Phase 2: Core services
    await init_core_services(state)

    # Phase 3: Event bus and WebSocket listener (optional — REST API works without it)
    await init_event_bus(state)
    if state.event_bus is None:
        state.degraded_services.append("event_bus")

    # Phase 4: Background tasks (optional — individual tasks handle their own failures)
    await init_background_tasks(state)

    # Phase 5: Health monitoring (optional — already degrades gracefully)
    await init_health_monitor(state)

    # Phase 6: Silence detection (optional — already degrades gracefully)
    await init_silence_detector(state)

    # Phase 7: Validation (optional — already degrades gracefully)
    await init_validation(state)

    # Expose db_manager and websocket_manager directly on app.state
    # This must be done AFTER initialization, not in create_app()
    app.state.db_manager = state.db_manager
    app.state.websocket_manager = state.websocket_manager
    app.state.websocket_broker = state.websocket_broker

    # Suppress Windows ProactorEventLoop ConnectionResetError noise
    # (Python 3.12+ on Windows: browser closes keep-alive connections,
    # proactor transport logs ERROR trying to shutdown already-closed sockets)
    import asyncio
    import sys

    if sys.platform == "win32":
        loop = asyncio.get_running_loop()
        _original_handler = loop.get_exception_handler()

        def _suppress_connection_reset(loop, context):
            exc = context.get("exception")
            if isinstance(exc, ConnectionResetError):
                return
            if _original_handler:
                _original_handler(loop, context)
            else:
                loop.default_exception_handler(context)

        loop.set_exception_handler(_suppress_connection_reset)

    # Phase 8: MCP SDK session manager (optional — REST/dashboard work without it)
    from api.endpoints.mcp_sdk_server import start_mcp_session_manager, stop_mcp_session_manager

    try:
        await start_mcp_session_manager()
    except Exception as e:  # Broad catch: startup resilience, non-fatal initialization
        logger.warning("Optional startup phase [mcp_session_manager] failed: %s — running in degraded mode", e)
        state.degraded_services.append("mcp_session_manager")

    # Mark startup complete
    state.startup_complete = True
    app.state.startup_complete = True

    if state.degraded_services:
        logger.warning("Startup complete with degraded services: %s", ", ".join(state.degraded_services))
    logger.info("=" * 70)
    logger.info("API startup complete - All systems initialized")
    logger.info("=" * 70)

    yield

    # Shutdown
    if "mcp_session_manager" not in state.degraded_services:
        await stop_mcp_session_manager()
    await shutdown(state)

    logger.info("API shutdown complete")


def _configure_middleware(app: FastAPI) -> None:
    """Configure all middleware for the FastAPI application.

    Sets up CORS, security headers, rate limiting, authentication,
    CSRF protection, input validation, and API metrics middleware.
    Middleware is added in reverse order of execution (last added = first executed).
    """
    # Configure CORS - use explicit origins from config.yaml security section
    from src.giljo_mcp._config_io import read_config as _read_app_config

    cors_origins = []
    config = {}  # Default to empty dict so config.get() is safe if read fails

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
            "http://127.0.0.1:7272",
            "http://localhost:7272",
        ]
        logger.info(f"Using default CORS origins (no wildcards): {cors_origins}")
    else:
        # Reject wildcard patterns for security
        safe_origins = [origin for origin in cors_origins if "*" not in origin]
        if len(safe_origins) < len(cors_origins):
            logger.warning("CORS wildcard entries removed from config — only explicit origins are allowed")
            cors_origins = (
                safe_origins
                if safe_origins
                else [
                    "http://127.0.0.1:7272",
                    "http://localhost:7272",
                ]
            )

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
                frontend_port = config.get("services", {}).get("frontend", {}).get("port", 7272)
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

    # Add HTTPS origin variants when SSL is enabled
    ssl_enabled = config.get("features", {}).get("ssl_enabled", False)
    if ssl_enabled:
        https_origins = []
        for origin in cors_origins.copy():
            if origin.startswith("http://"):
                https_variant = "https://" + origin[len("http://") :]
                if https_variant not in cors_origins:
                    https_origins.append(https_variant)
        if https_origins:
            cors_origins.extend(https_origins)
            logger.info(f"Added HTTPS CORS origins for SSL mode: {https_origins}")

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

    # CSRF protection middleware (executes after auth, before route handlers)
    # Handover 0765f: Enabled with double-submit cookie pattern
    app.add_middleware(
        CSRFProtectionMiddleware,
        exempt_paths=[
            "/health",
            "/api/health",
            "/api/metrics",
        ],
        exempt_prefixes=[
            "/api/auth/",  # Auth endpoints (login, register, refresh — no CSRF cookie yet)
            "/api/oauth/token",  # OAuth token exchange (external MCP clients, PKCE-protected)
            "/api/oauth/.well-known/",  # OAuth metadata (public GET)
            "/api/setup/",  # Setup wizard (runs before auth is configured)
            "/mcp",  # MCP-over-HTTP (API key auth, not cookie-based)
            "/api/download/",  # Public download endpoints
            "/api/mcp-installer/",  # MCP installer (Bearer token auth, not cookie-based)
            "/ws",  # WebSocket endpoints
            "/assets",  # Static file assets (production frontend serving)
        ],
    )

    # v3.0: Setup mode middleware removed - unified authentication for all endpoints

    # Add CORS middleware (executes 1st - MUST be first to handle OPTIONS preflight requests)
    # This MUST execute before all other middleware to add CORS headers to OPTIONS responses
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-API-Key", "X-Tenant-Key", "X-CSRF-Token"],
    )


def _register_routers(app: FastAPI) -> None:
    """Register all API routers on the FastAPI application.

    Includes routers for projects, agents, messages, tasks, configuration,
    MCP endpoints, organizations, and other feature modules.
    """
    # Include routers
    # Handover 0046 Issue #4: Router prefix moved to router definition
    # Handover 0126: Modular products module (prefix and tags defined in module __init__.py)
    app.include_router(products.router)
    app.include_router(vision_documents.router, prefix="/api/vision-documents", tags=["vision-documents"])
    # Handover 0125: Modular projects module (prefix and tags defined in module __init__.py)
    app.include_router(projects.router)
    # Handover 0440a: Project type taxonomy module (prefix and tags defined in module __init__.py)
    app.include_router(project_types.router)
    app.include_router(claude_export.router, prefix="/api", tags=["claude-export"])
    app.include_router(downloads.router, tags=["downloads"])
    app.include_router(messages.router, prefix="/api/v1/messages", tags=["messages"])
    app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
    # Handover 0124: Consolidated agent_jobs module (includes orchestration endpoints)
    app.include_router(agent_jobs.router)  # Prefix and tags defined in module __init__.py
    # Handover 0107: Job operations (cancel, force-fail, health) at /api/jobs prefix
    app.include_router(agent_jobs.jobs_router)  # Separate prefix for job operations
    app.include_router(prompts.router, prefix="/api/v1/prompts", tags=["prompts"])  # Handover 0109
    app.include_router(configuration.router, prefix="/api/v1/config", tags=["configuration"])
    app.include_router(system_prompts.router, prefix="/api/v1/system", tags=["system"])
    app.include_router(statistics.router, prefix="/api/v1/stats", tags=["statistics"])
    # Handover 0126: Modular templates module (prefix and tags defined in module __init__.py)
    app.include_router(templates.router)
    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(auth_pin_recovery.router, prefix="/api/auth", tags=["auth"])
    app.include_router(oauth.router, prefix="/api/oauth", tags=["oauth"])
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

    # MCP SDK Streamable HTTP endpoint (Handover 0846 — replaces custom JSON-RPC 0032)
    # Registered as a direct FastAPI route (not app.mount) to avoid the
    # 307 trailing-slash redirect that Mount adds and breaks MCP clients.
    from api.endpoints.mcp_sdk_server import get_mcp_asgi_app

    _mcp_app = get_mcp_asgi_app()

    @app.api_route("/mcp", methods=["GET", "POST", "DELETE"], include_in_schema=False)
    @app.api_route("/mcp/", methods=["GET", "POST", "DELETE"], include_in_schema=False)
    async def mcp_endpoint(request: Request):
        """MCP SDK Streamable HTTP endpoint."""
        from starlette.responses import Response

        response_started = False
        status_code = 200
        headers_list = []
        body_parts = []

        async def send(message):
            nonlocal response_started, status_code, headers_list
            if message["type"] == "http.response.start":
                response_started = True
                status_code = message["status"]
                headers_list = message.get("headers", [])
            elif message["type"] == "http.response.body":
                body_parts.append(message.get("body", b""))

        await _mcp_app(request.scope, request.receive, send)

        return Response(
            content=b"".join(body_parts),
            status_code=status_code,
            headers={
                (k.decode() if isinstance(k, bytes) else k): (v.decode() if isinstance(v, bytes) else v)
                for k, v in headers_list
            },
        )

    # Slash command endpoints (Handover 0080a)
    app.include_router(slash_commands.router, prefix="/api", tags=["slash-commands"])

    # AI Tools configuration generator endpoints
    app.include_router(ai_tools.router, prefix="/api/ai-tools", tags=["ai-tools"])

    # Organization endpoints (Handover 0424c)
    app.include_router(org_crud.router, prefix="/api/organizations", tags=["organizations"])
    app.include_router(org_members.router, prefix="/api/organizations", tags=["organization-members"])
    app.include_router(org_members.transfer_router, prefix="/api/organizations", tags=["organization-transfer"])


async def _authenticate_ws_connection(
    websocket: WebSocket,
    client_id: str,
    api_key: Optional[str],
    token: Optional[str],
) -> Optional[dict]:
    """Authenticate an incoming WebSocket connection and return the auth context.

    Obtains a short-lived database session (None in setup mode), delegates to
    authenticate_websocket, validates that a tenant_key is present for normal
    connections, and then cleans up the session.  On failure the connection is
    closed with code 1008 and None is returned.

    Args:
        websocket: The incoming WebSocket connection (not yet accepted).
        client_id: Caller-supplied client identifier.
        api_key: Optional API-key query param.
        token: Optional JWT query param.

    Returns:
        auth_context dict on success, or None if the connection was rejected.
    """
    try:
        session = None
        session_cm = None
        if state.db_manager:
            session_cm = state.db_manager.get_session_async()
            session = await session_cm.__aenter__()

        try:
            auth_result = await authenticate_websocket(websocket, db=session)

            await websocket.accept()

            user_info = auth_result.get("user", {})
            is_setup = auth_result.get("context") == "setup"
            tenant_key_from_user = user_info.get("tenant_key")

            if not tenant_key_from_user and not is_setup:
                logger.error(f"WebSocket rejected for {client_id}: missing tenant_key in auth context")
                await websocket.close(code=1008, reason="Missing tenant key")
                return None

            logger.info(
                f"[WS AUTH DEBUG] auth_result keys: {list(auth_result.keys())}, "
                f"user_info keys: {list(user_info.keys())}, tenant_key={tenant_key_from_user}"
            )
            auth_context = {
                "user": user_info,
                "context": auth_result.get("context", "normal"),
                "tenant_key": tenant_key_from_user,
            }
            if token:
                auth_context["auth_type"] = "jwt"
            elif api_key:
                auth_context["auth_type"] = "api_key"
            else:
                auth_context["auth_type"] = "setup"

            await state.websocket_manager.connect(websocket, client_id, auth_context=auth_context)
            state.connections[client_id] = websocket

            auth_type = auth_context.get("auth_type", "setup")
            logger.info(
                f"WebSocket connected: {client_id} "
                f"(context: {auth_result.get('context', 'normal')}, auth_type: {auth_type})"
            )
            return auth_context

        finally:
            if session_cm is not None:
                await session_cm.__aexit__(None, None, None)

    except WebSocketException as e:
        logger.warning(f"WebSocket authentication failed for {client_id}: {e.reason}")
        await websocket.close(code=1008, reason=e.reason or "Unauthorized")
        return None


async def _handle_ws_subscribe(
    websocket: WebSocket,
    client_id: str,
    data: dict,
    auth_context: dict,
) -> None:
    """Handle a WebSocket subscribe message with tenant isolation enforcement.

    Resolves the tenant_key for the requested entity by querying the database,
    denies the subscription when the tenant cannot be resolved, and blocks
    cross-tenant subscriptions (Handover 0769a security fix).

    Args:
        websocket: Active WebSocket connection.
        client_id: Caller-supplied client identifier.
        data: Parsed JSON message containing ``entity_type`` and ``entity_id``.
        auth_context: Auth context dict from _authenticate_ws_connection,
                      must contain ``tenant_key``.
    """
    entity_type = data.get("entity_type")
    entity_id = data.get("entity_id")

    try:
        tenant_key = None
        if state.db_manager:
            async with state.db_manager.get_session_async() as session:
                if entity_type == "project":
                    stmt = select(Project).where(Project.id == entity_id)
                    result = await session.execute(stmt)
                    project = result.scalar_one_or_none()
                    if project:
                        tenant_key = project.tenant_key
                elif entity_type == "agent":
                    stmt = select(AgentJob).where(AgentJob.job_id == entity_id)
                    result = await session.execute(stmt)
                    agent_job = result.scalar_one_or_none()
                    if agent_job:
                        tenant_key = agent_job.tenant_key
                elif entity_type == "message":
                    stmt = select(Message).where(Message.id == entity_id)
                    result = await session.execute(stmt)
                    message = result.scalar_one_or_none()
                    if message:
                        tenant_key = message.tenant_key

        if not tenant_key:
            await websocket.send_json(
                {
                    "type": "error",
                    "error": "subscription_denied",
                    "message": f"Cannot resolve tenant for {entity_type}:{entity_id}",
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                }
            )
            return

        if tenant_key != auth_context.get("tenant_key"):
            logger.warning(
                f"Cross-tenant subscription blocked: user tenant={auth_context.get('tenant_key')}, "
                f"entity tenant={tenant_key}"
            )
            await websocket.send_json(
                {
                    "type": "error",
                    "error": "subscription_denied",
                    "message": "Cross-tenant subscription not allowed",
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                }
            )
            return

        await state.websocket_manager.subscribe(client_id, entity_type, entity_id, tenant_key)
        await websocket.send_json({"type": "subscribed", "entity_type": entity_type, "entity_id": entity_id})

    except HTTPException as e:
        await websocket.send_json(
            {
                "type": "error",
                "error": "subscription_denied",
                "message": str(e.detail),
                "entity_type": entity_type,
                "entity_id": entity_id,
            }
        )


def _register_event_handlers(app: FastAPI) -> None:
    """Register route handlers, WebSocket endpoint, and exception handlers.

    Sets up the root endpoint, health check, WebSocket endpoint for real-time
    updates, and global exception handlers.
    """

    dist_dir = Path(state.config.get_nested("paths.static", "frontend/dist")) if state.config else Path("frontend/dist")
    has_frontend = dist_dir.exists() and (dist_dir / "index.html").exists()

    if not has_frontend:

        @app.get("/")
        async def root():
            """Root endpoint"""
            edition = "community"
            if hasattr(app.state, "config") and app.state.config:
                edition = getattr(app.state.config, "edition", None) or "community"
            return {
                "name": "GiljoAI MCP",
                "version": "1.0.0",
                "edition": edition,
                "status": "operational",
                "endpoints": {"api": "/docs", "websocket": "/ws", "health": "/health"},
            }

    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        checks = {"api": "healthy", "database": "unknown", "websocket": "unknown"}

        if state.db_manager:
            try:
                async with state.db_manager.get_session_async() as session:
                    await session.execute(text("SELECT 1"))
                    checks["database"] = "healthy"
            except (ConnectionError, TimeoutError, RuntimeError, OSError) as e:
                checks["database"] = f"unhealthy: {e!s}"

        if state.websocket_manager:
            checks["websocket"] = "healthy"
            checks["active_connections"] = len(state.connections)

        status = "healthy" if all(v == "healthy" or isinstance(v, int) for v in checks.values()) else "degraded"

        return {"status": status, "checks": checks}

    from src.giljo_mcp.auth.dependencies import get_current_active_user
    from src.giljo_mcp.models.auth import User

    @app.get("/api/system/status")
    async def system_status(current_user: User = Depends(get_current_active_user)):
        """System status for admin dashboard notifications.

        Returns pending migration flag and update availability. Requires
        a valid authenticated session.
        """
        return {
            "pending_migration": state.pending_migration,
            "update_available": state.update_available,
        }

    @app.websocket("/ws/{client_id}")
    async def websocket_endpoint(
        websocket: WebSocket, client_id: str, api_key: Optional[str] = Query(None), token: Optional[str] = Query(None)
    ):
        """WebSocket endpoint for real-time updates with authentication"""
        auth_context = await _authenticate_ws_connection(
            websocket=websocket,
            client_id=client_id,
            api_key=api_key,
            token=token,
        )
        if auth_context is None:
            return

        try:
            while True:
                data = await websocket.receive_json()

                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

                elif data.get("type") == "subscribe":
                    await _handle_ws_subscribe(
                        websocket=websocket,
                        client_id=client_id,
                        data=data,
                        auth_context=auth_context,
                    )

                elif data.get("type") == "unsubscribe":
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


def _build_openapi_servers() -> list[dict[str, str]]:
    """Build OpenAPI servers list respecting ssl_enabled config."""
    try:
        from src.giljo_mcp.config_manager import get_config

        ssl_enabled = get_config().get_nested("features.ssl_enabled", default=False)
    except (OSError, ImportError, ValueError):
        ssl_enabled = False
    proto = "https" if ssl_enabled else "http"
    return [
        {"url": f"{proto}://localhost:7272", "description": "Local development server"},
        {"url": f"{proto}://0.0.0.0:7272", "description": "LAN accessible server"},
    ]


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""

    app = FastAPI(
        title="GiljoAI MCP API Beta 1.0.0 - Community Edition",
        description="""
        ## Multi-Agent Orchestration System REST API

        GiljoAI MCP provides a comprehensive REST API for managing AI agent orchestration,
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
            {
                "name": "messages",
                "description": "Inter-agent messaging - send, acknowledge, and complete messages between agents",
            },
            {"name": "tasks", "description": "Task management - track and manage development tasks and technical debt"},
            {"name": "configuration", "description": "Configuration management - system and tenant-specific settings"},
            {
                "name": "statistics",
                "description": "Statistics and monitoring - system metrics, performance, and health checks",
            },
        ],
        servers=_build_openapi_servers(),
        contact={
            "name": "GiljoAI Support",
            "url": "https://github.com/giljoai/mcp-orchestrator",
            "email": "infoteam@giljo.ai",
        },
        license_info={
            "name": "GiljoAI Community License v1.1",
            "url": "https://github.com/giljoai/GiljoAI_MCP/blob/master/LICENSE",
        },
    )

    # Configure middleware, routers, and event handlers
    _configure_middleware(app)
    _register_routers(app)
    _register_event_handlers(app)

    # Production frontend serving (single-port mode)
    # Must be LAST so API routes registered above take priority
    dist_dir = Path(state.config.get_nested("paths.static", "frontend/dist")) if state.config else Path("frontend/dist")
    if dist_dir.exists() and (dist_dir / "index.html").exists():
        from starlette.responses import FileResponse
        from starlette.staticfiles import StaticFiles

        @app.exception_handler(404)
        async def spa_fallback(request, exc):
            """SPA fallback: non-API 404s serve index.html for Vue Router."""
            path = request.url.path
            if not path.startswith(("/api", "/ws", "/mcp", "/health", "/docs", "/redoc", "/openapi.json")):
                return FileResponse(str(dist_dir / "index.html"))
            from fastapi.responses import JSONResponse

            return JSONResponse(status_code=404, content={"detail": "Not Found"})

        app.mount("/", StaticFiles(directory=str(dist_dir), html=False), name="static")

    return app


# Export for uvicorn
app = create_app()
