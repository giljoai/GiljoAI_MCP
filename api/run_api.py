#!/usr/bin/env python3
"""
Run the GiljoAI MCP REST API server
"""

import argparse
import logging
import os
import sys
from pathlib import Path

import uvicorn


# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import colored logger and filter utilities
try:
    from src.giljo_mcp.colored_logger import (
        LogFilter,
        print_error,
        print_highlight,
        print_info,
        print_success,
        print_warning,
        setup_colored_logging,
    )

    COLORED_LOGGING_AVAILABLE = True
except ImportError:
    COLORED_LOGGING_AVAILABLE = False
    # Fallback
    print_success = print_error = print_info = print_highlight = print_warning = print

# Import PortManager for centralized port management
try:
    from src.giljo_mcp.port_manager import get_port_manager

    PORT_MANAGER_AVAILABLE = True
except ImportError:
    PORT_MANAGER_AVAILABLE = False
    logging.warning("PortManager not available, using fallback port detection")


def find_available_port(preferred_port: int) -> int:
    """Find an available port, starting with the preferred one.

    Args:
        preferred_port: The preferred port number

    Returns:
        Available port number

    Raises:
        RuntimeError: If no available port can be found
    """
    import socket

    # Check if preferred port is available
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex(("127.0.0.1", preferred_port))
            if result != 0:  # Port is available
                return preferred_port
    except OSError:  # Socket operations can fail
        pass  # nosec B110 - best effort port check

    # Try some alternative ports
    alternatives = [7273, 7274, 8747, 8823, 9456, 9789]
    for port in alternatives:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(("127.0.0.1", port))
                if result != 0:  # Port is available
                    logging.warning(f"Port {preferred_port} is occupied, using alternative port {port}")
                    return port
        except OSError:  # noqa: PERF203 - Port scan resilience: continue trying ports on socket errors
            continue  # nosec B112 - best effort port scan

    raise RuntimeError(f"Could not find available port (preferred: {preferred_port})")


def get_port_from_sources() -> int:
    """Get port from multiple sources in priority order

    Priority:
    1. GILJO_PORT environment variable
    2. config.yaml (via PortManager)
    3. Default 7272

    Also checks if port is available and finds alternative if needed.

    Returns:
        Available port number
    """
    if PORT_MANAGER_AVAILABLE:
        try:
            # Use PortManager for proper port configuration
            manager = get_port_manager()
            # Get port with availability check
            port = manager.get_api_port(check_availability=True)
            logging.info(f"Using port {port} from PortManager")
            return port
        except (ImportError, RuntimeError, ValueError, OSError) as e:
            logging.warning(f"PortManager failed, using fallback: {e}")

    # Fallback to environment variable or default
    env_port = os.environ.get("GILJO_PORT") or os.environ.get("GILJO_API_PORT")
    if env_port:
        try:
            port = int(env_port)
            if 1024 <= port <= 65535:
                logging.info(f"Using port {port} from environment variable")
                return port
        except ValueError:
            logging.warning(f"Invalid port value in environment: {env_port}")

    # Ultimate fallback
    default_port = 7272
    logging.info(f"Using default port {default_port}")
    return default_port


def get_default_host() -> str:
    """Get default host for API server binding.

    Bind address is derived from the install-time network choice:
    - Localhost installs: 127.0.0.1 (HTTP, no network exposure)
    - LAN/WAN installs: 0.0.0.0 (HTTPS via mkcert)

    Priority:
    1. services.api.host from config.yaml (set by installer)
    2. Default: "0.0.0.0" (backward compat for pre-0843 installs)

    Returns:
        Host to bind to
    """
    try:
        from src.giljo_mcp._config_io import read_config

        config = read_config()
        configured_host = config.get("services", {}).get("api", {}).get("host")
        if configured_host:
            logging.info(f"Using configured API host: {configured_host}")
            return configured_host

        logging.info("No host configured, defaulting to 0.0.0.0")
        return "0.0.0.0"
    except (OSError, ValueError, KeyError) as e:
        logging.warning(f"Could not read config: {e}, defaulting to 0.0.0.0")

    return "0.0.0.0"


