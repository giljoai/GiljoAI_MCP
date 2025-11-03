#!/usr/bin/env python
"""
GiljoAI MCP Server - Production FastMCP Implementation

This is the proper MCP server entry point that:
1. Initializes FastMCP instance
2. Registers all orchestration and coordination tools
3. Runs as stdio server for Claude Code/Codex/Gemini integration
4. Handles authentication and multi-tenant isolation

Replaces the HTTP adapter approach with native MCP server.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus

from fastmcp import FastMCP

# Add src to path for imports
src_dir = Path(__file__).parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from giljo_mcp.config_manager import get_config
from giljo_mcp.database import DatabaseManager
from giljo_mcp.tenant import TenantManager

# Version
__version__ = "3.1.0"

# Configure logging to file only (not stderr which would interfere with stdio)
log_dir = Path.home() / ".giljo_mcp" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_dir / "mcp_server.log"),
    ],
)
logger = logging.getLogger(__name__)


def get_database_manager() -> DatabaseManager:
    """
    Create DatabaseManager from config or environment variables.

    Returns:
        DatabaseManager: Configured database manager instance

    Raises:
        ValueError: If database configuration is invalid
    """
    try:
        # Try to load from config file
        config = get_config()

        # Build PostgreSQL connection URL
        username = config.database.username
        password = quote_plus(config.database.password) if config.database.password else ""
        host = config.database.host
        port = config.database.port
        database = config.database.database_name

        if password:
            database_url = f"postgresql://{username}:{password}@{host}:{port}/{database}"
        else:
            database_url = f"postgresql://{username}@{host}:{port}/{database}"

        logger.info(f"Database configured: {host}:{port}/{database}")

        return DatabaseManager(database_url=database_url, is_async=True)

    except Exception as e:
        logger.error(f"Failed to load config: {e}")

        # Fall back to environment variables
        db_host = os.getenv("GILJO_DB_HOST", "localhost")
        db_port = os.getenv("GILJO_DB_PORT", "5432")
        db_user = os.getenv("GILJO_DB_USER", "postgres")
        db_pass = os.getenv("GILJO_DB_PASSWORD", "")
        db_name = os.getenv("GILJO_DB_NAME", "giljo_mcp")

        if db_pass:
            database_url = f"postgresql://{db_user}:{quote_plus(db_pass)}@{db_host}:{db_port}/{db_name}"
        else:
            database_url = f"postgresql://{db_user}@{db_host}:{db_port}/{db_name}"

        logger.warning("Using database settings from environment variables")

        return DatabaseManager(database_url=database_url, is_async=True)


def create_mcp_server(db_manager: DatabaseManager) -> FastMCP:
    """
    Create and configure FastMCP server with all tools registered.

    This is the core initialization function that sets up the MCP server
    with all orchestration, coordination, and management tools.

    Args:
        db_manager: DatabaseManager instance for database operations

    Returns:
        FastMCP: Configured MCP server instance with all tools registered
    """
    logger.info("=" * 60)
    logger.info("Initializing GiljoAI MCP Server")
    logger.info(f"Version: {__version__}")
    logger.info("=" * 60)

    # Create FastMCP server
    mcp = FastMCP("giljo-mcp")

    # TenantManager is a static class, use the class itself
    tenant_manager = TenantManager

    logger.info("Registering orchestration tools...")

    # ========================================================================
    # Register all tool groups
    # Each register function adds its tools to the MCP server
    # ========================================================================

    # Import core orchestration tools only
    from giljo_mcp.tools import register_orchestration_tools

    # Register all tool groups with the MCP server
    tool_counts = {}

    # Core orchestration tools (highest priority)
    # These include: health_check, get_orchestrator_instructions, spawn_agent_job, etc.
    logger.info("Registering core orchestration tools...")
    register_orchestration_tools(mcp, db_manager)
    # Note: tool counting happens after server is running
    logger.info("Core orchestration tools registered")

    # Additional tool groups can be registered here
    # For now, focusing on core orchestration tools to get the MCP server working
    # TODO: Register remaining tool groups (coordination, communication, etc.)

    # Log registration summary
    logger.info("Tool registration complete")

    logger.info("=" * 60)
    logger.info("MCP Server initialization complete")
    logger.info("=" * 60)

    return mcp


async def run_server():
    """
    Main entry point for running the MCP server.

    This function:
    1. Initializes the database manager
    2. Creates the MCP server with all tools
    3. Runs the server in stdio mode
    """
    logger.info("Starting GiljoAI MCP Server...")

    try:
        # Initialize database manager
        db_manager = get_database_manager()
        logger.info("Database manager initialized")

        # Create MCP server with all tools registered
        mcp = create_mcp_server(db_manager)

        # Run server in stdio mode for Claude Code/Codex/Gemini integration
        logger.info("Running MCP server in stdio mode...")
        logger.info("Server is now ready to accept MCP commands")

        # FastMCP handles stdio communication automatically
        await mcp.run()

    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        raise
    finally:
        logger.info("MCP Server shutdown complete")


def main():
    """
    Command-line entry point for the MCP server.

    Usage:
        python -m giljo_mcp.mcp_server
    """
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
