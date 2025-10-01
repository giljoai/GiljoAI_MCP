#!/usr/bin/env python3
"""
Run the GiljoAI MCP REST API server
"""

import argparse
import logging
import os
import socket
import sys
from pathlib import Path

import uvicorn


# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def load_config_port() -> int:
    """Load port from config.yaml if available

    Returns:
        Port number from config, or 7272 as default
    """
    try:
        import yaml
        config_path = Path(__file__).parent.parent / "config.yaml"
        if config_path.exists():
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
                # Try new unified structure first (server.port)
                if config and "server" in config:
                    port = config["server"].get("port")
                    if port and isinstance(port, int):
                        return port
                    # Fallback to old structure (server.ports.api)
                    if "ports" in config["server"]:
                        port = config["server"]["ports"].get("api")
                        if port and isinstance(port, int):
                            return port
    except Exception as e:
        logging.debug(f"Could not load port from config: {e}")

    return 7272  # Default unified port


def check_port_available(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is available

    Args:
        port: Port number to check
        host: Host to check on

    Returns:
        True if port is available, False if in use
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result != 0  # True if NOT in use (connection failed)
    except Exception:
        return False


def find_available_port(preferred: int) -> int:
    """Find an available port, starting with preferred

    Args:
        preferred: Preferred port number

    Returns:
        Available port number

    Raises:
        RuntimeError: If no available port can be found
    """
    # Try preferred port first
    if check_port_available(preferred):
        return preferred

    # Try alternative ports
    alternatives = [7273, 7274, 8747, 8823, 9456, 9789]
    for port in alternatives:
        if check_port_available(port):
            logging.warning(f"Port {preferred} is occupied, using alternative port {port}")
            return port

    # Last resort: find random available port in safe range
    import random
    for _ in range(10):
        port = random.randint(7200, 9999)
        if check_port_available(port):
            logging.warning(f"Using random available port {port}")
            return port

    raise RuntimeError(f"Could not find available port (preferred: {preferred})")


def get_port_from_sources() -> int:
    """Get port from multiple sources in priority order

    Priority:
    1. GILJO_PORT environment variable
    2. config.yaml
    3. Default 7272

    Also checks if port is available and finds alternative if needed.

    Returns:
        Available port number
    """
    # Check environment variable first (highest priority)
    env_port = os.environ.get("GILJO_PORT")
    if env_port:
        try:
            port = int(env_port)
            if 1024 <= port <= 65535:
                return find_available_port(port)
        except (ValueError, RuntimeError):
            logging.warning(f"Invalid GILJO_PORT value: {env_port}")

    # Check config file
    config_port = load_config_port()
    try:
        return find_available_port(config_port)
    except RuntimeError:
        # If all else fails, return the config port and let uvicorn handle the error
        return config_port


def main():
    """Main entry point for running the API server"""
    parser = argparse.ArgumentParser(description="GiljoAI MCP REST API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=None, help="Port to bind to (default: auto-detect from config/env)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Logging level (default: info)",
    )
    parser.add_argument("--ssl-keyfile", help="SSL key file for HTTPS")
    parser.add_argument("--ssl-certfile", help="SSL certificate file for HTTPS")

    args = parser.parse_args()

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

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()), format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

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
