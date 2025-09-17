"""
GiljoAI MCP Server - FastMCP Implementation
Provides MCP protocol server with tool organization and tenant isolation
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any

from fastmcp import FastMCP

# from fastmcp.types import AnyUrl  # May not be needed

from .config_manager import get_config, ConfigManager
from .database import DatabaseManager
from .tenant import TenantManager

logger = logging.getLogger(__name__)


class GiljoMCPServer:
    """Main MCP server implementation using FastMCP framework"""

    def __init__(self, config: Optional[ConfigManager] = None):
        """Initialize the MCP server with configuration"""
        self.config = config or get_config()
        self.db_manager: Optional[DatabaseManager] = None
        self.tenant_manager: Optional[TenantManager] = None

        # Initialize FastMCP server with lifespan
        self.mcp = FastMCP(name="GiljoAI MCP Server", lifespan=self._lifespan)

    @asynccontextmanager
    async def _lifespan(self):
        """Server lifespan management with proper resource handling"""
        try:
            logger.info("Starting GiljoAI MCP Server...")

            # Initialize database connection
            await self._initialize_database()

            # Initialize tenant manager
            self.tenant_manager = TenantManager(self.db_manager)

            # Register tool groups
            await self._register_tools()

            # Server info endpoints
            self._register_info_endpoints()

            logger.info(f"Server ready on port {self.config.server.mcp_port}")

            yield

        finally:
            logger.info("Shutting down GiljoAI MCP Server...")

            # Cleanup database connections
            if self.db_manager:
                await self.db_manager.close_async()

            logger.info("Server shutdown complete")

    async def _initialize_database(self):
        """Initialize database connection based on configuration"""
        # Build database URL based on configuration
        if self.config.database.type == "postgresql":
            # Use PostgreSQL configuration - try multiple hosts if needed
            hosts = [self.config.database.pg_host, "10.1.0.164"]
            for host in hosts:
                try:
                    db_url = DatabaseManager.build_postgresql_url(
                        host=host,
                        port=self.config.database.pg_port,
                        database=self.config.database.pg_database,
                        username=self.config.database.pg_user,
                        password=self.config.database.pg_password or "4010",
                    )
                    logger.info(
                        f"Attempting PostgreSQL connection to {host}:{self.config.database.pg_port}"
                    )
                    self.db_manager = DatabaseManager(db_url, is_async=True)
                    await self.db_manager.create_tables_async()
                    logger.info(f"Successfully connected to PostgreSQL at {host}")
                    return
                except Exception as e:
                    logger.warning(f"Failed to connect to PostgreSQL at {host}: {e}")
                    continue
            raise Exception("Failed to connect to PostgreSQL with all available hosts")
        else:
            # Default to SQLite for local development
            db_url = DatabaseManager.build_sqlite_url(
                str(self.config.database.sqlite_path)
            )
            logger.info(f"Using SQLite database at {self.config.database.sqlite_path}")

            # Create database manager with async support
            self.db_manager = DatabaseManager(db_url, is_async=True)

            # Initialize database schema
            await self.db_manager.create_tables_async()

            logger.info("Database initialized successfully")

    async def _register_tools(self):
        """Register all tool groups with the MCP server"""
        try:
            # Import tools dynamically to avoid circular imports
            from .tools.project import register_project_tools
            from .tools.agent import register_agent_tools
            from .tools.message import register_message_tools
            from .tools.context import register_context_tools
            from .tools.template import register_template_tools
            from .tools.git import register_git_tools

            # Register each tool group with database and tenant manager
            register_project_tools(self.mcp, self.db_manager, self.tenant_manager)
            register_agent_tools(self.mcp, self.db_manager, self.tenant_manager)
            register_message_tools(self.mcp, self.db_manager, self.tenant_manager)
            register_context_tools(self.mcp, self.db_manager, self.tenant_manager)
            register_template_tools(self.mcp, self.db_manager, self.tenant_manager)
            register_git_tools(self.mcp, self.db_manager, self.tenant_manager)

            logger.info("All tool groups registered successfully")

        except ImportError as e:
            logger.warning(f"Some tools not yet implemented: {e}")

    def _register_info_endpoints(self):
        """Register server information endpoints"""

        @self.mcp.tool()
        async def health() -> Dict[str, Any]:
            """Check server health status"""
            return {
                "status": "healthy",
                "server": "GiljoAI MCP",
                "version": "0.1.0",
                "mode": self.config.server.mode.value,
            }

        @self.mcp.tool()
        async def ready() -> Dict[str, Any]:
            """Check if server is ready to handle requests"""
            # Verify database connectivity
            db_ready = False
            if self.db_manager:
                try:
                    async with self.db_manager.get_session() as session:
                        # Simple query to verify connection
                        await session.execute("SELECT 1")
                        db_ready = True
                except Exception as e:
                    logger.error(f"Database not ready: {e}")

            return {
                "ready": db_ready,
                "database": self.config.database.type,
                "tenant_system": self.tenant_manager is not None,
            }

        @self.mcp.tool()
        async def info() -> Dict[str, Any]:
            """Get server information and capabilities"""
            return {
                "name": "GiljoAI MCP Server",
                "version": "0.1.0",
                "description": "Multi-tenant MCP orchestration server",
                "capabilities": {
                    "project_management": True,
                    "agent_orchestration": True,
                    "message_routing": True,
                    "context_discovery": True,
                    "multi_tenant": True,
                },
                "configuration": {
                    "mode": self.config.server.mode.value,
                    "database": self.config.database.type,
                    "port": self.config.server.mcp_port,
                    "authentication": self._get_auth_mode(),
                },
            }

    def _get_auth_mode(self) -> str:
        """Determine authentication mode based on deployment"""
        if self.config.server.mode.value == "LOCAL":
            return "none"
        elif self.config.server.mode.value == "LAN":
            return "api_key"
        else:
            return "jwt"

    async def run(self, host: str = "localhost", port: Optional[int] = None):
        """Run the MCP server"""
        port = port or self.config.server.mcp_port

        # FastMCP handles the actual server running
        # This is typically done through the CLI or programmatically
        logger.info(f"Starting MCP server on {host}:{port}")

        # Note: FastMCP typically runs via stdio for MCP protocol
        # This method is for initialization and configuration
        return self.mcp


def create_server(config: Optional[ConfigManager] = None) -> GiljoMCPServer:
    """Factory function to create server instance"""
    return GiljoMCPServer(config)


async def main():
    """Main entry point for running the server"""
    config = get_config()
    server = create_server(config)

    # Get the FastMCP instance
    mcp_app = await server.run()

    # FastMCP handles stdio communication for MCP protocol
    # In production, this would be handled by the MCP client connection
    logger.info("MCP Server initialized and ready for connections")

    return mcp_app


if __name__ == "__main__":
    # For direct execution (testing)
    asyncio.run(main())
