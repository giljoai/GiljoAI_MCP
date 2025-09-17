"""
Main entry point for the GiljoAI MCP FastAPI application.

This module provides the main FastAPI application instance that can be used
by ASGI servers like uvicorn, gunicorn, or other deployment tools.
"""

from .app import app


# Export the FastAPI app for ASGI servers
__all__ = ["app"]

if __name__ == "__main__":
    import sys
    from pathlib import Path

    import uvicorn

    # Add src to path for imports
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

    from src.giljo_mcp.config_manager import get_config

    config = get_config()

    # Run the development server
    uvicorn.run(
        "api.main:app",
        host=config.server.api_host,
        port=config.server.api_port,
        reload=False,  # Disable reload to avoid Windows handle issues
        access_log=True,
    )
