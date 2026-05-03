#!/usr/bin/env python3

# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Run the GiljoAI MCP REST API server
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import ClassVar

import uvicorn


# Ensure project root is on sys.path so uvicorn can resolve "api.app:app"
# (api/ is not a pip package — it needs the project root on sys.path)
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import PortManager for centralized port management
try:
    from giljo_mcp.port_manager import get_port_manager

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
    alternatives = [7273, 8747, 8823, 9456, 9789]
    for port in alternatives:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(("127.0.0.1", port))
                if result != 0:  # Port is available
                    logging.warning(f"Port {preferred_port} is occupied, using alternative port {port}")
                    return port
        except OSError:
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
        from giljo_mcp._config_io import read_config

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


class _ColoredFormatter(logging.Formatter):
    """Colored log output for terminal readability."""

    COLORS: ClassVar[dict[str, str]] = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET: ClassVar[str] = "\033[0m"
    BOLD: ClassVar[str] = "\033[1m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        levelname = f"{self.BOLD}{color}{record.levelname:<8}{self.RESET}"
        timestamp = self.formatTime(record, self.datefmt)
        name = f"\033[34m{record.name}\033[0m"  # Blue for logger name
        message = record.getMessage()
        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        exc = f"\n{record.exc_text}" if record.exc_text else ""
        return f"{timestamp} - {name} - {levelname} - {color}{message}{self.RESET}{exc}"


class _NoiseFilter(logging.Filter):
    """Filter to exclude health check, ping, and static asset log noise."""

    EXCLUDE_PATTERNS: ClassVar[list[str]] = [
        "GET /health",
        "GET /api/v1/health",
        "WebSocket ping",
        "WebSocket pong",
        "keepalive",
        "keep-alive",
        "heartbeat",
        "/ws/",
        "ping-pong",
        "GET /assets/",
        "GET /index.html",
        "GET /favicon.ico",
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage().lower()
        return not any(p.lower() in message for p in self.EXCLUDE_PATTERNS)


def main():
    """Main entry point for running the API server"""
    parser = argparse.ArgumentParser(description="GiljoAI MCP REST API Server")
    parser.add_argument("--host", default=None, help="Host to bind to (default: auto-detect from config)")
    parser.add_argument("--port", type=int, default=None, help="Port to bind to (default: auto-detect from config/env)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    parser.add_argument(
        "--log-level",
        default="info",
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
        except RuntimeError:
            logging.exception("Port error")
            sys.exit(1)

    # Configure stdlib logging with colored output
    log_level = getattr(logging, args.log_level.upper())
    colored_formatter = _ColoredFormatter(datefmt="%Y-%m-%d %H:%M:%S")
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(colored_formatter)
    console_handler.setLevel(log_level)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)

    # Apply noise filter
    noise_filter = _NoiseFilter()
    console_handler.addFilter(noise_filter)

    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"]:
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.setLevel(log_level)
        for handler in uvicorn_logger.handlers:
            handler.addFilter(noise_filter)

    logger = logging.getLogger(__name__)

    # Log startup information
    logger.info("=" * 60)
    logger.info("  GiljoAI MCP REST API Beta 1.0.0")
    logger.info("=" * 60)

    logger.info(f"Server binding to {args.host}:{args.port}")
    logger.info(f"Port selection: {'Command line' if args.port else 'Auto-detected'}")
    logger.info(f"Workers: {args.workers}")
    logger.info(f"Auto-reload: {'Enabled' if args.reload else 'Disabled'}")
    logger.info(f"Log level: {args.log_level.upper()}")

    # SSL Configuration Priority:
    # 1. Command-line arguments (--ssl-keyfile, --ssl-certfile)
    # 2. config.yaml paths (paths.ssl_cert, paths.ssl_key)
    # 3. Environment variables (SSL_CERT_FILE, SSL_KEY_FILE)
    ssl_config = {}

    # Try command-line arguments first
    if args.ssl_keyfile and args.ssl_certfile:
        ssl_config = {"ssl_keyfile": args.ssl_keyfile, "ssl_certfile": args.ssl_certfile}
        logger.info(f"SSL enabled via CLI: {args.ssl_certfile}")

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
                        logger.info(f"SSL enabled via config.yaml: {cert_path}")
                    else:
                        logger.warning("SSL enabled in config but certificate files not found:")
                        if not cert_path.exists():
                            logger.warning(f"  Cert: {cert_path} (not found)")
                        if not key_path.exists():
                            logger.warning(f"  Key:  {key_path} (not found)")
                        logger.info("Falling back to HTTP mode")
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
                logger.info(f"SSL enabled via environment: {cert_path}")

    if not ssl_config:
        logger.info("Running in HTTP mode (no SSL configured)")

    logger.info("-" * 60)
    http_proto = "https" if ssl_config else "http"
    ws_proto = "wss" if ssl_config else "ws"
    logger.info("API Endpoints:")
    logger.info(f"  Documentation: {http_proto}://{args.host}:{args.port}/docs")
    logger.info(f"  ReDoc: {http_proto}://{args.host}:{args.port}/redoc")
    logger.info(f"  OpenAPI JSON: {http_proto}://{args.host}:{args.port}/openapi.json")
    logger.info(f"  Health Check: {http_proto}://{args.host}:{args.port}/health")
    logger.info(f"  WebSocket: {ws_proto}://{args.host}:{args.port}/ws/{{client_id}}")
    logger.info("-" * 60)
    logger.info("Available API Routes:")
    logger.info("  /api/v1/projects - Project management")
    logger.info("  /api/v1/agents - Agent control")
    logger.info("  /api/v1/messages - Inter-agent messaging")
    logger.info("  /api/v1/tasks - Task management")
    logger.info("  /api/v1/context - Context and vision documents")
    logger.info("  /api/v1/config - Configuration management")
    logger.info("  /api/v1/stats - Statistics and monitoring")
    logger.info("=" * 60)
    logger.info("Server starting... Ready to accept connections!")
    logger.info("Ping/keepalive messages are filtered from output")
    logger.info("=" * 60)

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
