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
            result = sock.connect_ex(('127.0.0.1', preferred_port))
            if result != 0:  # Port is available
                return preferred_port
    except Exception:
        pass

    # Try some alternative ports
    alternatives = [7273, 7274, 8747, 8823, 9456, 9789]
    for port in alternatives:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('127.0.0.1', port))
                if result != 0:  # Port is available
                    logging.warning(f"Port {preferred_port} is occupied, using alternative port {port}")
                    return port
        except Exception:
            continue

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
        except Exception as e:
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


def main():
    """Main entry point for running the API server"""
    # Set up basic logging immediately to catch early errors
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    )
    early_logger = logging.getLogger(__name__)
    early_logger.info("Starting API server initialization...")

    parser = argparse.ArgumentParser(description="GiljoAI MCP REST API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=None, help="Port to bind to (default: auto-detect from config/env)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    parser.add_argument(
        "--log-level",
        default="debug",  # Changed to debug for verbose output
        choices=["debug", "info", "warning", "error", "critical"],
        help="Logging level (default: debug)",
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

    # Determine port with fallback logic
    if args.port is None:
        args.port = get_port_from_sources()
    else:
        # If port specified on command line, still check if available
        try:
            args.port = find_available_port(args.port)
        except RuntimeError as e:
            logging.error(f"Port error: {e}")
            sys.exit(1)

    # Configure logging with verbose output
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        force=True  # Force reconfiguration
    )

    # Set uvicorn and fastapi loggers to same level for consistency
    logging.getLogger("uvicorn").setLevel(getattr(logging, args.log_level.upper()))
    logging.getLogger("uvicorn.access").setLevel(getattr(logging, args.log_level.upper()))
    logging.getLogger("uvicorn.error").setLevel(getattr(logging, args.log_level.upper()))
    logging.getLogger("fastapi").setLevel(getattr(logging, args.log_level.upper()))

    logger = logging.getLogger(__name__)

    # Log startup information
    logger.info("=" * 60)
    logger.info("GiljoAI MCP Orchestrator REST API v2.0")
    logger.info("=" * 60)
    logger.info(f"Starting server on {args.host}:{args.port}")
    logger.info(f"Port selection: {'Command line' if args.port else 'Auto-detected'}")
    logger.info(f"Workers: {args.workers}")
    logger.info(f"Auto-reload: {args.reload}")
    logger.info(f"Log level: {args.log_level}")

    if args.ssl_keyfile and args.ssl_certfile:
        logger.info(f"SSL enabled with cert: {args.ssl_certfile}")
        ssl_config = {"ssl_keyfile": args.ssl_keyfile, "ssl_certfile": args.ssl_certfile}
    else:
        ssl_config = {}
        logger.info("Running in HTTP mode (no SSL)")

    logger.info("-" * 60)
    logger.info("API Endpoints:")
    logger.info(f"  Documentation: http://{args.host}:{args.port}/docs")
    logger.info(f"  ReDoc: http://{args.host}:{args.port}/redoc")
    logger.info(f"  OpenAPI JSON: http://{args.host}:{args.port}/openapi.json")
    logger.info(f"  Health Check: http://{args.host}:{args.port}/health")
    logger.info(f"  WebSocket: ws://{args.host}:{args.port}/ws/{{client_id}}")
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
    except Exception:
        logger.exception("Failed to start server")
        sys.exit(1)


if __name__ == "__main__":
    main()
