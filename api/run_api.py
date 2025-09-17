#!/usr/bin/env python3
"""
Run the GiljoAI MCP REST API server
"""

import argparse
import logging
import sys
from pathlib import Path

import uvicorn


# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    """Main entry point for running the API server"""
    parser = argparse.ArgumentParser(description="GiljoAI MCP REST API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to (default: 8000)")
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

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()), format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logger = logging.getLogger(__name__)

    # Log startup information
    logger.info("=" * 60)
    logger.info("GiljoAI MCP Orchestrator REST API")
    logger.info("=" * 60)
    logger.info(f"Starting server on {args.host}:{args.port}")
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
    except Exception as e:
        logger.exception(f"Failed to start server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
