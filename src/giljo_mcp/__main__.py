"""
GiljoAI MCP Server - Main Entry Point
Handles server startup, configuration validation, and initialization
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from giljo_mcp.config_manager import get_config, ConfigManager, DeploymentMode
from giljo_mcp.database import DatabaseManager
from giljo_mcp.server import create_server
from giljo_mcp.auth import AuthManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def check_database_connection(config) -> bool:
    """Verify database connectivity with retry logic"""
    hosts_to_try = []
    
    if config.database.type == "postgresql":
        # Try localhost first, then fallback to IP
        hosts_to_try = [config.database.pg_host, "10.1.0.164"]
    
    for attempt, host in enumerate(hosts_to_try or [None], 1):
        try:
            # Build database URL based on configuration
            if config.database.type == "postgresql":
                # Use the current host in retry loop
                db_url = DatabaseManager.build_postgresql_url(
                    host=host,
                    port=config.database.pg_port,
                    database=config.database.pg_database,
                    username=config.database.pg_user,
                    password=config.database.pg_password or "4010"  # Fallback to known password
                )
                logger.info(f"Testing PostgreSQL connection to {host}:{config.database.pg_port} (attempt {attempt})")
            else:
                db_url = DatabaseManager.build_sqlite_url(
                    str(config.database.sqlite_path)
                )
                logger.info(f"Testing SQLite connection at {config.database.sqlite_path}")
                
            # Test connection
            db_manager = DatabaseManager(db_url, is_async=True)
            
            # Try to initialize database
            await db_manager.create_tables_async()
            
            # Close connection
            await db_manager.close_async()
            
            logger.info("Database connection successful")
            
            # If PostgreSQL worked with fallback IP, update config
            if config.database.type == "postgresql" and host != config.database.pg_host:
                logger.info(f"Using fallback host {host} for PostgreSQL")
                config.database.pg_host = host
                
            return True
            
        except Exception as e:
            logger.warning(f"Database connection attempt {attempt} failed: {e}")
            if config.database.type != "postgresql" or attempt == len(hosts_to_try):
                logger.error(f"All database connection attempts failed")
                return False
            continue
    
    return False


async def run_migrations(config) -> bool:
    """Run database migrations if needed"""
    try:
        # For now, we rely on SQLAlchemy's create_all
        # In production, we would use Alembic
        logger.info("Database schema up to date (using SQLAlchemy create_all)")
        return True
        
    except Exception as e:
        logger.error(f"Migration check failed: {e}")
        return False


async def startup_sequence():
    """Main startup sequence for the server"""
    try:
        logger.info("=" * 60)
        logger.info("GiljoAI MCP Server Starting...")
        logger.info("=" * 60)
        
        # Step 1: Load or create configuration
        logger.info("Step 1: Loading configuration...")
        config = get_config()
        
        logger.info(f"Configuration loaded: Mode={config.server.mode.value}, Port={config.server.mcp_port}")
        
        # Step 2: Validate database connection
        logger.info("Step 2: Validating database connection...")
        if not await check_database_connection(config):
            logger.error("Database connection failed. Please check your configuration.")
            return False
        
        # Step 3: Run migrations
        logger.info("Step 3: Checking database migrations...")
        if not await run_migrations(config):
            logger.error("Database migration failed.")
            return False
        
        # Step 4: Initialize authentication
        logger.info("Step 4: Initializing authentication...")
        auth_manager = AuthManager(config)
        
        auth_mode = "None (LOCAL)"
        if config.server.mode == DeploymentMode.LAN:
            auth_mode = "API Key"
        elif config.server.mode == DeploymentMode.WAN:
            auth_mode = "JWT Token"
        
        logger.info(f"Authentication mode: {auth_mode}")
        
        # Step 5: Create and initialize server
        logger.info("Step 5: Creating MCP server...")
        server = create_server(config)
        
        # Step 6: Get FastMCP application
        mcp_app = await server.run(
            host="localhost" if config.server.mode == DeploymentMode.LOCAL else "0.0.0.0",
            port=config.server.mcp_port
        )
        
        logger.info("=" * 60)
        logger.info(f"✅ GiljoAI MCP Server Ready!")
        logger.info(f"Mode: {config.server.mode.value}")
        logger.info(f"Port: {config.server.mcp_port}")
        logger.info(f"Database: {config.database.type}")
        logger.info(f"Authentication: {auth_mode}")
        logger.info("=" * 60)
        
        # Note: In production, FastMCP would handle the stdio communication
        # For testing, we can run the server directly
        if hasattr(mcp_app, 'run_stdio'):
            # Run via stdio for MCP protocol
            await mcp_app.run_stdio()
        else:
            # Keep server running for testing
            logger.info("Server initialized. Ready for MCP client connections.")
            # In production, the MCP client would connect via stdio
            
        return True
        
    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        return False


def main():
    """Main entry point"""
    try:
        # Check Python version
        if sys.version_info < (3, 8):
            logger.error("Python 3.8+ required")
            sys.exit(1)
        
        # Run startup sequence
        success = asyncio.run(startup_sequence())
        
        if not success:
            logger.error("Server startup failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("\nServer shutdown requested")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()