def main():
    """Main entry point for running the API server"""
    parser = argparse.ArgumentParser(description="GiljoAI MCP REST API Server")
    parser.add_argument("--host", default=None, help="Host to bind to (default: auto-detect from config)")
    parser.add_argument("--port", type=int, default=None, help="Port to bind to (default: auto-detect from config/env)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    parser.add_argument(
        "--log-level",
        default="info",  # Changed to info to reduce noise
        choices=["debug", "info", "warning", "error", "critical"],
        help="Logging level (default: info)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose debug logging (equivalent to --log-level debug)",
    )
    parser.add_argument("--ssl-keyfile", help="SSL key file for HTTPS")
    parser.add_argument("--ssl-certfile", help="SSL certificate file for HTTPS")

    args = parser.parse_args()

    # Override log level if verbose flag is set
    if args.verbose:
        args.log_level = "debug"

    # Determine host with mode-based default
    if args.host is None:
        args.host = get_default_host()

    # Determine port with fallback logic
    if args.port is None:
        args.port = get_port_from_sources()
    else:
        # If port specified on command line, still check if available
        try:
            args.port = find_available_port(args.port)
        except RuntimeError as e:
            print_error(f"Port error: {e}")
            sys.exit(1)

    # Configure colored logging if available
    if COLORED_LOGGING_AVAILABLE:
        setup_colored_logging(level=getattr(logging, args.log_level.upper()))

        # Create filter to exclude ping/keepalive/health check messages
        exclude_patterns = [
            "GET /health",
            "GET /api/v1/health",
            "WebSocket ping",
            "WebSocket pong",
            "keepalive",
            "keep-alive",
            "heartbeat",
            "/ws/",
            "ping-pong",
        ]

        # Apply filter to root logger
        log_filter = LogFilter(exclude_patterns)
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            handler.addFilter(log_filter)

        # Apply to uvicorn loggers
        for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"]:
            uvicorn_logger = logging.getLogger(logger_name)
            uvicorn_logger.setLevel(getattr(logging, args.log_level.upper()))
            for handler in uvicorn_logger.handlers:
                handler.addFilter(log_filter)
    else:
        # Fallback to basic logging
        logging.basicConfig(
            level=getattr(logging, args.log_level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            force=True,
        )
        logging.getLogger("uvicorn").setLevel(getattr(logging, args.log_level.upper()))
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)  # Reduce access log noise
        logging.getLogger("uvicorn.error").setLevel(getattr(logging, args.log_level.upper()))
        logging.getLogger("fastapi").setLevel(getattr(logging, args.log_level.upper()))

    logger = logging.getLogger(__name__)

    # Log startup information with colored output
    print_highlight("=" * 60)
    print_highlight("  GiljoAI MCP REST API Beta 1.0.0")
    print_highlight("=" * 60)

    print_success(f"Server binding to {args.host}:{args.port}")
    print_info(f"Port selection: {'Command line' if args.port else 'Auto-detected'}")
    print_info(f"Workers: {args.workers}")
    print_info(f"Auto-reload: {'Enabled' if args.reload else 'Disabled'}")
    print_info(f"Log level: {args.log_level.upper()}")

    # SSL Configuration Priority:
    # 1. Command-line arguments (--ssl-keyfile, --ssl-certfile)
    # 2. config.yaml paths (paths.ssl_cert, paths.ssl_key)
    # 3. Environment variables (SSL_CERT_FILE, SSL_KEY_FILE)
    ssl_config = {}

    # Try command-line arguments first
    if args.ssl_keyfile and args.ssl_certfile:
        ssl_config = {"ssl_keyfile": args.ssl_keyfile, "ssl_certfile": args.ssl_certfile}
        print_success(f"SSL enabled via CLI: {args.ssl_certfile}")

    # Try config.yaml if no CLI args
    if not ssl_config:
        try:
            import yaml

            config_path = Path(__file__).parent.parent / "config.yaml"
            if config_path.exists():
                with open(config_path) as f:
                    config = yaml.safe_load(f) or {}

                ssl_enabled = config.get("features", {}).get("ssl_enabled", False)
                ssl_cert = config.get("paths", {}).get("ssl_cert")
                ssl_key = config.get("paths", {}).get("ssl_key")

                if ssl_enabled and ssl_cert and ssl_key:
                    cert_path = Path(ssl_cert)
                    key_path = Path(ssl_key)

                    if cert_path.exists() and key_path.exists():
                        ssl_config = {"ssl_keyfile": str(key_path), "ssl_certfile": str(cert_path)}
                        print_success(f"SSL enabled via config.yaml: {cert_path}")
                    else:
                        print_warning("SSL enabled in config but certificate files not found:")
                        if not cert_path.exists():
                            print_warning(f"  Cert: {cert_path} (not found)")
                        if not key_path.exists():
                            print_warning(f"  Key:  {key_path} (not found)")
                        print_info("Falling back to HTTP mode")
        except (OSError, ValueError, ImportError) as e:
            logger.warning(f"Failed to load SSL config from config.yaml: {e}")

    # Try environment variables as last resort
    if not ssl_config:
        ssl_cert_env = os.getenv("SSL_CERT_FILE")
        ssl_key_env = os.getenv("SSL_KEY_FILE")
        if ssl_cert_env and ssl_key_env:
            cert_path = Path(ssl_cert_env)
            key_path = Path(ssl_key_env)
            if cert_path.exists() and key_path.exists():
                ssl_config = {"ssl_keyfile": str(key_path), "ssl_certfile": str(cert_path)}
                print_success(f"SSL enabled via environment: {cert_path}")

    if not ssl_config:
        print_info("Running in HTTP mode (no SSL configured)")

    print_info("-" * 60)
    http_proto = "https" if ssl_config else "http"
    ws_proto = "wss" if ssl_config else "ws"
    print_info("API Endpoints:")
    print_info(f"  Documentation: {http_proto}://{args.host}:{args.port}/docs")
    print_info(f"  ReDoc: {http_proto}://{args.host}:{args.port}/redoc")
    print_info(f"  OpenAPI JSON: {http_proto}://{args.host}:{args.port}/openapi.json")
    print_success(f"  Health Check: {http_proto}://{args.host}:{args.port}/health")
    print_success(f"  WebSocket: {ws_proto}://{args.host}:{args.port}/ws/{{client_id}}")
    print_info("-" * 60)
    print_info("Available API Routes:")
    print_info("  /api/v1/projects - Project management")
    print_info("  /api/v1/agents - Agent control")
    print_info("  /api/v1/messages - Inter-agent messaging")
    print_info("  /api/v1/tasks - Task management")
    print_info("  /api/v1/context - Context and vision documents")
    print_info("  /api/v1/config - Configuration management")
    print_info("  /api/v1/stats - Statistics and monitoring")
    print_highlight("=" * 60)
    print_success("Server starting... Ready to accept connections!")
    print_info("Ping/keepalive messages are filtered from output")
    print_highlight("=" * 60)

    try:
        # Run the server
        uvicorn.run(
            "api.app:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            workers=args.workers if not args.reload else 1,  # Can't use multiple workers with reload
            log_level=args.log_level,
            **ssl_config,
        )
    except KeyboardInterrupt:
        logger.info("\nShutting down server...")
    except (RuntimeError, OSError, ImportError):
        logger.exception("Failed to start server")
        sys.exit(1)


if __name__ == "__main__":
    main()
